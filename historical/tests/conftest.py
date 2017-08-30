import pytest
from moto.dynamodb2 import mock_dynamodb2
from moto.kinesis import mock_kinesis
from moto.s3 import mock_s3
from moto.iam import mock_iam
from moto.sts import mock_sts
import boto3
import os


@pytest.fixture(scope="function")
def s3():
    with mock_s3():
        yield boto3.client("s3")


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
def swag_table(dynamodb):
    resource = boto3.resource('dynamodb', region_name='us-east-1')

    table = resource.create_table(
        TableName='accounts',
        KeySchema=[
            {
                'AttributeName': 'id',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        })

    table.meta.client.get_waiter('table_exists').wait(TableName='accounts')


@pytest.fixture(scope="function")
def swag_accounts(swag_table):
    from swag_client.backend import SWAGManager
    from swag_client.util import parse_swag_config_options

    swag_opts = {
        'swag.type': 'dynamodb',
        'swag.namespace': 'accounts',
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

    os.environ['SWAG_ENABLED'] = "True"

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
def mock_lambda_context():
    class MockLambdaContext():
        @staticmethod
        def get_remaining_time_in_millis():
            return 5000

    # Mock out the Raven Python Lambda timer method:
    import raven_python_lambda
    raven_python_lambda.install_timers = lambda x, y: None

    return MockLambdaContext()


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
