"""
.. module: historical.s3.poller
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import os
import uuid
import logging

import boto3
from botocore.exceptions import ClientError

from cloudaux.aws.s3 import list_buckets

from raven_python_lambda import RavenLambdaWrapper

from historical.constants import CURRENT_REGION, HISTORICAL_ROLE
from historical.s3.models import s3_polling_schema
from historical.common.accounts import get_historical_accounts

logging.basicConfig()
log = logging.getLogger("historical")
log.setLevel(logging.INFO)


def get_record(all_buckets, index, account):
    return {
        "Data": bytes(s3_polling_schema.serialize_me(account, {
            "bucket_name": all_buckets[index]["Name"],
            "creation_date": all_buckets[index]["CreationDate"].replace(tzinfo=None, microsecond=0).isoformat() + "Z"
        }), "utf-8"),
        "PartitionKey": uuid.uuid4().hex
    }


def create_polling_event(account, stream):
    # Place onto the S3 Kinesis stream each S3 bucket for each account...
    # This should probably fan out on an account-by-account basis (we'll need to examine if this is an issue)
    all_buckets = list_buckets(account_number=account,
                               assume_role=HISTORICAL_ROLE,
                               session_name="historical-cloudwatch-s3list",
                               region=CURRENT_REGION)["Buckets"]
    client = boto3.client("kinesis", region_name=CURRENT_REGION)

    # Need to add all buckets into the stream:
    limiter = int(os.environ.get("MAX_BUCKET_BATCH", 50))
    current_batch = 1
    total_batch = int(len(all_buckets) / limiter)
    remainder = len(all_buckets) % limiter
    offset = 0
    while current_batch <= total_batch:
        records = []
        while offset < (limiter * current_batch):
            records.append(get_record(all_buckets, offset, account))
            offset += 1

        client.put_records(Records=records, StreamName=stream)
        current_batch += 1

    # Process remainder:
    if remainder:
        records = []
        while offset < len(all_buckets):
            records.append(get_record(all_buckets, offset, account))
            offset += 1

        client.put_records(Records=records, StreamName=stream)


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical S3 event poller.

    This poller is run at a set interval in order to ensure that changes do not go undetected by historical.

    Historical pollers generate `polling events` which simulate changes. These polling events contain configuration
    data such as the account/region defining where the collector should attempt to gather data from.
    """
    log.debug('Running poller. Configuration: {}'.format(event))

    for account in get_historical_accounts():
        # Skip accounts that have role assumption errors:
        try:
            create_polling_event(account['id'], os.environ.get("HISTORICAL_STREAM", "HistoricalS3PollerStream"))
        except ClientError as e:
            log.warning('Unable to generate events for account. AccountId: {account_id} Reason: {reason}'.format(
                account_id=account['id'],
                reason=e
            ))

        log.debug('Finished generating polling events. Events Created: {}'.format(len(account['id'])))
