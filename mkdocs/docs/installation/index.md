# Installation & Configuration
**Note: Some assembly is required.**

There are many components that make up Historical. Included is a Docker container that you can use to run Terraform for installation.

Please review each section below in order to ensure that all aspects of the installation go smoothly. This is important because there are _many_ components that have to be configured correctly for Historical to operate properly.

## Architecture
Before reading this installation guide, please become familiar with the Historical architecture. This will assist you in making the proper configuration for Historical. [You can review that here](../architecture.md).

## Prerequisites
Historical requires the following prerequisites:

1. An AWS account that is dedicated for Historical (this is highly recommended).
1. CloudTrail must be enabled for **ALL** accounts and **ALL** regions.
1. CloudWatch Event Buses must be configured to route **ALL** CloudWatch Events to the Historical account. [Please review and follow the AWS documentation for sending and receiving events between AWS accounts before continuing](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/CloudWatchEvents-CrossAccountEventDelivery.html).
    - This diagram outlines how CloudWatch Event Buses should be configured:
    <a href="../img/cw-events.png"><img src="../img/cw-events.png"></a>
1. You will need to create IAM roles in all the accounts to monitor first. This requires your own orchestration to complete. See the IAM section below for details.
1. Historical makes use of [SWAG](https://github.com/Netflix-Skunkworks/swag-client) to define which AWS accounts Historical is enabled for. SWAG must be properly configured for Historical to operate. Alternatively, you can specify the AWS Account IDs that Historical will examine via an environment variable. However, it is _highly recommended_ that you make use of SWAG.

## IAM Setup
Please review the [IAM Role setup guide here](iam.md) for instructions.

## Terraform
A set of **sample** [Terraform](https://terraform.io) templates are included to assist with the roll-out of the infrastructure. This is intended to be run within a Docker container (code also included). The Docker container will:

This is used for both installation and uninstallation. [Please review the documentation in detail here](terraform.md).

## Configuration and Environment Variables
**IMPORTANT:** There are many environment variables and configuration details that are required to be set. [Please review this page for details on this](configuration.md).

## Prepare Docker Container
Once you have made the necessary changes to your Terraform configuration files, you need to build the Docker container. You will need to build your Docker container.

1. Please [install Docker](https://www.docker.com/get-started) if you haven't already.
1. Navigate to the `historical/terraform` directory.
1. In a terminal, run `docker build . -t historical_installer`

At this point, you now have a Docker container with all the required components to deploy Historical. _If you need to make any adjustments, you will need to re-build your container._

## Installation
Terraform requires a lot of permissions. You will need a very powerful AWS administrative role with lots of permissions to execute the Docker.

1. Get credentials from an IAM role with administrative permissions.
1. Make a copy of `terraform/SAMPLE-env.list` to `terraform/env.list`
1. Open `terraform/env.list`, and fill in the values. ALL values must be supplied and correct. See the [configuration documentation](configuration.md#docker-installer-specific-fields) for reference.
1. In a terminal, navigate to `terraform/`
1. Run Docker! `docker run --env-file ./env.list -t historical_installer`

Hopefully this works!

## Uninstallation
Like for installation, you will need a lot of permissions. You will need a very powerful AWS administrative role with lots of permissions to execute the Docker.

1. Get credentials from an IAM role with administrative permissions.
1. Use the `terraform/env.list` values used for installation.
1. In a terminal, navigate to `terraform/`
1. Run Docker! `docker run --env-file ./env.list --entrypoint /installer/teardown_historical.sh -t historical_installer`

This *might* fail the first time it runs. This is because Terraform doesn't wait long enough for all the resources to be deleted in the primary region. Try running it again if it fails the first time.

If it's still failing, you may need to find the resources that are failing to delete and manually delete them.

Please note: Depending on how active the Lambda functions are, the CloudWatch Event Log groups may still be present after stack deletion. You will need to manually delete these in each primary and secondary regions.

Hopefully this works well for you!

## Troubleshooting
Please review the [Troubleshooting](../troubleshooting) doc if you are experiencing issues.
