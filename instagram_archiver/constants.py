"""Constants."""
from __future__ import annotations

__all__ = ('API_HEADERS', 'BROWSER_CHOICES', 'PAGE_FETCH_HEADERS', 'SHARED_HEADERS', 'USER_AGENT')

USER_AGENT = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/137.0.0.0 Safari/537.36')
"""
User agent.

:meta hide-value:
"""
SHARED_HEADERS = {
    'accept': '*/*',
    'authority': 'www.instagram.com',
    'cache-control': 'no-cache',
    'dnt': '1',
    'pragma': 'no-cache',
    'user-agent': USER_AGENT,
    # 'x-asbd-id': '359341',
    # 'x-ig-app-id': '936619743392459',
}
"""
Headers to use for requests.

:meta hide-value:
"""
API_HEADERS = {
    'x-asbd-id': '359341',
    'x-ig-app-id': '936619743392459',
}
"""
Headers to use for API requests.

:meta hide-value:
"""
PAGE_FETCH_HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
              'image/apng,*/*;q=0.8',
    'dpr': '1.5',
    'sec-fetch-mode': 'navigate',  # Definitely required.
    'viewport-width': '3840',
}
"""
Headers to use for fetching HTML pages.

:meta hide-value:
"""
LOG_SCHEMA = """CREATE TABLE log (
    url TEXT PRIMARY KEY NOT NULL,
    date TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL
);"""
"""
Schema for log database.

:meta hide-value:
"""
BROWSER_CHOICES = ('brave', 'chrome', 'chromium', 'edge', 'opera', 'vivaldi', 'firefox', 'safari')
"""
Possible browser choices to get cookies from.

:meta hide-value:
"""
