from historical.tests.conftest import *


@pytest.fixture(scope='function')
def {{cookiecutter.technology_slug}}s(ec2):
    """Creates {{cookiecutter.technology_slug}}s."""
    # TODO create aws item
    # Example::
    #    yield ec2.create_vpc(
    #        CidrBlock='192.168.1.1/32',
    #        AmazonProvidedIpv6CidrBlock=True,
    #        InstanceTenancy='default'
    #    )['Vpc']
    yield


@pytest.fixture(scope='function')
def current_{{cookiecutter.technology_slug}}_table():
    from .models import Current{{cookiecutter.technology_slug | titlecase}}Model
    mock_dynamodb2().start()
    yield Current{{cookiecutter.technology_slug | titlecase}}Model.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
    mock_dynamodb2().stop()


@pytest.fixture(scope='function')
def durable_{{cookiecutter.technology_slug}}_table():
    from .models import Durable{{cookiecutter.technology_slug | titlecase}}Model
    mock_dynamodb2().start()
    yield Durable{{cookiecutter.technology_slug | titlecase}}Model.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
    mock_dynamodb2().stop()