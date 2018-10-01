"""
.. module: historical.common.extensions
    :platform: Unix
    :copyright: (c) 2018 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Kevin Glisson <kglisson@netflix.com>
"""
from jinja2.ext import Extension


def titlecase(input_str):
    """Transforms a string to titlecase."""
    return "".join([x.title() for x in input_str.split('_')])


class HistoricalExtension(Extension):
    """Extension class for Cookiecutters."""

    def __init__(self, environment):
        """Instantiates the Historical Extension

        :param environment:
        """
        super(HistoricalExtension, self).__init__(environment)
        environment.filters['titlecase'] = titlecase

    def parse(self, parser):
        """If any of the :attr:`tags` matched this method is called with the
        parser as first argument.  The token the parser stream is pointing at
        is the name token that matched.  This method has to return one or a
        list of multiple nodes.
        """
        raise NotImplementedError()
