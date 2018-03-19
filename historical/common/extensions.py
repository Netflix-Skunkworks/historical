from jinja2.ext import Extension


def titlecase(f):
    """Transforms a string to titlecase."""
    return "".join([x.title() for x in f.split('_')])


class HistoricalExtension(Extension):
    def __init__(self, environment):
        super(HistoricalExtension, self).__init__(environment)
        environment.filters['titlecase'] = titlecase
