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

from historical.constants import HISTORICAL_ROLE, LOGGING_LEVEL, POLL_REGIONS, RANDOMIZE_POLLER
from historical.common.util import deserialize_records
from historical.vpc.models import VPC_POLLING_SCHEMA
from historical.models import HistoricalPollerTaskEventModel
from historical.common.accounts import get_historical_accounts
from historical.common.sqs import get_queue_url, produce_events

logging.basicConfig()
LOG = logging.getLogger("historical")
LOG.setLevel(LOGGING_LEVEL)


@RavenLambdaWrapper()
def poller_tasker_handler(event, context):  # pylint: disable=W0613
    """
    Historical VPC Poller Tasker.

    The Poller is run at a set interval in order to ensure that changes do not go undetected by Historical.

    Historical pollers generate `polling events` which simulate changes. These polling events contain configuration
    data such as the account/region defining where the collector should attempt to gather data from.

    This is the entry point. This will task subsequent Poller lambdas to list all of a given resource in a select few
    AWS accounts.
    """
    LOG.debug('[@] Running Poller Tasker...')

    queue_url = get_queue_url(os.environ.get('POLLER_TASKER_QUEUE_NAME', 'HistoricalVPCPollerTasker'))
    poller_task_schema = HistoricalPollerTaskEventModel()

    events = []
    for account in get_historical_accounts():
        for region in POLL_REGIONS:
            events.append(poller_task_schema.serialize_me(account['id'], region))

    try:
        produce_events(events, queue_url, randomize_delay=RANDOMIZE_POLLER)
    except ClientError as exc:
        LOG.error(f'[X] Unable to generate poller tasker events! Reason: {exc}')

    LOG.debug('[@] Finished tasking the pollers.')


@RavenLambdaWrapper()
def poller_processor_handler(event, context):  # pylint: disable=W0613
    """
    Historical Security Group Poller Processor.

    This will receive events from the Poller Tasker, and will list all objects of a given technology for an
    account/region pair. This will generate `polling events` which simulate changes. These polling events contain
    configuration data such as the account/region defining where the collector should attempt to gather data from.
    """
    LOG.debug('[@] Running Poller...')

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

            events = [VPC_POLLING_SCHEMA.serialize(record['account_id'], v) for v in vpcs]
            produce_events(events, queue_url, randomize_delay=RANDOMIZE_POLLER)
            LOG.debug(f"[@] Finished generating polling events. Account: {record['account_id']}/{record['region']} "
                      f"Events Created: {len(events)}")
        except ClientError as exc:
            LOG.error(f"[X] Unable to generate events for account/region. Account Id/Region: {record['account_id']}"
                      f"/{record['region']} Reason: {exc}")
