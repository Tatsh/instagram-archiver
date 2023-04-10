from typing import Any, Collection, TypedDict


class MediaInfoItemVideoVersion(TypedDict):
    height: int
    url: str
    width: int


class MediaInfoItemImageVersions2Candidate(TypedDict):
    height: int
    url: str
    width: int


class MediaInfoItemImageVersions2(TypedDict):
    candidates: Collection[MediaInfoItemImageVersions2Candidate]


class MediaInfoItem(TypedDict):
    image_versions2: MediaInfoItemImageVersions2
    taken_at: int
    user: Any
    video_dash_manifest: str
    video_duration: float
    video_versions: Collection[MediaInfoItemVideoVersion]
