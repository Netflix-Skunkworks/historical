"""
.. module: {{cookiecutter.technology_slug}}.collector
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: {{cookiecutter.author}} <{{cookiecutter.email}}>
"""
import os
import logging

from pynamodb.exceptions import DeleteError

from raven_python_lambda import RavenLambdaWrapper

from historical.common import cloudwatch
from historical.common.kinesis import deserialize_records
from .models import Current{{cookiecutter.technology_slug | titlecase}}Model

logging.basicConfig()
log = logging.getLogger('historical')
level = logging.getLevelName(os.environ.get('HISTORICAL_LOGGING_LEVEL', 'WARNING'))
log.setLevel(level)


# TODO update with your events
UPDATE_EVENTS = [
    'HistoricalPoller'
]

DELETE_EVENTS = [

]


def get_arn(id, account):
    """Gets arn for {{cookiecutter.technology_name}}"""
    # TODO make ARN for technology
    # Example::
    # return 'arn:aws:ec2:{region}:{account_id}:security-group/{group_id}'.format(
    #     group_id=group_id,
    #     region=CURRENT_REGION,
    #     account_id=account_id
    # )
    return


def group_records_by_type(records):
    """Break records into two lists; create/update events and delete events."""
    update_records, delete_records = [], []
    for r in records:
        if isinstance(r, str):
            break

        if r['detail']['eventName'] in UPDATE_EVENTS:
            update_records.append(r)
        else:
            delete_records.append(r)
    return update_records, delete_records


def describe_technology(record):
    """Attempts to  describe {{cookiecutter.technology_name}} ids."""
    account_id = record['account']

    # TODO describe the technology item
    # Example::
    #    group_name = cloudwatch.filter_request_parameters('groupName', record)
    #    vpc_id = cloudwatch.filter_request_parameters('vpcId', record)
    #    group_id = cloudwatch.filter_request_parameters('groupId', record)
    #
    #    try:
    #        if vpc_id and group_name:
    #            return describe_security_groups(
    #                account_number=account_id,
    #                assume_role=HISTORICAL_ROLE,
    #                region=CURRENT_REGION,
    #                Filters=[
    #                    {
    #                        'Name': 'group-name',
    #                        'Values': [group_name]
    #                    },
    #                    {
    #                        'Name': 'vpc-id',
    #                        'Values': [vpc_id]
    #                    }
    #                ]
    #            )['SecurityGroups']
    #        elif group_id:
    #            return describe_security_groups(
    #                account_number=account_id,
    #                assume_role=HISTORICAL_ROLE,
    #                region=CURRENT_REGION,
    #                GroupIds=[group_id]
    #            )['SecurityGroups']
    #        else:
    #            raise Exception('Describe requires a groupId or a groupName and VpcId.')
    #    except ClientError as e:
    #        if e.response['Error']['Code'] == 'InvalidGroup.NotFound':
    #            return []
    #        raise e

    return


def create_delete_model(record):
    """Create a {{cookiecutter.technology_name}} model from a record."""
    data = cloudwatch.get_historical_base_info(record)

    # TODO get tech ID
    # Example::
    #    group_id = cloudwatch.filter_request_parameters('groupId', record)
    #    vpc_id = cloudwatch.filter_request_parameters('vpcId', record)
    #    group_name = cloudwatch.filter_request_parameters('groupName', record)

    tech_id = None
    arn = get_arn(tech_id, record['account'])

    log.debug('Deleting Dynamodb Records. Hash Key: {arn}'.format(arn=arn))

    # tombstone these records so that the deletion event time can be accurately tracked.
    data.update({
        'configuration': {}
    })

    items = list(Current{{cookiecutter.technology_slug | titlecase}}Model.query(arn, limit=1))

    if items:
        model_dict = items[0].__dict__['attribute_values'].copy()
        model_dict.update(data)
        model = Current{{cookiecutter.technology_slug | titlecase }}Model(**model_dict)
        model.save()
        return model


def capture_delete_records(records):
    """Writes all of our delete events to DynamoDB."""
    for r in records:
        model = create_delete_model(r)
        if model:
            try:
                model.delete(eventTime__le=r['detail']['eventTime'])
            except DeleteError as e:
                log.warning('Unable to delete {{cookiecutter.technology_name}}. {{cookiecutter.technology_name}} does not exist. Record: {record}'.format(
                    record=r
                ))
        else:
            log.warning('Unable to delete {{cookiecutter.technology_name}}. {{cookiecutter.technology_name}} does not exist. Record: {record}'.format(
                record=r
            ))


def capture_update_records(records):
    """Writes all updated configuration info to DynamoDB"""
    for record in records:
        data = cloudwatch.get_historical_base_info(record)
        items = describe_technology(record)

        if len(items) > 1:
            raise Exception('Multiple items found. Record: {record}'.format(record=record))

        if not items:
            log.warning('No technology information found. Record: {record}'.format(record=record))
            continue

        item = items[0]

        # determine event data for group
        log.debug('Processing item. Group: {}'.format(item))

        # TODO update data
        # Example::
        # data.update({
        #     'GroupId': item['GroupId'],
        #     'GroupName': item['GroupName'],
        #     'Description': item['Description'],
        #     'VpcId': item.get('VpcId'),
        #     'Tags': item.get('Tags', []),
        #     'arn': get_arn(item['GroupId'], item['OwnerId']),
        #     'OwnerId': item['OwnerId'],
        #     'configuration': item,
        #     'Region': cloudwatch.get_region(record)
        # })

        log.debug('Writing Dynamodb Record. Records: {record}'.format(record=data))

        current_revision = Current{{cookiecutter.technology_slug | titlecase}}Model(**data)
        current_revision.save()


@RavenLambdaWrapper()
def handler(event, context):
    """
    Historical {{cookiecutter.technology_name}} event collector.
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
