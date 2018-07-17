"""
.. module: historical.tests.test_snsproxy
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import json
import math
import sys
import time
from datetime import datetime

from mock import MagicMock

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


def test_make_sns_blob():
    from historical.common.sns import shrink_sns_blob

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

    shrunken_blob = shrink_sns_blob(data)

    assert shrunken_blob['userIdentity'] == data['userIdentity']
    assert shrunken_blob['sns_too_big']
    assert shrunken_blob['eventName'] == data['eventName']
    assert shrunken_blob['dynamodb']['Keys'] == data['dynamodb']['Keys']

    assert not shrunken_blob['dynamodb']['NewImage'].get('configuration')
    assert not shrunken_blob['dynamodb']['OldImage'].get('configuration')


def test_process_sns_forward():
    import historical.common.sns

    test_blob = {'value': None}
    old_publish_message = historical.common.sns._publish_message
    old_logger = historical.common.sns.log

    def mock_publish_message(client, blob, topic_arn):
        assert math.ceil(sys.getsizeof(blob) / 1024) < 256

        # Sort the JSON for easier comparisons later...
        test_blob['value'] = json.dumps(json.loads(blob), sort_keys=True)

    historical.common.sns._publish_message = mock_publish_message

    mock_logger = MagicMock()
    historical.common.sns.log = mock_logger

    from historical.common.sns import process_sns_forward

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
    process_sns_forward(data, "sometopic", None)
    assert test_blob['value'] == json.dumps(data, sort_keys=True)
    assert not json.loads(test_blob['value']).get('sns_too_big')
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
    process_sns_forward(data, "sometopic", None)
    assert test_blob['value'] != json.dumps(data, sort_keys=True)
    assert json.loads(test_blob['value'])['sns_too_big']
    assert not mock_logger.debug.called

    # With a region that is not in the SNSPROXY_REGIONS var:
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
    process_sns_forward(data, "sometopic", None)
    assert mock_logger.debug.called

    # Unmock:
    historical.common.sns._publish_message = old_publish_message
    historical.common.sns.log = old_logger


def test_snsproxy_dynamodb_differ(historical_role, current_s3_table, durable_s3_table, mock_lambda_environment,
                                  buckets):
    """
    This mostly checks that the differ is able to properly load the reduced dataset from the SNSProxy.
    """
    # Create the item in the current table:
    from historical.s3.collector import handler as current_handler
    from historical.s3.differ import handler as diff_handler
    from historical.s3.models import CurrentS3Model, DurableS3Model
    from historical.common.sns import shrink_sns_blob

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
    shrunken_existing = json.dumps(shrink_sns_blob(json.loads(json.dumps(ddb_existing_item, default=serialize))))
    shrunken_missing = json.dumps(shrink_sns_blob(json.loads(json.dumps(ddb_missing_item, default=serialize))))

    records = RecordsFactory(
        records=[SQSDataFactory(body=json.dumps(SnsDataFactory(Message=shrunken_existing), default=serialize)),
                 SQSDataFactory(body=json.dumps(SnsDataFactory(Message=shrunken_missing), default=serialize))]
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
