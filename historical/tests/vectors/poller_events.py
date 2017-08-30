SECURITY_GROUP_EVENT = {
    "account": "123456789010",
    "region": "us-east-1",
    "detail": {
        "eventID": "a3c1efab-1658-43ea-af24-7fbdf4363ef2",
        "eventTime": "2017-05-30T19:50:56Z",
        "requestParameters": {
            "groupId": "sg-4e386e31"
        },
        "eventType": "AwsApiCall",
        "awsRegion": "us-east-1",
        "userIdentity": {
            "sessionContext": {
                "sessionIssuer": {
                    "userName": "historical_poller",
                    "type": "Role",
                    "arn": "arn:aws:iam::123456789010:role/historical_poller",
                    "principalId": "AROAIKELBS2RNWG7KASDF",
                    "accountId": "123456789010"
                }
            }
        },
        "detail-type": "Historical security group poller.",
        "source": "historical.poller",
        "time": "2017-05-30T19:50:56Z",
        "id": "150ff76e-185d-4db2-82c0-dcf52c27a11a"
    }
}
