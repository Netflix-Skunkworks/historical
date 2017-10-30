"""
.. module: historical.security_group.poller
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

from swag_client.backend import SWAGManager
from swag_client.util import parse_swag_config_options

from historical.constants import CURRENT_REGION, HISTORICAL_ROLE
from historical.s3.models import s3_polling_schema

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


def create_polling_event(account):
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

        client.put_records(Records=records, StreamName=os.environ["HISTORICAL_STREAM"])
        current_batch += 1

    # Process remainder:
    if remainder:
        records = []
        while offset < len(all_buckets):
            records.append(get_record(all_buckets, offset, account))
            offset += 1

        client.put_records(Records=records, StreamName=os.environ["HISTORICAL_STREAM"])


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical S3 event poller.

    This poller is run at a set interval in order to ensure that changes do not go undetected by historical.

    Historical pollers generate `polling events` which simulate changes. These polling events contain configuration
    data such as the account/region defining where the collector should attempt to gather data from.
    """
    log.debug('Running poller. Configuration: {}'.format(event))

    # Get the queue that we are going to place the events in:
    if os.environ['SWAG_BUCKET']:
        swag_opts = {
            'swag.type': 's3',
            'swag.bucket_name': os.environ['SWAG_BUCKET'],
            'swag.data_file': os.environ['SWAG_DATA_FILE'],
            'swag.region': os.environ['SWAG_REGION'],
            'swag.cache_expires': 0
        }
        swag = SWAGManager(**parse_swag_config_options(swag_opts))
        accounts = [account["id"] for account in swag.get_all("[?provider=='aws']")]
    else:
        accounts = os.environ['ENABLED_ACCOUNTS']

    for account in accounts:
        # Skip accounts that have role assumption errors:
        try:
            create_polling_event(account)
        except ClientError as e:
            log.warning('Unable to generate events for account. AccountId: {account_id} Reason: {reason}'.format(
                account_id=account,
                reason=e
            ))

    log.debug('Finished generating polling events. Events Created: {}'.format(len(accounts)))
