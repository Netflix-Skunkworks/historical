"""
.. module: historical.s3.models
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
from marshmallow import Schema, fields, post_dump
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, MapAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from historical.constants import CURRENT_REGION
from historical.models import DurableHistoricalModel, CurrentHistoricalModel, AWSHistoricalMixin, \
    HistoricalPollingEventDetail, HistoricalPollingBaseModel


# The schema version -- TODO: Get this from CloudAux
VERSION = 9


class S3Model(object):
    BucketName = UnicodeAttribute()
    Region = UnicodeAttribute()


class DurableS3Model(DurableHistoricalModel, AWSHistoricalMixin, S3Model):
    class Meta:
        table_name = 'HistoricalS3DurableTable'
        region = CURRENT_REGION
        tech = 's3'


class CurrentS3Model(CurrentHistoricalModel, AWSHistoricalMixin, S3Model):
    class Meta:
        table_name = 'HistoricalS3CurrentTable'
        region = CURRENT_REGION
        tech = 's3'


class ViewIndex(GlobalSecondaryIndex):
    class Meta:
        projection = AllProjection()
        region = CURRENT_REGION

    view = NumberAttribute(default=0, hash_key=True)


class S3PollingRequestParamsModel(Schema):
    bucket_name = fields.Str(dump_to="bucketName", load_from="bucketName", required=True)
    creation_date = fields.Str(dump_to="creationDate", load_from="creationDate", required=True)


class S3PollingEventDetail(HistoricalPollingEventDetail):
    request_parameters = fields.Nested(S3PollingRequestParamsModel, dump_to="requestParameters",
                                       load_from="requestParameters", required=True)

    event_source = fields.Str(load_only=True, load_from="eventSource", required=True)
    event_name = fields.Str(load_only=True, load_from="eventName", required=True)

    @post_dump
    def add_required_s3_polling_data(self, data):
        data["eventSource"] = "historical.s3.poller"
        data["eventName"] = "DescribeBucket"

        return data


class S3PollingEventModel(HistoricalPollingBaseModel):
    detail = fields.Nested(S3PollingEventDetail, required=True)

    version = fields.Str(load_only=True, required=True)

    @post_dump()
    def dump_s3_polling_event_data(self, data):
        data["version"] = "1"

        return data

    def serialize_me(self, account, bucket_details):
        return self.dumps({
            "account": account,
            "detail": {
                "request_parameters": {
                    "bucket_name": bucket_details["Name"],
                    "creation_date": bucket_details["CreationDate"].replace(
                        tzinfo=None, microsecond=0).isoformat() + "Z"
                }
            }
        }).data


s3_polling_schema = S3PollingEventModel(strict=True)
