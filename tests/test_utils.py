from __future__ import annotations

from typing import TYPE_CHECKING
import json

from instagram_archiver.utils import (
    JSONFormattedString,
    UnknownMimetypeError,
    dump_json,
    get_extension,
    json_dumps_formatted,
    write_bytes,
    write_failed_urls,
    write_if_new,
)
import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_json_dumps_formatted(mocker: MockerFixture) -> None:
    obj = {'key': 'value'}
    formatted_json = json.dumps(obj, sort_keys=True, indent=2)
    mock_json_dumps = mocker.patch('instagram_archiver.utils.json.dumps',
                                   return_value=formatted_json)
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


def test_write_bytes(tmp_path: Path) -> None:
    target = tmp_path / 'binary.bin'
    write_bytes(target, b'\x00\x01\x02')
    assert target.read_bytes() == b'\x00\x01\x02'


def test_dump_json(tmp_path: Path) -> None:
    target = tmp_path / 'out.json'
    dump_json(target, {'b': 2, 'a': 1})
    parsed = json.loads(target.read_text(encoding='utf-8'))
    assert parsed == {'a': 1, 'b': 2}


def test_dump_json_writeplus(tmp_path: Path) -> None:
    target = tmp_path / 'out.json'
    dump_json(target, {'a': 1}, mode='w+')
    parsed = json.loads(target.read_text(encoding='utf-8'))
    assert parsed == {'a': 1}


def test_write_failed_urls(tmp_path: Path) -> None:
    target = tmp_path / 'failed.txt'
    write_failed_urls(target, ['https://a/', 'https://b/'])
    lines = target.read_text(encoding='utf-8').splitlines()
    assert lines == ['https://a/', 'https://b/']


def test_get_extension_jpeg() -> None:
    assert get_extension('image/jpeg') == 'jpg'


def test_get_extension_png() -> None:
    assert get_extension('image/png') == 'png'


def test_get_extension_webp() -> None:
    assert get_extension('image/webp') == 'webp'


def test_get_extension_unknown_mimetype() -> None:
    mimetype = 'application/fffffffffffffffffffffffffffffffff'
    with pytest.raises(UnknownMimetypeError) as exc_info:
        get_extension(mimetype)
    assert str(exc_info.value) == mimetype
