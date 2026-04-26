from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock
import asyncio

from instagram_archiver.typing import (
    COMMENTS_PROCESSED,
    IMAGES_PROCESSED,
    VIDEOS_PROCESSED,
    YT_DLP_STATUS,
    Stats,
    YTDLPState,
)
from instagram_archiver.workers import (
    WorkerAbort,
    comments_worker,
    image_worker,
    video_worker,
)
import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


async def test_image_worker_processes_then_exits(mocker: MockerFixture) -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    edge = {'node': {'id': 'eid'}}
    await queue.put(edge)
    await queue.put(None)
    save = AsyncMock()
    stats = Stats()
    on_message = mocker.MagicMock()
    on_cleanup = mocker.MagicMock()
    stop = asyncio.Event()
    first: list[BaseException] = []
    await image_worker(queue,
                       first,
                       save,
                       stop,
                       on_message=on_message,
                       on_cleanup=on_cleanup,
                       stats=stats)
    save.assert_awaited_once_with(edge)
    on_message.assert_called_once()
    on_cleanup.assert_called_once()
    assert stats[IMAGES_PROCESSED] == 1


async def test_image_worker_stops_on_event() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put(None)
    save = AsyncMock()
    stop = asyncio.Event()
    stop.set()
    first: list[BaseException] = []
    await image_worker(queue, first, save, stop)


async def test_image_worker_records_first_exception() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put({'node': {'id': 'x'}})
    save = AsyncMock(side_effect=RuntimeError('boom'))
    stop = asyncio.Event()
    first: list[BaseException] = []
    await image_worker(queue, first, save, stop)
    assert first
    assert isinstance(first[0], RuntimeError)
    assert stop.is_set()


async def test_image_worker_no_op_when_stop_already_set_during_save() -> None:
    """If ``stop_event`` is already set when ``save_media`` raises, the worker doesn't append.

    Exercises the ``_set_first_exception`` branch where ``stop_event.is_set()`` is True.
    """
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put({'node': {'id': 'x'}})
    stop = asyncio.Event()

    async def _set_then_raise(_edge: Any) -> None:
        stop.set()
        msg = 'after stop'
        raise RuntimeError(msg)

    first: list[BaseException] = []
    await image_worker(queue, first, _set_then_raise, stop)
    # `_set_first_exception` short-circuits because `stop` was already set, so `first`
    # remains empty even though the worker observed an exception.
    assert first == []


async def test_image_worker_no_callbacks_no_stats() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put({'node': {'id': 'x'}})
    await queue.put(None)
    save = AsyncMock()
    stop = asyncio.Event()
    first: list[BaseException] = []
    await image_worker(queue, first, save, stop)
    save.assert_awaited_once()


async def test_comments_worker_processes_then_exits(mocker: MockerFixture) -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    edge = {'node': {'id': 'cid'}}
    await queue.put(edge)
    await queue.put(None)
    save = AsyncMock()
    stats = Stats()
    on_message = mocker.MagicMock()
    on_cleanup = mocker.MagicMock()
    stop = asyncio.Event()
    first: list[BaseException] = []
    await comments_worker(queue,
                          first,
                          save,
                          stop,
                          on_message=on_message,
                          on_cleanup=on_cleanup,
                          stats=stats)
    save.assert_awaited_once_with(edge)
    on_message.assert_called_once()
    on_cleanup.assert_called_once()
    assert stats[COMMENTS_PROCESSED] == 1


async def test_comments_worker_records_first_exception() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put({'node': {'id': 'y'}})
    save = AsyncMock(side_effect=RuntimeError('boom'))
    stop = asyncio.Event()
    first: list[BaseException] = []
    await comments_worker(queue, first, save, stop)
    assert first
    assert isinstance(first[0], RuntimeError)
    assert stop.is_set()


async def test_comments_worker_no_callbacks() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put({'node': {'id': 'x'}})
    await queue.put(None)
    save = AsyncMock()
    stop = asyncio.Event()
    first: list[BaseException] = []
    await comments_worker(queue, first, save, stop)
    save.assert_awaited_once()


async def test_video_worker_success(mocker: MockerFixture) -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put('https://example.com/v')
    await queue.put(None)
    ydl = mocker.MagicMock()
    ydl.download = AsyncMock(return_value=0)
    stats = Stats()
    state = YTDLPState()
    save_to_log = mocker.MagicMock()
    is_saved = mocker.MagicMock(return_value=False)
    on_cleanup = mocker.MagicMock()
    on_message = mocker.MagicMock()
    stop = asyncio.Event()
    first: list[BaseException] = []
    failed: set[str] = set()
    idle = asyncio.Event()
    await video_worker(queue,
                       first,
                       failed,
                       stop,
                       fail=False,
                       idle_event=idle,
                       is_saved=is_saved,
                       on_cleanup=on_cleanup,
                       on_message=on_message,
                       save_to_log=save_to_log,
                       stats=stats,
                       ydl=ydl,
                       yt_dlp_state=state)
    save_to_log.assert_called_once_with('https://example.com/v')
    assert stats[VIDEOS_PROCESSED] == 1
    assert state.current_url is None
    assert idle.is_set()


async def test_video_worker_skips_already_saved(mocker: MockerFixture) -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put('https://example.com/v')
    await queue.put(None)
    ydl = mocker.MagicMock()
    ydl.download = AsyncMock()
    stop = asyncio.Event()
    first: list[BaseException] = []
    failed: set[str] = set()
    is_saved = mocker.MagicMock(return_value=True)
    save_to_log = mocker.MagicMock()
    await video_worker(queue,
                       first,
                       failed,
                       stop,
                       fail=False,
                       is_saved=is_saved,
                       save_to_log=save_to_log,
                       ydl=ydl)
    ydl.download.assert_not_called()
    save_to_log.assert_not_called()


async def test_video_worker_nonzero_returncode_no_fail(mocker: MockerFixture) -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put('https://example.com/v')
    await queue.put(None)
    ydl = mocker.MagicMock()
    ydl.download = AsyncMock(return_value=1)
    stop = asyncio.Event()
    first: list[BaseException] = []
    failed: set[str] = set()
    await video_worker(queue,
                       first,
                       failed,
                       stop,
                       fail=False,
                       is_saved=mocker.MagicMock(return_value=False),
                       save_to_log=mocker.MagicMock(),
                       ydl=ydl)
    assert 'https://example.com/v' in failed
    assert not first


async def test_video_worker_nonzero_returncode_with_fail(mocker: MockerFixture) -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put('https://example.com/v')
    ydl = mocker.MagicMock()
    ydl.download = AsyncMock(return_value=1)
    stop = asyncio.Event()
    first: list[BaseException] = []
    failed: set[str] = set()
    await video_worker(queue,
                       first,
                       failed,
                       stop,
                       fail=True,
                       is_saved=mocker.MagicMock(return_value=False),
                       save_to_log=mocker.MagicMock(),
                       ydl=ydl)
    assert first
    assert isinstance(first[0], WorkerAbort)


async def test_video_worker_exception_fail(mocker: MockerFixture) -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put('https://example.com/v')
    ydl = mocker.MagicMock()
    ydl.download = AsyncMock(side_effect=RuntimeError('boom'))
    stop = asyncio.Event()
    first: list[BaseException] = []
    failed: set[str] = set()
    await video_worker(queue,
                       first,
                       failed,
                       stop,
                       fail=True,
                       is_saved=mocker.MagicMock(return_value=False),
                       save_to_log=mocker.MagicMock(),
                       ydl=ydl)
    assert 'https://example.com/v' in failed
    assert first
    assert isinstance(first[0], WorkerAbort)


async def test_video_worker_exception_no_fail(mocker: MockerFixture) -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put('https://example.com/v')
    await queue.put(None)
    ydl = mocker.MagicMock()
    ydl.download = AsyncMock(side_effect=RuntimeError('boom'))
    stop = asyncio.Event()
    first: list[BaseException] = []
    failed: set[str] = set()
    await video_worker(queue,
                       first,
                       failed,
                       stop,
                       fail=False,
                       is_saved=mocker.MagicMock(return_value=False),
                       save_to_log=mocker.MagicMock(),
                       ydl=ydl)
    assert 'https://example.com/v' in failed
    assert not first


async def test_video_worker_state_no_stats(mocker: MockerFixture) -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put('https://example.com/v')
    await queue.put(None)
    ydl = mocker.MagicMock()
    ydl.download = AsyncMock(return_value=0)
    stop = asyncio.Event()
    first: list[BaseException] = []
    failed: set[str] = set()
    state = YTDLPState(total_urls=1)
    await video_worker(queue,
                       first,
                       failed,
                       stop,
                       fail=False,
                       is_saved=mocker.MagicMock(return_value=False),
                       save_to_log=mocker.MagicMock(),
                       ydl=ydl,
                       yt_dlp_state=state)
    assert state.current_index == 1


async def test_video_worker_state_render(mocker: MockerFixture) -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put('https://example.com/v')
    await queue.put(None)
    ydl = mocker.MagicMock()
    ydl.download = AsyncMock(return_value=0)
    stop = asyncio.Event()
    first: list[BaseException] = []
    failed: set[str] = set()
    state = YTDLPState(total_urls=2)
    stats = Stats()
    await video_worker(queue,
                       first,
                       failed,
                       stop,
                       fail=False,
                       is_saved=mocker.MagicMock(return_value=False),
                       save_to_log=mocker.MagicMock(),
                       stats=stats,
                       ydl=ydl,
                       yt_dlp_state=state)
    # After processing one URI, current_index advances and stats reflect cleared status.
    assert state.current_index == 1
    assert stats[YT_DLP_STATUS] is None


def test_yt_dlp_state_render_idle() -> None:
    state = YTDLPState()
    assert state.render() is None


def test_yt_dlp_state_render_active() -> None:
    state = YTDLPState(current_index=1, current_url='https://x', total_urls=3)
    assert state.render() == 'https://x (1/3)'


def test_stats_construction() -> None:
    stats = Stats()
    stats.increment(IMAGES_PROCESSED)
    assert stats[IMAGES_PROCESSED] == 1


@pytest.mark.parametrize(('worker', 'queue_kind'), [(image_worker, 'image'),
                                                    (comments_worker, 'comments')])
async def test_worker_immediate_sentinel(worker: Any, queue_kind: str,
                                         mocker: MockerFixture) -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    await queue.put(None)
    save = AsyncMock()
    stop = asyncio.Event()
    first: list[BaseException] = []
    await worker(queue, first, save, stop)
    save.assert_not_called()
