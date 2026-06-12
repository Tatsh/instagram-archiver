"""SQLite-backed dedup log shared by the scrapers."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse
import logging
import sqlite3

from .constants import LOG_SCHEMA

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ('LogDB', 'clean_url')

log = logging.getLogger(__name__)


def clean_url(url: str) -> str:
    """
    Normalise a URL for dedup lookup by stripping its query string and fragment.

    Parameters
    ----------
    url : str
        URL to normalise.

    Returns
    -------
    str
        URL with only its scheme, netloc, and path.
    """
    parsed = urlparse(url)
    return f'https://{parsed.netloc}{parsed.path}'


class LogDB:
    """SQLite-backed dedup log."""
    def __init__(self, path: Path, *, disabled: bool = False) -> None:
        """
        Initialise the dedup log.

        Parameters
        ----------
        path : Path
            Location of the SQLite database file.
        disabled : bool
            When ``True``, every operation becomes a no-op and :py:meth:`is_saved` always
            returns ``False``.
        """
        self._disabled = disabled
        self._path = path
        self._connection = sqlite3.connect(path)
        self._cursor = self._connection.cursor()
        self._setup()

    def _setup(self) -> None:
        if self._disabled:
            return
        existed = self._path.exists()
        if not existed or (existed and self._path.stat().st_size == 0):
            log.debug('Creating schema.')
            self._cursor.execute(LOG_SCHEMA)

    def is_saved(self, url: str) -> bool:
        """
        Check whether ``url`` has previously been recorded.

        Parameters
        ----------
        url : str
            URL to check.

        Returns
        -------
        bool
            ``True`` if the URL is in the log, ``False`` otherwise (or always when the log
            is disabled).
        """
        if self._disabled:
            return False
        self._cursor.execute('SELECT COUNT(url) FROM log WHERE url = ?', (clean_url(url),))
        count: int
        (count,) = self._cursor.fetchone()
        return count == 1

    def save(self, url: str) -> None:
        """
        Record ``url`` in the log.

        Parameters
        ----------
        url : str
            URL to record.
        """
        if self._disabled:
            return
        self._cursor.execute('INSERT INTO log (url) VALUES (?)', (clean_url(url),))
        self._connection.commit()

    def close(self) -> None:
        """Close the underlying cursor and connection."""
        self._cursor.close()
        self._connection.close()
