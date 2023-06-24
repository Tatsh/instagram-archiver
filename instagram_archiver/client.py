from inspect import Traceback
from os import makedirs, utime
from pathlib import Path
from pprint import pprint as pp
from typing import Collection, Literal, Mapping, Type, TypeVar, overload
from urllib.parse import urlparse
import json
import re
import sqlite3

from loguru import logger
from ratelimit import limits, sleep_and_retry
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from yt_dlp.cookies import extract_cookies_from_browser
import requests
import yt_dlp

from .constants import LOG_SCHEMA, RETRY_ABORT_NUM, SHARED_HEADERS, SHARED_YT_DLP_OPTIONS
from .ig_typing import (CarouselMedia, Comments, Edge, HighlightsTray, MediaInfo, MediaInfoItem,
                        MediaInfoItemImageVersions2Candidate, WebProfileInfo)
from .utils import chdir, get_extension, json_dumps_formatted, write_if_new

__all__ = ('InstagramClient',)

Browser = Literal['brave', 'chrome', 'chromium', 'edge', 'opera', 'vivaldi', 'firefox', 'safari']
T = TypeVar('T')


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
                 browser: Browser = 'chrome',
                 browser_profile: str = 'Default',
                 debug: bool = False,
                 comments: bool = False) -> None:
        self._no_log = disable_log
        self._session = requests.Session()
        self._browser = browser
        self._browser_profile = browser_profile
        self._setup_session(browser, browser_profile)
        self._output_dir = Path(output_dir or Path('.').resolve() / username)
        makedirs(self._output_dir, exist_ok=True)
        self._log_db = Path(log_file or self._output_dir / '.log.db')
        self._connection = sqlite3.connect(self._log_db)
        self._cursor = self._connection.cursor()
        self._setup_db()
        self._username = username
        self._video_urls: list[str] = []
        self._debug = debug
        self._get_comments = comments

    def _add_video_url(self, url: str) -> None:
        logger.debug(f'Added video URL: {url}')
        self._video_urls.append(url)

    def _setup_db(self) -> None:
        existed = self._log_db.exists()
        if not existed or (existed and self._log_db.stat().st_size == 0):
            logger.debug('Creating schema')
            self._cursor.execute(LOG_SCHEMA)

    def _setup_session(self,
                       browser: Literal['brave', 'chrome', 'chromium', 'edge', 'opera', 'vivaldi',
                                        'firefox', 'safari'] = 'chrome',
                       browser_profile: str = 'Default') -> None:
        self._session.mount(
            'https://',
            HTTPAdapter(max_retries=Retry(
                backoff_factor=1.5,  # wait times are normally 1 and 3 seconds
                redirect=0,
                status=0,
                respect_retry_after_header=False,
                status_forcelist=frozenset((413, 429, 500, 502, 503, 504)),
                total=RETRY_ABORT_NUM)))
        self._session.headers.update({
            **SHARED_HEADERS,
            **dict(cookie='; '.join(f'{cookie.name}={cookie.value}' \
                for cookie in extract_cookies_from_browser(browser, browser_profile)
                    if 'instagram.com' in cookie.domain))
        })
        r = self._get_rate_limited('https://www.instagram.com', return_json=False)
        m = re.search(r'"config":{"csrf_token":"([^"]+)"', r.text)
        assert m is not None
        self._session.headers.update({'x-csrftoken': m.group(1)})

    def _save_to_log(self, url: str) -> None:
        if self._no_log:
            return
        self._cursor.execute('INSERT INTO log (url) VALUES (?)', (_clean_url(url),))
        self._connection.commit()

    def _is_saved(self, url: str) -> bool:
        if self._no_log:
            return False
        self._cursor.execute('SELECT COUNT(url) FROM log WHERE url = ?', (_clean_url(url),))
        count: int
        count, = self._cursor.fetchone()
        return count == 1

    def _save_image_versions2(self, sub_item: CarouselMedia | MediaInfoItem,
                              timestamp: int) -> None:
        def key(x: MediaInfoItemImageVersions2Candidate) -> int:
            return x['width'] * x['height']

        best = sorted(sub_item['image_versions2']['candidates'], key=key, reverse=True)[0]
        if self._is_saved(best['url']):
            return
        r = self._session.head(best['url'])
        r.raise_for_status()
        ext = get_extension(r.headers['content-type'])
        name = f'{sub_item["id"]}.{ext}'
        with open(name, 'wb') as f:
            for content in (self._session.get(best['url'],
                                              stream=True).iter_content(chunk_size=512)):
                f.write(content)
        utime(name, (timestamp, timestamp))
        self._save_to_log(r.url)

    def _save_comments(self, edge: Edge) -> None:
        if self._get_comments:
            comment_url = ('https://www.instagram.com/api/v1/media/'
                           f'{edge["node"]["id"]}/comments/')
            shared_params = dict(can_support_threading='true')
            top_comment_data = comment_data = self._get_rate_limited(
                comment_url,
                params={
                    **shared_params, 'permalink_enabled': 'false'
                },
                cast_to=Comments)
            while comment_data['can_view_more_preview_comments'] and comment_data['next_min_id']:
                comment_data = self._get_rate_limited(comment_url,
                                                      params={
                                                          **shared_params,
                                                          'min_id':
                                                              comment_data['next_min_id'],
                                                      },
                                                      cast_to=Comments)
                top_comment_data['comments'].extend(comment_data['comments'])
            comments_json = f'{edge["node"]["id"]}-comments.json'
            with open(comments_json, 'w+') as f:
                json.dump(top_comment_data, f, sort_keys=True, indent=2)

    def _save_media(self, edge: Edge) -> None:
        media_info_url = ('https://i.instagram.com/api/v1/media/'
                          f'{edge["node"]["id"]}/info/')
        if self._is_saved(media_info_url):
            return
        media_info = self._get_rate_limited(media_info_url, cast_to=MediaInfo)
        if media_info['more_available'] or media_info['num_results'] != 1:
            pp(media_info)
            raise ValueError('Unhandled more_available set to True')
        timestamp = media_info['items'][0]['taken_at']
        id_json_file = f'{edge["node"]["id"]}.json'
        media_info_json_file = f'{edge["node"]["id"]}-media-info-0000.json'
        write_if_new(id_json_file, str(json_dumps_formatted(edge['node'])))
        write_if_new(media_info_json_file, str(json_dumps_formatted(media_info)))
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

    def _save_stuff(self, edges: Collection[Edge], parent_edge: Edge | None = None) -> None:
        for edge in edges:
            if edge['node']['__typename'] == 'GraphVideo':
                try:
                    shortcode = edge['node']['shortcode']
                except KeyError as e:
                    if parent_edge:
                        try:
                            shortcode = parent_edge['node']['shortcode']
                        except KeyError as exc:
                            raise ValueError('Unknown shortcode') from exc
                    else:
                        raise ValueError('Unknown shortcode') from e
                self._add_video_url(f'https://www.instagram.com/p/{shortcode}')
            elif edge['node']['__typename'] == 'GraphImage':
                self._save_media(edge)
            elif edge['node']['__typename'] == 'GraphSidecar':
                logger.debug('Recursion into child edges')
                if (not edge['node']['comments_disabled']
                        and edge['node']['edge_media_to_comment']['count']):
                    self._save_comments(edge)
                self._save_stuff(edge['node']['edge_sidecar_to_children']['edges'], edge)
            else:
                raise ValueError(f'Unknown type "{edge["node"]["__typename"]}"')

    @overload
    def _get_rate_limited(self, url: str, *, cast_to: Type[T]) -> T:
        pass

    @overload
    def _get_rate_limited(self,
                          url: str,
                          *,
                          return_json: Literal[False] = False) -> requests.Response:
        pass

    @overload
    def _get_rate_limited(self,
                          url: str,
                          *,
                          params: Mapping[str, str] | None = None,
                          cast_to: Type[T]) -> T:
        pass

    @sleep_and_retry
    @limits(calls=10, period=60)
    def _get_rate_limited(
            self,
            url: str,
            *,
            return_json: bool = True,
            params: Mapping[str, str] | None = None,
            cast_to: Type[T] | None = None) -> T | requests.Response:  # pylint: disable=unused-argument
        with self._session.get(url, params=params) as r:
            r.raise_for_status()
            return r.json() if return_json else r

    def _highlights_tray(self, user_id: int | str) -> HighlightsTray:
        return self._get_rate_limited(
            f'https://i.instagram.com/api/v1/highlights/{user_id}/'
            'highlights_tray/',
            cast_to=HighlightsTray)

    def __enter__(self) -> 'InstagramClient':
        return self

    def __exit__(self, _: Type[BaseException], __: BaseException, ___: Traceback) -> None:
        self._cursor.close()
        self._connection.close()

    def process(self) -> None:
        with chdir(self._output_dir):
            self._get_rate_limited(f'https://www.instagram.com/{self._username}/',
                                   return_json=False)
            r = self._get_rate_limited('https://i.instagram.com/api/v1/users/web_profile_info/',
                                       params={'username': self._username},
                                       cast_to=WebProfileInfo)
            with open('web_profile_info.json', 'w') as f:
                json.dump(r, f, indent=2, sort_keys=True)
            user_info = r['data']['user']
            if not self._is_saved(user_info['profile_pic_url_hd']):
                with open('profile_pic.jpg', 'wb') as f:
                    for chunk in self._session.get(user_info['profile_pic_url_hd'],
                                                   stream=True).iter_content(chunk_size=512):
                        f.write(chunk)
                self._save_to_log(user_info['profile_pic_url_hd'])
            for item in self._highlights_tray(user_info['id'])['tray']:
                self._add_video_url('https://www.instagram.com/stories/highlights/'
                                    f'{item["id"].split(":")[-1]}/')
            self._save_stuff(user_info['edge_owner_to_timeline_media']['edges'])
            page_info = user_info['edge_owner_to_timeline_media']['page_info']
            while page_info['has_next_page']:
                params = dict(query_hash='69cba40317214236af40e7efa697781d',
                              variables=json.dumps(
                                  dict(id=user_info['id'], first=12,
                                       after=page_info['end_cursor'])))
                media = self._get_rate_limited(
                    'https://www.instagram.com/graphql/query/',
                    params=params,
                    cast_to=WebProfileInfo)['data']['user']['edge_owner_to_timeline_media']
                page_info = media['page_info']
                self._save_stuff(media['edges'])
            if len(self._video_urls) > 0:
                with yt_dlp.YoutubeDL({
                        **SHARED_YT_DLP_OPTIONS,  # type: ignore[misc]
                        **{
                            'cookiesfrombrowser': [
                                self._browser, self._browser_profile, None, None
                            ],
                            'getcomments': self._get_comments,
                            'verbose': self._debug
                        }
                }) as ydl:
                    failed_urls: list[str] = []
                    while (self._video_urls and (url := self._video_urls.pop())):
                        if self._is_saved(url):
                            logger.debug(f'{url} is already saved')
                            continue
                        if ydl.extract_info(url):
                            logger.debug(f'Extracting {url}')
                            self._save_to_log(url)
                        else:
                            failed_urls.append(url)
                    if len(failed_urls) > 0:
                        logger.error('Some video URIs failed. Check failed.txt.')
                        with open('failed.txt', 'w') as f:
                            for url in failed_urls:
                                f.write(f'{url}\n')
