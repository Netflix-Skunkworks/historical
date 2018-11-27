# Historical Architecture
Historical is a serverless AWS application that consists of many components.

Historical is written in Python 3 and heavily leverages AWS technologies such as Lambda, SNS, SQS, DynamoDB, CloudTrail, and CloudWatch.

## General Architectural Overview
Here is a diagram of the Historical Architecture:
<a href="../img/historical-overview.jpg"><img src="../img/historical-overview.jpg"></a>

**Please Note:** This stack is deployed _for every technology monitored_! There are many, many Historical stacks that will be deployed.

### Polling vs. Events
Historical is *both* a polling and event driven system. It will periodically poll AWS accounts for changes. However, because Historical responds to events in the environment, polling doesn't need to be very aggressive and only happens once every few hours.

Polling is necessary because events are not 100% reliable. This ensures that data is current just in case an event is dropped.

Historical is *eventually consistent*, and makes a *best effort* to maintain a current and up-to-date inventory of AWS resources.

## Prerequisite Overview

This is a high-level overview of the prerequisites that are required to make Historical operate. For more details on setting up the required prerequisites, please review the [installation documentation](../installation).

1. **ALL AWS accounts** accounts have CloudTrail enabled.
1. **ALL AWS accounts** and **ALL regions** in those accounts have a CloudWatch Event rule that captures ALL events and sends them over the CloudWatch Event Bus to the Historical account for processing.
1. IAM roles exist in **ALL** accounts and are assumable by the Historical Lambda functions.
1. Historical makes use of [SWAG](https://github.com/Netflix-Skunkworks/swag-client) to define which AWS accounts Historical is enabled for. While not a hard requirement, use of SWAG is _highly recommended_.

## Regions
Historical has the concept of regions that fit 3 categories:

- Primary region
- Secondary region(s)
- Off region(s)

The **Primary Region** is considered the "Base" of Historical. This region has all of the major components that make up Historical. This region processes all in-region AND off-region originating events.

The **Off Region(s)** are regions you don't have a lot of infrastructure deployed in. However, you still want visibility in these regions should events happen there. These regions have very minimal amount of Historical-related infrastructure deployed. These regions will forward ALL events to the Primary Region for processing.

The **Secondary Region(s)** are regions that are important to you. Secondary regions look like the primary region and process in-region events. If you have a lot of infrastructure within a region, you should place a Historical stack there. This will allow you to quickly receive and process events, and also gives your applications a regionally-local means of accessing Historical data.

**Note:** Place a Historical off-region stack in any region that is not Primary or Secondary. This will ensure full visibility in your environment.

## Component Overview
This section describes some of the high-level architectural components.

### Primary Components
Below are the primary components of the Historical architecture:

1. CloudWatch Event Rules
1. CloudWatch Change Events
1. Poller
1. Collector
1. Current Table
1. DynamoDB Stream Proxy
1. Differ
1. Durable Table
1. Off-region SNS forwarders

As general overview, the infrastructure is an event processing and enriching pipeline. An event will arrive, will get enriched with additional information, and will provide notifications to downstream subscribers on the given changes.

SQS queues are used in as many places as much as possible to invoke Lambda functions. SQS makes it easy to provide Lambda execution concurrency, auto-scaling, retry of failures without blocking, and dead-letter queuing capabilities.

SNS topics are used to make it easy for _N_ number of interested parties to subscribe to the Historical DynamoDB table changes. Presently, this is only attached to the Durable table. More details on this below.

### CloudWatch Event Rules
There are two different CloudWatch Event Rules:

1. Timed Events
1. Change Events

Timed events are used to kick off the Poller. See the section on the poller below for additional details. Change events are events that arrive from CloudWatch Events when an AWS resource's configuration changes.

### Poller
The Poller's primary function is to obtain a full inventory of AWS resources.

The Poller is split into two parts:

1. Poller Tasker
1. Poller

The "Poller Tasker" is a Lambda function that iterates over all AWS accounts Historical is configured for, and tasks the Poller to *list* all resources in the given environment.

The Poller Tasker in the *PRIMARY REGION* tasks the Poller to list resources that reside in the primary region and all off-regions. A Poller Tasker in a *SECONDARY REGION* will only task a poller to describe resources that reside in the same region.

The Poller *lists* all resources in a given account/region, and tasks a "Poller Collector" to fetch details about the resource in question.

### Collector
The Collector describes a given AWS resource and stores its configuration to the "Current" DynamoDB table. The Collector is split into two parts (same code, different invocation mechanisms):

1. Poller Collector
1. Event Collector

The Poller Collector is a collector that will only respond to polling events. The Event Collector will only respond to CloudWatch change events.

The Collector is split into two parts to prevent change events from being sandwiched in between polling events. Historical gives priority to change events over polling events to ensure timeliness of resource configuration changes.

In both cases, the Collector will go to the AWS account and region that the item resides in, and use `boto3` to describe the configuration of the resource.

### Current Table
The "Current" table is a global DynamoDB table that stores the current configuration of a given resource in
AWS.

This acts as a cache for current the state of the environment.

The Current table has as DynamoDB Stream that will kick off a DynamoDB Stream Proxy that then invokes the Differ.

#### Special Note:
The Current table has a TTL set on all items. This TTL is updated any time a change event arrives, or when the Poller runs. The TTL is set to clean-up orphaned items, which can happen if a deletion event is lost. Deleted items will not be picked up by the Poller (only lists items that exist in the account) and thus, will be removed from the Current table on TTL expiration. As a result, the Poller must "see" a resource at least once every few hours before it is deemed deleted from the environment.

### DynamoDB Stream Proxy
The DynamoDB Stream Proxy is a Lambda function that proxies DynamoDB Stream events to SNS or SQS. The purpose is to task subsequent Lambda functions on the specific changes that happen to the DynamoDB table.

The Historical infrastructure has two configurations for the DynamoDB Proxy:

1. Current Table Forwarder (DynamoDB Stream Proxy to Differ SQS)
1. Durable Table Forwarder (DynamoDB Stream Proxy to Change Notification SNS)

The Current Table Forwarder proxies events to the SQS queue that invokes the Differ Lambda function.

The Durable Table Forwarder proxies events to an SNS topic that can be subscribed. SNS enables *N* subscribers to Historical events. The Durable table proxy serializes the DynamoDB Stream events into an easily consumable JSON that contains the full and complete configuration of the resource in question, along with the the CloudTrail context. This enables downstream applications to make intelligent decisions about the changes that occur as they have the full and complete context of the resource and the changes made to it.

#### Special Note:
DynamoDB Streams in Global DynamoDB tables invoke this Lambda whenever a DynamoDB update occurs in ANY of the regions the table is configured to sync with. For the Current table, this can result in Historical Lambda functions _"stepping on each other's toes"_ (this is not a concern for Durable table changes). To avoid this, the Current table DynamoDB Stream Proxy has a `PROXY_REGIONS` environment variable that is configured to only proxy DynamoDB Stream updates that occur to resources that reside in the specified regions. The *PRIMARY REGION* must be configured to proxy events that occur in the primary region, and all off-regions. The *SECONDARY REGION(S)* must be configured to proxy events that occur in the same region.

#### Another Special Note:
DynamoDB items are capped to 400KB. SNS and SQS have maximum message sizes of 256KB. Logic exists to handle cases where DynamoDB items are too big to send over to SNS/SQS. Follow-up Lambdas and subscribers will need to make use of the Historical code to fetch the full configuration of the item either out of the Current or Durable tables (depending on the use case). Enhancements will be made in the future to help address this to make the data easier to consume in these (rare) circumstances.

### Differ
The Differ is a Lambda function that gets invoked upon changes to the Current table. The DynamoDB stream provides the Differ (via the Proxy) the current state of the resource that changed. The Differ checks if the resource in question has had an effective change. If so, the Differ saves a new change record to the Durable table to maintain history of the resource as it changes over time, and also saves the CloudTrail context.

### Durable Table
The "Durable" table is a Global DynamoDB table that stores a resource configuration with change history.

The Durable table has as DynamoDB Stream that invokes another DynamoDB Stream Proxy. This is used to notify downstream subscribers of the effective changes that occur to the environment.

### Off-Region SNS Forwarders
Very bare infrastructure is intentionally deployed in the off-regions. This helps to reduce costs and complexity of the Historical infrastructure.

The off-region SNS forwarders are SNS topics that receive CloudWatch events for resource changes that occur in the off-regions. These topics forward events to the Event Collector SQS queue in the primary region for processing.

## Special Stacks
Some resource types have different stack configurations due to nuances of the resource type.

The following resource types have different stack types:

- S3
- IAM (Coming Soon!)

### S3
The AWS S3 stack is almost identical to the standard stack. The difference is due to AWS S3 buckets having a globally unique namespace.

For S3, because it is not presently possible to only poll for in-region S3 buckets, the poller lives in the primary region only. The poller in the primary region polls for all S3 buckets in all regions.

The secondary regions will still respond to in-region events, but lack all polling components.

<a href="../img/historical-s3.jpg">This diagram showcases the S3 stack.</a>

### IAM
This is coming soon!

## Installation & Configuration

Please refer to the [installation docs](../installation) for additional details.
