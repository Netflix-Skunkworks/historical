# Historical

[![serverless](http://public.serverless.com/badges/v3.svg)](http://www.serverless.com)

Historical is a AWS configuration collection service. Historical uses a combination of Cloudwatch Events (CWE) and Polling to gather
and store configuration data from multiple accounts.

Configuration data is stored as natively as possible. Historical does not make any attempts to modify or coerce the data before storage or during retrieval. Because of this applications are able to easily switch between using historical and directly using AWS API calls.

Key Features:

- Multi account
- Serverless architecture

#### Supported Technologies

| Service Name | Development Status |
| ------------ | ------------------ |
| iam.roles    | In-progress        |
| ec2.security_groups | In-progress |
| s3           | In-progress        |


## Installation

Before we being

Historical is a python package with it's own command lines tools (`historical`). Under the hood, Historical uses serverless for deployment and configuration of it's lambda functions.

Historical is available on pypi:

```bash
    pip install historical
```


## AWS Setup
Serverless requires different IAM credentials to deploy depending what infrastructure exists. If we assume that you have never used serverless before you will need `admin` credentials to deploy this lambda.


## Basic Usage


# Usage
## Deployment

    historical deploy


# Tips & Tricks

### `help` command
Just use it on anything:

    historical  help
or

    historical <command> --help

### `deploy function` command
Deploy only one function:

    historical deploy function -f <function-name>

### `logs` command
Tail the logs of a function:

    historical logs -f <function-name> -t

### `info` command
Information about the service (stage, region, endpoints, functions):

    historical info

### `invoke` command
Run a specific function with a provided input and get the logs

    historical invoke -f <function-name> -p event.json -l


## Development
| **Step** | **Command** |**Description**|
|---|-------|------|
|  1. | `mkvirtualenv historical` | Create virtual environment |
|  2. | `pip install -e .` | Install dependencies|


