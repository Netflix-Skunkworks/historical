"""
.. module: historical.tests.test_vpc
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

VPC = {
    'arn': 'arn:aws:ec2:us-east-1:123456789012:vpc/vpc-123343',
    'VpcId': 'vpc-123343',
    'accountId': '123456789012',
    'IsDefault': True,
    'CidrBlock': 'string',
    'State': 'available',
    'Name': 'vpc0',
    'Tags': [{'Key': 'name', 'Value': 'vpc0'}],
    'Region': 'us-east-1',
    'configuration': {
            'CidrBlock': 'string',
            'DhcpOptionsId': 'string',
            'State': 'available',
            'VpcId': 'string',
            'InstanceTenancy': 'default',
            'Ipv6CidrBlockAssociationSet': [
                {
                    'AssociationId': 'string',
                    'Ipv6CidrBlock': 'string',
                    'Ipv6CidrBlockState': {
                        'State': 'associated',
                        'StatusMessage': 'string'
                    }
                },
            ],
            'CidrBlockAssociationSet': [
                {
                    'AssociationId': 'string',
                    'CidrBlock': 'string',
                    'CidrBlockState': {
                        'State': 'associated',
                        'StatusMessage': 'string'
                    }
                },
            ],
            'IsDefault': True,
            'Tags': [
                {
                    'Key': 'name',
                    'Value': 'vpc0'
                },
            ]
        },
}


def test_current_table(current_vpc_table):
    from historical.vpc.models import CurrentVPCModel

    CurrentVPCModel(**VPC).save()

    items = list(CurrentVPCModel.query('arn:aws:ec2:us-east-1:123456789012:vpc/vpc-123343'))

    assert len(items) == 1
    assert isinstance(items[0].ttl, int)
    assert items[0].ttl > 0


def test_durable_table(durable_vpc_table):
    from historical.vpc.models import DurableVPCModel

    # we are explicit about our eventTimes because as RANGE_KEY it will need to be unique.
    VPC['eventTime'] = datetime(2017, 5, 11, 23, 30)
    DurableVPCModel(**VPC).save()

    items = list(DurableVPCModel.query('arn:aws:ec2:us-east-1:123456789012:vpc/vpc-123343'))

    assert len(items) == 1
    assert not getattr(items[0], 'ttl', None)

    VPC['eventTime'] = datetime(2017, 5, 12, 23, 30)
    DurableVPCModel(**VPC).save()

    items = list(DurableVPCModel.query('arn:aws:ec2:us-east-1:123456789012:vpc/vpc-123343'))

    assert len(items) == 2


def test_poller(historical_kinesis, historical_role, mock_lambda_environment, vpcs, swag_accounts):
    from historical.vpc.poller import handler
    handler({}, None)

    shard_id = historical_kinesis.describe_stream(
        StreamName='historicalstream')['StreamDescription']['Shards'][0]['ShardId']
    iterator = historical_kinesis.get_shard_iterator(
        StreamName='historicalstream', ShardId=shard_id, ShardIteratorType='AT_SEQUENCE_NUMBER',
        StartingSequenceNumber='0')
    records = historical_kinesis.get_records(ShardIterator=iterator['ShardIterator'])
    assert len(records['Records']) == 2


def test_differ(durable_vpc_table, mock_lambda_environment):
    from historical.vpc.models import DurableVPCModel
    from historical.vpc.differ import handler
    from historical.models import TTL_EXPIRY

    ttl = int(time.time() + TTL_EXPIRY)
    new_vpc = VPC.copy()
    new_vpc['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    new_vpc['ttl'] = ttl
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=new_vpc,
                    Keys={
                        'arn': new_vpc['arn']
                    }
                ),
                eventName='INSERT'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)

    assert DurableVPCModel.count() == 1

    duplicate_vpc = VPC.copy()
    duplicate_vpc['eventTime'] = datetime(year=2017, month=5, day=12, hour=11, minute=30, second=0).isoformat() + 'Z'
    duplicate_vpc['ttl'] = ttl
    # ensure no new record for the same data
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=duplicate_vpc,
                    Keys={
                        'arn': duplicate_vpc['arn']
                    }
                ),
                eventName='MODIFY'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert DurableVPCModel.count() == 1

    updated_vpc = VPC.copy()
    updated_vpc['eventTime'] = datetime(year=2017, month=5, day=12, hour=11, minute=30, second=0).isoformat() + 'Z'
    updated_vpc['configuration']['State'] = 'changeme'
    updated_vpc['ttl'] = ttl
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=updated_vpc,
                    Keys={
                        'arn': VPC['arn']
                    }
                ),
                eventName='MODIFY'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert DurableVPCModel.count() == 2

    updated_vpc = VPC.copy()
    updated_vpc['eventTime'] = datetime(year=2017, month=5, day=12, hour=9, minute=30, second=0).isoformat() + 'Z'
    updated_vpc['configuration']['CidrBlock'] = 'changeme'
    updated_vpc['ttl'] = ttl
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=updated_vpc,
                    Keys={
                        'arn': VPC['arn']
                    }
                ),
                eventName='MODIFY'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert DurableVPCModel.count() == 3

    updated_vpc = VPC.copy()
    updated_vpc['eventTime'] = datetime(year=2017, month=5, day=12, hour=9, minute=31, second=0).isoformat() + 'Z'
    updated_vpc.update({'Name': 'blah'})
    updated_vpc['ttl'] = ttl
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=updated_vpc,
                    Keys={
                        'arn': VPC['arn']
                    }
                ),
                eventName='MODIFY'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert DurableVPCModel.count() == 4

    deleted_vpc = VPC.copy()
    deleted_vpc['eventTime'] = datetime(year=2017, month=5, day=12, hour=12, minute=30, second=0).isoformat() + 'Z'
    deleted_vpc['ttl'] = ttl

    # ensure new record
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    OldImage=deleted_vpc,
                    Keys={
                        'arn': VPC['arn']
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
    assert DurableVPCModel.count() == 5


def test_collector(historical_role, mock_lambda_environment, vpcs, current_vpc_table):
    from historical.vpc.models import CurrentVPCModel
    from historical.vpc.collector import handler
    event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={'vpcId': vpcs['VpcId']},
            eventName='CreateVpc'
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

    assert CurrentVPCModel.count() == 1

    event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={'vpcId': vpcs['VpcId']},
            eventName='DeleteVpc'
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

    assert CurrentVPCModel.count() == 0
