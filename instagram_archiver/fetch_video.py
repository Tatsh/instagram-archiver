from os import chdir
from pathlib import Path
from typing import Optional, Sequence, Union
import sys

from loguru import logger
import click
import yt_dlp

from .constants import SHARED_HEADERS
from .extractor import ImprovedInstagramIE
from .utils import YoutubeDLLogger


@click.command()
@click.option('-o',
              '--output-dir',
              default=None,
              help='Output directory',
              type=click.Path(exists=True))
@click.option('-d', '--debug', is_flag=True, help='Enable debug output')
@click.argument('urls', required=True, nargs=-1)
def main(output_dir: Optional[Union[Path, str]],
         urls: Sequence[str],
         debug: bool = False):
    if output_dir:
        chdir(output_dir)
    sys.argv = [sys.argv[0]]
    ydl_opts = yt_dlp.parse_options()[-1]
    with yt_dlp.YoutubeDL({
            **ydl_opts,
            **dict(http_headers=SHARED_HEADERS,
                   logger=YoutubeDLLogger(),
                   verbose=debug)
    }) as ydl:
        ydl.add_info_extractor(ImprovedInstagramIE())
        failed_urls = []
        for url in urls:
            if not ydl.extract_info(url, ie_key='ImprovedInstagram'):
                failed_urls.append(url)
        if len(failed_urls) > 0:
            logger.error('Failed URLS:')
            for url in failed_urls:
                logger.error(f'  {url}')
