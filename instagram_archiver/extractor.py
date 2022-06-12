# pylint: disable=abstract-method
from typing import Any, Mapping

from bs4 import BeautifulSoup as Soup
from yt_dlp.extractor.instagram import InstagramIE
from yt_dlp.utils import float_or_none, int_or_none, traverse_obj

from instagram_archiver.ig_typing import MediaInfoItem

from .constants import EXTRACT_VIDEO_INFO_JS
from .utils import call_node_json


class ImprovedInstagramIE(InstagramIE):
    _VALID_URL = (r'(?P<url>https?://(?:www\.)?instagram\.com(?:/[^/]+)?/'
                  r'(?:p|tv|reel)/(?P<id>[^/?#&]+))')

    @classmethod
    def ie_key(cls) -> str:
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
            script for script in Soup(webpage, 'html5lib').select('script')
            if script.string and script.string.startswith(
                'requireLazy(["JSScheduler","ServerJS",'
                '"ScheduledApplyEach"],')
        ][0].string
        assert xig_js is not None
        xig_js = xig_js.strip()
        assert len(xig_js) > 0
        data = call_node_json(EXTRACT_VIDEO_INFO_JS + xig_js)
        props = data['hostableView']['props']
        info: MediaInfoItem = self._download_json(
            ('https://i.instagram.com/api/v1/media/'
             f'{props["media_id"]}/info/'), video_id)['items'][0]
        username = traverse_obj(
            info,
            ('user', 'username'),
            expected_type=str,
        )
        formats = [{
            'url': x['url'],
            'width': x['width'],
            'height': x['height'],
        } for x in info['video_versions']]
        dash = info.get('video_dash_manifest')
        if dash:
            formats.extend(
                self._parse_mpd_formats(self._parse_xml(dash, video_id),
                                        mpd_id='dash'))
        self._sort_formats(formats)
        return {
            'id':
            video_id,
            'formats':
            formats,
            'title':
            f'Video by {username}',
            'description':
            traverse_obj(info, ('caption', 'text'), expected_type=str),
            'duration':
            float_or_none(info.get('video_duration')),
            'timestamp':
            traverse_obj(info, 'taken_at', expected_type=int_or_none),
            'uploader_id':
            str(traverse_obj(info, ('user', 'pk'), expected_type=int)),
            'uploader':
            traverse_obj(info, ('user', 'full_name'), expected_type=str),
            'channel':
            username,
            'like_count':
            traverse_obj(info, 'like_count', expected_type=int_or_none),
            'comment_count':
            traverse_obj(info, 'comment_count', expected_type=int_or_none),
            'thumbnails': [{
                'url': thumbnail['url'],
                'width': thumbnail.get('width'),
                'height': thumbnail.get('height'),
            } for thumbnail in info.get('image_versions2', {}).get(
                'candidates', []) if thumbnail.get('url')],
            'http_headers': {
                'Referer': 'https://www.instagram.com/',
            }
        }
