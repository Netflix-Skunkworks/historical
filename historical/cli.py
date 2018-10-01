"""
.. module: historical.cli
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""
import os
import logging

import click
import click_log
from cookiecutter.main import cookiecutter  # pylint: disable=E0401

from historical.__about__ import __version__

LOG = logging.getLogger('historical')
click_log.basic_config(LOG)


@click.group()
@click_log.simple_verbosity_option(LOG)
@click.version_option(version=__version__)
def cli():
    """Historical commandline for managing historical functions."""
    pass


@cli.command()
def new():
    """Creates a new historical technology."""
    dir_path = os.path.dirname(os.path.realpath(__file__))
    cookiecutter(os.path.join(dir_path, 'historical-cookiecutter/'))
