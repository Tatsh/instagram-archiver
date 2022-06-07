from typing import Any, Mapping, Match, NoReturn, Optional, Sequence, Tuple


class InfoExtractor:
    @classmethod
    def _match_valid_url(cls, url: str) -> Match[str]:
        ...

    def _download_webpage_handle(self, url: str,
                                 video_id: str) -> Tuple[str, Any]:
        ...

    def report_warning(self, s: str) -> None:
        ...

    def _download_webpage(self,
                          url: str,
                          video_id: str,
                          note: Optional[str] = ...) -> str:
        ...

    def _download_json(self, url: str, video_id: str) -> Any:
        ...

    def _parse_json(self,
                    json_str: Optional[str],
                    video_id: str,
                    fatal: Optional[bool] = ...) -> Any:
        ...

    def _search_regex(self,
                      re: str,
                      content: str,
                      note: str,
                      default: Optional[str] = ...,
                      fatal: Optional[bool] = ...) -> Optional[str]:
        ...

    def raise_login_required(self, message: str) -> NoReturn:
        ...

    def _og_search_video_url(self,
                             webpage: str,
                             secure: Optional[bool] = ...) -> Optional[str]:
        ...

    def playlist_result(self, items: Sequence[Mapping[str,
                                                      Any]], video_id: str,
                        s: str, desc: Optional[str]) -> Mapping[str, Any]:
        ...

    def _parse_mpd_formats(self, *args: Any, **kwargs: Any) -> Sequence[Any]:
        ...

    def _parse_xml(self, dash: str, video_id: str) -> Any:
        ...

    def _sort_formats(self, *args: Any) -> None:
        ...

    def _og_search_thumbnail(self, webpage: str) -> Optional[str]:
        ...
