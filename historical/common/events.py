"""
.. module: historical.common.events
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
from historical.common.cloudwatch import filter_request_parameters, get_region, get_user_identity, get_principal, \
    get_event_time, get_account_id


def process_poller_event(event):
    """Use poller event data to describe configuration data."""
    return dict()


def determine_event_type(event):
    """Determines whether we have a cloudwatch event or a polling event."""
    return 'cloudwatch'


def process_cloudwatch_event(event):
    """Use cloudwatch event data to describe configuration data."""
    aws_group_id = filter_request_parameters('groupId', event)

    data = dict(
        aws_region=get_region(event),
        user_identity=get_user_identity(event),
        principal_id=get_principal(event),
        event_time=get_event_time(event),
        aws_group_id=aws_group_id,
        aws_account_id=get_account_id(event)
    )

    if event.get('eventName') == 'DeleteSecurityGroup':
        data['revision'] = {}

    else:
        group = describe_security_group(
            get_account_id(event),
            get_region(event),
            None,
            aws_group_id,
        )

        data['aws_vpc_id'] = group['VpcId']
        data['revision'] = group

    return data


def create_polling_event(account, region):
    """Creates a new polling event."""
    pass