from os.path import isfile
from pathlib import Path
from types import FrameType
from typing import (Any, Iterable, Iterator, Literal, Optional, Sequence, Set,
                    TypeVar, Union)
import json
import logging
import subprocess as sp
import sys

from loguru import logger
import click

__all__ = ('UnknownMimetypeError', 'call_node_json', 'chunks', 'get_extension',
           'write_if_new')


def call_node_json(content: str) -> Any:
    with sp.Popen(('node',),
                  text=True,
                  stderr=sp.PIPE,
                  stdin=sp.PIPE,
                  stdout=sp.PIPE) as proc:
        return json.loads(proc.communicate(content, timeout=5)[0].strip())


def write_if_new(target: Union[Path, str],
                 content: Union[str, bytes],
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


T = TypeVar('T')


def chunks(seq: Sequence[T], n: int) -> Iterator[Iterator[T]]:
    for i in range(0, len(seq), n):
        yield iter(seq[i:i + n])


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


def unique_iter(seq: Iterable[T]) -> Iterator[T]:
    """https://stackoverflow.com/a/480227/374110"""
    seen: Set[T] = set()
    seen_add = seen.add
    return (x for x in seq if not (x in seen or seen_add(x)))


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
