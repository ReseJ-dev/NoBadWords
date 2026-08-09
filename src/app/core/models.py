"""Shared data models for the desktop application."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class VideoFile:
    """A video selected in the desktop application."""

    path: Path
    size_bytes: int
    duration_seconds: float | None = None

    @classmethod
    def from_path(cls, path: Path) -> "VideoFile":
        """Create video metadata from a local file without probing media."""
        resolved_path = path.expanduser().resolve()
        return cls(path=resolved_path, size_bytes=resolved_path.stat().st_size)


@dataclass(slots=True)
class ApplicationState:
    """Mutable state shared by the desktop workflow."""

    selected_video: VideoFile | None = None
    media_info: "MediaInfo | None" = None


@dataclass(frozen=True, slots=True)
class MediaInfo:
    """Technical metadata reported by FFprobe for a media file."""

    duration: float
    width: int
    height: int
    frame_rate: float
    video_codec: str
    audio_codec: str | None
    audio_stream_count: int
    sample_rate: int | None

