"""
.. module: historical.common.dynamodb
    :platform: Unix
    :copyright: (c) 2018 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import json
import logging

from deepdiff import DeepDiff
from boto3.dynamodb.types import TypeDeserializer

from historical.constants import REGION_ATTR

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
    # DynamoDB Global Table items:
    # https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/globaltables_HowItWorks.html
    obj.pop("aws:rep:deleting", None)
    obj.pop("aws:rep:updatetime", None)
    obj.pop("aws:rep:updateregion", None)

    obj.pop("ttl", None)
    obj.pop("eventSource", None)

    return obj


def modify_record(durable_model, current_revision, arn, event_time, diff_func):
    """Handles a DynamoDB MODIFY event type."""
    # We want the newest items first.
    # See: http://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.html
    items = list(durable_model.query(
        arn,
        (durable_model.eventTime <= event_time),
        scan_index_forward=False,
        limit=1,
        consistent_read=True))

    if items:
        latest_revision = items[0]

        latest_config = latest_revision._get_json()[1]['attributes']
        current_config = current_revision._get_json()[1]['attributes']

        # Determine if there is truly a difference, disregarding Ephemeral Paths
        diff = diff_func(latest_config, current_config)
        if diff:
            log.debug(
                '[~] Difference found saving new revision to durable table. Arn: {} LatestConfig: {} '
                'CurrentConfig: {}'.format(arn, json.dumps(latest_config), json.dumps(current_config)))
            current_revision.save()
    else:
        current_revision.save()
        log.error('Got modify event but no current revision found. Arn: {arn}'.format(arn=arn))


def delete_differ_record(old_image, durable_model, region_attr):
    """Handles a DynamoDB DELETE event type -- For the Differ."""
    data = {}
    for item in old_image:
        data[item] = deser.deserialize(old_image[item])

    data['configuration'] = {}
    # we give our own timestamps for TTL deletions
    del data['eventTime']
    durable_model(**data).save()
    log.debug('[+] Adding deletion marker.')


def deserialize_current_to_durable(record, current_model, durable_model):
    """
    Utility function that will take a dynamo event record and turn it into the proper pynamo object.

    This will remove the "current table" specific fields, and properly deserialize the ugly Dynamo datatypes away.
    :param record:
    :param model:
    :return:
    """
    # Was the item in question too big for SNS? If so, then we need to fetch the item from the current Dynamo table:
    if record.get("sns_too_big"):
        arn = record['dynamodb']['Keys']['arn']['S']
        log.debug('[-->] Item with ARN: {} was too big for SNS -- fetching it from the Current table...'.format(arn))
        item = list(current_model.query(arn))

        # If for whatever reason, the item *cannot* be found, then this record should be skipped over.
        # This will happen if this event came in and got processed right after the item was deleted
        # from the Current table. If so, then do nothing -- the deletion event will be processed later.
        if not item:
            return None

        # We need to place the real configuration data into the record so it can be deserialized into
        # the durable model correctly:
        record['dynamodb']['NewImage']['configuration'] = item[0]._serialize()['attributes']['configuration']

    new_image = remove_current_specific_fields(record['dynamodb']['NewImage'])
    data = {}

    for item in new_image:
        # This could end up as loss of precision
        data[item] = deser.deserialize(new_image[item])

    return durable_model(**data)


def process_dynamodb_differ_record(record, current_model, durable_model, diff_func=None):
    """
    Processes a DynamoDB NewImage record (for Differ events).

    This will ONLY process the record if the record exists in one of the regions defined by the SNSPROXY_REGIONS of
    the current SNSProxy function.
    """
    diff_func = diff_func or default_diff

    # De-serialize the the record (it's an SNS message inside of an SQS event message):
    record = json.loads(json.loads(record['body'])['Message'])

    # Nothing special needs to be done for deletions as far as items that are too big for SNS are concerned.
    # This is because the deletion will remove the `configuration` field and save the item without it.
    if record['eventName'] == 'REMOVE':
        # We are *ONLY* tracking the deletions from the DynamoDB TTL service.
        # Why? Because when we process deletion records, we are first saving a new "empty" revision to the "Current"
        # table. The "empty" revision will then trigger this Lambda as a "MODIFY" event. Then, right after it saves
        # the "empty" revision, it will then delete the item from the "Current" table. At that point,
        # we have already saved the "deletion revision" to the "Durable" table. Thus, no need to process
        # the deletion events -- except for TTL expirations (which should never happen -- but if they do, you need
        # to investigate why...)
        if record.get('userIdentity'):
            if record['userIdentity']['type'] == 'Service':
                if record['userIdentity']['principalId'] == 'dynamodb.amazonaws.com':
                    log.error('We received a TTL delete. Old Image: {}'.format(record['dynamodb']['OldImage']))
                    old_image = remove_current_specific_fields(record['dynamodb']['OldImage'])
                    delete_differ_record(old_image, durable_model, REGION_ATTR)

    if record['eventName'] in ['INSERT', 'MODIFY']:
        arn = record['dynamodb']['Keys']['arn']['S']
        current_revision = deserialize_current_to_durable(record, current_model, durable_model)

        if not current_revision:
            log.error("[?] Received item too big for SNS, and was not able to find the original item with ARN: {}"
                      .format(arn))
            return

        if record['eventName'] == 'INSERT':
            current_revision.save()
            log.debug('[+] Saving new revision to durable table.')

        elif record['eventName'] == 'MODIFY':
            modify_record(durable_model, current_revision, arn, current_revision.eventTime, diff_func)
