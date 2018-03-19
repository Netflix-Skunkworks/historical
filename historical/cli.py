import os
import logging
import click
import click_log
from cookiecutter.main import cookiecutter

from historical.__about__ import __version__

log = logging.getLogger('historical')
click_log.basic_config(log)


@click.group()
@click_log.simple_verbosity_option(log)
@click.version_option(version=__version__)
def cli():
    """Historical commandline for managing historical functions."""
    pass


@cli.command()
def new():
    """Creates a new historical technology."""
    dir_path = os.path.dirname(os.path.realpath(__file__))
    cookiecutter(os.path.join(dir_path, 'historical-cookiecutter/'))
