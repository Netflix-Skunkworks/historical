"""
.. module: historical.models
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
.. author:: Mike Grima <mgrima@netflix.com>
"""
from datetime import datetime
from pynamodb.attributes import UnicodeAttribute, Attribute, MapAttribute
from marshmallow import Schema, fields
from pynamodb.constants import STRING

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


def default_event_time():
    return datetime.utcnow().replace(tzinfo=None, microsecond=0).isoformat() + "Z"


class EventTimeAttribute(Attribute):
    """
    An attribute for storing a UTC Datetime or iso8601 string
    """
    attr_type = STRING

    def serialize(self, value):
        """
        Takes a datetime object and returns a string
        """
        if isinstance(value, str):
            return value
        return value.strftime(DATETIME_FORMAT)

    def deserialize(self, value):
        """
        Takes a iso8601 datetime string and returns a datetime object
        """
        return datetime.strptime(value, DATETIME_FORMAT)


class DurableHistoricalModel(object):
    eventTime = EventTimeAttribute(range_key=True, default=default_event_time)


class CurrentHistoricalModel(object):
    eventTime = EventTimeAttribute(default=default_event_time)


class AWSHistoricalMixin(object):
    arn = UnicodeAttribute(hash_key=True)
    accountId = UnicodeAttribute()
    userIdentity = MapAttribute(null=True)
    principalId = UnicodeAttribute(null=True)
    configuration = MapAttribute()


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
