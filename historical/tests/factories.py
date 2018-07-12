"""
.. module: historical.tests.factories
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""

import pytz
import datetime
from boto3.dynamodb.types import TypeSerializer
from factory import SubFactory, Factory, post_generation
from factory.fuzzy import FuzzyDateTime, FuzzyText


seria = TypeSerializer()


def serialize(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime.datetime):
        serial = obj.replace(microsecond=0).replace(tzinfo=None).isoformat() + "Z"
        return serial

    if isinstance(obj, bytes):
        return obj.decode('utf-8')

    return obj.__dict__


class SessionIssuer(object):
    def __init__(self, userName, type, arn, principalId, accountId):
        self.userName = userName
        self.type = type
        self.arn = arn
        self.principalId = principalId
        self.accountId = accountId


class SessionIssuerFactory(Factory):
    class Meta:
        model = SessionIssuer

    userName = FuzzyText()
    type = 'Role'
    arn = 'arn:aws:iam::123456789012:role/historical_poller'
    principalId = 'AROAIKELBS2RNWG7KASDF'
    accountId = '123456789012'


class UserIdentity(object):
    def __init__(self, sessionContext, principalId, type):
        self.sessionContext = sessionContext
        self.principalId = principalId
        self.type = type


class UserIdentityFactory(Factory):
    class Meta:
        model = UserIdentity

    sessionContext = SubFactory(SessionIssuerFactory)
    principalId = 'AROAIKELBS2RNWG7KASDF:joe@example.com'
    type = 'Service'


class SQSData(object):
    def __init__(self, messageId, receiptHandle, body):
        self.messageId = messageId
        self.receiptHandle = receiptHandle
        self.body = body
        self.eventSource = "aws:sqs"


class SQSDataFactory(Factory):
    class Meta:
        model = SQSData

    body = FuzzyText()
    messageId = FuzzyText()
    receiptHandle = FuzzyText()


class SQSRecord(object):
    def __init__(self, sqs):
        self.sqs = sqs


class Records(object):
    def __init__(self, records):
        self.Records = records


class RecordsFactory(Factory):
    """Factory for generating multiple Event (SNS, CloudWatch, Kinesis, DynamoDB) records."""
    class Meta:
        model = Records

    @post_generation
    def Records(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of groups were passed in, use them
            for record in extracted:
                self.Records.append(record)


class DynamoDBData(object):
    def __init__(self, NewImage, OldImage, Keys):
        self.OldImage = {k: seria.serialize(v) for k, v in OldImage.items()}
        self.NewImage = {k: seria.serialize(v) for k, v in NewImage.items()}
        self.Keys = {k: seria.serialize(v) for k, v in Keys.items()}


class DynamoDBDataFactory(Factory):
    class Meta:
        model = DynamoDBData

    NewImage = {}
    Keys = {}
    OldImage = {}


class DynamoDBRecord(object):
    def __init__(self, dynamodb, eventName, userIdentity):
        self.dynamodb = dynamodb
        self.eventName = eventName
        self.userIdentity = userIdentity


class DynamoDBRecordFactory(Factory):
    """Factory generating a DynamoDBRecord"""
    class Meta:
        model = DynamoDBRecord

    dynamodb = SubFactory(DynamoDBDataFactory)
    eventName = 'INSERT'
    userIdentity = SubFactory(UserIdentityFactory)


class DynamoDBRecordsFactory(Factory):
    class Meta:
        model = Records

    @post_generation
    def Records(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of groups were passed in, use them
            for record in extracted:
                self.Records.append(record)


class Event(object):
    def __init__(self, account, region, time):
        self.account = account
        self.region = region
        self.time = time


class EventFactory(Factory):
    """Parent class for all event factories."""
    class Meta:
        model = Event

    account = '123456789012'
    region = 'us-east-1'
    time = FuzzyDateTime(datetime.datetime.utcnow().replace(tzinfo=pytz.utc))


class Detail(object):
    def __init__(self, eventTime, awsEventType, awsRegion, eventName, userIdentity, id, eventSource, requestParameters):
        self.eventTime = eventTime
        self.awsRegion = awsRegion
        self.awsEventType = awsEventType
        self.userIdentity = userIdentity
        self.id = id
        self.eventSource = eventSource
        self.requestParameters = requestParameters
        self.eventName = eventName


class DetailFactory(Factory):
    class Meta:
        model = Detail

    eventTime = FuzzyDateTime(datetime.datetime.utcnow().replace(tzinfo=pytz.utc, microsecond=0))
    awsEventType = 'AwsApiCall'
    userIdentity = SubFactory(UserIdentityFactory)
    id = FuzzyText()
    eventName = ''
    requestParameters = dict()
    eventSource = 'aws.ec2'
    awsRegion = 'us-east-1'


class CloudwatchEvent(Event):
    def __init__(self, detail, account, region, time):
        self.detail = detail
        super().__init__(account, region, time)


class CloudwatchEventFactory(EventFactory):
    """Factory for generating cloudwatch events"""
    class Meta:
        model = CloudwatchEvent

    detail = SubFactory(DetailFactory)


class HistoricalPollingEvent(Event):
    def __init__(self, detail, account, region, time):
        self.detail = detail
        super().__init__(account, region, time)


class HistoricalPollingEventFactory(CloudwatchEventFactory):
    """Factory for generating historical polling events"""
    class Meta:
        model = HistoricalPollingEvent

    detail = SubFactory(DetailFactory)


class SnsData:
    def __init__(self, Message, EventSource, EventVersion, EventSubscriptionArn):
        self.Message = Message
        self.EventSource = EventSource
        self.EventVersion = EventVersion
        self.EventSubscriptionArn = EventSubscriptionArn


class SnsDataFactory(Factory):
    class Meta:
        model = SnsData
    Message = FuzzyText()
    EventVersion = FuzzyText()
    EventSource = "aws:sns"
    EventSubscriptionArn = FuzzyText()
