from __future__ import annotations

from typing import TYPE_CHECKING
import json

from instagram_archiver.utils import (
    JSONFormattedString,
    UnknownMimetypeError,
    get_extension,
    json_dumps_formatted,
    write_if_new,
)
import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_json_dumps_formatted(mocker: MockerFixture) -> None:
    obj = {'key': 'value'}
    formatted_json = json.dumps(obj, sort_keys=True, indent=2)
    mock_json_dumps = mocker.patch(
        'instagram_archiver.utils.json.dumps', return_value=formatted_json
    )
    result = json_dumps_formatted(obj)
    assert isinstance(result, JSONFormattedString)
    assert result.formatted == formatted_json
    assert result.original_value == obj
    mock_json_dumps.assert_called_once_with(obj, sort_keys=True, indent=2)
    assert str(result) == formatted_json


def test_write_if_new_file_does_not_exist(mocker: MockerFixture) -> None:
    mock_is_file = mocker.patch('pathlib.Path.is_file', return_value=False)
    mock_open_file = mocker.patch('click.open_file', mocker.mock_open())

    target = 'test_file.txt'
    content = 'Test content'
    write_if_new(target, content)

    mock_is_file.assert_called_once_with()
    mock_open_file.assert_called_once_with(target, 'w')
    mock_open_file().write.assert_called_once_with(content)


def test_write_if_new_file_exists(mocker: MockerFixture) -> None:
    mock_is_file = mocker.patch('pathlib.Path.is_file', return_value=True)
    mock_open_file = mocker.patch('click.open_file', mocker.mock_open())

    target = 'test_file.txt'
    content = 'Test content'
    write_if_new(target, content)

    mock_is_file.assert_called_once_with()
    mock_open_file.assert_not_called()


def test_get_extension_jpeg(mocker: MockerFixture) -> None:
    mimetype = 'image/jpeg'
    result = get_extension(mimetype)
    assert result == 'jpg'


def test_get_extension_png(mocker: MockerFixture) -> None:
    mimetype = 'image/png'
    result = get_extension(mimetype)
    assert result == 'png'


def test_get_extension_unknown_mimetype(mocker: MockerFixture) -> None:
    mimetype = 'application/pdf'
    with pytest.raises(UnknownMimetypeError) as exc_info:
        get_extension(mimetype)
    assert str(exc_info.value) == mimetype
