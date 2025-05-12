"""Utility functions."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeVar, override
import json
import logging
import logging.config

import click

if TYPE_CHECKING:
    from .typing import Edge

__all__ = ('JSONFormattedString', 'UnknownMimetypeError', 'get_extension', 'json_dumps_formatted',
           'setup_logging', 'write_if_new')

T = TypeVar('T')


def setup_logging(*,
                  debug: bool = False,
                  force_color: bool = False,
                  no_color: bool = False) -> None:  # pragma: no cover
    """Set up logging configuration."""
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': True,
        'root': {
            'handlers': ('console',),
            'level': 'DEBUG' if debug else 'INFO',
        },
        'formatters': {
            'default': {
                '()': 'colorlog.ColoredFormatter',
                'force_color': force_color,
                'format':
                    '%(log_color)s%(levelname)-8s%(reset)s | %(light_green)s%(name)s%(reset)s:'
                    '%(light_red)s%(funcName)s%(reset)s:%(blue)s%(lineno)d%(reset)s - %(message)s',
                'no_color': no_color,
            },
            'simple': {
                'format': '%(message)s',
            },
        },
        'handlers': {
            'console': {
                'class': 'colorlog.StreamHandler',
                'formatter': 'default' if debug else 'simple',
            },
        },
        'loggers': {
            'instagram_archiver': {
                'handlers': ('console',),
                'propagate': False,
            },
            'urllib3': {
                'handlers': ('console',),
                'propagate': False,
            }
        },
    })


class JSONFormattedString:
    """Contains a formatted version of the JSON str and the original value."""
    def __init__(self, formatted: str, original: Any) -> None:
        self.formatted = formatted
        """Formatted JSON string."""
        self.original_value = original
        """Original value."""

    @override
    def __str__(self) -> str:
        return self.formatted


def json_dumps_formatted(obj: Any) -> JSONFormattedString:
    """
    Return a special object with the formatted version of the JSON str and the original.

    Parameters
    ----------
    obj : Any
        The object to be formatted.
    """
    return JSONFormattedString(json.dumps(obj, sort_keys=True, indent=2), obj)


def write_if_new(target: Path | str, content: str | bytes, mode: str = 'w') -> None:
    """Write a file only if it will be a new file."""
    if not Path(target).is_file():
        with click.open_file(str(target), mode) as f:
            f.write(content)


class UnknownMimetypeError(Exception):
    """Raised when an unknown mimetype is encountered in :py:func:`~get_extension`."""


def get_extension(mimetype: str) -> Literal['png', 'jpg']:
    """
    Get the appropriate three-letter extension for a mimetype.

    Raises
    ------
    UnknownMimetypeError
        If the mimetype is not recognised.
    """
    if mimetype == 'image/jpeg':
        return 'jpg'
    if mimetype == 'image/png':
        return 'png'
    raise UnknownMimetypeError(mimetype)


if TYPE_CHECKING:

    class InstagramClientInterface(Protocol):
        should_save_comments: bool

        def save_comments(self, edge: Edge) -> None:
            ...
else:
    InstagramClientInterface = object


class SaveCommentsCheckDisabledMixin(InstagramClientInterface):
    """Mixin to control saving comments."""
    @override
    def save_comments(self, edge: Edge) -> None:
        if not self.should_save_comments:
            return
        super().save_comments(edge)  # type: ignore[safe-super]
