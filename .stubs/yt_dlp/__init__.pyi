from typing import Any, Iterable, List, Mapping, Optional, Sequence, Tuple
from yt_dlp.extractor.common import InfoExtractor


def parse_options(
    argv: Optional[List[str]] = ...
) -> Tuple[Any, Any, Iterable[str], Mapping[str, Any]]:
    ...


class YoutubeDL:
    def __init__(self, options: Mapping[str, Any]) -> None:
        ...

    def __enter__(self) -> 'YoutubeDL':
        ...

    def __exit__(self, a: Any, b: Any, c: Any) -> None:
        ...

    def download(self, urls: Sequence[str]) -> None:
        ...

    def add_info_extractor(self, ie: InfoExtractor) -> None:
        ...

    def extract_info(self, url: str, ie_key: Optional[str] = ...) -> Any:
        ...

    def in_download_archive(self, info: Mapping[str, str]) -> bool:
        ...
