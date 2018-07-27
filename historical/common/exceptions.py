"""
.. module: historical.common.exceptions
    :platform: Unix
    :copyright: (c) 2018 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""


class DurableItemIsMissingException(Exception):
    pass


class MissingProxyConfigurationException(Exception):
    pass
