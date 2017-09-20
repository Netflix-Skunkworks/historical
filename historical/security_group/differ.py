"""
.. module: historical.security_group.differ
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import logging
from deepdiff import DeepDiff

from raven_python_lambda import RavenLambdaWrapper

from historical.models import EPHEMERAL_PATHS
from historical.common.dynamodb import process_dynamodb_record
from historical.security_group.models import DurableSecurityGroupModel

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(logging.WARNING)


def is_new_revision(latest_revision, current_revision):
    """Determine if two revisions have actually changed."""
    diff = DeepDiff(
        current_revision._get_json(),
        latest_revision._get_json(),
        exclude_paths=EPHEMERAL_PATHS,
        ignore_order=True
    )
    return diff


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical security group event differ.

    Listens to the Historical current table and determines if there are differences that need to be persisted in the
    historical record.
    """
    for record in event['Records']:
        process_dynamodb_record(record, DurableSecurityGroupModel, is_new_revision)
