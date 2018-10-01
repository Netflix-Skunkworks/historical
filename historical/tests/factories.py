# pylint: disable=R0205,E1101,C0103,W0622,W0613
"""
.. module: historical.tests.factories
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
.. author:: Mike Grima <mgrima@netflix.com>
"""
import datetime

from boto3.dynamodb.types import TypeSerializer
from factory import SubFactory, Factory, post_generation  # pylint: disable=E0401
from factory.fuzzy import FuzzyDateTime, FuzzyText  # pylint: disable=E0401
import pytz  # pylint: disable=E0401

SERIA = TypeSerializer()


def serialize(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime.datetime):
        serial = obj.replace(microsecond=0).replace(tzinfo=None).isoformat() + "Z"
        return serial

    if isinstance(obj, bytes):
        return obj.decode('utf-8')

    return obj.__dict__


class SessionIssuer(object):
    """Model for the Session Issuer in the CloudWatch Event"""

    def __init__(self, userName, type, arn, principalId, accountId):
        self.userName = userName
        self.type = type
        self.arn = arn
        self.principalId = principalId
        self.accountId = accountId


class SessionIssuerFactory(Factory):
    """Generates the Session Issuer component of the CloudWatch Event"""

    class Meta:
        """Defines the Model"""

        model = SessionIssuer

    userName = FuzzyText()
    type = 'Role'
    arn = 'arn:aws:iam::123456789012:role/historical_poller'
    principalId = 'AROAIKELBS2RNWG7KASDF'
    accountId = '123456789012'


class UserIdentity(object):
    """Model for the User Identity component of the CloudWatch Event"""

    def __init__(self, sessionContext, principalId, type):
        self.sessionContext = sessionContext
        self.principalId = principalId
        self.type = type


class UserIdentityFactory(Factory):
    """Generates the User Identity component of the CloudWatch Event"""

    class Meta:
        """Defines the Model"""

        model = UserIdentity

    sessionContext = SubFactory(SessionIssuerFactory)
    principalId = 'AROAIKELBS2RNWG7KASDF:joe@example.com'
    type = 'Service'


class SQSData(object):
    """Model for an SQS Event Message"""

    def __init__(self, messageId, receiptHandle, body):
        self.messageId = messageId
        self.receiptHandle = receiptHandle
        self.body = body
        self.eventSource = "aws:sqs"


class SQSDataFactory(Factory):
    """Generates the SQS Event Message"""

    class Meta:
        """Defines the Model"""

        model = SQSData

    body = FuzzyText()
    messageId = FuzzyText()
    receiptHandle = FuzzyText()


class SQSRecord(object):
    """Model for an individual SQS Event Record"""

    def __init__(self, sqs):
        self.sqs = sqs


class Records(object):
    """Generic Model for multiple Records for an event source (DynamoDB, SQS, SNS, etc.)"""

    def __init__(self, records):
        self.Records = records


class RecordsFactory(Factory):
    """Factory for generating multiple Event (SNS, CloudWatch, Kinesis, DynamoDB, SQS) records."""

    class Meta:
        """Defines the Model"""

        model = Records

    @post_generation
    def Records(self, create, extracted, **kwargs):
        """Generates the Records"""
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of groups were passed in, use them
            for record in extracted:
                self.Records.append(record)


class DynamoDBData(object):
    """Model for the DynamoDB Stream data itself"""

    def __init__(self, NewImage, OldImage, Keys):
        self.OldImage = {k: SERIA.serialize(v) for k, v in OldImage.items()}
        self.NewImage = {k: SERIA.serialize(v) for k, v in NewImage.items()}
        self.Keys = {k: SERIA.serialize(v) for k, v in Keys.items()}


class DynamoDBDataFactory(Factory):
    """DynamoDB Stream Data Component Model"""

    class Meta:
        """Defines the Model"""

        model = DynamoDBData

    NewImage = {}
    Keys = {}
    OldImage = {}


class DynamoDBRecord(object):
    """DynamoDB Stream Model"""

    def __init__(self, dynamodb, eventName, userIdentity):
        self.dynamodb = dynamodb
        self.eventName = eventName
        self.userIdentity = userIdentity


class DynamoDBRecordFactory(Factory):
    """Factory generating a DynamoDBRecord"""

    class Meta:
        """Defines the Model"""

        model = DynamoDBRecord

    dynamodb = SubFactory(DynamoDBDataFactory)
    eventName = 'INSERT'
    userIdentity = SubFactory(UserIdentityFactory)


class DynamoDBRecordsFactory(Factory):
    """Factory to generate DynamoDB Stream Events"""

    class Meta:
        """Defines the Model"""

        model = Records

    @post_generation
    def Records(self, create, extracted, **kwargs):
        """Generates the proper records"""
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of groups were passed in, use them
            for record in extracted:
                self.Records.append(record)


class Event(object):
    """The base of the Event Model"""

    def __init__(self, account, region, time):
        self.account = account
        self.region = region
        self.time = time


class EventFactory(Factory):
    """Parent class for all event factories."""

    class Meta:
        """Defines the Model"""

        model = Event

    account = '123456789012'
    region = 'us-east-1'
    time = FuzzyDateTime(datetime.datetime.utcnow().replace(tzinfo=pytz.utc))


class Detail(object):
    """The CloudWatch Event `detail` Model"""

    # pylint: disable=W0622,R0902
    def __init__(self, eventTime, awsEventType, awsRegion, eventName, userIdentity, id, eventSource,
                 requestParameters, responseElements, collected=None):
        self.eventTime = eventTime
        self.awsRegion = awsRegion
        self.awsEventType = awsEventType
        self.userIdentity = userIdentity
        self.id = id
        self.eventSource = eventSource
        self.requestParameters = requestParameters
        self.responseElements = responseElements
        self.eventName = eventName
        self.collected = collected


class DetailFactory(Factory):
    """Factory for making the CloudWatch Event `detail` component"""

    class Meta:
        """Defines the Model"""

        model = Detail

    eventTime = FuzzyDateTime(datetime.datetime.utcnow().replace(tzinfo=pytz.utc, microsecond=0))
    awsEventType = 'AwsApiCall'
    userIdentity = SubFactory(UserIdentityFactory)
    id = FuzzyText()
    eventName = ''
    requestParameters = dict()
    responseElements = dict()
    eventSource = 'aws.ec2'
    awsRegion = 'us-east-1'
    collected = None


class CloudwatchEvent(Event):
    """The CloudWatch Event Model"""

    def __init__(self, detail, account, region, time):
        self.detail = detail
        super().__init__(account, region, time)


class CloudwatchEventFactory(EventFactory):
    """Factory for generating CloudWatch Events"""

    class Meta:
        """Defines the Model"""

        model = CloudwatchEvent

    detail = SubFactory(DetailFactory)


class HistoricalPollingEvent(Event):
    """Polling Event Model"""

    def __init__(self, detail, account, region, time):
        self.detail = detail
        super().__init__(account, region, time)


class HistoricalPollingEventFactory(CloudwatchEventFactory):
    """Factory for generating historical polling events"""

    class Meta:
        """Defines the model"""

        model = HistoricalPollingEvent

    detail = SubFactory(DetailFactory)


class SnsData:
    """SNS Event model"""

    def __init__(self, Message, EventSource, EventVersion, EventSubscriptionArn):
        self.Message = Message
        self.EventSource = EventSource
        self.EventVersion = EventVersion
        self.EventSubscriptionArn = EventSubscriptionArn


class SnsDataFactory(Factory):
    """SNS Event Model Factory"""

    class Meta:
        """Defines the model"""

        model = SnsData

    Message = FuzzyText()
    EventVersion = FuzzyText()
    EventSource = "aws:sns"
    EventSubscriptionArn = FuzzyText()
