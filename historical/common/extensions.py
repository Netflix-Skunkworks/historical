"""
.. module: historical.common.extensions
    :platform: Unix
    :copyright: (c) 2018 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
from jinja2.ext import Extension


def titlecase(f):
    """Transforms a string to titlecase."""
    return "".join([x.title() for x in f.split('_')])


class HistoricalExtension(Extension):
    def __init__(self, environment):
        super(HistoricalExtension, self).__init__(environment)
        environment.filters['titlecase'] = titlecase
