# pylint: disable=unused-private-member
from typing import Any, Literal, Sequence, TypedDict

from typing_extensions import NotRequired

__all__ = ('BrowserName', 'CarouselMedia', 'Comments', 'Edge', 'EdgeMediaToComment',
           'EdgeOwnerToTimelineMedia', 'EdgeOwnerToTimelineMediaPageInfo', 'EdgeSidecarToChildren',
           'GraphImageNode', 'GraphNodeOwner', 'GraphSidecarNode', 'GraphVideoNode',
           'GraphVideoNodeVideoDimensions', 'HasID', 'HighlightItem', 'HighlightsTray', 'MediaInfo',
           'MediaInfoItem', 'MediaInfoItemImageVersions2', 'MediaInfoItemImageVersions2Candidate',
           'MediaInfoItemVideoVersion', 'UserInfo', 'WebProfileInfo', 'WebProfileInfoData')


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


class EdgeOwnerToTimelineMediaPageInfo(TypedDict):
    end_cursor: str
    has_next_page: bool


class EdgeOwnerToTimelineMedia(TypedDict):
    edges: Sequence['Edge']
    page_info: EdgeOwnerToTimelineMediaPageInfo


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


class EdgeSidecarToChildren(TypedDict):
    edges: Sequence['Edge']


class EdgeMediaToComment(TypedDict):
    count: int


class Comments(TypedDict):
    can_view_more_preview_comments: bool
    comments: list[HasID]
    next_min_id: str


class MediaInfo(TypedDict):
    more_available: bool
    num_results: int
    items: Sequence[MediaInfoItem]


class GraphSidecarNode(TypedDict):
    __typename: Literal['GraphSidecar']
    comments_disabled: bool
    edge_media_to_comment: EdgeMediaToComment
    edge_sidecar_to_children: EdgeSidecarToChildren
    id: str
    shortcode: NotRequired[str]


class GraphVideoNodeVideoDimensions(TypedDict):
    height: int
    width: int


class GraphNodeOwner(TypedDict):
    id: str
    username: str


class GraphVideoNode(TypedDict):
    __typename: Literal['GraphVideo']
    accessibility_caption: Any
    clips_music_attribution_info: NotRequired[Any]
    coauthor_producers: Sequence[Any]
    comments_disabled: bool
    dash_info: Any
    dimensions: GraphVideoNodeVideoDimensions
    display_url: str
    edge_liked_by: EdgeMediaToComment
    edge_media_caption: Any
    edge_media_preview_like: EdgeMediaToComment
    edge_media_to_comment: EdgeMediaToComment
    edge_media_to_tagged_user: Any
    fact_check_information: Any
    fact_check_overall_rating: Any
    felix_profile_grid_crop: Any
    gating_info: Any
    has_audio: bool
    has_upcoming_event: bool
    id: str
    is_video: Literal[True]
    location: Any
    media_overlay_info: Any
    media_preview: Any
    nft_asset_info: Any
    owner: GraphNodeOwner
    pinned_for_users: Sequence[Any]
    product_type: str
    sharing_friction_info: Any
    shortcode: NotRequired[str]
    taken_at_timestamp: int
    thumbnail_resources: Sequence[Any]
    thumbnail_src: str
    tracking_token: str
    video_url: str
    video_view_count: int
    viewer_can_reshare: bool


class GraphImageNode(TypedDict):
    __typename: Literal['GraphImage']
    id: str
    shortcode: NotRequired[str]


class Edge(TypedDict):
    node: GraphSidecarNode | GraphImageNode | GraphVideoNode


class WebProfileInfoData(TypedDict):
    user: UserInfo


class WebProfileInfo(TypedDict):
    data: WebProfileInfoData


BrowserName = Literal['brave', 'chrome', 'chromium', 'edge', 'firefox', 'opera', 'safari',
                      'vivaldi']
