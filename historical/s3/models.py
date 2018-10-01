"""
.. module: historical.s3.models
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
from marshmallow import fields, post_dump, Schema
from pynamodb.attributes import UnicodeAttribute

from historical.constants import CURRENT_REGION
from historical.models import AWSHistoricalMixin, CurrentHistoricalModel, DurableHistoricalModel, \
    HistoricalPollingBaseModel, HistoricalPollingEventDetail


# The schema version -- TODO: Get this from CloudAux
VERSION = 9


class S3Model:
    """S3 specific fields for DynamoDB."""

    BucketName = UnicodeAttribute()
    Region = UnicodeAttribute()


class DurableS3Model(DurableHistoricalModel, AWSHistoricalMixin, S3Model):
    """The Durable Table model for S3."""

    class Meta:
        """Table Details"""

        table_name = 'HistoricalS3DurableTable'
        region = CURRENT_REGION
        tech = 's3'


class CurrentS3Model(CurrentHistoricalModel, AWSHistoricalMixin, S3Model):
    """The Current Table model for S3."""

    class Meta:
        """Table Details"""

        table_name = 'HistoricalS3CurrentTable'
        region = CURRENT_REGION
        tech = 's3'


class S3PollingRequestParamsModel(Schema):
    """Schema with the required fields for the Poller to instruct the Collector to fetch S3 details."""

    bucket_name = fields.Str(dump_to="bucketName", load_from="bucketName", required=True)
    creation_date = fields.Str(dump_to="creationDate", load_from="creationDate", required=True)


class S3PollingEventDetail(HistoricalPollingEventDetail):
    """Schema that provides the required fields for mimicking the CloudWatch Event for Polling."""

    request_parameters = fields.Nested(S3PollingRequestParamsModel, dump_to="requestParameters",
                                       load_from="requestParameters", required=True)
    event_source = fields.Str(load_only=True, load_from="eventSource", required=True)
    event_name = fields.Str(load_only=True, load_from="eventName", required=True)

    @post_dump
    def add_required_s3_polling_data(self, data):
        """Adds the required data to the JSON.

        :param data:
        :return:
        """
        data["eventSource"] = "historical.s3.poller"
        data["eventName"] = "DescribeBucket"

        return data


class S3PollingEventModel(HistoricalPollingBaseModel):
    """This is the Marshmallow schema for a Polling event. This is made to look like a CloudWatch Event."""

    detail = fields.Nested(S3PollingEventDetail, required=True)
    version = fields.Str(load_only=True, required=True)

    @post_dump()
    def dump_s3_polling_event_data(self, data):
        """Adds the required data to the JSON.

        :param data:
        :return:
        """
        data["version"] = "1"

        return data

    def serialize_me(self, account, bucket_details):
        """Serializes the JSON for the Polling Event Model.

        :param account:
        :param bucket_details:
        :return:
        """
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


S3_POLLING_SCHEMA = S3PollingEventModel(strict=True)
