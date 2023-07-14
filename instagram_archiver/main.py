from pathlib import Path
import sys

from loguru import logger
from requests.exceptions import RetryError
import click

from .client import AuthenticationError, InstagramClient
from .constants import BROWSER_CHOICES
from .find_query_hashes import find_query_hashes
from .ig_typing import BrowserName
from .utils import setup_logging

__all__ = ('main',)


@click.command()
@click.option('-o',
              '--output-dir',
              default=None,
              help='Output directory',
              type=click.Path(file_okay=False, path_type=Path, resolve_path=True, writable=True))
@click.option('-b',
              '--browser',
              default='chrome',
              type=click.Choice(BROWSER_CHOICES),
              help='Browser to read cookies from')
@click.option('-p', '--profile', default='Default', help='Browser profile')
@click.option('-d', '--debug', is_flag=True, help='Enable debug output')
@click.option('--no-log', is_flag=True, help='Ignore log (re-fetch everything)')
@click.option('-C',
              '--include-comments',
              is_flag=True,
              help='Also download all comments (extends download time significantly).')
@click.option('--print-query-hashes',
              is_flag=True,
              help='Print current query hashes and exit.',
              hidden=True)
@click.argument('username', required=False)
def main(output_dir: Path | None,
         browser: BrowserName,
         profile: str,
         username: str | None = None,
         debug: bool = False,
         include_comments: bool = False,
         no_log: bool = False,
         print_query_hashes: bool = False) -> None:
    """Archive a profile's posts."""
    setup_logging(debug)
    if print_query_hashes:
        for query_hash in sorted(find_query_hashes(browser, profile)):
            click.echo(query_hash)
        return
    if not username:
        raise click.UsageError('Username is required')
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
