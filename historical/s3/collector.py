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
from historical.constants import HISTORICAL_ROLE, CURRENT_REGION, LOGGING_LEVEL
from historical.common import cloudwatch
from historical.common.util import deserialize_records
from historical.s3.models import CurrentS3Model, VERSION

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(LOGGING_LEVEL)


UPDATE_EVENTS = [
    'DescribeBucket',   # Polling event
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
    arn = 'arn:aws:s3:::{}'.format(cloudwatch.filter_request_parameters('bucketName', record))
    log.debug('[-] Deleting Dynamodb Records. Hash Key: {arn}'.format(arn=arn))

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
    for r in delete_records:
        arn = 'arn:aws:s3:::{}'.format(r['detail']['requestParameters']['bucketName'])

        # Need to check if the event is NEWER than the previous event in case
        # events are out of order. This could *possibly* happen if something
        # was deleted, and then quickly re-created. It could be *possible* for the
        # deletion event to arrive after the creation event. Thus, this will check
        # if the current event timestamp is newer and will only delete if the deletion
        # event is newer.
        try:
            log.debug('[-] Deleting bucket: {}'.format(arn))
            model = create_delete_model(r)
            model.save(condition=(CurrentS3Model.eventTime <= r['detail']['eventTime']))
            model.delete()

        except PynamoDBConnectionError as pdce:
            log.warn("[?] Unable to delete bucket: {}. Either it doesn't exist, or this deletion event is stale "
                     "(arrived before a NEWER creation/update). The specific exception is: {}".format(arn, pdce))


def process_update_records(update_records):
    """Process the requests for S3 bucket update requests"""
    events = sorted(update_records, key=lambda x: x['account'])

    # Group records by account for more efficient processing
    for account_id, events in groupby(events, lambda x: x['account']):
        events = list(events)

        # Grab the bucket names (de-dupe events):
        buckets = {}
        for e in events:
            # If the creation date is present, then use it:
            bucket_event = buckets.get(e['detail']['requestParameters']['bucketName'], {
                'creationDate': e['detail']['requestParameters'].get('creationDate')
            })
            bucket_event.update(e['detail']['requestParameters'])

            buckets[e['detail']['requestParameters']['bucketName']] = bucket_event
            buckets[e['detail']['requestParameters']['bucketName']]['eventDetails'] = e

        # Query AWS for current configuration
        for b, item in buckets.items():
            log.debug('[~] Processing Create/Update for: {}'.format(b))
            # If the bucket does not exist, then simply drop the request --
            # If this happens, there is likely a Delete event that has occurred and will be processed soon.
            try:
                bucket_details = get_bucket(b,
                                            account_number=account_id,
                                            include_created=(item.get('creationDate') is None),
                                            assume_role=HISTORICAL_ROLE,
                                            region=CURRENT_REGION)
                if bucket_details.get('Error'):
                    log.error('[X] Unable to fetch details about bucket: {}. '
                              'The error details are: {}'.format(b, bucket_details['Error']))
                    continue

            except ClientError as ce:
                if ce.response['Error']['Code'] == 'NoSuchBucket':
                    log.warning('[?] Received update request for bucket: {} that does not '
                                'currently exist. Skipping.'.format(b))
                    continue

                # Catch Access Denied exceptions as well:
                if ce.response['Error']['Code'] == 'AccessDenied':
                    log.error('[X] Unable to fetch details for S3 Bucket: {} in {}. Access is Denied. '
                              'Skipping...'.format(b, account_id))
                    continue
                raise Exception(ce)

            # Pull out the fields we want:
            data = {
                'arn': 'arn:aws:s3:::{}'.format(b),
                'principalId': cloudwatch.get_principal(item['eventDetails']),
                'userIdentity': cloudwatch.get_user_identity(item['eventDetails']),
                'accountId': account_id,
                'eventTime': item['eventDetails']['detail']['eventTime'],
                'BucketName': b,
                'Region': bucket_details.pop('Region'),
                # Duplicated in top level and configuration for secondary index
                'Tags': bucket_details.pop('Tags', {}) or {},
                'eventSource': item['eventDetails']['detail']['eventSource'],
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
def handler(event, context):
    """
    Historical S3 event collector.

    This collector is responsible for processing CloudWatch events and polling events.
    """
    records = deserialize_records(event['Records'])

    # Split records into two groups, update and delete.
    # We don't want to query for deleted records.
    update_records, delete_records = group_records_by_type(records, UPDATE_EVENTS)

    log.debug('[@] Processing update records...')
    process_update_records(update_records)
    log.debug('[@] Completed processing of update records.')

    log.debug('[@] Processing delete records...')
    process_delete_records(delete_records)
    log.debug('[@] Completed processing of delete records.')

    log.debug('[@] Successfully updated current Historical table')
