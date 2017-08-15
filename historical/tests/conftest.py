import pytest
from moto.dynamodb2 import mock_dynamodb2


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
