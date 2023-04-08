import sys
import click
from loguru import logger
from requests.exceptions import RetryError

from .client import AuthenticationError, InstagramClient
from .utils import setup_logging


@click.command()
@click.option('-o',
              '--output-dir',
              default=None,
              help='Output directory',
              type=click.Path(exists=True))
@click.option('-b',
              '--browser',
              default='chrome',
              help='Browser to read cookies from')
@click.option('-p', '--profile', default='Default', help='Browser profile')
@click.option('-d', '--debug', is_flag=True, help='Enable debug output')
@click.option('--no-log',
              is_flag=True,
              help='Ignore log (re-fetch everything)')
@click.argument('username')
def main(output_dir: str | None,
         browser: str,
         profile: str,
         username: str,
         debug: bool = False,
         no_log: bool = False) -> None:
    setup_logging(debug)
    try:
        with InstagramClient(username=username,
                             output_dir=output_dir,
                             browser_profile=profile,
                             browser=browser,
                             debug=debug,
                             disable_log=no_log) as client:
            client.process()
    except RetryError as e:
        click.echo(str(e), file=sys.stderr)
        click.echo('You should wait a few hours before trying again.',
                   file=sys.stderr)
        raise click.Abort() from e
    except AuthenticationError as e:
        click.echo(
            'You are probably not logged into Instagram in this browser profile or your '
            'session has expired.',
            file=sys.stderr)
        raise click.Abort() from e
    except Exception as e:
        if debug:
            logger.exception(e)
        else:
            click.echo('Run with --debug for more information')
        raise click.Abort(
            f'{e} (run with --debug for more information)') from e
