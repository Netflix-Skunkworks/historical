"""
.. module: historical.s3.poller
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import os
import logging

from botocore.exceptions import ClientError

from cloudaux.aws.s3 import list_buckets

from raven_python_lambda import RavenLambdaWrapper

from historical.common.sqs import get_queue_url, produce_events
from historical.constants import CURRENT_REGION, HISTORICAL_ROLE
from historical.s3.models import s3_polling_schema
from historical.common.accounts import get_historical_accounts

logging.basicConfig()
log = logging.getLogger("historical")
log.setLevel(logging.INFO)


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical S3 Poller.

    This poller is run at a set interval in order to ensure that changes do not go undetected by historical.

    Historical pollers generate `polling events` which simulate changes. These polling events contain configuration
    data such as the account/region defining where the collector should attempt to gather data from.
    """
    log.debug('Running poller. Configuration: {}'.format(event))

    queue_url = get_queue_url(os.environ.get('POLLER_QUEUE_NAME', 'HistoricalS3Poller'))

    for account in get_historical_accounts():
        # Skip accounts that have role assumption errors:
        try:
            # List all buckets in the account:
            all_buckets = list_buckets(account_number=account['id'],
                                       assume_role=HISTORICAL_ROLE,
                                       session_name="historical-cloudwatch-s3list",
                                       region=CURRENT_REGION)["Buckets"]

            events = [s3_polling_schema.serialize_me(account['id'], bucket) for bucket in all_buckets]
            produce_events(events, queue_url)
        except ClientError as e:
            log.warning('Unable to generate events for account. AccountId: {account_id} Reason: {reason}'.format(
                account_id=account['id'],
                reason=e
            ))

        log.debug('Finished generating polling events. Events Created: {}'.format(len(account['id'])))
