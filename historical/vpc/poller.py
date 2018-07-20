"""
.. module: historical.vpc.poller
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
.. author:: Mike Grima <mgrima@netflix.com>
"""
import os
import logging

from botocore.exceptions import ClientError

from raven_python_lambda import RavenLambdaWrapper
from cloudaux.aws.ec2 import describe_vpcs

from historical.constants import POLL_REGIONS, HISTORICAL_ROLE, LOGGING_LEVEL
from historical.common.util import deserialize_records
from historical.vpc.models import vpc_polling_schema
from historical.models import HistoricalPollerTaskEventModel
from historical.common.accounts import get_historical_accounts
from historical.common.sqs import produce_events, get_queue_url

logging.basicConfig()
log = logging.getLogger("historical")
log.setLevel(LOGGING_LEVEL)


@RavenLambdaWrapper()
def poller_tasker_handler(event, context):
    """
    Historical VPC Poller Tasker.

    The Poller is run at a set interval in order to ensure that changes do not go undetected by Historical.

    Historical pollers generate `polling events` which simulate changes. These polling events contain configuration
    data such as the account/region defining where the collector should attempt to gather data from.

    This is the entry point. This will task subsequent Poller lambdas to list all of a given resource in a select few
    AWS accounts.
    """
    log.debug('[@] Running Poller Tasker...')

    queue_url = get_queue_url(os.environ.get('POLLER_TASKER_QUEUE_NAME', 'HistoricalVPCPollerTasker'))
    poller_task_schema = HistoricalPollerTaskEventModel()

    events = []
    for account in get_historical_accounts():
        for region in POLL_REGIONS:
            events.append(poller_task_schema.serialize_me(account['id'], region))

    try:
        produce_events(events, queue_url)
    except ClientError as e:
        log.error('[X] Unable to generate poller tasker events! Reason: {reason}'.format(reason=e))

    log.debug('[@] Finished tasking the pollers.')


@RavenLambdaWrapper()
def poller_processor_handler(event, context):
    """
    Historical Security Group Poller Processor.

    This will receive events from the Poller Tasker, and will list all objects of a given technology for an
    account/region pair. This will generate `polling events` which simulate changes. These polling events contain
    configuration data such as the account/region defining where the collector should attempt to gather data from.
    """
    log.debug('[@] Running Poller...')

    queue_url = get_queue_url(os.environ.get('POLLER_QUEUE_NAME', 'HistoricalVPCPoller'))

    records = deserialize_records(event['Records'])

    for record in records:
        # Skip accounts that have role assumption errors:
        try:
            vpcs = describe_vpcs(
                account_number=record['account_id'],
                assume_role=HISTORICAL_ROLE,
                region=record['region']
            )

            events = [vpc_polling_schema.serialize(record['account_id'], v) for v in vpcs]
            produce_events(events, queue_url)
            log.debug('[@] Finished generating polling events. Account: {}/{} '
                      'Events Created: {}'.format(record['account_id'], record['region'], len(events)))
        except ClientError as e:
            log.error('[X] Unable to generate events for account/region. Account Id/Region: {account_id}/{region}'
                      ' Reason: {reason}'.format(account_id=record['account_id'], region=record['region'], reason=e))

        log.debug('[@] Finished generating polling events. Events Created: {}'.format(len(record['account_id'])))
