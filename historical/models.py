"""
.. module: historical.models
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
.. author:: Mike Grima <mgrima@netflix.com>
"""
from datetime import datetime
from pynamodb.attributes import UTCDateTimeAttribute, JSONAttribute, UnicodeAttribute
from marshmallow import Schema, fields, post_dump, pre_load


class DurableHistoricalModel(object):
    eventTime = UTCDateTimeAttribute(range_key=True, default=datetime.utcnow())


class CurrentHistoricalModel(object):
    pass


class AWSHistoricalMixin(object):
    arn = UnicodeAttribute(hash_key=True)
    accountId = UnicodeAttribute()
    userIdentity = JSONAttribute(null=True)
    principalId = UnicodeAttribute(null=True)
    configuration = JSONAttribute()


class HistoricalPollingEventDetail(Schema):
    # You must replace these:
    event_source = fields.Str(dump_to="eventSource", load_from="eventSource", required=True)
    event_name = fields.Str(dump_to="eventName", load_from="eventName", required=True)
    request_parameters = fields.Dict(dump_to="requestParameters", load_from="requestParameters", required=True)

    event_time = fields.Str(load_only=True, load_from="eventTime", required=True)

    @post_dump()
    def add_required_data(self, data):
        data["eventTime"] = datetime.utcnow().replace(tzinfo=None, microsecond=0).isoformat()

        return data


class HistoricalPollingBaseModel(Schema):
    version = fields.Str(required=True)
    account = fields.Str(required=True)

    detail_type = fields.Str(load_only=True, load_from="detail-type", required=True)
    source = fields.Str(load_only=True, required=True)
    time = fields.Str(load_only=True, required=True)

    # You must replace this:
    detail = fields.Nested(HistoricalPollingEventDetail, required=True)

    @post_dump()
    def add_required_data(self, data):
        data["detail-type"] = "Historical Polling Event"
        data["source"] = "historical"
        data["time"] = datetime.utcnow().replace(tzinfo=None, microsecond=0).isoformat()

        return data
