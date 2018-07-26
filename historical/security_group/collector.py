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
from pynamodb.exceptions import DeleteError

from raven_python_lambda import RavenLambdaWrapper

from cloudaux.aws.ec2 import describe_security_groups

from historical.common.sqs import group_records_by_type
from historical.constants import CURRENT_REGION, HISTORICAL_ROLE, LOGGING_LEVEL
from historical.common import cloudwatch
from historical.common.util import deserialize_records
from historical.security_group.models import CurrentSecurityGroupModel

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(LOGGING_LEVEL)


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
        region=CURRENT_REGION,
        account_id=account_id
    )


def describe_group(record):
    """Attempts to  describe group ids."""
    account_id = record['account']
    group_name = cloudwatch.filter_request_parameters('groupName', record)
    vpc_id = cloudwatch.filter_request_parameters('vpcId', record)
    group_id = cloudwatch.filter_request_parameters('groupId', record, look_in_response=True)

    try:
        # Always depend on Group ID first:
        if group_id:
            return describe_security_groups(
                account_number=account_id,
                assume_role=HISTORICAL_ROLE,
                region=CURRENT_REGION,
                GroupIds=[group_id]
            )['SecurityGroups']

        elif vpc_id and group_name:
            return describe_security_groups(
                account_number=account_id,
                assume_role=HISTORICAL_ROLE,
                region=CURRENT_REGION,
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
                            'We got: ID: {} VPC/Name: {}/{}.'.format(group_id, vpc_id, group_name))
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidGroup.NotFound':
            return []
        raise e


# TODO handle deletes by name
def create_delete_model(record):
    """Create a security group model from a record."""
    data = cloudwatch.get_historical_base_info(record)

    group_id = cloudwatch.filter_request_parameters('groupId', record)
    vpc_id = cloudwatch.filter_request_parameters('vpcId', record)
    group_name = cloudwatch.filter_request_parameters('groupName', record)

    arn = get_arn(group_id, record['account'])

    log.debug('[-] Deleting Dynamodb Records. Hash Key: {arn}'.format(arn=arn))

    # tombstone these records so that the deletion event time can be accurately tracked.
    data.update({
        'configuration': {}
    })

    items = list(CurrentSecurityGroupModel.query(arn, limit=1))

    if items:
        model_dict = items[0].__dict__['attribute_values'].copy()
        model_dict.update(data)
        model = CurrentSecurityGroupModel(**model_dict)
        model.save()
        return model


def capture_delete_records(records):
    """Writes all of our delete events to DynamoDB."""
    for r in records:
        model = create_delete_model(r)
        if model:
            try:
                model.delete(condition=(CurrentSecurityGroupModel.eventTime <= r['detail']['eventTime']))
            except DeleteError as _:
                log.warning('[X] Unable to delete security group. Security group does not exist. Record: {record}'.format(
                    record=r
                ))
        else:
            log.warning('[?] Unable to delete security group. Security group does not exist. Record: {record}'.format(
                record=r
            ))


def capture_update_records(records):
    """Writes all updated configuration info to DynamoDB"""
    for record in records:
        data = cloudwatch.get_historical_base_info(record)
        group = describe_group(record)

        if len(group) > 1:
            raise Exception('[X] Multiple groups found. Record: {record}'.format(record=record))

        if not group:
            log.warning('[?] No group information found. Record: {record}'.format(record=record))
            continue

        group = group[0]

        # determine event data for group
        log.debug('Processing group. Group: {}'.format(group))
        data.update({
            'GroupId': group['GroupId'],
            'GroupName': group['GroupName'],
            'Description': group['Description'],
            'VpcId': group.get('VpcId'),
            'Tags': group.get('Tags', []),
            'arn': get_arn(group['GroupId'], group['OwnerId']),
            'OwnerId': group['OwnerId'],
            'configuration': group,
            'Region': cloudwatch.get_region(record)
        })

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
    update_records, delete_records = group_records_by_type(records, UPDATE_EVENTS)
    capture_delete_records(delete_records)

    # filter out error events
    update_records = [e for e in update_records if not e['detail'].get('errorCode')]

    # group records by account for more efficient processing
    log.debug('[@] Update Records: {records}'.format(records=records))

    capture_update_records(update_records)
