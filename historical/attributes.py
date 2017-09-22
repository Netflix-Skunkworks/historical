"""
.. module: historical.attributes
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
.. author:: Mike Grima <mgrima@netflix.com>
"""
import json
import decimal

from pynamodb.attributes import (
    Attribute,
    MapAttribute,
    ListAttribute,
    BooleanAttribute,
    NumberAttribute,
)

import pynamodb
from pynamodb.constants import STRING, NUMBER

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class HistoricalUnicodeAttribute(Attribute):
    """
    A Historical unicode attribute.
    Replaces '' with '<empty>' during serialization and correctly deserialize '<empty>' to ''
    """
    attr_type = STRING

    def serialize(self, value):
        """
        Returns a unicode string
        """
        if value is None or not len(value):
            return '<empty>'
        return value

    def deserialize(self, value):
        if value == '<empty>':
            return ''
        return value


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


def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        if obj % 1:
            return float(obj)
        return int(obj)
    raise TypeError


class HistoricalDecimalAttribute(Attribute):
    """
    A number attribute
    """
    attr_type = NUMBER

    def serialize(self, value):
        """
        Encode numbers as JSON
        """
        return json.dumps(value, default=decimal_default)

    def deserialize(self, value):
        """
        Decode numbers from JSON
        """
        return json.loads(value)


pynamodb.attributes.SERIALIZE_CLASS_MAP = {
    dict: MapAttribute(),
    list: ListAttribute(),
    set: ListAttribute(),
    bool: BooleanAttribute(),
    float: NumberAttribute(),
    int: NumberAttribute(),
    str: HistoricalUnicodeAttribute(),
    decimal.Decimal: HistoricalDecimalAttribute()
}
