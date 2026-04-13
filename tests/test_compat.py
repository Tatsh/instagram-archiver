from __future__ import annotations

from pathlib import Path

from instagram_archiver.compat import chdir
import pytest


def test_chdir_changes_working_directory(tmp_path: Path) -> None:
    original = Path.cwd()
    nested = tmp_path / 'nested'
    nested.mkdir()
    with chdir(nested):
        assert Path.cwd() == nested
    assert Path.cwd() == original


def test_chdir_restores_after_exception(tmp_path: Path) -> None:
    original = Path.cwd()
    nested = tmp_path / 'nested'
    nested.mkdir()

    def boom_in_chdir() -> None:
        with chdir(nested):
            assert Path.cwd() == nested
            msg = 'boom'
            raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match='boom'):
        boom_in_chdir()
    assert Path.cwd() == original
