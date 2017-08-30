
SECURITY_GROUP_EVENT = {
    "account": "123456789010",
    "region": "us-east-1",
    "detail": {
        "eventVersion": "1.05",
        "eventID": "a3c1efab-1658-43ea-af24-7fbdf4363ef2",
        "eventTime": "2017-05-30T19:50:56Z",
        "requestParameters": {
            "ipPermissions": {
                "items": [
                    {
                        "prefixListIds": {},
                        "fromPort": 0,
                        "ipRanges": {},
                        "groups": {
                            "items": [
                                {
                                    "groupId": "sg-4e386e22"
                                }
                            ]
                        },
                        "toPort": 65535,
                        "ipProtocol": "tcp",
                        "ipv6Ranges": {}
                    }
                ]
            },
            "groupId": "sg-4e386e31"
        },
        "eventType": "AwsApiCall",
        "responseElements": {
            "_return": True
        },
        "awsRegion": "us-east-1",
        "eventName": "AuthorizeSecurityGroupIngress",
        "userIdentity": {
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
        },
        "eventSource": "ec2.amazonaws.com",
        "requestID": "06917c2d-0d45-45cb-bce7-1b0773734d1c",
        "userAgent": "console.ec2.amazonaws.com",
        "sourceIPAddress": "192.168.1.1"
    },
    "detail-type": "AWS API Call via CloudTrail",
    "source": "aws.ec2",
    "version": "0",
    "time": "2017-05-30T19:50:56Z",
    "id": "150ff76e-185d-4db2-82c0-dcf52c27a11a",
    "resources": []
}
