"""
.. module: historical.security_group.models
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
from marshmallow import fields, post_dump

from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, MapAttribute

from historical.constants import CURRENT_REGION
from historical.models import (
    HistoricalPollingEventDetail,
    HistoricalPollingBaseModel,
    DurableHistoricalModel,
    CurrentHistoricalModel,
    AWSHistoricalMixin
)

VERSION = 1


class SecurityGroupModel(object):
    GroupId = UnicodeAttribute()
    GroupName = UnicodeAttribute()
    VpcId = UnicodeAttribute(null=True)
    Region = UnicodeAttribute()


class DurableSecurityGroupModel(DurableHistoricalModel, AWSHistoricalMixin, SecurityGroupModel):
    class Meta:
        table_name = 'HistoricalSecurityGroupDurableTable'
        region = CURRENT_REGION
        tech = 'securitygroup'


class CurrentSecurityGroupModel(CurrentHistoricalModel, AWSHistoricalMixin, SecurityGroupModel):
    class Meta:
        table_name = 'HistoricalSecurityGroupCurrentTable'
        region = CURRENT_REGION
        tech = 'securitygroup'


class ViewIndex(GlobalSecondaryIndex):
    class Meta:
        projection = AllProjection()
        region = CURRENT_REGION

    view = NumberAttribute(default=0, hash_key=True)


class SecurityGroupPollingEventDetail(HistoricalPollingEventDetail):
    region = fields.Str(required=True, load_from='awsRegion', dump_to='awsRegion')

    @post_dump
    def add_required_security_group_polling_data(self, data):
        data['eventSource'] = 'historical.ec2.poller'
        data['eventName'] = 'Poller'
        return data


class SecurityGroupPollingEventModel(HistoricalPollingBaseModel):
    detail = fields.Nested(SecurityGroupPollingEventDetail, required=True)

    @post_dump()
    def dump_security_group_polling_event_data(self, data):
        data['version'] = '1'
        return data

    def serialize(self, account, group, region):
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


security_group_polling_schema = SecurityGroupPollingEventModel(strict=True)
