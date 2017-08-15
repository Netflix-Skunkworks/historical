"""
.. module: historical.security_group.models
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, JSONAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from historical.models import DurableHistoricalModel, CurrentHistoricalModel, AWSHistoricalMixin


class SecurityGroupModel(object):
    aws_group_id = UnicodeAttribute()
    aws_group_name = UnicodeAttribute()
    aws_vpc_id = UnicodeAttribute()
    aws_region = UnicodeAttribute()
    description = UnicodeAttribute()
    tags = JSONAttribute()


class DurableSecurityGroupModel(Model, DurableHistoricalModel, AWSHistoricalMixin, SecurityGroupModel):
    class Meta:
        table_name = 'historical-durable-security-group'


class CurrentSecurityGroupModel(Model, CurrentHistoricalModel, AWSHistoricalMixin, SecurityGroupModel):
    class Meta:
        table_name = 'historical-current-security-group'


class ViewIndex(GlobalSecondaryIndex):
    class Meta:
        projection = AllProjection()
    view = NumberAttribute(default=0, hash_key=True)
