from inspect import Traceback
from os import makedirs, utime
from pathlib import Path
from pprint import pprint as pp
from typing import Any, Mapping, Sequence, Type
from urllib.parse import urlparse
import json
import re
import sqlite3
import sys

from loguru import logger
from ratelimit import limits, sleep_and_retry
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from yt_dlp.cookies import extract_cookies_from_browser
import requests
import yt_dlp

from .constants import LOG_SCHEMA, SHARED_HEADERS
from .utils import YoutubeDLLogger, chdir, get_extension, json_dumps_formatted, write_if_new


def _clean_url(url: str) -> str:
    parsed = urlparse(url)
    return f'https://{parsed.netloc}{parsed.path}'


class AuthenticationError(Exception):
    pass


class InstagramClient:
    def __init__(self,
                 *,
                 username: str,
                 log_file: str | Path | None = None,
                 output_dir: str | None = None,
                 disable_log: bool = False,
                 backoff_factor: float = 2.5,
                 status_forcelist: Sequence[int] | None = None,
                 browser: str = 'chrome',
                 browser_profile: str = 'Default',
                 debug: bool = False) -> None:
        self._no_log = disable_log
        self._session = requests.Session()
        self._setup_session(status_forcelist, backoff_factor, browser,
                            browser_profile)
        self._output_dir = Path(output_dir or Path('.').resolve() / username)
        makedirs(self._output_dir, exist_ok=True)
        self._log_db = Path(log_file or self._output_dir / '.log.db')
        self._connection = sqlite3.connect(self._log_db)
        self._cursor = self._connection.cursor()
        self._setup_db()
        self._username = username
        self._video_urls: list[str] = []
        self._debug = debug

    def _setup_db(self) -> None:
        existed = self._log_db.exists()
        if not existed or (existed and self._log_db.stat().st_size == 0):
            logger.debug('Creating schema')
            self._cursor.execute(LOG_SCHEMA)

    def _setup_session(self,
                       status_forcelist: Sequence[int] | None = None,
                       backoff_factor: float = 2.5,
                       browser: str = 'chrome',
                       browser_profile: str = 'Default') -> None:
        self._session.mount(
            'https://',
            HTTPAdapter(
                max_retries=Retry(backoff_factor=backoff_factor,
                                  status_forcelist=status_forcelist or (
                                      429, 500, 502, 503, 504))))
        self._session.headers.update({
            **SHARED_HEADERS,
            **dict(cookie='; '.join(f'{cookie.name}={cookie.value}' \
                for cookie in extract_cookies_from_browser(browser, browser_profile)
                    if 'instagram.com' in cookie.domain))
        })
        r = self._get_rate_limited('https://www.instagram.com',
                                   return_json=False)
        m = re.search(r'"config":{"csrf_token":"([^"]+)"', r.text)
        assert m is not None
        self._session.headers.update({'x-csrftoken': m.group(1)})

    def _save_to_log(self, url: str) -> None:
        if self._no_log:
            return
        self._cursor.execute('INSERT INTO log (url) VALUES (?)',
                             (_clean_url(url),))
        self._connection.commit()

    def _is_saved(self, url: str) -> bool:
        if self._no_log:
            return False
        self._cursor.execute('SELECT COUNT(url) FROM log WHERE url = ?',
                             (_clean_url(url),))
        count: int
        count, = self._cursor.fetchone()
        return count == 1

    def _save_image_versions2(self, sub_item: Any, timestamp: int) -> None:
        def key(x: Mapping[str, int]) -> int:
            return x['width'] * x['height']

        best = sorted(sub_item['image_versions2']['candidates'],
                      key=key,
                      reverse=True)[0]
        if self._is_saved(best['url']):
            return
        r = self._get_rate_limited(best['url'], return_json=False)
        ext = get_extension(r.headers['content-type'])
        name = f'{sub_item["id"]}.{ext}'
        write_if_new(name, r.content, 'wb')
        utime(name, (timestamp, timestamp))
        self._save_to_log(r.url)

    def _save_media(self, edge: Any) -> None:
        media_info_url = ('https://i.instagram.com/api/v1/media/'
                          f'{edge["node"]["id"]}/info/')
        if self._is_saved(media_info_url):
            return
        r = self._get_rate_limited(media_info_url, return_json=False)
        if '/login' in r.url:
            raise AuthenticationError('Are you logged in?')
        media_info = r.json()
        if media_info['more_available']:
            pp(media_info)
            raise ValueError('Unhandled more_available')
        timestamp = media_info['items'][0]['taken_at']
        id_json_file = f'{edge["node"]["id"]}.json'
        media_info_json_file = f'{edge["node"]["id"]}-media-info-0000.json'
        write_if_new(id_json_file, json_dumps_formatted(edge['node']))
        write_if_new(media_info_json_file, json_dumps_formatted(media_info))
        for file in (id_json_file, media_info_json_file):
            utime(file, (timestamp, timestamp))
        self._save_to_log(media_info_url)
        for item in media_info['items']:
            timestamp = item['taken_at']
            if 'carousel_media' in item:
                for sub_item in item['carousel_media']:
                    self._save_image_versions2(sub_item, timestamp)
            elif 'image_versions2' in item:
                self._save_image_versions2(item, timestamp)

    def _save_stuff(self, edges: Any, parent_edge: Any = None) -> None:
        for edge in edges:
            if edge['node']['__typename'] == 'GraphVideo':
                try:
                    shortcode = edge['node']['shortcode']
                except KeyError as e:
                    if parent_edge:
                        shortcode = parent_edge['node']['shortcode']
                    else:
                        raise ValueError('Unknown shortcode') from e
                self._video_urls.append(
                    f'https://www.instagram.com/p/{shortcode}')
            elif edge['node']['__typename'] == 'GraphImage':
                self._save_media(edge)
            elif edge['node']['__typename'] == 'GraphSidecar':
                logger.debug('Recursion into child edges')
                self._save_stuff(
                    edge['node']['edge_sidecar_to_children']['edges'], edge)

    @sleep_and_retry
    @limits(calls=10, period=60)
    def _get_rate_limited(self,
                          url: str,
                          raise_for_status: bool = True,
                          return_json: bool = True,
                          params: Mapping[str, str] | None = None) -> Any:
        with self._session.get(url, params=params) as r:
            if raise_for_status:
                r.raise_for_status()
            return r.json() if return_json else r

    def _highlights_tray(self, user_id: int | str) -> Any:
        return self._get_rate_limited(
            f'https://i.instagram.com/api/v1/highlights/{user_id}/'
            'highlights_tray/')

    def __enter__(self) -> 'InstagramClient':
        return self

    def __exit__(self, _: Type[BaseException], __: BaseException,
                 ___: Traceback) -> None:
        self._cursor.close()
        self._connection.close()

    def process(self) -> None:
        with chdir(self._output_dir):
            r = self._get_rate_limited(
                f'https://www.instagram.com/{self._username}/',
                return_json=False)
            r = self._get_rate_limited(
                'https://i.instagram.com/api/v1/users/web_profile_info/',
                params={'username': self._username})
            with open('web_profile_info.json', 'w') as f:
                json.dump(r, f, indent=2, sort_keys=True)
            user_info = r['data']['user']
            if not self._is_saved(user_info['profile_pic_url_hd']):
                r = self._get_rate_limited(user_info['profile_pic_url_hd'],
                                           return_json=False)
                with open('profile_pic.jpg', 'wb') as f:
                    f.write(r.content)
                self._save_to_log(user_info['profile_pic_url_hd'])
            for item in self._highlights_tray(user_info['id'])['tray']:
                self._video_urls.append(
                    'https://www.instagram.com/stories/highlights/'
                    f'{item["id"].split(":")[-1]}/')
            self._save_stuff(
                user_info['edge_owner_to_timeline_media']['edges'])
            page_info = user_info['edge_owner_to_timeline_media']['page_info']
            while page_info['has_next_page']:
                params = dict(query_hash='69cba40317214236af40e7efa697781d',
                              variables=json.dumps(
                                  dict(id=user_info['id'],
                                       first=12,
                                       after=page_info['end_cursor'])))
                media = self._get_rate_limited(
                    'https://www.instagram.com/graphql/query/', params=params
                )['data']['user']['edge_owner_to_timeline_media']
                page_info = media['page_info']
                self._save_stuff(media['edges'])
            sys.argv = [sys.argv[0]]
            ydl_opts = yt_dlp.parse_options()[-1]
            if len(self._video_urls) > 0:
                with yt_dlp.YoutubeDL({
                        **ydl_opts,
                        **dict(download_archive=None,
                               http_headers=SHARED_HEADERS,
                               logger=YoutubeDLLogger(),
                               verbose=self._debug)
                }) as ydl:
                    failed_urls = []
                    for url in self._video_urls:
                        if self._is_saved(url):
                            continue
                        if ydl.extract_info(url, ie_key='Instagram'):
                            self._save_to_log(url)
                        elif ydl.extract_info(url, ie_key='InstagramStory'):
                            self._save_to_log(url)
                        else:
                            failed_urls.append(url)
                    if len(failed_urls) > 0:
                        logger.error(
                            'Some video URIs failed. Check failed.txt.')
                        with open('failed.txt', 'w') as f:
                            for url in failed_urls:
                                f.write(f'{url}\n')
        self._video_urls = []
