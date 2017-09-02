"""
.. module: historical.security_group.poller
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import os
import logging

from raven_python_lambda import RavenLambdaWrapper
from cloudaux.aws.ec2 import describe_security_groups

from swag_client.backend import SWAGManager
from swag_client.util import parse_swag_config_options

from historical.common.kinesis import produce_events

logging.basicConfig()
log = logging.getLogger("historical")
log.setLevel(logging.INFO)


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical security group event poller.

    This poller is run at a set interval in order to ensure that changes do not go undetected by historical.

    Historical pollers generate `polling events` which simulate changes. These polling events contain configuration
    data such as the account/region defining where the collector should attempt to gather data from.
    """
    log.debug('Running poller. Configuration: {}'.format(event))

    if os.environ.get('SWAG_BUCKET', False):
        swag_opts = {
            'swag.type': 's3',
            'swag.bucket_name': os.environ['SWAG_BUCKET'],
            'swag.data_file': os.environ.get('SWAG_DATA_FILE', 'accounts.json'),
            'swag.region': os.environ.get('SWAG_BUCKET_REGION', 'us-east-1')
        }
        swag = SWAGManager(**parse_swag_config_options(swag_opts))
        accounts = swag.get_all()
    else:
        accounts = os.environ['ENABLED_ACCOUNTS']

    for account in accounts:
        groups = describe_security_groups(account_number=account['id'], assume_role=os.environ['HISTORICAL_ROLE'], region=os.environ['AWS_DEFAULT_REGION'])
        events = [{'group_id': g['GroupId'], 'owner_id': g['OwnerId']} for g in groups['SecurityGroups']]
        produce_events(events, os.environ.get('HISTORICAL_STREAM', 'HistoricalSecurityGroupEventStream'))

        log.debug('Finished generating polling events. Account: {} Events Created: {}'.format(account['id'], len(events)))
