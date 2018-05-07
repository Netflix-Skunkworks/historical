"""
.. module: historical.constants
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
import os
CURRENT_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
HISTORICAL_ROLE = os.environ.get('HISTORICAL_ROLE', 'Historical')
POLL_REGIONS = os.environ.get('POLL_REGIONS', 'us-east-1').split(",")
DIFF_REGIONS = os.environ.get('DIFF_REGIONS', "us-east-1").split(",")
