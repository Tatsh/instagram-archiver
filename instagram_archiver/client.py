"""Generic client."""

from __future__ import annotations

from http import HTTPStatus
from os import utime
from typing import TYPE_CHECKING, Any, TypeVar, cast
import json
import logging

from niquests.exceptions import HTTPError, RetryError
from typing_extensions import Self
from yt_dlp_utils.aio import setup_session

from .constants import API_HEADERS, SHARED_HEADERS
from .typing import (
    POSTS_HANDLED,
    CarouselMedia,
    Comments,
    Edge,
    HighlightsTray,
    MediaInfo,
    MediaInfoItem,
    MediaInfoItemImageVersions2Candidate,
    StoryReelItem,
    XDTStoriesV3ReelPageGalleryConnection,
    XDTStoriesV3ReelPageGalleryQueryResponse,
)
from .utils import dump_json, get_extension, json_dumps_formatted, write_bytes, write_if_new

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from types import TracebackType
    import asyncio

    from niquests import AsyncSession

    from .typing import BrowserName, Stats, YTDLPState

__all__ = ('CSRFTokenNotFound', 'InstagramClient', 'UnexpectedRedirect')

T = TypeVar('T')
log = logging.getLogger(__name__)

_REEL_PAGE_GALLERY_DOC_ID = '26659189347081290'
_REEL_PAGE_GALLERY_PAGINATION_DOC_ID = '27002830962682635'


def _extract_reel_connection(
        data: Mapping[str, Any]) -> XDTStoriesV3ReelPageGalleryConnection | None:
    """
    Find the reel-gallery connection in a GraphQL ``data`` payload.

    The wrapper key used by Instagram's PolarisStoriesV3 query is volatile, so this helper first
    looks for the documented ``xdt_api__v1__feed__reels_media`` key and otherwise falls back to
    the first value in ``data`` that exposes both ``edges`` and ``page_info`` fields.

    Parameters
    ----------
    data : Mapping[str, Any]
        The decoded GraphQL ``data`` mapping.

    Returns
    -------
    XDTStoriesV3ReelPageGalleryConnection | None
        The matching connection, or ``None`` if nothing in ``data`` looks like one.
    """
    candidate = data.get('xdt_api__v1__feed__reels_media')
    if isinstance(candidate, dict) and 'edges' in candidate and 'page_info' in candidate:
        return cast('XDTStoriesV3ReelPageGalleryConnection', candidate)
    for value in data.values():
        if isinstance(value, dict) and 'edges' in value and 'page_info' in value:
            return cast('XDTStoriesV3ReelPageGalleryConnection', value)
    return None


class CSRFTokenNotFound(RuntimeError):
    """CSRF token not found in cookies."""


class UnexpectedRedirect(RuntimeError):
    """Unexpected redirect in a request."""


class InstagramClient:
    """Generic asynchronous client for Instagram."""
    def __init__(self, browser: BrowserName = 'chrome', browser_profile: str = 'Default') -> None:
        """
        Initialise the client.

        Parameters
        ----------
        browser : BrowserName
            The browser to read cookies from.
        browser_profile : str
            The browser profile to use.
        """
        self._browser = browser
        self._browser_profile = browser_profile
        self.session: AsyncSession
        """The niquests :py:class:`~niquests.AsyncSession` used for all HTTP calls."""
        self.failed_urls: set[str] = set()
        """Set of failed URLs."""
        self.should_save_comments: bool = False
        """Whether to fetch comments. Subclasses or mixins flip this on."""
        self.video_urls: list[str] = []
        """List of video URLs to download."""

    async def _setup_session(self) -> None:
        """Create the underlying :py:class:`~niquests.AsyncSession`."""
        self.session = await setup_session(self._browser,
                                           self._browser_profile,
                                           domains={'instagram.com'},
                                           setup_retry=True)
        self.session.headers.update(SHARED_HEADERS)

    def add_video_url(self, url: str) -> None:
        """
        Add a video URL to the list of video URLs.

        Parameters
        ----------
        url : str
            URL to enqueue for yt-dlp.
        """
        log.debug('Added video URL: %s', url)
        self.video_urls.append(url)

    def add_csrf_token_header(self) -> None:
        """
        Add CSRF token header to the session.

        Raises
        ------
        CSRFTokenNotFound
            If the CSRF token is not found in the cookies.
        """
        token = cast('Any', self.session.cookies).get('csrftoken')
        if not token:
            raise CSRFTokenNotFound
        self.session.headers.update({'x-csrftoken': token})

    async def graphql_query(
            self,
            variables: Mapping[str, Any],
            *,
            cast_to: type[T],  # noqa: ARG002
            doc_id: str = '9806959572732215') -> T | None:
        """
        Make a GraphQL query.

        Parameters
        ----------
        variables : Mapping[str, Any]
            Variables passed to the query.
        cast_to : type[T]
            Expected type of the ``data`` field in a successful response.
        doc_id : str
            GraphQL document identifier.

        Returns
        -------
        T | None
            The ``data`` payload, or ``None`` if the request failed or the response was invalid.
        """
        r = await self.session.post('https://www.instagram.com/graphql/query',
                                    headers={
                                        'content-type': 'application/x-www-form-urlencoded',
                                        **API_HEADERS
                                    },
                                    data={
                                        'doc_id': doc_id,
                                        'variables': json.dumps(variables, separators=(',', ':'))
                                    })
        if r.status_code != HTTPStatus.OK:
            return None
        data = r.json()
        if not isinstance(data, dict):
            log.error('GraphQL response was not a JSON object.')
            return None
        if (status := data.get('status')) != 'ok':
            log.error('GraphQL status not "ok": %s', status)
            return None
        if data.get('errors'):
            log.warning('Response has errors.')
            log.debug('Response: %s', json.dumps(data, indent=2))
        if not data.get('data'):
            log.error('No data in response.')
        return cast('T', data['data'])

    async def get_text(self, url: str, *, params: Mapping[str, str] | None = None) -> str:
        """
        Get text from a URL.

        Parameters
        ----------
        url : str
            URL to fetch.
        params : Mapping[str, str] | None
            Optional query string parameters.

        Returns
        -------
        str
            Response body as text.
        """
        r = await self.session.get(url, params=params, headers=API_HEADERS)
        r.raise_for_status()
        return r.text or ''

    async def get_json(
            self,
            url: str,
            *,
            cast_to: type[T],  # noqa: ARG002
            params: Mapping[str, str] | None = None) -> T:
        """
        Get JSON data from a URL.

        Parameters
        ----------
        url : str
            URL to fetch.
        cast_to : type[T]
            Expected type of the decoded JSON body.
        params : Mapping[str, str] | None
            Optional query string parameters.

        Returns
        -------
        T
            Response body decoded from JSON.
        """
        r = await self.session.get(url, params=params, headers=API_HEADERS)
        r.raise_for_status()
        return cast('T', r.json())

    async def highlights_tray(self, user_id: int | str) -> HighlightsTray:
        """
        Get the highlights tray data for a user.

        Parameters
        ----------
        user_id : int | str
            Instagram user identifier.

        Returns
        -------
        HighlightsTray
            Highlights tray payload from the API.
        """
        return await self.get_json(
            f'https://i.instagram.com/api/v1/highlights/{user_id}/highlights_tray/',
            cast_to=HighlightsTray)

    async def __aenter__(self) -> Self:
        """
        Enter the asynchronous context manager.

        Returns
        -------
        Self
            This client instance.
        """
        await self._setup_session()
        return self

    async def __aexit__(self, _: type[BaseException] | None, __: BaseException | None,
                        ___: TracebackType | None) -> None:
        """Close the underlying session."""
        await self.session.close()

    def is_saved(self, url: str) -> bool:  # pragma: no cover  # noqa: ARG002, PLR6301
        """
        Check if a URL is already saved.

        Parameters
        ----------
        url : str
            URL to check.

        Returns
        -------
        bool
            ``False`` in the base implementation.
        """
        return False

    def save_to_log(self, url: str) -> None:
        """
        Save a URL to the log.

        Parameters
        ----------
        url : str
            URL to record.
        """

    async def save_image_versions2(self, sub_item: CarouselMedia | MediaInfoItem | StoryReelItem,
                                   timestamp: int) -> None:
        """
        Save images in the ``image_versions2`` dictionary.

        Parameters
        ----------
        sub_item : CarouselMedia | MediaInfoItem | StoryReelItem
            Source item containing ``image_versions2`` candidates.
        timestamp : int
            Timestamp to apply to the saved file.
        """
        def key(x: MediaInfoItemImageVersions2Candidate) -> int:
            return x['width'] * x['height']

        best = max(sub_item['image_versions2']['candidates'], key=key)
        if self.is_saved(best['url']):
            return
        r = await self.session.head(best['url'])
        if r.status_code != HTTPStatus.OK:
            log.warning('HEAD request failed with status code %s.', r.status_code)
            return
        content_type = r.headers['content-type']
        if isinstance(content_type, bytes):
            content_type = content_type.decode()
        ext = get_extension(content_type)
        name = f'{sub_item["id"]}.{ext}'
        body = await self.session.get(best['url'])
        if body.content is not None:
            write_bytes(name, body.content)
        utime(name, (timestamp, timestamp))
        if r.url is not None:
            self.save_to_log(r.url)

    async def reel_page_gallery(
            self,
            reel_ids: Sequence[str],
            *,
            after: str | None = None,
            first: int = 5,
            initial_reel_id: str | None = None,
            is_highlight: bool = True) -> XDTStoriesV3ReelPageGalleryConnection | None:
        """
        Fetch a page of the PolarisStoriesV3 reel gallery.

        Used to retrieve full story metadata (image and video items) for the supplied reels. The
        first page uses the ``ReelPageGalleryQuery`` document; subsequent pages (when ``after`` is
        supplied) use the pagination document.

        Parameters
        ----------
        reel_ids : Sequence[str]
            Numeric reel identifiers (user IDs for current stories or numeric highlight IDs).
        after : str | None
            Cursor returned by a previous page, or ``None`` for the first page.
        first : int
            Maximum number of reels to return per page.
        initial_reel_id : str | None
            Reel that the user "opened first". Defaults to the first entry of ``reel_ids``.
        is_highlight : bool
            ``True`` when ``reel_ids`` refer to highlights, ``False`` for current stories.

        Returns
        -------
        XDTStoriesV3ReelPageGalleryConnection | None
            The connection payload, or ``None`` when the request fails or the response shape is
            unexpected.
        """
        ordered_ids = list(reel_ids)
        if not ordered_ids:
            return None
        resolved_initial = initial_reel_id or ordered_ids[0]
        if after is None:
            variables: dict[str, Any] = {
                'first': first,
                'initial_reel_id': resolved_initial,
                'last': None,
                'reel_ids': ordered_ids,
            }
            doc_id = _REEL_PAGE_GALLERY_DOC_ID
        else:
            variables = {
                'after': after,
                'before': None,
                'first': first,
                'initial_reel_id': resolved_initial,
                'is_highlight': is_highlight,
                'last': None,
                'reel_ids': ordered_ids,
            }
            doc_id = _REEL_PAGE_GALLERY_PAGINATION_DOC_ID
        data = await self.graphql_query(variables,
                                        cast_to=XDTStoriesV3ReelPageGalleryQueryResponse,
                                        doc_id=doc_id)
        if not data:
            return None
        connection = _extract_reel_connection(data)
        if connection is None:
            log.warning('Reel gallery response did not contain a recognisable connection.')
        return connection

    async def save_reel_item(self,
                             item: StoryReelItem,
                             video_queue: asyncio.Queue[str | None] | None = None,
                             *,
                             username: str | None = None,
                             yt_dlp_state: YTDLPState | None = None) -> None:
        """
        Save a single story item.

        Image-only items are written via :py:meth:`save_image_versions2`; items with a video are
        routed to ``video_queue`` for the yt-dlp worker (or appended to
        :py:attr:`video_urls` when no queue is supplied, mirroring the synchronous helper used
        elsewhere).

        Parameters
        ----------
        item : StoryReelItem
            Story item payload from a reel page gallery response.
        video_queue : asyncio.Queue[str | None] | None
            Optional queue receiving permalinks for the yt-dlp worker. When ``None``, video URLs
            are appended to :py:attr:`video_urls` instead.
        username : str | None
            Username of the reel owner. Used to build the ``stories/{username}/{pk}/`` permalink
            for video items. Falls back to the literal ``"_"`` when not available, which yt-dlp
            still accepts because it identifies the story by ``pk``.
        yt_dlp_state : YTDLPState | None
            Optional yt-dlp progress state whose ``total_urls`` counter is incremented when a
            video URL is enqueued.
        """
        has_video = bool(item.get('video_versions')) or bool(item.get('video_dash_manifest'))
        if has_video:
            permalink = (f'https://www.instagram.com/stories/{username or "_"}/'
                         f'{item["pk"]}/')
            if video_queue is None:
                self.add_video_url(permalink)
            else:
                await video_queue.put(permalink)
                if yt_dlp_state is not None:
                    yt_dlp_state.total_urls += 1
            return
        if 'image_versions2' not in item:
            log.debug('Reel item `%s` has neither image nor video data.', item.get('pk'))
            return
        await self.save_image_versions2(item, item['taken_at'])

    async def save_comments(self, edge: Edge) -> None:
        """
        Save comments for an edge node.

        Parameters
        ----------
        edge : Edge
            Edge whose comments should be saved.
        """
        comment_url = f'https://www.instagram.com/api/v1/media/{edge["node"]["id"]}/comments/'
        shared_params = {'can_support_threading': 'true'}
        try:
            comment_data = await self.get_json(comment_url,
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
                comment_data = await self.get_json(comment_url,
                                                   params={
                                                       **shared_params, 'min_id':
                                                           comment_data['next_min_id']
                                                   },
                                                   cast_to=Comments)
            except HTTPError:
                log.exception('Failed to get comments.')
                break
            top_comment_data['comments'] = list(top_comment_data['comments']) + list(
                comment_data['comments'])
        comments_json = f'{edge["node"]["id"]}-comments.json'
        dump_json(comments_json, top_comment_data, mode='w+')

    async def save_media(self, edge: Edge) -> None:
        """
        Save media for an edge node.

        Parameters
        ----------
        edge : Edge
            Edge whose media should be saved.

        Raises
        ------
        UnexpectedRedirect
            If a redirect occurs unexpectedly.
        """
        media_info_url = f'https://www.instagram.com/api/v1/media/{edge["node"]["pk"]}/info/'
        log.debug('Saving media at URL: %s', media_info_url)
        if self.is_saved(media_info_url):
            return
        r = await self.session.get(media_info_url, headers=API_HEADERS, allow_redirects=False)
        if r.status_code != HTTPStatus.OK:
            if r.status_code in {HTTPStatus.MOVED_PERMANENTLY, HTTPStatus.FOUND}:
                raise UnexpectedRedirect
            log.warning('GET request failed with status code %s.', r.status_code)
            log.debug('Content: %s', r.text)
            return
        text = r.text or ''
        if 'image_versions2' not in text or 'taken_at' not in text:
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
            if carousel_media := item.get('carousel_media'):
                for sub_item in carousel_media:
                    await self.save_image_versions2(sub_item, timestamp)
            elif 'image_versions2' in item:
                await self.save_image_versions2(item, timestamp)

    async def dispatch_edges(self,
                             edges: Iterable[Edge],
                             image_queue: asyncio.Queue[Edge | None],
                             comments_queue: asyncio.Queue[Edge | None],
                             video_queue: asyncio.Queue[str | None],
                             *,
                             parent_edge: Edge | None = None,
                             stats: Stats | None = None,
                             yt_dlp_state: YTDLPState | None = None) -> None:
        """
        Dispatch edges to the appropriate worker queue.

        Parameters
        ----------
        edges : Iterable[Edge]
            Edges to dispatch.
        image_queue : asyncio.Queue[Edge | None]
            Queue receiving non-video edges.
        comments_queue : asyncio.Queue[Edge | None]
            Queue receiving edges whose comments should also be saved.
        video_queue : asyncio.Queue[str | None]
            Queue receiving video URLs.
        parent_edge : Edge | None
            Optional parent edge used as a fallback for the shortcode lookup.
        stats : Stats | None
            Optional live statistics object whose ``POSTS_HANDLED`` counter is incremented for
            every dispatched edge.
        yt_dlp_state : YTDLPState | None
            Optional yt-dlp progress state whose ``total_urls`` counter is incremented for
            every URL routed to the video worker.
        """
        for edge in edges:
            if stats is not None:
                stats.increment(POSTS_HANDLED)
            if edge['node']['__typename'] != 'XDTMediaDict':
                log.warning(  # type: ignore[unreachable]
                    'Unknown type: `%s`. Item %s will not be processed.',
                    edge['node']['__typename'], edge['node']['id'])
                shortcode = edge['node']['code']
                self.failed_urls.add(f'https://www.instagram.com/p/{shortcode}/')
                continue
            try:
                shortcode = edge['node']['code']
            except KeyError:
                if parent_edge:
                    try:
                        shortcode = parent_edge['node']['code']
                    except KeyError:
                        log.exception('Unknown shortcode.')
                        continue
                else:
                    log.exception('Unknown shortcode.')
                    continue
            if edge['node'].get('video_dash_manifest'):
                await video_queue.put(f'https://www.instagram.com/p/{shortcode}/')
                if yt_dlp_state is not None:
                    yt_dlp_state.total_urls += 1
            else:
                await image_queue.put(edge)
                if self.should_save_comments:
                    await comments_queue.put(edge)

    async def save_edges(self, edges: Iterable[Edge], parent_edge: Edge | None = None) -> None:
        """
        Save edge node media.

        Parameters
        ----------
        edges : Iterable[Edge]
            Edges to process.
        parent_edge : Edge | None
            Optional parent edge used as a fallback for the shortcode lookup.
        """
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
                        await self.save_comments(edge)
                        await self.save_media(edge)
                    except RetryError:
                        log.exception('Retries exhausted.')
                        return
            else:
                log.warning(  # type: ignore[unreachable]
                    'Unknown type: `%s`. Item %s will not be processed.',
                    edge['node']['__typename'], edge['node']['id'])
                shortcode = edge['node']['code']
                self.failed_urls.add(f'https://www.instagram.com/p/{shortcode}/')
