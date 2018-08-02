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
from historical.common.util import deserialize_records
from historical.constants import CURRENT_REGION, HISTORICAL_ROLE, LOGGING_LEVEL, RANDOMIZE_POLLER
from historical.models import HistoricalPollerTaskEventModel
from historical.s3.models import s3_polling_schema
from historical.common.accounts import get_historical_accounts

logging.basicConfig()
log = logging.getLogger("historical")
log.setLevel(LOGGING_LEVEL)


@RavenLambdaWrapper()
def poller_tasker_handler(event, context):
    """
    Historical S3 Poller Tasker.

    The Poller is run at a set interval in order to ensure that changes do not go undetected by Historical.

    Historical pollers generate `polling events` which simulate changes. These polling events contain configuration
    data such as the account/region defining where the collector should attempt to gather data from.

    This is the entry point. This will task subsequent Poller lambdas to list all of a given resource in a select few
    AWS accounts.
    """
    log.debug('[@] Running Poller Tasker...')

    queue_url = get_queue_url(os.environ.get('POLLER_TASKER_QUEUE_NAME', 'HistoricalS3PollerTasker'))
    poller_task_schema = HistoricalPollerTaskEventModel()

    events = [poller_task_schema.serialize_me(account['id'], CURRENT_REGION) for account in get_historical_accounts()]

    try:
        produce_events(events, queue_url, randomize_delay=RANDOMIZE_POLLER)
    except ClientError as e:
        log.error('[X] Unable to generate poller tasker events! Reason: {reason}'.format(reason=e))

    log.debug('[@] Finished tasking the pollers.')


@RavenLambdaWrapper()
def poller_processor_handler(event, context):
    """
    Historical S3 Poller Processor.

    This will receive events from the Poller Tasker, and will list all objects of a given technology for an
    account/region pair. This will generate `polling events` which simulate changes. These polling events contain
    configuration data such as the account/region defining where the collector should attempt to gather data from.
    """
    log.debug('[@] Running Poller...')

    queue_url = get_queue_url(os.environ.get('POLLER_QUEUE_NAME', 'HistoricalS3Poller'))

    records = deserialize_records(event['Records'])

    for record in records:
        # Skip accounts that have role assumption errors:
        try:
            # List all buckets in the account:
            all_buckets = list_buckets(account_number=record['account_id'],
                                       assume_role=HISTORICAL_ROLE,
                                       session_name="historical-cloudwatch-s3list",
                                       region=record['region'])["Buckets"]

            events = [s3_polling_schema.serialize_me(record['account_id'], bucket) for bucket in all_buckets]
            produce_events(events, queue_url, randomize_delay=RANDOMIZE_POLLER)
        except ClientError as e:
            log.error('[X] Unable to generate events for account. Account Id: {account_id} Reason: {reason}'.format(
                account_id=record['account_id'], reason=e))

        log.debug('[@] Finished generating polling events for account: {}. Events Created: {}'.format(
            record['account_id'], len(record['account_id'])))
