"""
.. module: historical.security_group.models
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
from marshmallow import Schema, fields, post_dump

from pynamodb.models import Model
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, ListAttribute

from historical.constants import CURRENT_REGION
from historical.models import (
    HistoricalPollingEventDetail,
    HistoricalPollingBaseModel,
    DurableHistoricalModel,
    CurrentHistoricalModel,
    AWSHistoricalMixin
)


class SecurityGroupModel(object):
    GroupId = UnicodeAttribute()
    GroupName = UnicodeAttribute()
    VpcId = UnicodeAttribute(null=True)
    OwnerId = UnicodeAttribute()
    Description = UnicodeAttribute()
    Tags = ListAttribute()
    Region = UnicodeAttribute()


class DurableSecurityGroupModel(Model, DurableHistoricalModel, AWSHistoricalMixin, SecurityGroupModel):
    class Meta:
        table_name = 'HistoricalSecurityGroupDurableTable'
        region = CURRENT_REGION


class CurrentSecurityGroupModel(Model, CurrentHistoricalModel, AWSHistoricalMixin, SecurityGroupModel):
    class Meta:
        table_name = 'HistoricalSecurityGroupCurrentTable'
        region = CURRENT_REGION


class ViewIndex(GlobalSecondaryIndex):
    class Meta:
        projection = AllProjection()
        region = CURRENT_REGION

    view = NumberAttribute(default=0, hash_key=True)


class SecurityGroupPollingRequestParamsModel(Schema):
    group_id = fields.Str(dump_to='groupId', load_from='groupId', required=True)
    owner_id = fields.Str(dump_to='ownerId', load_from='ownerId', required=True)


class SecurityGroupPollingEventDetail(HistoricalPollingEventDetail):
    @post_dump
    def add_required_security_group_polling_data(self, data):
        data['eventSource'] = 'historical.ec2.poller'
        data['eventName'] = 'HistoricalPoller'
        return data


class SecurityGroupPollingEventModel(HistoricalPollingBaseModel):
    detail = fields.Nested(SecurityGroupPollingEventDetail, required=True)

    @post_dump()
    def dump_security_group_polling_event_data(self, data):
        data['version'] = '1'
        return data

    def serialize(self, account, group):
        return self.dumps({
            'account': account,
            'detail': {
                'request_parameters': {
                    'groupId': group['GroupId']
                }
            }
        }).data


security_group_polling_schema = SecurityGroupPollingEventModel(strict=True)
