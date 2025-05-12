"""Instagram client."""
from __future__ import annotations

from contextlib import chdir
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, override
from urllib.parse import urlparse
import json
import logging
import sqlite3

from requests import HTTPError
from yt_dlp_utils import get_configured_yt_dlp

from .client import InstagramClient
from .constants import LOG_SCHEMA
from .typing import (
    BrowserName,
    WebProfileInfo,
    XDTAPIV1FeedUserTimelineGraphQLConnectionContainer,
)
from .utils import SaveCommentsCheckDisabledMixin

if TYPE_CHECKING:
    from types import TracebackType

__all__ = ('ProfileScraper',)

T = TypeVar('T')
log = logging.getLogger(__name__)


def _clean_url(url: str) -> str:
    parsed = urlparse(url)
    return f'https://{parsed.netloc}{parsed.path}'


class ProfileScraper(SaveCommentsCheckDisabledMixin, InstagramClient):
    """The scraper."""
    def __init__(self,
                 username: str,
                 *,
                 log_file: str | Path | None = None,
                 output_dir: str | Path | None = None,
                 disable_log: bool = False,
                 browser: BrowserName = 'chrome',
                 browser_profile: str = 'Default',
                 comments: bool = False) -> None:
        """
        Initialise ``ProfileScraper``.

        Parameters
        ----------
        username : str
            The username to scrape.
        log_file : str | Path | None
            The log file to use.
        output_dir : str | Path | None
            The output directory to save the posts to.
        disable_log : bool
            Whether to disable logging or not.
        browser : BrowserName
            The browser to use.
        browser_profile : str
            The browser profile to use.
        comments : bool
            Whether to save comments or not.
        """
        super().__init__(browser, browser_profile)
        self._no_log = disable_log
        self._output_dir = Path(output_dir or Path.cwd() / username)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._log_db = Path(log_file or self._output_dir / '.log.db')
        self._connection = sqlite3.connect(self._log_db)
        self._cursor = self._connection.cursor()
        self._setup_db()
        self._username = username
        self.should_save_comments = comments

    def _setup_db(self) -> None:
        if self._no_log:
            return
        existed = self._log_db.exists()
        if not existed or (existed and self._log_db.stat().st_size == 0):
            log.debug('Creating schema.')
            self._cursor.execute(LOG_SCHEMA)

    @override
    def save_to_log(self, url: str) -> None:
        if self._no_log:
            return
        self._cursor.execute('INSERT INTO log (url) VALUES (?)', (_clean_url(url),))
        self._connection.commit()

    @override
    def is_saved(self, url: str) -> bool:
        if self._no_log:
            return False
        self._cursor.execute('SELECT COUNT(url) FROM log WHERE url = ?', (_clean_url(url),))
        count: int
        count, = self._cursor.fetchone()
        return count == 1

    @override
    def __exit__(self, _: type[BaseException] | None, __: BaseException | None,
                 ___: TracebackType | None) -> None:
        """Clean up."""
        self._cursor.close()
        self._connection.close()

    def process(self) -> None:
        """Process posts."""
        with chdir(self._output_dir):
            self.get_text(f'https://www.instagram.com/{self._username}/')
            self.add_csrf_token_header()
            r = self.get_json('https://i.instagram.com/api/v1/users/web_profile_info/',
                              params={'username': self._username},
                              cast_to=WebProfileInfo)
            with Path('web_profile_info.json').open('w', encoding='utf-8') as f:
                json.dump(r, f, indent=2, sort_keys=True)
            user_info = r['data']['user']
            if not self.is_saved(user_info['profile_pic_url_hd']):
                with Path('profile_pic.jpg').open('wb') as f:
                    f.writelines(
                        self.session.get(user_info['profile_pic_url_hd'],
                                         stream=True).iter_content(chunk_size=512))
                self.save_to_log(user_info['profile_pic_url_hd'])
            try:
                for item in self.highlights_tray(user_info['id'])['tray']:
                    self.add_video_url('https://www.instagram.com/stories/highlights/'
                                       f'{item["id"].split(":")[-1]}/')
            except HTTPError:
                log.exception('Failed to get highlights data.')
            self.save_edges(user_info['edge_owner_to_timeline_media']['edges'])
            d = self.graphql_query(
                {
                    'data': {
                        'count': 12,
                        'include_reel_media_seen_timestamp': True,
                        'include_relationship_info': True,
                        'latest_besties_reel_media': True,
                        'latest_reel_media': True
                    },
                    'username': self._username,
                    '__relay_internal__pv__PolarisIsLoggedInrelayprovider': True,
                    '__relay_internal__pv__PolarisShareSheetV3relayprovider': True,
                },
                cast_to=XDTAPIV1FeedUserTimelineGraphQLConnectionContainer)
            if not d:
                log.error('First GraphQL query failed.')
            else:
                self.save_edges(d['xdt_api__v1__feed__user_timeline_graphql_connection']['edges'])
                page_info = d['xdt_api__v1__feed__user_timeline_graphql_connection']['page_info']
                while page_info['has_next_page']:
                    d = self.graphql_query(
                        {
                            'after': page_info['end_cursor'],
                            'before': None,
                            'data': {
                                'count': 12,
                                'include_reel_media_seen_timestamp': True,
                                'include_relationship_info': True,
                                'latest_besties_reel_media': True,
                                'latest_reel_media': True,
                            },
                            'first': 12,
                            'last': None,
                            'username': self._username,
                            '__relay_internal__pv__PolarisIsLoggedInrelayprovider': True,
                            '__relay_internal__pv__PolarisShareSheetV3relayprovider': True,
                        },
                        cast_to=XDTAPIV1FeedUserTimelineGraphQLConnectionContainer)
                    if not d:
                        break
                    page_info = d['xdt_api__v1__feed__user_timeline_graphql_connection'][
                        'page_info']
                    self.save_edges(
                        d['xdt_api__v1__feed__user_timeline_graphql_connection']['edges'])
            if self.video_urls:
                with get_configured_yt_dlp() as ydl:
                    while self.video_urls and (url := self.video_urls.pop()):
                        if self.is_saved(url):
                            log.info('`%s` is already saved.', url)
                            continue
                        if ydl.extract_info(url):
                            log.info('Extracting `%s`.', url)
                            self.save_to_log(url)
                        else:
                            self.failed_urls.add(url)
            if self.failed_urls:
                log.warning('Some video URIs failed. Check failed.txt.')
                with Path('failed.txt').open('w', encoding='utf-8') as f:
                    for url in self.failed_urls:
                        f.write(f'{url}\n')
