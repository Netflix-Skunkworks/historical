# Historical
[![Build Status](https://travis-ci.org/Netflix-Skunkworks/historical.svg?branch=master)](https://travis-ci.org/Netflix-Skunkworks/historical)
[![Coverage Status](https://coveralls.io/repos/github/Netflix-Skunkworks/historical/badge.svg?branch=master)](https://coveralls.io/github/Netflix-Skunkworks/historical?branch=master)
## Historical is under heavy development and is not ready for production use.

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


