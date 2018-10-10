"""
.. module: historical.common.sqs
    :platform: Unix
    :copyright: (c) 2018 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import logging
import uuid
import random

import boto3

from historical.constants import CURRENT_REGION

logging.basicConfig()
LOG = logging.getLogger('historical')
LOG.setLevel(logging.INFO)


def chunks(event_list, chunk_size):
    """Yield successive n-sized chunks from the event list."""
    for i in range(0, len(event_list), chunk_size):
        yield event_list[i:i + chunk_size]


def get_queue_url(queue_name):
    """Get the URL of the SQS queue to send events to."""
    client = boto3.client("sqs", CURRENT_REGION)
    queue = client.get_queue_url(QueueName=queue_name)

    return queue["QueueUrl"]


def make_sqs_record(event, delay_seconds=0):
    """Get a dict with the components required for SQS"""
    return {
        "Id": uuid.uuid4().hex,
        "DelaySeconds": delay_seconds,
        "MessageBody": event
    }


def get_random_delay(max_seconds):
    """Gets a randomized number between 0 and the max number in seconds for
       how long a message in SQS should be delayed.

       900 seconds (15 min) is the maximum permitted by SQS.
    :param max_seconds:
    :return:
    """
    return random.randint(0, max_seconds)  # nosec


def produce_events(events, queue_url, batch_size=10, randomize_delay=0):
    """
    Efficiently sends events to the SQS event queue.

    Note: SQS has a max size of 10 items.  Please be aware that this can make the messages go past size -- even
    with shrinking messages!

    Events can get randomized delays, maximum of 900 seconds. Set that in `randomize_delay`
    :param events:
    :param queue_url:
    :param batch_size:
    :param randomize_delay:
    """
    client = boto3.client('sqs', region_name=CURRENT_REGION)

    for chunk in chunks(events, batch_size):
        records = [make_sqs_record(event, delay_seconds=get_random_delay(randomize_delay)) for event in chunk]

        client.send_message_batch(Entries=records, QueueUrl=queue_url)


def group_records_by_type(records, update_events):
    """Break records into two lists; create/update events and delete events.

    :param records:
    :param update_events:
    :return update_records, delete_records:
    """
    update_records, delete_records = [], []
    for record in records:
        if record.get("detail-type", "") == "Scheduled Event":
            LOG.error("[X] Received a Scheduled Event in the Queue... Please check that your environment is set up"
                      " correctly.")
            continue

        # Ignore SQS junk messages (like subscription notices and things):
        if not record.get("detail"):
            continue

        # Do not capture error events:
        if not record["detail"].get("errorCode"):
            if record['detail']['eventName'] in update_events:
                update_records.append(record)
            else:
                delete_records.append(record)

    return update_records, delete_records
