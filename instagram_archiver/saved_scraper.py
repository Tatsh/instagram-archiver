"""Saved posts scraper."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
import asyncio
import logging

from typing_extensions import Self, override

from .client import InstagramClient
from .compat import chdir
from .constants import API_HEADERS, PAGE_FETCH_HEADERS
from .dedup import LogDB
from .utils import SaveCommentsCheckDisabledMixin
from .workers import WorkerAbort, comments_worker, image_worker, video_worker

if TYPE_CHECKING:
    from collections.abc import Iterable
    from types import TracebackType

    from yt_dlp_utils.aio import AsyncYoutubeDL

    from .typing import BrowserName, Edge, OnMessage, Stats, YTDLPState

__all__ = ('SavedScraper',)

log = logging.getLogger(__name__)


class SavedScraper(SaveCommentsCheckDisabledMixin, InstagramClient):
    """Scrape saved posts."""
    def __init__(self,
                 browser: BrowserName = 'chrome',
                 browser_profile: str = 'Default',
                 output_dir: str | Path | None = None,
                 *,
                 comments: bool = False,
                 disable_log: bool = False,
                 log_file: str | Path | None = None) -> None:
        """
        Initialise ``SavedScraper``.

        Parameters
        ----------
        browser : BrowserName
            The browser to use.
        browser_profile : str
            The browser profile to use.
        output_dir : str | Path | None
            The output directory to save the posts to.
        comments : bool
            Whether to save comments or not.
        disable_log : bool
            Whether to disable the SQLite dedup log.
        log_file : str | Path | None
            Custom path for the dedup log database. Defaults to ``.log.db`` inside
            ``output_dir``.
        """
        super().__init__(browser, browser_profile)
        self._output_dir = Path(output_dir or Path.cwd() / '@@saved-posts@@')
        Path(self._output_dir).mkdir(parents=True, exist_ok=True)
        self._log_db = LogDB(Path(log_file or self._output_dir / '.log.db'), disabled=disable_log)
        self.should_save_comments = comments

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

    async def unsave(self, items: Iterable[str]) -> None:
        """
        Unsave saved posts.

        Parameters
        ----------
        items : Iterable[str]
            Shortcodes to unsave.
        """
        for item in items:
            log.debug('Unsaving %s.', item)
            await self.session.post(f'https://www.instagram.com/web/save/{item}/unsave/',
                                    headers=API_HEADERS)

    async def _producer(self,
                        image_queue: asyncio.Queue[Edge | None],
                        comments_queue: asyncio.Queue[Edge | None],
                        video_queue: asyncio.Queue[str | None],
                        *,
                        stats: Stats | None = None,
                        unsave: bool,
                        yt_dlp_state: YTDLPState | None = None) -> None:
        self.add_csrf_token_header()
        await self.session.get('https://www.instagram.com/', headers=PAGE_FETCH_HEADERS)
        feed = await self.get_json('https://www.instagram.com/api/v1/feed/saved/posts/',
                                   cast_to=dict[str, Any])
        edges: Iterable[Edge] = cast('Iterable[Edge]', ({
            'node': {
                '__typename': 'XDTMediaDict',
                'id': item['media']['id'],
                'code': item['media']['code'],
                'owner': item['media']['owner'],
                'pk': item['media']['pk'],
                'video_dash_manifest': item['media'].get('video_dash_manifest')
            }
        } for item in feed['items']))
        await self.dispatch_edges(edges,
                                  image_queue,
                                  comments_queue,
                                  video_queue,
                                  stats=stats,
                                  yt_dlp_state=yt_dlp_state)
        if unsave:
            await self.unsave(item['media']['code'] for item in feed['items'])
        if feed.get('more_available'):
            log.warning('Unhandled pagination.')

    async def process(self,
                      ydl: AsyncYoutubeDL,
                      *,
                      fail: bool = False,
                      on_cleanup: OnMessage | None = None,
                      on_message: OnMessage | None = None,
                      stats: Stats | None = None,
                      unsave: bool = False,
                      yt_dlp_idle_event: asyncio.Event | None = None,
                      yt_dlp_state: YTDLPState | None = None) -> None:
        """
        Process the saved posts in parallel using producer/consumer queues.

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
        unsave : bool
            If ``True``, unsave each post after dispatching it.
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
                                     unsave=unsave,
                                     yt_dlp_state=yt_dlp_state)
            except asyncio.CancelledError:
                stop_event.set()
                if on_cleanup is not None:
                    on_cleanup('Producer cancellation received.')
                raise
            except Exception as error:  # noqa: BLE001
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
            if first_exception:
                if isinstance(first_exception[0], WorkerAbort):
                    return
                raise first_exception[0]
