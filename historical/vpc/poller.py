"""
.. module: historical.vpc.poller
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import os
import logging

from botocore.exceptions import ClientError

from raven_python_lambda import RavenLambdaWrapper
from cloudaux.aws.ec2 import describe_vpcs

from historical.constants import POLL_REGIONS, HISTORICAL_ROLE
from historical.vpc.models import vpc_polling_schema
from historical.common.accounts import get_historical_accounts
from historical.common.sqs import produce_events, get_queue_url

logging.basicConfig()
log = logging.getLogger("historical")
log.setLevel(logging.INFO)


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical VPC Poller.

    This Poller is run at a set interval in order to ensure that changes do not go undetected by historical.

    Historical Pollers generate `polling events` which simulate changes. These polling events contain configuration
    data such as the account/region defining where the collector should attempt to gather data from.
    """
    log.debug('Running poller. Configuration: {}'.format(event))

    queue_url = get_queue_url(os.environ.get('POLLER_QUEUE_NAME', 'HistoricalVPCPoller'))

    for account in get_historical_accounts():
        for region in POLL_REGIONS:
            try:
                vpcs = describe_vpcs(
                    account_number=account['id'],
                    assume_role=HISTORICAL_ROLE,
                    region=region
                )

                events = [vpc_polling_schema.serialize(account['id'], v) for v in vpcs]
                produce_events(events, queue_url)
                log.debug('Finished generating polling events. Account: {}/{} '
                          'Events Created: {}'.format(account['id'], region, len(events)))
            except ClientError as e:
                log.warning('Unable to generate events for account/region. Account Id/Region: {account_id}/{region}'
                            ' Reason: {reason}'.format(account_id=account['id'], region=region, reason=e))
