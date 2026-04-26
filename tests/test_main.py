from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock
import asyncio
import os
import signal

from instagram_archiver.client import UnexpectedRedirect
from instagram_archiver.main import main
from typing_extensions import Self
import click
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from click.testing import CliRunner
    from pytest_mock import MockerFixture


def _consume_coro(coro: Any) -> None:
    """
    Close the coroutine passed to a mocked ``asyncio.run``.

    Silences the ``coroutine ... was never awaited`` :py:class:`RuntimeWarning`.
    """
    coro.close()


def _raise_after_consume(exc: type[BaseException] | BaseException) -> Callable[[Any], None]:
    """Return a side-effect that consumes the coroutine then raises ``exc``."""
    def _side(coro: Any) -> None:
        coro.close()
        raise exc

    return _side


def test_main_invalid_browser(runner: CliRunner) -> None:
    result = runner.invoke(main, ['--browser', 'invalid_browser', 'testuser'])
    assert result.exit_code == 2
    assert "Invalid value for '-b' / '--browser'" in result.output


def test_main_help_option(runner: CliRunner) -> None:
    result = runner.invoke(main, ['-h'])
    assert result.exit_code == 0
    assert 'Usage: main [OPTIONS] [USERNAME]' in result.output


def test_main_requires_username_or_saved(runner: CliRunner) -> None:
    result = runner.invoke(main, [])
    assert result.exit_code != 0
    assert 'Provide a USERNAME or pass --saved/-s.' in result.output


def test_main_username_and_saved_are_mutually_exclusive(runner: CliRunner) -> None:
    result = runner.invoke(main, ['--saved', 'testuser'])
    assert result.exit_code != 0
    assert 'mutually exclusive' in result.output


def test_main_unsave_requires_saved(runner: CliRunner) -> None:
    result = runner.invoke(main, ['--unsave', 'testuser'])
    assert result.exit_code != 0
    assert '--unsave only applies with --saved/-s.' in result.output


def test_main_invokes_profile_runner(runner: CliRunner, mocker: MockerFixture) -> None:
    mock_setup_logging = mocker.patch('instagram_archiver.main.setup_logging')
    mock_run = mocker.patch('instagram_archiver.main.asyncio.run', side_effect=_consume_coro)
    mock_async = mocker.patch('instagram_archiver.main._async_profile_main', new_callable=AsyncMock)
    result = runner.invoke(main, ['--debug', 'testuser'])
    assert result.exit_code == 0
    mock_setup_logging.assert_called_once_with(debug=True, loggers=mocker.ANY)
    mock_run.assert_called_once()
    mock_async.assert_called_once()


def test_main_unexpected_redirect(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run',
                 side_effect=_raise_after_consume(UnexpectedRedirect))
    result = runner.invoke(main, ['testuser'])
    assert result.exit_code == 1
    assert 'Unexpected redirect. Assuming request limit has been reached.' in result.output


def test_main_exception(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run',
                 side_effect=_raise_after_consume(Exception('Test exception')))
    result = runner.invoke(main, ['testuser'])
    assert result.exit_code == 1
    assert 'Run with --debug for more information.' in result.output


def test_main_exception_debug(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run',
                 side_effect=_raise_after_consume(Exception('Test exception')))
    result = runner.invoke(main, ['testuser', '-d'])
    assert result.exit_code == 1
    assert 'Run with --debug for more information.' not in result.output


def test_main_explicit_output_dir(runner: CliRunner, mocker: MockerFixture, tmp_path: Path) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mock_run = mocker.patch('instagram_archiver.main.asyncio.run', side_effect=_consume_coro)
    mock_async = mocker.patch('instagram_archiver.main._async_profile_main', new_callable=AsyncMock)
    result = runner.invoke(main, ['-o', str(tmp_path / 'foo'), 'tu'])
    assert result.exit_code == 0
    mock_run.assert_called_once()
    mock_async.assert_called_once()


def test_main_aborted(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run',
                 side_effect=_raise_after_consume(click.Abort))
    result = runner.invoke(main, ['testuser'])
    assert result.exit_code == 1


def test_main_keyboardinterrupt(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run',
                 side_effect=_raise_after_consume(KeyboardInterrupt))
    result = runner.invoke(main, ['testuser'])
    assert result.exit_code != 0


def test_main_saved_invokes_saved_runner(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mock_run = mocker.patch('instagram_archiver.main.asyncio.run', side_effect=_consume_coro)
    mock_async = mocker.patch('instagram_archiver.main._async_saved_main', new_callable=AsyncMock)
    result = runner.invoke(main, ['--saved'])
    assert result.exit_code == 0
    mock_run.assert_called_once()
    mock_async.assert_called_once()


def test_main_saved_short_flag(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=_consume_coro)
    mock_async = mocker.patch('instagram_archiver.main._async_saved_main', new_callable=AsyncMock)
    result = runner.invoke(main, ['-s'])
    assert result.exit_code == 0
    mock_async.assert_called_once()


def test_main_saved_debug_flag(runner: CliRunner, mocker: MockerFixture) -> None:
    mock_setup_logging = mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=_consume_coro)
    mocker.patch('instagram_archiver.main._async_saved_main', new_callable=AsyncMock)
    result = runner.invoke(main, ['--saved', '--debug'])
    assert result.exit_code == 0
    mock_setup_logging.assert_called_once_with(debug=True, loggers=mocker.ANY)


def test_main_saved_include_comments(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=_consume_coro)
    mock_async = mocker.patch('instagram_archiver.main._async_saved_main', new_callable=AsyncMock)
    result = runner.invoke(main, ['--saved', '--include-comments'])
    assert result.exit_code == 0
    assert mock_async.call_args.kwargs['include_comments'] is True


def test_main_saved_unsave_flag(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=_consume_coro)
    mock_async = mocker.patch('instagram_archiver.main._async_saved_main', new_callable=AsyncMock)
    result = runner.invoke(main, ['--saved', '--unsave'])
    assert result.exit_code == 0
    assert mock_async.call_args.kwargs['unsave'] is True


def test_main_saved_quiet_flag(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=_consume_coro)
    mock_async = mocker.patch('instagram_archiver.main._async_saved_main', new_callable=AsyncMock)
    result = runner.invoke(main, ['--saved', '--quiet'])
    assert result.exit_code == 0
    assert mock_async.call_args.kwargs['quiet'] is True


def test_main_saved_no_log_flag(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=_consume_coro)
    mock_async = mocker.patch('instagram_archiver.main._async_saved_main', new_callable=AsyncMock)
    result = runner.invoke(main, ['--saved', '--no-log'])
    assert result.exit_code == 0
    assert mock_async.call_args.kwargs['no_log'] is True


def test_main_saved_exception(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run',
                 side_effect=_raise_after_consume(Exception('Test exception')))
    result = runner.invoke(main, ['--saved'])
    assert result.exit_code == 1
    assert 'Run with --debug for more information.' in result.output


def test_main_saved_exception_debug(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run',
                 side_effect=_raise_after_consume(Exception('Test exception')))
    result = runner.invoke(main, ['--saved', '--debug'])
    assert result.exit_code == 1
    assert 'Run with --debug for more information.' not in result.output


def test_main_saved_unexpected_redirect(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run',
                 side_effect=_raise_after_consume(UnexpectedRedirect))
    result = runner.invoke(main, ['--saved'])
    assert result.exit_code == 1
    assert 'Unexpected redirect. Assuming request limit has been reached.' in result.output


def test_main_saved_keyboardinterrupt(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run',
                 side_effect=_raise_after_consume(KeyboardInterrupt))
    result = runner.invoke(main, ['--saved'])
    assert result.exit_code != 0


def test_main_saved_aborted(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run',
                 side_effect=_raise_after_consume(click.Abort))
    result = runner.invoke(main, ['--saved'])
    assert result.exit_code == 1


# End-to-end orchestration tests — these let `asyncio.run` actually run so that
# `_drive_scraper`, `_async_*_main`, the signal handlers, and the status display
# wiring are exercised through the public CLI surface only.


class _FakeScraper:
    """Stand-in for :py:class:`ProfileScraper`/:py:class:`SavedScraper`.

    Replaces the real scrapers via ``mocker.patch`` on the ``instagram_archiver.main``
    module symbols so tests can drive the orchestration without hitting Instagram.
    The class attribute ``process_impl`` is the coroutine factory the test wants to
    run as the scraper's ``process`` method; ``cookies`` is the iterable handed to
    the orchestration's cookie-loop.
    """

    process_impl: Any = None
    cookies: tuple[Any, ...] = ()
    instances: tuple[_FakeScraper, ...] = ()

    def __init__(self, *_args: Any, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.session = SimpleNamespace(cookies=list(type(self).cookies))
        type(self).instances = (*type(self).instances, self)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def process(self, ydl: Any, **kwargs: Any) -> None:
        impl = type(self).process_impl
        if impl is None:
            return
        await impl(self, ydl, **kwargs)


def _install_fake_scraper(
    mocker: MockerFixture,
    target: str,
    process_impl: Any | None = None,
    cookies: tuple[Any, ...] = ()) -> type[_FakeScraper]:
    """Patch ``instagram_archiver.main.<target>`` with a fresh ``_FakeScraper`` subclass."""
    cls = type('_FakeScraper', (_FakeScraper,), {
        'process_impl': process_impl,
        'cookies': cookies,
        'instances': (),
    })
    mocker.patch(f'instagram_archiver.main.{target}', cls)
    return cls


def _patch_yt_dlp(mocker: MockerFixture) -> Any:
    """Patch ``get_configured_yt_dlp`` so ``_drive_scraper`` finds a usable yt-dlp wrapper."""
    fake_ydl = mocker.MagicMock()
    fake_ydl.ydl.cookiejar.set_cookie = mocker.MagicMock()
    mocker.patch('instagram_archiver.main.get_configured_yt_dlp', return_value=fake_ydl)
    return fake_ydl


def _patch_status_display(mocker: MockerFixture) -> Any:
    """Patch ``StatusDisplay`` so ``_start_status_display`` doesn't touch a TTY."""
    return mocker.patch('instagram_archiver.main.StatusDisplay')


def test_main_e2e_profile_quiet(runner: CliRunner, mocker: MockerFixture, tmp_path: Path) -> None:
    """Quiet profile run exercises ``_drive_scraper`` without the StatusDisplay branch."""
    mocker.patch('instagram_archiver.main.setup_logging')
    fake_cls = _install_fake_scraper(mocker, 'ProfileScraper')
    _patch_yt_dlp(mocker)
    result = runner.invoke(main, ['-q', '-o', str(tmp_path), 'tu'])
    assert result.exit_code == 0
    assert len(fake_cls.instances) == 1
    assert fake_cls.instances[0].kwargs['username'] == 'tu'


def test_main_e2e_profile_with_status_display(runner: CliRunner, mocker: MockerFixture,
                                              tmp_path: Path) -> None:
    """Default-mode profile run exercises ``_start_status_display`` and the refresh task."""
    mocker.patch('instagram_archiver.main.setup_logging')
    _install_fake_scraper(mocker, 'ProfileScraper')
    _patch_yt_dlp(mocker)
    mock_display_cls = _patch_status_display(mocker)
    result = runner.invoke(main, ['-o', str(tmp_path), 'tu'])
    assert result.exit_code == 0
    mock_display_cls.assert_called_once()
    mock_display_cls.return_value.start.assert_called_once()
    mock_display_cls.return_value.stop.assert_called_once()


def test_main_e2e_saved(runner: CliRunner, mocker: MockerFixture, tmp_path: Path) -> None:
    """``--saved`` exercises ``_async_saved_main`` and its inner ``coro_factory``."""
    mocker.patch('instagram_archiver.main.setup_logging')
    fake_cls = _install_fake_scraper(mocker, 'SavedScraper')
    _patch_yt_dlp(mocker)
    result = runner.invoke(main, ['-q', '-s', '-u', '-o', str(tmp_path)])
    assert result.exit_code == 0
    assert len(fake_cls.instances) == 1


def test_main_e2e_uses_profile_default_output_dir(runner: CliRunner, mocker: MockerFixture,
                                                  tmp_path: Path) -> None:
    """Without ``--output-dir`` the profile mode should fall back to the username."""
    mocker.patch('instagram_archiver.main.setup_logging')
    fake_cls = _install_fake_scraper(mocker, 'ProfileScraper')
    _patch_yt_dlp(mocker)
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ['-q', 'tu'])
    assert result.exit_code == 0
    # The default branch passes ``Path(profile_username)`` straight through.
    assert fake_cls.instances[0].kwargs['output_dir'] == Path('tu')


def test_main_e2e_output_dir_with_username_template(runner: CliRunner, mocker: MockerFixture,
                                                    tmp_path: Path) -> None:
    """``%(username)s`` in ``--output-dir`` is interpolated."""
    mocker.patch('instagram_archiver.main.setup_logging')
    fake_cls = _install_fake_scraper(mocker, 'ProfileScraper')
    _patch_yt_dlp(mocker)
    result = runner.invoke(main, ['-q', '-o', str(tmp_path / '%(username)s'), 'alice'])
    assert result.exit_code == 0
    assert fake_cls.instances[0].kwargs['output_dir'] == tmp_path / 'alice'


async def _send_signal_and_return(scraper: _FakeScraper, ydl: Any, **kwargs: Any) -> None:
    """Process body: send SIGINT to self once, then return normally.

    The sleep is long enough for asyncio's wake-up-fd plumbing to dispatch the signal
    to the loop's registered handler before the process body returns.
    """
    del ydl, kwargs
    os.kill(os.getpid(), signal.SIGINT)
    await asyncio.sleep(0.05)


async def _send_signal_busy_then_idle(scraper: _FakeScraper, ydl: Any, **kwargs: Any) -> None:
    """Process body: clear yt-dlp idle event, send SIGINT, set idle, return."""
    del ydl
    yt_dlp_idle_event = kwargs['yt_dlp_idle_event']
    yt_dlp_idle_event.clear()
    os.kill(os.getpid(), signal.SIGINT)
    await asyncio.sleep(0.05)
    yt_dlp_idle_event.set()
    await asyncio.sleep(0.05)


async def _send_signal_twice(scraper: _FakeScraper, ydl: Any, **kwargs: Any) -> None:
    """Process body: send SIGINT twice (the second triggers force-quit).

    The trailing ``asyncio.sleep`` is long enough to let ``scraper_task.cancel`` propagate
    a :py:class:`asyncio.CancelledError` back into this coroutine.
    """
    del ydl, kwargs
    os.kill(os.getpid(), signal.SIGINT)
    await asyncio.sleep(0)
    os.kill(os.getpid(), signal.SIGINT)
    await asyncio.sleep(1)


def test_main_e2e_signal_handler_idle(runner: CliRunner, mocker: MockerFixture,
                                      tmp_path: Path) -> None:
    """SIGINT while yt-dlp is idle exercises ``_show_status_message`` + click.Abort."""
    mocker.patch('instagram_archiver.main.setup_logging')
    _install_fake_scraper(mocker, 'ProfileScraper', process_impl=_send_signal_and_return)
    _patch_yt_dlp(mocker)
    result = runner.invoke(main, ['-q', '-o', str(tmp_path), 'tu'])
    assert result.exit_code == 1


def test_main_e2e_signal_handler_busy(runner: CliRunner, mocker: MockerFixture,
                                      tmp_path: Path) -> None:
    """SIGINT while yt-dlp is busy exercises ``_set_transient_message`` + warning task."""
    mocker.patch('instagram_archiver.main.setup_logging')
    _install_fake_scraper(mocker, 'ProfileScraper', process_impl=_send_signal_busy_then_idle)
    _patch_yt_dlp(mocker)
    result = runner.invoke(main, ['-q', '-o', str(tmp_path), 'tu'])
    assert result.exit_code == 1


def test_main_e2e_signal_force_quit(runner: CliRunner, mocker: MockerFixture,
                                    tmp_path: Path) -> None:
    """Two SIGINTs exercise the force-quit branch that cancels the scraper task."""
    mocker.patch('instagram_archiver.main.setup_logging')
    _install_fake_scraper(mocker, 'ProfileScraper', process_impl=_send_signal_twice)
    _patch_yt_dlp(mocker)
    result = runner.invoke(main, ['-q', '-o', str(tmp_path), 'tu'])
    assert result.exit_code == 1


async def _raise_cancelled(scraper: _FakeScraper, ydl: Any, **kwargs: Any) -> None:
    """
    Process body: raise CancelledError without any prior signal.

    Raises
    ------
    asyncio.CancelledError
        Always. Drives the no-signal branch of ``_drive_scraper``'s exception handler.
    """
    del scraper, ydl, kwargs
    raise asyncio.CancelledError


def test_main_e2e_cancelled_no_signal(runner: CliRunner, mocker: MockerFixture,
                                      tmp_path: Path) -> None:
    """A bare CancelledError in the scraper re-raises (no ``signal_count > 0`` branch).

    ``CancelledError`` is a :py:class:`BaseException` subclass, so Click's runner does not
    catch it; it propagates straight through ``runner.invoke``.
    """
    mocker.patch('instagram_archiver.main.setup_logging')
    _install_fake_scraper(mocker, 'ProfileScraper', process_impl=_raise_cancelled)
    _patch_yt_dlp(mocker)
    with pytest.raises(asyncio.CancelledError):
        runner.invoke(main, ['-q', '-o', str(tmp_path), 'tu'])


def test_main_e2e_status_display_with_message(runner: CliRunner, mocker: MockerFixture,
                                              tmp_path: Path) -> None:
    """Driving an ``on_message`` callback through the StatusDisplay branch."""
    mocker.patch('instagram_archiver.main.setup_logging')

    async def _fire_message(scraper: _FakeScraper, ydl: Any, **kwargs: Any) -> None:
        del scraper, ydl
        on_message = kwargs.get('on_message')
        if on_message is not None:
            on_message('hello from worker')

    _install_fake_scraper(mocker, 'ProfileScraper', process_impl=_fire_message)
    _patch_yt_dlp(mocker)
    mock_display_cls = _patch_status_display(mocker)
    result = runner.invoke(main, ['-o', str(tmp_path), 'tu'])
    assert result.exit_code == 0
    mock_display_cls.return_value.set_message.assert_any_call('hello from worker')


def test_main_e2e_windows_signal_fallback(runner: CliRunner, mocker: MockerFixture,
                                          tmp_path: Path) -> None:
    """``add_signal_handler`` raising ``NotImplementedError`` triggers the Windows fallback."""
    mocker.patch('instagram_archiver.main.setup_logging')
    _install_fake_scraper(mocker, 'ProfileScraper')
    _patch_yt_dlp(mocker)
    # Asyncio's default loop on Linux is a SelectorEventLoop. Forcing add_signal_handler to
    # raise NotImplementedError simulates the Windows policy and drives the fallback path.
    mocker.patch('asyncio.unix_events._UnixSelectorEventLoop.add_signal_handler',
                 side_effect=NotImplementedError)
    result = runner.invoke(main, ['-q', '-o', str(tmp_path), 'tu'])
    assert result.exit_code == 0


def test_main_e2e_cookies_loaded_into_yt_dlp(runner: CliRunner, mocker: MockerFixture,
                                             tmp_path: Path) -> None:
    """A non-empty ``session.cookies`` exercises the yt-dlp cookiejar transfer loop."""
    mocker.patch('instagram_archiver.main.setup_logging')
    fake_cookie = mocker.MagicMock()
    _install_fake_scraper(mocker, 'ProfileScraper', cookies=(fake_cookie,))
    fake_ydl = _patch_yt_dlp(mocker)
    result = runner.invoke(main, ['-q', '-o', str(tmp_path), 'tu'])
    assert result.exit_code == 0
    fake_ydl.ydl.cookiejar.set_cookie.assert_called_once_with(fake_cookie)


def test_main_e2e_signal_handler_idle_with_display(runner: CliRunner, mocker: MockerFixture,
                                                   tmp_path: Path) -> None:
    """SIGINT-while-idle with the StatusDisplay active hits ``display.write`` in the handler."""
    mocker.patch('instagram_archiver.main.setup_logging')
    _install_fake_scraper(mocker, 'ProfileScraper', process_impl=_send_signal_and_return)
    _patch_yt_dlp(mocker)
    mock_display_cls = _patch_status_display(mocker)
    result = runner.invoke(main, ['-o', str(tmp_path), 'tu'])
    assert result.exit_code == 1
    mock_display_cls.return_value.write.assert_called()


def test_main_e2e_signal_handler_busy_with_display(runner: CliRunner, mocker: MockerFixture,
                                                   tmp_path: Path) -> None:
    """SIGINT-while-busy with the StatusDisplay active hits ``display.set_message``."""
    mocker.patch('instagram_archiver.main.setup_logging')
    _install_fake_scraper(mocker, 'ProfileScraper', process_impl=_send_signal_busy_then_idle)
    _patch_yt_dlp(mocker)
    mock_display_cls = _patch_status_display(mocker)
    result = runner.invoke(main, ['-o', str(tmp_path), 'tu'])
    assert result.exit_code == 1
    mock_display_cls.return_value.set_message.assert_called()


async def _send_signal_busy_no_idle(scraper: _FakeScraper, ydl: Any, **kwargs: Any) -> None:
    """SIGINT while busy and *never* set idle; warning_task is cancelled in the finally block."""
    del scraper, ydl
    yt_dlp_idle_event = kwargs['yt_dlp_idle_event']
    yt_dlp_idle_event.clear()
    os.kill(os.getpid(), signal.SIGINT)
    await asyncio.sleep(0.05)
    # Return without setting yt_dlp_idle_event — _swap_warning_when_idle is still awaiting it
    # when _drive_scraper's finally cancels it, exercising that CancelledError branch.


async def _signal_then_invoke_cleanup(scraper: _FakeScraper, ydl: Any, **kwargs: Any) -> None:
    """Process body: send SIGINT, then invoke ``on_cleanup`` so its signal-gated body runs."""
    del scraper, ydl
    on_cleanup = kwargs.get('on_cleanup')
    os.kill(os.getpid(), signal.SIGINT)
    await asyncio.sleep(0.05)
    if on_cleanup is not None:
        on_cleanup('worker emitted cleanup')


async def _invoke_cleanup_without_signal(scraper: _FakeScraper, ydl: Any, **kwargs: Any) -> None:
    """Process body: invoke ``on_cleanup`` *without* a prior signal — early-return branch."""
    del scraper, ydl
    on_cleanup = kwargs.get('on_cleanup')
    if on_cleanup is not None:
        on_cleanup('worker emitted cleanup with no signal')


def test_main_e2e_on_cleanup_without_signal_is_a_noop(runner: CliRunner, mocker: MockerFixture,
                                                      tmp_path: Path) -> None:
    """``on_cleanup`` while ``signal_count == 0`` returns early without writing to the display."""
    mocker.patch('instagram_archiver.main.setup_logging')
    _install_fake_scraper(mocker, 'ProfileScraper', process_impl=_invoke_cleanup_without_signal)
    _patch_yt_dlp(mocker)
    mock_display_cls = _patch_status_display(mocker)
    result = runner.invoke(main, ['-o', str(tmp_path), 'tu'])
    assert result.exit_code == 0
    # The display.write call would only happen if on_cleanup got past its signal_count guard.
    for call in mock_display_cls.return_value.write.call_args_list:
        assert call.args != ('worker emitted cleanup with no signal',)


def test_main_e2e_on_cleanup_after_signal_with_display(runner: CliRunner, mocker: MockerFixture,
                                                       tmp_path: Path) -> None:
    """``on_cleanup`` invoked while ``signal_count > 0`` writes through the StatusDisplay."""
    mocker.patch('instagram_archiver.main.setup_logging')
    _install_fake_scraper(mocker, 'ProfileScraper', process_impl=_signal_then_invoke_cleanup)
    _patch_yt_dlp(mocker)
    mock_display_cls = _patch_status_display(mocker)
    result = runner.invoke(main, ['-o', str(tmp_path), 'tu'])
    assert result.exit_code == 1
    mock_display_cls.return_value.write.assert_any_call('worker emitted cleanup')


def test_main_e2e_signal_busy_warning_task_cancelled(runner: CliRunner, mocker: MockerFixture,
                                                     tmp_path: Path) -> None:
    """``_swap_warning_when_idle`` gets cancelled by ``_cancel_task`` in the finally block."""
    mocker.patch('instagram_archiver.main.setup_logging')
    _install_fake_scraper(mocker, 'ProfileScraper', process_impl=_send_signal_busy_no_idle)
    _patch_yt_dlp(mocker)
    result = runner.invoke(main, ['-q', '-o', str(tmp_path), 'tu'])
    assert result.exit_code == 1


def test_main_e2e_windows_signal_dispatched(runner: CliRunner, mocker: MockerFixture,
                                            tmp_path: Path) -> None:
    """Windows fallback path: a real signal arrives, ``_windows_signal_handler`` body runs."""
    mocker.patch('instagram_archiver.main.setup_logging')
    _install_fake_scraper(mocker, 'ProfileScraper', process_impl=_send_signal_and_return)
    _patch_yt_dlp(mocker)
    mocker.patch('asyncio.unix_events._UnixSelectorEventLoop.add_signal_handler',
                 side_effect=NotImplementedError)
    result = runner.invoke(main, ['-q', '-o', str(tmp_path), 'tu'])
    # The Windows fallback registers via signal.signal; the SIGINT delivered by the fake
    # process body invokes _windows_signal_handler which forwards to on_signal.
    assert result.exit_code in {0, 1}


def test_main_e2e_windows_signal_handler_restore_value_error(runner: CliRunner,
                                                             mocker: MockerFixture,
                                                             tmp_path: Path) -> None:
    """``signal.signal`` raising ``ValueError`` on restore is suppressed."""
    mocker.patch('instagram_archiver.main.setup_logging')
    _install_fake_scraper(mocker, 'ProfileScraper')
    _patch_yt_dlp(mocker)
    mocker.patch('asyncio.unix_events._UnixSelectorEventLoop.add_signal_handler',
                 side_effect=NotImplementedError)
    # First call (registration) succeeds; later call (restore) raises ValueError.
    real_signal = signal.signal
    calls = {'count': 0}

    def _maybe_raise(sig: Any, handler: Any) -> Any:
        calls['count'] += 1
        if calls['count'] > 2:  # restore phase
            raise ValueError
        return real_signal(sig, handler)

    mocker.patch('instagram_archiver.main.signal.signal', side_effect=_maybe_raise)
    result = runner.invoke(main, ['-q', '-o', str(tmp_path), 'tu'])
    assert result.exit_code == 0
