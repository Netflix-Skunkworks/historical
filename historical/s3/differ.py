"""
.. module: historical.security_group.differ
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import json
import logging
from boto3.dynamodb.types import TypeDeserializer
from deepdiff import DeepDiff

from raven_python_lambda import RavenLambdaWrapper

from historical.s3.models import DurableS3Model

deser = TypeDeserializer()

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(logging.WARNING)

# Path to where in the dict the ephemeral field is -- starting with "root['attribute_values'][rest...of...path]..."
EPHEMERAL_PATHS = [
    # Typical paths we generally don't care about:
    "root['attribute_values']['eventTime']",
    "root['attribute_values']['principalId']",
    "root['attribute_values']['userIdentity']",
    
    # Configuration level changes are don't care about:
    "root['attribute_values']['configuration']['_version']"
]


def is_new_revision(latest_revision, current_revision):
    """Determine if two revisions have actually changed."""
    diff = DeepDiff(
        current_revision.__dict__,
        latest_revision.__dict__,
        exclude_paths=EPHEMERAL_PATHS,
        ignore_order=True
    )
    asdf = current_revision.__dict__
    quer = latest_revision.__dict__
    print(diff)
    return diff


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical S3 event differ.

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

            current_revision = DurableS3Model(**data)
            if record['eventName'] == 'INSERT':
                current_revision.save()
                log.debug('Saving new revision to durable table.')

            elif record['eventName'] == 'MODIFY':
                # We want the newest items first.
                # See: http://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.html
                items = list(DurableS3Model.query(arn, eventTime__le=data['eventTime'], scan_index_forward=False,
                                                  limit=1))
                if items:
                    latest_revision = items[0]

                    # Determine if there is truly a difference, disregarding Ephemeral Paths
                    if is_new_revision(latest_revision, current_revision):
                        current_revision.save()
                        log.debug('Difference found saving new revision to durable table.')
                else:
                    log.warning('Got modify event but no current revision found. Record: {record}'.format(record=record))

        if record['eventName'] == 'REMOVE':
            old = record['dynamodb']['OldImage']

            data = {}
            for item in old:
                data[item] = deser.deserialize(old[item])

            data["configuration"] = {}
            data["Tags"] = {}
            DurableS3Model(**data).save()
            log.debug('Adding deletion marker.')
