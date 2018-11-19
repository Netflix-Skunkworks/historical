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
echo "[-->] Copying the requirements file over to the build dir..."
mkdir build
cp requirements.txt build/

# Navigate to the build dir:
cd build/
BUILD_SOURCE_DIR=$( pwd )

# Make the venv:
echo "[...] Building the venv..."
python36 -m venv venv
source venv/bin/activate

# Packaging:
ZIP_NAME="historical-${TECH}.zip"
echo "[...] Building the Lambda..."
pip install -r requirements.txt -t ./artifacts
echo "[...] Zipping the Lambda..."
cd artifacts
zip -r ${ZIP_NAME} .
cd ${BUILD_SOURCE_DIR}

# Make a sym link and place it in the Terraform infra dir for later reference.
cd ${WORKING_DIR}
ln -s ${WORKING_DIR}/build/artifacts/${ZIP_NAME} ${WORKING_DIR}/infra/lambda.zip

# Start the Terraform work:
echo "[-->] Initializing Terraform for DynamoDB work..."
cd ./dynamodb
# Copy the tech template into the local directory for Terraform to set up the tech's DynamoDB components:
cp ${TECH}/${TECH}.tf ./
/terraform init -plugin-dir=/installer/terraform-plugins -backend-config "bucket=$TF_S3_BUCKET" -backend-config "key=terraform/$TECH/DYNAMODB"
if [ $? -ne 0 ]; then
    echo "[X] Terraform init has failed!!"
    exit 1
fi
echo "[-->] Applying the DynamoDB template..."
/terraform apply -auto-approve
if [ $? -ne 0 ]; then
    echo "[X] Terraform application has failed!!"
    exit 1
fi
echo "[+] Completed applying Terraform for DynamoDB"

echo "[@] Now deploying the rest of the infrastructure for each region -- starting with the PRIMARY REGION: ${PRIMARY_REGION}..."
# Copy the tech template into the local directory for Terraform to set up the tech's complete infrastructure components:
cd ${WORKING_DIR}/infra
cp ${TECH}/${TECH}.tf ./

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

    echo "[-->] Applying the template now..."
    TF_VAR_REGION=${region} /terraform apply -auto-approve
    if [ $? -ne 0 ]; then
        echo "[X] Terraform application has failed!!"
        exit 1
    fi
    echo "[+] Completed applying template in ${region}."

    # Clear out the existing Terraform data:
    rm -Rf .terraform/
done

echo "[@] DONE"
