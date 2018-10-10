"""
.. module: historical.security_group.differ
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import logging

from raven_python_lambda import RavenLambdaWrapper

from historical.common.dynamodb import process_dynamodb_differ_record
from historical.common.util import deserialize_records
from historical.security_group.models import CurrentSecurityGroupModel, DurableSecurityGroupModel
from historical.constants import LOGGING_LEVEL

logging.basicConfig()
LOG = logging.getLogger('historical')
LOG.setLevel(LOGGING_LEVEL)


@RavenLambdaWrapper()
def handler(event, context):  # pylint: disable=W0613
    """
    Historical security group event differ.

    Listens to the Historical current table and determines if there are differences that need to be persisted in the
    historical record.
    """
    # De-serialize the records:
    records = deserialize_records(event['Records'])

    for record in records:
        process_dynamodb_differ_record(record, CurrentSecurityGroupModel, DurableSecurityGroupModel)
