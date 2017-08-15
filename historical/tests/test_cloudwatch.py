from datetime import datetime


def test_filter_request_parameters():
    from historical.common.cloudwatch import filter_request_parameters
    from historical.tests.vectors.cloudwatch_events import SECURITY_GROUP_EVENT

    assert filter_request_parameters('groupId', SECURITY_GROUP_EVENT) == 'sg-4e386e31'


def test_get_user_identity():
    from historical.common.cloudwatch import get_user_identity
    from historical.tests.vectors.cloudwatch_events import SECURITY_GROUP_EVENT
    assert get_user_identity(SECURITY_GROUP_EVENT) == {
            "principalId": "AROAIKELBS2RNWG7KASDF:joe@example.com",
            "accessKeyId": "ASIAIOBJTHIHQAS2ASDF",
            "sessionContext": {
                "sessionIssuer": {
                    "userName": "test_admin",
                    "type": "Role",
                    "arn": "arn:aws:iam::123456789010:role/test_admin",
                    "principalId": "AROAIKELBS2RNWG7KASDF",
                    "accountId": "123456789010"
                },
                "attributes": {
                    "creationDate": "2017-05-30T18:04:37Z",
                    "mfaAuthenticated": "false"
                }
            },
            "type": "AssumedRole",
            "arn": "arn:aws:sts::123456789010:assumed-role/test_admin/joe@example.com",
            "accountId": "12345689010"
        }


def test_get_principal():
    from historical.common.cloudwatch import get_principal
    from historical.tests.vectors.cloudwatch_events import SECURITY_GROUP_EVENT
    assert get_principal(SECURITY_GROUP_EVENT) == 'joe@example.com'


def test_get_region():
    from historical.common.cloudwatch import get_region
    from historical.tests.vectors.cloudwatch_events import SECURITY_GROUP_EVENT
    assert get_region(SECURITY_GROUP_EVENT) == 'us-east-1'


def test_get_event_time():
    from historical.common.cloudwatch import get_event_time
    from historical.tests.vectors.cloudwatch_events import SECURITY_GROUP_EVENT
    assert get_event_time(SECURITY_GROUP_EVENT) == datetime.strptime('2017-05-30T19:50:56Z', "%Y-%m-%dT%H:%M:%SZ")


def test_get_account_id():
    from historical.common.cloudwatch import get_account_id
    from historical.tests.vectors.cloudwatch_events import SECURITY_GROUP_EVENT
    assert get_account_id(SECURITY_GROUP_EVENT) == '123456789010'

