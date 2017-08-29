"""
.. module: historical.security_group.poller
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import logging
import os

from swag_client.backend import SWAGManager
from swag_client.util import parse_swag_config_options

from historical.common.events import create_polling_event

logging.basicConfig()
log = logging.getLogger("historical")
log.setLevel(logging.INFO)


def handler(event, context):
    """
    Historical security group event poller.

    This poller is run at a set interval in order to ensure that changes do not go undetected by historical.

    Historical pollers generate `polling events` which simulate changes. These polling events contain configuration
    data such as the account/region defining where the collector should attempt to gather data from.
    """
    log.debug('Running poller. Configuration: {}'.format(event))

    if os.environ['SWAG_ENABLED']:
        swag_opts = {
            'swag.type': 'dynamodb'
        }
        swag = SWAGManager(**parse_swag_config_options(swag_opts))
        accounts = swag.get_all()
    else:
        accounts = os.environ['ENABLED_ACCOUNTS']

    for account, regions in accounts:
        create_polling_event(account, regions)

    log.debug('Finished generating polling events. Events Created: {}'.format(len(accounts)))
