import json
import pytz
import datetime
from historical.tests.factories import (
    CloudwatchEventFactory,
    DetailFactory,
    KinesisDataFactory,
    KinesisRecordFactory,
    KinesisRecordsFactory,
    DynamoDBDataFactory,
    DynamoDBRecordFactory,
    DynamoDBRecordsFactory,
    serialize
)

SECURITY_GROUP = {
    'arn': 'arn:aws:ec2:us-east-1:123456789010:security-group/sg-1234568',
    'GroupId': 'sg-1234568',
    'GroupName': 'testGroup',
    'VpcId': 'vpc-123343',
    'accountId': '123456789010',
    'OwnerId': '123456789010',
    'Description': 'This is a test',
    'Tags': [{'owner': 'test@example.com'}],
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

    items = list(CurrentSecurityGroupModel.query('arn:aws:ec2:us-east-1:123456789010:security-group/sg-1234568'))

    assert len(items) == 1


def test_durable_table(durable_security_group_table):
    from historical.security_group.models import DurableSecurityGroupModel

    DurableSecurityGroupModel(**SECURITY_GROUP).save()

    items = list(DurableSecurityGroupModel.query('arn:aws:ec2:us-east-1:123456789010:security-group/sg-1234568'))

    assert len(items) == 1


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


def test_differ(durable_security_group_table):
    from historical.security_group.models import DurableSecurityGroupModel
    from historical.security_group.differ import handler
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=SECURITY_GROUP,
                    Keys={
                        'arn': SECURITY_GROUP['arn']
                    }
                ),
                eventName='INSERT'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)

    assert DurableSecurityGroupModel.count() == 1

    # ensure no new record for the same data
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=SECURITY_GROUP,
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
    assert DurableSecurityGroupModel.count() == 1

    # ensure new record
    group = SECURITY_GROUP.copy()
    group['Description'] = 'changeme'
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=group,
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

    # ensure new record
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=group,
                    Keys={
                        'arn': SECURITY_GROUP['arn']
                    }
                ),
                eventName='REMOVE'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert DurableSecurityGroupModel.count() == 2


def test_collector(historical_role, mock_lambda_environment, security_groups, current_security_group_table):
    from historical.security_group.models import CurrentSecurityGroupModel
    from historical.security_group.collector import handler
    event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={'GroupId': security_groups['GroupId']}
        )
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

    handler(data, {})

    assert CurrentSecurityGroupModel.count() == 1
