"""
.. module: historical.vpc.models
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
from marshmallow import Schema, fields, post_dump

from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, BooleanAttribute, MapAttribute

from historical.constants import CURRENT_REGION
from historical.models import (
    HistoricalPollingEventDetail,
    HistoricalPollingBaseModel,
    DurableHistoricalModel,
    CurrentHistoricalModel,
    AWSHistoricalMixin
)


VERSION = 1


class VPCModel(object):
    VpcId = UnicodeAttribute()
    State = UnicodeAttribute()
    CidrBlock = UnicodeAttribute()
    IsDefault = BooleanAttribute()
    Name = UnicodeAttribute(null=True)
    Region = UnicodeAttribute()


class DurableVPCModel(DurableHistoricalModel, AWSHistoricalMixin, VPCModel):
    class Meta:
        table_name = 'HistoricalVPCDurableTable'
        region = CURRENT_REGION
        tech = 'vpc'


class CurrentVPCModel(CurrentHistoricalModel, AWSHistoricalMixin, VPCModel):
    class Meta:
        table_name = 'HistoricalVPCCurrentTable'
        region = CURRENT_REGION
        tech = 'vpc'


class ViewIndex(GlobalSecondaryIndex):
    class Meta:
        projection = AllProjection()
        region = CURRENT_REGION

    view = NumberAttribute(default=0, hash_key=True)


class VPCPollingRequestParamsModel(Schema):
    vpc_id = fields.Str(dump_to='vpcId', load_from='vpcId', required=True)
    owner_id = fields.Str(dump_to='ownerId', load_from='ownerId', required=True)


class VPCPollingEventDetail(HistoricalPollingEventDetail):
    @post_dump
    def add_required_vpc_polling_data(self, data):
        data['eventSource'] = 'historical.ec2.poller'
        data['eventName'] = 'Poller'
        return data


class VPCPollingEventModel(HistoricalPollingBaseModel):
    detail = fields.Nested(VPCPollingEventDetail, required=True)

    @post_dump()
    def dump_vpc_polling_event_data(self, data):
        data['version'] = '1'
        return data

    def serialize(self, account, group):
        return self.dumps({
            'account': account,
            'detail': {
                'request_parameters': {
                    'vpcId': group['VpcId']
                }
            }
        }).data


vpc_polling_schema = VPCPollingEventModel(strict=True)
