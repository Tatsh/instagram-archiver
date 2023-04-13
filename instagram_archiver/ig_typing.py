# pylint: disable=unused-private-member
from typing import Literal, Sequence, TypedDict

from typing_extensions import NotRequired


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


class GraphVideoNode(TypedDict):
    __typename: Literal['GraphVideo']
    id: str
    shortcode: NotRequired[str]


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
