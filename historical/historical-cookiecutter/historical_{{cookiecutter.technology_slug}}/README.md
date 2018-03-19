## ⚡ Historical Deploy

[![serverless](http://public.serverless.com/badges/v3.svg)](http://www.serverless.com)

## About
These are the serverless configuration files needed to various pieces of historical infrastructure. These are configuration files only. Historical itself is located at:

https://github.com/Netflix-Skunkworks/historical


## Monitoring

All of the functions are wrapped with the `RavenLambdaWrapper`. This decorator forwards lambda
telemetry to a [Sentry](https://sentry.io) instance. This will have no effect unless you specify `SENTRY_DSN`
in the Lambda's environment variables.


### Deployment

Install python requirements:

    pip install -r requirements.txt

Run the tests:

    py.test

Get the serverless package:

    npm install serverless

Fetch AWS credentials.

Deploy package

    sls deploy --region us-east-1 --stage <prod>|<test>
