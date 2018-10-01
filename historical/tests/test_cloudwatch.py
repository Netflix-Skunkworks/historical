"""
.. module: historical.tests.test_s3
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""

import json

from historical.tests.factories import (
    CloudwatchEventFactory,
    DetailFactory,
    serialize
)


def test_filter_request_parameters():
    """Tests that specific elements can be pulled out of the Request Parameters in the CloudWatch Event."""
    from historical.common.cloudwatch import filter_request_parameters
    event = CloudwatchEventFactory(
        detail=DetailFactory(
            requestParameters={'GroupId': 'sg-4e386e31'}
        )
    )
    data = json.loads(json.dumps(event, default=serialize))
    assert filter_request_parameters('GroupId', data) == 'sg-4e386e31'


def test_get_user_identity():
    """Tests that the User Identity can be pulled out of the CloudWatch Event."""
    from historical.common.cloudwatch import get_user_identity
    event = CloudwatchEventFactory()
    data = json.loads(json.dumps(event, default=serialize))
    assert get_user_identity(data)


def test_get_principal():
    """Tests that the Principal object can be pulled out of the CloudWatch Event."""
    from historical.common.cloudwatch import get_principal
    event = CloudwatchEventFactory()
    data = json.loads(json.dumps(event, default=serialize))
    assert get_principal(data) == 'joe@example.com'


def test_get_region():
    """Tests that the Region can be pulled out of the CloudWatch Event."""
    from historical.common.cloudwatch import get_region
    event = CloudwatchEventFactory()
    data = json.loads(json.dumps(event, default=serialize))
    assert get_region(data) == 'us-east-1'


def test_get_event_time():
    """Tests that the Event Time can be pulled out of the CloudWatch Event."""
    from historical.common.cloudwatch import get_event_time
    event = CloudwatchEventFactory()
    data = json.loads(json.dumps(event, default=serialize))
    assert get_event_time(data)


def test_get_account_id():
    """Tests that the Account ID can be pulled out of the CloudWatch Event."""
    from historical.common.cloudwatch import get_account_id
    event = CloudwatchEventFactory()
    data = json.loads(json.dumps(event, default=serialize))
    assert get_account_id(data) == '123456789012'
