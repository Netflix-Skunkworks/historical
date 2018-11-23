# Historical Terraform Setup

A set of **sample** [Terraform](https://terraform.io) templates are included to assist with the roll-out of the infrastructure. This is intended to be run within a Docker container (code also included). The Docker container will:

1. Package the Historical Lambda code
1. Run the Terraform templates to provision all of the infrastructure

This is all run within an [Amazon Linux](https://hub.docker.com/_/amazonlinux/) Docker container. Amazon Linux is required because Historical's dependencies make use of statically linked libraries, which will fail to run in the Lambda environment unless the binaries are built on Amazon Linux.

You can also use this to uninstall Historical from your environment as well.

**Please review each section below, as the details are very important:**

### Structure
The Terraform templates are split into multiple components:

1. **Terraform Plugins** (located in terraform/terraform-plugins)
1. **DynamoDB** (located in terraform/dynamodb)
1. **Infrastructure** (located in terraform/infra)

#### Terraform Backend Configuration
We make the assumption that the Terraform backend is on S3. As such, you will need an S3 bucket that resides in the Historical AWS account. It is __highly recommended__ that you configure the Historical Terraform S3 bucket with versioning enabled. This is needed should there ever be an issue with the Terraform state.

**NOTE:** For __ALL__ Terraform `main.tf` template files, at the top of the template file is a backend region configuration. It looks like this:

        terraform {
          backend "s3" {
            // Set this to where your Terraform S3 bucket is located (using us-west-2 as the example):
            region = "us-west-2"
          }
        }

You will need to set the region to where your Terraform S3 bucket resides. In our examples, we are making use of `us-west-2`.

#### Terraform Plugins
This is a Terraform template that is executed in the Docker `build` step. This is done to pin the Terraform plugins to the Docker container so that they need not be re-downloaded later. It is important to keep the version numbers in this doc in sync with the rest of the templates.

#### DynamoDB Templates
This is used to construct the Global DynamoDB tables used by Historical. This is structured as follows:

1. `main.tf` - This is the main template with the components required to build out the Global DynamoDB tables for a given Historical stack. The sample included makes an **ASSUMPTION** that you will be utilizing `us-west-2` as your _PRIMARY REGION_, and `us-east-1` and `eu-west-1` as your _SECONDARY REGIONS_.
    - **You will need to modify this template accordingly to change the defaults set.**
    - This is used for ALL stacks. If you want to specify different primary and secondary regions for a given AWS resource type, then you will need to make your own modifications to the installation scripting to leverage different templates.
1. Per-resource type stack configurations. Included are details for S3 and Security Groups. There is a Terraform template for each resource type. This is where you can configure the read and write capacities for the tables.
    - **You will need to modify these templates accordingly to change the defaults set.**
    - By default the tables are configured with a read and write capacity of `100` units. Change this as necessary.

When the installation scripts run, it copies over the resource type configuration to the same directory as the `main.tf` template. Terraform is then able to build out the infrastructure for a given resource type.

#### Infrastructure
This is organized similar to the DynamoDB templates. This must be executed _after_ the DynamoDB templates on installation and _before_ the DynamoDB templates on tear-down (for uninstallation should you need to tear down the stack). This is structured as follows:

1. `main.tf` - This is the main template with most of the infrastructure components identified. Very few (or no) changes need to be made here.
    - This is used for ALL stacks.
1. `off-regions.tf` - This outlines all of the off-region components that are required. This file has a duplicate of every region off-regions' components. Unfortunately, because Terraform lacks a great way to perform loops and iterations, we duplicate the configuration for each region. This makes the file very large and painful to edit. The sample included makes an **ASSUMPTION** that you will be utilizing `us-west-2` as your _PRIMARY REGION_, and `us-east-1` and `eu-west-1` as your _SECONDARY REGIONS_. Thus, all other regions are the off-regions in our sample. You will need to alter this should you want to change the regions for your deployment.
    - **You will need to modify this template accordingly to change the defaults set.**
    - This is used for ALL stacks. If you want to specify different primary, secondary, and off-regions for a given AWS resource type, then you will need to make your own modifications to the installation scripting to leverage different templates.
1. Per-resource type stack configurations. Included are details for S3 and Security Groups. There is a Terraform template for each resource type. This is where you need to configure a number of details.
    - _Most_ of the defaults values are fine and should not be changed.
    - You will need to set the `PRIMARY_REGION`, and `POLLING_REGIONS` variables accordingly. With the exception of S3, the `POLLING_REGIONS` should include the primary and secondary regions in the list.
    - **You will need to review all of the variables and comments in the template to understand what they mean how they should be set. If you change the defaults, you will need to make updates as necessary.**


## Configuration and Environment Variables
**IMPORTANT:** There are many environment variables and configuration details that are required to be set. [Please review this page for details on this](configuration.md).


## Next Steps
Once you have thoroughly reviewed this section, please return back to the [installation documentation](../).
