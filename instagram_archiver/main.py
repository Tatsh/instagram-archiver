"""Main application."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from requests import HTTPError
import click

from .client import AuthenticationError, InstagramClient
from .constants import BROWSER_CHOICES
from .utils import setup_logging

if TYPE_CHECKING:
    from .typing import BrowserName

__all__ = ('main',)


@click.command(context_settings={'help_option_names': ('-h', '--help')})
@click.option('-o',
              '--output-dir',
              default=None,
              help='Output directory.',
              type=click.Path(file_okay=False, path_type=Path, resolve_path=True, writable=True))
@click.option('-b',
              '--browser',
              default='chrome',
              type=click.Choice(BROWSER_CHOICES),
              help='Browser to read cookies from. Must match yt-dlp settings.')
@click.option('-p',
              '--profile',
              default='Default',
              help='Browser profile. Must match yt-dlp settings.')
@click.option('-d', '--debug', is_flag=True, help='Enable debug output.')
@click.option('--no-log', is_flag=True, help='Ignore log (re-fetch everything)')
@click.option('-C',
              '--include-comments',
              is_flag=True,
              help='Also download all comments (extends download time significantly).')
@click.argument('username', required=False)
def main(output_dir: Path | None,
         browser: BrowserName,
         profile: str,
         username: str | None = None,
         *,
         debug: bool = False,
         include_comments: bool = False,
         no_log: bool = False) -> None:
    """Archive a profile's posts."""  # noqa: DOC501
    setup_logging(debug=debug)
    if not username:
        raise click.BadOptionUsage('username', 'Username required in this case.')
    try:
        with InstagramClient(browser=browser,
                             browser_profile=profile,
                             comments=include_comments,
                             disable_log=no_log,
                             output_dir=output_dir,
                             username=username) as client:
            client.process()
    except (AuthenticationError, HTTPError) as e:
        click.echo(
            'You are probably not logged into Instagram in this browser profile or your session has'
            ' expired.',
            err=True)
        raise click.Abort from e
    except Exception as e:
        if isinstance(e, KeyboardInterrupt) or debug:
            raise
        click.echo('Run with --debug for more information.', err=True)
        raise click.Abort from e
