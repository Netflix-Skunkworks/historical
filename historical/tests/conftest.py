import os
import pytest

import boto3

from moto.dynamodb2 import mock_dynamodb2
from moto.kinesis import mock_kinesis
from moto.s3 import mock_s3
from moto.iam import mock_iam
from moto.sts import mock_sts
from moto.ec2 import mock_ec2


@pytest.fixture(scope="function")
def s3():
    with mock_s3():
        yield boto3.client("s3")


@pytest.fixture(scope="function")
def ec2():
    with mock_ec2():
        yield boto3.client("ec2")


@pytest.fixture(scope="function")
def sts():
    with mock_sts():
        yield boto3.client("sts")


@pytest.fixture(scope="function")
def iam():
    with mock_iam():
        yield boto3.client("iam")


@pytest.fixture(scope="function")
def dynamodb():
    with mock_dynamodb2():
        yield boto3.client("dynamodb", region_name="us-east-1")


@pytest.fixture(scope="function")
def swag_accounts(s3):
    from swag_client.backend import SWAGManager
    from swag_client.util import parse_swag_config_options

    bucket_name = 'SWAG'
    data_file = 'accounts.json'
    region = 'us-east-1'

    s3.create_bucket(Bucket=bucket_name)
    os.environ['SWAG_BUCKET'] = bucket_name
    os.environ['SWAG_DATA_FILE'] = data_file
    os.environ['SWAG_REGION'] = region

    swag_opts = {
        'swag.type': 's3',
        'swag.bucket_name': bucket_name,
        'swag.data_file': data_file,
        'swag.region': region,
        'swag.cache_expires': 0
    }

    swag = SWAGManager(**parse_swag_config_options(swag_opts))

    account = {
        'aliases': ['test'],
        'contacts': ['admins@test.net'],
        'description': 'LOL, Test account',
        'email': 'testaccount@test.net',
        'environment': 'test',
        'id': '012345678910',
        'name': 'testaccount',
        'owner': 'wouldntyouliketoknow',
        'provider': 'aws',
        'sensitive': False
    }

    swag.create(account)


@pytest.fixture(scope="function")
def historical_role(iam, sts):
    iam.create_role(RoleName="historicalrole", AssumeRolePolicyDocument="{}")
    os.environ["HISTORICAL_ROLE"] = "historicalrole"


@pytest.fixture(scope="function")
def historical_kinesis():
    with mock_kinesis():
        client = boto3.client("kinesis", region_name="us-east-1")
        client.create_stream(StreamName="historicalstream", ShardCount=1)
        os.environ["HISTORICAL_STREAM"] = "historicalstream"

        yield client


@pytest.fixture(scope="function")
def buckets(s3):
    # Create buckets:
    for i in range(0, 50):
        s3.create_bucket(Bucket="testbucket{}".format(i))


@pytest.fixture(scope="function")
def security_groups(ec2):
    """Creates security groups."""
    ec2.create_security_group(
        Description='test security group',
        GroupName='test',
        VpcId='vpc-test'
    )

def mock_lambda_context():
    class MockLambdaContext():
        @staticmethod
        def get_remaining_time_in_millis():
            return 5000

    # Mock out the Raven Python Lambda timer method:
    import raven_python_lambda
    raven_python_lambda.install_timers = lambda x, y: None


@pytest.fixture(scope="function")
def mock_lambda_environment():
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['SENTRY_ENABLED'] = 'f'


@pytest.fixture()
def current_security_group_table():
    from historical.security_group.models import CurrentSecurityGroupModel
    mock_dynamodb2().start()
    CurrentSecurityGroupModel.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
    yield
    mock_dynamodb2().stop()


@pytest.fixture()
def durable_security_group_table():
    from historical.security_group.models import DurableSecurityGroupModel
    mock_dynamodb2().start()
    DurableSecurityGroupModel.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
    yield
    mock_dynamodb2().stop()
