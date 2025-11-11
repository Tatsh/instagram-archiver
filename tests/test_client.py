from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

from instagram_archiver.client import CSRFTokenNotFound, InstagramClient, UnexpectedRedirect
from instagram_archiver.typing import Comments, HighlightsTray
from requests import HTTPError
import pytest
import requests

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def client(mocker: MockerFixture) -> InstagramClient:
    mocker.patch('instagram_archiver.client.setup_session')
    return InstagramClient()


def test_add_video_url(client: InstagramClient) -> None:
    client.add_video_url('https://example.com/video')
    assert 'https://example.com/video' in client.video_urls


def test_add_csrf_token_header_success(client: MagicMock) -> None:
    client.session.cookies.get.return_value = 'test_csrf_token'
    client.add_csrf_token_header()
    client.session.headers.update.assert_called_once_with({'x-csrftoken': 'test_csrf_token'})


def test_add_csrf_token_header_failure(client: MagicMock) -> None:
    client.session.cookies.get.return_value = None
    with pytest.raises(CSRFTokenNotFound):
        client.add_csrf_token_header()


def test_graphql_query_success(client: MagicMock, mocker: MockerFixture) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'status': 'ok', 'data': {'key': 'value'}}
    client.session.post.return_value.__enter__.return_value = mock_response

    result = client.graphql_query({'key': 'value'}, cast_to=dict)
    assert result == {'key': 'value'}


def test_graphql_query_failure(client: MagicMock, mocker: MockerFixture) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 400
    client.session.post.return_value.__enter__.return_value = mock_response

    result = client.graphql_query({'key': 'value'}, cast_to=dict)
    assert result is None


def test_get_text(client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.text = 'response text'
    client.session.get.return_value.__enter__.return_value = mock_response

    result = client.get_text('https://example.com')
    assert result == 'response text'


def test_highlights_tray(client: MagicMock, mocker: MockerFixture) -> None:
    mock_get_json = mocker.patch.object(client, 'get_json', return_value={'tray': []})
    result = client.highlights_tray(12345)
    assert result == {'tray': []}
    mock_get_json.assert_called_once_with(
        'https://i.instagram.com/api/v1/highlights/12345/highlights_tray/', cast_to=HighlightsTray
    )


def test_save_image_versions2(client: MagicMock, mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=False)
    mock_get_extension = mocker.patch('instagram_archiver.client.get_extension', return_value='jpg')
    mocker.patch('instagram_archiver.client.Path')
    mocker.patch('instagram_archiver.client.write_if_new')
    mock_utime = mocker.patch('instagram_archiver.client.utime')
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {'content-type': 'image/jpeg'}
    client.session.head.return_value = mock_response
    client.session.get.return_value.iter_content.return_value = [b'data']

    sub_item = {
        'id': '123',
        'image_versions2': {
            'candidates': [{'url': 'https://example.com/image', 'width': 100, 'height': 100}]
        },
    }
    client.save_image_versions2(sub_item, 1234567890)

    mock_is_saved.assert_called_once_with('https://example.com/image')
    mock_get_extension.assert_called_once_with('image/jpeg')
    mock_utime.assert_called_once_with('123.jpg', (1234567890, 1234567890))


def test_save_comments(client: MagicMock, mocker: MockerFixture) -> None:
    mock_get_json = mocker.patch.object(
        client,
        'get_json',
        side_effect=[
            {
                'comments': [{'text': 'comment1'}],
                'can_view_more_preview_comments': True,
                'next_min_id': '123',
            },
            {
                'comments': [{'text': 'comment2'}],
                'can_view_more_preview_comments': False,
                'next_min_id': None,
            },
        ],
    )
    mock_path = mocker.patch('instagram_archiver.client.Path')
    mocker.patch('instagram_archiver.client.json.dump')

    edge = {'node': {'id': '123'}}
    client.save_comments(edge)

    mock_get_json.assert_called()
    mock_path.return_value.open.assert_called_once_with('w+', encoding='utf-8')


def test_graphql_query_error_status(client: MagicMock, mocker: MockerFixture) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'status': 'error', 'errors': ['Some error']}
    client.session.post.return_value.__enter__.return_value = mock_response

    result = client.graphql_query({'key': 'value'}, cast_to=dict)
    assert result is None


def test_graphql_query_error_status_ok(client: MagicMock, mocker: MockerFixture) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'status': 'ok',
        'errors': ['Some error'],
        'data': {'key': 'value'},
    }
    client.session.post.return_value.__enter__.return_value = mock_response

    result = client.graphql_query({'key': 'value'}, cast_to=dict)
    assert result == {'key': 'value'}


def test_graphql_query_no_data(client: MagicMock, mocker: MockerFixture) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'status': 'ok', 'data': None}
    client.session.post.return_value.__enter__.return_value = mock_response

    result = client.graphql_query({'key': 'value'}, cast_to=dict)
    assert result is None


def test_graphql_query_http_error(client: MagicMock, mocker: MockerFixture) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 500
    client.session.post.return_value.__enter__.return_value = mock_response

    result = client.graphql_query({'key': 'value'}, cast_to=dict)
    assert result is None


def test_save_image_versions2_already_saved(client: MagicMock, mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=True)
    sub_item = {
        'id': '123',
        'image_versions2': {
            'candidates': [{'url': 'https://example.com/image', 'width': 100, 'height': 100}]
        },
    }
    client.save_image_versions2(sub_item, 1234567890)

    mock_is_saved.assert_called_once_with('https://example.com/image')
    client.session.head.assert_not_called()


def test_save_image_versions2_head_request_failure(
    client: MagicMock, mocker: MockerFixture
) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=False)
    mock_response = MagicMock()
    mock_response.status_code = 404
    client.session.head.return_value = mock_response

    sub_item = {
        'id': '123',
        'image_versions2': {
            'candidates': [{'url': 'https://example.com/image', 'width': 100, 'height': 100}]
        },
    }
    client.save_image_versions2(sub_item, 1234567890)

    mock_is_saved.assert_called_once_with('https://example.com/image')
    client.session.head.assert_called_once_with('https://example.com/image')
    client.session.get.assert_not_called()


def test_save_comments_http_error(client: MagicMock, mocker: MockerFixture) -> None:
    mock_get_json = mocker.patch.object(client, 'get_json', side_effect=HTTPError)
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')

    edge = {'node': {'id': '123'}}
    client.save_comments(edge)

    mock_get_json.assert_called_once_with(
        'https://www.instagram.com/api/v1/media/123/comments/',
        params={'can_support_threading': 'true', 'permalink_enabled': 'false'},
        cast_to=Comments,
    )
    mock_log_exception.assert_called_once_with('Failed to get comments.')


def test_save_comments_http_error_page_2(client: MagicMock, mocker: MockerFixture) -> None:
    mock_get_json = mocker.patch.object(
        client,
        'get_json',
        side_effect=[{'can_view_more_preview_comments': True, 'next_min_id': 'min'}, HTTPError],
    )
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')
    mocker.patch('instagram_archiver.client.Path')
    mocker.patch('instagram_archiver.client.json.dump')

    edge = {'node': {'id': '123'}}
    client.save_comments(edge)

    mock_get_json.assert_called_with(
        'https://www.instagram.com/api/v1/media/123/comments/',
        params={'can_support_threading': 'true', 'min_id': 'min'},
        cast_to=Comments,
    )
    mock_log_exception.assert_called_once_with('Failed to get comments.')


def test_save_media_already_saved(client: MagicMock, mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=True)
    edge = {'node': {'code': 'test_code', 'pk': 'pk'}}
    client.save_media(edge)
    mock_is_saved.assert_called_once_with('https://www.instagram.com/api/v1/media/pk/info/')
    client.session.get.assert_not_called()


def test_save_media_get_request_failure(client: MagicMock, mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=False)
    mock_response = MagicMock()
    mock_response.status_code = 404
    client.session.get.return_value = mock_response
    mock_log_warning = mocker.patch('instagram_archiver.client.log.warning')

    edge = {'node': {'code': 'test_code', 'pk': 'pk'}}
    client.save_media(edge)

    mock_is_saved.assert_called_once_with('https://www.instagram.com/api/v1/media/pk/info/')
    client.session.get.assert_called_once_with(
        'https://www.instagram.com/api/v1/media/pk/info/', headers=mocker.ANY, allow_redirects=False
    )
    mock_log_warning.assert_called_once_with('GET request failed with status code %s.', 404)


def test_save_media_redirect_error(client: MagicMock, mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=False)
    mock_response = MagicMock()
    mock_response.status_code = 301
    client.session.get.return_value = mock_response

    edge = {'node': {'code': 'test_code', 'pk': 'pk'}}
    with pytest.raises(UnexpectedRedirect):
        client.save_media(edge)

    mock_is_saved.assert_called_once_with('https://www.instagram.com/api/v1/media/pk/info/')
    client.session.get.assert_called_once_with(
        'https://www.instagram.com/api/v1/media/pk/info/', headers=mocker.ANY, allow_redirects=False
    )


def test_save_media_invalid_response(client: MagicMock, mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=False)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = 'invalid response'
    client.session.get.return_value = mock_response
    mock_log_warning = mocker.patch('instagram_archiver.client.log.warning')

    edge = {'node': {'code': 'test_code', 'pk': 'pk'}}
    client.save_media(edge)

    mock_is_saved.assert_called_once_with('https://www.instagram.com/api/v1/media/pk/info/')
    client.session.get.assert_called_once_with(
        'https://www.instagram.com/api/v1/media/pk/info/', headers=mocker.ANY, allow_redirects=False
    )
    mock_log_warning.assert_called_once_with('Invalid response. image_versions2 dict not found.')


def test_save_media_success(client: MagicMock, mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=False)
    mock_write_if_new = mocker.patch('instagram_archiver.client.write_if_new')
    mock_utime = mocker.patch('instagram_archiver.client.utime')
    mocker.patch.object(client, 'save_image_versions2')
    mock_save_to_log = mocker.patch.object(client, 'save_to_log')
    mock_response = MagicMock(
        json=MagicMock(
            return_value={
                'items': [
                    {'taken_at': 1234567890, 'carousel_media': [{}]},
                    {'taken_at': 1234567890, 'image_versions2': {}},
                    {'taken_at': 1234567890},
                ]
            }
        )
    )
    mock_response.status_code = 200
    mock_response.text = '{"image_versions2": {}, "taken_at": 1234567890}'
    client.session.get.return_value = mock_response
    edge = {'node': {'code': 'test_code', 'id': '123', 'pk': 'pk'}}
    client.save_media(edge)
    client.session.get.assert_called_once_with(
        'https://www.instagram.com/api/v1/media/pk/info/', headers=mocker.ANY, allow_redirects=False
    )
    mock_is_saved.assert_called_once_with('https://www.instagram.com/api/v1/media/pk/info/')
    mock_write_if_new.assert_any_call('123.json', mocker.ANY)
    mock_write_if_new.assert_any_call('123-media-info-0000.json', mocker.ANY)
    mock_utime.assert_any_call('123.json', (1234567890, 1234567890))
    mock_utime.assert_any_call('123-media-info-0000.json', (1234567890, 1234567890))
    mock_save_to_log.assert_called_once_with('https://www.instagram.com/api/v1/media/pk/info/')


def test_save_edges_typename_xdtmediadict_video(client: MagicMock, mocker: MockerFixture) -> None:
    mock_add_video_url = mocker.patch.object(client, 'add_video_url')
    edge = {
        'node': {'__typename': 'XDTMediaDict', 'code': 'test_code', 'video_dash_manifest': True}
    }
    client.save_edges([edge])
    mock_add_video_url.assert_called_once_with('https://www.instagram.com/p/test_code/')


def test_save_edges_typename_xdtmediadict_media(client: MagicMock, mocker: MockerFixture) -> None:
    mock_save_comments = mocker.patch.object(client, 'save_comments')
    mock_save_media = mocker.patch.object(client, 'save_media')
    edge = {'node': {'__typename': 'XDTMediaDict', 'code': 'test_code'}}
    client.save_edges([edge])
    mock_save_comments.assert_called_once_with(edge)
    mock_save_media.assert_called_once_with(edge)


def test_save_edges_typename_xdtmediadict_retry_error(
    client: MagicMock, mocker: MockerFixture
) -> None:
    mock_save_comments = mocker.patch.object(
        client, 'save_comments', side_effect=requests.exceptions.RetryError
    )
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')
    edge = {'node': {'__typename': 'XDTMediaDict', 'code': 'test_code'}}
    client.save_edges([edge])
    mock_save_comments.assert_called_once_with(edge)
    mock_log_exception.assert_called_once_with('Retries exhausted.')


def test_save_edges_unknown_typename(client: MagicMock, mocker: MockerFixture) -> None:
    mock_log_warning = mocker.patch('instagram_archiver.client.log.warning')
    mock_failed_urls = mocker.patch.object(client, 'failed_urls')
    edge = {'node': {'__typename': 'UnknownType', 'id': '123', 'code': 'test_code'}}
    client.save_edges([edge])
    mock_log_warning.assert_called_once_with(
        'Unknown type: `%s`. Item %s will not be processed.', 'UnknownType', '123'
    )
    mock_failed_urls.add.assert_called_once_with('https://www.instagram.com/p/test_code/')


def test_save_edges_parent_edge(client: MagicMock, mocker: MockerFixture) -> None:
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')
    mocker.patch.object(client, 'save_media')
    mocker.patch.object(client, 'save_comments')
    parent_edge = {'node': {'code': 'parent_code', 'id': 'some_id'}}
    edge = {'node': {'__typename': 'XDTMediaDict', 'id': 'other_id'}}
    client.save_edges([edge], parent_edge=parent_edge)
    mock_log_exception.assert_not_called()


def test_save_edges_parent_edge_missing_code(client: MagicMock, mocker: MockerFixture) -> None:
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')
    parent_edge: dict[str, Any] = {'node': {}}
    edge = {'node': {'__typename': 'XDTMediaDict'}}
    client.save_edges([edge], parent_edge=parent_edge)
    mock_log_exception.assert_called_once_with('Unknown shortcode.')


def test_save_edges_missing_code_no_parent(client: MagicMock, mocker: MockerFixture) -> None:
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')
    mocker.patch.object(client, 'save_media')
    mocker.patch.object(client, 'save_comments')
    edge = {'node': {'__typename': 'XDTMediaDict'}}
    client.save_edges([edge])
    mock_log_exception.assert_called_once_with('Unknown shortcode.')


def test_get_json_success(client: MagicMock, mocker: MockerFixture) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'key': 'value'}
    client.session.get.return_value.__enter__.return_value = mock_response
    result = client.get_json('https://example.com', cast_to=dict)
    assert result == {'key': 'value'}
    client.session.get.assert_called_once_with(
        'https://example.com', params=None, headers=mocker.ANY
    )


def test_get_json_with_params(client: MagicMock, mocker: MockerFixture) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'key': 'value'}
    client.session.get.return_value.__enter__.return_value = mock_response
    params = {'param1': 'value1'}
    result = client.get_json('https://example.com', cast_to=dict, params=params)
    assert result == {'key': 'value'}
    client.session.get.assert_called_once_with(
        'https://example.com', params=params, headers=mocker.ANY
    )
