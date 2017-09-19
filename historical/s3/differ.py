"""
.. module: historical.security_group.differ
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import logging
from boto3.dynamodb.types import TypeDeserializer
from deepdiff import DeepDiff

from raven_python_lambda import RavenLambdaWrapper

from historical.s3.models import DurableS3Model
from historical.common.dynamodb import replace_decimals, remove_current_specific_fields, process_dynamodb_record

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
    return diff


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical S3 event differ.

    Listens to the Historical current table and determines if there are differences that need to be persisted in the
    historical record.
    """
    for record in event['Records']:
        process_dynamodb_record(record, DurableS3Model, is_new_revision)
