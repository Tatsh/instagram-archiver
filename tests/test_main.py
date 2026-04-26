from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from instagram_archiver.client import UnexpectedRedirect
from instagram_archiver.main import main, save_saved_main
import click

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import CliRunner
    from pytest_mock import MockerFixture


def test_main_invalid_browser(runner: CliRunner) -> None:
    result = runner.invoke(main, ['--browser', 'invalid_browser', 'testuser'])
    assert result.exit_code == 2
    assert "Invalid value for '-b' / '--browser'" in result.output


def test_main_help_option(runner: CliRunner) -> None:
    result = runner.invoke(main, ['-h'])
    assert result.exit_code == 0
    assert 'Usage: main [OPTIONS] USERNAME' in result.output
    assert "Archive a profile's posts." in result.output


def test_main_invokes_async_runner(runner: CliRunner, mocker: MockerFixture) -> None:
    mock_setup_logging = mocker.patch('instagram_archiver.main.setup_logging')
    mock_run = mocker.patch('instagram_archiver.main.asyncio.run')
    mock_async = mocker.patch('instagram_archiver.main._async_profile_main', new_callable=AsyncMock)
    result = runner.invoke(main, ['--debug', 'testuser'])
    assert result.exit_code == 0
    mock_setup_logging.assert_called_once_with(debug=True, loggers=mocker.ANY)
    mock_run.assert_called_once()
    mock_async.assert_called_once()


def test_main_unexpected_redirect(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=UnexpectedRedirect)
    result = runner.invoke(main, ['testuser'])
    assert result.exit_code == 1
    assert 'Unexpected redirect. Assuming request limit has been reached.' in result.output


def test_main_exception(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=Exception('Test exception'))
    result = runner.invoke(main, ['testuser'])
    assert result.exit_code == 1
    assert 'Run with --debug for more information.' in result.output


def test_main_exception_debug(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=Exception('Test exception'))
    result = runner.invoke(main, ['testuser', '-d'])
    assert result.exit_code == 1
    assert 'Run with --debug for more information.' not in result.output


def test_main_explicit_output_dir(runner: CliRunner, mocker: MockerFixture, tmp_path: Path) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mock_run = mocker.patch('instagram_archiver.main.asyncio.run')
    mock_async = mocker.patch('instagram_archiver.main._async_profile_main', new_callable=AsyncMock)
    result = runner.invoke(main, ['-o', str(tmp_path / 'foo'), 'tu'])
    assert result.exit_code == 0
    mock_run.assert_called_once()
    mock_async.assert_called_once()


def test_main_aborted(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=click.Abort)
    result = runner.invoke(main, ['testuser'])
    assert result.exit_code == 1


def test_main_keyboardinterrupt(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=KeyboardInterrupt)
    result = runner.invoke(main, ['testuser'])
    assert result.exit_code != 0


def test_save_saved_main_no_options(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mock_run = mocker.patch('instagram_archiver.main.asyncio.run')
    mock_async = mocker.patch('instagram_archiver.main._async_saved_main', new_callable=AsyncMock)
    result = runner.invoke(save_saved_main, [])
    assert result.exit_code == 0
    mock_run.assert_called_once()
    mock_async.assert_called_once()


def test_save_saved_main_debug_flag(runner: CliRunner, mocker: MockerFixture) -> None:
    mock_setup_logging = mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run')
    mocker.patch('instagram_archiver.main._async_saved_main', new_callable=AsyncMock)
    result = runner.invoke(save_saved_main, ['--debug'])
    assert result.exit_code == 0
    mock_setup_logging.assert_called_once_with(debug=True, loggers=mocker.ANY)


def test_save_saved_main_include_comments(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run')
    mock_async = mocker.patch('instagram_archiver.main._async_saved_main', new_callable=AsyncMock)
    result = runner.invoke(save_saved_main, ['--include-comments'])
    assert result.exit_code == 0
    assert mock_async.call_args.kwargs['include_comments'] is True


def test_save_saved_main_unsave_flag(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run')
    mock_async = mocker.patch('instagram_archiver.main._async_saved_main', new_callable=AsyncMock)
    result = runner.invoke(save_saved_main, ['--unsave'])
    assert result.exit_code == 0
    assert mock_async.call_args.kwargs['unsave'] is True


def test_save_saved_main_quiet_flag(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run')
    mock_async = mocker.patch('instagram_archiver.main._async_saved_main', new_callable=AsyncMock)
    result = runner.invoke(save_saved_main, ['--quiet'])
    assert result.exit_code == 0
    assert mock_async.call_args.kwargs['quiet'] is True


def test_save_saved_main_exception(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=Exception('Test exception'))
    result = runner.invoke(save_saved_main, [])
    assert result.exit_code == 1
    assert 'Run with --debug for more information.' in result.output


def test_save_saved_main_exception_debug(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=Exception('Test exception'))
    result = runner.invoke(save_saved_main, ['--debug'])
    assert result.exit_code == 1
    assert 'Run with --debug for more information.' not in result.output


def test_save_saved_main_unexpected_redirect(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=UnexpectedRedirect)
    result = runner.invoke(save_saved_main)
    assert result.exit_code == 1
    assert 'Unexpected redirect. Assuming request limit has been reached.' in result.output


def test_save_saved_main_keyboardinterrupt(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=KeyboardInterrupt)
    result = runner.invoke(save_saved_main)
    assert result.exit_code != 0


def test_save_saved_main_aborted(runner: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch('instagram_archiver.main.setup_logging')
    mocker.patch('instagram_archiver.main.asyncio.run', side_effect=click.Abort)
    result = runner.invoke(save_saved_main)
    assert result.exit_code == 1
