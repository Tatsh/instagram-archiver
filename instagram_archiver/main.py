from os import chdir, makedirs
from os.path import isfile
from pathlib import Path
from typing import Any, Optional, Union
import json
import sys

from bs4 import BeautifulSoup as Soup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from yt_dlp.cookies import extract_cookies_from_browser
import click
import requests
import yt_dlp

from .constants import EXTRACT_XIGSHAREDDATA_JS, SHARED_HEADERS
from .extractor import ImprovedInstagramIE
from .utils import (YoutubeDLLogger, call_node_json, get_extension,
                    setup_logging, write_if_new)


@click.command()
@click.option('-o', '--output-dir', default=None, help='Output directory')
@click.option('-b',
              '--browser',
              default='chrome',
              help='Browser to read cookies from')
@click.option('-p', '--profile', default='Default', help='Browser profile')
@click.option('-d', '--debug', is_flag=True, help='Enable debug output')
@click.argument('username')
def main(output_dir: Optional[Union[Path, str]],
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
            HTTPAdapter(
                max_retries=Retry(backoff_factor=2.5,
                                  status_forcelist=[429, 500, 502, 503, 504])))
        session.headers.update({
            **SHARED_HEADERS,
            **dict(cookie='; '.join(f'{c.name}={c.value}' \
                for c in extract_cookies_from_browser(browser, profile)
                    if 'instagram.com' in c.domain))
        })
        r = session.get('https://www.instagram.com')
        r.raise_for_status()
        r = session.get(f'https://www.instagram.com/{username}/')
        r.raise_for_status()
        try:
            xig_js = [
                c for c in Soup(r.content, 'html5lib').select('script')
                if c.string and c.string.startswith(
                    'requireLazy(["JSScheduler","ServerJS",'
                    '"ScheduledApplyEach"],')
            ][0].string
        except IndexError as e:
            raise click.Abort() from e
        assert xig_js is not None
        data = call_node_json(EXTRACT_XIGSHAREDDATA_JS + xig_js)
        session.headers.update({'x-csrftoken': data['config']['csrf_token']})
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

        def save_stuff(edges: Any) -> None:
            nonlocal video_urls
            for edge in edges:
                shortcode = edge['node']['shortcode']
                if edge['node']['__typename'] == 'GraphVideo':
                    video_urls.append(
                        f'https://www.instagram.com/p/{shortcode}')
                elif edge['node']['__typename'] in ('GraphImage',
                                                    'GraphSidecar'):
                    r = session.head(edge['node']['display_url'])
                    r.raise_for_status()
                    ext = get_extension(r.headers['content-type'])
                    name = f'{edge["node"]["id"]}.{ext}'
                    if not isfile(name):
                        r = session.get(edge['node']['display_url'])
                        r.raise_for_status()
                        write_if_new(
                            f'{edge["node"]["id"]}.{ext}',
                            r.content,
                            'wb',
                        )
                    write_if_new(f'{edge["node"]["id"]}.json',
                                 json.dumps(edge['node']))

        save_stuff(user_info['edge_owner_to_timeline_media']['edges'])
        page_info = (user_info['edge_owner_to_timeline_media']['page_info'])
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
                ydl.add_info_extractor(ImprovedInstagramIE())
                for url in video_urls:
                    if not ydl.extract_info(url, ie_key='ImprovedInstagram'):
                        raise click.Abort()
