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
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, JSONAttribute

from historical.models import HistoricalPollingEventDetail, HistoricalPollingBaseModel
from historical.models import DurableHistoricalModel, CurrentHistoricalModel, AWSHistoricalMixin


class SecurityGroupModel(object):
    GroupId = UnicodeAttribute()
    GroupName = UnicodeAttribute()
    VpcId = UnicodeAttribute(null=True)
    OwnerId = UnicodeAttribute()
    Description = UnicodeAttribute()
    Tags = JSONAttribute()


class DurableSecurityGroupModel(Model, DurableHistoricalModel, AWSHistoricalMixin, SecurityGroupModel):
    class Meta:
        table_name = 'HistoricalSecurityGroupDurableTable'


class CurrentSecurityGroupModel(Model, CurrentHistoricalModel, AWSHistoricalMixin, SecurityGroupModel):
    class Meta:
        table_name = 'HistoricalSecurityGroupCurrentTable'


class ViewIndex(GlobalSecondaryIndex):
    class Meta:
        projection = AllProjection()

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
