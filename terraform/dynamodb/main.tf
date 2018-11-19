terraform {
  backend "s3" {
    // Set this to where your Terraform S3 bucket is located (using us-west-2 as the example):
    region = "us-west-2"
  }
}
// ----------------------------

// ----------------------------
// Set up AWS for the primary region (this one is the main account where most API calls will be based from):
provider "aws" {
  version = "1.39"

  // Set the region to where you need it: us-west-2 is the example:
  "region" = "us-west-2"
}

// Alias providers for the specifc tables:
provider "aws" {
  version = "1.39"

  // This is the PRIMARY REGION ALIAS (us-west-2 is the example):
  "alias" = "us-west-2"
  "region" = "us-west-2"
}

// Create aliases for the SECONDARY REGIONS:
provider "aws" {
  version = "1.39"

  "alias" = "us-east-1"
  "region" = "us-east-1"
}

provider "aws" {
  version = "1.39"

  "alias" = "eu-west-1"
  "region" = "eu-west-1"
}

// ------------ CURRENT TABLES ----------------
// Create the Current tables for all regions:
resource "aws_dynamodb_table" "current_table_primary" {
  provider = "aws.us-west-2"    // Set this to the alias pointed to for the PRIMARY REGION ALIAS

  name                = "${var.CURRENT_TABLE}"
  read_capacity       = "${var.CURRENT_TABLE_READ_CAP}"
  write_capacity      = "${var.CURRENT_TABLE_WRITE_CAP}"
  hash_key            = "arn"
  stream_enabled      = true
  stream_view_type    = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "arn"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled = true
  }
}

// SET UP YOUR SECONDARY REGION TABLES HERE:
resource "aws_dynamodb_table" "current_table_secondary_1" {
  provider = "aws.us-east-1"    // Set this to the alias for your secondary table

  name                = "${var.CURRENT_TABLE}"
  read_capacity       = "${var.CURRENT_TABLE_READ_CAP}"
  write_capacity      = "${var.CURRENT_TABLE_WRITE_CAP}"
  hash_key            = "arn"
  stream_enabled      = true
  stream_view_type    = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "arn"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled = true
  }
}

resource "aws_dynamodb_table" "current_table_secondary_2" {
  provider = "aws.eu-west-1"    // Set this to the alias for your secondary table

  name                = "${var.CURRENT_TABLE}"
  read_capacity       = "${var.CURRENT_TABLE_READ_CAP}"
  write_capacity      = "${var.CURRENT_TABLE_WRITE_CAP}"
  hash_key            = "arn"
  stream_enabled      = true
  stream_view_type    = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "arn"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled = true
  }
}


// GLOBAL DYNAMO TABLE:
resource "aws_dynamodb_global_table" "current_table" {
  // Set these to the proper tables above:
  depends_on = [
    "aws_dynamodb_table.current_table_primary",
    "aws_dynamodb_table.current_table_secondary_1",
    "aws_dynamodb_table.current_table_secondary_2"]

  name = "${var.CURRENT_TABLE}"

  // Set the primary and secondary regions below:
  replica = {
    region_name = "us-west-2"
  }

  replica = {
    region_name = "us-east-1"
  }

  replica = {
    region_name = "eu-west-1"
  }
}
// ----------------------------

// ------------ DURABLE TABLES ----------------

// Create the Durable table:
resource "aws_dynamodb_table" "durable_table_primary" {
  provider            = "aws.us-west-2"     // Set this to the alias pointed to for the PRIMARY REGION ALIAS

  name                = "${var.DURABLE_TABLE}"
  read_capacity       = "${var.DURABLE_TABLE_READ_CAP}"
  write_capacity      = "${var.DURABLE_TABLE_WRITE_CAP}"
  hash_key            = "arn"
  range_key           = "eventTime"
  stream_enabled      = true
  stream_view_type    = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "arn"
    type = "S"
  }

  attribute {
    name = "eventTime"
    type = "S"
  }
}

resource "aws_dynamodb_table" "durable_table_secondary_1" {
  provider            = "aws.us-east-1"     // Set this to the alias for your secondary table

  name                = "${var.DURABLE_TABLE}"
  read_capacity       = "${var.DURABLE_TABLE_READ_CAP}"
  write_capacity      = "${var.DURABLE_TABLE_WRITE_CAP}"
  hash_key            = "arn"
  range_key           = "eventTime"
  stream_enabled      = true
  stream_view_type    = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "arn"
    type = "S"
  }

  attribute {
    name = "eventTime"
    type = "S"
  }
}

resource "aws_dynamodb_table" "durable_table_secondary_2" {
  provider          = "aws.eu-west-1"   // Set this to the alias for your secondary table

  name              = "${var.DURABLE_TABLE}"
  read_capacity     = "${var.DURABLE_TABLE_READ_CAP}"
  write_capacity    = "${var.DURABLE_TABLE_WRITE_CAP}"
  hash_key          = "arn"
  range_key         = "eventTime"
  stream_enabled    = true
  stream_view_type  = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "arn"
    type = "S"
  }

  attribute {
    name = "eventTime"
    type = "S"
  }
}

// GLOBAL DYNAMO TABLE:
resource "aws_dynamodb_global_table" "durable_table" {
  // Set these to the proper tables above:
  depends_on = [
    "aws_dynamodb_table.durable_table_primary",
    "aws_dynamodb_table.durable_table_secondary_1",
    "aws_dynamodb_table.durable_table_secondary_2"
  ]

  name = "${var.DURABLE_TABLE}"

  // Set the primary and secondary regions below:
  replica = {
    region_name = "us-west-2"
  }

  replica = {
    region_name = "us-east-1"
  }

  replica = {
    region_name = "eu-west-1"
  }
}
// -----------------------------
