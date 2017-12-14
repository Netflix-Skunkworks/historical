# Historical
[![Build Status](https://travis-ci.org/Netflix-Skunkworks/historical.svg?branch=master)](https://travis-ci.org/Netflix-Skunkworks/historical)
[![Coverage Status](https://coveralls.io/repos/github/Netflix-Skunkworks/historical/badge.svg?branch=master)](https://coveralls.io/github/Netflix-Skunkworks/historical?branch=master)
[![PyPI version](https://badge.fury.io/py/historical.svg)](https://badge.fury.io/py/historical)

## Historical is under heavy development and is not ready for production use.

# Historical

Historical is a AWS configuration collection service. It uses a combination of Cloudwatch Events (CWE) and periodic polling to gather
and store configuration data from multiple accounts.

Key Features:

- Real-time
- Multi-account
- Serverless architecture
- Region isolation

#### Supported Technologies

| Service Name | Development Status |
| ------------ | ------------------ |
| iam.roles    | In-progress        |
| ec2.security_groups | Complete ✅ |
| ec2.vpc | Complete ✅ |
| ec2.elb | In-progress |
| s3           | Complete ✅       |
| route53      | In-progress        |

## Documentation
https://historical.readthedocs.com


