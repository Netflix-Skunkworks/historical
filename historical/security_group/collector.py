"""
.. module: historical.security_group.collector
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import os
import logging

from botocore.exceptions import ClientError

from raven_python_lambda import RavenLambdaWrapper

from cloudaux.aws.ec2 import describe_security_groups

from historical.common import cloudwatch
from historical.common.kinesis import deserialize_records
from historical.security_group.models import CurrentSecurityGroupModel

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(logging.DEBUG)


UPDATE_EVENTS = [
    'AuthorizeSecurityGroupEgress',
    'AuthorizeSecurityGroupIngress',
    'RevokeSecurityGroupEgress',
    'RevokeSecurityGroupIngress',
    'CreateSecurityGroup',
    'HistoricalPoller'
]

DELETE_EVENTS = [
    'DeleteSecurityGroup'
]


def get_arn(group_id, account_id):
    """Creates a security group ARN."""
    return 'arn:aws:ec2:{region}:{account_id}:security-group/{group_id}'.format(
        group_id=group_id,
        region=os.environ['AWS_DEFAULT_REGION'],
        account_id=account_id
    )


def group_records_by_type(records):
    """Break records into two lists; create/update events and delete events."""
    update_records, delete_records = [], []
    for r in records:
        # TODO remove
        if isinstance(r, str):
            break

        if r['detail']['eventName'] in UPDATE_EVENTS:
            update_records.append(r)
        else:
            delete_records.append(r)
    return update_records, delete_records


def describe_group(record):
    """Attempts to describe group ids."""
    account_id = record['account']
    group_name = cloudwatch.filter_request_parameters('groupName', record)
    vpc_id = cloudwatch.filter_request_parameters('vpcId', record)
    group_id = cloudwatch.filter_request_parameters('groupId', record)

    try:
        if vpc_id and group_name:
            return describe_security_groups(
                account_number=account_id,
                assume_role=os.environ.get('HISTORICAL_ROLE', 'Historical'),
                region=os.environ['AWS_DEFAULT_REGION'],
                Filters=[
                    {
                        'Name': 'group-name',
                        'Values': [group_name]
                    },
                    {
                        'Name': 'vpc-id',
                        'Values': [vpc_id]
                    }
                ]
            )['SecurityGroups']
        elif group_id:
            return describe_security_groups(
                account_number=account_id,
                assume_role=os.environ.get('HISTORICAL_ROLE', 'Historical'),
                region=os.environ['AWS_DEFAULT_REGION'],
                GroupIds=[group_id]
            )['SecurityGroups']
        else:
            raise Exception('Describe requires a groupId or a groupName and VpcId.')
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidGroup.NotFound':
            return []
        raise e


# TODO handle deletes by name
def capture_delete_records(records):
    """Writes all of our delete events to DynamoDB."""
    for r in records:
        arn = get_arn(r['detail']['requestParameters']['groupId'], r['account'])
        log.debug('Deleting Dynamodb Records. Hash Key: {arn}'.format(arn=arn))
        CurrentSecurityGroupModel(arn=arn).delete()


def capture_update_records(records):
    """Writes all updated configuration info to DynamoDB"""
    for record in records:

        group = describe_group(record)

        if len(group) > 1:
            raise Exception('Multiple groups found. Record: {record}'.format(record=record))

        if not group:
            log.warning('No group information found. Record: {record}'.format(record=record))
            continue

        group = group[0]

        # determine event data for group
        log.debug('Processing group. Group: {}'.format(group))
        data = {
            'GroupId': group['GroupId'],
            'GroupName': group['GroupName'],
            'Description': group['Description'],
            'VpcId': group['VpcId'],
            'Tags': group.get('Tags', []),
            'principalId': cloudwatch.get_principal(record),
            'arn': get_arn(group['GroupId'], group['OwnerId']),
            'OwnerId': group['OwnerId'],
            'userIdentity': cloudwatch.get_user_identity(record),
            'accountId': record['account'],
            'configuration': group
        }

        log.debug('Writing Dynamodb Record. Records: {record}'.format(record=data))

        current_revision = CurrentSecurityGroupModel(**data)
        current_revision.save()


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical security group event collector.
    This collector is responsible for processing Cloudwatch events and polling events.
    """
    records = deserialize_records(event['Records'])

    # Split records into two groups, update and delete.
    # We don't want to query for deleted records.
    update_records, delete_records = group_records_by_type(records)
    capture_delete_records(delete_records)

    # filter out error events
    update_records = [e for e in update_records if not e['detail'].get('errorCode')]

    # group records by account for more efficient processing
    log.debug('Update Records: {records}'.format(records=records))

    capture_update_records(update_records)
