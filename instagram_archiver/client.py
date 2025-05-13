"""Generic client."""
from __future__ import annotations

from http import HTTPStatus
from os import utime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self, TypeVar, cast
import json
import logging

from requests import HTTPError
from yt_dlp_utils import setup_session
import requests

from .constants import API_HEADERS, SHARED_HEADERS
from .typing import (
    CarouselMedia,
    Comments,
    Edge,
    HighlightsTray,
    MediaInfo,
    MediaInfoItem,
    MediaInfoItemImageVersions2Candidate,
)
from .utils import get_extension, json_dumps_formatted, write_if_new

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from types import TracebackType

    from .typing import BrowserName

__all__ = ('CSRFTokenNotFound', 'InstagramClient', 'UnexpectedRedirect')

T = TypeVar('T')
log = logging.getLogger(__name__)


class CSRFTokenNotFound(RuntimeError):
    """CSRF token not found in cookies."""


class UnexpectedRedirect(RuntimeError):
    """Unexpected redirect in a request."""


class InstagramClient:
    """Generic client for Instagram."""
    def __init__(self, browser: BrowserName = 'chrome', browser_profile: str = 'Default') -> None:
        """
        Initialise the client.

        Parameters
        ----------
        browser : str
            The browser to use.

        browser_profile : str
            The browser profile to use.
        """
        self.session = setup_session(browser,
                                     browser_profile,
                                     SHARED_HEADERS,
                                     domains={'instagram.com'},
                                     status_forcelist=(413, 429, 500, 502, 503, 504))
        self.failed_urls: set[str] = set()
        """Set of failed URLs."""
        self.video_urls: list[str] = []
        """List of video URLs to download."""

    def add_video_url(self, url: str) -> None:
        """Add a video URL to the list of video URLs."""
        log.info('Added video URL: %s', url)
        self.video_urls.append(url)

    def add_csrf_token_header(self) -> None:
        """
        Add CSRF token header to the session.

        Raises
        ------
        CSRFTokenNotFound
            If the CSRF token is not found in the cookies.
        """
        token = self.session.cookies.get('csrftoken')
        if not token:
            raise CSRFTokenNotFound
        self.session.headers.update({'x-csrftoken': token})

    def graphql_query(self,
                      variables: Mapping[str, Any],
                      *,
                      cast_to: type[T],
                      doc_id: str = '9806959572732215') -> T | None:
        """Make a GraphQL query."""
        with self.session.post('https://www.instagram.com/graphql/query',
                               headers={
                                   'content-type': 'application/x-www-form-urlencoded',
                               } | API_HEADERS,
                               data={
                                   'doc_id': doc_id,
                                   'variables': json.dumps(variables, separators=(',', ':'))
                               }) as r:
            if r.status_code != HTTPStatus.OK:
                return None
            data = r.json()
            assert isinstance(data, dict)
            if (status := data.get('status')) != 'ok':
                log.error('GraphQL status not "ok": %s', status)
                return None
            if data.get('errors'):
                log.warning('Response has errors.')
                log.debug('Response: %s', json.dumps(data, indent=2))
            if not data.get('data'):
                log.error('No data in response.')
            return cast('T', data['data'])

    def get_text(self, url: str, *, params: Mapping[str, str] | None = None) -> str:
        """Get text from a URL."""
        with self.session.get(url, params=params, headers=API_HEADERS) as r:
            r.raise_for_status()
            return r.text

    def highlights_tray(self, user_id: int | str) -> HighlightsTray:
        """Get the highlights tray data for a user."""
        return self.get_json(
            f'https://i.instagram.com/api/v1/highlights/{user_id}/highlights_tray/',
            cast_to=HighlightsTray)

    def __enter__(self) -> Self:  # pragma: no cover
        """Recommended way to initialise the client."""
        return self

    def __exit__(self, _: type[BaseException] | None, __: BaseException | None,
                 ___: TracebackType | None) -> None:
        """Clean up."""

    def is_saved(self, url: str) -> bool:  # pragma: no cover
        """Check if a URL is already saved."""
        return False

    def save_to_log(self, url: str) -> None:
        """Save a URL to the log."""

    def save_image_versions2(self, sub_item: CarouselMedia | MediaInfoItem, timestamp: int) -> None:
        """Save images in the image_versions2 dictionary."""
        def key(x: MediaInfoItemImageVersions2Candidate) -> int:
            return x['width'] * x['height']

        best = max(sub_item['image_versions2']['candidates'], key=key)
        if self.is_saved(best['url']):
            return
        r = self.session.head(best['url'])
        if r.status_code != HTTPStatus.OK:
            log.warning('HEAD request failed with status code %s.', r.status_code)
            return
        ext = get_extension(r.headers['content-type'])
        name = f'{sub_item["id"]}.{ext}'
        with Path(name).open('wb') as f:
            f.writelines(self.session.get(best['url'], stream=True).iter_content(chunk_size=512))
        utime(name, (timestamp, timestamp))
        self.save_to_log(r.url)

    def save_comments(self, edge: Edge) -> None:
        """Save comments for an edge node."""
        comment_url = ('https://www.instagram.com/api/v1/media/'
                       f'{edge["node"]["id"]}/comments/')
        shared_params = {'can_support_threading': 'true'}
        try:
            comment_data = self.get_json(comment_url,
                                         params={
                                             **shared_params, 'permalink_enabled': 'false'
                                         },
                                         cast_to=Comments)
        except HTTPError:
            log.exception('Failed to get comments.')
            return
        top_comment_data: Any = comment_data
        while comment_data['can_view_more_preview_comments'] and comment_data['next_min_id']:
            try:
                comment_data = self.get_json(comment_url,
                                             params={
                                                 **shared_params,
                                                 'min_id':
                                                     comment_data['next_min_id'],
                                             },
                                             cast_to=Comments)
            except HTTPError:
                log.exception('Failed to get comments.')
                break
            top_comment_data['comments'] = (list(top_comment_data['comments']) +
                                            list(comment_data['comments']))
        comments_json = f'{edge["node"]["id"]}-comments.json'
        with Path(comments_json).open('w+', encoding='utf-8') as f:
            json.dump(top_comment_data, f, sort_keys=True, indent=2)

    def save_media(self, edge: Edge) -> None:
        """
        Save media for an edge node.

        Raises
        ------
        UnexpectedRedirect
            If a redirect occurs unexpectedly.
        """
        media_info_url = f'https://www.instagram.com/api/v1/media/{edge["node"]["pk"]}/info/'
        log.info('Saving media at URL: %s', media_info_url)
        if self.is_saved(media_info_url):
            return
        r = self.session.get(media_info_url, headers=API_HEADERS, allow_redirects=False)
        if r.status_code != HTTPStatus.OK:
            if r.status_code in {HTTPStatus.MOVED_PERMANENTLY, HTTPStatus.FOUND}:
                raise UnexpectedRedirect
            log.warning('GET request failed with status code %s.', r.status_code)
            log.debug('Content: %s', r.text)
            return
        if 'image_versions2' not in r.text or 'taken_at' not in r.text:
            log.warning('Invalid response. image_versions2 dict not found.')
            return
        media_info: MediaInfo = r.json()
        timestamp = media_info['items'][0]['taken_at']
        id_json_file = f'{edge["node"]["id"]}.json'
        media_info_json_file = f'{edge["node"]["id"]}-media-info-0000.json'
        write_if_new(id_json_file, str(json_dumps_formatted(edge['node'])))
        write_if_new(media_info_json_file, str(json_dumps_formatted(media_info)))
        for file in (id_json_file, media_info_json_file):
            utime(file, (timestamp, timestamp))
        self.save_to_log(media_info_url)
        for item in media_info['items']:
            timestamp = item['taken_at']
            if (carousel_media := item.get('carousel_media')):
                for sub_item in carousel_media:
                    self.save_image_versions2(sub_item, timestamp)
            elif 'image_versions2' in item:
                self.save_image_versions2(item, timestamp)

    def save_edges(self, edges: Iterable[Edge], parent_edge: Edge | None = None) -> None:
        """Save edge node media."""
        for edge in edges:
            if edge['node']['__typename'] == 'XDTMediaDict':
                try:
                    shortcode = edge['node']['code']
                except KeyError:
                    if parent_edge:
                        try:
                            shortcode = parent_edge['node']['code']
                        except KeyError:
                            log.exception('Unknown shortcode.')
                            return
                    else:
                        log.exception('Unknown shortcode.')
                if edge['node'].get('video_dash_manifest'):
                    self.add_video_url(f'https://www.instagram.com/p/{shortcode}/')
                else:
                    try:
                        self.save_comments(edge)
                        self.save_media(edge)
                    except requests.exceptions.RetryError:
                        log.exception('Retries exhausted.')
                        return
            else:
                log.warning(  # type: ignore[unreachable]
                    'Unknown type: `%s`. Item %s will not be processed.',
                    edge['node']['__typename'], edge['node']['id'])
                shortcode = edge['node']['code']
                self.failed_urls.add(f'https://www.instagram.com/p/{shortcode}/')

    def get_json(self, url: str, *, cast_to: type[T], params: Mapping[str, str] | None = None) -> T:
        """Get JSON data from a URL."""
        with self.session.get(url, params=params, headers=API_HEADERS) as r:
            r.raise_for_status()
            return cast('T', r.json())
