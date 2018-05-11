"""
.. module: {{cookiecutter.technology_slug}}.test_{{cookiecutter.technology_slug}}
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
    RecordsFactory,
    DynamoDBDataFactory,
    DynamoDBRecordFactory,
    DynamoDBRecordsFactory,
    UserIdentityFactory,
    serialize
)

# TODO dictionary representation of technology
# Example::
# VPC = {
#    'arn': 'arn:aws:ec2:us-east-1:123456789012:vpc/vpc-123343',
#    'VpcId': 'vpc-123343',
#    'accountId': '123456789012',
#    'IsDefault': True,
#    'CidrBlock': 'string',
#    'State': 'available',
#    'Name': 'vpc0',
#    'Tags': [{'Key': 'name', 'Value': 'vpc0'}],
#    'Region': 'us-east-1',
#    'configuration': {
#            'CidrBlock': 'string',
#            'DhcpOptionsId': 'string',
#            'State': 'available',
#            'VpcId': 'string',
#            'InstanceTenancy': 'default',
#            'Ipv6CidrBlockAssociationSet': [
#                {
#                    'AssociationId': 'string',
#                    'Ipv6CidrBlock': 'string',
#                    'Ipv6CidrBlockState': {
#                        'State': 'associated',
#                        'StatusMessage': 'string'
#                    }
#                },
#            ],
#            'CidrBlockAssociationSet': [
#                {
#                    'AssociationId': 'string',
#                    'CidrBlock': 'string',
#                    'CidrBlockState': {
#                        'State': 'associated',
#                        'StatusMessage': 'string'
#                    }
#                },
#            ],
#            'IsDefault': True,
#            'Tags': [
#                {
#                    'Key': 'name',
#                    'Value': 'vpc0'
#                },
#            ]
#        },
# }
ITEM = {}


def test_current_table(current_{{cookiecutter.technology_slug}}_table):
    from .models import Current{{cookiecutter.technology_slug}}Model

    Current{{cookiecutter.technology_slug}}Model(**ITEM).save()

    # TODO Modify ARN
    items = list(Current{{cookiecutter.technology_slug}}Model.query('arn:aws:ec2:us-east-1:123456789012:vpc/vpc-123343'))

    assert len(items) == 1
    assert isinstance(items[0].ttl, int)
    assert items[0].ttl > 0


def test_durable_table(durable_{{cookiecutter.technology_slug}}_table):
    from .models import Durable{{cookiecutter.technology_slug | titlecase}}Model

    # we are explicit about our eventTimes because as RANGE_KEY it will need to be unique.
    ITEM['eventTime'] = datetime(2017, 5, 11, 23, 30)
    Durable{{cookiecutter.technology_slug | titlecase}}Model(**ITEM).save()

    # TODO modify ARN
    items = list(Durable{{cookiecutter.technology_slug | titlecase}}Model.query('arn:aws:ec2:us-east-1:123456789012:vpc/vpc-123343'))

    assert len(items) == 1
    assert not getattr(items[0], 'ttl', None)

    ITEM['eventTime'] = datetime(2017, 5, 12, 23, 30)
    Durable{{cookiecutter.technology_slug | titlecase}}Model(**ITEM).save()

    # TODO modify arn
    items = list(Durable{{cookiecutter.technology_slug | titlecase}}Model.query('arn:aws:ec2:us-east-1:123456789012:vpc/vpc-123343'))

    assert len(items) == 2


def test_poller(historical_kinesis, historical_role, mock_lambda_environment, {{cookiecutter.technology_slug}}s, swag_accounts):
    from .poller import handler
    handler(None, None)

    shard_id = historical_kinesis.describe_stream(
        StreamName='historicalstream')['StreamDescription']['Shards'][0]['ShardId']
    iterator = historical_kinesis.get_shard_iterator(
        StreamName='historicalstream', ShardId=shard_id, ShardIteratorType='AT_SEQUENCE_NUMBER',
        StartingSequenceNumber='0')
    records = historical_kinesis.get_records(ShardIterator=iterator['ShardIterator'])
    assert len(records['Records']) == 2


def test_differ(durable_{{cookiecutter.technology_slug}}_table, mock_lambda_environment):
    from .models import Durable{{cookiecutter.technology_slug | titlecase}}Model
    from .differ import handler
    from historical.models import TTL_EXPIRY

    ttl = int(time.time() + TTL_EXPIRY)
    new_item = ITEM.copy()
    new_item['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    new_item['ttl'] = ttl
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=new_item,
                    Keys={
                        'arn': new_item['arn']
                    }
                ),
                eventName='INSERT'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)

    assert Durable{{cookiecutter.technology_slug | titlecase}}Model.count() == 1

    duplicate_item = ITEM.copy()
    duplicate_item['eventTime'] = datetime(year=2017, month=5, day=12, hour=11, minute=30, second=0).isoformat() + 'Z'
    duplicate_item['ttl'] = ttl

    # ensure no new record for the same data
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=duplicate_item,
                    Keys={
                        'arn': duplicate_item['arn']
                    }
                ),
                eventName='MODIFY'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert Durable{{cookiecutter.technology_slug | titlecase}}Model.count() == 1

    updated_item = ITEM.copy()
    updated_item['eventTime'] = datetime(year=2017, month=5, day=12, hour=11, minute=30, second=0).isoformat() + 'Z'

    # TODO update configuration
    # Example::
    #   updated_item['configuration']['State'] = 'changeme'

    updated_item['ttl'] = ttl
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=updated_item,
                    Keys={
                        'arn': ITEM['arn']
                    }
                ),
                eventName='MODIFY'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert Durable{{cookiecutter.technology_slug | titlecase}}Model.count() == 2

    updated_item = ITEM.copy()
    updated_item['eventTime'] = datetime(year=2017, month=5, day=12, hour=9, minute=30, second=0).isoformat() + 'Z'

    # TODO change some internal value
    # Example::
    #   updated_item['configuration']['CidrBlock'] = 'changeme'

    updated_item['ttl'] = ttl
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=updated_item,
                    Keys={
                        'arn': ITEM['arn']
                    }
                ),
                eventName='MODIFY'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert Durable{{cookiecutter.technology_slug | titlecase}}Model.count() == 3

    updated_item = ITEM.copy()
    updated_item['eventTime'] = datetime(year=2017, month=5, day=12, hour=9, minute=31, second=0).isoformat() + 'Z'
    updated_item.update({'Name': 'blah'})
    updated_item['ttl'] = ttl
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    NewImage=updated_item,
                    Keys={
                        'arn': ITEM['arn']
                    }
                ),
                eventName='MODIFY'
            )
        ]
    )
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, None)
    assert Durable{{cookiecutter.technology_slug | titlecase}}Model.count() == 4

    deleted_item = ITEM.copy()
    deleted_item['eventTime'] = datetime(year=2017, month=5, day=12, hour=12, minute=30, second=0).isoformat() + 'Z'
    deleted_item['ttl'] = ttl

    # ensure new record
    data = DynamoDBRecordsFactory(
        records=[
            DynamoDBRecordFactory(
                dynamodb=DynamoDBDataFactory(
                    OldImage=deleted_item,
                    Keys={
                        'arn': ITEM['arn']
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
    assert Durable{{cookiecutter.technology_slug | titlecase}}Model.count() == 5


def test_collector(historical_role, mock_lambda_environment, {{cookiecutter.technology_slug}}s):
    from .models import Current{{cookiecutter.technology_slug | titlecase}}Model
    from .collector import handler

    # TODO modify event
    event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={}, # e.g. {'vpcId': vpcs['VpcId']},
            eventName='', # e.g. 'CreateVpc'
        ),
    )
    data = json.dumps(event, default=serialize)
    data = RecordsFactory(
        records=[
            KinesisRecordFactory(
                kinesis=KinesisDataFactory(data=data))
        ]
    )
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, None)

    assert Current{{cookiecutter.technology_slug | titlecase}}Model.count() == 1

    # TODO modify delete event
    event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={}, # e.g. {'vpcId': vpcs['VpcId']},
            eventName='', # e.g. ''DeleteVpc'
        ),
    )
    data = json.dumps(event, default=serialize)
    data = RecordsFactory(
        records=[
            KinesisRecordFactory(
                kinesis=KinesisDataFactory(data=data))
        ]
    )
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, None)

    assert Current{{cookiecutter.technology_slug | titlecase}}Model.count() == 0
