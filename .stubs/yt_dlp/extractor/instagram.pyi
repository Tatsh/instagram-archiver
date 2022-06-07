from typing import Any, Mapping, Sequence
from yt_dlp.extractor.common import InfoExtractor


class InstagramIE(InfoExtractor):
    def _extract_nodes(self, nodes: Sequence[Any],
                       b: bool) -> Sequence[Mapping[str, Any]]:
        ...
