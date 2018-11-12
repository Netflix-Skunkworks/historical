"""
.. module: historical.s3.collector
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import logging
from itertools import groupby

from botocore.exceptions import ClientError
from pynamodb.exceptions import PynamoDBConnectionError
from raven_python_lambda import RavenLambdaWrapper
from cloudaux.orchestration.aws.s3 import get_bucket

from historical.common.sqs import group_records_by_type
from historical.constants import CURRENT_REGION, HISTORICAL_ROLE, LOGGING_LEVEL
from historical.common import cloudwatch
from historical.common.util import deserialize_records
from historical.s3.models import CurrentS3Model, VERSION

logging.basicConfig()
LOG = logging.getLogger('historical')
LOG.setLevel(LOGGING_LEVEL)


UPDATE_EVENTS = [
    'PollS3',   # Polling event
    'DeleteBucketCors',
    'DeleteBucketLifecycle',
    'DeleteBucketPolicy',
    'DeleteBucketReplication',
    'DeleteBucketTagging',
    'DeleteBucketWebsite',
    'CreateBucket',
    'PutBucketAcl',
    'PutBucketCors',
    'PutBucketLifecycle',
    'PutBucketPolicy',
    'PutBucketLogging',
    'PutBucketNotification',
    'PutBucketReplication',
    'PutBucketTagging',
    'PutBucketRequestPayment',
    'PutBucketVersioning',
    'PutBucketWebsite'
]


DELETE_EVENTS = [
    'DeleteBucket',
]


def create_delete_model(record):
    """Create an S3 model from a record."""
    arn = f"arn:aws:s3:::{cloudwatch.filter_request_parameters('bucketName', record)}"
    LOG.debug(f'[-] Deleting Dynamodb Records. Hash Key: {arn}')

    data = {
        'arn': arn,
        'principalId': cloudwatch.get_principal(record),
        'userIdentity': cloudwatch.get_user_identity(record),
        'accountId': record['account'],
        'eventTime': record['detail']['eventTime'],
        'BucketName': cloudwatch.filter_request_parameters('bucketName', record),
        'Region': cloudwatch.get_region(record),
        'Tags': {},
        'configuration': {},
        'eventSource': record['detail']['eventSource'],
        'version': VERSION
    }

    return CurrentS3Model(**data)


def process_delete_records(delete_records):
    """Process the requests for S3 bucket deletions"""
    for rec in delete_records:
        arn = f"arn:aws:s3:::{rec['detail']['requestParameters']['bucketName']}"

        # Need to check if the event is NEWER than the previous event in case
        # events are out of order. This could *possibly* happen if something
        # was deleted, and then quickly re-created. It could be *possible* for the
        # deletion event to arrive after the creation event. Thus, this will check
        # if the current event timestamp is newer and will only delete if the deletion
        # event is newer.
        try:
            LOG.debug(f'[-] Deleting bucket: {arn}')
            model = create_delete_model(rec)
            model.save(condition=(CurrentS3Model.eventTime <= rec['detail']['eventTime']))
            model.delete()

        except PynamoDBConnectionError as pdce:
            LOG.warning(f"[?] Unable to delete bucket: {arn}. Either it doesn't exist, or this deletion event is stale "
                        f"(arrived before a NEWER creation/update). The specific exception is: {pdce}")


def process_update_records(update_records):
    """Process the requests for S3 bucket update requests"""
    events = sorted(update_records, key=lambda x: x['account'])

    # Group records by account for more efficient processing
    for account_id, events in groupby(events, lambda x: x['account']):
        events = list(events)

        # Grab the bucket names (de-dupe events):
        buckets = {}
        for event in events:
            # If the creation date is present, then use it:
            bucket_event = buckets.get(event['detail']['requestParameters']['bucketName'], {
                'creationDate': event['detail']['requestParameters'].get('creationDate')
            })
            bucket_event.update(event['detail']['requestParameters'])

            buckets[event['detail']['requestParameters']['bucketName']] = bucket_event
            buckets[event['detail']['requestParameters']['bucketName']]['eventDetails'] = event

        # Query AWS for current configuration
        for b_name, item in buckets.items():
            LOG.debug(f'[~] Processing Create/Update for: {b_name}')
            # If the bucket does not exist, then simply drop the request --
            # If this happens, there is likely a Delete event that has occurred and will be processed soon.
            try:
                bucket_details = get_bucket(b_name,
                                            account_number=account_id,
                                            include_created=(item.get('creationDate') is None),
                                            assume_role=HISTORICAL_ROLE,
                                            region=CURRENT_REGION)
                if bucket_details.get('Error'):
                    LOG.error(f"[X] Unable to fetch details about bucket: {b_name}. "
                              f"The error details are: {bucket_details['Error']}")
                    continue

            except ClientError as cerr:
                if cerr.response['Error']['Code'] == 'NoSuchBucket':
                    LOG.warning(f'[?] Received update request for bucket: {b_name} that does not '
                                'currently exist. Skipping.')
                    continue

                # Catch Access Denied exceptions as well:
                if cerr.response['Error']['Code'] == 'AccessDenied':
                    LOG.error(f'[X] Unable to fetch details for S3 Bucket: {b_name} in {account_id}. Access is Denied. '
                              'Skipping...')
                    continue
                raise Exception(cerr)

            # Pull out the fields we want:
            data = {
                'arn': f'arn:aws:s3:::{b_name}',
                'principalId': cloudwatch.get_principal(item['eventDetails']),
                'userIdentity': cloudwatch.get_user_identity(item['eventDetails']),
                'userAgent': item['eventDetails']['detail'].get('userAgent'),
                'sourceIpAddress': item['eventDetails']['detail'].get('sourceIPAddress'),
                'requestParameters': item['eventDetails']['detail'].get('requestParameters'),
                'accountId': account_id,
                'eventTime': item['eventDetails']['detail']['eventTime'],
                'BucketName': b_name,
                'Region': bucket_details.pop('Region'),
                # Duplicated in top level and configuration for secondary index
                'Tags': bucket_details.pop('Tags', {}) or {},
                'eventSource': item['eventDetails']['detail']['eventSource'],
                'eventName': item['eventDetails']['detail']['eventName'],
                'version': VERSION
            }

            # Remove the fields we don't care about:
            del bucket_details['Arn']
            del bucket_details['GrantReferences']
            del bucket_details['_version']
            del bucket_details['Name']

            if not bucket_details.get('CreationDate'):
                bucket_details['CreationDate'] = item['creationDate']

            data['configuration'] = bucket_details

            current_revision = CurrentS3Model(**data)
            current_revision.save()


@RavenLambdaWrapper()
def handler(event, context):  # pylint: disable=W0613
    """
    Historical S3 event collector.

    This collector is responsible for processing CloudWatch events and polling events.
    """
    records = deserialize_records(event['Records'])

    # Split records into two groups, update and delete.
    # We don't want to query for deleted records.
    update_records, delete_records = group_records_by_type(records, UPDATE_EVENTS)

    LOG.debug('[@] Processing update records...')
    process_update_records(update_records)
    LOG.debug('[@] Completed processing of update records.')

    LOG.debug('[@] Processing delete records...')
    process_delete_records(delete_records)
    LOG.debug('[@] Completed processing of delete records.')

    LOG.debug('[@] Successfully updated current Historical table')
