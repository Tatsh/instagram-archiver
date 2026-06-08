from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, MagicMock
import asyncio

from instagram_archiver.client import CSRFTokenNotFound, InstagramClient, UnexpectedRedirect
from instagram_archiver.typing import POSTS_HANDLED, Comments, HighlightsTray, Stats, YTDLPState
from niquests.exceptions import HTTPError, RetryError
import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def client(mocker: MockerFixture) -> InstagramClient:
    mocker.patch('instagram_archiver.client.setup_session', new_callable=AsyncMock)
    instance = InstagramClient()
    instance.session = mocker.MagicMock()
    instance.session.post = AsyncMock()  # type: ignore[method-assign]
    instance.session.get = AsyncMock()  # type: ignore[method-assign]
    instance.session.head = AsyncMock()  # type: ignore[method-assign]
    instance.session.close = AsyncMock()  # type: ignore[method-assign]
    return instance


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


async def test_graphql_query_success(client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'status': 'ok', 'data': {'key': 'value'}}
    client.session.post.return_value = mock_response

    result = await client.graphql_query({'key': 'value'}, cast_to=dict)
    assert result == {'key': 'value'}


async def test_graphql_query_failure(client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 400
    client.session.post.return_value = mock_response

    result = await client.graphql_query({'key': 'value'}, cast_to=dict)
    assert result is None


async def test_get_text(client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.text = 'response text'
    client.session.get.return_value = mock_response

    result = await client.get_text('https://example.com')
    assert result == 'response text'


async def test_get_text_none_body(client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.text = None
    client.session.get.return_value = mock_response

    result = await client.get_text('https://example.com')
    assert not result


async def test_highlights_tray(client: MagicMock, mocker: MockerFixture) -> None:
    mock_get_json = mocker.patch.object(client,
                                        'get_json',
                                        new_callable=AsyncMock,
                                        return_value={'tray': []})
    result = await client.highlights_tray(12345)
    assert result == {'tray': []}
    mock_get_json.assert_awaited_once_with(
        'https://i.instagram.com/api/v1/highlights/12345/highlights_tray/', cast_to=HighlightsTray)


async def test_save_image_versions2(client: MagicMock, mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=False)
    mock_get_extension = mocker.patch('instagram_archiver.client.get_extension', return_value='jpg')
    mock_write_bytes = mocker.patch('instagram_archiver.client.write_bytes')
    mock_utime = mocker.patch('instagram_archiver.client.utime')
    head_response = MagicMock(status_code=200,
                              headers={'content-type': 'image/jpeg'},
                              url='https://example.com/image')
    client.session.head.return_value = head_response
    body_response = MagicMock(content=b'data')
    client.session.get.return_value = body_response

    sub_item = {
        'id': '123',
        'image_versions2': {
            'candidates': [{
                'url': 'https://example.com/image',
                'width': 100,
                'height': 100
            }]
        }
    }
    await client.save_image_versions2(sub_item, 1234567890)

    mock_is_saved.assert_called_once_with('https://example.com/image')
    mock_get_extension.assert_called_once_with('image/jpeg')
    mock_write_bytes.assert_called_once_with('123.jpg', b'data')
    mock_utime.assert_called_once_with('123.jpg', (1234567890, 1234567890))


async def test_save_image_versions2_content_type_bytes(client: MagicMock,
                                                       mocker: MockerFixture) -> None:
    mocker.patch.object(client, 'is_saved', return_value=False)
    mock_get_extension = mocker.patch('instagram_archiver.client.get_extension', return_value='jpg')
    mocker.patch('instagram_archiver.client.write_bytes')
    mocker.patch('instagram_archiver.client.utime')
    head_response = MagicMock(status_code=200,
                              headers={'content-type': b'image/jpeg'},
                              url='https://example.com/image')
    client.session.head.return_value = head_response
    client.session.get.return_value = MagicMock(content=b'data')

    sub_item = {
        'id': '321',
        'image_versions2': {
            'candidates': [{
                'url': 'https://example.com/image',
                'width': 100,
                'height': 100
            }]
        }
    }
    await client.save_image_versions2(sub_item, 1234567890)
    mock_get_extension.assert_called_once_with('image/jpeg')


async def test_save_image_versions2_no_content(client: MagicMock, mocker: MockerFixture) -> None:
    mocker.patch.object(client, 'is_saved', return_value=False)
    mocker.patch('instagram_archiver.client.get_extension', return_value='jpg')
    mock_write_bytes = mocker.patch('instagram_archiver.client.write_bytes')
    mocker.patch('instagram_archiver.client.utime')
    client.session.head.return_value = MagicMock(status_code=200,
                                                 headers={'content-type': 'image/jpeg'},
                                                 url='https://example.com/image')
    client.session.get.return_value = MagicMock(content=None)

    sub_item = {
        'id': '999',
        'image_versions2': {
            'candidates': [{
                'url': 'https://example.com/image',
                'width': 100,
                'height': 100
            }]
        }
    }
    await client.save_image_versions2(sub_item, 1234567890)
    mock_write_bytes.assert_not_called()


async def test_save_image_versions2_no_url(client: MagicMock, mocker: MockerFixture) -> None:
    mocker.patch.object(client, 'is_saved', return_value=False)
    mocker.patch('instagram_archiver.client.get_extension', return_value='jpg')
    mocker.patch('instagram_archiver.client.write_bytes')
    mocker.patch('instagram_archiver.client.utime')
    mock_save_to_log = mocker.patch.object(client, 'save_to_log')
    client.session.head.return_value = MagicMock(status_code=200,
                                                 headers={'content-type': 'image/jpeg'},
                                                 url=None)
    client.session.get.return_value = MagicMock(content=b'data')

    sub_item = {
        'id': '888',
        'image_versions2': {
            'candidates': [{
                'url': 'https://example.com/image',
                'width': 100,
                'height': 100
            }]
        }
    }
    await client.save_image_versions2(sub_item, 1234567890)
    mock_save_to_log.assert_not_called()


async def test_save_comments(client: MagicMock, mocker: MockerFixture) -> None:
    mock_get_json = mocker.patch.object(client,
                                        'get_json',
                                        new_callable=AsyncMock,
                                        side_effect=[{
                                            'comments': [{
                                                'text': 'comment1'
                                            }],
                                            'can_view_more_preview_comments': True,
                                            'next_min_id': '123'
                                        }, {
                                            'comments': [{
                                                'text': 'comment2'
                                            }],
                                            'can_view_more_preview_comments': False,
                                            'next_min_id': None
                                        }])
    mock_dump_json = mocker.patch('instagram_archiver.client.dump_json')

    edge = {'node': {'id': '123', 'pk': '123'}}
    await client.save_comments(edge)

    mock_get_json.assert_awaited()
    mock_dump_json.assert_called_once_with('123-comments.json', mocker.ANY, mode='w+')


async def test_graphql_query_error_status(client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'status': 'error', 'errors': ['Some error']}
    client.session.post.return_value = mock_response

    result = await client.graphql_query({'key': 'value'}, cast_to=dict)
    assert result is None


async def test_graphql_query_error_status_ok(client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'status': 'ok',
        'errors': ['Some error'],
        'data': {
            'key': 'value'
        }
    }
    client.session.post.return_value = mock_response

    result = await client.graphql_query({'key': 'value'}, cast_to=dict)
    assert result == {'key': 'value'}


async def test_graphql_query_no_data(client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'status': 'ok', 'data': None}
    client.session.post.return_value = mock_response

    result = await client.graphql_query({'key': 'value'}, cast_to=dict)
    assert result is None


async def test_graphql_query_http_error(client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 500
    client.session.post.return_value = mock_response

    result = await client.graphql_query({'key': 'value'}, cast_to=dict)
    assert result is None


async def test_graphql_query_json_not_object(client: MagicMock, mocker: MockerFixture) -> None:
    mock_log_error = mocker.patch('instagram_archiver.client.log.error')
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    client.session.post.return_value = mock_response

    result = await client.graphql_query({'key': 'value'}, cast_to=dict)
    assert result is None
    mock_log_error.assert_called_once_with('GraphQL response was not a JSON object.')


async def test_save_image_versions2_already_saved(client: MagicMock, mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=True)
    sub_item = {
        'id': '123',
        'image_versions2': {
            'candidates': [{
                'url': 'https://example.com/image',
                'width': 100,
                'height': 100
            }]
        }
    }
    await client.save_image_versions2(sub_item, 1234567890)

    mock_is_saved.assert_called_once_with('https://example.com/image')
    client.session.head.assert_not_called()


async def test_save_image_versions2_head_request_failure(client: MagicMock,
                                                         mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=False)
    head_response = MagicMock(status_code=404)
    client.session.head.return_value = head_response

    sub_item = {
        'id': '123',
        'image_versions2': {
            'candidates': [{
                'url': 'https://example.com/image',
                'width': 100,
                'height': 100
            }]
        }
    }
    await client.save_image_versions2(sub_item, 1234567890)

    mock_is_saved.assert_called_once_with('https://example.com/image')
    client.session.head.assert_awaited_once_with('https://example.com/image')
    client.session.get.assert_not_called()


async def test_save_comments_with_child_comments(client: MagicMock, mocker: MockerFixture) -> None:
    client.should_save_child_comments = True
    parent_with_replies = {'id': 'p1', 'pk': 'p1pk', 'child_comment_count': 2}
    parent_no_replies = {'id': 'p2', 'pk': 'p2pk', 'child_comment_count': 0}
    mocker.patch.object(client,
                        'get_json',
                        new_callable=AsyncMock,
                        side_effect=[{
                            'comments': [parent_with_replies, parent_no_replies],
                            'can_view_more_preview_comments': False,
                            'next_min_id': None
                        }, {
                            'child_comments': [{
                                'id': 'r1',
                                'pk': 'r1pk'
                            }, {
                                'id': 'r2',
                                'pk': 'r2pk'
                            }],
                            'has_more_head_child_comments': False
                        }])
    mock_dump_json = mocker.patch('instagram_archiver.client.dump_json')

    await client.save_comments({'node': {'id': '999', 'pk': '999'}})

    assert parent_with_replies['child_comments'] == [{
        'id': 'r1',
        'pk': 'r1pk'
    }, {
        'id': 'r2',
        'pk': 'r2pk'
    }]
    assert 'child_comments' not in parent_no_replies
    mock_dump_json.assert_called_once_with('999-comments.json', mocker.ANY, mode='w+')


async def test_save_comments_child_comments_paginated(client: MagicMock,
                                                      mocker: MockerFixture) -> None:
    client.should_save_child_comments = True
    parent = {'id': 'p', 'pk': 'ppk', 'child_comment_count': 3}
    mock_get_json = mocker.patch.object(client,
                                        'get_json',
                                        new_callable=AsyncMock,
                                        side_effect=[{
                                            'comments': [parent],
                                            'can_view_more_preview_comments': False,
                                            'next_min_id': None
                                        }, {
                                            'child_comments': [{
                                                'id': 'r1'
                                            }],
                                            'has_more_head_child_comments': True,
                                            'next_min_id': 'cursor1'
                                        }, {
                                            'child_comments': [{
                                                'id': 'r2'
                                            }, {
                                                'id': 'r3'
                                            }],
                                            'has_more_head_child_comments': False
                                        }])
    mocker.patch('instagram_archiver.client.dump_json')

    await client.save_comments({'node': {'id': 'mid', 'pk': 'mid'}})

    children = cast('list[dict[str, Any]]', parent['child_comments'])
    assert [c['id'] for c in children] == ['r1', 'r2', 'r3']
    paged_call = mock_get_json.await_args_list[2]
    assert paged_call.kwargs['params']['min_id'] == 'cursor1'


async def test_save_comments_child_comments_disabled(client: MagicMock,
                                                     mocker: MockerFixture) -> None:
    client.should_save_child_comments = False
    parent = {'id': 'p', 'pk': 'ppk', 'child_comment_count': 5}
    mocker.patch.object(client,
                        'get_json',
                        new_callable=AsyncMock,
                        return_value={
                            'comments': [parent],
                            'can_view_more_preview_comments': False,
                            'next_min_id': None
                        })
    mocker.patch('instagram_archiver.client.dump_json')
    await client.save_comments({'node': {'id': 'm', 'pk': 'm'}})
    assert 'child_comments' not in parent


async def test_save_comments_child_comments_http_error(client: MagicMock,
                                                       mocker: MockerFixture) -> None:
    client.should_save_child_comments = True
    parent = {'id': 'p', 'pk': 'ppk', 'child_comment_count': 1}
    mocker.patch.object(client,
                        'get_json',
                        new_callable=AsyncMock,
                        side_effect=[{
                            'comments': [parent],
                            'can_view_more_preview_comments': False,
                            'next_min_id': None
                        }, HTTPError])
    mocker.patch('instagram_archiver.client.dump_json')
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')
    await client.save_comments({'node': {'id': 'mid', 'pk': 'mid'}})
    assert 'child_comments' not in parent
    mock_log_exception.assert_called_once_with('Failed to get child comments for `%s`.', 'ppk')


async def test_save_comments_child_comments_partial_then_error(client: MagicMock,
                                                               mocker: MockerFixture) -> None:
    """When pagination errors after collecting some replies, what we have is still embedded."""
    client.should_save_child_comments = True
    parent = {'id': 'p', 'pk': 'ppk', 'child_comment_count': 5}
    mocker.patch.object(client,
                        'get_json',
                        new_callable=AsyncMock,
                        side_effect=[{
                            'comments': [parent],
                            'can_view_more_preview_comments': False,
                            'next_min_id': None
                        }, {
                            'child_comments': [{
                                'id': 'r1'
                            }],
                            'has_more_head_child_comments': True,
                            'next_min_id': 'cursor1'
                        }, HTTPError])
    mocker.patch('instagram_archiver.client.dump_json')
    mocker.patch('instagram_archiver.client.log.exception')
    await client.save_comments({'node': {'id': 'mid', 'pk': 'mid'}})
    children = cast('list[dict[str, Any]]', parent['child_comments'])
    assert [c['id'] for c in children] == ['r1']


async def test_save_comments_child_comments_no_pk(client: MagicMock, mocker: MockerFixture) -> None:
    """Comment with child_comment_count > 0 but no pk/id is skipped with a debug log."""
    client.should_save_child_comments = True
    parent: dict[str, Any] = {'child_comment_count': 1}
    mocker.patch.object(client,
                        'get_json',
                        new_callable=AsyncMock,
                        return_value={
                            'comments': [parent],
                            'can_view_more_preview_comments': False,
                            'next_min_id': None
                        })
    mocker.patch('instagram_archiver.client.dump_json')
    mock_log_debug = mocker.patch('instagram_archiver.client.log.debug')
    await client.save_comments({'node': {'id': 'mid', 'pk': 'mid'}})
    assert 'child_comments' not in parent
    mock_log_debug.assert_called_once_with('Skipping reply fetch for comment with no pk/id.')


async def test_save_comments_http_error(client: MagicMock, mocker: MockerFixture) -> None:
    mock_get_json = mocker.patch.object(client,
                                        'get_json',
                                        new_callable=AsyncMock,
                                        side_effect=HTTPError)
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')

    edge = {'node': {'id': '123', 'pk': '123'}}
    await client.save_comments(edge)

    mock_get_json.assert_awaited_once_with('https://www.instagram.com/api/v1/media/123/comments/',
                                           params={
                                               'can_support_threading': 'true',
                                               'permalink_enabled': 'false'
                                           },
                                           headers=mocker.ANY,
                                           cast_to=Comments)
    mock_log_exception.assert_called_once_with('Failed to get comments.')


async def test_save_comments_http_error_page_2(client: MagicMock, mocker: MockerFixture) -> None:
    mock_get_json = mocker.patch.object(client,
                                        'get_json',
                                        new_callable=AsyncMock,
                                        side_effect=[{
                                            'can_view_more_preview_comments': True,
                                            'next_min_id': 'min',
                                            'comments': []
                                        }, HTTPError])
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')
    mocker.patch('instagram_archiver.client.dump_json')

    edge = {'node': {'id': '123', 'pk': '123'}}
    await client.save_comments(edge)

    mock_get_json.assert_awaited_with('https://www.instagram.com/api/v1/media/123/comments/',
                                      params={
                                          'can_support_threading': 'true',
                                          'min_id': 'min',
                                          'sort_order': 'popular'
                                      },
                                      headers=mocker.ANY,
                                      cast_to=Comments)
    mock_log_exception.assert_called_once_with('Failed to get comments.')


async def test_save_comments_uses_pk_in_url_and_id_in_filename(client: MagicMock,
                                                               mocker: MockerFixture) -> None:
    """The URL uses ``pk`` (bare numeric) and the filename keeps ``id`` (``<pk>_<owner>``)."""
    mock_get_json = mocker.patch.object(client,
                                        'get_json',
                                        new_callable=AsyncMock,
                                        return_value={
                                            'comments': [],
                                            'can_view_more_preview_comments': False,
                                            'next_min_id': None
                                        })
    mock_dump_json = mocker.patch('instagram_archiver.client.dump_json')
    edge = {'node': {'id': '3893923910883717076_31696836669', 'pk': '3893923910883717076'}}
    await client.save_comments(edge)
    args, _kwargs = mock_get_json.call_args
    assert args[0] == 'https://www.instagram.com/api/v1/media/3893923910883717076/comments/'
    mock_dump_json.assert_called_once_with('3893923910883717076_31696836669-comments.json',
                                           mocker.ANY,
                                           mode='w+')


async def test_save_comments_includes_referer_when_shortcode_present(client: MagicMock,
                                                                     mocker: MockerFixture) -> None:
    mock_get_json = mocker.patch.object(client,
                                        'get_json',
                                        new_callable=AsyncMock,
                                        return_value={
                                            'comments': [],
                                            'can_view_more_preview_comments': False,
                                            'next_min_id': None
                                        })
    mocker.patch('instagram_archiver.client.dump_json')
    edge = {'node': {'id': 'i', 'pk': 'p', 'code': 'DYJ_yqCn6_U'}}
    await client.save_comments(edge)
    sent_headers = mock_get_json.call_args.kwargs['headers']
    assert sent_headers['referer'] == 'https://www.instagram.com/p/DYJ_yqCn6_U/'


async def test_save_media_already_saved(client: MagicMock, mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=True)
    edge = {'node': {'code': 'test_code', 'pk': 'pk'}}
    await client.save_media(edge)
    mock_is_saved.assert_called_once_with('https://www.instagram.com/api/v1/media/pk/info/')
    client.session.get.assert_not_called()


async def test_save_media_get_request_failure(client: MagicMock, mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=False)
    response = MagicMock(status_code=404, text='not found')
    client.session.get.return_value = response
    mock_log_warning = mocker.patch('instagram_archiver.client.log.warning')

    edge = {'node': {'code': 'test_code', 'pk': 'pk'}}
    await client.save_media(edge)

    mock_is_saved.assert_called_once_with('https://www.instagram.com/api/v1/media/pk/info/')
    client.session.get.assert_awaited_once_with('https://www.instagram.com/api/v1/media/pk/info/',
                                                headers=mocker.ANY,
                                                allow_redirects=False)
    mock_log_warning.assert_called_once_with('GET request failed with status code %s.', 404)


async def test_save_media_redirect_error(client: MagicMock, mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=False)
    response = MagicMock(status_code=301)
    client.session.get.return_value = response

    edge = {'node': {'code': 'test_code', 'pk': 'pk'}}
    with pytest.raises(UnexpectedRedirect):
        await client.save_media(edge)

    mock_is_saved.assert_called_once_with('https://www.instagram.com/api/v1/media/pk/info/')
    client.session.get.assert_awaited_once_with('https://www.instagram.com/api/v1/media/pk/info/',
                                                headers=mocker.ANY,
                                                allow_redirects=False)


async def test_save_media_invalid_response(client: MagicMock, mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=False)
    response = MagicMock(status_code=200, text='invalid response')
    client.session.get.return_value = response
    mock_log_warning = mocker.patch('instagram_archiver.client.log.warning')

    edge = {'node': {'code': 'test_code', 'pk': 'pk'}}
    await client.save_media(edge)

    mock_is_saved.assert_called_once_with('https://www.instagram.com/api/v1/media/pk/info/')
    mock_log_warning.assert_called_once_with('Invalid response. image_versions2 dict not found.')


async def test_save_media_invalid_response_none_text(client: MagicMock,
                                                     mocker: MockerFixture) -> None:
    mocker.patch.object(client, 'is_saved', return_value=False)
    response = MagicMock(status_code=200, text=None)
    client.session.get.return_value = response
    mock_log_warning = mocker.patch('instagram_archiver.client.log.warning')

    edge = {'node': {'code': 'test_code', 'pk': 'pk'}}
    await client.save_media(edge)
    mock_log_warning.assert_called_once_with('Invalid response. image_versions2 dict not found.')


async def test_save_media_success(client: MagicMock, mocker: MockerFixture) -> None:
    mock_is_saved = mocker.patch.object(client, 'is_saved', return_value=False)
    mock_write_if_new = mocker.patch('instagram_archiver.client.write_if_new')
    mock_utime = mocker.patch('instagram_archiver.client.utime')
    mocker.patch.object(client, 'save_image_versions2', new_callable=AsyncMock)
    mock_save_to_log = mocker.patch.object(client, 'save_to_log')
    response = MagicMock(status_code=200,
                         text='{"image_versions2": {}, "taken_at": 1234567890}',
                         json=MagicMock(
                             return_value={
                                 'items': [{
                                     'taken_at': 1234567890,
                                     'carousel_media': [{}]
                                 }, {
                                     'taken_at': 1234567890,
                                     'image_versions2': {}
                                 }, {
                                     'taken_at': 1234567890
                                 }]
                             }))
    client.session.get.return_value = response
    edge = {'node': {'code': 'test_code', 'id': '123', 'pk': 'pk'}}
    await client.save_media(edge)
    client.session.get.assert_awaited_once_with('https://www.instagram.com/api/v1/media/pk/info/',
                                                headers=mocker.ANY,
                                                allow_redirects=False)
    mock_is_saved.assert_called_once_with('https://www.instagram.com/api/v1/media/pk/info/')
    mock_write_if_new.assert_any_call('123.json', mocker.ANY)
    mock_write_if_new.assert_any_call('123-media-info-0000.json', mocker.ANY)
    mock_utime.assert_any_call('123.json', (1234567890, 1234567890))
    mock_utime.assert_any_call('123-media-info-0000.json', (1234567890, 1234567890))
    mock_save_to_log.assert_called_once_with('https://www.instagram.com/api/v1/media/pk/info/')


async def test_save_edges_typename_xdtmediadict_video(client: MagicMock,
                                                      mocker: MockerFixture) -> None:
    mock_add_video_url = mocker.patch.object(client, 'add_video_url')
    edge = {
        'node': {
            '__typename': 'XDTMediaDict',
            'code': 'test_code',
            'video_dash_manifest': True
        }
    }
    await client.save_edges([edge])
    mock_add_video_url.assert_called_once_with('https://www.instagram.com/p/test_code/')


async def test_save_edges_typename_xdtmediadict_media(client: MagicMock,
                                                      mocker: MockerFixture) -> None:
    mock_save_comments = mocker.patch.object(client, 'save_comments', new_callable=AsyncMock)
    mock_save_media = mocker.patch.object(client, 'save_media', new_callable=AsyncMock)
    edge = {'node': {'__typename': 'XDTMediaDict', 'code': 'test_code'}}
    await client.save_edges([edge])
    mock_save_comments.assert_awaited_once_with(edge)
    mock_save_media.assert_awaited_once_with(edge)


async def test_save_edges_typename_xdtmediadict_retry_error(client: MagicMock,
                                                            mocker: MockerFixture) -> None:
    mock_save_comments = mocker.patch.object(client,
                                             'save_comments',
                                             new_callable=AsyncMock,
                                             side_effect=RetryError)
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')
    edge = {'node': {'__typename': 'XDTMediaDict', 'code': 'test_code'}}
    await client.save_edges([edge])
    mock_save_comments.assert_awaited_once_with(edge)
    mock_log_exception.assert_called_once_with('Retries exhausted.')


async def test_save_edges_unknown_typename(client: MagicMock, mocker: MockerFixture) -> None:
    mock_log_warning = mocker.patch('instagram_archiver.client.log.warning')
    edge = {'node': {'__typename': 'UnknownType', 'id': '123', 'code': 'test_code'}}
    await client.save_edges([edge])
    mock_log_warning.assert_called_once_with('Unknown type: `%s`. Item %s will not be processed.',
                                             'UnknownType', '123')
    assert 'https://www.instagram.com/p/test_code/' in client.failed_urls


async def test_save_edges_parent_edge(client: MagicMock, mocker: MockerFixture) -> None:
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')
    mocker.patch.object(client, 'save_media', new_callable=AsyncMock)
    mocker.patch.object(client, 'save_comments', new_callable=AsyncMock)
    parent_edge = {'node': {'code': 'parent_code', 'id': 'some_id'}}
    edge = {'node': {'__typename': 'XDTMediaDict', 'id': 'other_id'}}
    await client.save_edges([edge], parent_edge=parent_edge)
    mock_log_exception.assert_not_called()


async def test_save_edges_parent_edge_missing_code(client: MagicMock,
                                                   mocker: MockerFixture) -> None:
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')
    parent_edge: dict[str, Any] = {'node': {}}
    edge = {'node': {'__typename': 'XDTMediaDict'}}
    await client.save_edges([edge], parent_edge=parent_edge)
    mock_log_exception.assert_called_once_with('Unknown shortcode.')


async def test_save_edges_missing_code_no_parent(client: MagicMock, mocker: MockerFixture) -> None:
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')
    mocker.patch.object(client, 'save_media', new_callable=AsyncMock)
    mocker.patch.object(client, 'save_comments', new_callable=AsyncMock)
    edge = {'node': {'__typename': 'XDTMediaDict'}}
    await client.save_edges([edge])
    mock_log_exception.assert_called_once_with('Unknown shortcode.')


async def test_get_json_success(client: MagicMock, mocker: MockerFixture) -> None:
    response = MagicMock(status_code=200, json=MagicMock(return_value={'key': 'value'}))
    client.session.get.return_value = response
    result = await client.get_json('https://example.com', cast_to=dict)
    assert result == {'key': 'value'}
    client.session.get.assert_awaited_once_with('https://example.com',
                                                params=None,
                                                headers=mocker.ANY)


async def test_get_json_with_params(client: MagicMock, mocker: MockerFixture) -> None:
    response = MagicMock(status_code=200, json=MagicMock(return_value={'key': 'value'}))
    client.session.get.return_value = response
    params = {'param1': 'value1'}
    result = await client.get_json('https://example.com', cast_to=dict, params=params)
    assert result == {'key': 'value'}
    client.session.get.assert_awaited_once_with('https://example.com',
                                                params=params,
                                                headers=mocker.ANY)


async def test_dispatch_edges_video(client: MagicMock) -> None:
    image_q: asyncio.Queue[Any] = asyncio.Queue()
    comments_q: asyncio.Queue[Any] = asyncio.Queue()
    video_q: asyncio.Queue[Any] = asyncio.Queue()
    edge = {'node': {'__typename': 'XDTMediaDict', 'code': 'sc', 'video_dash_manifest': 'manifest'}}
    await client.dispatch_edges([edge], image_q, comments_q, video_q)
    assert video_q.get_nowait() == 'https://www.instagram.com/p/sc/'
    assert image_q.empty()
    assert comments_q.empty()


async def test_dispatch_edges_increments_stats_and_yt_dlp_state(client: MagicMock) -> None:
    """``stats=`` increments ``POSTS_HANDLED`` and ``yt_dlp_state=`` bumps ``total_urls``."""
    image_q: asyncio.Queue[Any] = asyncio.Queue()
    comments_q: asyncio.Queue[Any] = asyncio.Queue()
    video_q: asyncio.Queue[Any] = asyncio.Queue()
    stats = Stats()
    state = YTDLPState()
    edge = {'node': {'__typename': 'XDTMediaDict', 'code': 'sc', 'video_dash_manifest': 'manifest'}}
    await client.dispatch_edges([edge],
                                image_q,
                                comments_q,
                                video_q,
                                stats=stats,
                                yt_dlp_state=state)
    assert stats[POSTS_HANDLED] == 1
    assert state.total_urls == 1


async def test_dispatch_edges_image_and_comments(client: MagicMock) -> None:
    client.should_save_comments = True
    image_q: asyncio.Queue[Any] = asyncio.Queue()
    comments_q: asyncio.Queue[Any] = asyncio.Queue()
    video_q: asyncio.Queue[Any] = asyncio.Queue()
    edge = {'node': {'__typename': 'XDTMediaDict', 'code': 'sc'}}
    await client.dispatch_edges([edge], image_q, comments_q, video_q)
    assert image_q.get_nowait() is edge
    assert comments_q.get_nowait() is edge
    assert video_q.empty()


async def test_dispatch_edges_image_no_comments(client: MagicMock) -> None:
    client.should_save_comments = False
    image_q: asyncio.Queue[Any] = asyncio.Queue()
    comments_q: asyncio.Queue[Any] = asyncio.Queue()
    video_q: asyncio.Queue[Any] = asyncio.Queue()
    edge = {'node': {'__typename': 'XDTMediaDict', 'code': 'sc'}}
    await client.dispatch_edges([edge], image_q, comments_q, video_q)
    assert image_q.get_nowait() is edge
    assert comments_q.empty()


async def test_dispatch_edges_unknown_type(client: MagicMock) -> None:
    image_q: asyncio.Queue[Any] = asyncio.Queue()
    comments_q: asyncio.Queue[Any] = asyncio.Queue()
    video_q: asyncio.Queue[Any] = asyncio.Queue()
    edge = {'node': {'__typename': 'Other', 'id': '99', 'code': 'sc99'}}
    await client.dispatch_edges([edge], image_q, comments_q, video_q)
    assert 'https://www.instagram.com/p/sc99/' in client.failed_urls


async def test_dispatch_edges_missing_code_no_parent(client: MagicMock,
                                                     mocker: MockerFixture) -> None:
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')
    image_q: asyncio.Queue[Any] = asyncio.Queue()
    comments_q: asyncio.Queue[Any] = asyncio.Queue()
    video_q: asyncio.Queue[Any] = asyncio.Queue()
    edge = {'node': {'__typename': 'XDTMediaDict'}}
    await client.dispatch_edges([edge], image_q, comments_q, video_q)
    mock_log_exception.assert_called_once_with('Unknown shortcode.')
    assert image_q.empty()


async def test_dispatch_edges_missing_code_parent_fallback(client: MagicMock) -> None:
    image_q: asyncio.Queue[Any] = asyncio.Queue()
    comments_q: asyncio.Queue[Any] = asyncio.Queue()
    video_q: asyncio.Queue[Any] = asyncio.Queue()
    parent = {'node': {'code': 'pcode'}}
    edge = {'node': {'__typename': 'XDTMediaDict'}}
    await client.dispatch_edges([edge], image_q, comments_q, video_q, parent_edge=parent)
    assert image_q.get_nowait() is edge


async def test_dispatch_edges_missing_code_parent_missing(client: MagicMock,
                                                          mocker: MockerFixture) -> None:
    mock_log_exception = mocker.patch('instagram_archiver.client.log.exception')
    image_q: asyncio.Queue[Any] = asyncio.Queue()
    comments_q: asyncio.Queue[Any] = asyncio.Queue()
    video_q: asyncio.Queue[Any] = asyncio.Queue()
    parent: dict[str, Any] = {'node': {}}
    edge = {'node': {'__typename': 'XDTMediaDict'}}
    await client.dispatch_edges([edge], image_q, comments_q, video_q, parent_edge=parent)
    mock_log_exception.assert_called_once_with('Unknown shortcode.')


async def test_reel_page_gallery_initial(client: MagicMock, mocker: MockerFixture) -> None:
    mock_query = mocker.patch.object(client,
                                     'graphql_query',
                                     new_callable=AsyncMock,
                                     return_value={
                                         'xdt_api__v1__feed__reels_media': {
                                             'edges': [],
                                             'page_info': {
                                                 'end_cursor': None,
                                                 'has_next_page': False
                                             }
                                         }
                                     })
    result = await client.reel_page_gallery(['1', '2'])
    assert result == {'edges': [], 'page_info': {'end_cursor': None, 'has_next_page': False}}
    args, kwargs = mock_query.call_args
    variables = args[0]
    assert variables == {'first': 5, 'initial_reel_id': '1', 'last': None, 'reel_ids': ['1', '2']}
    assert kwargs['doc_id'] == '26659189347081290'


async def test_reel_page_gallery_paginated(client: MagicMock, mocker: MockerFixture) -> None:
    mock_query = mocker.patch.object(client,
                                     'graphql_query',
                                     new_callable=AsyncMock,
                                     return_value={
                                         'xdt_api__v1__feed__reels_media': {
                                             'edges': [],
                                             'page_info': {
                                                 'end_cursor': None,
                                                 'has_next_page': False
                                             }
                                         }
                                     })
    await client.reel_page_gallery(['1', '2'],
                                   after='cur',
                                   first=3,
                                   initial_reel_id='2',
                                   is_highlight=False)
    args, kwargs = mock_query.call_args
    assert args[0] == {
        'after': 'cur',
        'before': None,
        'first': 3,
        'initial_reel_id': '2',
        'is_highlight': False,
        'last': None,
        'reel_ids': ['1', '2']
    }
    assert kwargs['doc_id'] == '27002830962682635'


async def test_reel_page_gallery_no_data(client: MagicMock, mocker: MockerFixture) -> None:
    mocker.patch.object(client, 'graphql_query', new_callable=AsyncMock, return_value=None)
    assert await client.reel_page_gallery(['1']) is None


async def test_reel_page_gallery_empty_reel_ids(client: MagicMock, mocker: MockerFixture) -> None:
    mock_query = mocker.patch.object(client, 'graphql_query', new_callable=AsyncMock)
    assert await client.reel_page_gallery([]) is None
    mock_query.assert_not_called()


async def test_reel_page_gallery_unrecognised_response(client: MagicMock,
                                                       mocker: MockerFixture) -> None:
    mocker.patch.object(client,
                        'graphql_query',
                        new_callable=AsyncMock,
                        return_value={'unrelated_key': {
                            'value': 1
                        }})
    mock_log_warning = mocker.patch('instagram_archiver.client.log.warning')
    assert await client.reel_page_gallery(['1']) is None
    mock_log_warning.assert_called_once_with(
        'Reel gallery response did not contain a recognisable connection.')


async def test_reel_page_gallery_fallback_key(client: MagicMock, mocker: MockerFixture) -> None:
    """The connection extractor falls back to any value with edges + page_info."""
    payload = {'edges': [], 'page_info': {'end_cursor': None, 'has_next_page': False}}
    mocker.patch.object(client,
                        'graphql_query',
                        new_callable=AsyncMock,
                        return_value={'some_renamed_wrapper': payload})
    assert await client.reel_page_gallery(['1']) == payload


async def test_save_reel_item_image(client: MagicMock, mocker: MockerFixture) -> None:
    mock_save_image = mocker.patch.object(client, 'save_image_versions2', new_callable=AsyncMock)
    item = {'id': 'i', 'image_versions2': {'candidates': []}, 'pk': 'pk', 'taken_at': 99}
    await client.save_reel_item(item)
    mock_save_image.assert_awaited_once_with(item, 99)


async def test_save_reel_item_video_with_queue(client: MagicMock) -> None:
    state = YTDLPState()
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    item = {
        'id': 'v',
        'image_versions2': {
            'candidates': []
        },
        'pk': 'video',
        'taken_at': 1,
        'video_versions': [{
            'url': 'https://example.com/v.mp4',
            'width': 1,
            'height': 1
        }]
    }
    await client.save_reel_item(item, queue, username='alice', yt_dlp_state=state)
    assert queue.get_nowait() == 'https://www.instagram.com/stories/alice/video/'
    assert state.total_urls == 1


async def test_save_reel_item_video_no_queue(client: MagicMock, mocker: MockerFixture) -> None:
    mock_add = mocker.patch.object(client, 'add_video_url')
    item = {
        'id': 'v',
        'image_versions2': {
            'candidates': []
        },
        'pk': 'video',
        'taken_at': 1,
        'video_dash_manifest': 'manifest'
    }
    await client.save_reel_item(item)
    mock_add.assert_called_once_with('https://www.instagram.com/stories/_/video/')


async def test_save_reel_item_neither(client: MagicMock, mocker: MockerFixture) -> None:
    mock_log_debug = mocker.patch('instagram_archiver.client.log.debug')
    mock_save_image = mocker.patch.object(client, 'save_image_versions2', new_callable=AsyncMock)
    await client.save_reel_item({'id': 'x', 'pk': 'unknown', 'taken_at': 0})
    mock_save_image.assert_not_called()
    mock_log_debug.assert_called_once_with('Reel item `%s` has neither image nor video data.',
                                           'unknown')


async def test_aenter_aexit(mocker: MockerFixture) -> None:
    mock_setup = mocker.patch('instagram_archiver.client.setup_session', new_callable=AsyncMock)
    mock_setup.return_value = MagicMock(close=AsyncMock(), headers=MagicMock())
    client = InstagramClient()
    async with client:
        assert client.session is mock_setup.return_value
    client.session.close.assert_awaited_once()
