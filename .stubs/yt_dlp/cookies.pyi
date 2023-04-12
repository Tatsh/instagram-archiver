from http.cookiejar import Cookie
from typing import Any, Collection

def extract_cookies_from_browser(browser: str,
                                 profile: str = ...,
                                 logger: Any = ...,
                                 *,
                                 keyring: Any = ...) -> Collection[Cookie]:
    ...
