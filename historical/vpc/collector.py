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
log = logging.getLogger('historical')
log.setLevel(LOGGING_LEVEL)


UPDATE_EVENTS = [
    'CreateVpc',
    'ModifyVpcAttribute',
    'Poller'
]

DELETE_EVENTS = [
    'DeleteVpc'
]


def get_arn(vpc_id, account_id):
    """Creates a vpc ARN."""
    return 'arn:aws:ec2:{region}:{account_id}:vpc/{vpc_id}'.format(
        vpc_id=vpc_id,
        region=CURRENT_REGION,
        account_id=account_id
    )


def describe_vpc(record):
    """Attempts to describe vpc ids."""
    account_id = record['account']
    vpc_name = cloudwatch.filter_request_parameters('vpcName', record)
    vpc_id = cloudwatch.filter_request_parameters('vpcId', record)

    try:
        if vpc_id and vpc_name:
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
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidVpc.NotFound':
            return []
        raise e


def create_delete_model(record):
    """Create a vpc model from a record."""
    data = cloudwatch.get_historical_base_info(record)

    vpc_id = cloudwatch.filter_request_parameters('vpcId', record)

    arn = get_arn(vpc_id, record['account'])

    log.debug('[-] Deleting Dynamodb Records. Hash Key: {arn}'.format(arn=arn))

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


def capture_delete_records(records):
    """Writes all of our delete events to DynamoDB."""
    for r in records:
        model = create_delete_model(r)
        if model:
            try:
                model.delete(condition=(CurrentVPCModel.eventTime <= r['detail']['eventTime']))
            except DeleteError as _:
                log.warning('[?] Unable to delete VPC. VPC does not exist. Record: {record}'.format(
                    record=r
                ))
        else:
            log.warning('[?] Unable to delete VPC. VPC does not exist. Record: {record}'.format(
                record=r
            ))


def get_vpc_name(vpc):
    """Fetches VPC Name (as tag) from VPC."""
    for t in vpc.get('Tags', []):
        if t['Key'].lower() == 'name':
            return t['Value']


def capture_update_records(records):
    """Writes all updated configuration info to DynamoDB"""
    for record in records:
        data = cloudwatch.get_historical_base_info(record)
        vpc = describe_vpc(record)

        if len(vpc) > 1:
            raise Exception('[X] Multiple vpcs found. Record: {record}'.format(record=record))

        if not vpc:
            log.warning('[?] No vpc information found. Record: {record}'.format(record=record))
            continue

        vpc = vpc[0]

        # determine event data for vpc
        log.debug('Processing vpc. Vpc: {}'.format(vpc))
        data.update({
            'VpcId': vpc.get('VpcId'),
            'arn': get_arn(vpc['VpcId'], data['accountId']),
            'configuration': vpc,
            'State': vpc.get('State'),
            'IsDefault': vpc.get('IsDefault'),
            'CidrBlock': vpc.get('CidrBlock'),
            'Name': get_vpc_name(vpc),
            'Region': cloudwatch.get_region(record),
            'version': VERSION
        })

        data['Tags'] = pull_tag_dict(vpc)

        log.debug('[+] Writing DynamoDB Record. Records: {record}'.format(record=data))

        current_revision = CurrentVPCModel(**data)
        current_revision.save()


@RavenLambdaWrapper()
def handler(event, context):
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
    update_records = [e for e in update_records if not e['detail'].get('errorCode')]

    # group records by account for more efficient processing
    log.debug('[@] Update Records: {records}'.format(records=records))

    capture_update_records(update_records)
