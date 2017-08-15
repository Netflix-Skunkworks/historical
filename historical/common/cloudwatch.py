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
from itertools import zip_longest

import boto3

logger = logging.getLogger(__name__)


def filter_request_parameters(field_name, msg):
    """
    From an event, extract the field name from the message.
    Different API calls put this information in different places, so check a few places.
    """
    val = msg.get('detail', {}).get(field_name, None)

    if not val:
        print(msg.get('detail'))
        val = msg.get('detail', {}).get('requestParameters', {}).get(field_name, None)

    return val


def get_user_identity(event):
    """Gets event identity from event."""
    return event['detail']['userIdentity']


def get_principal(event):
    """Gets principal id from event"""
    ui = get_user_identity(event)
    return ui['principalId'].split(':')[-1]


def get_region(event):
    """Get region from event details."""
    return event['detail']['awsRegion']


def get_event_time(event):
    """Gets the event time from an event"""
    return datetime.strptime(event['detail']['eventTime'], "%Y-%m-%dT%H:%M:%SZ")


def get_account_id(event):
    """Gets the account id from an event"""
    return event['account']


def format_cloudwatch_event(data, source, account, region):
    """Creates an event-detail that looks similar to what would normally come from aws."""
    return {
        "detail-type": "Polling Event via Historical",
        "source": "historical.{0}".format(source),
        "detail": {
            "eventType": "AwsApiCall",
            "eventTime": datetime.utcnow().isoformat(),
            "awsRegion": region,
            "userIdentity": {
                "accountId": account
            },
            "eventData": data,
        }
    }


def grouper(iterable, n, fillvalue=None):
    """Collect data into fixed-length chunks or blocks"""
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def create_events(events, source, account, region):
    """Creates Cloudtrail Events"""
    client = boto3.client('cloudwatch')

    # cloudtrail only accepts 10 events at a time
    for entries in grouper(events, 10):
        client.put_events(
            Entries=[format_cloudwatch_event(e, source, account, region) for e in entries]
        )
