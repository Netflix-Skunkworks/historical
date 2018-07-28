"""
.. module: historical.common.sqs
    :platform: Unix
    :copyright: (c) 2018 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import logging
import uuid

import boto3

from historical.constants import CURRENT_REGION

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(logging.INFO)


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


def produce_events(events, queue_url, batch_size=10):
    """
    Efficiently sends events to the SQS event queue.

    Note: SQS has a max size of 10 items.  Please be aware that this can make the messages go past size -- even
    with shrinking messages!
    """
    client = boto3.client('sqs', region_name=CURRENT_REGION)

    for chunk in chunks(events, batch_size):
        records = [make_sqs_record(event) for event in chunk]

        client.send_message_batch(Entries=records, QueueUrl=queue_url)


def group_records_by_type(records, update_events):
    """Break records into two lists; create/update events and delete events."""
    update_records, delete_records = [], []
    for r in records:
        if r.get("detail-type", "") == "Scheduled Event":
            log.error("[X] Received a Scheduled Event in the Queue... Please check that your environment is set up"
                      " correctly.")
            continue

        # Ignore SQS junk messages (like subscription notices and things):
        if not r.get("detail"):
            continue

        # Do not capture error events:
        if not r["detail"].get("errorCode"):
            if r['detail']['eventName'] in update_events:
                update_records.append(r)
            else:
                delete_records.append(r)

    return update_records, delete_records
