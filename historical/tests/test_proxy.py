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
                "Prefix": None,
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
        "MetricsConfigurations": [],
        "InventoryConfigurations": [],
        "Name": "testbucket1",
        "_version": 8
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

    shrunken_blob = shrink_blob(data)

    assert shrunken_blob['userIdentity'] == data['userIdentity']
    assert shrunken_blob[EVENT_TOO_BIG_FLAG]
    assert shrunken_blob['eventName'] == data['eventName']
    assert shrunken_blob['dynamodb']['Keys'] == data['dynamodb']['Keys']

    assert not shrunken_blob['dynamodb']['NewImage'].get('configuration')
    assert not shrunken_blob['dynamodb']['OldImage'].get('configuration')


def test_make_proper_record():
    import historical.common.proxy

    old_publish_message = historical.common.proxy._publish_sns_message
    old_logger = historical.common.proxy.log

    mock_logger = MagicMock()
    historical.common.proxy.log = mock_logger

    from historical.common.proxy import make_proper_record

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

    # Nothing changed -- should be exactly the same:
    test_blob = json.dumps(json.loads(make_proper_record(data)), sort_keys=True)
    assert test_blob == json.dumps(data, sort_keys=True)
    assert not json.loads(test_blob).get(EVENT_TOO_BIG_FLAG)
    assert not mock_logger.debug.called

    # With a big item...
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

    assert math.ceil(sys.getsizeof(json.dumps(data)) / 1024) >= 256
    test_blob = json.dumps(json.loads(make_proper_record(data)), sort_keys=True)
    assert test_blob != json.dumps(data, sort_keys=True)
    assert json.loads(test_blob)[EVENT_TOO_BIG_FLAG]
    assert not mock_logger.debug.called

    # With a region that is not in the PROXY_REGIONS var:
    new_bucket['Region'] = "us-west-2"
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
    make_proper_record(data)
    assert mock_logger.debug.called

    # Unmock:
    historical.common.proxy._publish_sns_message = old_publish_message
    historical.common.proxy.log = old_logger


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
    missing_bucket['configuration']['Name'] = 'notinthecurrenttable'
    ddb_missing_item = DynamoDBRecordFactory(
        dynamodb=DynamoDBDataFactory(
            NewImage=missing_bucket,
            Keys={
                'arn': 'arn:aws:s3:::notinthecurrenttable'
            },
            OldImage=new_bucket),
        eventName='INSERT')

    # Get the shrunken blob:
    shrunken_existing = json.dumps(shrink_blob(json.loads(json.dumps(ddb_existing_item, default=serialize))))
    shrunken_missing = json.dumps(shrink_blob(json.loads(json.dumps(ddb_missing_item, default=serialize))))

    # Also try one without the SNS data factory -- it should stil work properly on de-serialization:
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
    assert result[0].configuration.attribute_values['Name'] == 'testbucket1'

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