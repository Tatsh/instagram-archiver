from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

from instagram_archiver.profile_scraper import ProfileScraper
from instagram_archiver.saved_scraper import SavedScraper
from instagram_archiver.workers import WorkerAbort
from niquests.exceptions import HTTPError
import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _patch_db(mocker: MockerFixture,
              *,
              exists: bool = True,
              size: int = 1,
              fetchone_value: tuple[int, ...] = (0,)) -> Any:
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = exists
    mock_path.return_value.stat.return_value.st_size = size
    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchone.return_value = fetchone_value
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    return mock_cursor


def test_profile_scraper_no_log(mocker: MockerFixture, mock_setup_session: AsyncMock) -> None:
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mocker.patch('instagram_archiver.profile_scraper.Path')
    scraper_with_no_logging: Any = ProfileScraper('test_user', disable_log=True)
    ex = scraper_with_no_logging._cursor.execute  # noqa: SLF001
    ex.assert_not_called()  # ty: ignore[unresolved-attribute]


def test_profile_scraper_with_empty_log(mocker: MockerFixture,
                                        mock_setup_session: AsyncMock) -> None:
    mock_cursor = _patch_db(mocker, exists=True, size=0)
    ProfileScraper('test_user')
    mock_cursor.execute.assert_called_once()


def test_profile_scraper_with_no_log(mocker: MockerFixture, mock_setup_session: AsyncMock) -> None:
    mock_cursor = _patch_db(mocker, exists=False)
    ProfileScraper('test_user')
    mock_cursor.execute.assert_called_once()


def test_profile_scraper_with_log_existing(mocker: MockerFixture,
                                           mock_setup_session: AsyncMock) -> None:
    mock_cursor = _patch_db(mocker, exists=True, size=1)
    ProfileScraper('test_user')
    mock_cursor.execute.assert_not_called()


async def test_save_comments_does_nothing_when_disabled(mocker: MockerFixture,
                                                        mock_setup_session: AsyncMock) -> None:
    _patch_db(mocker)
    mock_super = mocker.patch('instagram_archiver.profile_scraper.InstagramClient.save_comments',
                              new_callable=AsyncMock)

    scraper = ProfileScraper('test_user')
    await scraper.save_comments({
        'node': {
            '__typename': 'XDTMediaDict',
            'code': '12345',
            'id': '12345',
            'owner': {
                'id': '67890',
                'username': 'username'
            },
            'pk': '92834',
            'video_dash_manifest': None
        }
    })
    mock_super.assert_not_called()


async def test_save_comments_runs_when_enabled(mocker: MockerFixture,
                                               mock_setup_session: AsyncMock) -> None:
    _patch_db(mocker)
    mock_super = mocker.patch('instagram_archiver.profile_scraper.InstagramClient.save_comments',
                              new_callable=AsyncMock)

    scraper = ProfileScraper('test_user', comments=True)
    await scraper.save_comments({
        'node': {
            '__typename': 'XDTMediaDict',
            'code': '12345',
            'id': '12345',
            'owner': {
                'id': '67890',
                'username': 'username'
            },
            'pk': '1111',
            'video_dash_manifest': None
        }
    })
    mock_super.assert_awaited_once()


def test_save_to_log_disabled(mocker: MockerFixture, mock_setup_session: AsyncMock) -> None:
    mock_cursor = _patch_db(mocker)
    scraper = ProfileScraper('test_user', disable_log=True)
    scraper.save_to_log('test_url')
    mock_cursor.execute.assert_not_called()


def test_save_to_log(mocker: MockerFixture, mock_setup_session: AsyncMock) -> None:
    mock_cursor = _patch_db(mocker)
    scraper = ProfileScraper('test_user')
    scraper.save_to_log('test_url')
    mock_cursor.execute.assert_called_once()


def test_is_saved(mocker: MockerFixture, mock_setup_session: AsyncMock) -> None:
    mock_cursor = _patch_db(mocker, fetchone_value=(1,))
    scraper = ProfileScraper('test_user')
    assert scraper.is_saved('test_url') is True
    mock_cursor.execute.assert_called_once()


def test_is_saved_log_disabled(mocker: MockerFixture, mock_setup_session: AsyncMock) -> None:
    mock_cursor = _patch_db(mocker)
    scraper = ProfileScraper('test_user', disable_log=True)
    scraper.is_saved('test_url')
    mock_cursor.execute.assert_not_called()


async def test_aexit_cleans_up(mocker: MockerFixture, mock_setup_session: AsyncMock) -> None:
    mock_cursor = _patch_db(mocker)
    mock_setup_session.return_value = mocker.MagicMock(close=AsyncMock(),
                                                       headers=mocker.MagicMock(),
                                                       cookies=mocker.MagicMock())
    scraper = ProfileScraper('test_user')
    async with scraper:
        pass
    mock_cursor.close.assert_called_once()


def _build_profile_scraper(mocker: MockerFixture,
                           *,
                           comments: bool = False,
                           video_urls: list[str] | None = None) -> ProfileScraper:
    _patch_db(mocker)
    mocker.patch('instagram_archiver.profile_scraper.chdir')
    mocker.patch('instagram_archiver.profile_scraper.dump_json')
    mocker.patch('instagram_archiver.profile_scraper.write_bytes')
    mocker.patch('instagram_archiver.profile_scraper.write_failed_urls')
    scraper = ProfileScraper('test_user', comments=comments)
    scraper.session = mocker.MagicMock()
    scraper.session.get = AsyncMock(  # type: ignore[method-assign]
        return_value=mocker.MagicMock(content=b'pic'))
    if video_urls:
        scraper.video_urls = video_urls
    return scraper


async def test_process_first_graphql_failure(mocker: MockerFixture,
                                             mock_setup_session: AsyncMock) -> None:
    mock_log_error = mocker.patch('instagram_archiver.profile_scraper.log.error')
    scraper = _build_profile_scraper(mocker)
    mocker.patch.object(scraper,
                        'get_json',
                        new_callable=AsyncMock,
                        return_value={
                            'data': {
                                'user': {
                                    'edge_owner_to_timeline_media': {
                                        'edges': []
                                    },
                                    'id': '12345',
                                    'profile_pic_url_hd': 'https://test_url'
                                }
                            }
                        })
    mocker.patch.object(scraper, 'get_text', new_callable=AsyncMock)
    mocker.patch.object(scraper,
                        'highlights_tray',
                        new_callable=AsyncMock,
                        return_value={'tray': []})
    mocker.patch.object(scraper, 'graphql_query', new_callable=AsyncMock, return_value=None)
    mocker.patch.object(scraper, 'is_saved', return_value=True)
    await scraper.process(mocker.MagicMock())
    mock_log_error.assert_called_once_with('First GraphQL query failed.')


async def test_process_data_not_in_profile_info(mocker: MockerFixture,
                                                mock_setup_session: AsyncMock) -> None:
    mock_log_error = mocker.patch('instagram_archiver.profile_scraper.log.error')
    mock_log_warning = mocker.patch('instagram_archiver.profile_scraper.log.warning')
    scraper = _build_profile_scraper(mocker)
    mocker.patch.object(scraper, 'get_json', new_callable=AsyncMock, return_value={})
    mocker.patch.object(scraper, 'get_text', new_callable=AsyncMock)
    mocker.patch.object(scraper, 'graphql_query', new_callable=AsyncMock, return_value=None)
    await scraper.process(mocker.MagicMock())
    mock_log_error.assert_called_once_with('First GraphQL query failed.')
    mock_log_warning.assert_called_once_with(
        'Failed to get user info. Profile information and image will not be saved.')


async def test_process_already_saved_profile_pic(mocker: MockerFixture,
                                                 mock_setup_session: AsyncMock) -> None:
    mock_log_error = mocker.patch('instagram_archiver.profile_scraper.log.error')
    scraper = _build_profile_scraper(mocker)
    mocker.patch.object(scraper,
                        'get_json',
                        new_callable=AsyncMock,
                        return_value={
                            'data': {
                                'user': {
                                    'edge_owner_to_timeline_media': {
                                        'edges': []
                                    },
                                    'id': '12345',
                                    'profile_pic_url_hd': 'https://test_url'
                                }
                            }
                        })
    mocker.patch.object(scraper, 'get_text', new_callable=AsyncMock)
    mock_save_to_log = mocker.patch.object(scraper, 'save_to_log')
    mocker.patch.object(scraper, 'is_saved', return_value=True)
    mocker.patch.object(scraper,
                        'highlights_tray',
                        new_callable=AsyncMock,
                        return_value={'tray': []})
    mocker.patch.object(scraper, 'graphql_query', new_callable=AsyncMock, return_value=None)
    await scraper.process(mocker.MagicMock())
    mock_save_to_log.assert_not_called()
    mock_log_error.assert_called_once_with('First GraphQL query failed.')


async def test_process_highlights_queues_videos(mocker: MockerFixture,
                                                mock_setup_session: AsyncMock) -> None:
    mocker.patch('instagram_archiver.profile_scraper.log.error')
    scraper = _build_profile_scraper(mocker)
    mocker.patch.object(scraper,
                        'get_json',
                        new_callable=AsyncMock,
                        return_value={
                            'data': {
                                'user': {
                                    'edge_owner_to_timeline_media': {
                                        'edges': []
                                    },
                                    'id': '12345',
                                    'profile_pic_url_hd': 'https://test_url'
                                }
                            }
                        })
    mocker.patch.object(scraper, 'get_text', new_callable=AsyncMock)
    mocker.patch.object(scraper,
                        'highlights_tray',
                        new_callable=AsyncMock,
                        return_value={'tray': [{
                            'id': 'f:12345'
                        }]})
    mocker.patch.object(scraper, 'graphql_query', new_callable=AsyncMock, return_value=None)
    mocker.patch.object(scraper, 'is_saved', return_value=False)
    mocker.patch.object(scraper, 'save_to_log')
    ydl = mocker.MagicMock()
    ydl.download = AsyncMock(return_value=0)
    await scraper.process(ydl)
    ydl.download.assert_awaited_with(('https://www.instagram.com/stories/highlights/12345/',))


async def test_process_highlights_error(mocker: MockerFixture,
                                        mock_setup_session: AsyncMock) -> None:
    mock_log_exception = mocker.patch('instagram_archiver.profile_scraper.log.exception')
    scraper = _build_profile_scraper(mocker)
    mocker.patch.object(scraper,
                        'get_json',
                        new_callable=AsyncMock,
                        return_value={
                            'data': {
                                'user': {
                                    'edge_owner_to_timeline_media': {
                                        'edges': []
                                    },
                                    'id': '12345',
                                    'profile_pic_url_hd': 'https://test_url'
                                }
                            }
                        })
    mocker.patch.object(scraper, 'get_text', new_callable=AsyncMock)
    mocker.patch.object(scraper, 'highlights_tray', new_callable=AsyncMock, side_effect=HTTPError)
    mocker.patch.object(scraper, 'graphql_query', new_callable=AsyncMock, return_value=None)
    mocker.patch.object(scraper, 'is_saved', return_value=True)
    await scraper.process(mocker.MagicMock())
    mock_log_exception.assert_called_once_with('Failed to get highlights data.')


async def test_process_with_pagination(mocker: MockerFixture,
                                       mock_setup_session: AsyncMock) -> None:
    scraper = _build_profile_scraper(mocker)
    mocker.patch.object(scraper,
                        'get_json',
                        new_callable=AsyncMock,
                        return_value={
                            'data': {
                                'user': {
                                    'edge_owner_to_timeline_media': {
                                        'edges': []
                                    },
                                    'id': '12345',
                                    'profile_pic_url_hd': 'https://test_url'
                                }
                            }
                        })
    mocker.patch.object(scraper, 'get_text', new_callable=AsyncMock)
    mocker.patch.object(scraper,
                        'highlights_tray',
                        new_callable=AsyncMock,
                        return_value={'tray': []})
    mocker.patch.object(scraper, 'is_saved', return_value=True)
    mock_graphql_query = mocker.patch.object(
        scraper,
        'graphql_query',
        new_callable=AsyncMock,
        side_effect=[{
            'xdt_api__v1__feed__user_timeline_graphql_connection': {
                'edges': [],
                'page_info': {
                    'has_next_page': True,
                    'end_cursor': 'cur'
                }
            }
        }, {
            'xdt_api__v1__feed__user_timeline_graphql_connection': {
                'edges': [],
                'page_info': {
                    'has_next_page': True,
                    'end_cursor': 'cur'
                }
            }
        }, None])
    await scraper.process(mocker.MagicMock())
    assert mock_graphql_query.call_count == 3


async def test_process_failed_urls_written(mocker: MockerFixture,
                                           mock_setup_session: AsyncMock) -> None:
    scraper = _build_profile_scraper(mocker)
    mock_write = mocker.patch('instagram_archiver.profile_scraper.write_failed_urls')
    scraper.failed_urls.add('https://example.com/p/x/')
    mocker.patch.object(scraper, 'get_json', new_callable=AsyncMock, return_value={})
    mocker.patch.object(scraper, 'get_text', new_callable=AsyncMock)
    mocker.patch.object(scraper, 'graphql_query', new_callable=AsyncMock, return_value=None)
    await scraper.process(mocker.MagicMock())
    mock_write.assert_called_once_with('failed.txt', scraper.failed_urls)


async def test_process_producer_exception_propagates(mocker: MockerFixture,
                                                     mock_setup_session: AsyncMock) -> None:
    scraper = _build_profile_scraper(mocker)
    mocker.patch.object(scraper,
                        'get_text',
                        new_callable=AsyncMock,
                        side_effect=RuntimeError('boom'))
    with pytest.raises(RuntimeError, match='boom'):
        await scraper.process(mocker.MagicMock())


async def test_process_worker_abort_swallowed(mocker: MockerFixture,
                                              mock_setup_session: AsyncMock) -> None:
    scraper = _build_profile_scraper(mocker)
    mocker.patch.object(scraper, 'get_text', new_callable=AsyncMock, side_effect=WorkerAbort())
    await scraper.process(mocker.MagicMock())


async def test_process_saved_with_unsaving(mocker: MockerFixture,
                                           mock_setup_session: AsyncMock) -> None:
    mocker.patch('instagram_archiver.saved_scraper.Path')
    mocker.patch('instagram_archiver.saved_scraper.chdir')
    mock_setup_session.return_value = mocker.MagicMock(headers=mocker.MagicMock(),
                                                       cookies=mocker.MagicMock())
    scraper = SavedScraper()
    scraper.session = mocker.MagicMock()
    scraper.session.get = AsyncMock()  # type: ignore[method-assign]
    scraper.session.post = AsyncMock()  # type: ignore[method-assign]
    mocker.patch.object(scraper,
                        'get_json',
                        new_callable=AsyncMock,
                        return_value={
                            'items': [{
                                'media': {
                                    'id': '12345',
                                    'code': '12345',
                                    'owner': {
                                        'id': '67890',
                                        'username': 'username'
                                    },
                                    'pk': 'pk',
                                    'video_dash_manifest': None
                                }
                            }]
                        })
    mock_unsave = mocker.patch.object(scraper, 'unsave', new_callable=AsyncMock)
    mock_dispatch = mocker.patch.object(scraper, 'dispatch_edges', new_callable=AsyncMock)
    await scraper.process(mocker.MagicMock(), unsave=True)
    mock_dispatch.assert_awaited_once()
    mock_unsave.assert_awaited_once()


async def test_process_saved(mocker: MockerFixture, mock_setup_session: AsyncMock) -> None:
    mock_log_warning = mocker.patch('instagram_archiver.saved_scraper.log.warning')
    mocker.patch('instagram_archiver.saved_scraper.Path')
    mocker.patch('instagram_archiver.saved_scraper.chdir')
    scraper = SavedScraper()
    scraper.session = mocker.MagicMock()
    scraper.session.get = AsyncMock()  # type: ignore[method-assign]
    scraper.session.post = AsyncMock()  # type: ignore[method-assign]
    mocker.patch.object(scraper,
                        'get_json',
                        new_callable=AsyncMock,
                        return_value={
                            'items': [{
                                'media': {
                                    'id': '12345',
                                    'code': '12345',
                                    'owner': {
                                        'id': '67890',
                                        'username': 'username'
                                    },
                                    'pk': 'pk',
                                    'video_dash_manifest': None
                                }
                            }],
                            'more_available': True
                        })
    mock_unsave = mocker.patch.object(scraper, 'unsave', new_callable=AsyncMock)
    mocker.patch.object(scraper, 'dispatch_edges', new_callable=AsyncMock)
    await scraper.process(mocker.MagicMock())
    mock_unsave.assert_not_called()
    mock_log_warning.assert_called_once_with('Unhandled pagination.')


async def test_saved_unsave_iterates(mocker: MockerFixture, mock_setup_session: AsyncMock) -> None:
    mocker.patch('instagram_archiver.saved_scraper.Path')
    scraper = SavedScraper()
    scraper.session = mocker.MagicMock()
    scraper.session.post = AsyncMock()  # type: ignore[method-assign]
    await scraper.unsave(['a', 'b'])
    assert scraper.session.post.await_count == 2


async def test_saved_worker_abort(mocker: MockerFixture, mock_setup_session: AsyncMock) -> None:
    mocker.patch('instagram_archiver.saved_scraper.Path')
    mocker.patch('instagram_archiver.saved_scraper.chdir')
    scraper = SavedScraper()
    scraper.session = mocker.MagicMock()
    scraper.session.get = AsyncMock()  # type: ignore[method-assign]
    scraper.session.post = AsyncMock()  # type: ignore[method-assign]
    mocker.patch.object(scraper, 'get_json', new_callable=AsyncMock, side_effect=WorkerAbort())
    await scraper.process(mocker.MagicMock())


async def test_saved_producer_exception_propagates(mocker: MockerFixture,
                                                   mock_setup_session: AsyncMock) -> None:
    mocker.patch('instagram_archiver.saved_scraper.Path')
    mocker.patch('instagram_archiver.saved_scraper.chdir')
    scraper = SavedScraper()
    scraper.session = mocker.MagicMock()
    scraper.session.get = AsyncMock()  # type: ignore[method-assign]
    scraper.session.post = AsyncMock()  # type: ignore[method-assign]
    mocker.patch.object(scraper,
                        'get_json',
                        new_callable=AsyncMock,
                        side_effect=RuntimeError('boom'))
    with pytest.raises(RuntimeError, match='boom'):
        await scraper.process(mocker.MagicMock())
