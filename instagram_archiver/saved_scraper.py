"""Saved posts scraper."""
from __future__ import annotations

from contextlib import chdir
from pathlib import Path
from typing import TYPE_CHECKING, Any
import logging

from .client import InstagramClient
from .constants import API_HEADERS, PAGE_FETCH_HEADERS
from .utils import SaveCommentsCheckDisabledMixin

if TYPE_CHECKING:

    from collections.abc import Iterable

    from .typing import BrowserName

__all__ = ('SavedScraper',)
log = logging.getLogger(__name__)


class SavedScraper(SaveCommentsCheckDisabledMixin, InstagramClient):
    """Scrape saved posts."""
    def __init__(
        self,
        browser: BrowserName = 'chrome',
        browser_profile: str = 'Default',
        output_dir: str | Path | None = None,
        *,
        comments: bool = False,
    ) -> None:
        """
        Initialise ``SavedScraper``.

        Parameters
        ----------
        browser : BrowserName
            The browser to use.
        browser_profile : str
            The browser profile to use.
        output_dir : str | Path | None
            The output directory to save the posts to.
        comments : bool
            Whether to save comments or not.
        """
        super().__init__(browser, browser_profile)
        self._output_dir = Path(output_dir or Path.cwd() / '@@saved-posts@@')
        Path(self._output_dir).mkdir(parents=True, exist_ok=True)
        self.should_save_comments = comments

    def unsave(self, items: Iterable[str]) -> None:
        """Unsave saved posts."""
        for item in items:
            log.info('Unsaving %s.', item)
            self.session.post(f'https://www.instagram.com/web/save/{item}/unsave/',
                              headers=API_HEADERS)

    def process(self, *, unsave: bool = False) -> None:
        """Process the saved posts."""
        with chdir(self._output_dir):
            self.add_csrf_token_header()
            self.session.get('https://www.instagram.com/', headers=PAGE_FETCH_HEADERS)
            feed = self.get_json('https://www.instagram.com/api/v1/feed/saved/posts/',
                                 cast_to=dict[str, Any])
            self.save_edges({
                'node': {
                    '__typename': 'XDTMediaDict',
                    'id': item['media']['id'],
                    'code': item['media']['code'],
                    'owner': item['media']['owner'],
                    'pk': item['media']['pk'],
                    'video_dash_manifest': item['media'].get('video_dash_manifest')
                }
            } for item in feed['items'])
            if unsave:
                self.unsave(item['media']['code'] for item in feed['items'])
            if feed.get('more_available'):
                log.warning('Unhandled pagination.')
