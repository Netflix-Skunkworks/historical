import json

import boto3
import datetime
import os
from historical.s3.models import s3_polling_schema


def test_buckets_fixture(buckets):
    client = boto3.client("s3")
    results = client.list_buckets()
    assert len(results["Buckets"]) == 50


def test_schema_serialization():
    # Make an object to serialize:
    now = datetime.datetime.utcnow().replace(tzinfo=None, microsecond=0).isoformat()

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


def test_current_table():
    pass


def test_durable_table():
    pass


def test_poller(historical_role, buckets, mock_lambda_context, historical_kinesis, swag_accounts):
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
        assert datetime.datetime.strptime(data["detail"]["request_parameters"]["creation_date"], "%Y-%m-%dT%H:%M:%S")

        # Remove from the dict (at the end, there should be 0 items left)
        del all_buckets[data["detail"]["request_parameters"]["bucket_name"]]

    assert len(all_buckets) == 0


def test_differ():
    assert True


def test_collector():
    assert True
