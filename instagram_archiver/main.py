"""Main application."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import click

from .client import UnexpectedRedirect
from .constants import BROWSER_CHOICES
from .profile_scraper import ProfileScraper
from .saved_scraper import SavedScraper
from .utils import setup_logging

if TYPE_CHECKING:
    from .typing import BrowserName

__all__ = ('main',)


@click.command(context_settings={'help_option_names': ('-h', '--help')})
@click.option('-o',
              '--output-dir',
              default='%(username)s',
              help='Output directory.',
              type=click.Path(file_okay=False, writable=True))
@click.option('-b',
              '--browser',
              default='chrome',
              type=click.Choice(BROWSER_CHOICES),
              help='Browser to read cookies from.')
@click.option('-p', '--profile', default='Default', help='Browser profile.')
@click.option('-d', '--debug', is_flag=True, help='Enable debug output.')
@click.option('--no-log', is_flag=True, help='Ignore log (re-fetch everything).')
@click.option('-C',
              '--include-comments',
              is_flag=True,
              help='Also download all comments (extends download time significantly).')
@click.argument('username')
def main(output_dir: str,
         username: str,
         browser: BrowserName = 'chrome',
         profile: str = 'Default',
         *,
         debug: bool = False,
         include_comments: bool = False,
         no_log: bool = False) -> None:
    """Archive a profile's posts."""  # noqa: DOC501
    setup_logging(debug=debug)
    try:
        with ProfileScraper(browser=browser,
                            browser_profile=profile,
                            comments=include_comments,
                            disable_log=no_log,
                            output_dir=(Path(output_dir % {'username': username})
                                        if '%(username)s' in output_dir else Path(output_dir)),
                            username=username) as client:
            client.process()
    except UnexpectedRedirect as e:
        click.echo('Unexpected redirect. Assuming request limit has been reached.', err=True)
        raise click.Abort from e
    except Exception as e:
        if isinstance(e, KeyboardInterrupt) or debug:
            raise
        click.echo('Run with --debug for more information.', err=True)
        raise click.Abort from e


@click.command(context_settings={'help_option_names': ('-h', '--help')})
@click.option('-o',
              '--output-dir',
              default='.',
              help='Output directory.',
              type=click.Path(file_okay=False, writable=True))
@click.option('-b',
              '--browser',
              default='chrome',
              type=click.Choice(BROWSER_CHOICES),
              help='Browser to read cookies from.')
@click.option('-p', '--profile', default='Default', help='Browser profile.')
@click.option('-d', '--debug', is_flag=True, help='Enable debug output.')
@click.option('-C',
              '--include-comments',
              is_flag=True,
              help='Also download all comments (extends download time significantly).')
@click.option('-u', '--unsave', is_flag=True, help='Unsave posts after successful archive.')
def save_saved_main(output_dir: str,
                    browser: BrowserName = 'chrome',
                    profile: str = 'Default',
                    *,
                    debug: bool = False,
                    include_comments: bool = False,
                    unsave: bool = False) -> None:
    """Archive your saved posts."""  # noqa: DOC501
    setup_logging(debug=debug)
    try:
        SavedScraper(browser, profile, output_dir, comments=include_comments).process(unsave=unsave)
    except UnexpectedRedirect as e:
        click.echo('Unexpected redirect. Assuming request limit has been reached.', err=True)
        raise click.Abort from e
    except Exception as e:
        if isinstance(e, KeyboardInterrupt) or debug:
            raise
        click.echo('Run with --debug for more information.', err=True)
        raise click.Abort from e
