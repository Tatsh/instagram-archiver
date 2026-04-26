"""Worker orchestration for asynchronous edge processing."""

from __future__ import annotations

from typing import TYPE_CHECKING
import logging

from .typing import (
    COMMENTS_PROCESSED,
    IMAGES_PROCESSED,
    VIDEOS_PROCESSED,
    YT_DLP_STATUS,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    import asyncio

    from yt_dlp_utils.aio import AsyncYoutubeDL

    from .typing import Edge, OnMessage, Stats, YTDLPState

__all__ = ('WorkerAbort', 'comments_worker', 'image_worker', 'video_worker')

log = logging.getLogger(__name__)


class WorkerAbort(Exception):
    """Worker-level abort signal for graceful CLI handling."""


def _set_first_exception(first_exception: list[BaseException], error: BaseException,
                         stop_event: asyncio.Event) -> None:
    """
    Set the first fatal exception and trigger shutdown.

    Parameters
    ----------
    first_exception : list[BaseException]
        Mutable container for the first observed fatal exception.
    error : BaseException
        The exception to store.
    stop_event : asyncio.Event
        Event signalling that the pipeline should stop.
    """
    if not stop_event.is_set():
        first_exception.append(error)
        stop_event.set()


async def image_worker(image_queue: asyncio.Queue[Edge | None],
                       first_exception: list[BaseException],
                       save_media: Callable[[Edge], Awaitable[None]],
                       stop_event: asyncio.Event,
                       *,
                       on_cleanup: OnMessage | None = None,
                       on_message: OnMessage | None = None,
                       stats: Stats | None = None) -> None:
    """
    Save image/post media sequentially.

    Parameters
    ----------
    image_queue : asyncio.Queue[Edge | None]
        Queue containing edge payloads to save. ``None`` is a shutdown sentinel.
    first_exception : list[BaseException]
        Mutable container for the first observed fatal exception.
    save_media : Callable[[Edge], Awaitable[None]]
        Coroutine factory invoked once per edge to perform the download.
    stop_event : asyncio.Event
        Event indicating that workers should stop.
    on_cleanup : OnMessage | None
        Optional callback that receives cleanup status updates.
    on_message : OnMessage | None
        Optional callback that receives progress text updates.
    stats : Stats | None
        Optional live statistics object updated after each saved post.
    """
    while not stop_event.is_set():
        edge = await image_queue.get()
        try:
            if edge is None:
                if on_cleanup is not None:
                    on_cleanup('Image worker exited.')
                return
            if on_message is not None:
                on_message(f'Saving media for post {edge["node"].get("id", "?")}...')
            await save_media(edge)
            if stats is not None:
                stats.increment(IMAGES_PROCESSED)
        except Exception as error:  # noqa: BLE001
            _set_first_exception(first_exception, error, stop_event)
            return
        finally:
            image_queue.task_done()


async def comments_worker(comments_queue: asyncio.Queue[Edge | None],
                          first_exception: list[BaseException],
                          save_comments: Callable[[Edge], Awaitable[None]],
                          stop_event: asyncio.Event,
                          *,
                          on_cleanup: OnMessage | None = None,
                          on_message: OnMessage | None = None,
                          stats: Stats | None = None) -> None:
    """
    Save comments for posts sequentially.

    Parameters
    ----------
    comments_queue : asyncio.Queue[Edge | None]
        Queue containing edge payloads whose comments should be saved. ``None`` is a
        shutdown sentinel.
    first_exception : list[BaseException]
        Mutable container for the first observed fatal exception.
    save_comments : Callable[[Edge], Awaitable[None]]
        Coroutine factory invoked once per edge to fetch comments.
    stop_event : asyncio.Event
        Event indicating that workers should stop.
    on_cleanup : OnMessage | None
        Optional callback that receives cleanup status updates.
    on_message : OnMessage | None
        Optional callback that receives progress text updates.
    stats : Stats | None
        Optional live statistics object updated after each comment thread.
    """
    while not stop_event.is_set():
        edge = await comments_queue.get()
        try:
            if edge is None:
                if on_cleanup is not None:
                    on_cleanup('Comments worker exited.')
                return
            if on_message is not None:
                on_message(f'Saving comments for post {edge["node"].get("id", "?")}...')
            await save_comments(edge)
            if stats is not None:
                stats.increment(COMMENTS_PROCESSED)
        except Exception as error:  # noqa: BLE001
            _set_first_exception(first_exception, error, stop_event)
            return
        finally:
            comments_queue.task_done()


async def video_worker(video_queue: asyncio.Queue[str | None],
                       first_exception: list[BaseException],
                       failed_urls: set[str],
                       stop_event: asyncio.Event,
                       *,
                       fail: bool,
                       idle_event: asyncio.Event | None = None,
                       is_saved: Callable[[str], bool],
                       on_cleanup: OnMessage | None = None,
                       on_message: OnMessage | None = None,
                       save_to_log: Callable[[str], None],
                       stats: Stats | None = None,
                       ydl: AsyncYoutubeDL,
                       yt_dlp_state: YTDLPState | None = None) -> None:
    """
    Process video URLs one yt-dlp download at a time.

    Parameters
    ----------
    video_queue : asyncio.Queue[str | None]
        Queue containing video URLs. ``None`` is a shutdown sentinel.
    first_exception : list[BaseException]
        Mutable container for the first observed fatal exception.
    failed_urls : set[str]
        Set updated with URLs whose download did not produce any media.
    stop_event : asyncio.Event
        Event indicating that workers should stop.
    fail : bool
        Whether yt-dlp failures should abort processing.
    idle_event : asyncio.Event | None
        Optional event that is set when the worker is idle and cleared while a
        download is in progress.
    is_saved : Callable[[str], bool]
        Callback returning ``True`` if a URL has already been archived.
    on_cleanup : OnMessage | None
        Optional callback that receives cleanup status updates.
    on_message : OnMessage | None
        Optional callback that receives progress text updates.
    save_to_log : Callable[[str], None]
        Callback used to record a successfully downloaded URL.
    stats : Stats | None
        Optional live statistics object updated after each video URL.
    ydl : AsyncYoutubeDL
        Configured yt-dlp wrapper instance.
    yt_dlp_state : YTDLPState | None
        Optional yt-dlp progress state updated with the current URL and index.
    """
    if idle_event is not None:
        idle_event.set()
    while not stop_event.is_set():
        url = await video_queue.get()
        try:
            if url is None:
                if on_cleanup is not None:
                    on_cleanup('yt-dlp worker exited.')
                return
            if is_saved(url):
                log.debug('%s is already saved.', url)
                continue
            try:
                if idle_event is not None:
                    idle_event.clear()
                if yt_dlp_state is not None:
                    yt_dlp_state.current_url = url
                    yt_dlp_state.current_index += 1
                    if stats is not None:
                        stats[YT_DLP_STATUS] = yt_dlp_state.render()
                if on_message is not None:
                    on_message(f'Downloading {url} with yt-dlp...')
                return_code = await ydl.download((url,))
                if return_code == 0:
                    save_to_log(url)
                    if stats is not None:
                        stats.increment(VIDEOS_PROCESSED)
                else:
                    failed_urls.add(url)
                    log.error('yt-dlp returned error code %d for %s.', return_code, url)
                    if fail:
                        _set_first_exception(first_exception, WorkerAbort(), stop_event)
            except Exception:
                failed_urls.add(url)
                log.exception('yt-dlp failure.')
                if fail:
                    _set_first_exception(first_exception, WorkerAbort(), stop_event)
            finally:
                if yt_dlp_state is not None:
                    yt_dlp_state.current_url = None
                    if stats is not None:
                        stats[YT_DLP_STATUS] = yt_dlp_state.render()
                if idle_event is not None:
                    idle_event.set()
        finally:
            video_queue.task_done()
