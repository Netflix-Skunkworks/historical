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

from historical.common.util import deserialize_records
from historical.constants import LOGGING_LEVEL
from historical.s3.models import DurableS3Model, CurrentS3Model
from historical.common.dynamodb import process_dynamodb_differ_record

deser = TypeDeserializer()

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(LOGGING_LEVEL)

# Path to where in the dict the ephemeral field is -- starting with "root['M'][PathInConfigDontForgetDataType]..."
EPHEMERAL_PATHS = [
    # Configuration level changes are don't care about:
    "root['configuration']['M']['_version']"
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
    # De-serialize the records:
    records = deserialize_records(event['Records'])

    for record in records:
        process_dynamodb_differ_record(record, CurrentS3Model, DurableS3Model, diff_func=is_new_revision)
