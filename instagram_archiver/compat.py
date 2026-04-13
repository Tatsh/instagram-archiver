"""Compatibility helpers for Python versions before 3.11."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
import os

if TYPE_CHECKING:
    from collections.abc import Generator

__all__ = ('chdir',)


@contextmanager
def chdir(path: str | Path) -> Generator[None, None, None]:
    """
    Temporarily change the current working directory.

    Parameters
    ----------
    path : str | Path
        Target directory.

    Yields
    ------
    None
        Execution continues with the working directory set to ``path``.
    """
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)
