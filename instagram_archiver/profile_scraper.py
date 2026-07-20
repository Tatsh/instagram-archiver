"""Instagram profile scraper."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
import asyncio
import logging

from niquests.exceptions import HTTPError
from typing_extensions import Self, override

from .client import InstagramClient
from .compat import chdir
from .dedup import LogDB
from .typing import (
    BrowserName,
    Edge,
    WebProfileInfo,
    XDTAPIV1FeedUserTimelineGraphQLConnectionContainer,
)
from .utils import SaveCommentsCheckDisabledMixin, dump_json, write_bytes, write_failed_urls
from .workers import WorkerAbort, comments_worker, image_worker, video_worker

if TYPE_CHECKING:
    from types import TracebackType

    from yt_dlp_utils.aio import AsyncYoutubeDL

    from .typing import OnMessage, Stats, YTDLPState

__all__ = ('ProfileScraper',)

log = logging.getLogger(__name__)


class ProfileScraper(SaveCommentsCheckDisabledMixin, InstagramClient):
    """Scrape an Instagram profile timeline."""
    def __init__(self,
                 username: str,
                 *,
                 log_file: str | Path | None = None,
                 output_dir: str | Path | None = None,
                 disable_log: bool = False,
                 browser: BrowserName = 'chrome',
                 browser_profile: str = 'Default',
                 child_comments: bool = False,
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
        child_comments : bool
            Whether to recursively fetch child (reply) comments. Implies ``comments=True``.
        comments : bool
            Whether to save comments or not.
        """
        super().__init__(browser, browser_profile)
        self._output_dir = Path(output_dir or Path.cwd() / username)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._log_db = LogDB(Path(log_file or self._output_dir / '.log.db'), disabled=disable_log)
        self._username = username
        self.should_save_comments = comments or child_comments
        self.should_save_child_comments = child_comments

    @override
    def save_to_log(self, url: str) -> None:
        self._log_db.save(url)

    @override
    def is_saved(self, url: str) -> bool:
        return self._log_db.is_saved(url)

    @override
    async def __aenter__(self) -> Self:
        """
        Enter the context manager.

        Returns
        -------
        Self
            This scraper instance.
        """
        await super().__aenter__()
        return self

    @override
    async def __aexit__(self, _: type[BaseException] | None, __: BaseException | None,
                        ___: TracebackType | None) -> None:
        """Close the SQLite log and the underlying session."""
        self._log_db.close()
        await super().__aexit__(_, __, ___)

    async def _dispatch_reel(self,
                             reel_ids: list[str],
                             *,
                             is_highlight: bool,
                             username: str,
                             video_queue: asyncio.Queue[str | None],
                             yt_dlp_state: YTDLPState | None = None) -> None:
        after: str | None = None
        while True:
            connection = await self.reel_page_gallery(reel_ids,
                                                      after=after,
                                                      is_highlight=is_highlight)
            if connection is None:
                return
            for edge in connection['edges']:
                for item in edge['node']['items']:
                    await self.save_reel_item(item,
                                              video_queue,
                                              username=username,
                                              yt_dlp_state=yt_dlp_state)
            page_info = connection['page_info']
            if not page_info['has_next_page']:
                return
            after = page_info['end_cursor']

    async def _producer(self,
                        image_queue: asyncio.Queue[Edge | None],
                        comments_queue: asyncio.Queue[Edge | None],
                        video_queue: asyncio.Queue[str | None],
                        *,
                        stats: Stats | None = None,
                        yt_dlp_state: YTDLPState | None = None) -> None:
        await self.get_text(f'https://www.instagram.com/{self._username}/')
        self.add_csrf_token_header()
        r = await self.get_json('https://i.instagram.com/api/v1/users/web_profile_info/',
                                params={'username': self._username},
                                cast_to=WebProfileInfo)
        profile_data = r.get('data')
        if profile_data is not None:
            dump_json('web_profile_info.json', r)
            user_info = profile_data['user']
            if not self.is_saved(user_info['profile_pic_url_hd']):
                pic_response = await self.session.get(user_info['profile_pic_url_hd'])
                if pic_response.content is not None:
                    write_bytes('profile_pic.jpg', pic_response.content)
                self.save_to_log(user_info['profile_pic_url_hd'])
            try:
                tray = (await self.highlights_tray(user_info['id']))['tray']
            except HTTPError:
                log.exception('Failed to get highlights data.')
            else:
                highlight_ids = [item['id'].split(':')[-1] for item in tray]
                if highlight_ids:
                    await self._dispatch_reel(highlight_ids,
                                              is_highlight=True,
                                              username=self._username,
                                              video_queue=video_queue,
                                              yt_dlp_state=yt_dlp_state)
            try:
                await self._dispatch_reel([str(user_info['id'])],
                                          is_highlight=False,
                                          username=self._username,
                                          video_queue=video_queue,
                                          yt_dlp_state=yt_dlp_state)
            except HTTPError:
                log.exception('Failed to get current stories.')
            await self.dispatch_edges(user_info['edge_owner_to_timeline_media']['edges'],
                                      image_queue,
                                      comments_queue,
                                      video_queue,
                                      stats=stats,
                                      yt_dlp_state=yt_dlp_state)
        else:
            log.warning('Failed to get user info. Profile information and image will not be saved.')
        d = await self.graphql_query(
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
                '__relay_internal__pv__PolarisShareSheetV3relayprovider': True
            },
            cast_to=XDTAPIV1FeedUserTimelineGraphQLConnectionContainer)
        if not d:
            log.error('First GraphQL query failed.')
            return
        await self.dispatch_edges(d['xdt_api__v1__feed__user_timeline_graphql_connection']['edges'],
                                  image_queue,
                                  comments_queue,
                                  video_queue,
                                  stats=stats,
                                  yt_dlp_state=yt_dlp_state)
        page_info = d['xdt_api__v1__feed__user_timeline_graphql_connection']['page_info']
        while page_info['has_next_page']:
            d = await self.graphql_query(
                {
                    'after': page_info['end_cursor'],
                    'before': None,
                    'data': {
                        'count': 12,
                        'include_reel_media_seen_timestamp': True,
                        'include_relationship_info': True,
                        'latest_besties_reel_media': True,
                        'latest_reel_media': True
                    },
                    'first': 12,
                    'last': None,
                    'username': self._username,
                    '__relay_internal__pv__PolarisIsLoggedInrelayprovider': True,
                    '__relay_internal__pv__PolarisShareSheetV3relayprovider': True
                },
                cast_to=XDTAPIV1FeedUserTimelineGraphQLConnectionContainer)
            if not d:
                break
            page_info = d['xdt_api__v1__feed__user_timeline_graphql_connection']['page_info']
            await self.dispatch_edges(
                d['xdt_api__v1__feed__user_timeline_graphql_connection']['edges'],
                image_queue,
                comments_queue,
                video_queue,
                stats=stats,
                yt_dlp_state=yt_dlp_state)

    async def process(self,
                      ydl: AsyncYoutubeDL,
                      *,
                      fail: bool = False,
                      on_cleanup: OnMessage | None = None,
                      on_message: OnMessage | None = None,
                      stats: Stats | None = None,
                      yt_dlp_idle_event: asyncio.Event | None = None,
                      yt_dlp_state: YTDLPState | None = None) -> None:
        """
        Process posts in parallel using producer/consumer queues.

        Parameters
        ----------
        ydl : AsyncYoutubeDL
            Configured yt-dlp wrapper.
        fail : bool
            Whether yt-dlp failures should abort processing.
        on_cleanup : OnMessage | None
            Optional callback that receives cleanup status updates.
        on_message : OnMessage | None
            Optional callback that receives progress text updates.
        stats : Stats | None
            Optional live statistics object.
        yt_dlp_idle_event : asyncio.Event | None
            Optional event that the video worker sets when idle.
        yt_dlp_state : YTDLPState | None
            Optional yt-dlp progress state shared with the video worker.

        Raises
        ------
        asyncio.CancelledError
            Re-raised when the producer is cancelled (typically from a termination signal).
        """
        with chdir(self._output_dir):
            stop_event = asyncio.Event()
            first_exception: list[BaseException] = []
            image_queue: asyncio.Queue[Edge | None] = asyncio.Queue()
            comments_queue: asyncio.Queue[Edge | None] = asyncio.Queue()
            video_queue: asyncio.Queue[str | None] = asyncio.Queue()
            workers = (asyncio.create_task(
                image_worker(image_queue,
                             first_exception,
                             self.save_media,
                             stop_event,
                             on_cleanup=on_cleanup,
                             on_message=on_message,
                             stats=stats)),
                       asyncio.create_task(
                           comments_worker(comments_queue,
                                           first_exception,
                                           self.save_comments,
                                           stop_event,
                                           on_cleanup=on_cleanup,
                                           on_message=on_message,
                                           stats=stats)),
                       asyncio.create_task(
                           video_worker(video_queue,
                                        first_exception,
                                        self.failed_urls,
                                        stop_event,
                                        fail=fail,
                                        idle_event=yt_dlp_idle_event,
                                        is_saved=self.is_saved,
                                        on_cleanup=on_cleanup,
                                        on_message=on_message,
                                        save_to_log=self.save_to_log,
                                        stats=stats,
                                        ydl=ydl,
                                        yt_dlp_state=yt_dlp_state)))
            try:
                await self._producer(image_queue,
                                     comments_queue,
                                     video_queue,
                                     stats=stats,
                                     yt_dlp_state=yt_dlp_state)
            except asyncio.CancelledError:
                stop_event.set()
                if on_cleanup is not None:
                    on_cleanup('Producer cancellation received.')
                raise
            except Exception as error:  # ruff:ignore[blind-except]
                if not stop_event.is_set():
                    first_exception.append(error)
                    stop_event.set()
            finally:
                await image_queue.put(None)
                if on_cleanup is not None:
                    on_cleanup('Queued image worker shutdown sentinel.')
                await comments_queue.put(None)
                if on_cleanup is not None:
                    on_cleanup('Queued comments worker shutdown sentinel.')
                await video_queue.put(None)
                if on_cleanup is not None:
                    on_cleanup('Queued yt-dlp worker shutdown sentinel.')
            await asyncio.gather(*workers, return_exceptions=True)
            if on_cleanup is not None:
                on_cleanup('All worker tasks cleaned up.')
            if self.failed_urls:
                log.warning('Some URIs failed. Check failed.txt.')
                write_failed_urls('failed.txt', self.failed_urls)
            if first_exception:
                if isinstance(first_exception[0], WorkerAbort):
                    return
                raise first_exception[0]
