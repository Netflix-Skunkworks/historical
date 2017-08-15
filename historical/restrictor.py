"""
.. module: historical.restrictor
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import os
import logging
from raven_python_lambda import RavenLambdaWrapper

logging.basicConfig()
log = logging.getLogger("Historical")
log.setLevel(logging.INFO)


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical restrictor event handler.

    This function is responsible for restricting and controlling the flow from
    one sqs queue to another. Within historical this function is used to feed
    historical collectors a known rate. This ensures that in the event of event
    storm collectors are able to orderly process events. This also ensures that
    we are good API limit consumers and don't overwhelm AWS description APIs.

    """
    flow_policy = os.environ['FLOW_POLICY']
    log.debug('Current flow policy: {}'.format(flow_policy))
    log.debug('Reading from source queue. QueueName: {}'.format(os.environ['SOURCE_QUEUE']))
    log.debug('Attempting to fetch 10 items from queue.')
    log.debug('Got items. NumItems: {}'.format(len([])))
    log.debug('Writing to destination queue. QueueName: {}'.format(os.environ['DESTINATION_QUEUE']))

