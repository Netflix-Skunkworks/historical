"""
.. module: historical.tests.test_s3
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import json
import time
from datetime import datetime
from historical.tests.factories import (
    CloudwatchEventFactory,
    DetailFactory,
    KinesisDataFactory,
    KinesisRecordFactory,
    KinesisRecordsFactory,
    DynamoDBDataFactory,
    DynamoDBRecordFactory,
    DynamoDBRecordsFactory,
    UserIdentityFactory,
    serialize
)

SECURITY_GROUP = {
    'arn': 'arn:aws:ec2:us-east-1:123456789012:security-group/sg-1234568',
    'GroupId': 'sg-1234568',
    'GroupName': 'testGroup',
    'VpcId': 'vpc-123343',
    'accountId': '123456789012',
    'OwnerId': '123456789012',
    'Description': 'This is a test',
    'Region': 'us-east-1',
    'Tags': [{'Name': 'test', 'Value': '<empty>'}],
    'configuration': {
        'Description': 'string',
        'GroupName': 'string',
        'IpPermissions': [
            {
                'FromPort': 123,
                'IpProtocol': 'string',
                'IpRanges': [
                    {
                        'CidrIp': 'string'
                    },
                ],
                'Ipv6Ranges': [
                    {
                        'CidrIpv6': 'string'
                    },
                ],
                'PrefixListIds': [
                    {
                        'PrefixListId': 'string'
                    },
                ],
                'ToPort': 123,
                'UserIdGroupPairs': [
                    {
                        'GroupId': 'string',
                        'GroupName': 'string',
                        'PeeringStatus': 'string',
                        'UserId': 'string',
                        'VpcId': 'string',
                        'VpcPeeringConnectionId': 'string'
                    },
                ]
            },
        ],
        'OwnerId': 'string',
        'GroupId': 'string',
        'IpPermissionsEgress': [
            {
                'FromPort': 123,
                'IpProtocol': 'string',
                'IpRanges': [
                    {
                        'CidrIp': 'string'
                    },
                ],
                'Ipv6Ranges': [
                    {
                        'CidrIpv6': 'string'
                    },
                ],
                'PrefixListIds': [
                    {
                        'PrefixListId': 'string'
                    },
                ],
                'ToPort': 123,
                'UserIdGroupPairs': [
                    {
                        'GroupId': 'string',
                        'GroupName': 'string',
                        'PeeringStatus': 'string',
                        'UserId': 'string',
                        'VpcId': 'string',
                        'VpcPeeringConnectionId': 'string'
                    },
                ]
            },
        ],
        'Tags': [
            {
                'Key': 'string',
                'Value': 'string'
            },
        ],
        'VpcId': 'string'
    }
}


def test_current_table(current_security_group_table):
    from historical.security_group.models import CurrentSecurityGroupModel

    CurrentSecurityGroupModel(**SECURITY_GROUP).save()

    items = list(CurrentSecurityGroupModel.query('arn:aws:ec2:us-east-1:123456789012:security-group/sg-1234568'))

    assert len(items) == 1
    assert isinstance(items[0].ttl, int)
    assert items[0].ttl > 0


def test_durable_table(durable_security_group_table):
    from historical.security_group.models import DurableSecurityGroupModel

    # we are explicit about our eventTimes because as RANGE_KEY it will need to be unique.
    SECURITY_GROUP['eventTime'] = datetime(2017, 5, 11, 23, 30)
    DurableSecurityGroupModel(**SECURITY_GROUP).save()

    items = list(DurableSecurityGroupModel.query('arn:aws:ec2:us-east-1:123456789012:security-group/sg-1234568'))

    assert len(items) == 1
    assert not getattr(items[0], "ttl", None)

    SECURITY_GROUP['eventTime'] = datetime(2017, 5, 12, 23, 30)
    DurableSecurityGroupModel(**SECURITY_GROUP).save()

    items = list(DurableSecurityGroupModel.query('arn:aws:ec2:us-east-1:123456789012:security-group/sg-1234568'))

    assert len(items) == 2


def test_poller(historical_kinesis, historical_role, mock_lambda_environment, security_groups, swag_accounts):
    from historical.security_group.poller import handler
    handler(None, None)

    shard_id = historical_kinesis.describe_stream(
        StreamName="historicalstream")["StreamDescription"]["Shards"][0]["ShardId"]
    iterator = historical_kinesis.get_shard_iterator(
        StreamName="historicalstream", ShardId=shard_id, ShardIteratorType="AT_SEQUENCE_NUMBER",
        StartingSequenceNumber="0")
    records = historical_kinesis.get_records(ShardIterator=iterator["ShardIterator"])
    assert len(records['Records']) == 3


def test_differ(durable_security_group_table, mock_lambda_environment):
    from historical.security_group.models import DurableSecurityGroupModel
    from historical.security_group.differ import handler
    from historical.models import TTL_EXPIRY

    ttl = int(time.time() + TTL_EXPIRY)
    new_group = SECURITY_GROUP.copy()
    new_group['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    new_group["ttl"] = ttl
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=new_group,
                    Keys={
                        'arn': new_group['arn']
                    }
                ),
                eventName='INSERT'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)

    assert DurableSecurityGroupModel.count() == 1

    duplicate_group = SECURITY_GROUP.copy()
    duplicate_group['eventTime'] = datetime(year=2017, month=5, day=12, hour=11, minute=30, second=0).isoformat() + 'Z'
    duplicate_group["ttl"] = ttl
    # ensure no new record for the same data
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=duplicate_group,
                    Keys={
                        'arn': duplicate_group['arn']
                    }
                ),
                eventName='MODIFY'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert DurableSecurityGroupModel.count() == 1

    updated_group = SECURITY_GROUP.copy()
    updated_group['eventTime'] = datetime(year=2017, month=5, day=12, hour=11, minute=30, second=0).isoformat() + 'Z'
    updated_group['configuration']['Description'] = 'changeme'
    updated_group["ttl"] = ttl
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=updated_group,
                    Keys={
                        'arn': SECURITY_GROUP['arn']
                    }
                ),
                eventName='MODIFY'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert DurableSecurityGroupModel.count() == 2

    updated_group = SECURITY_GROUP.copy()
    updated_group['eventTime'] = datetime(year=2017, month=5, day=12, hour=9, minute=30, second=0).isoformat() + 'Z'
    updated_group['configuration']['IpPermissions'][0]['IpRanges'][0]['CidrIp'] = 'changeme'
    updated_group["ttl"] = ttl
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=updated_group,
                    Keys={
                        'arn': SECURITY_GROUP['arn']
                    }
                ),
                eventName='MODIFY'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert DurableSecurityGroupModel.count() == 3

    deleted_group = SECURITY_GROUP.copy()
    deleted_group['eventTime'] = datetime(year=2017, month=5, day=12, hour=12, minute=30, second=0).isoformat() + 'Z'
    deleted_group["ttl"] = ttl

    # ensure new record
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    OldImage=deleted_group,
                    Keys={
                        'arn': SECURITY_GROUP['arn']
                    }
                ),
                eventName='REMOVE',
                userIdentity=UserIdentityFactory(
                    type='Service',
                    principalId='dynamodb.amazonaws.com'
                )
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert DurableSecurityGroupModel.count() == 4


def test_collector(historical_role, mock_lambda_environment, security_groups, current_security_group_table):
    from historical.security_group.models import CurrentSecurityGroupModel
    from historical.security_group.collector import handler
    event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={'groupId': security_groups['GroupId']},
            eventName='CreateSecurityGroup'
        ),
    )
    data = json.dumps(event, default=serialize)
    data = KinesisRecordsFactory(
        records=[
            KinesisRecordFactory(
                kinesis=KinesisDataFactory(data=data))
        ]
    )
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, None)

    assert CurrentSecurityGroupModel.count() == 1

    event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={'groupId': security_groups['GroupId']},
            eventName='DeleteSecurityGroup'
        ),
    )
    data = json.dumps(event, default=serialize)
    data = KinesisRecordsFactory(
        records=[
            KinesisRecordFactory(
                kinesis=KinesisDataFactory(data=data))
        ]
    )
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, None)

    assert CurrentSecurityGroupModel.count() == 0
