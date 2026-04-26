from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

from instagram_archiver.client import UnexpectedRedirect
from instagram_archiver.main import main
import click

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

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
