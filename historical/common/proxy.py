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

from historical.common.exceptions import MissingProxyConfigurationException
from historical.common.sqs import produce_events
from historical.constants import CURRENT_REGION, REGION_ATTR, PROXY_REGIONS, EVENT_TOO_BIG_FLAG

log = logging.getLogger('historical')


@retry(stop_max_attempt_number=4, wait_exponential_multiplier=1000, wait_exponential_max=1000)
def _publish_sns_message(client, blob, topic_arn):
    client.publish(TopicArn=topic_arn, Message=blob)


def shrink_blob(record):
    """
    Makes a shrunken blob to be sent to SNS/SQS (due to the 256KB size limitations of SNS/SQS messages).
    This will essentially remove the "configuration" field such that the size of the SNS/SQS message remains under 256KB.
    :param record:
    :return:
    """
    item = {
        "eventName": record["eventName"],
        EVENT_TOO_BIG_FLAG: True
    }

    # To handle TTLs (if they happen)
    if record.get("userIdentity"):
        item["userIdentity"] = record["userIdentity"]

    # Remove the 'configuration' field from new and old images if applicable:
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
    for record in event['Records']:
        item = make_proper_record(record)

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


def make_proper_record(record):
    """Prepares and ships an individual record over to SNS/SQS for future processing.

    :param record:
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

    blob = json.dumps(record)

    size = math.ceil(sys.getsizeof(blob) / 1024)
    if size >= 256:
        # Need to send over a smaller blob to inform the recipient that it needs to go out and
        # fetch the item from the Historical table!
        blob = json.dumps(shrink_blob(record))

    return blob
