from enum import Enum
from http.cookiejar import Cookie
from typing import Collection, Literal, Protocol

from yt_dlp import YoutubeDL

class _LinuxKeyring(Enum):
    KWALLET = ...
    GNOMEKEYRING = ...
    BASICTEXT = ...


class YDLLoggerProto(Protocol):
    def __init__(self, ydl: YoutubeDL | None = ...) -> None:
        ...

    def debug(self, message: str) -> None:
        ...

    def info(self, message: str) -> None:
        ...

    def warning(self, message: str, only_once: bool = False) -> None:
        ...

    def error(self, message: str) -> None:
        ...

    def progress_bar(self) -> None:
        ...


def extract_cookies_from_browser(browser: Literal['brave', 'chrome', 'chromium', 'edge', 'opera',
                                                  'vivaldi', 'firefox', 'safari'],
                                 profile: str = ...,
                                 logger: YDLLoggerProto = ...,
                                 *,
                                 keyring: _LinuxKeyring = ...) -> Collection[Cookie]:
    ...
