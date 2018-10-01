"""
.. module: historical.vpc.models
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
.. author:: Mike Grima <mgrima@netflix.com>
"""
from marshmallow import fields, post_dump, Schema

from pynamodb.attributes import BooleanAttribute, UnicodeAttribute

from historical.constants import CURRENT_REGION
from historical.models import (
    AWSHistoricalMixin,
    CurrentHistoricalModel,
    DurableHistoricalModel,
    HistoricalPollingBaseModel,
    HistoricalPollingEventDetail,
)


VERSION = 1


class VPCModel:
    """VPC specific fields for DynamoDB."""

    VpcId = UnicodeAttribute()
    State = UnicodeAttribute()
    CidrBlock = UnicodeAttribute()
    IsDefault = BooleanAttribute()
    Name = UnicodeAttribute(null=True)
    Region = UnicodeAttribute()


class DurableVPCModel(DurableHistoricalModel, AWSHistoricalMixin, VPCModel):
    """The Durable Table model for VPC."""

    class Meta:
        """Table details"""

        table_name = 'HistoricalVPCDurableTable'
        region = CURRENT_REGION
        tech = 'vpc'


class CurrentVPCModel(CurrentHistoricalModel, AWSHistoricalMixin, VPCModel):
    """The Current Table model for VPC."""

    class Meta:
        """Table details"""

        table_name = 'HistoricalVPCCurrentTable'
        region = CURRENT_REGION
        tech = 'vpc'


class VPCPollingRequestParamsModel(Schema):
    """Schema with the required fields for the Poller to instruct the Collector to fetch VPC details."""

    vpc_id = fields.Str(dump_to='vpcId', load_from='vpcId', required=True)
    owner_id = fields.Str(dump_to='ownerId', load_from='ownerId', required=True)


class VPCPollingEventDetail(HistoricalPollingEventDetail):
    """Schema that provides the required fields for mimicking the CloudWatch Event for Polling."""

    @post_dump
    def add_required_vpc_polling_data(self, data):
        """Adds the required data to the JSON.

        :param data:
        :return:
        """
        data['eventSource'] = 'historical.ec2.poller'
        data['eventName'] = 'Poller'
        return data


class VPCPollingEventModel(HistoricalPollingBaseModel):
    """This is the Marshmallow schema for a Polling event. This is made to look like a CloudWatch Event."""

    detail = fields.Nested(VPCPollingEventDetail, required=True)

    @post_dump()
    def dump_vpc_polling_event_data(self, data):
        """Adds the required data to the JSON.

        :param data:
        :return:
        """
        data['version'] = '1'
        return data

    def serialize(self, account, group):
        """Serializes the JSON for the Polling Event Model.

        :param account:
        :param group:
        :return:
        """
        return self.dumps({
            'account': account,
            'detail': {
                'request_parameters': {
                    'vpcId': group['VpcId']
                }
            }
        }).data


VPC_POLLING_SCHEMA = VPCPollingEventModel(strict=True)
