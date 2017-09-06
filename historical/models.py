"""
.. module: historical.models
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
.. author:: Mike Grima <mgrima@netflix.com>
"""
import decimal
import json
from datetime import datetime
from dateutil.tz import tzutc
from pynamodb.attributes import JSONAttribute, UnicodeAttribute, Attribute
from marshmallow import Schema, fields, post_dump
from pynamodb.constants import STRING

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return int(o)
        return super(DecimalEncoder, self).default(o)


class ConfigurationAttribute(Attribute):
    """
        A JSON Attribute

        Encodes JSON to unicode internally
        """
    attr_type = STRING

    def serialize(self, value):
        """
        Serializes JSON to unicode
        """
        if value is None:
            return None
        encoded = json.dumps(value, cls=DecimalEncoder)
        try:
            return unicode(encoded)
        except NameError:
            return encoded

    def deserialize(self, value):
        """
        Deserializes JSON
        """
        return json.loads(value)


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
        else:
            if value.tzinfo is None:
                value = value.replace(tzinfo=tzutc())
            return value.astimezone(tzutc()).strftime(DATETIME_FORMAT)

    def deserialize(self, value):
        """
        Takes a iso8601 datetime string and returns a datetime object
        """
        return datetime.strptime(value, DATETIME_FORMAT)


class DurableHistoricalModel(object):
    pass    # Placeholder for future changes.


class CurrentHistoricalModel(object):
    pass    # Placeholder for future changes.


class AWSHistoricalMixin(object):
    arn = UnicodeAttribute(hash_key=True)
    accountId = UnicodeAttribute()
    userIdentity = JSONAttribute(null=True)
    principalId = UnicodeAttribute(null=True)
    configuration = ConfigurationAttribute()
    eventTime = EventTimeAttribute(range_key=True, default=datetime.utcnow())


class HistoricalPollingEventDetail(Schema):
    # You must replace these:
    event_source = fields.Str(dump_to="eventSource", load_from="eventSource", required=True)
    event_name = fields.Str(dump_to="eventName", load_from="eventName", required=True)
    request_parameters = fields.Dict(dump_to="requestParameters", load_from="requestParameters", required=True)

    event_time = fields.Str(load_only=True, load_from="eventTime", required=True)

    @post_dump()
    def add_required_data(self, data):
        data["eventTime"] = datetime.utcnow().replace(tzinfo=None, microsecond=0).isoformat() + "Z"

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
        data["time"] = datetime.utcnow().replace(tzinfo=None, microsecond=0).isoformat() + "Z"

        return data
