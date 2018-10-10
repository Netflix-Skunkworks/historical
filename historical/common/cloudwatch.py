"""
.. module: historical.common.cloudwatch
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
.. author:: Mike Grima <mgrima@netflix.com>
"""
from datetime import datetime

from historical.constants import CURRENT_REGION


def filter_request_parameters(field_name, msg, look_in_response=False):
    """
    From an event, extract the field name from the message.
    Different API calls put this information in different places, so check a few places.
    """
    val = msg['detail'].get(field_name, None)
    try:
        if not val:
            val = msg['detail'].get('requestParameters', {}).get(field_name, None)

        # If we STILL didn't find it -- check if it's in the response element (default off)
        if not val and look_in_response:
            if msg['detail'].get('responseElements'):
                val = msg['detail']['responseElements'].get(field_name, None)

    # Just in case... We didn't find the value, so just make it None:
    except AttributeError:
        val = None

    return val


def get_user_identity(event):
    """Gets event identity from event."""
    return event['detail'].get('userIdentity', {})


def get_principal(event):
    """Gets principal id from the event"""
    user_identity = get_user_identity(event)
    return user_identity.get('principalId', '').split(':')[-1]


def get_region(event):
    """Get region from event details."""
    return event['detail'].get('awsRegion', CURRENT_REGION)


def get_event_time(event):
    """Gets the event time from an event"""
    return datetime.strptime(event['detail']['eventTime'], "%Y-%m-%dT%H:%M:%SZ")


def get_account_id(event):
    """Gets the account id from an event"""
    return event['account']


def get_collected_details(event):
    """Gets collected details if the technology's poller already described the given asset"""
    return event['detail'].get('collected')


def get_historical_base_info(event):
    """Gets the base details from the CloudWatch Event."""
    data = {
        'principalId': get_principal(event),
        'userIdentity': get_user_identity(event),
        'accountId': event['account'],
        'userAgent': event['detail'].get('userAgent'),
        'sourceIpAddress': event['detail'].get('sourceIPAddress'),
        'requestParameters': event['detail'].get('requestParameters')
    }

    if event['detail'].get('eventTime'):
        data['eventTime'] = event['detail']['eventTime']

    if event['detail'].get("eventSource"):
        data['eventSource'] = event['detail']['eventSource']

    return data
