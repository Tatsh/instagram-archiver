"""Constants."""
from __future__ import annotations

__all__ = ('BROWSER_CHOICES', 'SHARED_HEADERS', 'USER_AGENT')

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
    'x-asbd-id': '359341',
    'x-ig-app-id': '936619743392459',
}
"""
Headers to use for requests.

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
