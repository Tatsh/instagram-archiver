"""Typing helpers."""
# ruff: noqa: D101
from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ('BrowserName', 'CarouselMedia', 'Comments', 'Edge', 'HighlightsTray', 'MediaInfo',
           'MediaInfoItem', 'MediaInfoItemImageVersions2Candidate', 'WebProfileInfo',
           'XDTAPIV1FeedUserTimelineGraphQLConnectionContainer')


class MediaInfoItemVideoVersion(TypedDict):
    height: int
    url: str
    width: int


class MediaInfoItemImageVersions2Candidate(TypedDict):
    height: int
    url: str
    width: int


class HighlightItem(TypedDict):
    id: str


class HighlightsTray(TypedDict):
    tray: Sequence[HighlightItem]


class PageInfo(TypedDict):
    end_cursor: str
    has_next_page: bool


class EdgeOwnerToTimelineMedia(TypedDict):
    edges: Sequence[Edge]
    page_info: PageInfo


class UserInfo(TypedDict):
    edge_owner_to_timeline_media: EdgeOwnerToTimelineMedia
    id: str
    profile_pic_url_hd: str


class MediaInfoItemImageVersions2(TypedDict):
    candidates: Sequence[MediaInfoItemImageVersions2Candidate]


class CarouselMedia(TypedDict):
    image_versions2: MediaInfoItemImageVersions2
    id: str


class HasID(TypedDict):
    id: str


class MediaInfoItem(TypedDict):
    carousel_media: NotRequired[list[CarouselMedia]]
    image_versions2: MediaInfoItemImageVersions2
    id: str
    taken_at: int
    user: HasID
    video_dash_manifest: str
    video_duration: float
    video_versions: Sequence[MediaInfoItemVideoVersion]


class Comments(TypedDict):
    can_view_more_preview_comments: bool
    comments: list[HasID]
    next_min_id: str


class MediaInfo(TypedDict):
    more_available: bool
    num_results: int
    items: Sequence[MediaInfoItem]


class Owner(TypedDict):
    id: str
    username: str


class XDTMediaDict(TypedDict):
    __typename: Literal['XDTMediaDict']
    code: str
    id: str
    owner: Owner
    video_dash_manifest: str | None


class Edge(TypedDict):
    node: XDTMediaDict


class XDTAPIV1FeedUserTimelineGraphQLConnection(TypedDict):
    edges: Sequence[Edge]
    page_info: PageInfo


class XDTAPIV1FeedUserTimelineGraphQLConnectionContainer(TypedDict):
    xdt_api__v1__feed__user_timeline_graphql_connection: XDTAPIV1FeedUserTimelineGraphQLConnection


class WebProfileInfoData(TypedDict):
    user: UserInfo


class WebProfileInfo(TypedDict):
    data: WebProfileInfoData


BrowserName = Literal['brave', 'chrome', 'chromium', 'edge', 'firefox', 'opera', 'safari',
                      'vivaldi']
"""Possible browser choices to get cookies from."""
