# Historical Environment Variables & Configuration

Below is a reference of all of the environment variables that Historical makes use of, and the required/default status of them:

Most of these variables are found in:

- [`historical/constants.py`](https://github.com/Netflix-Skunkworks/historical/blob/master/historical/constants.py)
- [`historical/mapping/__init__.py`](https://github.com/Netflix-Skunkworks/historical/blob/master/historical/mapping/__init__.py)

**NOTE: All environment variables are Strings**

## Required Fields
The fields below are required and **MUST** be configured by you in your Terraform templates:

| Variable | Where to set | Sample Value |
|:----------:|:-------------|:-------------|
|`PRIMARY_REGION`|Per-stack Terraform template<br />`variable PRIMARY_REGION`|`us-west-2`|
|`POLLING_REGIONS`|Per-stack Terraform template<br />`variable POLLING_REGIONS`|`["us-west-2", "us-east-1", "eu-west-1"]`<br />This should be set to the secondary regions for most stacks.<br /><br />S3 is the exception since it's a "global" namespace.<br />For S3, this is always set to the `PRIMARY_REGION`.<br /><br />This populates the `POLL_REGIONS` env. var for the<br />Poller Lambdas.|
|`REGION`|Infrastructure `main.tf`<br />This is a variable supplied<br />to Terraform in the<br />application of the template.|This value is used to determine if the current region<br />of the deployment is the primary region or a secondary region.|
|`PROXY_REGIONS`|Per-stack Terraform template<br />`current_proxy_env_vars` and `durable_proxy_env_vars`|`us-east-1,eu-west-1,us-east-2,etc.`<br />This is a comma-separated string of regions.<br /><br />The `current_proxy_env_vars` for the `PRIMARY_REGION` needs to be configured to contain the `PRIMARY_REGION` and all the "off-regions".<br /><br />The `durable_proxy_env_vars` should contain ALL<br />the regions (default).|
|`HISTORICAL_TECHNOLOGY`|Per-stack Terraform template<br />`durable_proxy_env_vars`|`s3` or `securitygroup`. This should be set in each sample stack properly.|
|`SIMPLE_DURABLE_PROXY`|Per-stack Terraform template<br />`durable_proxy_env_vars`|`True` - This is the default value for the Durable Proxy.<br />Don't change this.<br /><br />This value toggles whether the DynamoDB<br />stream events will be serialized nicely for downstream consumption or not.|
|`ENABLED_ACCOUNTS`|Per-stack Terraform template<br />`env_vars`|`ACCOUNTID1,ACCOUNTID2,etc.`<br />If you are not making use of [SWAG](https://github.com/Netflix-Skunkworks/swag-client), then you need to set this.|
|`SWAG_BUCKET`|Per-stack Terraform template<br />`env_vars`|`some-s3-bucket-name`<br />Required if you are making use of [SWAG](https://github.com/Netflix-Skunkworks/swag-client).|
|`SWAG_DATA_FILE`|Per-stack Terraform template<br />`env_vars`|`v2/accounts.json`<br />Required if you are making use of [SWAG](https://github.com/Netflix-Skunkworks/swag-client).<br />Points to where the `accounts.json` file is located.|
|`SWAG_OWNER`|Per-stack Terraform template<br />`env_vars`|`yourcompany`<br />Required if you are making use of [SWAG](https://github.com/Netflix-Skunkworks/swag-client).<br />The entity that owns the accounts you are monitoring.|
|`SWAG_REGION`|Per-stack Terraform template<br />`env_vars`|`us-west-2`<br />Required if you are making use of [SWAG](https://github.com/Netflix-Skunkworks/swag-client).<br />The region the `SWAG_BUCKET` is located.|

### Default Required Fields
These are fields that are required, but the default values are sufficient. These are not set in the Terraform templates.

| Variable | Description & Defaults |
|:----------:|:-------------|
|`CURRENT_REGION`|This is populated by the `AWS_DEFAULT_REGION` environment variable provided by Lambda. This will be set to the region that the Lambda function is running in.|
|`TTL_EXPIRY`|Default: `86400` seconds. This is the TTL for an item in the Current Table. This is used to account for missing deletion events.|
|`HISTORICAL_ROLE`|Default: `Historical`. Don't change this -- this is the name of the IAM role that Historical needs to assume to describe resources.|
|`REGION_ATTR`|Default: `Region`. Don't change this -- this is the name of the region attribute in the DynamoDB table.|
|`EVENT_TOO_BIG_FLAG`|Default: `event_too_big`. Don't change this -- this is a field name that informs Historical downstream functions if an event is too big to fit in SNS and SQS (>256KB).|

## Optional Fields

| Variable | Where to set | Sample Value |
|:----------:|:-------------|:-------------|
|`RANDOMIZE_POLLER`|Per-stack Terraform template<br />`poller_env_vars`|0 <= value <= 900. Number of seconds to delay<br />Polling messages in SQS.<br /><br />It is recommended you set this to `"900"` for the Poller.|
|`LOGGING_LEVEL`|Per-stack Terraform template<br />`env_vars`|[Any one of these values](https://github.com/Netflix-Skunkworks/historical/blob/master/historical/constants.py#L13-L17). `DEBUG` is recommended.|
|`TEST_ACCOUNTS_ONLY`|Per-stack Terraform template<br />`env_vars`|Default `False`. This is used if you are making use of [SWAG](https://github.com/Netflix-Skunkworks/swag-client).<br /><br />Set this to `True` if you want your stack to _ONLY_ query<br />against "test" accounts. Useful for having<br />"test" and "prod" stacks.|
|`PROXY_BATCH_SIZE`|Per-stack Terraform template<br />`current_proxy_env_vars`.|Default: `10`. Set this if the batched event size is too<br />big (>256KB) to send to SQS. This should be refactored<br />in the future so that this is not necessary.|
|`SENTRY_DSN`|Per-stack Terraform template<br />`env_vars`|If you make use of [Sentry](https://sentry.io/), then set this to your DSN.<br /><br />Historical makes use of the [`raven-python-lambda`](https://github.com/Netflix-Skunkworks/raven-python-lambda) for Sentry.<br />You can also optionally use SQS as a transport layer for<br />Sentry messages via [`raven-sqs-proxy`](https://github.com/Netflix-Skunkworks/raven-sqs-proxy).|
|Custom Tags|Per-stack Terraform template<br />`tags`|Add in a name-value pair of tags you want to affix<br />to your Lambda functions.|


## Docker Installer Specific Fields
The fields below are specific for installation and uninstallation of Historical via the Docker container.  These values are present in the [`terraform/SAMPLE-env.list`](https://github.com/Netflix-Skunkworks/historical/blob/master/terraform/SAMPLE-env.list) file.

**ALL FIELDS BELOW ARE REQUIRED**

| Variable | Sample Value |
|:----------:|:-------------|
|`AWS_ACCESS_KEY_ID`|The AWS Access Key ID for the credential that will be used to run Terraform. This is for a very powerful IAM Role.|
|`AWS_SECRET_ACCESS_KEY`|The AWS Secret Access Key for the credential that will be used to run Terraform. This is for a very powerful IAM Role.|
|`AWS_SESSION_TOKEN`|The AWS Session Token for the credential that will be used to run Terraform. This is for a very powerful IAM Role.|
|`TECH`|The Historical resource type for the stack in question. Either `s3` or `securitygroup` (for now).|
|`PRIMARY_REGION`|The Primary Region of your Historical Stack.|
|`SECONDARY_REGIONS`|The Secondary Regions of your Historical Stack. This is a comma separated string.|


## Next Steps
[Please return to the Installation documentation](../).
