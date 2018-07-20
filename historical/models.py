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
from pynamodb.attributes import UnicodeAttribute, MapAttribute, NumberAttribute

from historical.attributes import EventTimeAttribute


TTL_EXPIRY = 86400  # 24 Hours in seconds

EPHEMERAL_PATHS = [
]


def default_ttl():
    return int(time.time() + TTL_EXPIRY)


def default_event_time():
    return datetime.utcnow().replace(tzinfo=None, microsecond=0).isoformat() + "Z"


class DurableHistoricalModel(object):
    eventTime = EventTimeAttribute(range_key=True, default=default_event_time)


class CurrentHistoricalModel(object):
    eventTime = EventTimeAttribute(default=default_event_time)
    ttl = NumberAttribute(default=default_ttl())
    eventSource = UnicodeAttribute()


class AWSHistoricalMixin(object):
    arn = UnicodeAttribute(hash_key=True)
    accountId = UnicodeAttribute()
    userIdentity = MapAttribute(null=True)
    principalId = UnicodeAttribute(null=True)
    configuration = MapAttribute(null=True)
    userAgent = UnicodeAttribute(null=True)
    sourceIpAddress = UnicodeAttribute(null=True)
    requestParameters = MapAttribute(null=True)


class HistoricalPollingEventDetail(Schema):
    # You must replace these:
    event_source = fields.Str(dump_to="eventSource", load_from="eventSource", required=True)
    event_name = fields.Str(dump_to="eventName", load_from="eventName", required=True)
    request_parameters = fields.Dict(dump_to="requestParameters", load_from="requestParameters", required=True)

    event_time = fields.Str(dump_to="eventTime", load_from="eventTime", required=True,
                            default=default_event_time, missing=default_event_time)


class HistoricalPollingBaseModel(Schema):
    version = fields.Str(required=True)
    account = fields.Str(required=True)

    detail_type = fields.Str(load_from="detail-type", dump_to="detail-type", required=True,
                             missing='Historical Polling Event', default='Historical Polling Event')
    source = fields.Str(required=True, missing='historical', default='historical')
    time = fields.Str(required=True, default=default_event_time, missing=default_event_time)

    # You must replace this:
    detail = fields.Nested(HistoricalPollingEventDetail, required=True)


class HistoricalPollerTaskEventModel(Schema):
    account_id = fields.Str(required=True)
    region = fields.Str(required=True)

    def serialize_me(self, account_id, region):
        return self.dumps({
            "account_id": account_id,
            "region": region
        }).data
