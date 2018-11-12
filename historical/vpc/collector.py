"""
.. module: historical.vpc.collector
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import logging

from botocore.exceptions import ClientError
from pynamodb.exceptions import DeleteError

from raven_python_lambda import RavenLambdaWrapper

from cloudaux.aws.ec2 import describe_vpcs

from historical.common.sqs import group_records_by_type
from historical.constants import CURRENT_REGION, HISTORICAL_ROLE, LOGGING_LEVEL
from historical.common import cloudwatch
from historical.common.util import deserialize_records, pull_tag_dict
from historical.vpc.models import CurrentVPCModel, VERSION

logging.basicConfig()
LOG = logging.getLogger('historical')
LOG.setLevel(LOGGING_LEVEL)


UPDATE_EVENTS = [
    'CreateVpc',
    'ModifyVpcAttribute',
    'PollVpc'
]

DELETE_EVENTS = [
    'DeleteVpc'
]


def get_arn(vpc_id, region, account_id):
    """Creates a vpc ARN."""
    return f'arn:aws:ec2:{region}:{account_id}:vpc/{vpc_id}'


def describe_vpc(record):
    """Attempts to describe vpc ids."""
    account_id = record['account']
    vpc_name = cloudwatch.filter_request_parameters('vpcName', record)
    vpc_id = cloudwatch.filter_request_parameters('vpcId', record)

    try:
        if vpc_id and vpc_name:  # pylint: disable=R1705
            return describe_vpcs(
                account_number=account_id,
                assume_role=HISTORICAL_ROLE,
                region=CURRENT_REGION,
                Filters=[
                    {
                        'Name': 'vpc-id',
                        'Values': [vpc_id]
                    }
                ]
            )
        elif vpc_id:
            return describe_vpcs(
                account_number=account_id,
                assume_role=HISTORICAL_ROLE,
                region=CURRENT_REGION,
                VpcIds=[vpc_id]
            )
        else:
            raise Exception('[X] Describe requires VpcId.')
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'InvalidVpc.NotFound':
            return []
        raise exc


def create_delete_model(record):
    """Create a vpc model from a record."""
    data = cloudwatch.get_historical_base_info(record)

    vpc_id = cloudwatch.filter_request_parameters('vpcId', record)

    arn = get_arn(vpc_id, cloudwatch.get_region(record), record['account'])

    LOG.debug(F'[-] Deleting Dynamodb Records. Hash Key: {arn}')

    # tombstone these records so that the deletion event time can be accurately tracked.
    data.update({
        'configuration': {}
    })

    items = list(CurrentVPCModel.query(arn, limit=1))

    if items:
        model_dict = items[0].__dict__['attribute_values'].copy()
        model_dict.update(data)
        model = CurrentVPCModel(**model_dict)
        model.save()
        return model

    return None


def capture_delete_records(records):
    """Writes all of our delete events to DynamoDB."""
    for record in records:
        model = create_delete_model(record)
        if model:
            try:
                model.delete(condition=(CurrentVPCModel.eventTime <= record['detail']['eventTime']))
            except DeleteError:
                LOG.warning(f'[?] Unable to delete VPC. VPC does not exist. Record: {record}')
        else:
            LOG.warning(f'[?] Unable to delete VPC. VPC does not exist. Record: {record}')


def get_vpc_name(vpc):
    """Fetches VPC Name (as tag) from VPC."""
    for tag in vpc.get('Tags', []):
        if tag['Key'].lower() == 'name':
            return tag['Value']

    return None


def capture_update_records(records):
    """Writes all updated configuration info to DynamoDB"""
    for record in records:
        data = cloudwatch.get_historical_base_info(record)
        vpc = describe_vpc(record)

        if len(vpc) > 1:
            raise Exception(f'[X] Multiple vpcs found. Record: {record}')

        if not vpc:
            LOG.warning(f'[?] No vpc information found. Record: {record}')
            continue

        vpc = vpc[0]

        # determine event data for vpc
        LOG.debug(f'Processing vpc. VPC: {vpc}')
        data.update({
            'VpcId': vpc.get('VpcId'),
            'arn': get_arn(vpc['VpcId'], cloudwatch.get_region(record), data['accountId']),
            'configuration': vpc,
            'State': vpc.get('State'),
            'IsDefault': vpc.get('IsDefault'),
            'CidrBlock': vpc.get('CidrBlock'),
            'Name': get_vpc_name(vpc),
            'Region': cloudwatch.get_region(record),
            'version': VERSION
        })

        data['Tags'] = pull_tag_dict(vpc)

        LOG.debug(f'[+] Writing DynamoDB Record. Records: {data}')

        current_revision = CurrentVPCModel(**data)
        current_revision.save()


@RavenLambdaWrapper()
def handler(event, context):  # pylint: disable=W0613
    """
    Historical vpc event collector.
    This collector is responsible for processing Cloudwatch events and polling events.
    """
    records = deserialize_records(event['Records'])

    # Split records into two groups, update and delete.
    # We don't want to query for deleted records.
    update_records, delete_records = group_records_by_type(records, UPDATE_EVENTS)
    capture_delete_records(delete_records)

    # filter out error events
    update_records = [e for e in update_records if not e['detail'].get('errorCode')]  # pylint: disable=C0103

    # group records by account for more efficient processing
    LOG.debug(f'[@] Update Records: {records}')

    capture_update_records(update_records)
