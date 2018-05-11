"""
.. module: historical.common.accounts
    :platform: Unix
    :copyright: (c) 2018 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import os

from swag_client.backend import SWAGManager
from swag_client.util import parse_swag_config_options


def get_historical_accounts():
    """Fetches valid accounts from SWAG if enabled or a list accounts."""
    if os.environ.get('SWAG_BUCKET', False):
        swag_opts = {
            'swag.type': 's3',
            'swag.bucket_name': os.environ['SWAG_BUCKET'],
            'swag.data_file': os.environ.get('SWAG_DATA_FILE', 'accounts.json'),
            'swag.region': os.environ.get('SWAG_REGION', 'us-east-1')
        }
        swag = SWAGManager(**parse_swag_config_options(swag_opts))
        accounts = swag.get_service_enabled('historical', search_filter="[?provider=='aws'] && [?owner=='{}']".format(os.environ['SWAG_OWNER']))
    else:
        accounts = os.environ['ENABLED_ACCOUNTS']

    return accounts

