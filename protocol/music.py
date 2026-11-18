
"""Music models and serializers for Capsule Neo."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping


def _encode_flags(
    value: Mapping[str, Any] | str | None,
) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


@dataclass
class Track:
    """One audio item in a Capsule music queue."""

    url: str
    title: str = ""
    artist: str = ""
    duration: int | None = None

    # Full VK metadata. Can contain album, thumb, source, track_id, etc.
    meta: Mapping[str, Any] = field(default_factory=dict)

    # VK stat_flags are JSON strings in captured responses,
    # but accepting mappings is more convenient for callers.
    stat_flags: Mapping[str, Any] | str | None = None

    audio_hash: str | None = None
    cpp_hash: str | None = None
    position: int = 0

    liked: bool = False
    disliked: bool = False
    disliked_by_artist: bool = False
    in_user_playlist: bool = False

    media_type: int = 1
    kws_skip: Any = None
    autoplay: bool = True
    append: bool = False
    event_media_end: Any = None
    action_text: str = ""
    content_value: Mapping[str, Any] = field(default_factory=dict)
    need_vk_session: Any = None
    page_token: Any = None

    # Unknown track-level fields can be preserved without changing the model.
    extra: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        meta = dict(self.meta)

        if self.artist:
            meta.setdefault("artist", self.artist)
        if self.title:
            meta.setdefault("title", self.title)
        meta.setdefault("url", self.url)

        if self.duration is not None:
            meta.setdefault("duration", self.duration)

        flags = _encode_flags(self.stat_flags)

        # The captured protocol has stat_flags both inside meta
        # and at the track level.
        if flags is not None:
            meta["stat_flags"] = flags

        result: dict[str, Any] = {
            **dict(self.extra),
            "url": self.url,
            "meta": meta,
            "media_type": self.media_type,
            "kws_skip": self.kws_skip,
            "autoplay": self.autoplay,
            "append": self.append,
            "event_media_end": self.event_media_end,
            "action_text": self.action_text,
            "content_value": dict(self.content_value),
            "need_vk_session": self.need_vk_session,
            "page_token": self.page_token,
            "liked": self.liked,
            "disliked": self.disliked,
            "disliked_by_artist": self.disliked_by_artist,
            "in_user_playlist": self.in_user_playlist,
            "position": self.position,
        }

        if flags is not None:
            result["stat_flags"] = flags
        if self.audio_hash is not None:
            result["audio_hash"] = self.audio_hash
        if self.cpp_hash is not None:
            result["cpp_hash"] = self.cpp_hash

        return result


@dataclass
class Playlist:
    """A queue of tracks serialized as a Capsule 'playlist' command."""

    tracks: list[Track]

    player_type: str = "player"
    query: str = ""

    autoplay: bool = True
    append: bool = False
    seek_track: int = 0
    seek_second: int = 0

    tracks_type: str = "media"
    media_type: int = 1

    event_media_end: Any = None
    action_text: str = ""
    content_value: Mapping[str, Any] = field(default_factory=dict)
    need_vk_session: Any = None
    page_token: Any = None

    # Allows protocol fields discovered later to pass through unchanged.
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.tracks:
            raise ValueError("playlist must contain at least one track")

        # Ensure queue positions match their actual order.
        for index, track in enumerate(self.tracks):
            track.position = index

    def add(self, track: Track) -> "Playlist":
        track.position = len(self.tracks)
        self.tracks.append(track)
        return self

    def to_command(self) -> dict[str, Any]:
        return {
            **dict(self.extra),
            "tracks_type": self.tracks_type,
            "media_type": self.media_type,
            "seek_track": self.seek_track,
            "seek_second": self.seek_second,
            "tracks": [track.to_dict() for track in self.tracks],
            "autoplay": self.autoplay,
            "append": self.append,
            "event_media_end": self.event_media_end,
            "action_text": self.action_text,
            "content_value": dict(self.content_value),
            "need_vk_session": self.need_vk_session,
            "page_token": self.page_token,
            "player_type": self.player_type,
            "query": self.query,
            "type": "playlist",
            "length": len(self.tracks),
        }
