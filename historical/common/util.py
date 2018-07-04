"""
.. module: historical.commom.util
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
    """
    native_records = []
    for r in records:
        native_records.append(json.loads(r['body']))

        # Is this from SNS?
        # if r.get('Sns'):
        #     native_records.append(
        #         json.loads(
        #             r['Sns']['Message']
        #         )
        #     )

        # Is this from Kinesis? (Kinesis records come in a base64 encoded format)
        # elif r.get('kinesis'):
        #     native_records.append(
        #         json.loads(
        #             base64.b64decode(r['kinesis']['data'])
        #         )
        #     )

    return native_records
