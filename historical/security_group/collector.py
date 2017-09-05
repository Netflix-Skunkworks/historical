"""
.. module: historical.security_group.collector
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import os
import logging
from itertools import groupby

from raven_python_lambda import RavenLambdaWrapper

from cloudaux.aws.ec2 import describe_security_groups

from historical.common import cloudwatch
from historical.common.kinesis import deserialize_records
from historical.security_group.models import CurrentSecurityGroupModel

logging.basicConfig()
log = logging.getLogger('historical')
log.setLevel(logging.INFO)


def get_arn(group_id, account_id):
    return 'arn:aws:ec2:{region}:{account_id}:security-group/{group_id}'.format(
        group_id=group_id,
        region=os.environ['AWS_DEFAULT_REGION'],
        account_id=account_id
    )


def get_group_events(group_id, events):
    """Fetches event data for group_id"""
    group_events = []
    for e in events:
        if e['detail']['requestParameters']['GroupId'] == group_id:
            group_events.append(e)
    return group_events


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


def group_records_by_type(records):
    """Break records into two lists; create/update events and delete events."""
    update_records, delete_records = [], []
    for r in records:
        if r['detail']['eventName'] in UPDATE_EVENTS:
            update_records.append(r)
        else:
            delete_records.append(r)
    return update_records, delete_records


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

    events = sorted(update_records, key=lambda x: x['account'])

    # group records by account for more efficient processing
    for account_id, events in groupby(events, lambda x: x['account']):
        events = list(events)
        group_ids = [e['detail']['requestParameters']['GroupId'] for e in events]

        # de-dupe for query
        group_ids = list(set(group_ids))

        # query AWS for current configuration
        groups = describe_security_groups(
            account_number=account_id,
            assume_role=os.environ['HISTORICAL_ROLE'],
            region=os.environ['AWS_DEFAULT_REGION'],
            GroupIds=group_ids
        )['SecurityGroups']

        for group in groups:
            # determine event data for group
            for event in get_group_events(group['GroupId'], events):
                data = {
                    'GroupId': group['GroupId'],
                    'GroupName': group['GroupName'],
                    'Description': group['Description'],
                    'VpcId': group['VpcId'],
                    'Tags': group['Tags'],
                    'principalId': cloudwatch.get_principal(event),
                    'arn': get_arn(group['GroupId'], group['OwnerId']),
                    'OwnerId': group['OwnerId'],
                    'userIdentity': cloudwatch.get_user_identity(event),
                    'accountId': account_id,
                    'configuration': group
                }

                # we might be able to batch write, although if duplicates exist
                # we may want to write separately to ensure changes are propagated
                current_revision = CurrentSecurityGroupModel(**data)
                current_revision.save()

    for r in delete_records:
        arn = get_arn(r['detail']['requestParameters']['GroupId'], r['account'])
        CurrentSecurityGroupModel(arn=arn).delete()

    log.debug('Successfully updated current Historical table')
