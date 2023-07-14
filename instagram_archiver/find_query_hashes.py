from typing import Iterator, cast
import re

from bs4 import BeautifulSoup
from yt_dlp.cookies import extract_cookies_from_browser
import requests

from .constants import SHARED_HEADERS
from .ig_typing import BrowserName

__all__ = ('find_query_hashes',)


def find_query_hashes(browser: BrowserName = 'chrome', profile: str = 'Default') -> Iterator[str]:
    """Gets the current query hashes in Instagram's JavaScript files."""
    with requests.Session() as session:
        session.headers.update({
            **SHARED_HEADERS,
            **dict(cookie='; '.join(f'{cookie.name}={cookie.value}' \
                for cookie in extract_cookies_from_browser(browser, profile)
                    if 'instagram.com' in cookie.domain))
        })
        r = session.get('https://instagram.com')
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html5lib')
        for script in soup.select('script'):
            if script.has_attr('type') or not script.has_attr('src'):
                continue
            r = session.get(cast(str, script['src']))
            r.raise_for_status()
            yield from re.findall(r'[a-z]="([a-f0-9]{32})"', r.content.decode())
