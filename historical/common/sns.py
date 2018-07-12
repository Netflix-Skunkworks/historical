"""
.. module: historical.common.sns
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
from historical.constants import CURRENT_REGION, REGION_ATTR, SNSPROXY_REGIONS

log = logging.getLogger('historical')


@retry(stop_max_attempt_number=4, wait_exponential_multiplier=1000, wait_exponential_max=1000)
def _publish_message(client, blob, topic_arn):
    client.publish(TopicArn=topic_arn, Message=blob)


def shrink_sns_blob(record):
    """
    Makes a shrunken blob to be sent to SNS (due to the 256KB size limitations of SNS messages).
    This will essentially remove the "configuration" field such that the size of the SNS message remains under 256KB.
    :param record:
    :return:
    """
    sns_item = {
        "eventName": record["eventName"],
        "sns_too_big": True
    }

    # To handle TTLs (if they happen)
    if record.get("userIdentity"):
        sns_item["userIdentity"] = record["userIdentity"]

    # Remove the 'configuration' field from new and old images if applicable:
    if record['dynamodb'].get('NewImage'):
        record['dynamodb']['NewImage'].pop('configuration', None)

    if record['dynamodb'].get('OldImage'):
        record['dynamodb']['OldImage'].pop('configuration', None)

    sns_item['dynamodb'] = record['dynamodb']

    return sns_item


def process_sns_forward(record, topic_arn, client):
    """
    Prepares and ships an individual record over to SNS for future processing.
    :param record:
    :param topic_arn:
    :param client:
    :return:
    """
    # We should NOT be processing this if the item in question does not
    # reside in the SNSPROXY_REGIONS
    for img in ['NewImage', 'OldImage']:
        if record['dynamodb'].get(img):
            if record['dynamodb'][img][REGION_ATTR]['S'] not in SNSPROXY_REGIONS:
                log.debug("[/] Not processing record -- record event took place in: {}".format(
                    record['dynamodb'][img][REGION_ATTR]['S']))
                return

    sns_blob = json.dumps(record)

    size = math.ceil(sys.getsizeof(sns_blob) / 1024)
    if size >= 256:
        # Need to send over a smaller blob to inform the recipient that it needs to go out and
        # fetch the item from the Historical table!
        sns_blob = json.dumps(shrink_sns_blob(record))

    # Send it over!
    _publish_message(client, sns_blob, topic_arn)


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical S3 DynamoDB SNS Forwarder (the SNSProxy).

    Passes events from the Historical DynamoDB stream and passes it to SNS for additional events to trigger.
    """
    topic_arn = os.environ['SNSPROXY_TOPIC_ARN']
    client = boto3.client("sns", region_name=CURRENT_REGION)

    for record in event['Records']:
        process_sns_forward(record, topic_arn, client)
