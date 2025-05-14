from __future__ import annotations

from typing import TYPE_CHECKING, Any

from instagram_archiver.profile_scraper import ProfileScraper
from instagram_archiver.saved_scraper import SavedScraper
from requests import HTTPError

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_profile_scraper_no_log(mocker: MockerFixture, mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mocker.patch('instagram_archiver.profile_scraper.Path')
    scraper_with_no_logging: Any = ProfileScraper('test_user', disable_log=True)
    scraper_with_no_logging._cursor.execute.assert_not_called()  # noqa: SLF001


def test_profile_scraper_with_empty_log(mocker: MockerFixture, mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_path.return_value.stat.return_value.st_size = 0
    scraper: Any = ProfileScraper('test_user')
    scraper._cursor.execute.assert_called_once()  # noqa: SLF001


def test_profile_scraper_with_no_log(mocker: MockerFixture, mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = False
    scraper: Any = ProfileScraper('test_user')
    scraper._cursor.execute.assert_called_once()  # noqa: SLF001


def test_profile_scraper_with_log_existing(mocker: MockerFixture, mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_path.return_value.stat.return_value.st_size = 1
    scraper: Any = ProfileScraper('test_user')
    scraper._cursor.execute.assert_not_called()  # noqa: SLF001


def test_save_comments_does_nothing_when_disabled(mocker: MockerFixture,
                                                  mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_cursor = mocker.MagicMock()
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    mock_save_comments = mocker.patch(
        'instagram_archiver.profile_scraper.InstagramClient.save_comments')

    scraper = ProfileScraper('test_user')
    scraper.save_comments({
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
    mock_save_comments.assert_not_called()


def test_save_comments(mocker: MockerFixture, mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_cursor = mocker.MagicMock()
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    mock_save_comments = mocker.patch(
        'instagram_archiver.profile_scraper.InstagramClient.save_comments')

    scraper = ProfileScraper('test_user', comments=True)
    scraper.save_comments({
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
    mock_save_comments.assert_called_once()


def test_save_to_log_disabled(mocker: MockerFixture, mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_cursor = mocker.MagicMock()
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    scraper = ProfileScraper('test_user', disable_log=True)
    scraper.save_to_log('test_url')
    mock_cursor.execute.assert_not_called()


def test_save_to_log(mocker: MockerFixture, mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_cursor = mocker.MagicMock()
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    scraper = ProfileScraper('test_user')
    scraper.save_to_log('test_url')
    mock_cursor.execute.assert_called_once()


def test_is_saved(mocker: MockerFixture, mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_cursor = mocker.MagicMock()
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (1,)
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    scraper = ProfileScraper('test_user')
    assert scraper.is_saved('test_url') is True
    mock_cursor.execute.assert_called_once()


def test_is_saved_log_disabled(mocker: MockerFixture, mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_cursor = mocker.MagicMock()
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    scraper = ProfileScraper('test_user', disable_log=True)
    scraper.is_saved('test_url')
    mock_cursor.execute.assert_not_called()


def test_exit_cleans_up(mocker: MockerFixture, mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_cursor = mocker.MagicMock()
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    with ProfileScraper('test_user'):
        pass
    mock_cursor.close.assert_called_once()
    mock_connection.close.assert_called_once()


def test_process(mocker: MockerFixture, mock_setup_session: None) -> None:
    mock_log_error = mocker.patch('instagram_archiver.profile_scraper.log.error')
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mocker.patch('instagram_archiver.profile_scraper.chdir')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_json',
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
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_text')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.highlights_tray',
                 return_value={'tray': []})
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchone.return_value = (0,)
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    scraper = ProfileScraper('test_user')
    scraper.session = mocker.MagicMock()
    scraper.process()
    mock_log_error.assert_called_once_with('First GraphQL query failed.')


def test_process_data_not_in_profile_info(mocker: MockerFixture, mock_setup_session: None) -> None:
    mock_log_error = mocker.patch('instagram_archiver.profile_scraper.log.error')
    mock_log_warning = mocker.patch('instagram_archiver.profile_scraper.log.warning')
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mocker.patch('instagram_archiver.profile_scraper.chdir')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_json', return_value={})
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_text')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.highlights_tray',
                 return_value={'tray': []})
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchone.return_value = (0,)
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    scraper = ProfileScraper('test_user')
    scraper.session = mocker.MagicMock()
    scraper.process()
    mock_log_error.assert_called_once_with('First GraphQL query failed.')
    mock_log_warning.assert_called_once_with(
        'Failed to get user info. Profile information and image will not be saved.')


def test_process_already_saved_profile_pic(mocker: MockerFixture, mock_setup_session: None) -> None:
    mock_log_error = mocker.patch('instagram_archiver.profile_scraper.log.error')
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mocker.patch('instagram_archiver.profile_scraper.chdir')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_json',
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
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_text')
    mock_save_to_log = mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.save_to_log')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.is_saved', return_value=True)
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.highlights_tray',
                 return_value={'tray': []})
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchone.return_value = (0,)
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    scraper = ProfileScraper('test_user')
    scraper.session = mocker.MagicMock()
    scraper.process()
    mock_save_to_log.assert_not_called()
    mock_log_error.assert_called_once_with('First GraphQL query failed.')


def test_process_highlights(mocker: MockerFixture, mock_setup_session: None) -> None:
    mock_log_error = mocker.patch('instagram_archiver.profile_scraper.log.error')
    mock_add_video_url = mocker.patch(
        'instagram_archiver.profile_scraper.ProfileScraper.add_video_url')
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mocker.patch('instagram_archiver.profile_scraper.chdir')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_json',
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
    mock_yt_dlp = mocker.patch('instagram_archiver.profile_scraper.get_configured_yt_dlp'
                               ).return_value.__enter__.return_value
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_text')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.highlights_tray',
                 return_value={'tray': [{
                     'id': 'f:12345'
                 }]})
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchone.return_value = (0,)
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    scraper = ProfileScraper('test_user')
    scraper.session = mocker.MagicMock()
    scraper.video_urls = ['https://www.instagram.com/stories/highlights/12345/']
    scraper.process()
    mock_log_error.assert_called_once_with('First GraphQL query failed.')
    mock_add_video_url.assert_called_once_with(
        'https://www.instagram.com/stories/highlights/12345/')
    mock_yt_dlp.extract_info.assert_called_once_with(
        'https://www.instagram.com/stories/highlights/12345/')


def test_process_highlights_error(mocker: MockerFixture, mock_setup_session: None) -> None:
    mock_log_exception = mocker.patch('instagram_archiver.profile_scraper.log.exception')
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mocker.patch('instagram_archiver.profile_scraper.chdir')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_json',
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
    mocker.patch('instagram_archiver.profile_scraper.get_configured_yt_dlp')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_text')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.highlights_tray',
                 side_effect=HTTPError)
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchone.return_value = (0,)
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    scraper = ProfileScraper('test_user')
    scraper.session = mocker.MagicMock()
    scraper.video_urls = ['https://www.instagram.com/stories/highlights/12345/']
    scraper.process()
    mock_log_exception.assert_called_once_with('Failed to get highlights data.')


def test_process_edges(mocker: MockerFixture, mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.profile_scraper.log.error')
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mocker.patch('instagram_archiver.profile_scraper.chdir')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_json',
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
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_text')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.highlights_tray',
                 return_value={'tray': []})
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchone.return_value = (0,)
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    scraper = ProfileScraper('test_user')
    scraper.session = mocker.MagicMock()
    mock_save_edges = mocker.patch.object(scraper, 'save_edges')
    mock_graphql_query = mocker.patch.object(
        scraper,
        'graphql_query',
        side_effect=[{
            'xdt_api__v1__feed__user_timeline_graphql_connection': {
                'edges': [],
                'page_info': {
                    'has_next_page': False,
                    'end_cursor': None
                }
            }
        }])
    scraper.process()
    assert mock_save_edges.call_count == 2
    assert mock_graphql_query.call_count == 1


def test_process_edges_and_pagination(mocker: MockerFixture, mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.profile_scraper.log.error')
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mocker.patch('instagram_archiver.profile_scraper.chdir')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_json',
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
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_text')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.highlights_tray',
                 return_value={'tray': []})
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_path.return_value.exists.return_value = True
    mock_cursor = mocker.MagicMock()
    mock_cursor.fetchone.return_value = (0,)
    mock_connection = mocker.MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mocker.patch('instagram_archiver.profile_scraper.sqlite3.connect', return_value=mock_connection)
    scraper = ProfileScraper('test_user')
    scraper.session = mocker.MagicMock()
    mock_save_edges = mocker.patch.object(scraper, 'save_edges')
    mock_graphql_query = mocker.patch.object(
        scraper,
        'graphql_query',
        side_effect=[{
            'xdt_api__v1__feed__user_timeline_graphql_connection': {
                'edges': [],
                'page_info': {
                    'has_next_page': True,
                    'end_cursor': None
                }
            }
        }, {
            'xdt_api__v1__feed__user_timeline_graphql_connection': {
                'edges': [],
                'page_info': {
                    'has_next_page': True,
                    'end_cursor': None
                }
            }
        }, {}])
    scraper.process()
    assert mock_save_edges.call_count == 3
    assert mock_graphql_query.call_count == 3


def test_process_video_urls(mocker: MockerFixture, mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.profile_scraper.log.error')
    mocker.patch('instagram_archiver.profile_scraper.sqlite3')
    mocker.patch('instagram_archiver.profile_scraper.chdir')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_json',
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
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.get_text')
    mocker.patch('instagram_archiver.profile_scraper.ProfileScraper.highlights_tray',
                 return_value={'tray': [{
                     'id': 'f:12345'
                 }, {
                     'id': 'f:67890'
                 }, {
                     'id': 'f:54321'
                 }]})
    mock_path = mocker.patch('instagram_archiver.profile_scraper.Path')
    mock_yt_dlp = mocker.patch('instagram_archiver.profile_scraper.get_configured_yt_dlp'
                               ).return_value.__enter__.return_value
    mock_yt_dlp.extract_info.side_effect = [True, False, True]
    mock_path.return_value.exists.return_value = True
    scraper = ProfileScraper('test_user')
    scraper.session = mocker.MagicMock()
    mocker.patch.object(scraper, 'is_saved', side_effect=[False, True, False, False])
    mocker.patch.object(scraper, 'save_to_log')
    mock_save_edges = mocker.patch.object(scraper, 'save_edges')
    mock_graphql_query = mocker.patch.object(scraper, 'graphql_query', return_value={})
    scraper.process()
    assert mock_save_edges.call_count == 1
    assert mock_graphql_query.call_count == 1
    assert scraper.failed_urls
    mock_path.assert_called_with('failed.txt')


def test_process_saved_with_unsaving(mocker: MockerFixture, mock_setup_session: None) -> None:
    mocker.patch('instagram_archiver.saved_scraper.Path')
    mocker.patch('instagram_archiver.saved_scraper.chdir')
    scraper = SavedScraper()
    mocker.patch.object(scraper, 'session')
    mocker.patch.object(scraper,
                        'get_json',
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
    mock_save_edges = mocker.patch.object(scraper, 'save_edges')
    scraper.process(unsave=True)
    assert list(mock_save_edges.call_args_list[0].args[0]) == [{
        'node': {
            '__typename': 'XDTMediaDict',
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


def test_process_saved(mocker: MockerFixture, mock_setup_session: None) -> None:
    mock_log_warning = mocker.patch('instagram_archiver.saved_scraper.log.warning')
    mocker.patch('instagram_archiver.saved_scraper.Path')
    mocker.patch('instagram_archiver.saved_scraper.chdir')
    scraper = SavedScraper()
    mocker.patch.object(scraper, 'session')
    mocker.patch.object(scraper,
                        'get_json',
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
    mock_save_edges = mocker.patch.object(scraper, 'save_edges')
    mock_unsave = mocker.patch.object(scraper, 'unsave')
    scraper.process()
    assert list(mock_save_edges.call_args_list[0].args[0]) == [{
        'node': {
            '__typename': 'XDTMediaDict',
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
    mock_unsave.assert_not_called()
    mock_log_warning.assert_called_once_with('Unhandled pagination.')
