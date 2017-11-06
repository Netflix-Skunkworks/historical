"""
.. module: historical.s3.differ
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
from historical.common.dynamodb import process_dynamodb_record

deser = TypeDeserializer()

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(logging.WARNING)

# Path to where in the dict the ephemeral field is -- starting with "root['M'][PathInConfigDontForgetDataType]..."
EPHEMERAL_PATHS = [
    # Configuration level changes are don't care about:
    "root['M']['_version']"
]


def is_new_revision(latest_revision, current_revision):
    """Determine if two revisions have actually changed."""
    diff = DeepDiff(
        current_revision,
        latest_revision,
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
        process_dynamodb_record(record, DurableS3Model, diff_func=is_new_revision)
