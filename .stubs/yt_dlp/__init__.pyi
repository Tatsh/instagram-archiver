from typing import Any, Collection, Iterable, Mapping

from yt_dlp.extractor.common import InfoExtractor

def parse_options(
        argv: list[str] | None = ...) -> tuple[Any, Any, Iterable[str], Mapping[str, Any]]:
    ...


class YoutubeDL:
    def __init__(self, options: Mapping[str, Any]) -> None:
        ...

    def __enter__(self) -> 'YoutubeDL':
        ...

    def __exit__(self, a: Any, b: Any, c: Any) -> None:
        ...

    def download(self, urls: Collection[str]) -> None:
        ...

    def add_info_extractor(self, ie: InfoExtractor) -> None:
        ...

    def extract_info(self, url: str, ie_key: str | None = ...) -> Any:
        ...

    def in_download_archive(self, info: Mapping[str, str]) -> bool:
        ...
