from typing import TYPE_CHECKING, Final, Mapping

from .utils import YoutubeDLLogger

__all__ = ('LOG_SCHEMA', 'RETRY_ABORT_NUM', 'SHARED_HEADERS', 'SHARED_YT_DLP_OPTIONS',
           'YT_DLP_SLEEP_INTERVAL', 'USER_AGENT')

if TYPE_CHECKING:
    from yt_dlp import YoutubeDLOptions

USER_AGENT: Final[str] = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/112.0.0.0 Safari/537.36')
# Do not set the x-ig-d header as this will cause API calls to return 404
SHARED_HEADERS: Final[Mapping[str, str]] = {
    'accept': ('text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,'
               'image/avif,image/webp,image/apng,*/*;q=0.8,'
               'application/signed-exchange;v=b3;q=0.9'),
    'accept-language': 'en,en-GB;q=0.9,en-US;q=0.8',
    'authority': 'www.instagram.com',
    'cache-control': 'no-cache',
    'dnt': '1',
    'pragma': 'no-cache',
    'referer': 'https://www.instagram.com',
    'upgrade-insecure-requests': '1',
    'user-agent': USER_AGENT,
    'viewport-width': '2560',
    'x-ig-app-id': '936619743392459'
}
LOG_SCHEMA: Final[str] = '''
CREATE TABLE log (
    url TEXT PRIMARY KEY NOT NULL,
    date TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL
);
'''
CALLS_PER_MINUTE: Final[int] = 10
YT_DLP_SLEEP_INTERVAL: Final[float] = 60 / CALLS_PER_MINUTE
#: Value taken from Instagram's JS under BootloaderConfig
RETRY_ABORT_NUM: Final[int] = 2
SHARED_YT_DLP_OPTIONS: 'YoutubeDLOptions' = {
    'allowed_extractors': ['Instagram.*'],
    'allsubtitles': True,
    'cookiesfrombrowser': None,
    'geo_bypass': True,
    'getcomments': False,
    'hls_use_mpegts': True,
    'http_headers': SHARED_HEADERS,
    'ignore_no_formats_error': True,
    'ignoreerrors': True,
    'logger': YoutubeDLLogger(),
    'outtmpl': {
        'default': '%(title).128s___src=%(extractor)s___id=%(id)s.%(ext)s',
        'pl_thumbnail': ''
    },
    'overwrites': False,
    'max_sleep_interval': 6.0,
    'merge_output_format': 'mkv',
    'postprocessors': [{
        'api': 'https://sponsor.ajay.app',
        'categories': [
            'preview', 'selfpromo', 'interaction', 'music_offtopic', 'sponsor', 'poi_highlight',
            'intro', 'outro', 'filler', 'chapter'
        ],
        'key': 'SponsorBlock',
        'when': 'after_filter'
    }, {
        'format': 'srt',
        'key': 'FFmpegSubtitlesConvertor',
        'when': 'before_dl'
    }, {
        'already_have_subtitle': True,
        'key': 'FFmpegEmbedSubtitle'
    }, {
        'force_keyframes': False,
        'key': 'ModifyChapters',
        'remove_chapters_patterns': [],
        'remove_ranges': [],
        'remove_sponsor_segments': [],
        'sponsorblock_chapter_title': '[SponsorBlock]: %(category_names)'
    }, {
        'add_chapters': True,
        'add_infojson': 'if_exists',
        'add_metadata': True,
        'key': 'FFmpegMetadata'
    }, {
        'already_have_thumbnail': False,
        'key': 'EmbedThumbnail'
    }, {
        'key': 'FFmpegConcat',
        'only_multi_video': True,
        'when': 'playlist'
    }],
    'restrictfilenames': True,
    'skip_unavailable_fragments': True,
    'sleep_interval': YT_DLP_SLEEP_INTERVAL,
    'sleep_interval_requests': YT_DLP_SLEEP_INTERVAL,
    'sleep_interval_subtitles': YT_DLP_SLEEP_INTERVAL,
    'subtitleslangs': ['all'],
    'verbose': False,
    'writeautomaticsub': True,
    'writesubtitles': True,
    'writeinfojson': True,
    'writethumbnail': True,
}
