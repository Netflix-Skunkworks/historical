"""
.. module: historical.models
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
from datetime import datetime
from pynamodb.attributes import UTCDateTimeAttribute, JSONAttribute, UnicodeAttribute


class DurableHistoricalModel(object):
    event_time = UTCDateTimeAttribute(range_key=True, default=datetime.utcnow())


class CurrentHistoricalModel(object):
    pass


class AWSHistoricalMixin(object):
    arn = UnicodeAttribute(hash_key=True)
    aws_account_id = UnicodeAttribute()
    user_identity = JSONAttribute(null=True)
    principal_id = UnicodeAttribute(null=True)
    configuration = JSONAttribute()
