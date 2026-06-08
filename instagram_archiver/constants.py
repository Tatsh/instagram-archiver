"""Constants."""

from __future__ import annotations

__all__ = ('API_HEADERS', 'BROWSER_CHOICES', 'PAGE_FETCH_HEADERS', 'SHARED_HEADERS', 'USER_AGENT')

USER_AGENT = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/148.0.0.0 Safari/537.36')
"""
User agent.

Modern Chrome on Linux. Must be sent together with the matching ``Sec-CH-UA*`` client-hint
headers in :py:data:`SHARED_HEADERS`; Instagram's edge cross-references the two and serves the
React app shell (HTML) for ``/api/v1/media/<pk>/comments/`` and similar endpoints if they
disagree. The exact strings here are taken verbatim from a captured browser request that
Instagram successfully routed to the JSON API.

:meta hide-value:
"""
SHARED_HEADERS = {
    'accept': '*/*',
    'authority': 'www.instagram.com',
    'cache-control': 'no-cache',
    'dnt': '1',
    'pragma': 'no-cache',
    'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    'sec-ch-ua-full-version-list': ('"Chromium";v="148.0.7778.56", '
                                    '"Google Chrome";v="148.0.7778.56", '
                                    '"Not/A)Brand";v="99.0.0.0"'),
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-model': '""',
    'sec-ch-ua-platform': '"Linux"',
    'sec-ch-ua-platform-version': '""',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'user-agent': USER_AGENT
}
"""
Headers to use for requests.

The ``Sec-CH-UA*`` family must agree with :py:data:`USER_AGENT`. Instagram's edge runs a
``User-Agent`` ↔ client-hint consistency check on the ``/api/v1/...`` endpoints and falls back
to the React app shell (HTML) when they disagree. The strings here mirror a captured browser
request verbatim, including the GREASE entry and version-list ordering.

:meta hide-value:
"""
API_HEADERS = {'x-asbd-id': '359341', 'x-ig-app-id': '936619743392459'}
"""
Headers to use for API requests.

:meta hide-value:
"""
PAGE_FETCH_HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
              'image/apng,*/*;q=0.8',
    'dpr': '1.5',
    'sec-fetch-mode': 'navigate',  # Definitely required.
    'viewport-width': '3840'
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
