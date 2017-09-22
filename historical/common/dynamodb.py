import json
import logging

from deepdiff import DeepDiff
from boto3.dynamodb.types import TypeDeserializer

deser = TypeDeserializer()


log = logging.getLogger('historical')


def default_diff(latest_config, current_config):
    """Determine if two revisions have actually changed."""
    diff = DeepDiff(
        latest_config,
        current_config,
        ignore_order=True
    )
    return diff


def remove_current_specific_fields(obj):
    """Remove all fields that belong to the Current table -- that don't belong in the Durable table"""
    # TTL:
    if obj.get('ttl'):
        del obj['ttl']
    return obj


def modify_record(durable_model, current_revision, arn, event_time, diff_func):
    """Handles a DynamoDB MODIFY event type."""
    # We want the newest items first.
    # See: http://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.html
    items = list(durable_model.query(
        arn,
        eventTime__le=event_time,
        scan_index_forward=False,
        limit=1,
        consistent_read=True))

    if items:
        latest_revision = items[0]

        latest_config = latest_revision._get_json()[1]['attributes']['configuration']
        current_config = current_revision._get_json()[1]['attributes']['configuration']

        # Determine if there is truly a difference, disregarding Ephemeral Paths
        diff = diff_func(latest_config, current_config)
        if diff:
            log.debug(
                'Difference found saving new revision to durable table. Arn: {} LatestConfig: {} CurrentConfig: {}'.format(
                    arn, json.dumps(latest_config), json.dumps(current_config)
                ))
            current_revision.save()
    else:
        current_revision.save()
        log.error('Got modify event but no current revision found. Arn: {arn}'.format(arn=arn))


def delete_record(old_image, durable_model):
    """Handles a DynamoDB DELETE event type."""
    data = {}
    for item in old_image:
        data[item] = deser.deserialize(old_image[item])

    data['configuration'] = {}

    # we give our own timestamps for TTL deletions
    del data['eventTime']
    durable_model(**data).save()
    log.debug('Adding deletion marker.')


def process_dynamodb_record(record, durable_model, diff_func=default_diff):
    """Processes a group of DynamoDB NewImage records."""
    arn = record['dynamodb']['Keys']['arn']['S']

    if record['eventName'] in ['INSERT', 'MODIFY']:
        new = remove_current_specific_fields(record['dynamodb']['NewImage'])
        data = {}

        for item in new:
            # this could end up as loss of precision
            data[item] = deser.deserialize(new[item])

        current_revision = durable_model(**data)
        if record['eventName'] == 'INSERT':
            current_revision.save()
            log.debug('Saving new revision to durable table.')

        elif record['eventName'] == 'MODIFY':
            modify_record(durable_model, current_revision, arn, data['eventTime'], diff_func)

    if record['eventName'] == 'REMOVE':
        # only track deletes that are from the dynamodb TTL service
        if record.get('userIdentity'):
            if record['userIdentity']['type'] == 'Service':
                if record['userIdentity']['principalId'] == 'dynamodb.amazonaws.com':
                    old_image = remove_current_specific_fields(record['dynamodb']['OldImage'])
                    delete_record(old_image, durable_model)
