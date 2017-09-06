import json

import boto3
import os

from datetime import datetime, timedelta

from historical.s3.models import s3_polling_schema, CurrentS3Model
from historical.tests.factories import (
    CloudwatchEventFactory,
    DetailFactory,
    KinesisDataFactory,
    KinesisRecordFactory,
    KinesisRecordsFactory,
    serialize
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


def test_differ():
    assert True


def test_collector(historical_role, buckets, mock_lambda_context, mock_lambda_environment, swag_accounts,
                   current_s3_table):
    from historical.s3.collector import handler
    create_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1"
            },
            source="aws.s3",
            eventName="CreateBucket"
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
    now = datetime.utcnow().replace(tzinfo=None, microsecond=0).isoformat() + "Z"
    polling_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1",
                "creationDate": now
            },
            source="aws.s3",
            eventName="DescribeBucket"
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
    assert result[0].configuration["CreationDate"] == now

    # And deletion:
    delete_event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1"
            },
            source="aws.s3",
            eventName="DeleteBucket"
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


def test_collector_deletion_order(historical_role, buckets, mock_lambda_context, mock_lambda_environment, swag_accounts,
                   current_s3_table):
    from historical.s3.collector import handler

    # Will create two events -- A deletion event that occurs BEFORE the creation event,
    # but processed such that the deletion event arrives after the creation event.
    # The end result should be that the current table remain the same -- the deletion
    # event should NOT delete the existing configuration
    now = datetime.utcnow().replace(tzinfo=None, microsecond=0).isoformat() + "Z"
    five_min_prev = (datetime.now() - timedelta(minutes=15))\
        .replace(tzinfo=None, microsecond=0).isoformat() + "Z"

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
