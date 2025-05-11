"""Instagram client."""
from __future__ import annotations

from contextlib import chdir
from os import utime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self, TypeVar, cast
from urllib.parse import urlparse
import json
import logging
import sqlite3

from yt_dlp_utils import get_configured_yt_dlp, setup_session

from .constants import LOG_SCHEMA, SHARED_HEADERS
from .typing import (
    BrowserName,
    CarouselMedia,
    Comments,
    Edge,
    HighlightsTray,
    MediaInfo,
    MediaInfoItem,
    MediaInfoItemImageVersions2Candidate,
    WebProfileInfo,
    XDTAPIV1FeedUserTimelineGraphQLConnectionContainer,
)
from .utils import get_extension, json_dumps_formatted, write_if_new

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from types import TracebackType

__all__ = ('InstagramClient',)

T = TypeVar('T')
log = logging.getLogger(__name__)


class UnexpectedMoreAvailableTrue(ValueError):
    def __init__(self) -> None:
        super().__init__('Unhandled more_available set to True.')


class UnknownShortcode(ValueError):
    def __init__(self) -> None:
        super().__init__('Unknown shortcode.')


class AuthenticationError(Exception):
    pass


class CSRFTokenNotFound(AuthenticationError):
    pass


class GraphQLStatusError(ValueError):
    def __init__(self, status: str) -> None:
        super().__init__('GraphQL status not "ok": %s.', status)


class GraphQLError(RuntimeError):
    pass


def _clean_url(url: str) -> str:
    parsed = urlparse(url)
    return f'https://{parsed.netloc}{parsed.path}'


class InstagramClient:
    """The client."""
    def __init__(self,
                 *,
                 username: str,
                 log_file: str | Path | None = None,
                 output_dir: str | Path | None = None,
                 disable_log: bool = False,
                 browser: BrowserName = 'chrome',
                 browser_profile: str = 'Default',
                 comments: bool = False) -> None:
        self._no_log = disable_log
        self.session = setup_session(browser,
                                     browser_profile,
                                     SHARED_HEADERS,
                                     domains={'instagram.com'},
                                     setup_retry=True,
                                     status_forcelist=(413, 429, 500, 502, 503, 504))
        self._output_dir = Path(output_dir or Path.cwd() / username)
        Path(self._output_dir).mkdir(parents=True, exist_ok=True)
        self._log_db = Path(log_file or self._output_dir / '.log.db')
        self._connection = sqlite3.connect(self._log_db)
        self._cursor = self._connection.cursor()
        self._setup_db()
        self._failed_urls: set[str] = set()
        self._username = username
        self._video_urls: list[str] = []
        self._get_comments = comments

    def _add_video_url(self, url: str) -> None:
        log.info('Added video URL: %s', url)
        self._video_urls.append(url)

    def _setup_db(self) -> None:
        existed = self._log_db.exists()
        if not existed or (existed and self._log_db.stat().st_size == 0):
            log.debug('Creating schema.')
            self._cursor.execute(LOG_SCHEMA)

    def _add_csrf_token_header(self) -> None:
        token = self.session.cookies.get('csrftoken')
        if not token:
            raise CSRFTokenNotFound
        self.session.headers.update({'x-csrftoken': token})

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

        best = max(sub_item['image_versions2']['candidates'], key=key)
        if self._is_saved(best['url']):
            return
        r = self.session.head(best['url'])
        r.raise_for_status()
        ext = get_extension(r.headers['content-type'])
        name = f'{sub_item["id"]}.{ext}'
        with Path(name).open('wb') as f:
            f.writelines(self.session.get(best['url'], stream=True).iter_content(chunk_size=512))
        utime(name, (timestamp, timestamp))
        self._save_to_log(r.url)

    def _save_comments(self, edge: Edge) -> None:
        if self._get_comments:
            comment_url = ('https://www.instagram.com/api/v1/media/'
                           f'{edge["node"]["id"]}/comments/')
            shared_params = {'can_support_threading': 'true'}
            top_comment_data = comment_data = self._get_json(
                comment_url,
                params={
                    **shared_params, 'permalink_enabled': 'false'
                },
                cast_to=Comments)
            while comment_data['can_view_more_preview_comments'] and comment_data['next_min_id']:
                comment_data = self._get_json(comment_url,
                                              params={
                                                  **shared_params,
                                                  'min_id':
                                                      comment_data['next_min_id'],
                                              },
                                              cast_to=Comments)
                top_comment_data['comments'].extend(comment_data['comments'])
            comments_json = f'{edge["node"]["id"]}-comments.json'
            with Path(comments_json).open('w+', encoding='utf-8') as f:
                json.dump(top_comment_data, f, sort_keys=True, indent=2)

    def _save_media(self, edge: Edge) -> None:
        log.info('Saving media at URL: https://www.instagram.com/p/%s', edge['node']['code'])
        media_info_url = ('https://i.instagram.com/api/v1/media/'
                          f'{edge["node"]["id"]}/info/')
        if self._is_saved(media_info_url):
            return
        media_info = self._get_json(media_info_url, cast_to=MediaInfo)
        if media_info['more_available'] or media_info['num_results'] != 1:
            raise UnexpectedMoreAvailableTrue
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
            if edge['node']['__typename'] == 'XDTMediaDict':
                try:
                    shortcode = edge['node']['code']
                except KeyError as e:
                    if parent_edge:
                        try:
                            shortcode = parent_edge['node']['code']
                        except KeyError as exc:
                            raise UnknownShortcode from exc
                    else:
                        raise UnknownShortcode from e
                if edge['node']['video_dash_manifest']:
                    self._add_video_url(f'https://www.instagram.com/p/{shortcode}')
                else:
                    self._save_media(edge)
            else:
                log.warning(  # type: ignore[unreachable]
                    'Unknown type: `%s`. Item %s will not be processed.',
                    edge['node']['__typename'], edge['node']['id'])
                shortcode = edge['node']['code']
                self._failed_urls(f'https://www.instagram.com/p/{shortcode}')

    def _get_json(self,
                  url: str,
                  *,
                  cast_to: type[T],
                  params: Mapping[str, str] | None = None) -> T:
        with self.session.get(url, params=params) as r:
            r.raise_for_status()
            return cast('T', r.json())

    def _graphql_query(self,
                       variables: Mapping[str, Any],
                       *,
                       cast_to: type[T],
                       doc_id: str = '9806959572732215') -> T:
        with self.session.post('https://www.instagram.com/graphql/query',
                               headers={'content-type': 'application/x-www-form-urlencoded'},
                               data={
                                   'doc_id': doc_id,
                                   'variables': json.dumps(variables, separators=(',', ':'))
                               }) as r:
            r.raise_for_status()
            data = r.json()
            assert isinstance(data, dict)
            if (status := data.get('status')) != 'ok':
                raise GraphQLStatusError(cast('str', status))
            if data.get('errors'):
                log.warning('Response has errors.')
                log.debug('Response: %s', json.dumps(data, indent=2))
            if not data.get('data'):
                msg = 'No data in response.'
                raise GraphQLError(msg)
            return cast('T', data['data'])

    def _get_text(self, url: str, *, params: Mapping[str, str] | None = None) -> str:
        with self.session.get(url, params=params) as r:
            r.raise_for_status()
            return r.text

    def _highlights_tray(self, user_id: int | str) -> HighlightsTray:
        return self._get_json(
            f'https://i.instagram.com/api/v1/highlights/{user_id}/highlights_tray/',
            cast_to=HighlightsTray)

    def __enter__(self) -> Self:
        """Recommended way to initialise the client."""
        return self

    def __exit__(self, _: type[BaseException] | None, __: BaseException | None,
                 ___: TracebackType | None) -> None:
        """Clean up."""
        self._cursor.close()
        self._connection.close()

    def process(self) -> None:
        """Process posts."""
        with chdir(self._output_dir):
            self._get_text(f'https://www.instagram.com/{self._username}/')
            self._add_csrf_token_header()
            r = self._get_json('https://i.instagram.com/api/v1/users/web_profile_info/',
                               params={'username': self._username},
                               cast_to=WebProfileInfo)
            with Path('web_profile_info.json').open('w', encoding='utf-8') as f:
                json.dump(r, f, indent=2, sort_keys=True)
            user_info = r['data']['user']
            if not self._is_saved(user_info['profile_pic_url_hd']):
                with Path('profile_pic.jpg').open('wb') as f:
                    f.writelines(
                        self.session.get(user_info['profile_pic_url_hd'],
                                         stream=True).iter_content(chunk_size=512))
                self._save_to_log(user_info['profile_pic_url_hd'])
            for item in self._highlights_tray(user_info['id'])['tray']:
                self._add_video_url('https://www.instagram.com/stories/highlights/'
                                    f'{item["id"].split(":")[-1]}/')
            self._save_stuff(user_info['edge_owner_to_timeline_media']['edges'])
            d = self._graphql_query(
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
            self._save_stuff(d['xdt_api__v1__feed__user_timeline_graphql_connection']['edges'])
            page_info = d['xdt_api__v1__feed__user_timeline_graphql_connection']['page_info']
            while page_info['has_next_page']:
                d = self._graphql_query(
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
                page_info = d['xdt_api__v1__feed__user_timeline_graphql_connection']['page_info']
                self._save_stuff(d['xdt_api__v1__feed__user_timeline_graphql_connection']['edges'])
            if len(self._video_urls) > 0:
                with get_configured_yt_dlp() as ydl:
                    while self._video_urls and (url := self._video_urls.pop()):
                        if self._is_saved(url):
                            log.info('`%s` is already saved.', url)
                            continue
                        if ydl.extract_info(url):
                            log.info('Extracting `%s`.', url)
                            self._save_to_log(url)
                        else:
                            self._failed_urls.add(url)
                    if len(self._failed_urls) > 0:
                        log.warning('Some video URIs failed. Check failed.txt.')
                        with Path('failed.txt').open('w', encoding='utf-8') as f:
                            for url in self._failed_urls:
                                f.write(f'{url}\n')
