"""
.. module: historical.security_group.poller
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import os
import logging

from botocore.exceptions import ClientError

from raven_python_lambda import RavenLambdaWrapper
from cloudaux.aws.ec2 import describe_security_groups

from historical.common.sqs import get_queue_url, produce_events
from historical.common.util import deserialize_records
from historical.constants import POLL_REGIONS, HISTORICAL_ROLE, LOGGING_LEVEL, RANDOMIZE_POLLER
from historical.models import HistoricalPollerTaskEventModel
from historical.security_group.models import security_group_polling_schema
from historical.common.accounts import get_historical_accounts

logging.basicConfig()
log = logging.getLogger("historical")
log.setLevel(LOGGING_LEVEL)


@RavenLambdaWrapper()
def poller_tasker_handler(event, context):
    """
    Historical Security Group Poller Tasker.

    The Poller is run at a set interval in order to ensure that changes do not go undetected by Historical.

    Historical pollers generate `polling events` which simulate changes. These polling events contain configuration
    data such as the account/region defining where the collector should attempt to gather data from.

    This is the entry point. This will task subsequent Poller lambdas to list all of a given resource in a select few
    AWS accounts.
    """
    log.debug('[@] Running Poller Tasker...')

    queue_url = get_queue_url(os.environ.get('POLLER_TASKER_QUEUE_NAME', 'HistoricalSecurityGroupPollerTasker'))
    poller_task_schema = HistoricalPollerTaskEventModel()

    events = []
    for account in get_historical_accounts():
        for region in POLL_REGIONS:
            events.append(poller_task_schema.serialize_me(account['id'], region))

    try:
        produce_events(events, queue_url, randomize_delay=RANDOMIZE_POLLER)
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

    collector_poller_queue_url = get_queue_url(os.environ.get('POLLER_QUEUE_NAME', 'HistoricalSecurityGroupPoller'))
    takser_queue_url = get_queue_url(os.environ.get('POLLER_TASKER_QUEUE_NAME', 'HistoricalSecurityGroupPollerTasker'))

    poller_task_schema = HistoricalPollerTaskEventModel()
    records = deserialize_records(event['Records'])

    for record in records:
        # Skip accounts that have role assumption errors:
        try:
            # Did we get a NextToken?
            if record.get('NextToken'):
                log.debug(f"[@] Received pagination token: {record['NextToken']}")
                groups = describe_security_groups(
                    account_number=record['account_id'],
                    assume_role=HISTORICAL_ROLE,
                    region=record['region'],
                    MaxResults=200,
                    NextToken=record['NextToken']
                )
            else:
                groups = describe_security_groups(
                    account_number=record['account_id'],
                    assume_role=HISTORICAL_ROLE,
                    region=record['region'],
                    MaxResults=200
                )

            # FIRST THINGS FIRST: Did we get a `NextToken`? If so, we need to enqueue that ASAP because
            # 'NextToken`s expire in 60 seconds!
            if groups.get('NextToken'):
                logging.debug(f"[-->] Pagination required {groups['NextToken']}. Tasking continuation.")
                produce_events(
                    [poller_task_schema.serialize_me(record['account_id'], record['region'],
                                                     next_token=groups['NextToken'])],
                    takser_queue_url
                )

            # Task the collector to perform all the DDB logic -- this will pass in the collected data to the
            # collector in very small batches.
            events = [security_group_polling_schema.serialize(record['account_id'], g, record['region'])
                      for g in groups['SecurityGroups']]
            produce_events(events, collector_poller_queue_url, batch_size=3)

            log.debug(f"[@] Finished generating polling events. Account: {record['account_id']}/{record['region']} "
                      f"Events Created: {len(events)}")
        except ClientError as e:
            log.error(f"[X] Unable to generate events for account/region. Account Id/Region: {record['account_id']}"
                      f"/{record['region']} Reason: {e}")
