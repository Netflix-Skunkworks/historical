FROM amazonlinux:1

MAINTAINER Netflix OSS

COPY requirements.txt /installer/requirements.txt
COPY terraform-plugins /installer/terraform-plugins

ARG TERRAFORM_VERSION=0.11.10

RUN \
    yum install python36 python36-devel gcc-c++ make zip unzip git jq aws-cli -y \
    && curl https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip -o terraform_installer.zip -s \
    && unzip /terraform_installer.zip \
    && cd /installer/terraform-plugins \
    && /terraform init \
    && mv .terraform/plugins/linux_amd64/* ./ \
    && rm -Rf .terraform

# ENVIRONMENT VARIABLES:
ENV TECH=""
ENV TF_S3_BUCKET=""
ENV PRIMARY_REGION=""
ENV SECONDARY_REGIONS=""

# AWS CREDS:
ENV AWS_ACCESS_KEY_ID=""
ENV AWS_SECRET_ACCESS_KEY=""
ENV AWS_SESSION_TOKEN=""

# Do these later to help with caching:
COPY install_historical.sh /installer/install_historical.sh
COPY teardown_historical.sh /installer/teardown_historical.sh
COPY dynamodb /installer/dynamodb
COPY infra /installer/infra
RUN chmod +x /installer/*.sh

WORKDIR "/installer"
ENTRYPOINT ["/installer/install_historical.sh"]
