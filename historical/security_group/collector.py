"""
.. module: historical.security_group.collector
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import logging

from botocore.exceptions import ClientError
from pynamodb.exceptions import DeleteError

from raven_python_lambda import RavenLambdaWrapper

from cloudaux.aws.ec2 import describe_security_groups

from historical.common.sqs import group_records_by_type
from historical.constants import HISTORICAL_ROLE, LOGGING_LEVEL
from historical.common import cloudwatch
from historical.common.util import deserialize_records, pull_tag_dict
from historical.security_group.models import CurrentSecurityGroupModel, VERSION

logging.basicConfig()
LOG = logging.getLogger('historical')
LOG.setLevel(LOGGING_LEVEL)


UPDATE_EVENTS = [
    'AuthorizeSecurityGroupEgress',
    'AuthorizeSecurityGroupIngress',
    'RevokeSecurityGroupEgress',
    'RevokeSecurityGroupIngress',
    'CreateSecurityGroup',
    'PollSecurityGroups'
]

DELETE_EVENTS = [
    'DeleteSecurityGroup'
]


def get_arn(group_id, region, account_id):
    """Creates a security group ARN."""
    return f'arn:aws:ec2:{region}:{account_id}:security-group/{group_id}'


def describe_group(record, region):
    """Attempts to  describe group ids."""
    account_id = record['account']
    group_name = cloudwatch.filter_request_parameters('groupName', record)
    vpc_id = cloudwatch.filter_request_parameters('vpcId', record)
    group_id = cloudwatch.filter_request_parameters('groupId', record, look_in_response=True)

    # Did this get collected already by the poller?
    if cloudwatch.get_collected_details(record):
        LOG.debug(f"[<--] Received already collected security group data: {record['detail']['collected']}")
        return [record['detail']['collected']]

    try:
        # Always depend on Group ID first:
        if group_id:  # pylint: disable=R1705
            return describe_security_groups(
                account_number=account_id,
                assume_role=HISTORICAL_ROLE,
                region=region,
                GroupIds=[group_id]
            )['SecurityGroups']

        elif vpc_id and group_name:
            return describe_security_groups(
                account_number=account_id,
                assume_role=HISTORICAL_ROLE,
                region=region,
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

        else:
            raise Exception('[X] Did not receive Group ID or VPC/Group Name pairs. '
                            f'We got: ID: {group_id} VPC/Name: {vpc_id}/{group_name}.')
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'InvalidGroup.NotFound':
            return []
        raise exc


def create_delete_model(record):
    """Create a security group model from a record."""
    data = cloudwatch.get_historical_base_info(record)

    group_id = cloudwatch.filter_request_parameters('groupId', record)
    # vpc_id = cloudwatch.filter_request_parameters('vpcId', record)
    # group_name = cloudwatch.filter_request_parameters('groupName', record)

    arn = get_arn(group_id, cloudwatch.get_region(record), record['account'])

    LOG.debug(f'[-] Deleting Dynamodb Records. Hash Key: {arn}')

    # Tombstone these records so that the deletion event time can be accurately tracked.
    data.update({'configuration': {}})

    items = list(CurrentSecurityGroupModel.query(arn, limit=1))

    if items:
        model_dict = items[0].__dict__['attribute_values'].copy()
        model_dict.update(data)
        model = CurrentSecurityGroupModel(**model_dict)
        model.save()
        return model

    return None


def capture_delete_records(records):
    """Writes all of our delete events to DynamoDB."""
    for rec in records:
        model = create_delete_model(rec)
        if model:
            try:
                model.delete(condition=(CurrentSecurityGroupModel.eventTime <= rec['detail']['eventTime']))
            except DeleteError:
                LOG.warning(f'[X] Unable to delete security group. Security group does not exist. Record: {rec}')
        else:
            LOG.warning(f'[?] Unable to delete security group. Security group does not exist. Record: {rec}')


def capture_update_records(records):
    """Writes all updated configuration info to DynamoDB"""
    for rec in records:
        data = cloudwatch.get_historical_base_info(rec)
        group = describe_group(rec, cloudwatch.get_region(rec))

        if len(group) > 1:
            raise Exception(f'[X] Multiple groups found. Record: {rec}')

        if not group:
            LOG.warning(f'[?] No group information found. Record: {rec}')
            continue

        group = group[0]

        # Determine event data for group - and pop off items that are going to the top-level:
        LOG.debug(f'Processing group. Group: {group}')
        data.update({
            'GroupId': group['GroupId'],
            'GroupName': group.pop('GroupName'),
            'VpcId': group.pop('VpcId', None),
            'arn': get_arn(group.pop('GroupId'), cloudwatch.get_region(rec), group.pop('OwnerId')),
            'Region': cloudwatch.get_region(rec)
        })

        data['Tags'] = pull_tag_dict(group)

        # Set the remaining items to the configuration:
        data['configuration'] = group

        # Set the version:
        data['version'] = VERSION

        LOG.debug(f'[+] Writing Dynamodb Record. Records: {data}')
        current_revision = CurrentSecurityGroupModel(**data)
        current_revision.save()


@RavenLambdaWrapper()
def handler(event, context):  # pylint: disable=W0613
    """
    Historical security group event collector.
    This collector is responsible for processing Cloudwatch events and polling events.
    """
    records = deserialize_records(event['Records'])

    # Split records into two groups, update and delete.
    # We don't want to query for deleted records.
    update_records, delete_records = group_records_by_type(records, UPDATE_EVENTS)
    capture_delete_records(delete_records)

    # filter out error events
    update_records = [e for e in update_records if not e['detail'].get('errorCode')]

    # group records by account for more efficient processing
    LOG.debug(f'[@] Update Records: {records}')

    capture_update_records(update_records)
