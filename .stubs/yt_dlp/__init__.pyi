from inspect import Traceback
from typing import Collection, Literal, Mapping, Protocol, Type, TypedDict
import re

SponsorBlockCategories = Literal['preview', 'selfpromo', 'interaction', 'music_offtopic', 'sponsor',
                                 'poi_highlight', 'intro', 'outro', 'filler', 'chapter']


class LoggerProto(Protocol):
    def debug(self, message: str) -> None:
        ...

    def info(self, message: str) -> None:
        ...

    def warning(self, message: str) -> None:
        ...

    def error(self, message: str) -> None:
        ...


class PostprocessorSponsorBlock(TypedDict):
    api: str
    categories: list[SponsorBlockCategories]
    key: Literal['SponsorBlock']
    when: str


class PostprocessorFFmpegSubtitlesConvertor(TypedDict):
    format: str
    key: Literal['FFmpegSubtitlesConvertor']
    when: str


class PostprocessorFFmpegEmbedSubtitle(TypedDict):
    already_have_subtitle: bool
    key: Literal['FFmpegEmbedSubtitle']


class PostprocessorModifyChapters(TypedDict):
    force_keyframes: bool
    key: Literal['ModifyChapters']
    remove_chapters_patterns: list[re.Pattern[str]] | None
    remove_ranges: list[tuple[float, float]] | None
    remove_sponsor_segments: list[SponsorBlockCategories] | None
    sponsorblock_chapter_title: str


class PostprocessorFFmpegMetadata(TypedDict):
    add_chapters: bool
    add_infojson: bool | str
    add_metadata: bool
    key: Literal['FFmpegMetadata']


class PostprocessorEmbedThumbnail(TypedDict):
    already_have_thumbnail: bool
    key: Literal['EmbedThumbnail']


class PostprocessorFFmpegConcat(TypedDict):
    key: Literal['FFmpegConcat']
    only_multi_video: bool
    when: str


class InfoJSON(TypedDict):
    _type: str
    extractor: str
    extractor_key: str
    id: str
    title: str


class YoutubeDLOptions(TypedDict, total=False):
    allowed_extractors: Collection[str] | None
    allsubtitles: bool
    cookiesfrombrowser: list[str | None] | None
    geo_bypass: bool
    getcomments: bool
    hls_use_mpegts: bool
    http_headers: Mapping[str, str] | None
    ignoreerrors: bool
    ignore_no_formats_error: bool
    logger: LoggerProto
    max_sleep_interval: float
    merge_output_format: str
    outtmpl: Mapping[str, str] | None
    overwrites: bool
    postprocessors: list[PostprocessorSponsorBlock | PostprocessorFFmpegSubtitlesConvertor
                         | PostprocessorFFmpegEmbedSubtitle | PostprocessorModifyChapters
                         | PostprocessorFFmpegMetadata | PostprocessorEmbedThumbnail
                         | PostprocessorFFmpegConcat] | None
    restrictfilenames: bool
    skip_unavailable_fragments: bool
    sleep_interval: float
    sleep_interval_requests: float
    sleep_interval_subtitles: float
    subtitleslangs: Collection[str] | None
    verbose: bool
    writeautomaticsub: bool
    writeinfojson: bool
    writesubtitles: bool
    writethumbnail: bool


class YoutubeDL:
    def __init__(self, options: YoutubeDLOptions) -> None:
        ...

    def __enter__(self) -> 'YoutubeDL':
        ...

    def __exit__(self, a: Type[BaseException], b: BaseException, c: Traceback) -> None:
        ...

    def extract_info(self, url: str, ie_key: str | None = ...) -> InfoJSON | None:
        ...
