from os import chdir, makedirs
from os.path import isfile
from pathlib import Path
from typing import Any
import json
import re
import sys

from loguru import logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from yt_dlp.cookies import extract_cookies_from_browser
import click
import requests
import yt_dlp

from .constants import SHARED_HEADERS
from .utils import (YoutubeDLLogger, get_extension, setup_logging,
                    write_if_new)


def highlights_tray(session: requests.Session, user_id: int | str) -> Any:
    with session.get(f'https://i.instagram.com/api/v1/highlights/{user_id}/'
                     'highlights_tray/') as r:
        r.raise_for_status()
        return r.json()


@click.command()
@click.option('-o',
              '--output-dir',
              default=None,
              help='Output directory',
              type=click.Path(exists=True))
@click.option('-b',
              '--browser',
              default='chrome',
              help='Browser to read cookies from')
@click.option('-p', '--profile', default='Default', help='Browser profile')
@click.option('-d', '--debug', is_flag=True, help='Enable debug output')
@click.argument('username')
def main(output_dir: Path | str | None,
         browser: str,
         profile: str,
         username: str,
         debug: bool = False) -> None:
    setup_logging(debug)
    if output_dir is None:
        output_dir = Path('.', username)
        makedirs(output_dir, exist_ok=True)
    chdir(output_dir)
    with requests.Session() as session:
        session.mount(
            'https://',
            HTTPAdapter(max_retries=Retry(backoff_factor=2.5,
                                          status_forcelist=(
                                              429,
                                              500,
                                              502,
                                              503,
                                              504,
                                          ))))
        session.headers.update({
            **SHARED_HEADERS,
            **dict(cookie='; '.join(f'{cookie.name}={cookie.value}' \
                for cookie in extract_cookies_from_browser(browser, profile)
                    if 'instagram.com' in cookie.domain))
        })
        r = session.get('https://www.instagram.com')
        r.raise_for_status()
        r = session.get(f'https://www.instagram.com/{username}/')
        r.raise_for_status()
        m = re.search(r'"config":{"csrf_token":"([^"]+)"', r.text)
        assert m is not None
        session.headers.update({'x-csrftoken': m.group(1)})
        r = session.get(
            'https://i.instagram.com/api/v1/users/web_profile_info/',
            params={'username': username})
        r.raise_for_status()
        with open('web_profile_info.json', 'wb') as f:
            f.write(r.content)
        user_info = r.json()['data']['user']
        r = session.get(user_info['profile_pic_url_hd'])
        r.raise_for_status()
        with open('profile_pic.jpg', 'wb') as f:
            f.write(r.content)
        video_urls = []

        # for item in highlights_tray(session, user_info['id'])['tray']:
        #     video_urls.append('https://www.instagram.com/stories/highlights/'
        #                       f'{item["id"].split(":")[-1]}/')
        # sys.argv = [sys.argv[0]]
        # ydl_opts = yt_dlp.parse_options()[-1]
        # with yt_dlp.YoutubeDL({
        #         **ydl_opts,
        #         **dict(http_headers=SHARED_HEADERS,
        #                logger=YoutubeDLLogger(),
        #                verbose=debug)
        # }) as ydl:
        #     for url in video_urls:
        #         ydl.extract_info(url)

        def save_stuff(edges: Any) -> None:
            nonlocal video_urls
            for edge in edges:
                shortcode = edge['node']['shortcode']
                if edge['node']['__typename'] == 'GraphVideo':
                    video_urls.append(
                        f'https://www.instagram.com/p/{shortcode}')
                elif edge['node']['__typename'] == 'GraphImage':
                    r = session.head(edge['node']['display_url'])
                    r.raise_for_status()
                    ext = get_extension(r.headers['content-type'])
                    name = f'{edge["node"]["id"]}.{ext}'
                    if not isfile(name):
                        r = session.get(edge['node']['display_url'])
                        r.raise_for_status()
                        write_if_new(name, r.content, 'wb')
                    write_if_new(f'{edge["node"]["id"]}.json',
                                 json.dumps(edge['node']))
                elif edge['node']['__typename'] == 'GraphSidecar':
                    r = session.get('https://i.instagram.com/api/v1/media/'
                                    f'{edge["node"]["id"]}/info/')
                    item = r.json()['items'][0]
                    r.raise_for_status()
                    write_if_new(f'{edge["node"]["id"]}.json',
                                 json.dumps(item))
                    for item in item['carousel_media']:
                        best = sorted(item['image_versions2']['candidates'],
                                      key=lambda x: x['width'] * x['height'],
                                      reverse=True)[0]
                        r = session.head(best['url'])
                        r.raise_for_status()
                        ext = get_extension(r.headers['content-type'])
                        name = f'{item["id"]}.{ext}'
                        if not isfile(name):
                            r = session.get(best['url'])
                            r.raise_for_status()
                            write_if_new(name, r.content, 'wb')

        save_stuff(user_info['edge_owner_to_timeline_media']['edges'])
        page_info = user_info['edge_owner_to_timeline_media']['page_info']
        while page_info['has_next_page']:
            params = dict(query_hash='69cba40317214236af40e7efa697781d',
                          variables=json.dumps(
                              dict(id=user_info['id'],
                                   first=12,
                                   after=page_info['end_cursor'])))
            r = session.get('https://www.instagram.com/graphql/query/',
                            params=params)
            r.raise_for_status()
            media = r.json()['data']['user']['edge_owner_to_timeline_media']
            page_info = media['page_info']
            save_stuff(media['edges'])
        sys.argv = [sys.argv[0]]
        ydl_opts = yt_dlp.parse_options()[-1]
        if len(video_urls) > 0:
            with yt_dlp.YoutubeDL({
                    **ydl_opts,
                    **dict(http_headers=SHARED_HEADERS,
                           logger=YoutubeDLLogger(),
                           verbose=debug)
            }) as ydl:
                failed_urls = []
                for url in video_urls:
                    if (not ydl.in_download_archive(
                            dict(id=url.split('/')[-1],
                                 extractor_key='instagram'))
                            and not ydl.extract_info(url, ie_key='Instagram')):
                        failed_urls.append(url)
                if len(failed_urls) > 0:
                    logger.error('Some video URIs failed. Check failed.txt.')
                    with open('failed.txt', 'w') as f:
                        for url in failed_urls:
                            f.write(f'{url}\n')
