"""
.. module: historical.tests.test_commons
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import json
import os

from datetime import datetime

import pytest
from swag_client.backend import SWAGManager
from swag_client.util import parse_swag_config_options

from historical.common.exceptions import DurableItemIsMissingException
from historical.constants import EVENT_TOO_BIG_FLAG
from historical.s3.collector import process_update_records
from historical.tests.factories import CloudwatchEventFactory, DetailFactory, serialize, DynamoDBRecordFactory, \
    DynamoDBDataFactory

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


def test_deserialize_current_record_to_current_model(historical_role, current_s3_table, buckets):
    from historical.common.dynamodb import deserialize_current_record_to_current_model
    from historical.s3.models import CurrentS3Model

    # Create the event to fetch the Current data from:
    bucket = S3_BUCKET.copy()
    bucket['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    ddb_record = json.loads(json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        NewImage=bucket, Keys={
            'arn': bucket['arn']
        }),
        eventName='INSERT'), default=serialize))

    result = deserialize_current_record_to_current_model(ddb_record, CurrentS3Model)
    assert result.configuration.attribute_values['Name'] == "testbucket1"
    assert isinstance(result, CurrentS3Model)

    # And for event_too_big:
    # Create the bucket in the current table:
    now = datetime.utcnow().replace(tzinfo=None, microsecond=0)
    create_event = json.loads(json.dumps(CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1"
            },
            eventSource="aws.s3",
            eventName="CreateBucket",
            eventTime=now
        )
    ), default=serialize))
    process_update_records([create_event])

    del bucket['configuration']
    ddb_record = json.loads(json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        NewImage=bucket, Keys={
            'arn': bucket['arn']
        }),
        eventName='INSERT'), default=serialize))
    ddb_record[EVENT_TOO_BIG_FLAG] = True

    result = deserialize_current_record_to_current_model(ddb_record, CurrentS3Model)
    assert result.configuration.attribute_values['Name'] == "testbucket1"
    assert isinstance(result, CurrentS3Model)

    # And if the object isn't in the current table:
    ddb_record = json.loads(json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        NewImage=bucket, Keys={
            'arn': 'arn:aws:s3:::notarealbucket'
        }),
        eventName='INSERT'), default=serialize))
    ddb_record[EVENT_TOO_BIG_FLAG] = True

    result = deserialize_current_record_to_current_model(ddb_record, CurrentS3Model)
    assert not result


def test_deserialize_durable_record_to_durable_model(historical_role, durable_s3_table, buckets):
    from historical.common.dynamodb import deserialize_durable_record_to_durable_model, \
        deserialize_current_record_to_durable_model
    from historical.s3.models import CurrentS3Model, DurableS3Model

    # Create the event to fetch the Durable data from:
    bucket = S3_BUCKET.copy()
    del bucket['eventSource']
    bucket['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    ddb_record = json.loads(json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        NewImage=bucket, Keys={
            'arn': bucket['arn']
        }),
        eventName='INSERT'), default=serialize))
    result = deserialize_durable_record_to_durable_model(ddb_record, DurableS3Model)
    assert result
    assert result.configuration.attribute_values['Name'] == "testbucket1"
    assert result.eventTime == bucket['eventTime']
    assert isinstance(result, DurableS3Model)

    # And for event_too_big:
    # Create the bucket in the durable table:
    ddb_record = json.loads(json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        NewImage=bucket, Keys={
            'arn': bucket['arn']
        }),
        eventName='INSERT'), default=serialize))
    revision = deserialize_current_record_to_durable_model(ddb_record, CurrentS3Model, DurableS3Model)
    revision.save()
    ddb_record[EVENT_TOO_BIG_FLAG] = True
    del bucket['configuration']

    result = deserialize_durable_record_to_durable_model(ddb_record, DurableS3Model)
    assert result
    assert result.configuration.attribute_values['Name'] == "testbucket1"
    assert result.eventTime == bucket['eventTime']
    assert isinstance(result, DurableS3Model)

    # And if the object isn't in the durable table:
    ddb_record = json.loads(json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        NewImage=bucket, Keys={
            'arn': 'arn:aws:s3:::notarealbucket'
        }),
        eventName='INSERT'), default=serialize))
    ddb_record[EVENT_TOO_BIG_FLAG] = True

    # Raises an exception:
    with pytest.raises(DurableItemIsMissingException):
        deserialize_durable_record_to_durable_model(ddb_record, DurableS3Model)


def test_deserialize_durable_record_to_current_model(historical_role, current_s3_table, buckets):
    from historical.common.dynamodb import deserialize_durable_record_to_current_model
    from historical.s3.models import CurrentS3Model

    # Create the event to fetch the Current data from:
    bucket = S3_BUCKET.copy()
    del bucket['eventSource']
    bucket['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    ddb_record = json.loads(json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        NewImage=bucket, Keys={
            'arn': bucket['arn']
        }),
        eventName='INSERT'), default=serialize))

    result = deserialize_durable_record_to_current_model(ddb_record, CurrentS3Model)
    assert result.configuration.attribute_values['Name'] == "testbucket1"
    assert isinstance(result, CurrentS3Model)

    # And for event_too_big:
    # Create the bucket in the Current table:
    now = datetime.utcnow().replace(tzinfo=None, microsecond=0)
    create_event = json.loads(json.dumps(CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={
                "bucketName": "testbucket1"
            },
            eventSource="aws.s3",
            eventName="CreateBucket",
            eventTime=now
        )
    ), default=serialize))
    process_update_records([create_event])

    del bucket['configuration']
    ddb_record = json.loads(json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        NewImage=bucket, Keys={
            'arn': bucket['arn']
        }),
        eventName='INSERT'), default=serialize))

    ddb_record[EVENT_TOO_BIG_FLAG] = True

    result = deserialize_durable_record_to_current_model(ddb_record, CurrentS3Model)
    assert result
    assert result.configuration.attribute_values['Name'] == "testbucket1"
    assert isinstance(result, CurrentS3Model)

    # And if the object isn't in the durable table:
    ddb_record = json.loads(json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        NewImage=bucket, Keys={
            'arn': 'arn:aws:s3:::notarealbucket'
        }),
        eventName='INSERT'), default=serialize))
    ddb_record[EVENT_TOO_BIG_FLAG] = True

    result = deserialize_durable_record_to_current_model(ddb_record, CurrentS3Model)
    assert not result


def test_get_only_test_accounts(swag_accounts):
    from historical.common.accounts import get_historical_accounts

    # Setup:
    bucket_name = 'SWAG'
    data_file = 'accounts.json'
    region = 'us-east-1'
    owner = 'third-party'

    os.environ['SWAG_BUCKET'] = bucket_name
    os.environ['SWAG_DATA_FILE'] = data_file
    os.environ['SWAG_REGION'] = region
    os.environ['SWAG_OWNER'] = owner

    swag_opts = {
        'swag.type': 's3',
        'swag.bucket_name': bucket_name,
        'swag.data_file': data_file,
        'swag.region': region,
        'swag.cache_expires': 0
    }

    swag = SWAGManager(**parse_swag_config_options(swag_opts))

    # Production account:
    account = {
        'aliases': ['prod'],
        'contacts': ['admins@prod.net'],
        'description': 'LOL, PROD account',
        'email': 'prodaccount@test.net',
        'environment': 'prod',
        'id': '999999999999',
        'name': 'prodaccount',
        'owner': 'third-party',
        'provider': 'aws',
        'sensitive': False,
        'services': [
            {
                'name': 'historical',
                'status': [
                    {
                        'region': 'all',
                        'enabled': True
                    }
                ]
            }
        ]
    }
    swag.create(account)

    # Get all the swag accounts:
    result = get_historical_accounts()
    assert len(result) == 2

    assert result[1]['environment'] == 'prod'
    assert result[1]['id'] == '999999999999'

    # Only test accounts:
    os.environ['TEST_ACCOUNTS_ONLY'] = 'True'
    result = get_historical_accounts()
    assert len(result) == 1
    assert result[0]['environment'] == 'test'
    assert result[0]['id'] != '999999999999'

    # Test the boolean logic:
    os.environ['TEST_ACCOUNTS_ONLY'] = ''
    result = get_historical_accounts()
    assert len(result) == 2

    os.environ['TEST_ACCOUNTS_ONLY'] = 'false'
    result = get_historical_accounts()
    assert len(result) == 2
