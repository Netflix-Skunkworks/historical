"""
.. module: historical.common.util
    :platform: Unix
    :copyright: (c) 2018 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import json


def deserialize_records(records):
    """
    This properly deserializes records depending on where they came from:
        - SQS
        - SNS
    """
    native_records = []
    for r in records:
        parsed = json.loads(r['body'])

        # Is this a DynamoDB stream event?
        if isinstance(parsed, str):
            native_records.append(json.loads(parsed))

        # Is this a subscription message from SNS? If so, skip it:
        elif parsed.get('Type') == 'SubscriptionConfirmation':
            continue

        # Is this from SNS (cross-region request -- SNS messages wrapped in SQS message) -- or an SNS proxied message?
        elif parsed.get('Message'):
            native_records.append(json.loads(parsed['Message']))

        else:
            native_records.append(parsed)

    return native_records


def pull_tag_dict(data):
    """This will pull out a list of Tag Name-Value objects, and return it as a dictionary.

    :param data: The dict collected from the collector.
    :returns dict: A dict of the tag names and their corresponding values.
    """
    # If there are tags, set them to a normal dict, vs. a list of dicts:
    tags = data.pop('Tags', {}) or {}
    if tags:
        proper_tags = {}
        for t in tags:
            proper_tags[t['Key']] = t['Value']

        tags = proper_tags

    return tags
