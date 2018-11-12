"""
.. module: historical.security_group.models
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
from marshmallow import fields, post_dump

from pynamodb.attributes import UnicodeAttribute

from historical.constants import CURRENT_REGION
from historical.models import AWSHistoricalMixin, CurrentHistoricalModel, DurableHistoricalModel,\
    HistoricalPollingBaseModel, HistoricalPollingEventDetail

VERSION = 1


class SecurityGroupModel:
    """Security Group specific fields for DynamoDB."""

    GroupId = UnicodeAttribute()
    GroupName = UnicodeAttribute()
    VpcId = UnicodeAttribute(null=True)
    Region = UnicodeAttribute()


class DurableSecurityGroupModel(DurableHistoricalModel, AWSHistoricalMixin, SecurityGroupModel):
    """The Durable Table model for Security Groups."""

    class Meta:
        """Table details"""

        table_name = 'HistoricalSecurityGroupDurableTable'
        region = CURRENT_REGION
        tech = 'securitygroup'


class CurrentSecurityGroupModel(CurrentHistoricalModel, AWSHistoricalMixin, SecurityGroupModel):
    """The Current Table model for Security Groups."""

    class Meta:
        """Table details"""

        table_name = 'HistoricalSecurityGroupCurrentTable'
        region = CURRENT_REGION
        tech = 'securitygroup'


class SecurityGroupPollingEventDetail(HistoricalPollingEventDetail):
    """Schema that provides the required fields for mimicking the CloudWatch Event for Polling."""

    region = fields.Str(required=True, load_from='awsRegion', dump_to='awsRegion')

    @post_dump
    def add_required_security_group_polling_data(self, data):
        """Adds the required data to the JSON.

        :param data:
        :return:
        """
        data['eventSource'] = 'historical.ec2.poller'
        data['eventName'] = 'PollSecurityGroups'
        return data


class SecurityGroupPollingEventModel(HistoricalPollingBaseModel):
    """This is the Marshmallow schema for a Polling event. This is made to look like a CloudWatch Event."""

    detail = fields.Nested(SecurityGroupPollingEventDetail, required=True)

    @post_dump()
    def dump_security_group_polling_event_data(self, data):
        """Adds the required data to the JSON.

        :param data:
        :return:
        """
        data['version'] = '1'
        return data

    def serialize(self, account, group, region):
        """Serializes the JSON for the Polling Event Model.

        :param account:
        :param group:
        :param region:
        :return:
        """
        return self.dumps({
            'account': account,
            'detail': {
                'request_parameters': {
                    'groupId': group['GroupId']
                },
                'region': region,
                'collected': group
            }
        }).data


SECURITY_GROUP_POLLING_SCHEMA = SecurityGroupPollingEventModel(strict=True)
