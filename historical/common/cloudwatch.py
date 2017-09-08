"""
Helper functions for processing cloudwatch events.

.. module: historical.cloudwatch
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def filter_request_parameters(field_name, msg):
    """
    From an event, extract the field name from the message.
    Different API calls put this information in different places, so check a few places.
    """
    val = msg.get('detail', {}).get(field_name, None)

    if not val:
        val = msg.get('detail', {}).get('requestParameters', {}).get(field_name, None)

    return val


def get_user_identity(event):
    """Gets event identity from event."""
    return event['detail'].get('userIdentity', {})


def get_principal(event):
    """Gets principal id from event"""
    ui = get_user_identity(event)
    return ui.get('principalId', '').split(':')[-1]


def get_region(event):
    """Get region from event details."""
    return event['detail'].get('awsRegion')


def get_event_time(event):
    """Gets the event time from an event"""
    return datetime.strptime(event['detail']['eventTime'], "%Y-%m-%dT%H:%M:%SZ")


def get_account_id(event):
    """Gets the account id from an event"""
    return event['account']

