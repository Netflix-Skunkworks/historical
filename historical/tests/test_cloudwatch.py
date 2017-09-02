import json

from historical.tests.factories import (
    CloudwatchEventFactory,
    DetailFactory,
    serialize
)


def test_filter_request_parameters():
    from historical.common.cloudwatch import filter_request_parameters
    event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={'GroupId': 'sg-4e386e31'}
        )
    )
    data = json.loads(json.dumps(event, default=serialize))
    assert filter_request_parameters('GroupId', data) == 'sg-4e386e31'


def test_get_user_identity():
    from historical.common.cloudwatch import get_user_identity
    event = CloudwatchEventFactory()
    data = json.loads(json.dumps(event, default=serialize))
    assert get_user_identity(data)


def test_get_principal():
    from historical.common.cloudwatch import get_principal
    event = CloudwatchEventFactory()
    data = json.loads(json.dumps(event, default=serialize))
    assert get_principal(data) == 'joe@example.com'


def test_get_region():
    from historical.common.cloudwatch import get_region
    event = CloudwatchEventFactory()
    data = json.loads(json.dumps(event, default=serialize))
    assert get_region(data) == 'us-east-1'


def test_get_event_time():
    from historical.common.cloudwatch import get_event_time
    event = CloudwatchEventFactory()
    data = json.loads(json.dumps(event, default=serialize))
    assert get_event_time(data)


def test_get_account_id():
    from historical.common.cloudwatch import get_account_id
    event = CloudwatchEventFactory()
    data = json.loads(json.dumps(event, default=serialize))
    assert get_account_id(data) == '123456789010'

