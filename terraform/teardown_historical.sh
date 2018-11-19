#!/bin/bash

[ -z "$TECH" ] && echo "Need to set TECH -- one of [s3, securitygroup]" && exit 1;
[ -z "$TF_S3_BUCKET" ] && echo "Need to set TF_S3_BUCKET -- the S3 bucket to use for Terraform" && exit 1;
[ -z "$PRIMARY_REGION" ] && echo "Need to set PRIMARY_REGION." && exit 1;

# AWS ENV VARS:
[ -z "$AWS_ACCESS_KEY_ID" ] && echo "Need to set the AWS_ACCESS_KEY_ID" && exit 1;
[ -z "$AWS_SECRET_ACCESS_KEY" ] && echo "Need to set the AWS_SECRET_ACCESS_KEY" && exit 1;
[ -z "$AWS_SESSION_TOKEN" ] && echo "Need to set the AWS_SESSION_TOKEN" && exit 1;

# Copy the requirements.txt file over:
WORKING_DIR=$( pwd )

# Make an empty file to make Terraform happy:
touch ${WORKING_DIR}/infra/lambda.zip

# Tear down the stacks first:
cd ${WORKING_DIR}/infra
cp ${TECH}/${TECH}.tf ./

# Start the Terraform work:
echo "[@] Now tearing down the infrastructure for each region -- starting with the PRIMARY REGION: ${PRIMARY_REGION}..."
IFS=','
ALL_REGIONS=$PRIMARY_REGION,$SECONDARY_REGIONS
for region in $ALL_REGIONS;
do
    echo "[-->] Initializing Terraform for ${region}..."
    /terraform init -plugin-dir=/installer/terraform-plugins -backend-config "bucket=$TF_S3_BUCKET" -backend-config "key=terraform/$TECH/INFRA/$region"
    if [ $? -ne 0 ]; then
        echo "[X] Terraform init has failed!!"
        exit 1
    fi

    echo "[-->] Tearing down the stack now..."
    TF_VAR_REGION=${region} /terraform destroy -auto-approve
    if [ $? -ne 0 ]; then
        echo "[X] Terraform stack destroy has failed!! -- Sometimes this needs be run multiple times due to eventual consistency."
        exit 1
    fi
    echo "[+] Completed tearing down stack in ${region}."

    # Clear out the existing Terraform data:
    rm -Rf .terraform/
done

echo "[-->] Initializing Terraform for DynamoDB work..."
cd ${WORKING_DIR}/dynamodb
# Copy the tech template into the local directory for Terraform to tear down the tech's DynamoDB components:
cp ${TECH}/${TECH}.tf ./
/terraform init -plugin-dir=/installer/terraform-plugins -backend-config "bucket=$TF_S3_BUCKET" -backend-config "key=terraform/$TECH/DYNAMODB"
if [ $? -ne 0 ]; then
    echo "[X] Terraform init has failed!!"
    exit 1
fi
echo "[-->] Tearing down the DynamoDB stack..."
/terraform destroy -auto-approve
if [ $? -ne 0 ]; then
    echo "[X] Terraform stack destroy has failed!!"
    exit 1
fi
echo "[+] Completed tearing down DynamoDB."

echo "[@] DONE"
