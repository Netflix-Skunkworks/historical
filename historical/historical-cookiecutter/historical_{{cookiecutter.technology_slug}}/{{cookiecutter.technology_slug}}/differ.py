"""
.. module: {{cookiecutter.technology_slug}}.differ
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: {{cookiecutter.author}} <{{cookiecutter.email}}>
"""
import logging

from raven_python_lambda import RavenLambdaWrapper

from historical.common.dynamodb import process_dynamodb_differ_record
from .models import Durable{{cookiecutter.technology_slug | titlecase}}Model

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(logging.WARNING)


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical security group event differ.

    Listens to the Historical current table and determines if there are differences that need to be persisted in the
    historical record.
    """
    for record in event['Records']:
        process_dynamodb_differ_record(record, Durable{{cookiecutter.technology_slug | titlecase}}Model)
