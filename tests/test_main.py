from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from instagram_archiver.client import UnexpectedRedirect
from instagram_archiver.main import main, save_saved_main

if TYPE_CHECKING:
    from click.testing import CliRunner
    from pytest_mock import MockerFixture


def test_main_invalid_browser(runner: CliRunner) -> None:
    """Test main function raises error for invalid browser choice."""
    result = runner.invoke(main, ['--browser', 'invalid_browser', 'testuser'])
    assert result.exit_code == 2
    assert "Invalid value for '-b' / '--browser'" in result.output


def test_main_help_option(runner: CliRunner) -> None:
    """Test main function displays help message."""
    result = runner.invoke(main, ['-h'])
    assert result.exit_code == 0
    assert 'Usage: main [OPTIONS] USERNAME' in result.output
    assert "Archive a profile's posts." in result.output


def test_main_debug_flag(runner: CliRunner, mocker: MockerFixture) -> None:
    """Test main function with debug flag."""
    mock_setup_logging = mocker.patch('instagram_archiver.main.setup_logging')
    mock_client = mocker.patch('instagram_archiver.main.ProfileScraper', autospec=True)
    result = runner.invoke(main, ['--debug', 'testuser'])
    assert result.exit_code == 0
    mock_setup_logging.assert_called_once_with(debug=True, loggers=mocker.ANY)
    mock_client.assert_called_once_with(
        browser='chrome',
        browser_profile='Default',
        comments=False,
        disable_log=False,
        output_dir=Path('testuser'),
        username='testuser',
    )
    mock_client.return_value.__enter__.assert_called_once()
    mock_client.return_value.__exit__.assert_called_once()


def test_main_unexpected_redirect(runner: CliRunner, mocker: MockerFixture) -> None:
    mock_setup_logging = mocker.patch('instagram_archiver.main.setup_logging')
    mock_client = mocker.patch('instagram_archiver.main.ProfileScraper', autospec=True)

    mock_client.side_effect = UnexpectedRedirect('Test redirect')
    result = runner.invoke(main, ['testuser'])
    assert result.exit_code == 1
    assert 'Unexpected redirect. Assuming request limit has been reached.' in result.output
    mock_setup_logging.assert_called_once_with(debug=False, loggers=mocker.ANY)
    mock_client.assert_called_once_with(
        browser='chrome',
        browser_profile='Default',
        comments=False,
        disable_log=False,
        output_dir=Path('testuser'),
        username='testuser',
    )


def test_main_exception(runner: CliRunner, mocker: MockerFixture) -> None:
    """Test main function raises exception."""
    mock_client = mocker.patch('instagram_archiver.main.ProfileScraper', autospec=True)
    mock_client.side_effect = Exception('Test exception')
    result = runner.invoke(main, ['testuser'])
    assert result.exit_code == 1
    assert 'Run with --debug for more information.' in result.output
    mock_client.assert_called_once_with(
        browser='chrome',
        browser_profile='Default',
        comments=False,
        disable_log=False,
        output_dir=Path('testuser'),
        username='testuser',
    )


def test_main_exception_debug(runner: CliRunner, mocker: MockerFixture) -> None:
    """Test main function raises exception."""
    mock_client = mocker.patch('instagram_archiver.main.ProfileScraper', autospec=True)
    mock_client.side_effect = Exception('Test exception')
    result = runner.invoke(main, ['testuser', '-d'])
    assert result.exit_code == 1
    assert 'Run with --debug for more information.' not in result.output


def test_save_saved_main_no_options(runner: CliRunner, mocker: MockerFixture) -> None:
    """Test save_saved_main function with no options."""
    mock_setup_logging = mocker.patch('instagram_archiver.main.setup_logging')
    mock_scraper = mocker.patch('instagram_archiver.main.SavedScraper', autospec=True)
    result = runner.invoke(save_saved_main, [])
    assert result.exit_code == 0
    mock_setup_logging.assert_called_once_with(debug=False, loggers=mocker.ANY)
    mock_scraper.assert_called_once_with('chrome', 'Default', '.', comments=False)
    mock_scraper.return_value.process.assert_called_once_with(unsave=False)


def test_save_saved_main_debug_flag(runner: CliRunner, mocker: MockerFixture) -> None:
    """Test save_saved_main function with debug flag."""
    mock_setup_logging = mocker.patch('instagram_archiver.main.setup_logging')
    mock_scraper = mocker.patch('instagram_archiver.main.SavedScraper', autospec=True)
    result = runner.invoke(save_saved_main, ['--debug'])
    assert result.exit_code == 0
    mock_setup_logging.assert_called_once_with(debug=True, loggers=mocker.ANY)
    mock_scraper.assert_called_once_with('chrome', 'Default', '.', comments=False)
    mock_scraper.return_value.process.assert_called_once_with(unsave=False)


def test_save_saved_main_include_comments(runner: CliRunner, mocker: MockerFixture) -> None:
    """Test save_saved_main function with include-comments flag."""
    mock_setup_logging = mocker.patch('instagram_archiver.main.setup_logging')
    mock_scraper = mocker.patch('instagram_archiver.main.SavedScraper', autospec=True)
    result = runner.invoke(save_saved_main, ['--include-comments'])
    assert result.exit_code == 0
    mock_setup_logging.assert_called_once_with(debug=False, loggers=mocker.ANY)
    mock_scraper.assert_called_once_with('chrome', 'Default', '.', comments=True)
    mock_scraper.return_value.process.assert_called_once_with(unsave=False)


def test_save_saved_main_unsave_flag(runner: CliRunner, mocker: MockerFixture) -> None:
    """Test save_saved_main function with unsave flag."""
    mock_setup_logging = mocker.patch('instagram_archiver.main.setup_logging')
    mock_scraper = mocker.patch('instagram_archiver.main.SavedScraper', autospec=True)
    result = runner.invoke(save_saved_main, ['--unsave'])
    assert result.exit_code == 0
    mock_setup_logging.assert_called_once_with(debug=False, loggers=mocker.ANY)
    mock_scraper.assert_called_once_with('chrome', 'Default', '.', comments=False)
    mock_scraper.return_value.process.assert_called_once_with(unsave=True)


def test_save_saved_main_exception(runner: CliRunner, mocker: MockerFixture) -> None:
    """Test save_saved_main function raises exception."""
    mock_setup_logging = mocker.patch('instagram_archiver.main.setup_logging')
    mock_scraper = mocker.patch('instagram_archiver.main.SavedScraper', autospec=True)
    mock_scraper.return_value.process.side_effect = Exception('Test exception')
    result = runner.invoke(save_saved_main, [])
    assert result.exit_code == 1
    assert 'Run with --debug for more information.' in result.output
    mock_setup_logging.assert_called_once_with(debug=False, loggers=mocker.ANY)
    mock_scraper.assert_called_once_with('chrome', 'Default', '.', comments=False)
    mock_scraper.return_value.process.assert_called_once_with(unsave=False)


def test_save_saved_main_exception_debug(runner: CliRunner, mocker: MockerFixture) -> None:
    """Test save_saved_main function raises exception with debug flag."""
    mock_setup_logging = mocker.patch('instagram_archiver.main.setup_logging')
    mock_scraper = mocker.patch('instagram_archiver.main.SavedScraper', autospec=True)
    mock_scraper.return_value.process.side_effect = Exception('Test exception')
    result = runner.invoke(save_saved_main, ['--debug'])
    assert result.exit_code == 1
    assert 'Run with --debug for more information.' not in result.output
    mock_setup_logging.assert_called_once_with(debug=True, loggers=mocker.ANY)
    mock_scraper.assert_called_once_with('chrome', 'Default', '.', comments=False)
    mock_scraper.return_value.process.assert_called_once_with(unsave=False)


def test_save_saved_main_unexpected_redirect(runner: CliRunner, mocker: MockerFixture) -> None:
    mock_setup_logging = mocker.patch('instagram_archiver.main.setup_logging')
    mock_client = mocker.patch('instagram_archiver.main.SavedScraper', autospec=True)
    mock_client.side_effect = UnexpectedRedirect('Test redirect')
    result = runner.invoke(save_saved_main)
    assert result.exit_code == 1
    assert 'Unexpected redirect. Assuming request limit has been reached.' in result.output
    mock_setup_logging.assert_called_once_with(debug=False, loggers=mocker.ANY)
    mock_client.assert_called_once_with('chrome', 'Default', '.', comments=False)
