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

from marshmallow import fields, Schema
from pynamodb.models import Model
from pynamodb.attributes import ListAttribute, MapAttribute, NumberAttribute, UnicodeAttribute

from historical.attributes import EventTimeAttribute, fix_decimals, HistoricalDecimalAttribute
from historical.constants import TTL_EXPIRY


EPHEMERAL_PATHS = []


def default_ttl():
    """Return the default TTL as an int."""
    return int(time.time() + TTL_EXPIRY)


def default_event_time():
    """Get the current time and format it for the event time."""
    return datetime.utcnow().replace(tzinfo=None, microsecond=0).isoformat() + 'Z'


class BaseHistoricalModel(Model):
    """This is the base Historical DynamoDB model. All Historical PynamoDB models should subclass this."""

    # pylint: disable=R1701
    def __iter__(self):
        """Properly serialize the PynamoDB object as a `dict` via this function.
        Helper for serializing into a typical `dict`.  See: https://github.com/pynamodb/PynamoDB/issues/152
        """
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
    """The base Historical Durable (Differ) Table model base class."""

    eventTime = EventTimeAttribute(range_key=True, default=default_event_time)


class CurrentHistoricalModel(BaseHistoricalModel):
    """The base Historical Current Table model base class."""

    eventTime = EventTimeAttribute(default=default_event_time)
    ttl = NumberAttribute(default=default_ttl())
    eventSource = UnicodeAttribute()


class AWSHistoricalMixin(BaseHistoricalModel):
    """This is the main Historical event mixin. All the major required (and optional) fields are here."""

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
    eventName = UnicodeAttribute(null=True)


class HistoricalPollingEventDetail(Schema):
    """This is the Marshmallow schema for a Polling event. This is made to look like a CloudWatch Event."""

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
    """This is a Marshmallow schema that holds objects that were described in the Poller.

    Data here will be passed onto the Collector so that the Collector need not fetch new
    data from AWS.
    """

    version = fields.Str(required=True)
    account = fields.Str(required=True)

    detail_type = fields.Str(load_from='detail-type', dump_to='detail-type', required=True,
                             missing='Poller', default='Poller')
    source = fields.Str(required=True, missing='historical', default='historical')
    time = fields.Str(required=True, default=default_event_time, missing=default_event_time)

    # You must replace this:
    detail = fields.Nested(HistoricalPollingEventDetail, required=True)


class HistoricalPollerTaskEventModel(Schema):
    """This is a Marshmallow schema that will trigger the Poller to perform the List/Describe AWS API calls.

    This informs the Poller which account and region to list/describe against. If a next_token is specified, then it
    will properly list/describe from from that pagination marker.
    """

    account_id = fields.Str(required=True)
    region = fields.Str(required=True)
    next_token = fields.Str(load_from='NextToken', dump_to='NextToken')

    def serialize_me(self, account_id, region, next_token=None):
        """Dumps the proper JSON for the schema.

        :param account_id:
        :param region:
        :param next_token:
        :return:
        """
        payload = {
            'account_id': account_id,
            'region': region
        }

        if next_token:
            payload['next_token'] = next_token

        return self.dumps(payload).data


class SimpleDurableSchema(Schema):
    """This is a Marshmallow schema that represents a simplified serialized dict of the Durable Proxy events.

    This is so that downstream consumers of Historical events need-not worry too much about DynamoDB. This is a
    fully-outlined dict of all the data for representing a given technology.  This will specify if the object was
    too big for SNS/SQS delivery.
    """

    arn = fields.Str(required=True)
    event_time = fields.Str(required=True, default=default_event_time)
    tech = fields.Str(required=True)
    event_too_big = fields.Boolean(required=False)
    item = fields.Dict(required=False)

    def serialize_me(self, arn, event_time, tech, item=None):
        """Dumps the proper JSON for the schema. If the event is too big, then don't include the item.

        :param arn:
        :param event_time:
        :param tech:
        :param item:
        :return:
        """
        payload = {
            'arn': arn,
            'event_time': event_time,
            'tech': tech
        }

        if item:
            payload['item'] = item

        else:
            payload['event_too_big'] = True

        return self.dumps(payload).data.replace('<empty>', '')
