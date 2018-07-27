"""
.. module: historical.vpc.differ
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import logging

from raven_python_lambda import RavenLambdaWrapper

from historical.common.dynamodb import process_dynamodb_differ_record
from historical.common.util import deserialize_records
from historical.constants import LOGGING_LEVEL
from historical.vpc.models import DurableVPCModel, CurrentVPCModel

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(LOGGING_LEVEL)


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical security group event differ.

    Listens to the Historical current table and determines if there are differences that need to be persisted in the
    historical record.
    """
    # De-serialize the records:
    records = deserialize_records(event['Records'])

    for record in records:
        process_dynamodb_differ_record(record, CurrentVPCModel, DurableVPCModel)
