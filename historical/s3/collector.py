"""
.. module: historical.security_group.collector
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import logging
import os

from raven_python_lambda import RavenLambdaWrapper
from cloudaux.orchestration.aws.s3 import get_bucket
from cloudaux.aws.sqs import get_queue_url, receive_message

from historical.common.cloudwatch import filter_request_parameters, get_region, get_user_identity, get_principal, \
    get_event_time, get_account_id
from historical.common.events import determine_event_type
from historical.s3.models import CurrentS3Model

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(logging.INFO)


def get_configuration_data(data):
    """Describes the current state of the object."""
    return get_bucket(**data)


def process_cloudwatch_event(event):
    """Use cloudwatch event data to describe configuration data."""
    log.debug("Processing S3 CloudWatch event...")
    bucket_name = filter_request_parameters('bucketName', event)

    data = dict(
        aws_region=get_region(event),
        user_identity=get_user_identity(event),
        principal_id=get_principal(event),
        event_time=get_event_time(event),
        bucket_name=bucket_name,
        aws_account_id=get_account_id(event)
    )

    if event.get('eventName') == 'DeleteBucket':
        data['revision'] = {}

    else:
        bucket = get_bucket(bucket_name,
                            account_number=data["aws_account_id"],
                            assume_role=os.environ["HISTORICAL_ROLE"],
                            session_name="historical-cloudwatch-S3",
                            region=data["aws_region"])

        data['revision'] = bucket

    log.debug('Successfully processed CloudWatch Event. Data: {data}'.format(data=data[0]))

    current_revision = CurrentS3Model(**data)
    current_revision.save()
    log.debug('Successfully updated current Historical table')


def process_polling_event():
    log.debug("Processing S3 Polling event...")

    # For S3, we will always grab from the restrictor -- due to the way that S3 bucket info grabbing works,
    # since it has to call a bunch of APIs to completely describe a bucket.
    log.debug('Fetching items from S3 source queue. QueueName: {}'.format(os.environ['SOURCE_QUEUE']))
    url = get_queue_url(QueueName=os.environ['SOURCE_QUEUE'])
    events = receive_message(QueueUrl=url, MaxNumberOfMessage=os.environ.get("MAX_QUEUE_FETCH", 25))
    log.debug('Items found in queue. Number of Events: {}'.format(len(events)))

    for event in events:
        event_data = {}  # Process the polling event here...
        log.debug('Successfully processed event. Data: {data}'.format(data=event_data))

        current_revision = CurrentS3Model(**event_data)
        current_revision.save()
        log.debug('Successfully updated current Historical table')

        log.debug("Removing event from SQS queue...")
        # Delete the event from the SQS queue...
        log.debug("Removed event from SQS queue.")

    log.debug("Successfully processed S3 polling event.")


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical S3 event collector.

    This collector is responsible for processing CloudWatch events and polling events.

    Polling Events:
    When a polling event is received, this function is responsible for persisting
    configuration data to the correct DynamoDB tables.

    CloudWatch Events:
    When a CloudWatch event is received, this function must first fetch configuration
    data from AWS before persisting data.
    """
    event_type = determine_event_type(event, "aws.s3")
    if event_type == 'cloudwatch':
        process_cloudwatch_event(event)
    else:
        process_polling_event()
