from typing import Any, Mapping, Optional, cast

from bs4 import BeautifulSoup as Soup
from yt_dlp.extractor.instagram import InstagramIE
from yt_dlp.utils import (float_or_none, format_field, int_or_none,
                          lowercase_escape, str_to_int, traverse_obj)

from .constants import EXTRACT_VIDEO_INFO_JS
from .utils import call_node_json


class ImprovedInstagramIE(InstagramIE):
    _VALID_URL = (r'(?P<url>https?://(?:www\.)?instagram\.com(?:/[^/]+)?/'
                  r'(?:p|tv|reel)/(?P<id>[^/?#&]+))')

    @classmethod
    def ie_key(cls):
        return 'ImprovedInstagram'

    def _real_extract(self, url: str) -> Mapping[str, Any]:
        video_id, url = self._match_valid_url(url).group('id', 'url')
        webpage, urlh = self._download_webpage_handle(url, video_id)
        if 'www.instagram.com/accounts/login' in urlh.geturl():
            self.report_warning(
                'Main webpage is locked behind the login page. '
                'Retrying with embed webpage (Note that some metadata might '
                'be missing)')
            webpage = self._download_webpage(
                f'https://www.instagram.com/p/{video_id}/embed/',
                video_id,
                note='Downloading embed webpage')
        xig_js = [
            c for c in Soup(webpage, 'html5lib').select('script') if c.string
            and c.string.startswith('requireLazy(["JSScheduler","ServerJS",'
                                    '"ScheduledApplyEach"],')
        ][0].string
        assert xig_js is not None
        xig_js = xig_js.strip()
        assert len(xig_js) > 0
        data = call_node_json(EXTRACT_VIDEO_INFO_JS + xig_js)
        props = data['hostableView']['props']
        media_id = props['media_id']
        info = self._download_json(
            f'https://i.instagram.com/api/v1/media/{media_id}/info/',
            video_id)['items'][0]
        best_video = sorted(info['video_versions'],
                            key=lambda x: x['height'] * x['width'],
                            reverse=True)[0]
        shared_data = {
            'entry_data': {
                'PostPage': [{
                    'media': {
                        'owner':
                        info['user'],
                        'caption':
                        traverse_obj(info, ('caption', 'text'),
                                     expected_type=str),
                        'video_url':
                        best_video['url'],
                        'height':
                        best_video['height'],
                        'width':
                        best_video['width'],
                        'edge_media_to_parent_comment': {
                            'edges': []
                        },
                        'comments': {
                            'preview_comment': {
                                'to_comment': {
                                    'to_parent_comment':
                                    info.get('comment_count', None)
                                }
                            }
                        },
                        'likes': {
                            'preview_like': info.get('like_count', None)
                        },
                        'taken_at_timestamp':
                        info['taken_at'],
                        'display_resources': [{
                            'config_width': x['width'],
                            'config_height': x['height'],
                            'url': x['url']
                        } for x in info.get('image_versions2', {}).get(
                            'candidates', [])],
                        'dash_info': {
                            'video_dash_manifest':
                            info.get('video_dash_manifest', None)
                        }
                    }
                }]
            }
        }
        media = traverse_obj(shared_data,
                             ('entry_data', 'PostPage', 0, 'media'),
                             expected_type=dict)
        # _sharedData.entry_data.PostPage is empty when authenticated (see
        # https://github.com/ytdl-org/youtube-dl/pull/22880)
        if not media:
            additional_data = self._parse_json(self._search_regex(
                (r'window\.__additionalDataLoaded\s*\(\s*[^,]+,\s*({.+?})\s*'
                 r'\);'),
                webpage,
                'additional data',
                default='{}'),
                                               video_id,
                                               fatal=False)
            product_item = traverse_obj(additional_data, ('items', 0),
                                        expected_type=dict)
            if product_item:
                return self._extract_product(product_item)
            media = traverse_obj(additional_data,
                                 ('graphql', 'shortcode_media'),
                                 'shortcode_media',
                                 expected_type=dict) or {}
        if not media and 'www.instagram.com/accounts/login' in urlh.geturl():
            self.raise_login_required(
                'You need to log in to access this content')
        username = traverse_obj(
            media, ('owner', 'username')) or self._search_regex(
                r'"owner"\s*:\s*{\s*"username"\s*:\s*"(.+?)"',
                webpage,
                'username',
                fatal=False)
        description = (traverse_obj(
            media, ('edge_media_to_caption', 'edges', 0, 'node', 'text'),
            expected_type=str) or media.get('caption'))
        if not description:
            description = self._search_regex(r'"caption"\s*:\s*"(.+?)"',
                                             webpage,
                                             'description',
                                             default=None)
            if description is not None:
                description = lowercase_escape(description)
        video_url = media.get('video_url')
        if not video_url:
            nodes = traverse_obj(
                media, ('edge_sidecar_to_children', 'edges', ..., 'node'),
                expected_type=dict) or []
            if nodes:
                return self.playlist_result(
                    self._extract_nodes(nodes, True), video_id,
                    format_field(username, template='Post by %s'), description)
            video_url = self._og_search_video_url(webpage, secure=False)
        formats = [{
            'url': video_url,
            'width': self._get_dimension('width', media, webpage),
            'height': self._get_dimension('height', media, webpage),
        }]
        dash = traverse_obj(media, ('dash_info', 'video_dash_manifest'))
        if dash:
            formats.extend(
                self._parse_mpd_formats(self._parse_xml(dash, video_id),
                                        mpd_id='dash'))
        self._sort_formats(formats)
        comment_data = traverse_obj(media,
                                    ('edge_media_to_parent_comment', 'edges'))
        comments = [{
            'author':
            traverse_obj(comment_dict, ('node', 'owner', 'username')),
            'author_id':
            traverse_obj(comment_dict, ('node', 'owner', 'id')),
            'id':
            traverse_obj(comment_dict, ('node', 'id')),
            'text':
            traverse_obj(comment_dict, ('node', 'text')),
            'timestamp':
            traverse_obj(comment_dict, ('node', 'created_at'),
                         expected_type=int_or_none),
        } for comment_dict in comment_data] if comment_data else None

        display_resources = (media.get('display_resources')
                             or [{
                                 'src': media.get(key)
                             } for key in ('display_src', 'display_url')]
                             or [{
                                 'src': self._og_search_thumbnail(webpage)
                             }])
        thumbnails = [{
            'url': thumbnail['src'],
            'width': thumbnail.get('config_width'),
            'height': thumbnail.get('config_height'),
        } for thumbnail in display_resources if thumbnail.get('src')]
        return {
            'id':
            video_id,
            'formats':
            formats,
            'title':
            media.get('title') or f'Video by {username}',
            'description':
            description,
            'duration':
            float_or_none(cast(Optional[str], media.get('video_duration'))),
            'timestamp':
            traverse_obj(media,
                         'taken_at_timestamp',
                         'date',
                         expected_type=int_or_none),
            'uploader_id':
            traverse_obj(media, ('owner', 'id')),
            'uploader':
            traverse_obj(media, ('owner', 'full_name')),
            'channel':
            username,
            'like_count':
            self._get_count(media, 'likes', 'preview_like') or str_to_int(
                self._search_regex(
                    r'data-log-event="likeCountClick"[^>]*>[^\d]*([\d,\.]+)',
                    webpage,
                    'like count',
                    fatal=False)),
            'comment_count':
            self._get_count(media, 'comments', 'preview_comment', 'to_comment',
                            'to_parent_comment'),
            'comments':
            comments,
            'thumbnails':
            thumbnails,
            'http_headers': {
                'Referer': 'https://www.instagram.com/',
            }
        }
