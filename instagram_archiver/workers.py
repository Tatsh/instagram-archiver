"""Worker orchestration for asynchronous edge processing."""

from __future__ import annotations

from typing import TYPE_CHECKING
import logging

from .typing import COMMENTS_PROCESSED, IMAGES_PROCESSED, VIDEOS_PROCESSED, YT_DLP_STATUS

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


async def _process_edge(edge: Edge | None, save: Callable[[Edge], Awaitable[None]], *,
                        exit_message: str, message_prefix: str, on_cleanup: OnMessage | None,
                        on_message: OnMessage | None, stat_key: str, stats: Stats | None) -> bool:
    """
    Process a single queued edge for the image or comments worker.

    Parameters
    ----------
    edge : Edge | None
        Edge payload to save, or ``None`` for the shutdown sentinel.
    save : Callable[[Edge], Awaitable[None]]
        Coroutine factory invoked to persist the edge.
    exit_message : str
        Cleanup message emitted when the shutdown sentinel is received.
    message_prefix : str
        Prefix for the per-post progress message.
    on_cleanup : OnMessage | None
        Optional callback that receives cleanup status updates.
    on_message : OnMessage | None
        Optional callback that receives progress text updates.
    stat_key : str
        Statistics counter incremented after a successful save.
    stats : Stats | None
        Optional live statistics object.

    Returns
    -------
    bool
        ``True`` if the worker should keep running, ``False`` on the shutdown sentinel.
    """
    if edge is None:
        if on_cleanup is not None:
            on_cleanup(exit_message)
        return False
    if on_message is not None:
        on_message(f'{message_prefix} {edge["node"].get("id", "?")}...')
    await save(edge)
    if stats is not None:
        stats.increment(stat_key)
    return True


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
            if not await _process_edge(edge,
                                       save_media,
                                       exit_message='Image worker exited.',
                                       message_prefix='Saving media for post',
                                       on_cleanup=on_cleanup,
                                       on_message=on_message,
                                       stat_key=IMAGES_PROCESSED,
                                       stats=stats):
                return
        except Exception as error:  # ruff:ignore[blind-except]
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
            if not await _process_edge(edge,
                                       save_comments,
                                       exit_message='Comments worker exited.',
                                       message_prefix='Saving comments for post',
                                       on_cleanup=on_cleanup,
                                       on_message=on_message,
                                       stat_key=COMMENTS_PROCESSED,
                                       stats=stats):
                return
        except Exception as error:  # ruff:ignore[blind-except]
            _set_first_exception(first_exception, error, stop_event)
            return
        finally:
            comments_queue.task_done()


async def _run_yt_dlp(url: str, first_exception: list[BaseException], failed_urls: set[str],
                      stop_event: asyncio.Event, *, fail: bool, on_message: OnMessage | None,
                      save_to_log: Callable[[str], None], stats: Stats | None, ydl: AsyncYoutubeDL,
                      yt_dlp_state: YTDLPState | None) -> None:
    """
    Download a single URL with yt-dlp and record the outcome.

    Parameters
    ----------
    url : str
        The video URL to download.
    first_exception : list[BaseException]
        Mutable container for the first observed fatal exception.
    failed_urls : set[str]
        Set updated with URLs whose download did not produce any media.
    stop_event : asyncio.Event
        Event indicating that workers should stop.
    fail : bool
        Whether a non-zero yt-dlp return code should abort processing.
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
    if yt_dlp_state is not None:
        yt_dlp_state.current_url = url
        yt_dlp_state.current_index += 1
        if stats is not None:
            stats[YT_DLP_STATUS] = yt_dlp_state.render()
    if on_message is not None:
        on_message(f'Downloading {url} with yt-dlp...')
    if (return_code := await ydl.download((url,))) == 0:
        save_to_log(url)
        if stats is not None:
            stats.increment(VIDEOS_PROCESSED)
        return
    failed_urls.add(url)
    log.error('yt-dlp returned error code %d for %s.', return_code, url)
    if fail:
        _set_first_exception(first_exception, WorkerAbort(), stop_event)


async def _process_video_url(url: str | None, first_exception: list[BaseException],
                             failed_urls: set[str], stop_event: asyncio.Event, *, fail: bool,
                             idle_event: asyncio.Event | None, is_saved: Callable[[str], bool],
                             on_cleanup: OnMessage | None, on_message: OnMessage | None,
                             save_to_log: Callable[[str], None], stats: Stats | None,
                             ydl: AsyncYoutubeDL, yt_dlp_state: YTDLPState | None) -> bool:
    """
    Handle a single queued video URL, including the yt-dlp lifecycle.

    Parameters
    ----------
    url : str | None
        The video URL to process, or ``None`` for the shutdown sentinel.
    first_exception : list[BaseException]
        Mutable container for the first observed fatal exception.
    failed_urls : set[str]
        Set updated with URLs whose download did not produce any media.
    stop_event : asyncio.Event
        Event indicating that workers should stop.
    fail : bool
        Whether a yt-dlp failure should abort processing.
    idle_event : asyncio.Event | None
        Optional event cleared while a download is in progress and set when idle.
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

    Returns
    -------
    bool
        ``True`` if the worker should keep running, ``False`` on the shutdown sentinel.
    """
    if url is None:
        if on_cleanup is not None:
            on_cleanup('yt-dlp worker exited.')
        return False
    if is_saved(url):
        log.debug('%s is already saved.', url)
        return True
    try:
        if idle_event is not None:
            idle_event.clear()
        await _run_yt_dlp(url,
                          first_exception,
                          failed_urls,
                          stop_event,
                          fail=fail,
                          on_message=on_message,
                          save_to_log=save_to_log,
                          stats=stats,
                          ydl=ydl,
                          yt_dlp_state=yt_dlp_state)
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
    return True


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
            if not await _process_video_url(url,
                                            first_exception,
                                            failed_urls,
                                            stop_event,
                                            fail=fail,
                                            idle_event=idle_event,
                                            is_saved=is_saved,
                                            on_cleanup=on_cleanup,
                                            on_message=on_message,
                                            save_to_log=save_to_log,
                                            stats=stats,
                                            ydl=ydl,
                                            yt_dlp_state=yt_dlp_state):
                return
        finally:
            video_queue.task_done()
