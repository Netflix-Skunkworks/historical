

def test_current_table(current_security_group_table):
    from historical.security_group.models import CurrentSecurityGroupModel
    group = {
        'arn': 'arn:aws:ec2:us-east-1:123456789010:security-group/sg-1234568',
        'aws_group_id': 'sg-1234568',
        'aws_group_name': 'testGroup',
        'aws_vpc_id': 'vpc-123343',
        'aws_region': 'us-east-1',
        'aws_account_id': '123456789010',
        'description': 'This is a test',
        'tags': [{'owner': 'test@example.com'}],
        'configuration': {
            'Description': 'string',
            'GroupName': 'string',
            'IpPermissions': [
                {
                    'FromPort': 123,
                    'IpProtocol': 'string',
                    'IpRanges': [
                        {
                            'CidrIp': 'string'
                        },
                    ],
                    'Ipv6Ranges': [
                        {
                            'CidrIpv6': 'string'
                        },
                    ],
                    'PrefixListIds': [
                        {
                            'PrefixListId': 'string'
                        },
                    ],
                    'ToPort': 123,
                    'UserIdGroupPairs': [
                        {
                            'GroupId': 'string',
                            'GroupName': 'string',
                            'PeeringStatus': 'string',
                            'UserId': 'string',
                            'VpcId': 'string',
                            'VpcPeeringConnectionId': 'string'
                        },
                    ]
                },
            ],
            'OwnerId': 'string',
            'GroupId': 'string',
            'IpPermissionsEgress': [
                {
                    'FromPort': 123,
                    'IpProtocol': 'string',
                    'IpRanges': [
                        {
                            'CidrIp': 'string'
                        },
                    ],
                    'Ipv6Ranges': [
                        {
                            'CidrIpv6': 'string'
                        },
                    ],
                    'PrefixListIds': [
                        {
                            'PrefixListId': 'string'
                        },
                    ],
                    'ToPort': 123,
                    'UserIdGroupPairs': [
                        {
                            'GroupId': 'string',
                            'GroupName': 'string',
                            'PeeringStatus': 'string',
                            'UserId': 'string',
                            'VpcId': 'string',
                            'VpcPeeringConnectionId': 'string'
                        },
                    ]
                },
            ],
            'Tags': [
                {
                    'Key': 'string',
                    'Value': 'string'
                },
            ],
            'VpcId': 'string'
        }
    }

    CurrentSecurityGroupModel(**group).save()

    items = list(CurrentSecurityGroupModel.query('arn:aws:ec2:us-east-1:123456789010:security-group/sg-1234568'))

    assert len(items) == 1


def test_durable_table(durable_security_group_table):
    from historical.security_group.models import DurableSecurityGroupModel

    group = {
        'arn': 'arn:aws:ec2:us-east-1:123456789010:security-group/sg-1234568',
        'aws_group_id': 'sg-1234568',
        'aws_group_name': 'testGroup',
        'aws_vpc_id': 'vpc-123343',
        'aws_region': 'us-east-1',
        'aws_account_id': '123456789010',
        'description': 'This is a test',
        'tags': [{'owner': 'test@example.com'}],
        'configuration': {
            'Description': 'string',
            'GroupName': 'string',
            'IpPermissions': [
                {
                    'FromPort': 123,
                    'IpProtocol': 'string',
                    'IpRanges': [
                        {
                            'CidrIp': 'string'
                        },
                    ],
                    'Ipv6Ranges': [
                        {
                            'CidrIpv6': 'string'
                        },
                    ],
                    'PrefixListIds': [
                        {
                            'PrefixListId': 'string'
                        },
                    ],
                    'ToPort': 123,
                    'UserIdGroupPairs': [
                        {
                            'GroupId': 'string',
                            'GroupName': 'string',
                            'PeeringStatus': 'string',
                            'UserId': 'string',
                            'VpcId': 'string',
                            'VpcPeeringConnectionId': 'string'
                        },
                    ]
                },
            ],
            'OwnerId': 'string',
            'GroupId': 'string',
            'IpPermissionsEgress': [
                {
                    'FromPort': 123,
                    'IpProtocol': 'string',
                    'IpRanges': [
                        {
                            'CidrIp': 'string'
                        },
                    ],
                    'Ipv6Ranges': [
                        {
                            'CidrIpv6': 'string'
                        },
                    ],
                    'PrefixListIds': [
                        {
                            'PrefixListId': 'string'
                        },
                    ],
                    'ToPort': 123,
                    'UserIdGroupPairs': [
                        {
                            'GroupId': 'string',
                            'GroupName': 'string',
                            'PeeringStatus': 'string',
                            'UserId': 'string',
                            'VpcId': 'string',
                            'VpcPeeringConnectionId': 'string'
                        },
                    ]
                },
            ],
            'Tags': [
                {
                    'Key': 'string',
                    'Value': 'string'
                },
            ],
            'VpcId': 'string'
        }
    }

    DurableSecurityGroupModel(**group).save()

    items = list(DurableSecurityGroupModel.query('arn:aws:ec2:us-east-1:123456789010:security-group/sg-1234568'))

    assert len(items) == 1


def test_poller():
    assert True


def test_differ():
    assert True


def test_collector():
    assert True
