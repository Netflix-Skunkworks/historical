<div style="display: flex; align-items: baseline">
<img src="img/historical.jpg" style="max-height: 250px; padding-right: 10px"><h1>Historical<h1>
</div>

<h2 style="color: red">This project is in very active development and is not yet ready for production use!</h2>

Historical is a serverless application that tracks and reacts to AWS resource modifications anywhere in
your environment. Historical achieves this by describing AWS resources when they are changed, and keeping the history of those changes along with the the CloudTrail context of those changes.

Historical persists data in two places:

- A "Current" DynamoDB table, which is a cache of the current state of AWS resources
- A "Durable" DynamoDB table, which stores the change history of AWS resources

Historical enables downstream consumers to react to changes in the AWS environment
without the need to directly describe the resource. This greatly increases speed of reaction, reduces IAM permission complexity, and also avoids rate limiting.

## How it works
Historical leverages AWS CloudWatch Events. Events trigger a "Collector" Lambda function to describe the AWS resource that changed, and saves the configuration into a DynamoDB table. From this, a "Differ" Lambda function checks if the resource has changed from what was previously known about that resource. If the item has changed, a new change record is saved, which then enables downstream consumers the ability to react to changes in the environment as the environment effectively changes over time.

The CloudTrail context on the change is preserved in the change history.

## Current Technologies Implemented

- ### S3
- ### Security Groups
- ### IAM (In active development -- Coming Soon!)

## Architecture
Please review the [Architecture](architecture.md) documentation for an in-depth description of the components involved.

## Installation & Configuration
Please review the [Installation & Configuration](installation/) documentation for details.

## Troubleshooting
Please review the [Troubleshooting](troubleshooting.md) doc if you are experiencing issues.
