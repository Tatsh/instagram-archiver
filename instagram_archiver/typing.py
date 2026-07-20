"""Typing helpers."""

# ruff:file-ignore[undocumented-public-class]
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, TypedDict

from archiver_stats import Category, Stats as _BaseStats, StatusLine
from typing_extensions import NotRequired

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = ('COMMENTS_PROCESSED', 'IMAGES_PROCESSED', 'POSTS_HANDLED', 'VIDEOS_PROCESSED',
           'YT_DLP_STATUS', 'BrowserName', 'CarouselMedia', 'ChildCommentsPage', 'Comments', 'Edge',
           'HasID', 'HighlightsTray', 'MediaInfo', 'MediaInfoItem',
           'MediaInfoItemImageVersions2Candidate', 'OnMessage', 'Stats', 'StoryReel',
           'StoryReelEdge', 'StoryReelItem', 'UserInfo', 'WebProfileInfo', 'WebProfileInfoData',
           'XDTAPIV1FeedUserTimelineGraphQLConnection',
           'XDTAPIV1FeedUserTimelineGraphQLConnectionContainer', 'XDTMediaDict',
           'XDTStoriesV3ReelPageGalleryConnection', 'XDTStoriesV3ReelPageGalleryQueryResponse',
           'YTDLPState')

OnMessage: TypeAlias = Callable[[str], None]
"""Callback used to report human-readable progress updates."""

COMMENTS_PROCESSED = 'comments_processed'
"""Counter key for posts whose comments have been saved successfully.

:meta hide-value:
"""
IMAGES_PROCESSED = 'images_processed'
"""Counter key for image posts that have been saved successfully.

:meta hide-value:
"""
POSTS_HANDLED = 'posts_handled'
"""Counter key for posts routed by the producer.

:meta hide-value:
"""
VIDEOS_PROCESSED = 'videos_processed'
"""Counter key for video URLs handed to yt-dlp successfully.

:meta hide-value:
"""
YT_DLP_STATUS = 'yt_dlp_status'
"""Status-line key for the current yt-dlp URL.

:meta hide-value:
"""


class Stats(_BaseStats):
    """Live pipeline statistics shown in the progress spinner."""
    def __init__(self) -> None:
        super().__init__((Category(
            POSTS_HANDLED, 'Total posts fetched:'), Category(
                IMAGES_PROCESSED, 'Image posts:'), Category(VIDEOS_PROCESSED, 'Videos handled:'),
                          Category(COMMENTS_PROCESSED, 'Comment threads:')),
                         status_lines=(StatusLine(YT_DLP_STATUS, 'yt-dlp processing:',
                                                  POSTS_HANDLED),))


@dataclass
class YTDLPState:
    """Mutable yt-dlp progress state shared between the producer and the yt-dlp worker."""

    current_index: int = 0
    """1-based index of the URL currently being processed."""
    current_url: str | None = None
    """URL yt-dlp is currently downloading, or ``None`` when idle."""
    total_urls: int = 0
    """Running total of URLs enqueued for the yt-dlp worker."""
    def render(self) -> str | None:
        """
        Build the :py:data:`YT_DLP_STATUS` value from the current state.

        Returns
        -------
        str | None
            Rendered status string, or ``None`` when no URL is active.
        """
        if self.current_url is None or self.total_urls == 0:
            return None
        return f'{self.current_url} ({self.current_index}/{self.total_urls})'


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


class ChildCommentsPage(TypedDict):
    """One page of replies under a top-level comment."""

    child_comments: Sequence[Mapping[str, Any]]
    """Replies returned on this page."""
    has_more_head_child_comments: NotRequired[bool]
    """Whether more replies exist forward of the current cursor."""
    has_more_tail_child_comments: NotRequired[bool]
    """Whether more replies exist behind the current cursor."""
    next_min_id: NotRequired[str]
    """Cursor for fetching the next page when paging forward."""


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


class StoryReelItem(TypedDict):
    """A single story media item inside a reel."""

    code: NotRequired[str]
    """Optional shortcode of the story item."""
    id: str
    """Identifier."""
    image_versions2: NotRequired[MediaInfoItemImageVersions2]
    """Image versions, when the item carries a still image."""
    media_type: NotRequired[int]
    """Instagram media type (1=image, 2=video, etc)."""
    pk: str
    """Primary key."""
    taken_at: int
    """Timestamp when the media was taken."""
    user: NotRequired[HasID]
    """User who posted the story."""
    video_dash_manifest: NotRequired[str | None]
    """Video DASH manifest URL, if available."""
    video_versions: NotRequired[Sequence[MediaInfoItemVideoVersion]]
    """Video versions, if the item is a video."""


class StoryReel(TypedDict):
    """A reel (collection of story items belonging to a single user/highlight)."""

    id: str
    """Reel identifier (numeric user ID for stories, numeric highlight ID for highlights)."""
    items: Sequence[StoryReelItem]
    """Story items contained in this reel."""
    user: NotRequired[HasID]
    """Owner of the reel."""


class StoryReelEdge(TypedDict):
    """Edge wrapping a :py:class:`StoryReel`."""

    node: StoryReel
    """Node at this edge."""


class XDTStoriesV3ReelPageGalleryConnection(TypedDict):
    """Connection for the PolarisStoriesV3 reel page gallery query."""

    edges: Sequence[StoryReelEdge]
    """Edges of the connection."""
    page_info: PageInfo
    """Pagination information."""


class XDTStoriesV3ReelPageGalleryQueryResponse(TypedDict):
    """Container for :py:class:`XDTStoriesV3ReelPageGalleryConnection`."""

    xdt_api__v1__feed__reels_media: XDTStoriesV3ReelPageGalleryConnection
    """Reels media connection payload."""


class WebProfileInfoData(TypedDict):
    user: UserInfo
    """User information."""


class WebProfileInfo(TypedDict):
    """Profile information container."""

    data: NotRequired[WebProfileInfoData]
    """Profile data."""


BrowserName = Literal['brave', 'chrome', 'chromium', 'edge', 'firefox', 'opera', 'safari',
                      'vivaldi']
"""Possible browser choices to get cookies from."""
