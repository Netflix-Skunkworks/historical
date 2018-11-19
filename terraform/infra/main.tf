terraform {
  backend "s3" {
    // SET THIS TO YOUR PRIMARY REGION:
    region = "us-west-2"
  }
}
// ----------------------------

// Set up Providers:
provider "aws" {
  version = "1.39"

  region = "${var.REGION}"
}

provider "local" {
  version = "1.1"
}

provider "null" {
  version = "1.0"
}
// -------------------------

// Required from the CMD line:
variable "REGION" {}
// ----------------------------

data "aws_caller_identity" "current" {}
// ----------------------------

// SQS event receiver (for invoking the Collector lambda whenever a CloudWatch Event arrives):
resource "aws_sqs_queue" "sqs_event_queue" {
  name        = "${data.null_data_source.cwe_config.outputs["sqs_event_queue"]}"

  visibility_timeout_seconds = 301
}

resource "aws_sqs_queue_policy" "sqs_event_queue_policy" {
  queue_url = "${aws_sqs_queue.sqs_event_queue.id}"

  policy    = <<PATTERN
{
    "Version": "2012-10-17",
    "Id": "CloudWatchEventsReceiver",
    "Statement": [
        {
            "Resource": "arn:aws:sqs:${var.REGION}:${data.aws_caller_identity.current.account_id}:${aws_sqs_queue.sqs_event_queue.name}",
            "Effect": "Allow",
            "Sid": "CloudWatchEvents",
            "Action": "SQS:SendMessage",
            "Principal": {
                "Service": "events.amazonaws.com"
            }
        },
        {
            "Resource": "arn:aws:sqs:${var.REGION}:${data.aws_caller_identity.current.account_id}:${aws_sqs_queue.sqs_event_queue.name}",
            "Effect": "Allow",
            "Sid": "CloudWatchEvents",
            "Action": "SQS:SendMessage",
            "Condition": {
                "ArnEquals": {
                    "aws:SourceArn": "arn:aws:sns:*:${data.aws_caller_identity.current.account_id}:${data.null_data_source.cwe_config.outputs["off_regions_sns_name"]}"
                }
            },
            "Principal": {
                "AWS": "*"
            }
        }
    ]
}
PATTERN
}

// SQS Poller Tasker (invokes the Poller Lambda for listing all resources in the given account):
resource "aws_sqs_queue" "sqs_poller_tasker_queue" {
  count  = "${contains(var.POLLING_REGIONS, var.REGION) ? 1 : 0}"

  name   = "${data.null_data_source.cwe_config.outputs["sqs_poller_tasker_queue"]}"
  visibility_timeout_seconds = 301
}

// SQS Poller-Collector Queue (invokes the Collector from the Poller):
resource "aws_sqs_queue" "sqs_poller_collector_queue" {
  count = "${contains(var.POLLING_REGIONS, var.REGION) ? 1 : 0}"

  name  = "${data.null_data_source.cwe_config.outputs["sqs_poller_collector_queue"]}"

  visibility_timeout_seconds = 301
}

// SQS Differ-Launcher Queue (invokes the Differ from DynamoDB Stream events off of the Current table):
resource "aws_sqs_queue" "differ_queue" {
  name  = "${data.null_data_source.cwe_config.outputs["differ_queue"]}"

  visibility_timeout_seconds = 301
}


// Durable Table Proxy Topic (SNS topic for downstream applications to subsribe to for events):
resource "aws_sns_topic" "durable_proxy" {
  name  = "${data.null_data_source.proxy_configs.outputs["durable_sns_proxy"]}"
}
// ----------------------------

// ------------ CLOUDWATCH EVENTS ----------------
// Create the Historical CloudWatch Event Rule:
resource "aws_cloudwatch_event_rule" "event_rule" {
  name        = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  description = "${data.null_data_source.cwe_config.outputs["rule_desc"]}"

  event_pattern = "${data.null_data_source.cwe_config.outputs["event_pattern"]}"
}

// Create the Poller Event Rule:
resource "aws_cloudwatch_event_rule" "poller_event_rule" {
  count               = "${contains(var.POLLING_REGIONS, var.REGION) ? 1 : 0}"

  name                = "${data.null_data_source.cwe_config.outputs["poller_rule_name"]}"
  description         = "${data.null_data_source.cwe_config.outputs["poller_rule_desc"]}"
  schedule_expression = "${data.null_data_source.cwe_config.outputs["poller_rule_rate"]}"
}

// Create the Target for CloudWatch Event Rule:
resource "aws_cloudwatch_event_target" "cwe_target" {
  rule        = "${aws_cloudwatch_event_rule.event_rule.name}"
  target_id   = "${data.null_data_source.cwe_config.outputs["rule_target_name"]}"
  arn         = "${aws_sqs_queue.sqs_event_queue.arn}"
}


// ------------ LAMBDA FUNCTIONS ----------------
// Cloudwatch Log Group for the Poller Tasker:
resource "aws_cloudwatch_log_group" "poller_tasker_log_group" {
  count             = "${contains(var.POLLING_REGIONS, var.REGION) ? 1 : 0}"

  name              = "/aws/lambda/${data.null_data_source.lambda_function_config.outputs["lambda_name"]}-poller-tasker"
  retention_in_days = 3
}

// Cloudwatch Log Group for the Poller:
resource "aws_cloudwatch_log_group" "poller_log_group" {
  count             = "${contains(var.POLLING_REGIONS, var.REGION) ? 1 : 0}"

  name              = "/aws/lambda/${data.null_data_source.lambda_function_config.outputs["lambda_name"]}-poller"
  retention_in_days = 3
}

// Cloudwatch Log Group for the Collector:
resource "aws_cloudwatch_log_group" "collector_log_group" {
  name              = "/aws/lambda/${data.null_data_source.lambda_function_config.outputs["lambda_name"]}-collector"
  retention_in_days = 3
}

// Cloudwatch Log Group for the Differ:
resource "aws_cloudwatch_log_group" "differ_log_group" {
  name              = "/aws/lambda/${data.null_data_source.lambda_function_config.outputs["lambda_name"]}-differ"
  retention_in_days = 3
}

// Cloudwatch Log Group for the Current Proxy:
resource "aws_cloudwatch_log_group" "current_proxy_log_group" {
  name              = "/aws/lambda/${data.null_data_source.lambda_function_config.outputs["lambda_name"]}-current-proxy"
  retention_in_days = 3
}

// Cloudwatch Log Group for the Durable Proxy:
resource "aws_cloudwatch_log_group" "durable_proxy_log_group" {
  name              = "/aws/lambda/${data.null_data_source.lambda_function_config.outputs["lambda_name"]}-durable-proxy"
  retention_in_days = 3
}

// Make the Poller Tasker:
resource "aws_lambda_function" "poller_tasker" {
  count             = "${contains(var.POLLING_REGIONS, var.REGION) ? 1 : 0}"
  depends_on        = ["aws_cloudwatch_log_group.poller_tasker_log_group"]

  function_name     = "${data.null_data_source.lambda_function_config.outputs["lambda_name"]}-poller-tasker"
  description       = "${data.null_data_source.lambda_function_config.outputs["poller_tasker_desc"]}"
  role              = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/HistoricalLambdaProfile"
  handler           = "${data.null_data_source.lambda_function_config.outputs["poller_tasker_handler"]}"
  filename          = "lambda.zip"
  source_code_hash  = "${base64sha256(file("lambda.zip"))}"
  runtime           = "python3.6"
  memory_size       = "${data.null_data_source.lambda_function_config.outputs["lambda_memory"]}"
  tags              = "${data.null_data_source.tags.outputs}"
  timeout           = 300

  environment {
    variables = "${merge(data.null_data_source.env_vars.outputs, data.null_data_source.poller_env_vars.outputs)}"
  }
}

// Poller-Tasker Permissions for CloudWatch Events:
resource "aws_lambda_permission" "allow_cloudwatch_poller" {
  count           = "${contains(var.POLLING_REGIONS, var.REGION) ? 1 : 0}"

  statement_id    = "AllowExecutionFromCloudWatch"
  action          = "lambda:InvokeFunction"
  function_name   = "${aws_lambda_function.poller_tasker.function_name}"
  principal       = "events.amazonaws.com"
  source_arn      = "${aws_cloudwatch_event_rule.poller_event_rule.arn}"
}

// Poller CloudWatch Events target for invocation:
resource "aws_cloudwatch_event_target" "poller_event_target" {
  count   = "${contains(var.POLLING_REGIONS, var.REGION) ? 1 : 0}"

  rule    = "${aws_cloudwatch_event_rule.poller_event_rule.name}"
  arn     = "${aws_lambda_function.poller_tasker.arn}"
}

// The Poller Lambda:
resource "aws_lambda_function" "poller" {
  count             = "${contains(var.POLLING_REGIONS, var.REGION) ? 1 : 0}"
  depends_on        = ["aws_cloudwatch_log_group.poller_log_group"]

  function_name     = "${data.null_data_source.lambda_function_config.outputs["lambda_name"]}-poller"
  description       = "${data.null_data_source.lambda_function_config.outputs["poller_desc"]}"
  role              = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/HistoricalLambdaProfile"
  handler           = "${data.null_data_source.lambda_function_config.outputs["poller_handler"]}"
  filename          = "lambda.zip"
  source_code_hash  = "${base64sha256(file("lambda.zip"))}"
  runtime           = "python3.6"
  memory_size       = "${data.null_data_source.lambda_function_config.outputs["lambda_memory"]}"
  tags              = "${data.null_data_source.tags.outputs}"
  timeout           = 300

  environment {
    variables = "${merge(data.null_data_source.env_vars.outputs, data.null_data_source.poller_env_vars.outputs)}"
  }
}

// Event mapping for the Poller-Tasker Queue:
resource "aws_lambda_event_source_mapping" "poller_tasker_queue_event_mapping" {
  count               = "${contains(var.POLLING_REGIONS, var.REGION) ? 1 : 0}"

  batch_size          = 10
  event_source_arn    = "${aws_sqs_queue.sqs_poller_tasker_queue.arn}"
  function_name       = "${aws_lambda_function.poller.arn}"
  enabled             = true
}

// The Collector Lambda:
resource "aws_lambda_function" "collector" {
  depends_on        = ["aws_sqs_queue.sqs_event_queue", "aws_cloudwatch_log_group.collector_log_group"]

  function_name     = "${data.null_data_source.lambda_function_config.outputs["lambda_name"]}-collector"
  description       = "${data.null_data_source.lambda_function_config.outputs["collector_desc"]}"
  role              = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/HistoricalLambdaProfile"
  handler           = "${data.null_data_source.lambda_function_config.outputs["collector_handler"]}"
  filename          = "lambda.zip"
  source_code_hash  = "${base64sha256(file("lambda.zip"))}"
  runtime           = "python3.6"
  memory_size       = "${data.null_data_source.lambda_function_config.outputs["lambda_memory"]}"
  tags              = "${data.null_data_source.tags.outputs}"
  timeout           = 300

  reserved_concurrent_executions = "${data.null_data_source.lambda_function_config.outputs["collector_concurrency"]}"

  environment {
    variables = "${merge(data.null_data_source.env_vars.outputs, data.null_data_source.collector_env_vars.outputs)}"
  }
}

// Event mapping for the Poller-Collector Queue:
resource "aws_lambda_event_source_mapping" "poller_collector_queue_event_mapping" {
  count               = "${contains(var.POLLING_REGIONS, var.REGION) ? 1 : 0}"
  depends_on          = ["aws_lambda_function.collector"]

  batch_size          = 5
  event_source_arn    = "${aws_sqs_queue.sqs_poller_collector_queue.arn}"
  function_name       = "${aws_lambda_function.collector.arn}"
  enabled             = true
}

// Event mapping for the Event Queue:
resource "aws_lambda_event_source_mapping" "event_queue_mapping" {
  depends_on          = ["aws_lambda_function.collector"]

  batch_size          = 5
  event_source_arn    = "${aws_sqs_queue.sqs_event_queue.arn}"
  function_name       = "${aws_lambda_function.collector.arn}"
  enabled             = true
}

// Make the Current Table "Proxy":
resource "aws_lambda_function" "current-proxy" {
  depends_on        = ["aws_sqs_queue.differ_queue", "aws_cloudwatch_log_group.current_proxy_log_group"]

  function_name     = "${data.null_data_source.lambda_function_config.outputs["lambda_name"]}-current-proxy"
  description       = "Ships Current Table DynamoDB events to the Differ SQS Queue"
  role              = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/HistoricalLambdaProfile"
  handler           = "historical.common.proxy.handler"
  filename          = "lambda.zip"
  source_code_hash  = "${base64sha256(file("lambda.zip"))}"
  runtime           = "python3.6"
  memory_size       = "128"
  tags              = "${data.null_data_source.tags.outputs}"
  timeout           = 60

  environment {
    variables = "${merge(data.null_data_source.env_vars.outputs, data.null_data_source.current_proxy_env_vars.outputs, map("PROXY_QUEUE_URL", aws_sqs_queue.differ_queue.id))}"
  }
}

// Event mapping for the Current table stream to the Proxy:
resource "aws_lambda_event_source_mapping" "current_table_proxy_mapping" {
  depends_on          = ["aws_lambda_function.current-proxy"]

  batch_size          = 30
  event_source_arn    = "${data.aws_dynamodb_table.current-table.stream_arn}"
  function_name       = "${aws_lambda_function.current-proxy.arn}"
  starting_position   = "LATEST"
  enabled             = true
}

// Make the Differ:
resource "aws_lambda_function" "differ" {
  depends_on        = ["aws_sqs_queue.differ_queue", "aws_cloudwatch_log_group.differ_log_group"]

  function_name     = "${data.null_data_source.lambda_function_config.outputs["lambda_name"]}-differ"
  description       = "${data.null_data_source.lambda_function_config.outputs["differ_desc"]}"
  role              = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/HistoricalLambdaProfile"
  handler           = "${data.null_data_source.lambda_function_config.outputs["differ_handler"]}"
  filename          = "lambda.zip"
  source_code_hash  = "${base64sha256(file("lambda.zip"))}"
  runtime           = "python3.6"
  memory_size       = "${data.null_data_source.lambda_function_config.outputs["lambda_memory"]}"
  tags              = "${data.null_data_source.tags.outputs}"
  timeout           = 300

  environment {
    variables = "${merge(data.null_data_source.env_vars.outputs, data.null_data_source.differ_env_vars.outputs)}"
  }
}

// Event mapping to trigger the Differ from the Current table Proxy (Current Proxy -> SQS -> Differ)
resource "aws_lambda_event_source_mapping" "differ_mapping" {
  batch_size          = 5
  event_source_arn    = "${aws_sqs_queue.differ_queue.arn}"
  function_name       = "${aws_lambda_function.differ.arn}"
  enabled             = true
}

// Make the Durable Table "Proxy":
resource "aws_lambda_function" "durable-proxy" {
  depends_on        = ["aws_cloudwatch_log_group.durable_proxy_log_group"]

  function_name     = "${data.null_data_source.lambda_function_config.outputs["lambda_name"]}-durable-proxy"
  description       = "Ships Durable Table DynamoDB events to SNS"
  role              = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/HistoricalLambdaProfile"
  handler           = "historical.common.proxy.handler"
  filename          = "lambda.zip"
  source_code_hash  = "${base64sha256(file("lambda.zip"))}"
  runtime           = "python3.6"
  memory_size       = "128"
  tags              = "${data.null_data_source.tags.outputs}"
  timeout           = 60

  environment {
    variables = "${merge(data.null_data_source.env_vars.outputs, data.null_data_source.durable_proxy_env_vars.outputs, map("PROXY_TOPIC_ARN", aws_sns_topic.durable_proxy.arn))}"
  }
}

// Event mapping for the Durable table stream to the Proxy:
resource "aws_lambda_event_source_mapping" "durable_table_proxy_mapping" {
  batch_size          = 30
  event_source_arn    = "${data.aws_dynamodb_table.durable-table.stream_arn}"
  function_name       = "${aws_lambda_function.durable-proxy.arn}"
  starting_position   = "LATEST"
  enabled             = true
}
// ----------------------------
