from contextlib import contextmanager
from os import chdir as os_chdir, getcwd
from os.path import isfile
from pathlib import Path
from types import FrameType
from typing import Generic, Iterator, Literal, TypeVar
import json
import logging
import sys

from loguru import logger
import click

__all__ = ('UnknownMimetypeError', 'YoutubeDLLogger', 'chdir', 'get_extension',
           'json_dumps_formatted', 'setup_logging', 'write_if_new')

T = TypeVar('T')


class JSONFormattedString(Generic[T]):  # pylint: disable=too-few-public-methods
    def __init__(self, formatted: str, original: T) -> None:
        self.formatted = formatted
        self.original_value = original

    def __str__(self) -> str:
        return self.formatted


def json_dumps_formatted(obj: T) -> JSONFormattedString[T]:
    """Returns a special object with the formatted version of the JSON str and the original."""
    return JSONFormattedString(json.dumps(obj, sort_keys=True, indent=2), obj)


@contextmanager
def chdir(path: str | Path) -> Iterator[None]:
    """Context-managing ``chdir``. Changes to old path on exit."""
    old_path = getcwd()
    os_chdir(path)
    try:
        yield
    finally:
        chdir(old_path)


def write_if_new(target: Path | str, content: str | bytes, mode: str = 'w') -> None:
    """Write a file only if it will be a new file."""
    if not isfile(target):
        with click.open_file(str(target), mode) as f:
            f.write(content)


class UnknownMimetypeError(Exception):
    """Raised when an unknown mimetype is encountered in ``get_extension()``."""


def get_extension(mimetype: str) -> Literal['png', 'jpg']:
    """Gets the appropriate three-letter extension for a mimetype."""
    if mimetype == 'image/jpeg':
        return 'jpg'
    if mimetype == 'image/png':
        return 'png'
    raise UnknownMimetypeError(mimetype)


class InterceptHandler(logging.Handler):  # pragma: no cover
    """Intercept handler taken from Loguru's documentation."""
    def emit(self, record: logging.LogRecord) -> None:
        level: str | int
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # Find caller from where originated the logged message
        frame: FrameType | None = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_log_intercept_handler() -> None:  # pragma: no cover
    """Sets up Loguru to intercept records from the logging module."""
    logging.basicConfig(handlers=(InterceptHandler(),), level=0)


def setup_logging(debug: bool | None = False) -> None:
    """Shared function to enable logging."""
    if debug:  # pragma: no cover
        setup_log_intercept_handler()
        logger.enable('')
    else:
        logger.configure(handlers=(dict(
            format='<level>{message}</level>',
            level='INFO',
            sink=sys.stderr,
        ),))


class YoutubeDLLogger:
    """Basic logger front-end to loguru for use with ``YoutubeDL``."""
    def debug(self, message: str) -> None:
        if message.startswith('[debug] '):
            logger.debug(message)
        else:
            logger.info(message)

    def info(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        logger.warning(message)

    def error(self, message: str) -> None:
        logger.error(message)
