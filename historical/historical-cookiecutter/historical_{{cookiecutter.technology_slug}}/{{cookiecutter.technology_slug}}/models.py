"""
.. module: {{cookiecutter.technology_slug}}.models
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: {{cookiecutter.author}} <{{cookiecutter.email}}>
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


class {{cookiecutter.technology_slug | titlecase}}Model(object):
    # TODO add attributes specific to technology
    Tags = ListAttribute()


class Durable{{cookiecutter.technology_slug | titlecase}}Model(Model, DurableHistoricalModel, AWSHistoricalMixin, {{cookiecutter.technology_slug | titlecase}}Model):
    class Meta:
        table_name = 'Historical{{cookiecutter.technology_slug | titlecase}}DurableTable'
        region = CURRENT_REGION


class Current{{cookiecutter.technology_slug | titlecase}}Model(Model, CurrentHistoricalModel, AWSHistoricalMixin, {{cookiecutter.technology_slug | titlecase}}Model):
    class Meta:
        table_name = 'Historical{{cookiecutter.technology_slug | titlecase}}CurrentTable'
        region = CURRENT_REGION


class ViewIndex(GlobalSecondaryIndex):
    class Meta:
        projection = AllProjection()
        region = CURRENT_REGION

    view = NumberAttribute(default=0, hash_key=True)


class {{cookiecutter.technology_slug | titlecase}}PollingRequestParamsModel(Schema):
    # TODO add technology_slug validation fields
    owner_id = fields.Str(dump_to='ownerId', load_from='ownerId', required=True)


class {{cookiecutter.technology_slug | titlecase}}PollingEventDetail(HistoricalPollingEventDetail):
    @post_dump
    def add_required_{{cookiecutter.technology_slug}}_polling_data(self, data):
        data['eventSource'] = 'historical.ec2.poller'
        data['eventName'] = 'HistoricalPoller'
        return data


class {{cookiecutter.technology_slug | titlecase}}PollingEventModel(HistoricalPollingBaseModel):
    detail = fields.Nested({{cookiecutter.technology_slug | titlecase}}PollingEventDetail, required=True)

    @post_dump()
    def dump_security_group_polling_event_data(self, data):
        data['version'] = '1'
        return data

    # TODO add technology_slug specific fields
    def serialize(self, account, group):
        return self.dumps({
            'account': account,
            'detail': {
                'request_parameters': {
                    'groupId': group['GroupId']
                }
            }
        }).data


{{cookiecutter.technology_slug}}_polling_schema = {{cookiecutter.technology_slug | titlecase}}PollingEventModel(strict=True)
