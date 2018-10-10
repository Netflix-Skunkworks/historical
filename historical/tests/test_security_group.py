"""
.. module: historical.tests.test_security_group
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import json
import os
import time
from datetime import datetime

import boto3
from mock import patch  # pylint: disable=E0401

from historical.common.sqs import get_queue_url
from historical.models import HistoricalPollerTaskEventModel
from historical.security_group.models import VERSION
from historical.tests.factories import CloudwatchEventFactory, DetailFactory, DynamoDBDataFactory, \
    DynamoDBRecordFactory, RecordsFactory, serialize, SnsDataFactory, SQSDataFactory, UserIdentityFactory

SECURITY_GROUP = {
    'arn': 'arn:aws:ec2:us-east-1:123456789012:security-group/sg-1234568',
    'GroupId': 'sg-1234568',
    'GroupName': 'testGroup',
    'eventSource': 'aws.ec2',
    'VpcId': 'vpc-123343',
    'accountId': '123456789012',
    'Region': 'us-east-1',
    'Tags': {'test': '<empty>'},
    'version': VERSION,
    'configuration': {
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
        ]
    }
}


# pylint: disable=W0613
def test_current_table(current_security_group_table):
    """Tests for the Current PynamoDB model."""
    from historical.security_group.models import CurrentSecurityGroupModel

    CurrentSecurityGroupModel(**SECURITY_GROUP).save()

    items = list(CurrentSecurityGroupModel.query('arn:aws:ec2:us-east-1:123456789012:security-group/sg-1234568'))

    assert len(items) == 1
    assert isinstance(items[0].ttl, int)
    assert items[0].ttl > 0


# pylint: disable=W0613
def test_durable_table(durable_security_group_table):
    """Tests for the Durable PynamoDB model."""
    from historical.security_group.models import DurableSecurityGroupModel

    # we are explicit about our eventTimes because as RANGE_KEY it will need to be unique.
    security_group = SECURITY_GROUP.copy()
    security_group['eventTime'] = datetime(2017, 5, 11, 23, 30)
    security_group.pop("eventSource")
    DurableSecurityGroupModel(**security_group).save()

    items = list(DurableSecurityGroupModel.query('arn:aws:ec2:us-east-1:123456789012:security-group/sg-1234568'))

    assert len(items) == 1
    assert not getattr(items[0], "ttl", None)

    security_group['eventTime'] = datetime(2017, 5, 12, 23, 30)
    DurableSecurityGroupModel(**security_group).save()

    items = list(DurableSecurityGroupModel.query('arn:aws:ec2:us-east-1:123456789012:security-group/sg-1234568'))

    assert len(items) == 2


def make_poller_events():
    """A sort-of fixture to make polling events for tests."""
    from historical.security_group.poller import poller_tasker_handler as handler
    handler({}, None)

    # Need to ensure that all of the accounts and regions were properly tasked (only 1 region for S3):
    sqs = boto3.client("sqs", region_name="us-east-1")
    queue_url = get_queue_url(os.environ['POLLER_TASKER_QUEUE_NAME'])
    messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10)['Messages']

    # 'Body' needs to be made into 'body' for proper parsing later:
    for msg in messages:
        msg['body'] = msg.pop('Body')

    return messages


# pylint: disable=W0613
def test_poller_tasker_handler(mock_lambda_environment, historical_sqs, swag_accounts):
    """Test the Poller tasker."""
    from historical.common.accounts import get_historical_accounts
    from historical.constants import CURRENT_REGION

    messages = make_poller_events()
    all_historical_accounts = get_historical_accounts()
    assert len(messages) == len(all_historical_accounts) == 1

    poller_events = HistoricalPollerTaskEventModel().loads(messages[0]['body']).data
    assert poller_events['account_id'] == all_historical_accounts[0]['id']
    assert poller_events['region'] == CURRENT_REGION


# pylint: disable=W0613
def test_poller_processor_handler(historical_sqs, historical_role, mock_lambda_environment, security_groups, swag_accounts):
    """Test the Poller's processing component that tasks the collector."""
    # Mock this so it returns a `NextToken`:
    def mock_describe_security_groups(**kwargs):
        from cloudaux.aws.ec2 import describe_security_groups

        # Did we receive a NextToken? (this will happen on the second run through to verify that
        # this logic is being reached:
        if kwargs.get('NextToken'):
            assert kwargs['NextToken'] == 'MOARRESULTS'

        result = describe_security_groups(**kwargs)
        result['NextToken'] = 'MOARRESULTS'

        return result

    patch_sgs = patch('historical.security_group.poller.describe_security_groups', mock_describe_security_groups)
    patch_sgs.start()

    from historical.security_group.poller import poller_processor_handler as handler
    from historical.common import cloudwatch

    # Create the events and SQS records:
    messages = make_poller_events()
    event = json.loads(json.dumps(RecordsFactory(records=messages), default=serialize))

    # Run the poller handler:
    handler(event, mock_lambda_environment)

    # Need to ensure that 3 total SGs were added into SQS:
    sqs = boto3.client("sqs", region_name="us-east-1")
    queue_url = get_queue_url(os.environ['POLLER_QUEUE_NAME'])

    messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10)['Messages']
    assert len(messages) == 3

    # Verify that the region is properly propagated through, and that we got the collected data:
    for msg in messages:
        body = json.loads(msg['Body'])
        assert cloudwatch.get_region(body) == 'us-east-1'
        assert body['detail']['collected']['OwnerId'] == '123456789012'
        assert not body['detail']['collected'].get('ResponseMetadata')

    # Now, verify that the pagination was sent in properly to SQS tasker queue:
    queue_url = get_queue_url(os.environ['POLLER_TASKER_QUEUE_NAME'])
    messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10)['Messages']
    assert len(messages) == 1
    assert json.loads(messages[0]['Body'])['NextToken'] == 'MOARRESULTS'

    # Re-run the poller:
    messages[0]['body'] = messages[0]['Body']   # Need to change the casing
    handler({'Records': messages}, mock_lambda_environment)

    patch_sgs.stop()


# pylint: disable=W0613,R0915
def test_differ(current_security_group_table, durable_security_group_table, mock_lambda_environment):
    """Tests the Differ."""
    from historical.security_group.models import DurableSecurityGroupModel
    from historical.security_group.differ import handler
    from historical.models import TTL_EXPIRY

    ttl = int(time.time() + TTL_EXPIRY)
    new_group = SECURITY_GROUP.copy()
    new_group.pop("eventSource")
    new_group['eventTime'] = datetime(year=2017, month=5, day=12, hour=10, minute=30, second=0).isoformat() + 'Z'
    new_group["ttl"] = ttl
    data = json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        NewImage=new_group,
        Keys={
            'arn': new_group['arn']
        }
    ), eventName='INSERT'), default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=json.dumps(SnsDataFactory(Message=data), default=serialize))])
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, mock_lambda_environment)
    assert DurableSecurityGroupModel.count() == 1

    # ensure no new record for the same data
    duplicate_group = SECURITY_GROUP.copy()
    duplicate_group.pop("eventSource")
    duplicate_group['eventTime'] = datetime(year=2017, month=5, day=12, hour=11, minute=30, second=0).isoformat() + 'Z'
    duplicate_group["ttl"] = ttl
    data = json.dumps(DynamoDBRecordFactory(dynamodb=DynamoDBDataFactory(
        NewImage=duplicate_group,
        Keys={
            'arn': duplicate_group['arn']
        }
    ), eventName='MODIFY'), default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=json.dumps(SnsDataFactory(Message=data), default=serialize))])
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, mock_lambda_environment)
    assert DurableSecurityGroupModel.count() == 1

    updated_group = SECURITY_GROUP.copy()
    updated_group.pop("eventSource")
    updated_group['eventTime'] = datetime(year=2017, month=5, day=12, hour=11, minute=30, second=0).isoformat() + 'Z'
    updated_group['configuration']['Description'] = 'changeme'
    updated_group["ttl"] = ttl
    data = json.dumps(
        DynamoDBRecordFactory(
            dynamodb=DynamoDBDataFactory(NewImage=updated_group, Keys={'arn': SECURITY_GROUP['arn']}),
            eventName='MODIFY'),
        default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=json.dumps(SnsDataFactory(Message=data), default=serialize))])
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, mock_lambda_environment)
    assert DurableSecurityGroupModel.count() == 2

    updated_group = SECURITY_GROUP.copy()
    updated_group.pop("eventSource")
    updated_group['eventTime'] = datetime(year=2017, month=5, day=12, hour=9, minute=30, second=0).isoformat() + 'Z'
    updated_group['configuration']['IpPermissions'][0]['IpRanges'][0]['CidrIp'] = 'changeme'
    updated_group["ttl"] = ttl
    data = json.dumps(
        DynamoDBRecordFactory(
            dynamodb=DynamoDBDataFactory(NewImage=updated_group, Keys={'arn': SECURITY_GROUP['arn']}),
            eventName='MODIFY'),
        default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=json.dumps(SnsDataFactory(Message=data), default=serialize))])
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, mock_lambda_environment)
    assert DurableSecurityGroupModel.count() == 3

    deleted_group = SECURITY_GROUP.copy()
    deleted_group.pop("eventSource")
    deleted_group['eventTime'] = datetime(year=2017, month=5, day=12, hour=12, minute=30, second=0).isoformat() + 'Z'
    deleted_group["ttl"] = ttl

    # ensure new record
    data = json.dumps(
        DynamoDBRecordFactory(
            dynamodb=DynamoDBDataFactory(OldImage=deleted_group, Keys={'arn': SECURITY_GROUP['arn']}),
            eventName='REMOVE',
            userIdentity=UserIdentityFactory(type='Service', principalId='dynamodb.amazonaws.com')),
        default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=json.dumps(SnsDataFactory(Message=data), default=serialize))])
    data = json.loads(json.dumps(data, default=serialize))
    handler(data, mock_lambda_environment)
    assert DurableSecurityGroupModel.count() == 4


# pylint: disable=W0613
def test_collector(historical_role, mock_lambda_environment, historical_sqs, security_groups,
                   current_security_group_table):
    """Tests the Collector."""
    # This should NOT be called at first:
    def mock_describe_security_groups(**kwargs):
        assert False

    patch_sgs = patch('historical.security_group.collector.describe_security_groups', mock_describe_security_groups)
    patch_sgs.start()

    from historical.security_group.models import CurrentSecurityGroupModel
    from historical.security_group.collector import handler
    from cloudaux.aws.ec2 import describe_security_groups
    sg_details = describe_security_groups(
        account_number='012345678910',
        assume_role='Historical',
        region='us-east-1',
        GroupIds=[security_groups['GroupId']])['SecurityGroups'][0]

    event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={'groupId': security_groups['GroupId']},
            eventName='Poller',
            collected=sg_details))
    data = json.dumps(event, default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=data)])
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, mock_lambda_environment)
    patch_sgs.stop()
    group = list(CurrentSecurityGroupModel.scan())
    assert len(group) == 1

    # Validate that Tags are correct:
    assert len(group[0].Tags.attribute_values) == 2
    assert group[0].Tags.attribute_values['Some'] == 'Value'
    assert group[0].Tags.attribute_values['Empty'] == '<empty>'
    group[0].delete()

    # Standard SG events:
    event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={'groupId': security_groups['GroupId']},
            eventName='CreateSecurityGroup'
        ),
    )
    data = json.dumps(event, default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=data)])
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, mock_lambda_environment)

    group = list(CurrentSecurityGroupModel.scan())
    assert len(group) == 1

    # Validate that Tags are correct:
    assert len(group[0].Tags.attribute_values) == 2
    assert group[0].Tags.attribute_values['Some'] == 'Value'
    assert group[0].Tags.attribute_values['Empty'] == '<empty>'

    event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={'groupId': security_groups['GroupId']},
            eventName='DeleteSecurityGroup'
        ),
    )
    data = json.dumps(event, default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=data)])
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, mock_lambda_environment)

    assert CurrentSecurityGroupModel.count() == 0

    # Try to get it again -- this time, add the SG ID to the responseElements:
    event = CloudwatchEventFactory(
        detail=DetailFactory(
            responseElements={'groupId': security_groups['GroupId']},
            eventName='CreateSecurityGroup'
        ),
    )
    data = json.dumps(event, default=serialize)
    data = RecordsFactory(records=[SQSDataFactory(body=data)])
    data = json.dumps(data, default=serialize)
    data = json.loads(data)

    handler(data, mock_lambda_environment)
    assert CurrentSecurityGroupModel.count() == 1
