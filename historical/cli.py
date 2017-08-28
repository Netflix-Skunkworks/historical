import os
import logging

import click
import delegator

logger = logging.getLogger(__name__)


class Config(object):
    def __init__(self, home=None, debug=False):
        self.home = os.path.abspath(home or '.')
        self.debug = debug


@click.group()
@click.option('--config-home', envvar='HISTORICAL_HOME', default='.historical')
@click.option('--debug/--no-debug', default=False,
              envvar='HISTORICAL_DEBUG')
@click.pass_context
def cli(ctx, config_home, debug):
    """Historical commandline for managing historical functions."""
    ctx.obj = Config(config_home, debug)


@cli.command()
@click.pass_obj
@click.option('--region', default='us-east-1', help='Region to deploy to.')
@click.option('--stage', help='Stage to deploy to.')
def deploy(config, region, stage):
    """Deploy a new historical service."""
    delegator.run('sls deploy --region {region} --stage {stage}'.format(
        region=region,
        stage=stage))


@cli.command()
def info():
    """Print historical configuration information."""
    pass


@cli.command()
def invoke():
    """Run a specific function."""
    pass
