// Declare variables for the Security Group Stack:
variable "PRIMARY_REGION" {
  default = "us-west-2"
}

// Define the regions to place the poller infrastructure here:
variable "POLLING_REGIONS" {
  type = "list"

  default = ["us-west-2", "us-east-1", "eu-west-1"]
}

// Define the CloudWatch Event configuration:
data "null_data_source" "cwe_config" {
  inputs = {
    off_regions_sns_name = "HistoricalSecurityGroupCWEForwarder"

    rule_name         = "HistoricalSecurityGroupCloudWatchEventRule"
    rule_desc         = "EventRule forwarding Security Group changes."

    poller_rule_name  = "HistoricalSecurityGroupPollerEventRule"
    poller_rule_desc  = "EventRule for Polling Security Groups."
    poller_rule_rate  = "rate(6 hours)"

    sqs_poller_tasker_queue     = "HistoricalSecurityGroupPollerTasker"
    sqs_event_queue             = "HistoricalSecurityGroupEvents"
    sqs_poller_collector_queue  = "HistoricalSecurityGroupPoller"
    differ_queue                = "HistoricalSecurityGroupDiffer"

    rule_target_name  = "HistoricalSecurityGroupEventsToSQS"

    // Event Syntax:
    event_pattern = <<PATTERN
{
    "source": [
        "aws.ec2"
    ],
    "detail-type": [
        "AWS API Call via CloudTrail"
    ],
    "detail": {
        "eventSource": [
            "ec2.amazonaws.com"
        ],
        "eventName": [
            "AuthorizeSecurityGroupEgress",
            "AuthorizeSecurityGroupIngress",
            "CreateSecurityGroup",
            "DeleteSecurityGroup",
            "RevokeSecurityGroupEgress",
            "RevokeSecurityGroupIngress",
            "UpdateSecurityGroupRuleDescriptionsEgress",
            "UpdateSecurityGroupRuleDescriptionsIngress"
        ]
    }
}
PATTERN
  }
}

// Lambda function configuration:
data "null_data_source" "lambda_function_config" {
  inputs = {
    lambda_name     = "historical-securitygroup"
    lambda_memory   = "256"

    poller_tasker_handler = "historical.security_group.poller.poller_tasker_handler"
    poller_tasker_desc    = "Lambda that tasks the poller for Security Groups."

    poller_handler  = "historical.security_group.poller.poller_processor_handler"
    poller_desc     = "Lambda that polls for changes in Security Groups."

    collector_handler     = "historical.security_group.collector.handler"
    collector_desc        = "Processes polling and cloudwatch events for Security Groups."
    collector_concurrency = -1  // You can set this if you want to limit the number of concurrent executions.

    differ_handler  = "historical.security_group.differ.handler"
    differ_desc     = "Stream based function that is resposible for finding differences."
  }
}

// Lambda function tags:
data "null_data_source" "tags" {
  inputs = {
    owner = "yourteam@yourcompany.com"  // Feel free to add tags here.
  }
}

// Lambda Env Vars:
data "null_data_source" "env_vars" {
  inputs = {
    // For SWAG, see: https://github.com/Netflix-Skunkworks/swag-client (THIS IS HIGHLY RECOMMENDED)
    # SWAG_BUCKET    = "YOUR-SWAG-BUCKET-HERE"
    # SWAG_DATA_FILE = "v2/accounts.json"
    # SWAG_OWNER     = "YOURCOMPANY"
    # SWAG_REGION    = "YOUR SWAG BUCKET REGION"

    //SENTRY_DSN     =  "YOUR SENTRY DSN HERE." -- You can also use https://github.com/Netflix-Skunkworks/raven-sqs-proxy

    // IF YOU'RE NOT USING SWAG: YOU NEED TO SPECIFY THE ENABLED ACCOUNT ID'S HERE:
    ENABLED_ACCOUNTS = "YOURACCOUNTIDHERE,YOURSECONDACCOUNTHERE,ETC"   // CSV
    LOGGING_LEVEL    = "DEBUG"
  }
}

// Poller Env Vars:
data "null_data_source" "poller_env_vars" {
  inputs = {
    // The primary region (us-west-2 in this example) needs to specify all regions (minus the Secondary Regions) including itself.
    // The Secondary Regions will only poll within region.
    POLL_REGIONS        = "${var.REGION == "us-west-2" ? "us-east-2,us-west-1,us-west-2,ap-northeast-1,ap-northeast-2,ap-south-1,ap-southeast-1,ap-southeast-2,ca-central-1,eu-central-1,eu-west-2,eu-west-3,sa-east-1" : var.REGION}"
    RANDOMIZE_POLLER    = "900"
    TEST_ACCOUNTS_ONLY  = "False"   // Used with SWAG above -- This allows you to only run against "test" accounts.
  }
}

// Collector Env Vars:
data "null_data_source" "collector_env_vars" {
  inputs = {}
}

// Current Table Proxy Env Vars:
data "null_data_source" "current_proxy_env_vars" {
  inputs = {
    // The primary region (us-west-2 in this example) needs to specify all regions (minus the Secondary Regions) including itself.
    // The Secondary Regions will only process events that occur within region.
    PROXY_REGIONS = "${var.REGION == "us-west-2" ? "us-east-2,us-west-1,us-west-2,ap-northeast-1,ap-northeast-2,ap-south-1,ap-southeast-1,ap-southeast-2,ca-central-1,eu-central-1,eu-west-2,eu-west-3,sa-east-1" : var.REGION}"
  }
}

// Differ Env Vars:
data "null_data_source" "differ_env_vars" {
  inputs = {}
}

// Durable Table Proxy Env Vars:
data "null_data_source" "durable_proxy_env_vars" {
  inputs = {
    // This should contain all regions -- this allows downstream subscribers to receive events.
    PROXY_REGIONS = "us-east-1,eu-west-1,us-east-2,us-west-1,us-west-2,ap-northeast-1,ap-northeast-2,ap-south-1,ap-southeast-1,ap-southeast-2,ca-central-1,eu-central-1,eu-west-2,eu-west-3,sa-east-1"
  }
}

// Proxy Configuration:
data "null_data_source" "proxy_configs" {
  inputs = {
    durable_sns_proxy = "HistoricalSecurityGroupDurableProxy"
  }
}

// Current DynamoDB Table:
data "aws_dynamodb_table" "current-table" {
  name = "HistoricalSecurityGroupCurrentTable"
}

// Current DynamoDB Table:
data "aws_dynamodb_table" "durable-table" {
  name = "HistoricalSecurityGroupDurableTable"
}
