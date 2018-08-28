"""
.. module: historical.tests.test_s3
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import json

import boto3
import os
import time

from datetime import datetime

from botocore.exceptions import ClientError

from historical.common.sqs import get_queue_url
from historical.models import HistoricalPollerTaskEventModel
from historical.s3.models import s3_polling_schema, CurrentS3Model
from historical.tests.factories import (
    CloudwatchEventFactory,
    DetailFactory,
    RecordsFactory,
    serialize,
    SQSDataFactory,
    DynamoDBDataFactory,
    DynamoDBRecordFactory,
    UserIdentityFactory,
    SnsDataFactory)

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
    'schema_version': 9,
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
    }
}


def test_buckets_fixture(buckets):
    client = boto3.client("s3")
    results = client.list_buckets()
    assert len(results["Buckets"]) == 50


def test_schema_serialization():
    # Make an object to serialize:
    regular_now = datetime.utcnow()
    now_string = regular_now.replace(tzinfo=None, microsecond=0).isoformat() + "Z"

    bucket_details = {
        "Name": "muhbucket",
        "CreationDate": regular_now,
    }

    serialized = s3_polling_schema.serialize_me("012345678910", bucket_details)

    # The dumped data:
    loaded_serialized = json.loads(serialized)

    # The dumped data loaded again:
    loaded_data = s3_polling_schema.loads(serialized).data

    assert loaded_serialized["version"] == loaded_data["version"] == "1"
    assert loaded_serialized["detail-type"] == loaded_data["detail_type"] == "Historical Polling Event"
    assert loaded_serialized["source"] == loaded_data["source"] == "historical"
    assert loaded_serialized["account"] == loaded_data["account"] == "012345678910"

    # Not checking if other times are equal to now, since it's possible they could be off
    # the exception is bucket creation date.
    assert loaded_serialized["detail"]["eventTime"] == loaded_data["detail"]["event_time"]
    assert loaded_serialized["detail"]["eventSource"] == loaded_data["detail"]["event_source"] == "historical.s3.poller"
    assert loaded_serialized["detail"]["eventName"] == loaded_data["detail"]["event_name"] == "DescribeBucket"
    assert loaded_serialized["detail"]["requestParameters"]["bucketName"] == \
        loaded_data["detail"]["request_parameters"]["bucket_name"] == "muhbucket"
    assert loaded_serialized["detail"]["requestParameters"]["creationDate"] == \
        loaded_data["detail"]["request_parameters"]["creation_date"] == now_string


def test_current_table(current_s3_table):
    from historical.s3.models import CurrentS3Model

    CurrentS3Model(**S3_BUCKET).save()

    items = list(CurrentS3Model.query('arn:aws:s3:::testbucket1'))

    assert len(items) == 1
    assert isinstance(items[0].ttl, int)
    assert items[0].ttl > 0


def test_durable_table(durable_s3_table):
    from historical.s3.models import DurableS3Model

    # We are explicit about our eventTimes because as RANGE_KEY it will need to be unique.
    S3_BUCKET['eventTime'] = datetime(2017, 5, 11, 23, 30)
    S3_BUCKET.pop("eventSource")
    DurableS3Model(**S3_BUCKET).save()
    items = list(DurableS3Model.query('arn:aws:s3:::testbucket1'))
    assert len(items) == 1
    assert not getattr(items[0], "ttl", None)

    S3_BUCKET['eventTime'] = datetime(2017, 5, 12, 23, 30)
    DurableS3Model(**S3_BUCKET).save()
    items = list(DurableS3Model.query('arn:aws:s3:::testbucket1'))
    assert len(items) == 2


def make_poller_events():
    """A sort-of fixture to make polling events for tests."""
    from historical.s3.poller import poller_tasker_handler as handler
    handler({}, None)

    # Need to ensure that all of the accounts and regions were properly tasked (only 1 region for S3):
    sqs = boto3.client("sqs", region_name="us-east-1")
    queue_url = get_queue_url(os.environ['POLLER_TASKER_QUEUE_NAME'])
    messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10)['Messages']

    # 'Body' needs to be made into 'body' for proper parsing later:
    for m in messages:
        m['body'] = m.pop('Body')

    return messages


def test_poller_tasker_handler(mock_lambda_environment, historical_sqs, swag_accounts):
    from historical.common.accounts import get_historical_accounts
    from historical.constants import CURRENT_REGION

    messages = make_poller_events()
    all_historical_accounts = get_historical_accounts()
    assert len(messages) == len(all_historical_accounts) == 1

    poller_events = HistoricalPollerTaskEventModel().loads(messages[0]['body']).data
    assert poller_events['account_id'] == all_historical_accounts[0]['id']
    assert poller_events['region'] == CURRENT_REGION


def test_poller_processor_handler(historical_role, buckets, mock_lambda_environment, historical_sqs, swag_accounts):
    from historical.s3.poller import poller_processor_handler as handler

    # Create the events and SQS records:
    messages = make_poller_events()
    event = json.loads(json.dumps(RecordsFactory(records=messages), default=serialize))

    # Run the collector:
    handler(event, None)

    # Need to ensure that 51 total buckets were added into SQS:
    sqs = boto3.client("sqs", region_name="us-east-1")
    queue_url = get_queue_url(os.environ['POLLER_QUEUE_NAME'])

    all_buckets = {"SWAG": True}
    for i in range(0, 50):
        all_buckets["testbucket{}".format(i)] = True

    # Loop through the queue and make sure all buckets are accounted for:
    for i in range(0, 6):
        messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10)['Messages']
        message_ids = []

        for m in messages:
            message_ids.append({"Id": m['MessageId'], "ReceiptHandle": m['ReceiptHandle']})
            data = s3_polling_schema.loads(m['Body']).data

            assert all_buckets[data["detail"]["request_parameters"]["bucket_name"]]
            assert datetime.strptime(data["detail"]["request_parameters"]["creation_date"], '%Y-%m-%dT%H:%M:%SZ')
            assert data["detail"]["event_source"] == "historical.s3.poller"

            # Remove from the dict (at the end, there should be 0 items left)
            del all_buckets[data["detail"]["request_parameters"]["bucket_name"]]

        sqs.delete_message_batch(QueueUrl=queue_url, Entries=message_ids)

    assert len(all_buckets) == 0

    # Check that an exception raised doesn't break things:
    import historical.s3.poller

    def mocked_poller(account, stream, randomize_delay=0):
        raise ClientError({"Error": {"Message": "", "Code": "AccessDenied"}}, "sts:AssumeRole")

    old_method = historical.s3.poller.produce_events  # For pytest inter-test issues...
    historical.s3.poller.produce_events = mocked_poller
    handler(event, None)
    historical.s3.poller.produce_events = old_method
    # ^^ No exception = pass


def test_collector(historical_role, buckets, mock_lambda_environment, swag_accounts, current_s3_table):
    from historical.s3.collector import handler

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

    handler(data, mock_lambda_environment)
    result = list(CurrentS3Model.query("arn:aws:s3:::testbucket1"))
    assert len(result) == 1
    assert result[0].Tags.attribute_values["theBucketName"] == "testbucket1"
    assert result[0].eventSource == "aws.s3"

    # Polling (make sure the date is included):
    polling_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1",
                "creationDate": now
            },
            eventSource="historical.s3.poller",
            eventName="DescribeBucket",
            eventTime=now
        )
    )
    data = json.dumps(polling_event, default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=data)])
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, mock_lambda_environment)
    assert CurrentS3Model.count() == 1

    # Load the config and verify the polling timestamp is in there:
    result = list(CurrentS3Model.query("arn:aws:s3:::testbucket1"))
    assert result[0].configuration["CreationDate"] == now.isoformat() + "Z"
    assert result[0].eventSource == "historical.s3.poller"

    # And deletion:
    delete_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1"
            },
            eventSource="aws.s3",
            eventName="DeleteBucket",
            eventTime=now
        )
    )
    data = json.dumps(delete_event, default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=data)])
    data = json.dumps(data, default=serialize)
    data = json.loads(data)
    handler(data, mock_lambda_environment)
    assert CurrentS3Model.count() == 0


def test_collector_on_deleted_bucket(historical_role, buckets, mock_lambda_environment, swag_accounts,
                                     current_s3_table):
    from historical.s3.collector import handler

    # If an event arrives on a bucket that is deleted, then it should skip
    # and wait until the Deletion event arrives.
    create_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "not-a-bucket"
            },
            eventSource="aws.s3",
            eventName="PutBucketPolicy",
        )
    )
    create_event_data = json.dumps(create_event, default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=create_event_data)])
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, mock_lambda_environment)
    assert CurrentS3Model.count() == 0


def test_differ(current_s3_table, durable_s3_table, mock_lambda_environment):
    from historical.s3.models import DurableS3Model
    from historical.s3.differ import handler
    from historical.models import TTL_EXPIRY

    ttl = int(time.time() + TTL_EXPIRY)
    new_bucket = S3_BUCKET.copy()
    new_bucket['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    new_bucket["ttl"] = ttl
    ddb_record = json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        NewImage=new_bucket, Keys={
            'arn': new_bucket['arn']
        }),
        eventName='INSERT'), default=serialize)

    new_item = RecordsFactory(records=[SQSDataFactory(body=json.dumps(ddb_record, default=serialize))])
    data = json.loads(json.dumps(new_item, default=serialize))
    handler(data, mock_lambda_environment)
    assert DurableS3Model.count() == 1

    # Test duplicates don't change anything:
    data = json.loads(json.dumps(new_item, default=serialize))
    handler(data, mock_lambda_environment)
    assert DurableS3Model.count() == 1

    # Test ephemeral changes don't add new models:
    import historical.s3.differ
    old_ep = historical.s3.differ.EPHEMERAL_PATHS
    historical.s3.differ.EPHEMERAL_PATHS = ["root['schema_version']"]

    ephemeral_changes = S3_BUCKET.copy()
    ephemeral_changes["eventTime"] = \
        datetime(year=2017, month=5, day=12, hour=11, minute=30, second=0).isoformat() + 'Z'
    ephemeral_changes["schema_version"] = 99999
    ephemeral_changes["ttl"] = ttl

    data = json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        NewImage=ephemeral_changes, Keys={
            'arn': ephemeral_changes['arn']
        }
    ), eventName='MODIFY'), default=serialize)

    data = RecordsFactory(records=[SQSDataFactory(body=json.dumps(data, default=serialize))])
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, mock_lambda_environment)
    assert DurableS3Model.count() == 1

    # Add an update:
    new_changes = S3_BUCKET.copy()
    new_date = datetime(year=2017, month=5, day=12, hour=11, minute=30, second=0).isoformat() + 'Z'
    new_changes["eventTime"] = new_date
    new_changes["Tags"] = {"ANew": "Tag"}
    new_changes["configuration"]["Tags"] = {"ANew": "Tag"}
    new_changes["ttl"] = ttl
    data = json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        NewImage=new_changes, Keys={
            'arn': new_changes['arn']
        }
    ), eventName='MODIFY'), default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=json.dumps(data, default=serialize))])
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, mock_lambda_environment)
    results = list(DurableS3Model.query("arn:aws:s3:::testbucket1"))
    assert len(results) == 2
    assert results[1].Tags["ANew"] == results[1].configuration.attribute_values["Tags"]["ANew"] == "Tag"
    assert results[1].eventTime == new_date

    # And deletion (ensure new record -- testing TTL): -- And with SNS for testing completion
    delete_bucket = S3_BUCKET.copy()
    delete_bucket["eventTime"] = datetime(year=2017, month=5, day=12, hour=12, minute=30, second=0).isoformat() + 'Z'
    delete_bucket["ttl"] = ttl
    data = json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        OldImage=delete_bucket, Keys={
            'arn': delete_bucket['arn']
        }
    ),
        eventName='REMOVE',
        userIdentity=UserIdentityFactory(
            type='Service',
            principalId='dynamodb.amazonaws.com'
        )), default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=json.dumps(SnsDataFactory(Message=data), default=serialize))])
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, mock_lambda_environment)
    assert DurableS3Model.count() == 3

    historical.s3.differ.EPHEMERAL_PATHS = old_ep
