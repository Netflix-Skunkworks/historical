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
    obj.pop("ttl", None)

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


def deserialize_current_dynamo_to_pynamo(record, model):
    """
    Utility function that will take a dynamo event record and turn it into the proper pynamo object.

    This will remove the "current table" specific fields, and properly deserialize the ugly Dynamo datatypes away.
    :param record:
    :param model:
    :return:
    """
    new_image = remove_current_specific_fields(record['dynamodb']['NewImage'])
    data = {}

    for item in new_image:
        # This could end up as loss of precision
        data[item] = deser.deserialize(new_image[item])

    return model(**data)


def process_dynamodb_record(record, durable_model, diff_func=None):
    """Processes a group of DynamoDB NewImage records."""
    diff_func = diff_func or default_diff

    arn = record['dynamodb']['Keys']['arn']['S']

    if record['eventName'] in ['INSERT', 'MODIFY']:
        current_revision = deserialize_current_dynamo_to_pynamo(record, durable_model)

        if record['eventName'] == 'INSERT':
            current_revision.save()
            log.debug('Saving new revision to durable table.')

        elif record['eventName'] == 'MODIFY':
            modify_record(durable_model, current_revision, arn, current_revision.eventTime, diff_func)

    if record['eventName'] == 'REMOVE':
        # We are *ONLY* tracking the deletions from the DynamoDB TTL service.
        # Why? Because when we process deletion records, we are first saving a new "empty" revision to the "Current"
        # table. The "empty" revision will then trigger this Lambda as a "MODIFY" event. Then, right after it saves
        # the "empty" revision, it will then delete the item from the "Current" table. At that point,
        # we have already saved the "deletion revision" to the "Historical" table. Thus, no need to process
        # the deletion events -- except for TTL expirations (which should never happen -- but if they do, you need
        # to investigate why...)
        if record.get('userIdentity'):
            if record['userIdentity']['type'] == 'Service':
                if record['userIdentity']['principalId'] == 'dynamodb.amazonaws.com':
                    old_image = remove_current_specific_fields(record['dynamodb']['OldImage'])
                    delete_record(old_image, durable_model)
