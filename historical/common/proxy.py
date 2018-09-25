"""
.. module: historical.common.proxy
    :platform: Unix
    :copyright: (c) 2018 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import logging
import json
import math
import os
import sys

import boto3
from retrying import retry

from raven_python_lambda import RavenLambdaWrapper

from historical.common.dynamodb import deserialize_durable_record_to_durable_model, \
    remove_global_dynamo_specific_fields, deser
from historical.common.exceptions import MissingProxyConfigurationException
from historical.common.sqs import produce_events
from historical.constants import CURRENT_REGION, DurableEventTypes, REGION_ATTR, PROXY_REGIONS, EVENT_TOO_BIG_FLAG,\
    SIMPLE_DURABLE_PROXY

from historical.mapping import DURABLE_MAPPING, HISTORICAL_TECHNOLOGY

log = logging.getLogger('historical')


@retry(stop_max_attempt_number=4, wait_exponential_multiplier=1000, wait_exponential_max=1000)
def _publish_sns_message(client, blob, topic_arn):
    client.publish(TopicArn=topic_arn, Message=blob)


def shrink_blob(record, deletion):
    """
    Makes a shrunken blob to be sent to SNS/SQS (due to the 256KB size limitations of SNS/SQS messages).
    This will essentially remove the "configuration" field such that the size of the SNS/SQS message remains under
    256KB.
    :param record:
    :return:
    """
    item = {
        "eventName": record["eventName"],
        EVENT_TOO_BIG_FLAG: (not deletion)
    }

    # To handle TTLs (if they happen)
    if record.get("userIdentity"):
        item["userIdentity"] = record["userIdentity"]

    # Remove the 'configuration' field from new and old images if applicable:
    if not deletion:
        # Only remove it from non-deletions:
        if record['dynamodb'].get('NewImage'):
            record['dynamodb']['NewImage'].pop('configuration', None)

    if record['dynamodb'].get('OldImage'):
        record['dynamodb']['OldImage'].pop('configuration', None)

    item['dynamodb'] = record['dynamodb']

    return item


@RavenLambdaWrapper()
def handler(event, context):
    """Historical S3 DynamoDB Stream Forwarder (the 'Proxy').

    Passes events from the Historical DynamoDB stream and passes it to SNS or SQS for additional events to trigger.

    You can optionally use SNS or SQS. It is preferable to use SNS -> SQS, but in some cases, such as the Current stream
    to the Differ, this will make use of SQS to directly feed into the differ for performance purposes.
    """
    queue_url = os.environ.get('PROXY_QUEUE_URL')
    topic_arn = os.environ.get('PROXY_TOPIC_ARN')

    if not queue_url and not topic_arn:
        raise MissingProxyConfigurationException('[X] Must set the `PROXY_QUEUE_URL` or the `PROXY_TOPIC_ARN` vars.')

    items_to_ship = []

    # Must ALWAYS shrink for SQS because of 256KB limit of sending batched messages
    force_shrink = True if queue_url else False

    # Is this a "Simple Durable Proxy" -- that is -- are we stripping out all of the DynamoDB data from
    # the Differ?
    record_maker = make_proper_simple_record if SIMPLE_DURABLE_PROXY else make_proper_dynamodb_record

    for record in event['Records']:
        item = record_maker(record, force_shrink=force_shrink)

        # If there are no items, don't append anything:
        if item:
            items_to_ship.append(item)

    if items_to_ship:
        # SQS:
        if queue_url:
            produce_events(items_to_ship, queue_url)

        # SNS:
        else:
            client = boto3.client("sns", region_name=CURRENT_REGION)
            for i in items_to_ship:
                _publish_sns_message(client, i, topic_arn)


def make_proper_dynamodb_record(record, force_shrink=False):
    """Prepares and ships an individual DynamoDB record over to SNS/SQS for future processing.

    :param record:
    :param force_shrink:
    :return:
    """
    # We should NOT be processing this if the item in question does not
    # reside in the PROXY_REGIONS
    for img in ['NewImage', 'OldImage']:
        if record['dynamodb'].get(img):
            if record['dynamodb'][img][REGION_ATTR]['S'] not in PROXY_REGIONS:
                log.debug("[/] Not processing record -- record event took place in: {}".format(
                    record['dynamodb'][img][REGION_ATTR]['S']))
                return

    # Get the initial blob and determine if it is too big for SNS/SQS:
    blob = json.dumps(record)
    size = math.ceil(sys.getsizeof(blob) / 1024)

    # If it is too big, then we need to send over a smaller blob to inform the recipient that it needs to go out and
    # fetch the item from the Historical table!
    if size >= 200 or force_shrink:
        deletion = False
        # ^^ However -- deletions need to be handled differently, because the Differ won't be able to find a
        # deleted record. For deletions, we will only shrink the 'OldImage', but preserve the 'NewImage' since that is
        # "already" shrunken.
        if record['dynamodb'].get('NewImage'):
            # Config will be empty if there was a deletion:
            if not (record['dynamodb']['NewImage'].get('configuration', {}) or {}).get('M'):
                deletion = True

        blob = json.dumps(shrink_blob(record, deletion))

    return blob


def _get_durable_pynamo_obj(record_data, durable_model):
    image = remove_global_dynamo_specific_fields(record_data)
    data = {}

    for item, value in image.items():
        # This could end up as loss of precision
        data[item] = deser.deserialize(value)

    return durable_model(**data)


def make_proper_simple_record(record, force_shrink=False):
    """Prepares and ships an individual simplified durable table record over to SNS/SQS for future processing.

    :param record:
    :param force_shrink:
    :return:
    """
    # We should NOT be processing this if the item in question does not
    # reside in the PROXY_REGIONS
    for img in ['NewImage', 'OldImage']:
        if record['dynamodb'].get(img):
            if record['dynamodb'][img][REGION_ATTR]['S'] not in PROXY_REGIONS:
                log.debug("[/] Not processing record -- record event took place in: {}".format(
                    record['dynamodb'][img][REGION_ATTR]['S']))
                return

    # Convert to a simple object
    item = {
        'arn': record['dynamodb']['Keys']['arn']['S'],
        'event_time': record['dynamodb']['NewImage']['eventTime']['S'],
        'tech': HISTORICAL_TECHNOLOGY
    }

    # Get the proper event type:
    if not (record['dynamodb']['NewImage'].get('configuration', {}) or {}).get('M'):
        item['event'] = DurableEventTypes.DELETE.value

    elif not record['dynamodb'].get('OldImage'):
        item['event'] = DurableEventTypes.CREATE.value

    else:
        item['event'] = DurableEventTypes.UPDATE.value

    # We need to de-serialize the raw DynamoDB object into the proper PynamoDB obj:
    prepped_new_record = _get_durable_pynamo_obj(record['dynamodb']['NewImage'],
                                                 DURABLE_MAPPING.get(HISTORICAL_TECHNOLOGY))

    if record['dynamodb'].get('OldImage') or {}:
        prepped_old_record = _get_durable_pynamo_obj(record['dynamodb']['OldImage'],
                                                     DURABLE_MAPPING.get(HISTORICAL_TECHNOLOGY))
    else:
        prepped_old_record = {}

    item['new_image'] = dict(prepped_new_record)
    item['old_image'] = dict(prepped_old_record)

    # Get the initial blob and determine if it is too big for SNS/SQS:
    blob = json.dumps(item)
    size = math.ceil(sys.getsizeof(blob) / 1024)

    # If it is too big, then we need to send over a smaller blob to inform the recipient that it needs to go out and
    # fetch the item from the Historical table!
    if size >= 200 or force_shrink:
        del item['new_image']
        del item['old_image']

        item[EVENT_TOO_BIG_FLAG] = True

        blob = json.dumps(item)

    return blob
