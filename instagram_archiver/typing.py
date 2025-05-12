"""Typing helpers."""
# ruff: noqa: D101
from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ('BrowserName', 'CarouselMedia', 'Comments', 'Edge', 'HasID', 'HighlightsTray',
           'MediaInfo', 'MediaInfoItem', 'MediaInfoItemImageVersions2Candidate', 'UserInfo',
           'WebProfileInfo', 'WebProfileInfoData', 'XDTAPIV1FeedUserTimelineGraphQLConnection',
           'XDTAPIV1FeedUserTimelineGraphQLConnectionContainer', 'XDTMediaDict')


class MediaInfoItemVideoVersion(TypedDict):
    height: int
    url: str
    width: int


class MediaInfoItemImageVersions2Candidate(TypedDict):
    height: int
    """Height of the image."""
    url: str
    """URL of the image."""
    width: int
    """Width of the image."""


class HighlightItem(TypedDict):
    id: str
    """Identifier."""


class HighlightsTray(TypedDict):
    tray: Sequence[HighlightItem]
    """Highlights tray items."""


class PageInfo(TypedDict):
    end_cursor: str
    """End cursor for pagination."""
    has_next_page: bool
    """Whether there are more pages."""


class EdgeOwnerToTimelineMedia(TypedDict):
    edges: Sequence[Edge]
    page_info: PageInfo
    """Pagination information."""


class UserInfo(TypedDict):
    """User information."""
    edge_owner_to_timeline_media: EdgeOwnerToTimelineMedia
    """Timeline media edge."""
    id: str
    """User ID."""
    profile_pic_url_hd: str
    """Profile picture URL."""


class MediaInfoItemImageVersions2(TypedDict):
    candidates: Sequence[MediaInfoItemImageVersions2Candidate]
    """Image versions."""


class CarouselMedia(TypedDict):
    image_versions2: MediaInfoItemImageVersions2
    """Image versions."""
    id: str
    """Identifier."""


class HasID(TypedDict):
    """Dictionary with an ``id`` field."""
    id: str
    """Identifier."""


class MediaInfoItem(TypedDict):
    """Media information item."""
    carousel_media: NotRequired[Sequence[CarouselMedia] | None]
    """Carousel media items."""
    image_versions2: MediaInfoItemImageVersions2
    """Image versions."""
    id: str
    """Identifier."""
    taken_at: int
    """Timestamp when the media was taken"""
    user: HasID
    """User who posted the media."""
    video_dash_manifest: NotRequired[str | None]
    """URL of the video dash manifest."""
    video_duration: float
    """Duration of the video in seconds."""
    video_versions: Sequence[MediaInfoItemVideoVersion]
    """Video versions."""


class Comments(TypedDict):
    """Comments container."""
    can_view_more_preview_comments: bool
    """Whether more preview comments can be viewed."""
    comments: Sequence[HasID]
    """List of comments."""
    next_min_id: str
    """Next minimum ID for pagination."""


class MediaInfo(TypedDict):
    """Media information."""
    items: Sequence[MediaInfoItem]
    """List of media items."""


class Owner(TypedDict):
    id: str
    """Owner ID."""
    username: str
    """Owner username."""


class XDTMediaDict(TypedDict):
    __typename: Literal['XDTMediaDict']
    """Type name."""
    code: str
    """Short code."""
    id: str
    """Media ID."""
    owner: Owner
    """Owner information."""
    pk: str
    """Primary key. Also carousel ID."""
    video_dash_manifest: NotRequired[str | None]
    """Video dash manifest URL, if available."""


class Edge(TypedDict):
    """Edge of a graph."""
    node: XDTMediaDict
    """Node at this edge."""


class XDTAPIV1FeedUserTimelineGraphQLConnection(TypedDict):
    edges: Sequence[Edge]
    """Edges of the graph."""
    page_info: PageInfo
    """Pagination information."""


class XDTAPIV1FeedUserTimelineGraphQLConnectionContainer(TypedDict):
    """Container for :py:class:`XDTAPIV1FeedUserTimelineGraphQLConnection`."""
    xdt_api__v1__feed__user_timeline_graphql_connection: XDTAPIV1FeedUserTimelineGraphQLConnection
    """User timeline data."""


class WebProfileInfoData(TypedDict):
    user: UserInfo
    """User information."""


class WebProfileInfo(TypedDict):
    """Profile information container."""
    data: WebProfileInfoData
    """Profile data."""


BrowserName = Literal['brave', 'chrome', 'chromium', 'edge', 'firefox', 'opera', 'safari',
                      'vivaldi']
"""Possible browser choices to get cookies from."""
