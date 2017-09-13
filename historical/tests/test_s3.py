import json

import boto3
import os

from datetime import datetime, timedelta

from botocore.exceptions import ClientError

from historical.s3.models import s3_polling_schema, CurrentS3Model
from historical.tests.factories import (
    CloudwatchEventFactory,
    DetailFactory,
    KinesisDataFactory,
    KinesisRecordFactory,
    KinesisRecordsFactory,
    serialize,
    DynamoDBDataFactory,
    DynamoDBRecordFactory,
    DynamoDBRecordsFactory
)

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
        "LifecycleRules": [],
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


def test_buckets_fixture(buckets):
    client = boto3.client("s3")
    results = client.list_buckets()
    assert len(results["Buckets"]) == 50


def test_schema_serialization():
    # Make an object to serialize:
    now = datetime.utcnow().replace(tzinfo=None, microsecond=0).isoformat() + "Z"

    bucket_details = {
        "bucket_name": "muhbucket",
        "creation_date": now,
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
           loaded_data["detail"]["request_parameters"]["creation_date"] == now


def test_current_table(current_s3_table):
    from historical.s3.models import CurrentS3Model

    CurrentS3Model(**S3_BUCKET).save()

    items = list(CurrentS3Model.query('arn:aws:s3:::testbucket1'))

    assert len(items) == 1


def test_durable_table(durable_s3_table):
    from historical.s3.models import DurableS3Model

    # We are explicit about our eventTimes because as RANGE_KEY it will need to be unique.
    S3_BUCKET['eventTime'] = datetime(2017, 5, 11, 23, 30)
    DurableS3Model(**S3_BUCKET).save()
    items = list(DurableS3Model.query('arn:aws:s3:::testbucket1'))
    assert len(items) == 1

    S3_BUCKET['eventTime'] = datetime(2017, 5, 12, 23, 30)
    DurableS3Model(**S3_BUCKET).save()
    items = list(DurableS3Model.query('arn:aws:s3:::testbucket1'))
    assert len(items) == 2


def test_poller(historical_role, buckets, mock_lambda_context, mock_lambda_environment, historical_kinesis,
                swag_accounts):
    from historical.s3.poller import handler
    os.environ["MAX_BUCKET_BATCH"] = "4"
    handler({}, mock_lambda_context)

    # Need to ensure that 50 Buckets were added to the stream:
    kinesis = boto3.client("kinesis", region_name="us-east-1")

    all_buckets = {"SWAG": True}
    for i in range(0, 50):
        all_buckets["testbucket{}".format(i)] = True

    # Loop through the stream and make sure all buckets are accounted for:
    shard_id = kinesis.describe_stream(StreamName="historicalstream")["StreamDescription"]["Shards"][0]["ShardId"]
    iterator = kinesis.get_shard_iterator(StreamName="historicalstream", ShardId=shard_id,
                                          ShardIteratorType="AT_SEQUENCE_NUMBER", StartingSequenceNumber="0")
    records = kinesis.get_records(ShardIterator=iterator["ShardIterator"])
    for r in records["Records"]:
        data = s3_polling_schema.loads(r["Data"]).data

        assert all_buckets[data["detail"]["request_parameters"]["bucket_name"]]
        assert datetime.strptime(data["detail"]["request_parameters"]["creation_date"], '%Y-%m-%dT%H:%M:%SZ')

        # Remove from the dict (at the end, there should be 0 items left)
        del all_buckets[data["detail"]["request_parameters"]["bucket_name"]]

    assert len(all_buckets) == 0

    # Check that an exception raised doesn't break things:
    import historical.s3.poller

    def mocked_poller(account):
        raise ClientError({"Error": {"Message": "", "Code": "AccessDenied"}}, "sts:AssumeRole")

    old_method = historical.s3.poller.create_polling_event  # For pytest inter-test issues...
    historical.s3.poller.create_polling_event = mocked_poller
    handler({}, mock_lambda_context)
    historical.s3.poller.create_polling_event = old_method
    # ^^ No exception = pass


def test_collector(historical_role, buckets, mock_lambda_context, mock_lambda_environment, swag_accounts,
                   current_s3_table):
    from historical.s3.collector import handler
    now = datetime.utcnow().replace(tzinfo=None, microsecond=0)
    create_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1"
            },
            source="aws.s3",
            eventName="CreateBucket",
            eventTime=now
        )
    )
    data = json.dumps(create_event, default=serialize)
    data = KinesisRecordsFactory(
        records=[
            KinesisRecordFactory(
                kinesis=KinesisDataFactory(data=data))
        ]
    )
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, mock_lambda_context)
    assert CurrentS3Model.count() == 1

    # Polling (make sure the date is included):
    polling_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1",
                "creationDate": now
            },
            source="aws.s3",
            eventName="DescribeBucket",
            eventTime=now
        )
    )
    data = json.dumps(polling_event, default=serialize)
    data = KinesisRecordsFactory(
        records=[
            KinesisRecordFactory(
                kinesis=KinesisDataFactory(data=data))
        ]
    )
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, mock_lambda_context)
    assert CurrentS3Model.count() == 1

    # Load the config and verify the polling timestamp is in there:
    result = list(CurrentS3Model.query("arn:aws:s3:::testbucket1"))
    assert result[0].configuration["CreationDate"] == now.isoformat() + "Z"

    # And deletion:
    # Moto doesn't do anything with conditional events. There is a HAIR PULLING test issue with the eventTime
    # not being sent in, and tests sporadically failing. This ensures that Pynamo is sending over the
    # correct time so that moto tests work:
    import pynamodb.models
    before_mock = pynamodb.models.Model._set_defaults

    def mocked_method(*args, **kwargs):
        before_mock(*args, **kwargs)
        args[0]._attributes["eventTime"].default = now
        args[0].eventTime = now

    pynamodb.models.Model._set_defaults = mocked_method

    delete_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1"
            },
            source="aws.s3",
            eventName="DeleteBucket",
            eventTime=now
        )
    )
    data = json.dumps(delete_event, default=serialize)
    data = KinesisRecordsFactory(
        records=[
            KinesisRecordFactory(
                kinesis=KinesisDataFactory(data=data))
        ]
    )
    data = json.dumps(data, default=serialize)
    data = json.loads(data)
    handler(data, mock_lambda_context)
    assert CurrentS3Model.count() == 0
    pynamodb.models.Model._set_defaults = before_mock


def test_collector_deletion_order(historical_role, buckets, mock_lambda_context, mock_lambda_environment, swag_accounts,
                                  current_s3_table):
    from historical.s3.collector import handler

    # Will create two events -- A deletion event that occurs BEFORE the creation event,
    # but processed such that the deletion event arrives after the creation event.
    # The end result should be that the current table remain the same -- the deletion
    # event should NOT delete the existing configuration
    now = datetime.utcnow().replace(tzinfo=None, microsecond=0)
    five_min_prev = (datetime.now() - timedelta(minutes=15)).replace(tzinfo=None, microsecond=0)

    # Timestamps are annoying AF - Mike G
    import pynamodb.models
    before_mock = pynamodb.models.Model._set_defaults

    def mocked_method(*args, **kwargs):
        before_mock(*args, **kwargs)
        args[0]._attributes["eventTime"].default = now
        args[0].eventTime = five_min_prev

    pynamodb.models.Model._set_defaults = mocked_method

    create_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1"
            },
            source="aws.s3",
            eventName="CreateBucket",
            eventTime=now
        )
    )
    create_event_data = json.dumps(create_event, default=serialize)

    delete_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1"
            },
            source="aws.s3",
            eventName="DeleteBucket",
            eventTime=five_min_prev
        )
    )
    delete_event_data = json.dumps(delete_event, default=serialize)

    data = KinesisRecordsFactory(
        records=[
            KinesisRecordFactory(
                kinesis=KinesisDataFactory(data=create_event_data)),
            KinesisRecordFactory(
                kinesis=KinesisDataFactory(data=delete_event_data))
        ]
    )
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, mock_lambda_context)
    assert CurrentS3Model.count() == 1
    pynamodb.models.Model._set_defaults = before_mock


def test_collector_error_event(historical_role, buckets, mock_lambda_context, mock_lambda_environment, swag_accounts,
                               current_s3_table):
    from historical.s3.collector import handler
    now = datetime.utcnow().replace(tzinfo=None, microsecond=0)
    five_min_prev = (datetime.now() - timedelta(minutes=15)).replace(tzinfo=None, microsecond=0)
    # Should never process events that were errors.

    # Timestamps are annoying AF - Mike G
    import pynamodb.models
    before_mock = pynamodb.models.Model._set_defaults

    def mocked_method(*args, **kwargs):
        before_mock(*args, **kwargs)
        args[0]._attributes["eventTime"].default = now
        args[0].eventTime = five_min_prev

    pynamodb.models.Model._set_defaults = mocked_method

    create_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1"
            },
            source="aws.s3",
            eventName="CreateBucket",
            eventTime=now
        )
    )
    create_event_data = json.dumps(create_event, default=serialize)

    delete_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1"
            },
            source="aws.s3",
            eventName="DeleteBucket",
            eventTime=five_min_prev
        )
    )
    delete_event_data = json.dumps(delete_event, default=serialize)

    data = KinesisRecordsFactory(
        records=[
            KinesisRecordFactory(
                kinesis=KinesisDataFactory(data=create_event_data)),
            KinesisRecordFactory(
                kinesis=KinesisDataFactory(data=delete_event_data))
        ]
    )
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, mock_lambda_context)
    assert CurrentS3Model.count() == 1
    pynamodb.models.Model._set_defaults = before_mock


def test_collector_on_deleted_bucket(historical_role, buckets, mock_lambda_context, mock_lambda_environment,
                                     swag_accounts, current_s3_table):
    from historical.s3.collector import handler
    # If an event arrives on a bucket that is deleted, then it should skip
    # and wait until the Deletion event arrives.
    create_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "not-a-bucket"
            },
            source="aws.s3",
            eventName="PutBucketPolicy",
        )
    )
    create_event_data = json.dumps(create_event, default=serialize)
    data = KinesisRecordsFactory(
        records=[
            KinesisRecordFactory(
                kinesis=KinesisDataFactory(data=create_event_data))
        ]
    )
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, mock_lambda_context)
    assert CurrentS3Model.count() == 0


def test_differ(durable_s3_table, mock_lambda_environment):
    from historical.s3.models import DurableS3Model
    from historical.s3.differ import handler

    new_bucket = S3_BUCKET.copy()
    new_bucket['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=new_bucket,
                    Keys={
                        'arn': new_bucket['arn']
                    }
                ),
                eventName='INSERT'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert DurableS3Model.count() == 1

    # Test duplicates don't change anything:
    handler(data, None)
    assert DurableS3Model.count() == 1

    # Test ephemeral changes don't add new models:
    ephemeral_changes = S3_BUCKET.copy()
    ephemeral_changes["eventTime"] = \
        datetime(year=2017, month=5, day=12, hour=11, minute=30, second=0).isoformat() + 'Z'
    ephemeral_changes["configuration"]["_version"] = 99999
    ephemeral_changes["principalId"] = "someoneelse@example.com"
    ephemeral_changes["userIdentity"]["sessionContext"]["userName"] = "someoneelse"

    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=ephemeral_changes,
                    Keys={
                        'arn': ephemeral_changes['arn']
                    }
                ),
                eventName='MODIFY'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert DurableS3Model.count() == 1

    # Add an update:
    new_changes = S3_BUCKET.copy()
    new_date = datetime(year=2017, month=5, day=12, hour=11, minute=30, second=0).isoformat() + 'Z'
    new_changes["eventTime"] = new_date
    new_changes["Tags"] = {"ANew": "Tag"}
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=new_changes,
                    Keys={
                        'arn': new_changes['arn']
                    }
                ),
                eventName='MODIFY'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    results = list(DurableS3Model.query("arn:aws:s3:::testbucket1"))
    assert len(results) == 2
    assert results[1].Tags["ANew"] == "Tag"
    assert results[1].eventTime.isoformat() + 'Z' == new_date

    # And deletion:
    delete_bucket = S3_BUCKET.copy()
    delete_bucket["eventTime"] = datetime(year=2017, month=5, day=12, hour=12, minute=30, second=0).isoformat() + 'Z'
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    OldImage=delete_bucket,
                    Keys={
                        'arn': delete_bucket['arn']
                    }
                ),
                eventName='REMOVE'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert DurableS3Model.count() == 3
