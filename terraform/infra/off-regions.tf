// Declare the off regions:
// ----------------------------

// NOTE: TERRAFORM DOES NOT HAVE A GREAT WAY OF HANDLING LOOPS :(
// AS SUCH -- EVERYTHING IS DUPLICATED FOR EACH AND EVERY OFF-REGION :(
// MAKE THE NECESSARY EDITS. YOU CAN DELETE AND EDIT REGIONS AS NECESSARY.
// See what is in between the 'SAMPLE REGION START' and 'SAMPLE REGION END' for an idea of what is needed.

// ---- SAMPLE REGION START ----
// US-EAST-2

provider "aws" {
  version = "1.39"

  region = "us-east-2"
  alias  = "us-east-2"
}

resource "aws_cloudwatch_event_rule" "events_off_region_us-east-2" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.us-east-2"

  name        = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  description = "${data.null_data_source.cwe_config.outputs["rule_desc"]}"

  event_pattern = "${data.null_data_source.cwe_config.outputs["event_pattern"]}"
}

resource "aws_sns_topic" "off_region_events_sns_us-east-2" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.us-east-2"

  name        = "${data.null_data_source.cwe_config.outputs["off_regions_sns_name"]}"
}

resource "aws_sns_topic_policy" "off_region_sns_policy_us-east-2" {
  count    = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider = "aws.us-east-2"

  arn      = "${aws_sns_topic.off_region_events_sns_us-east-2.arn}"

  policy = <<PATTERN
  {
    "Version": "2012-10-17",
    "Id": "CloudwatchEvents",
    "Statement": [
      {
        "Sid": "CloudwatchEvents",
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sns:Publish",
        "Resource": "${aws_sns_topic.off_region_events_sns_us-east-2.arn}"
      }
    ]
  }
  PATTERN
}

resource "aws_cloudwatch_event_target" "off_region_cwe_target_us-east-2" {
  count   = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"

  provider = "aws.us-east-2"
  rule    = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  arn     = "${aws_sns_topic.off_region_events_sns_us-east-2.arn}"
}

resource "aws_sns_topic_subscription" "off_region_events_subscription_us-east-2" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.us-east-2"

  topic_arn   = "${aws_sns_topic.off_region_events_sns_us-east-2.arn}"
  protocol    = "sqs"
  endpoint    = "${aws_sqs_queue.sqs_event_queue.arn}"
}
// ---- SAMPLE REGION END ----

// US-WEST-1
provider "aws" {
  version = "1.39"

  region = "us-west-1"
  alias  = "us-west-1"
}

resource "aws_cloudwatch_event_rule" "events_off_region_us-west-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.us-west-1"

  name        = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  description = "${data.null_data_source.cwe_config.outputs["rule_desc"]}"

  event_pattern = "${data.null_data_source.cwe_config.outputs["event_pattern"]}"
}

resource "aws_sns_topic" "off_region_events_sns_us-west-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.us-west-1"

  name = "${data.null_data_source.cwe_config.outputs["off_regions_sns_name"]}"
}

resource "aws_sns_topic_policy" "off_region_sns_policy_us-west-1" {
  count    = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider = "aws.us-west-1"

  arn      = "${aws_sns_topic.off_region_events_sns_us-west-1.arn}"

  policy = <<PATTERN
  {
    "Version": "2012-10-17",
    "Id": "CloudwatchEvents",
    "Statement": [
      {
        "Sid": "CloudwatchEvents",
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sns:Publish",
        "Resource": "${aws_sns_topic.off_region_events_sns_us-west-1.arn}"
      }
    ]
  }
 PATTERN
}

resource "aws_cloudwatch_event_target" "off_region_cwe_target_us-west-1" {
  count   = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"

  provider = "aws.us-west-1"
  rule    = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  arn     = "${aws_sns_topic.off_region_events_sns_us-west-1.arn}"
}

resource "aws_sns_topic_subscription" "off_region_events_subscription_us-west-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.us-west-1"

  topic_arn   = "${aws_sns_topic.off_region_events_sns_us-west-1.arn}"
  protocol    = "sqs"
  endpoint    = "${aws_sqs_queue.sqs_event_queue.arn}"
}


// AP-NORTHEAST-1
provider "aws" {
  version = "1.39"

  region = "ap-northeast-1"
  alias  = "ap-northeast-1"
}

resource "aws_cloudwatch_event_rule" "events_off_region_ap-northeast-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-northeast-1"

  name        = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  description = "${data.null_data_source.cwe_config.outputs["rule_desc"]}"

  event_pattern = "${data.null_data_source.cwe_config.outputs["event_pattern"]}"
}

resource "aws_sns_topic" "off_region_events_sns_ap-northeast-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-northeast-1"

  name = "${data.null_data_source.cwe_config.outputs["off_regions_sns_name"]}"
}

resource "aws_sns_topic_policy" "off_region_sns_policy_ap-northeast-1" {
  count    = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider = "aws.ap-northeast-1"

  arn = "${aws_sns_topic.off_region_events_sns_ap-northeast-1.arn}"

  policy = <<PATTERN
  {
    "Version": "2012-10-17",
    "Id": "CloudwatchEvents",
    "Statement": [
      {
        "Sid": "CloudwatchEvents",
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sns:Publish",
        "Resource": "${aws_sns_topic.off_region_events_sns_ap-northeast-1.arn}"
      }
    ]
  }
 PATTERN
}

resource "aws_cloudwatch_event_target" "off_region_cwe_target_ap-northeast-1" {
  count   = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"

  provider = "aws.ap-northeast-1"
  rule    = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  arn     = "${aws_sns_topic.off_region_events_sns_ap-northeast-1.arn}"
}

resource "aws_sns_topic_subscription" "off_region_events_subscription_ap-northeast-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-northeast-1"

  topic_arn   = "${aws_sns_topic.off_region_events_sns_ap-northeast-1.arn}"
  protocol    = "sqs"
  endpoint    = "${aws_sqs_queue.sqs_event_queue.arn}"
}


// AP-NORTHEAST-2
provider "aws" {
  version = "1.39"

  region = "ap-northeast-2"
  alias  = "ap-northeast-2"
}

resource "aws_cloudwatch_event_rule" "events_off_region_ap-northeast-2" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-northeast-2"

  name        = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  description = "${data.null_data_source.cwe_config.outputs["rule_desc"]}"

  event_pattern = "${data.null_data_source.cwe_config.outputs["event_pattern"]}"
}

resource "aws_sns_topic" "off_region_events_sns_ap-northeast-2" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-northeast-2"

  name = "${data.null_data_source.cwe_config.outputs["off_regions_sns_name"]}"
}

resource "aws_sns_topic_policy" "off_region_sns_policy_ap-northeast-2" {
  count    = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider = "aws.ap-northeast-2"

  arn = "${aws_sns_topic.off_region_events_sns_ap-northeast-2.arn}"

  policy = <<PATTERN
  {
    "Version": "2012-10-17",
    "Id": "CloudwatchEvents",
    "Statement": [
      {
        "Sid": "CloudwatchEvents",
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sns:Publish",
        "Resource": "${aws_sns_topic.off_region_events_sns_ap-northeast-2.arn}"
      }
    ]
  }
  PATTERN
}

resource "aws_cloudwatch_event_target" "off_region_cwe_target_ap-northeast-2" {
  count   = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"

  provider = "aws.ap-northeast-2"
  rule    = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  arn     = "${aws_sns_topic.off_region_events_sns_ap-northeast-2.arn}"
}

resource "aws_sns_topic_subscription" "off_region_events_subscription_ap-northeast-2" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-northeast-2"

  topic_arn   = "${aws_sns_topic.off_region_events_sns_ap-northeast-2.arn}"
  protocol    = "sqs"
  endpoint    = "${aws_sqs_queue.sqs_event_queue.arn}"
}

// AP-NORTHEAST-3
/*provider "aws" {
  version = "1.39"

  region = "ap-northeast-3"
  alias  = "ap-northeast-3"
}

resource "aws_cloudwatch_event_rule" "events_off_region_ap-northeast-3" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-northeast-3"

  name        = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  description = "${data.null_data_source.cwe_config.outputs["rule_desc"]}"

  event_pattern = "${data.null_data_source.cwe_config.outputs["event_pattern"]}"
}

resource "aws_sns_topic" "off_region_events_sns_ap-northeast-3" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-northeast-3"

  name = "${data.null_data_source.cwe_config.outputs["off_regions_sns_name"]}"
}

resource "aws_sns_topic_policy" "off_region_sns_policy_ap-northeast-3" {
  count    = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider = "aws.ap-northeast-3"

  arn = "${aws_sns_topic.off_region_events_sns_ap-northeast-3.arn}"

  policy = <<PATTERN
  {
    "Version": "2012-10-17",
    "Id": "CloudwatchEvents",
    "Statement": [
      {
        "Sid": "CloudwatchEvents",
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sns:Publish",
        "Resource": "${aws_sns_topic.off_region_events_sns_ap-northeast-3.arn}"
      }
    ]
  }
  PATTERN
}

resource "aws_cloudwatch_event_target" "off_region_cwe_target_ap-northeast-3" {
  count   = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"

  provider = "aws.ap-northeast-3"
  rule    = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  arn     = "${aws_sns_topic.off_region_events_sns_ap-northeast-3.arn}"
}

resource "aws_sns_topic_subscription" "off_region_events_subscription_ap-northeast-3" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-northeast-3"

  topic_arn   = "${aws_sns_topic.off_region_events_sns_ap-northeast-3.arn}"
  protocol    = "sqs"
  endpoint    = "${aws_sqs_queue.sqs_event_queue.arn}"
}
*/


// AP-SOUTH-1
provider "aws" {
  version = "1.39"

  region = "ap-south-1"
  alias  = "ap-south-1"
}

resource "aws_cloudwatch_event_rule" "events_off_region_ap-south-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-south-1"

  name        = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  description = "${data.null_data_source.cwe_config.outputs["rule_desc"]}"

  event_pattern = "${data.null_data_source.cwe_config.outputs["event_pattern"]}"
}

resource "aws_sns_topic" "off_region_events_sns_ap-south-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-south-1"

  name = "${data.null_data_source.cwe_config.outputs["off_regions_sns_name"]}"
}

resource "aws_sns_topic_policy" "off_region_sns_policy_ap-south-1" {
  count    = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider = "aws.ap-south-1"

  arn = "${aws_sns_topic.off_region_events_sns_ap-south-1.arn}"

  policy = <<PATTERN
  {
    "Version": "2012-10-17",
    "Id": "CloudwatchEvents",
    "Statement": [
      {
        "Sid": "CloudwatchEvents",
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sns:Publish",
        "Resource": "${aws_sns_topic.off_region_events_sns_ap-south-1.arn}"
      }
    ]
  }
  PATTERN
}


resource "aws_cloudwatch_event_target" "off_region_cwe_target_ap-south-1" {
  count   = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"

  provider = "aws.ap-south-1"
  rule    = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  arn     = "${aws_sns_topic.off_region_events_sns_ap-south-1.arn}"
}

resource "aws_sns_topic_subscription" "off_region_events_subscription_ap-south-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-south-1"

  topic_arn   = "${aws_sns_topic.off_region_events_sns_ap-south-1.arn}"
  protocol    = "sqs"
  endpoint    = "${aws_sqs_queue.sqs_event_queue.arn}"
}


// AP-SOUTHEAST-1
provider "aws" {
  version = "1.39"

  region = "ap-southeast-1"
  alias  = "ap-southeast-1"
}

resource "aws_cloudwatch_event_rule" "events_off_region_ap-southeast-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-southeast-1"

  name        = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  description = "${data.null_data_source.cwe_config.outputs["rule_desc"]}"

  event_pattern = "${data.null_data_source.cwe_config.outputs["event_pattern"]}"
}

resource "aws_sns_topic" "off_region_events_sns_ap-southeast-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-southeast-1"

  name = "${data.null_data_source.cwe_config.outputs["off_regions_sns_name"]}"
}

resource "aws_sns_topic_policy" "off_region_sns_policy_ap-southeast-1" {
  count    = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider = "aws.ap-southeast-1"

  arn = "${aws_sns_topic.off_region_events_sns_ap-southeast-1.arn}"

  policy = <<PATTERN
  {
    "Version": "2012-10-17",
    "Id": "CloudwatchEvents",
    "Statement": [
      {
        "Sid": "CloudwatchEvents",
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sns:Publish",
        "Resource": "${aws_sns_topic.off_region_events_sns_ap-southeast-1.arn}"
      }
    ]
  }
  PATTERN
}

resource "aws_cloudwatch_event_target" "off_region_cwe_target_ap-southeast-1" {
  count   = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"

  provider = "aws.ap-southeast-1"
  rule    = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  arn     = "${aws_sns_topic.off_region_events_sns_ap-southeast-1.arn}"
}

resource "aws_sns_topic_subscription" "off_region_events_subscription_ap-southeast-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-southeast-1"

  topic_arn   = "${aws_sns_topic.off_region_events_sns_ap-southeast-1.arn}"
  protocol    = "sqs"
  endpoint    = "${aws_sqs_queue.sqs_event_queue.arn}"
}


// AP-SOUTHEAST-2
provider "aws" {
  version = "1.39"

  region  = "ap-southeast-2"
  alias   = "ap-southeast-2"
}

resource "aws_cloudwatch_event_rule" "events_off_region_ap-southeast-2" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-southeast-2"

  name        = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  description = "${data.null_data_source.cwe_config.outputs["rule_desc"]}"

  event_pattern = "${data.null_data_source.cwe_config.outputs["event_pattern"]}"
}

resource "aws_sns_topic" "off_region_events_sns_ap-southeast-2" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-southeast-2"

  name = "${data.null_data_source.cwe_config.outputs["off_regions_sns_name"]}"
}

resource "aws_sns_topic_policy" "off_region_sns_policy_ap-southeast-2" {
  count    = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider = "aws.ap-southeast-2"

  arn = "${aws_sns_topic.off_region_events_sns_ap-southeast-2.arn}"

  policy = <<PATTERN
  {
    "Version": "2012-10-17",
    "Id": "CloudwatchEvents",
    "Statement": [
      {
        "Sid": "CloudwatchEvents",
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sns:Publish",
        "Resource": "${aws_sns_topic.off_region_events_sns_ap-southeast-2.arn}"
      }
    ]
  }
  PATTERN
}

resource "aws_cloudwatch_event_target" "off_region_cwe_target_ap-southeast-2" {
  count   = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"

  provider = "aws.ap-southeast-2"
  rule    = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  arn     = "${aws_sns_topic.off_region_events_sns_ap-southeast-2.arn}"
}

resource "aws_sns_topic_subscription" "off_region_events_subscription_ap-southeast-2" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ap-southeast-2"

  topic_arn   = "${aws_sns_topic.off_region_events_sns_ap-southeast-2.arn}"
  protocol    = "sqs"
  endpoint    = "${aws_sqs_queue.sqs_event_queue.arn}"
}


// CA-CENTRAL-1
provider "aws" {
  version = "1.39"

  region  = "ca-central-1"
  alias   = "ca-central-1"
}

resource "aws_cloudwatch_event_rule" "events_off_region_ca-central-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ca-central-1"

  name        = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  description = "${data.null_data_source.cwe_config.outputs["rule_desc"]}"

  event_pattern = "${data.null_data_source.cwe_config.outputs["event_pattern"]}"
}

resource "aws_sns_topic" "off_region_events_sns_ca-central-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ca-central-1"

  name = "${data.null_data_source.cwe_config.outputs["off_regions_sns_name"]}"
}

resource "aws_sns_topic_policy" "off_region_sns_policy_ca-central-1" {
  count    = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider = "aws.ca-central-1"

  arn = "${aws_sns_topic.off_region_events_sns_ca-central-1.arn}"

  policy = <<PATTERN
  {
    "Version": "2012-10-17",
    "Id": "CloudwatchEvents",
    "Statement": [
      {
        "Sid": "CloudwatchEvents",
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sns:Publish",
        "Resource": "${aws_sns_topic.off_region_events_sns_ca-central-1.arn}"
      }
    ]
  }
  PATTERN
}

resource "aws_cloudwatch_event_target" "off_region_cwe_target_ca-central-1" {
  count   = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"

  provider = "aws.ca-central-1"
  rule    = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  arn     = "${aws_sns_topic.off_region_events_sns_ca-central-1.arn}"
}

resource "aws_sns_topic_subscription" "off_region_events_subscription_ca-central-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.ca-central-1"

  topic_arn   = "${aws_sns_topic.off_region_events_sns_ca-central-1.arn}"
  protocol    = "sqs"
  endpoint    = "${aws_sqs_queue.sqs_event_queue.arn}"
}


// EU-CENTRAL-1
provider "aws" {
  version = "1.39"

  region  = "eu-central-1"
  alias   = "eu-central-1"
}

resource "aws_cloudwatch_event_rule" "events_off_region_eu-central-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.eu-central-1"

  name        = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  description = "${data.null_data_source.cwe_config.outputs["rule_desc"]}"

  event_pattern = "${data.null_data_source.cwe_config.outputs["event_pattern"]}"
}

resource "aws_sns_topic" "off_region_events_sns_eu-central-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.eu-central-1"

  name = "${data.null_data_source.cwe_config.outputs["off_regions_sns_name"]}"
}

resource "aws_sns_topic_policy" "off_region_sns_policy_eu-central-1" {
  count    = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider = "aws.eu-central-1"

  arn = "${aws_sns_topic.off_region_events_sns_eu-central-1.arn}"

  policy = <<PATTERN
  {
    "Version": "2012-10-17",
    "Id": "CloudwatchEvents",
    "Statement": [
      {
        "Sid": "CloudwatchEvents",
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sns:Publish",
        "Resource": "${aws_sns_topic.off_region_events_sns_eu-central-1.arn}"
      }
    ]
  }
  PATTERN
}

resource "aws_cloudwatch_event_target" "off_region_cwe_target_eu-central-1" {
  count   = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"

  provider = "aws.eu-central-1"
  rule    = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  arn     = "${aws_sns_topic.off_region_events_sns_eu-central-1.arn}"
}

resource "aws_sns_topic_subscription" "off_region_events_subscription_eu-central-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.eu-central-1"

  topic_arn   = "${aws_sns_topic.off_region_events_sns_eu-central-1.arn}"
  protocol    = "sqs"
  endpoint    = "${aws_sqs_queue.sqs_event_queue.arn}"
}


// EU-WEST-2
provider "aws" {
  version = "1.39"

  region  = "eu-west-2"
  alias   = "eu-west-2"
}

resource "aws_cloudwatch_event_rule" "events_off_region_eu-west-2" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.eu-west-2"

  name        = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  description = "${data.null_data_source.cwe_config.outputs["rule_desc"]}"

  event_pattern = "${data.null_data_source.cwe_config.outputs["event_pattern"]}"
}

resource "aws_sns_topic" "off_region_events_sns_eu-west-2" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.eu-west-2"

  name = "${data.null_data_source.cwe_config.outputs["off_regions_sns_name"]}"
}

resource "aws_sns_topic_policy" "off_region_sns_policy_eu-west-2" {
  count    = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider = "aws.eu-west-2"

  arn = "${aws_sns_topic.off_region_events_sns_eu-west-2.arn}"

  policy = <<PATTERN
  {
    "Version": "2012-10-17",
    "Id": "CloudwatchEvents",
    "Statement": [
      {
        "Sid": "CloudwatchEvents",
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sns:Publish",
        "Resource": "${aws_sns_topic.off_region_events_sns_eu-west-2.arn}"
      }
    ]
  }
  PATTERN
}

resource "aws_cloudwatch_event_target" "off_region_cwe_target_eu-west-2" {
  count   = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"

  provider = "aws.eu-west-2"
  rule    = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  arn     = "${aws_sns_topic.off_region_events_sns_eu-west-2.arn}"
}

resource "aws_sns_topic_subscription" "off_region_events_subscription_eu-west-2" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.eu-west-2"

  topic_arn   = "${aws_sns_topic.off_region_events_sns_eu-west-2.arn}"
  protocol    = "sqs"
  endpoint    = "${aws_sqs_queue.sqs_event_queue.arn}"
}


// EU-WEST-3
provider "aws" {
  version = "1.39"

  region  = "eu-west-3"
  alias   = "eu-west-3"
}

resource "aws_cloudwatch_event_rule" "events_off_region_eu-west-3" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.eu-west-3"

  name        = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  description = "${data.null_data_source.cwe_config.outputs["rule_desc"]}"

  event_pattern = "${data.null_data_source.cwe_config.outputs["event_pattern"]}"
}

resource "aws_sns_topic" "off_region_events_sns_eu-west-3" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.eu-west-3"

  name = "${data.null_data_source.cwe_config.outputs["off_regions_sns_name"]}"
}

resource "aws_sns_topic_policy" "off_region_sns_policy_eu-west-3" {
  count    = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider = "aws.eu-west-3"

  arn = "${aws_sns_topic.off_region_events_sns_eu-west-3.arn}"

  policy = <<PATTERN
  {
    "Version": "2012-10-17",
    "Id": "CloudwatchEvents",
    "Statement": [
      {
        "Sid": "CloudwatchEvents",
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sns:Publish",
        "Resource": "${aws_sns_topic.off_region_events_sns_eu-west-3.arn}"
      }
    ]
  }
  PATTERN
}

resource "aws_cloudwatch_event_target" "off_region_cwe_target_eu-west-3" {
  count   = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"

  provider = "aws.eu-west-3"
  rule    = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  arn     = "${aws_sns_topic.off_region_events_sns_eu-west-3.arn}"
}

resource "aws_sns_topic_subscription" "off_region_events_subscription_eu-west-3" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.eu-west-3"

  topic_arn   = "${aws_sns_topic.off_region_events_sns_eu-west-3.arn}"
  protocol    = "sqs"
  endpoint    = "${aws_sqs_queue.sqs_event_queue.arn}"
}


// SA-EAST-1
provider "aws" {
  version = "1.39"

  region  = "sa-east-1"
  alias   = "sa-east-1"
}

resource "aws_cloudwatch_event_rule" "events_off_region_sa-east-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.sa-east-1"

  name        = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  description = "${data.null_data_source.cwe_config.outputs["rule_desc"]}"

  event_pattern = "${data.null_data_source.cwe_config.outputs["event_pattern"]}"
}

resource "aws_sns_topic" "off_region_events_sns_sa-east-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.sa-east-1"

  name = "${data.null_data_source.cwe_config.outputs["off_regions_sns_name"]}"
}

resource "aws_sns_topic_policy" "off_region_sns_policy_sa-east-1" {
  count    = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider = "aws.sa-east-1"

  arn = "${aws_sns_topic.off_region_events_sns_sa-east-1.arn}"

  policy = <<PATTERN
  {
    "Version": "2012-10-17",
    "Id": "CloudwatchEvents",
    "Statement": [
      {
        "Sid": "CloudwatchEvents",
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sns:Publish",
        "Resource": "${aws_sns_topic.off_region_events_sns_sa-east-1.arn}"
      }
    ]
  }
  PATTERN
}

resource "aws_cloudwatch_event_target" "off_region_cwe_target_sa-east-1" {
  count   = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"

  provider = "aws.sa-east-1"
  rule    = "${data.null_data_source.cwe_config.outputs["rule_name"]}"
  arn     = "${aws_sns_topic.off_region_events_sns_sa-east-1.arn}"
}

resource "aws_sns_topic_subscription" "off_region_events_subscription_sa-east-1" {
  count       = "${var.REGION == var.PRIMARY_REGION ? 1 : 0}"
  provider    = "aws.sa-east-1"

  topic_arn   = "${aws_sns_topic.off_region_events_sns_sa-east-1.arn}"
  protocol    = "sqs"
  endpoint    = "${aws_sqs_queue.sqs_event_queue.arn}"
}
