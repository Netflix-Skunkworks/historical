"""
.. module: historical.common.sqs
    :platform: Unix
    :copyright: (c) 2018 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import uuid

import boto3

from historical.constants import CURRENT_REGION


def chunks(event_list, chunk_size):
    """Yield successive n-sized chunks from the event list."""
    for i in range(0, len(event_list), chunk_size):
        yield event_list[i:i + chunk_size]


def get_queue_url(queue_name):
    """Get the URL of the SQS queue to send events to."""
    client = boto3.client("sqs", CURRENT_REGION)
    queue = client.get_queue_url(QueueName=queue_name)

    return queue["QueueUrl"]


def make_sqs_record(event):
    """Get a dict with the components required for SQS"""
    return {
        "Id": uuid.uuid4().hex,
        "DelaySeconds": 0,
        "MessageBody": event
    }


def produce_events(events, queue_url):
    """
    Efficiently sends events to the SQS event queue.
    """
    client = boto3.client('sqs', region_name=CURRENT_REGION)

    # SQS has max size of 10 items:
    for chunk in chunks(events, 10):
        records = [make_sqs_record(event) for event in chunk]

        client.send_message_batch(Entries=records, QueueUrl=queue_url)
