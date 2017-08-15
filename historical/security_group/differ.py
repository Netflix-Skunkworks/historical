"""
.. module: historical.security_group.differ
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import logging
from boto3.dynamodb.types import TypeDeserializer
from deepdiff import DeepDiff

from raven_python_lambda import RavenLambdaWrapper

from historical.security_group.models import DurableSecurityGroupModel

deser = TypeDeserializer()

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(logging.INFO)


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical security group event differ.

    Listens to the Historical current table and determines if there are differences that need to be persisted in the
    historical record.
    """
    ephemeral_paths = {}

    for record in event['Records']:
        log.info('Processing stream record...')
        arn = record['dynamodb']['Keys']['arn']['S']

        if record['eventName'] in ['INSERT', 'MODIFY']:
            new = record['dynamodb']['NewImage']
            data = {}
            for item in new:
                data[item] = deser.deserialize(new[item])

            if record['eventName'] == 'INSERT':
                DurableSecurityGroupModel(data).save()
                log.debug('Saving new revision to durable table.')

            elif record['eventName'] == 'MODIFY':
                latest_revision = DurableSecurityGroupModel.query(arn)

                # determine if there is truly a difference, disregarding ephemeral_paths
                if DeepDiff(data, latest_revision, exclude_paths=ephemeral_paths):
                    DurableSecurityGroupModel(data).update()
                    log.debug('Difference found saving new revision to durable table.')

        if record['eventName'] == 'REMOVE':
            DurableSecurityGroupModel(record['dynamodb']['Keys']['arn']['S'], {}).update()
            log.debug('Marking revision as deleted.')
