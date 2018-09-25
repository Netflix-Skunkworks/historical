"""
.. module: historical.constants
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import logging
import os

from enum import Enum

log_levels = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG
}


def extract_log_level_from_environment(k, default):
    return log_levels.get(os.environ.get(k)) or int(os.environ.get(k, default))


# 24 hours in seconds is the default
TTL_EXPIRY = int(os.environ.get('TTL_EXPIRY', 86400))

# By default, don't randomize the pollers (tasker or collector -- same env var):
RANDOMIZE_POLLER = int(os.environ.get('RANDOMIZE_POLLER', 0))

CURRENT_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
HISTORICAL_ROLE = os.environ.get('HISTORICAL_ROLE', 'Historical')
POLL_REGIONS = os.environ.get('POLL_REGIONS', 'us-east-1').split(",")
PROXY_REGIONS = os.environ.get('PROXY_REGIONS', 'us-east-1').split(",")
REGION_ATTR = os.environ.get('REGION_ATTR', 'Region')
SIMPLE_DURABLE_PROXY = os.environ.get('SIMPLE_DURABLE_PROXY', False)
LOGGING_LEVEL = extract_log_level_from_environment('LOGGING_LEVEL', logging.INFO)
EVENT_TOO_BIG_FLAG = "event_too_big"


class DurableEventTypes(Enum):
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    # EXPIRE = 'EXPIRE'  # Future TTLs on Durable tables??

