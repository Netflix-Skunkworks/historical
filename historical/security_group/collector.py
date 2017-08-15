"""
.. module: historical.security_group.collector
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import logging
import os

from raven_python_lambda import RavenLambdaWrapper
from cloudaux.aws.ec2 import describe_security_groups
from cloudaux.aws.sqs import get_queue_url, receive_message

from historical.common.events import process_poller_event, determine_event_type, process_cloudwatch_event
from historical.security_group.models import CurrentSecurityGroupModel

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(logging.INFO)


def get_configuration_data(data):
    """Describes the current state of the object."""
    return describe_security_groups(**data)


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical security group event collector.

    This collector is responsible for processing Cloudwatch events and polling events.

    Polling Events
    When a polling event is received, this function is responsible for persisting
    configuration data to the correct DynamoDB tables.

    Cloudwatch Events
    When a Cloudwatch event is received, this function must first fetch configuration
    data from AWS before persisting data.
    """
    # we should be handle events directly or attempt to grab them from the restrictor
    if os.environ.get('RESTRICTOR_ENABLED'):
        log.debug('Fetching items from source queue. QueueName: {}'.format(os.environ['SOURCE_QUEUE']))
        url = get_queue_url(QueueName=os.environ.get('HISTORICAL_QUEUE_NAME', 'HistoricalSecurityGroupIngest'))
        events = receive_message(QueueUrl=url, MaxNumberOfMessage=10)
        log.debug('Items found in queue. NumberEvents: {}'.format(len(events)))
    else:
        events = [event]

    for event in events:
        event_type = determine_event_type(event)

        if event_type == 'poller':
            data = process_poller_event(event)

        elif event_type == 'cloudwatch':
            data = process_cloudwatch_event(event)

        log.debug('Successfully processed event. Data: {data}'.format(data=data))

        current_revision = CurrentSecurityGroupModel(**data)
        current_revision.save()
        log.debug('Successfully updated current Historical table')
