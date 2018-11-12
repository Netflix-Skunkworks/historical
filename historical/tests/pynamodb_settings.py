# pylint: disable=E0401,C0103
"""
.. module: historical.tests.pynamodb_settings.py
    :platform: Unix
    :copyright: (c) 2018 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import requests


# This is a temporary file that is present to make PynamoDB work properly on unit tests.
# This issue has more details: https://github.com/pynamodb/PynamoDB/issues/558
# and will be fixed when this PR is merged: https://github.com/pynamodb/PynamoDB/pull/559

session_cls = requests.Session
