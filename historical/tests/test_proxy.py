"""
.. module: historical.tests.test_proxy
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import json
import math
import os
import sys
import time
from datetime import datetime

import boto3
import pytest
from mock import MagicMock

from historical.constants import EVENT_TOO_BIG_FLAG
from historical.models import TTL_EXPIRY
from historical.s3.models import VERSION, DurableS3Model
from historical.tests.factories import DynamoDBRecordFactory, DynamoDBDataFactory, DynamoDBRecordsFactory, serialize, \
    CloudwatchEventFactory, DetailFactory, RecordsFactory, SQSDataFactory, SnsDataFactory

S3_BUCKET = {
    "arn": "arn:aws:s3:::testbucket1",
    "principalId": "joe@example.com",
    "userIdentity": {
        "sessionContext": {
            "userName": "oUEKDvMsBwpk",
            "type": "Role",
            "arn": "arn:aws:iam::123456789012:role/historical_poller",
            "principalId": "AROAIKELBS2RNWG7KASDF",
            "accountId": "123456789012"
        },
        "principalId": "AROAIKELBS2RNWG7KASDF:joe@example.com"
    },
    "accountId": "123456789012",
    "eventTime": "2017-09-08T00:34:34Z",
    "eventSource": "aws.s3",
    "BucketName": "testbucket1",
    'version': VERSION,
    "Region": "us-east-1",
    "Tags": {},
    "configuration": {
        "Grants": {
            "75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a": [
                "FULL_CONTROL"
            ]
        },
        "Owner": {
            "ID": "75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a"
        },
        "LifecycleRules": [
            {
                "Status": "Enabled",
                "Prefix": '',
                "Expiration": {
                    "Days": 7
                },
                "ID": "Some cleanup"
            }
        ],
        "Logging": {},
        "Policy": None,
        "Versioning": {},
        "Website": None,
        "Cors": [],
        "Notifications": {},
        "Acceleration": None,
        "Replication": {},
        "CreationDate": "2006-02-03T16:45:09Z",
        "AnalyticsConfigurations": [],
        "MetricsConfigurations": []
    }
}


def test_make_blob():
    from historical.common.proxy import shrink_blob

    ttl = int(time.time() + TTL_EXPIRY)
    new_bucket = S3_BUCKET.copy()
    new_bucket['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    new_bucket["ttl"] = ttl
    ddb_record = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=new_bucket,
            Keys={
                'arn': new_bucket['arn']
            },
            OldImage=new_bucket),
        eventName='INSERT')
    new_item = DynamoDBRecordsFactory(records=[ddb_record])
    data = json.loads(json.dumps(new_item, default=serialize))['Records'][0]

    shrunken_blob = shrink_blob(data, False)

    assert shrunken_blob['userIdentity'] == data['userIdentity']
    assert shrunken_blob[EVENT_TOO_BIG_FLAG]
    assert shrunken_blob['eventName'] == data['eventName']
    assert shrunken_blob['dynamodb']['Keys'] == data['dynamodb']['Keys']

    assert not shrunken_blob['dynamodb']['NewImage'].get('configuration')
    assert not shrunken_blob['dynamodb']['OldImage'].get('configuration')


def test_detect_global_table_updates():
    from historical.common.dynamodb import remove_global_dynamo_specific_fields
    from historical.common.proxy import detect_global_table_updates

    new_bucket = S3_BUCKET.copy()
    new_bucket['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'

    old_bucket = dict(new_bucket)
    new_bucket['aws:rep:deleting'] = 'something'
    new_bucket['aws:rep:updatetime'] = new_bucket['eventTime']
    new_bucket['aws:rep:updateregion'] = 'us-east-1'

    ddb_record = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=new_bucket,
            Keys={
                'arn': new_bucket['arn']
            },
            OldImage=old_bucket),
        eventName='MODIFY')
    new_item = DynamoDBRecordsFactory(records=[ddb_record])
    data = json.loads(json.dumps(new_item, default=serialize))['Records'][0]
    assert detect_global_table_updates(data)

    # If they are both equal:
    old_bucket = new_bucket
    ddb_record = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=new_bucket,
            Keys={
                'arn': new_bucket['arn']
            },
            OldImage=old_bucket),
        eventName='MODIFY')
    new_item = DynamoDBRecordsFactory(records=[ddb_record])
    data = json.loads(json.dumps(new_item, default=serialize))['Records'][0]
    assert detect_global_table_updates(data)

    # An actual tangible change:
    old_bucket = dict(new_bucket)
    old_bucket = remove_global_dynamo_specific_fields(old_bucket)
    old_bucket['Region'] = 'us-west-2'
    ddb_record = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=new_bucket,
            Keys={
                'arn': new_bucket['arn']
            },
            OldImage=old_bucket),
        eventName='MODIFY')
    new_item = DynamoDBRecordsFactory(records=[ddb_record])
    data = json.loads(json.dumps(new_item, default=serialize))['Records'][0]
    assert not detect_global_table_updates(data)


def test_make_proper_dynamodb_record():
    import historical.common.proxy

    old_publish_message = historical.common.proxy._publish_sns_message
    old_logger = historical.common.proxy.log

    mock_logger = MagicMock()
    historical.common.proxy.log = mock_logger

    from historical.common.proxy import make_proper_dynamodb_record

    # With a small item:
    ttl = int(time.time() + TTL_EXPIRY)
    new_bucket = S3_BUCKET.copy()
    new_bucket['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    new_bucket["ttl"] = ttl
    ddb_record = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=new_bucket,
            Keys={
                'arn': new_bucket['arn']
            },
            OldImage=new_bucket),
        eventName='INSERT')
    new_item = DynamoDBRecordsFactory(records=[ddb_record])
    data = json.loads(json.dumps(new_item, default=serialize))['Records'][0]

    test_blob = json.dumps(json.loads(make_proper_dynamodb_record(data)), sort_keys=True)
    assert test_blob == json.dumps(data, sort_keys=True)
    assert not json.loads(test_blob).get(EVENT_TOO_BIG_FLAG)
    assert not mock_logger.debug.called

    # With a big item...
    new_bucket['configuration'] = new_bucket['configuration'].copy()
    new_bucket['configuration']['VeryLargeConfigItem'] = 'a' * 262144
    ddb_record = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=new_bucket,
            Keys={
                'arn': new_bucket['arn']
            },
            OldImage=new_bucket),
        eventName='INSERT')
    new_item = DynamoDBRecordsFactory(records=[ddb_record])
    data = json.loads(json.dumps(new_item, default=serialize))['Records'][0]

    assert math.ceil(sys.getsizeof(json.dumps(data)) / 1024) >= 200
    test_blob = json.dumps(json.loads(make_proper_dynamodb_record(data)), sort_keys=True)
    assert test_blob != json.dumps(data, sort_keys=True)
    assert json.loads(test_blob)[EVENT_TOO_BIG_FLAG]
    assert not mock_logger.debug.called

    # For a deletion event:
    deleted_bucket = S3_BUCKET.copy()
    deleted_bucket['Tags'] = {}
    deleted_bucket['configuration'] = {}
    new_bucket['Region'] = 'us-east-1'
    ddb_deleted_item = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=deleted_bucket,
            Keys={
                'arn': deleted_bucket['arn']
            },
            OldImage=new_bucket),
        eventName='INSERT')
    deleted_item = DynamoDBRecordsFactory(records=[ddb_deleted_item])
    data = json.loads(json.dumps(deleted_item, default=serialize))['Records'][0]
    item = json.loads(make_proper_dynamodb_record(data))
    assert not item['dynamodb']['OldImage'].get('configuration')
    assert not item['dynamodb']['NewImage']['configuration']['M']

    # Unmock:
    historical.common.proxy._publish_sns_message = old_publish_message
    historical.common.proxy.log = old_logger


def test_make_proper_simple_record():
    import historical.common.proxy

    old_tech = historical.common.proxy.HISTORICAL_TECHNOLOGY
    historical.common.proxy.HISTORICAL_TECHNOLOGY = 's3'

    from historical.common.proxy import make_proper_simple_record, _get_durable_pynamo_obj

    # With a small item:
    new_bucket = S3_BUCKET.copy()
    new_bucket['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    del new_bucket['eventSource']
    ddb_record = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=new_bucket,
            Keys={
                'arn': new_bucket['arn']
            },
            OldImage=new_bucket),
        eventName='INSERT')
    new_item = DynamoDBRecordsFactory(records=[ddb_record])
    data = json.loads(json.dumps(new_item, default=serialize))['Records'][0]

    test_blob = json.loads(make_proper_simple_record(data))
    assert test_blob['arn'] == new_bucket['arn']
    assert test_blob['event_time'] == new_bucket['eventTime']
    assert test_blob['tech'] == 's3'
    assert not test_blob.get(EVENT_TOO_BIG_FLAG)
    assert json.dumps(test_blob['item'], sort_keys=True) == \
        json.dumps(dict(_get_durable_pynamo_obj(data['dynamodb']['NewImage'], DurableS3Model)), sort_keys=True)

    # With a big item...
    new_bucket['configuration'] = new_bucket['configuration'].copy()
    new_bucket['configuration']['VeryLargeConfigItem'] = 'a' * 262144
    ddb_record = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=new_bucket,
            Keys={
                'arn': new_bucket['arn']
            },
            OldImage=new_bucket),
        eventName='INSERT')
    new_item = DynamoDBRecordsFactory(records=[ddb_record])
    data = json.loads(json.dumps(new_item, default=serialize))['Records'][0]

    assert math.ceil(sys.getsizeof(json.dumps(data)) / 1024) >= 200
    test_blob = json.loads(make_proper_simple_record(data))
    assert test_blob['arn'] == new_bucket['arn']
    assert test_blob['event_time'] == new_bucket['eventTime']
    assert test_blob['tech'] == 's3'
    assert test_blob[EVENT_TOO_BIG_FLAG]
    assert not test_blob.get('item')

    # For a deletion event:
    deleted_bucket = S3_BUCKET.copy()
    del deleted_bucket['eventSource']
    deleted_bucket['Tags'] = {}
    deleted_bucket['configuration'] = {}
    new_bucket['Region'] = 'us-east-1'
    ddb_deleted_item = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=deleted_bucket,
            Keys={
                'arn': deleted_bucket['arn']
            },
            OldImage=new_bucket),
        eventName='INSERT')
    deleted_item = DynamoDBRecordsFactory(records=[ddb_deleted_item])
    data = json.loads(json.dumps(deleted_item, default=serialize))['Records'][0]
    test_blob = json.loads(make_proper_simple_record(data))
    assert test_blob['arn'] == deleted_bucket['arn']
    assert test_blob['event_time'] == deleted_bucket['eventTime']
    assert test_blob['tech'] == 's3'
    assert json.dumps(test_blob['item'], sort_keys=True) == \
        json.dumps(dict(_get_durable_pynamo_obj(data['dynamodb']['NewImage'], DurableS3Model)), sort_keys=True)

    # For a creation event:
    new_bucket = S3_BUCKET.copy()
    new_bucket['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    del new_bucket['eventSource']
    ddb_record = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=new_bucket,
            Keys={
                'arn': new_bucket['arn']
            }),
        eventName='INSERT')
    new_item = DynamoDBRecordsFactory(records=[ddb_record])
    data = json.loads(json.dumps(new_item, default=serialize))['Records'][0]

    test_blob = json.loads(make_proper_simple_record(data))
    assert test_blob['arn'] == new_bucket['arn']
    assert test_blob['event_time'] == new_bucket['eventTime']
    assert test_blob['tech'] == 's3'
    assert not test_blob.get(EVENT_TOO_BIG_FLAG)
    assert json.dumps(test_blob['item'], sort_keys=True) == \
        json.dumps(dict(_get_durable_pynamo_obj(data['dynamodb']['NewImage'], DurableS3Model)), sort_keys=True)

    # Unmock:
    historical.common.proxy.HISTORICAL_TECHNOLOGY = old_tech


def test_proxy_dynamodb_differ(historical_role, current_s3_table, durable_s3_table, mock_lambda_environment,
                               buckets):
    """This mostly checks that the differ is able to properly load the reduced dataset from the Proxy."""
    # Create the item in the current table:
    from historical.s3.collector import handler as current_handler
    from historical.s3.differ import handler as diff_handler
    from historical.s3.models import CurrentS3Model, DurableS3Model
    from historical.common.proxy import shrink_blob

    # Mock out the loggers:
    import historical.common.dynamodb
    old_logger = historical.common.dynamodb.log
    mocked_logger = MagicMock()
    historical.common.dynamodb.log = mocked_logger

    now = datetime.utcnow().replace(tzinfo=None, microsecond=0)
    create_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1"
            },
            eventSource="aws.s3",
            eventName="CreateBucket",
            eventTime=now
        )
    )
    data = json.dumps(create_event, default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=data)])
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    current_handler(data, mock_lambda_environment)
    result = list(CurrentS3Model.query("arn:aws:s3:::testbucket1"))
    assert len(result) == 1

    # Mock out the DDB Stream for this creation and for an item that is NOT in the current table::
    ttl = int(time.time() + TTL_EXPIRY)
    new_bucket = S3_BUCKET.copy()
    new_bucket['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    new_bucket['ttl'] = ttl
    ddb_existing_item = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=new_bucket,
            Keys={
                'arn': new_bucket['arn']
            },
            OldImage=new_bucket),
        eventName='INSERT')

    missing_bucket = S3_BUCKET.copy()
    missing_bucket['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    missing_bucket['ttl'] = ttl
    missing_bucket['BucketName'] = 'notinthecurrenttable'
    missing_bucket['arn'] = 'arn:aws:s3:::notinthecurrenttable'
    ddb_missing_item = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=missing_bucket,
            Keys={
                'arn': 'arn:aws:s3:::notinthecurrenttable'
            },
            OldImage=new_bucket),
        eventName='INSERT')

    # Get the shrunken blob:
    shrunken_existing = json.dumps(shrink_blob(json.loads(json.dumps(ddb_existing_item, default=serialize)), False))
    shrunken_missing = json.dumps(shrink_blob(json.loads(json.dumps(ddb_missing_item, default=serialize)), False))

    # Also try one without the SNS data factory -- it should still work properly on de-serialization:
    records = RecordsFactory(
        records=[SQSDataFactory(body=json.dumps(SnsDataFactory(Message=shrunken_existing), default=serialize)),
                 SQSDataFactory(body=json.dumps(shrunken_missing, default=serialize))]
    )
    records_event = json.loads(json.dumps(records, default=serialize))

    # Run the differ:
    diff_handler(records_event, mock_lambda_environment)

    # Verify that the existing bucket in the Current table is in the Durable table with the correct configuration:
    result = list(DurableS3Model.query("arn:aws:s3:::testbucket1"))
    assert len(result) == 1
    assert result[0].BucketName == 'testbucket1'

    # Verify that the missing bucket is ignored -- as it will be processed presumably later:
    result = list(DurableS3Model.query("arn:aws:s3:::notinthecurrenttable"))
    assert not result

    # Verify that the proper log statements were reached:
    assert mocked_logger.debug.called
    assert mocked_logger.error.called
    debug_calls = [
        '[-->] Item with ARN: arn:aws:s3:::notinthecurrenttable was too big for SNS '
        '-- fetching it from the Current table...',
        '[+] Saving new revision to durable table.',
        '[-->] Item with ARN: arn:aws:s3:::testbucket1 was too big for SNS -- fetching it from the Current table...'
    ]
    for dc in debug_calls:
        mocked_logger.debug.assert_any_call(dc)

    mocked_logger.error.assert_called_once_with('[?] Received item too big for SNS, and was not able to '
                                                'find the original item with ARN: arn:aws:s3:::notinthecurrenttable')

    # Now, let's test if we are dealing with a deletion event: (this is also an out of order event)
    deleted_bucket = S3_BUCKET.copy()
    deleted_bucket['Tags'] = {}
    deleted_bucket['configuration'] = {}
    ddb_deleted_item = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=deleted_bucket,
            Keys={
                'arn': deleted_bucket['arn']
            },
            OldImage=new_bucket),
        eventName='INSERT')

    # Get the proper shrunken record:
    shrunken_deletion = json.dumps(shrink_blob(json.loads(json.dumps(ddb_deleted_item, default=serialize)), True))
    records = RecordsFactory(
        records=[SQSDataFactory(body=json.dumps(SnsDataFactory(Message=shrunken_deletion), default=serialize))]
    )
    records_event = json.loads(json.dumps(records, default=serialize))

    # Run the differ:
    diff_handler(records_event, mock_lambda_environment)

    # Verify that the existing bucket now has a deletion record:
    result = list(DurableS3Model.query(deleted_bucket['arn'], scan_index_forward=False))
    assert len(result) == 2
    assert result[0].configuration.attribute_values
    assert not result[1].configuration.attribute_values

    # Unmock the logger:
    historical.common.dynamodb.log = old_logger


def test_proxy_lambda(historical_role, historical_sqs, mock_lambda_environment):
    import historical.common.proxy
    from historical.constants import CURRENT_REGION
    from historical.common.exceptions import MissingProxyConfigurationException
    from historical.common.proxy import handler
    from historical.common.util import deserialize_records

    ttl = int(time.time() + TTL_EXPIRY)
    new_bucket = S3_BUCKET.copy()
    new_bucket['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    new_bucket["ttl"] = ttl
    ddb_record = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=new_bucket,
            Keys={
                'arn': new_bucket['arn']
            },
            OldImage=new_bucket),
        eventName='INSERT')
    new_item = DynamoDBRecordsFactory(records=[ddb_record])
    data = json.loads(json.dumps(new_item, default=serialize))

    # First check for failure if none of the environment variables are set:
    with pytest.raises(MissingProxyConfigurationException):
        handler(data, mock_lambda_environment)

    # Send messages with SQS:
    os.environ['PROXY_QUEUE_URL'] = 'proxyqueue'
    handler(data, mock_lambda_environment)

    # Verify that we got our message:
    sqs = boto3.client('sqs', region_name=CURRENT_REGION)
    messages = sqs.receive_message(QueueUrl='proxyqueue', MaxNumberOfMessages=10)['Messages']

    assert len(messages) == 1
    # 'Body' is lowercase:
    messages[0]['body'] = messages[0]['Body']
    records = deserialize_records(messages)
    assert records[0]['dynamodb']['Keys']['arn']['S'] == new_bucket['arn']
    sqs.delete_message(QueueUrl='proxyqueue', ReceiptHandle=messages[0]['ReceiptHandle'])

    # Nothing should be sent out if this was a DDB global table change event:
    ddb_change = json.loads(json.dumps(new_bucket))
    ddb_change['aws:rep:deleting'] = 'something'
    ddb_change['aws:rep:updatetime'] = new_bucket['eventTime']
    ddb_change['aws:rep:updateregion'] = 'us-east-1'
    ddb_change_record = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=ddb_change,
            Keys={
                'arn': new_bucket['arn']
            },
            OldImage=new_bucket),
        eventName='MODIFY')
    ddb_change_item = DynamoDBRecordsFactory(records=[ddb_change_record])
    ddb_change_data = json.loads(json.dumps(ddb_change_item, default=serialize))
    handler(ddb_change_data, mock_lambda_environment)
    assert not sqs.receive_message(QueueUrl='proxyqueue', MaxNumberOfMessages=10).get('Messages')

    # Nothing should be sent out if the region is different:
    import historical.common.proxy
    historical.common.proxy.PROXY_REGIONS = ['eu-west-1']
    handler(data, mock_lambda_environment)
    messages = sqs.receive_message(QueueUrl='proxyqueue', MaxNumberOfMessages=10)
    assert not messages.get('Messages')
    historical.common.proxy.PROXY_REGIONS = ['us-east-1']

    # Send messages with SNS (need to mock out SNS since it's hard to mock it)
    mock_func = MagicMock()
    old_publish = historical.common.proxy._publish_sns_message
    historical.common.proxy._publish_sns_message = mock_func
    del os.environ['PROXY_QUEUE_URL']

    os.environ['PROXY_TOPIC_ARN'] = 'thetopic'
    handler(data, mock_lambda_environment)
    assert mock_func.called

    # Clean-up:
    historical.common.proxy._publish_sns_message = old_publish
    del os.environ['PROXY_TOPIC_ARN']
