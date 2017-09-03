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

from historical.security_group.models import DurableSecurityGroupModel

deser = TypeDeserializer()

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(logging.INFO)

EPHEMERAL_PATHS = {"root['attribute_values']['eventTime']"}


def is_new_revision(latest_revision, current_revision):
    """Determine if two revisions have actually changed."""
    diff = DeepDiff(
        current_revision._serialize(),
        latest_revision._serialize(),
        exclude_paths=EPHEMERAL_PATHS,
        ignore_order=True
    )
    return diff


def handler(event, context):
    """
    Historical security group event differ.

    Listens to the Historical current table and determines if there are differences that need to be persisted in the
    historical record.
    """
    for record in event['Records']:
        log.info('Processing stream record...')
        arn = record['dynamodb']['Keys']['arn']['S']

        if record['eventName'] in ['INSERT', 'MODIFY']:
            new = record['dynamodb']['NewImage']
            data = {}
            for item in new:
                data[item] = deser.deserialize(new[item])

            current_revision = DurableSecurityGroupModel(**data)
            if record['eventName'] == 'INSERT':
                current_revision.save()
                log.debug('Saving new revision to durable table.')

            elif record['eventName'] == 'MODIFY':
                # We want the newest items first.
                # See: http://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.html
                latest_revision = list(DurableSecurityGroupModel.query(arn, scan_index_forward=False, limit=1))[0]

                # determine if there is truly a difference, disregarding ephemeral_paths
                if is_new_revision(latest_revision, current_revision):
                    current_revision.save()
                    log.debug('Difference found saving new revision to durable table.')

        if record['eventName'] == 'REMOVE':
            current_revision = DurableSecurityGroupModel(configuration={})
            current_revision.save()
            log.debug('Adding deletion marker.')
