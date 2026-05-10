"""Main application."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
import asyncio
import logging
import signal
import sys

from archiver_stats import STATUS_REFRESH_HZ, StatusDisplay
from bascom import setup_logging
from yt_dlp_utils.aio import get_configured_yt_dlp
import click

from .client import UnexpectedRedirect
from .constants import BROWSER_CHOICES
from .profile_scraper import ProfileScraper
from .saved_scraper import SavedScraper
from .typing import Stats, YTDLPState

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping
    from types import FrameType

    from .typing import BrowserName, OnMessage

__all__ = ('main',)

log = logging.getLogger(__name__)

_TERMINATION_SIGNALS = (signal.SIGINT, signal.SIGTERM)
_GENERIC_SHUTDOWN_MESSAGE = ('Termination requested. Finishing the in-flight work. Press '
                             'Ctrl+C (or send SIGTERM) again to force quit.')
_YT_DLP_ACTIVE_WARNING_MESSAGE = (
    'yt-dlp is still processing a download. Quitting now may corrupt the file. Press Ctrl+C '
    '(or send SIGTERM) again to force quit.')

_QUIET = {'level': 'WARNING'}


def _build_loggers(*, debug: bool) -> dict[str, dict[str, Any]]:
    """
    Build the ``loggers`` mapping for :py:func:`bascom.setup_logging`.

    ``urllib3.util.retry`` is always pinned to ``WARNING`` because its INFO chatter is
    routinely too noisy. When ``debug`` is ``False``, the package logger and ``yt_dlp_utils``
    are also pinned to ``WARNING`` so the live progress display is the only thing rendered
    on screen.

    Parameters
    ----------
    debug : bool
        Whether debug mode is active.

    Returns
    -------
    dict[str, dict[str, Any]]
        Mapping suitable for :py:func:`bascom.setup_logging`'s ``loggers`` keyword.
    """
    return {
        'instagram_archiver': {} if debug else _QUIET,
        'niquests': {},
        'quic': _QUIET,
        'urllib3': {},
        'urllib3.util.retry': _QUIET,
        'yt_dlp_utils': {} if debug else _QUIET,
    }


class _TerminationState:
    """Mutable state shared between signal handlers and ``_async_main``."""
    def __init__(self, yt_dlp_idle_event: asyncio.Event) -> None:
        self.signal_count = 0
        self.warning_task: asyncio.Task[None] | None = None
        self.yt_dlp_idle_event = yt_dlp_idle_event


def _show_status_message(display: StatusDisplay | None, message: str) -> None:
    if display is None:
        click.echo(message, err=True)
        return
    display.write(message)


def _set_transient_message(display: StatusDisplay | None, message: str) -> None:
    if display is None:
        click.echo(message, err=True)
        return
    display.set_message(message)


async def _cancel_task(task: asyncio.Task[None] | None) -> None:
    if task is None:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


def _make_termination_signal_handler(stop_event: asyncio.Event, scraper_task: asyncio.Task[None],
                                     display: StatusDisplay | None,
                                     state: _TerminationState) -> Callable[[], None]:
    async def _swap_warning_when_idle() -> None:
        try:
            await state.yt_dlp_idle_event.wait()
        except asyncio.CancelledError:
            return
        _set_transient_message(display, _GENERIC_SHUTDOWN_MESSAGE)

    def _handle_termination_signal() -> None:
        state.signal_count += 1
        if state.signal_count == 1:
            stop_event.set()
            if not state.yt_dlp_idle_event.is_set():
                _set_transient_message(display, _YT_DLP_ACTIVE_WARNING_MESSAGE)
                state.warning_task = asyncio.create_task(_swap_warning_when_idle())
            else:
                _show_status_message(display, _GENERIC_SHUTDOWN_MESSAGE)
            return
        _show_status_message(display, 'Force quit requested. Aborting in-flight work immediately.')
        scraper_task.cancel()

    return _handle_termination_signal


def _start_status_display(
        stats: Stats,
        stop_event: asyncio.Event) -> tuple[StatusDisplay, OnMessage, asyncio.Task[None]]:
    display = StatusDisplay(stats, stream=sys.stderr)
    display.start()

    def spin_update(message: str) -> None:
        display.set_message(message)

    async def _refresh_display() -> None:
        try:
            while not stop_event.is_set():
                display.refresh()
                await asyncio.sleep(1 / STATUS_REFRESH_HZ)
        except asyncio.CancelledError:
            return

    refresh_task = asyncio.create_task(_refresh_display())
    return display, spin_update, refresh_task


def _register_termination_signal_handlers(
        loop: asyncio.AbstractEventLoop, on_signal: Any
) -> tuple[list[signal.Signals], list[signal.Signals], dict[signal.Signals, Any]]:
    registered_loop_signals: list[signal.Signals] = []
    registered_windows_signal_handlers: list[signal.Signals] = []
    previous_windows_signal_handlers: dict[signal.Signals, Any] = {}
    try:
        for handled_signal in _TERMINATION_SIGNALS:
            loop.add_signal_handler(handled_signal, on_signal)
            registered_loop_signals.append(handled_signal)
    except NotImplementedError:
        for handled_signal in _TERMINATION_SIGNALS:
            previous_handler = _register_windows_signal_handler(handled_signal, on_signal)
            if previous_handler is None:
                continue
            previous_windows_signal_handlers[handled_signal] = previous_handler
            registered_windows_signal_handlers.append(handled_signal)
    return (registered_loop_signals, registered_windows_signal_handlers,
            previous_windows_signal_handlers)


def _register_windows_signal_handler(handled_signal: signal.Signals, on_signal: Any) -> Any | None:
    try:
        previous_handler = signal.getsignal(handled_signal)

        def _windows_signal_handler(_signum: int, _frame: FrameType | None) -> None:
            on_signal()

        signal.signal(handled_signal, _windows_signal_handler)
    except ValueError:
        return None
    else:
        return previous_handler


def _restore_termination_signal_handlers(
        loop: asyncio.AbstractEventLoop, registered_loop_signals: Iterable[signal.Signals],
        registered_windows_signal_handlers: Iterable[signal.Signals],
        previous_windows_signal_handlers: Mapping[signal.Signals, Any]) -> None:
    for handled_signal in registered_loop_signals:
        loop.remove_signal_handler(handled_signal)
    for handled_signal in registered_windows_signal_handlers:
        with suppress(ValueError):
            signal.signal(handled_signal, previous_windows_signal_handlers[handled_signal])


async def _drive_scraper(scraper: ProfileScraper | SavedScraper,
                         scraper_coro_factory: Callable[..., Any], *, debug: bool, quiet: bool,
                         sleep_time: int) -> None:
    async with scraper:
        ydl = get_configured_yt_dlp(sleep_time, debug=debug)
        for cookie in scraper.session.cookies:
            ydl.ydl.cookiejar.set_cookie(cookie)
        stats = Stats()
        yt_dlp_state = YTDLPState()
        yt_dlp_idle_event = asyncio.Event()
        yt_dlp_idle_event.set()
        termination_state = _TerminationState(yt_dlp_idle_event)
        display: StatusDisplay | None = None
        on_message: OnMessage | None = None
        refresh_task: asyncio.Task[None] | None = None
        stop_event = asyncio.Event()
        if not debug and not quiet:
            display, on_message, refresh_task = _start_status_display(stats, stop_event)

        def on_cleanup(message: str) -> None:
            if termination_state.signal_count == 0:
                return
            _show_status_message(display, message)

        loop = asyncio.get_running_loop()
        scraper_task: asyncio.Task[None] = asyncio.create_task(
            scraper_coro_factory(ydl,
                                 on_cleanup=on_cleanup,
                                 on_message=on_message,
                                 stats=stats,
                                 yt_dlp_idle_event=yt_dlp_idle_event,
                                 yt_dlp_state=yt_dlp_state))
        handler = _make_termination_signal_handler(stop_event, scraper_task, display,
                                                   termination_state)
        (registered_loop_signals, registered_windows_signal_handlers,
         previous_windows_signal_handlers) = _register_termination_signal_handlers(loop, handler)
        try:
            await scraper_task
        except asyncio.CancelledError as e:
            if termination_state.signal_count > 0:
                raise click.Abort from e
            raise
        finally:
            stop_event.set()
            await _cancel_task(termination_state.warning_task)
            await _cancel_task(refresh_task)
            if display is not None:
                display.stop()
            _restore_termination_signal_handlers(loop, registered_loop_signals,
                                                 registered_windows_signal_handlers,
                                                 previous_windows_signal_handlers)
        if termination_state.signal_count > 0:
            raise click.Abort


async def _async_profile_main(browser: BrowserName, profile: str, username: str, output_dir: Path,
                              *, debug: bool, include_child_comments: bool, include_comments: bool,
                              no_log: bool, quiet: bool, sleep_time: int) -> None:
    scraper = ProfileScraper(browser=browser,
                             browser_profile=profile,
                             child_comments=include_child_comments,
                             comments=include_comments,
                             disable_log=no_log,
                             output_dir=output_dir,
                             username=username)
    await _drive_scraper(scraper, scraper.process, debug=debug, quiet=quiet, sleep_time=sleep_time)


async def _async_saved_main(browser: BrowserName, profile: str, output_dir: str, *, debug: bool,
                            include_child_comments: bool, include_comments: bool, no_log: bool,
                            quiet: bool, sleep_time: int, unsave: bool) -> None:
    scraper = SavedScraper(browser,
                           profile,
                           output_dir,
                           child_comments=include_child_comments,
                           comments=include_comments,
                           disable_log=no_log)

    async def coro_factory(ydl: Any, **kwargs: Any) -> None:
        await scraper.process(ydl, unsave=unsave, **kwargs)

    await _drive_scraper(scraper, coro_factory, debug=debug, quiet=quiet, sleep_time=sleep_time)


@click.command(context_settings={'help_option_names': ('-h', '--help')})
@click.option('-o',
              '--output-dir',
              default=None,
              help='Output directory. Defaults to the username (profile mode) or `.` (saved mode).',
              type=click.Path(file_okay=False, writable=True))
@click.option('-b',
              '--browser',
              default='chrome',
              type=click.Choice(BROWSER_CHOICES),
              help='Browser to read cookies from.')
@click.option('-p', '--profile', default='Default', help='Browser profile.')
@click.option('-d', '--debug', is_flag=True, help='Enable debug output.')
@click.option('-q', '--quiet', is_flag=True, help='Disable progress display updates.')
@click.option('-S',
              '--sleep-time',
              default=1,
              type=int,
              help='Number of seconds yt-dlp waits between requests.')
@click.option('--no-log', is_flag=True, help='Ignore log (re-fetch everything).')
@click.option('-C',
              '--include-comments',
              is_flag=True,
              help='Also download all comments (extends download time significantly).')
@click.option('-R',
              '--include-child-comments',
              is_flag=True,
              help='Also recursively download child (reply) comments. Implies --include-comments.')
@click.option('-s',
              '--saved',
              'saved',
              is_flag=True,
              help='Archive your saved posts instead of a profile (mutually exclusive with '
              'USERNAME).')
@click.option('-u',
              '--unsave',
              is_flag=True,
              help='Unsave posts after successful archive (only with --saved).')
@click.argument('username', required=False)
def main(output_dir: str | None,
         username: str | None,
         browser: BrowserName = 'chrome',
         profile: str = 'Default',
         sleep_time: int = 1,
         *,
         debug: bool = False,
         include_child_comments: bool = False,
         include_comments: bool = False,
         no_log: bool = False,
         quiet: bool = False,
         saved: bool = False,
         unsave: bool = False) -> None:
    """
    Archive a profile (USERNAME) or your saved posts (--saved).

    Pass exactly one of: a USERNAME positional argument, or ``--saved``/``-s``.
    """  # noqa: DOC501
    if saved and username is not None:
        msg = 'USERNAME and --saved are mutually exclusive.'
        raise click.UsageError(msg)
    if not saved and username is None:
        msg = 'Provide a USERNAME or pass --saved/-s.'
        raise click.UsageError(msg)
    if unsave and not saved:
        msg = '--unsave only applies with --saved/-s.'
        raise click.UsageError(msg)
    setup_logging(debug=debug, loggers=cast('Any', _build_loggers(debug=debug)))
    try:
        if saved:
            resolved_saved_output_dir = output_dir if output_dir is not None else '.'
            asyncio.run(
                _async_saved_main(browser,
                                  profile,
                                  resolved_saved_output_dir,
                                  debug=debug,
                                  include_child_comments=include_child_comments,
                                  include_comments=include_comments,
                                  no_log=no_log,
                                  quiet=quiet,
                                  sleep_time=sleep_time,
                                  unsave=unsave))
        else:
            # `username` is non-None here because the validation above re-raises
            # ``UsageError`` when both `--saved` is unset and `username` is missing.
            profile_username = cast('str', username)
            resolved_profile_output_dir = (Path(output_dir % {'username': profile_username}) if
                                           (output_dir and '%(username)s' in output_dir) else Path(
                                               output_dir or profile_username))
            asyncio.run(
                _async_profile_main(browser,
                                    profile,
                                    profile_username,
                                    resolved_profile_output_dir,
                                    debug=debug,
                                    include_child_comments=include_child_comments,
                                    include_comments=include_comments,
                                    no_log=no_log,
                                    quiet=quiet,
                                    sleep_time=sleep_time))
    except UnexpectedRedirect as e:
        click.echo('Unexpected redirect. Assuming request limit has been reached.', err=True)
        raise click.Abort from e
    except click.Abort:
        raise
    except Exception as e:
        if isinstance(e, KeyboardInterrupt) or debug:
            raise
        click.echo('Run with --debug for more information.', err=True)
        raise click.Abort from e
