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

log_levels = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG
}


def extract_log_level_from_environment(k, default):
    return log_levels.get(os.environ.get(k)) or int(os.environ.get(k, default))


CURRENT_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
HISTORICAL_ROLE = os.environ.get('HISTORICAL_ROLE', 'Historical')
POLL_REGIONS = os.environ.get('POLL_REGIONS', 'us-east-1').split(",")
PROXY_REGIONS = os.environ.get('PROXY_REGIONS', 'us-east-1').split(",")
REGION_ATTR = os.environ.get('REGION_ATTR', 'Region')
LOGGING_LEVEL = extract_log_level_from_environment('LOGGING_LEVEL', logging.INFO)
EVENT_TOO_BIG_FLAG = "event_too_big"
