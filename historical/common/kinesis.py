import sys

import json
import uuid
import base64

import boto3


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def determine_chunk_size(events):
    """Determines the number of event """
    total_size = 0

    for e in events:
        total_size += sys.getsizeof(e['Data'])
    return total_size


def produce_events(events, stream):
    """
    Efficiently batches and sends events to kinesis stream.

    Initially tries the max batch size of 500 records. If after encoding this
    is over the 5mb limit it attempts to backoff the number of records until
    it falls below the 5mb limit.
    """
    client = boto3.client('kinesis')

    events = [
        {
            'Data': json.dumps(event).encode('utf-8'),
            'PartitionKey': uuid.uuid4().hex
        } for event in events
    ]

    chunk_size = 500

    while True:
        if determine_chunk_size(events) >= 5242880:
            chunk_size = chunk_size / 2
        else:
            break

    for chunk in chunks(events, 500):
        client.put_records(
            Records=chunk,
            StreamName=stream
        )


def deserialize_records(records):
    """
    Kinesis records come in a base64 encoded format. This function
    parses these records and returns native python data structures.
    """
    native_records = []
    for r in records:
        native_records.append(
            json.loads(
                base64.b64decode(r['kinesis']['data'])
            )
        )
    return native_records
