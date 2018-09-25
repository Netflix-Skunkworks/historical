"""
.. module: historical.models
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
.. author:: Mike Grima <mgrima@netflix.com>
"""
import time
from datetime import datetime

from marshmallow import Schema, fields
from pynamodb.models import Model

from historical.attributes import EventTimeAttribute, HistoricalDecimalAttribute, fix_decimals

from pynamodb.attributes import UnicodeAttribute, MapAttribute, NumberAttribute, ListAttribute

from historical.constants import TTL_EXPIRY


EPHEMERAL_PATHS = []


def default_ttl():
    return int(time.time() + TTL_EXPIRY)


def default_event_time():
    return datetime.utcnow().replace(tzinfo=None, microsecond=0).isoformat() + 'Z'


class BaseHistoricalModel(Model):
    """Helper for serializing into a typical `dict`.  See: https://github.com/pynamodb/PynamoDB/issues/152"""
    def __iter__(self):
        for name, attr in self.get_attributes().items():
            try:
                if isinstance(attr, MapAttribute):
                    name, obj = name, getattr(self, name).as_dict()
                    yield name, fix_decimals(obj)  # Don't forget to remove the stupid decimals :/
                elif isinstance(attr, NumberAttribute) or isinstance(attr, HistoricalDecimalAttribute):
                    yield name, int(attr.serialize(getattr(self, name)))
                elif isinstance(attr, ListAttribute):
                    name, obj = name, [el.as_dict() for el in getattr(self, name)]
                    yield name, fix_decimals(obj)  # Don't forget to remove the stupid decimals :/
                else:
                    yield name, attr.serialize(getattr(self, name))

            # For Nulls:
            except AttributeError:
                yield name, None


class DurableHistoricalModel(BaseHistoricalModel):
    eventTime = EventTimeAttribute(range_key=True, default=default_event_time)


class CurrentHistoricalModel(BaseHistoricalModel):
    eventTime = EventTimeAttribute(default=default_event_time)
    ttl = NumberAttribute(default=default_ttl())
    eventSource = UnicodeAttribute()


class AWSHistoricalMixin(BaseHistoricalModel):
    arn = UnicodeAttribute(hash_key=True)
    accountId = UnicodeAttribute()
    configuration = MapAttribute()
    Tags = MapAttribute()
    version = HistoricalDecimalAttribute()
    userIdentity = MapAttribute(null=True)
    principalId = UnicodeAttribute(null=True)
    userAgent = UnicodeAttribute(null=True)
    sourceIpAddress = UnicodeAttribute(null=True)
    requestParameters = MapAttribute(null=True)


class HistoricalPollingEventDetail(Schema):
    # You must replace these:
    event_source = fields.Str(dump_to='eventSource', load_from='eventSource', required=True)
    event_name = fields.Str(dump_to='eventName', load_from='eventName', required=True)
    request_parameters = fields.Dict(dump_to='requestParameters', load_from='requestParameters', required=True)

    # This field is for technologies that lack a "list" method. For those technologies, the tasked poller
    # will perform all the describes and embed the major configuration details into this field:
    collected = fields.Dict(dump_to='collected', load_from='collected', required=False)
    # ^^ The collector will then need to look for this and figure out how to save it to DDB.

    event_time = fields.Str(dump_to='eventTime', load_from='eventTime', required=True,
                            default=default_event_time, missing=default_event_time)


class HistoricalPollingBaseModel(Schema):
    version = fields.Str(required=True)
    account = fields.Str(required=True)

    detail_type = fields.Str(load_from='detail-type', dump_to='detail-type', required=True,
                             missing='Poller', default='Poller')
    source = fields.Str(required=True, missing='historical', default='historical')
    time = fields.Str(required=True, default=default_event_time, missing=default_event_time)

    # You must replace this:
    detail = fields.Nested(HistoricalPollingEventDetail, required=True)


class HistoricalPollerTaskEventModel(Schema):
    account_id = fields.Str(required=True)
    region = fields.Str(required=True)
    next_token = fields.Str(load_from='NextToken', dump_to='NextToken')

    def serialize_me(self, account_id, region, next_token=None):
        payload = {
            'account_id': account_id,
            'region': region
        }

        if next_token:
            payload['next_token'] = next_token

        return self.dumps(payload).data
