from contextlib import contextmanager
import json
from os import chdir as os_chdir, getcwd
from os.path import isfile
from pathlib import Path
from types import FrameType
from typing import Any, Iterator, Literal, Optional, Union
import logging
import sys

from loguru import logger
import click

__all__ = ('UnknownMimetypeError', 'chdir', 'get_extension',
           'json_dumps_formatted', 'write_if_new')


def json_dumps_formatted(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=2)


@contextmanager
def chdir(path: str | Path) -> Iterator[None]:
    old_path = getcwd()
    os_chdir(path)
    try:
        yield
    finally:
        chdir(old_path)


def write_if_new(target: Path | str,
                 content: str | bytes,
                 mode: str = 'w') -> None:
    if not isfile(target):
        with click.open_file(str(target), mode) as f:
            f.write(content)


class UnknownMimetypeError(Exception):
    pass


def get_extension(mimetype: str) -> Literal['png', 'jpg']:
    if mimetype == 'image/jpeg':
        return 'jpg'
    if mimetype == 'image/png':
        return 'png'
    raise UnknownMimetypeError(mimetype)


class InterceptHandler(logging.Handler):  # pragma: no cover
    """Intercept handler taken from Loguru's documentation."""
    def emit(self, record: logging.LogRecord) -> None:
        level: Union[str, int]
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # Find caller from where originated the logged message
        frame: Optional[FrameType] = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage())


def setup_log_intercept_handler() -> None:  # pragma: no cover
    """Sets up Loguru to intercept records from the logging module."""
    logging.basicConfig(handlers=(InterceptHandler(),), level=0)


def setup_logging(debug: Optional[bool] = False) -> None:
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
    def debug(self, message: str) -> None:
        if message.startswith('[debug] '):
            logger.debug(message)
        else:
            logger.info(message)

    def info(self, _: str) -> None:
        pass

    def warning(self, message: str) -> None:
        logger.warning(message)

    def error(self, message: str) -> None:
        logger.error(message)
