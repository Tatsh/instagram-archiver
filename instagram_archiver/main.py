import sys

from loguru import logger
from requests.exceptions import RetryError
import click

from .client import AuthenticationError, Browser, InstagramClient
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
              type=click.Choice(
                  ['brave', 'chrome', 'chromium', 'edge', 'opera', 'vivaldi', 'firefox', 'safari']),
              help='Browser to read cookies from')
@click.option('-p', '--profile', default='Default', help='Browser profile')
@click.option('-d', '--debug', is_flag=True, help='Enable debug output')
@click.option('--no-log', is_flag=True, help='Ignore log (re-fetch everything)')
@click.option('-C',
              '--include-comments',
              is_flag=True,
              help='Also download all comments (extends '
              'download time significantly).')
@click.argument('username')
def main(output_dir: str | None,
         browser: Browser,
         profile: str,
         username: str,
         debug: bool = False,
         no_log: bool = False,
         include_comments: bool = False) -> None:
    setup_logging(debug)
    try:
        with InstagramClient(username=username,
                             output_dir=output_dir,
                             browser_profile=profile,
                             browser=browser,
                             debug=debug,
                             disable_log=no_log,
                             comments=include_comments) as client:
            client.process()
    except RetryError as e:
        click.echo(
            'Open your browser and login if necessary. If you are logged in and this continues, '
            'try waiting at least 12 hours.',
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
        raise click.Abort(f'{e} (run with --debug for more information)') from e
