"""Shared data models for the desktop application."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Language = Literal["Russian", "English", "Auto"]
WhisperModel = Literal["tiny", "base", "small", "medium", "large-v3"]
Device = Literal["Auto", "CPU", "CUDA"]
CensorshipMode = Literal["Beep", "Mute", "Cut"]


@dataclass(frozen=True, slots=True)
class ScanSettings:
    """User-configurable speech scan and censorship preferences."""

    language: Language = "Russian"
    whisper_model: WhisperModel = "base"
    device: Device = "Auto"
    censorship_mode: CensorshipMode = "Beep"
    confidence: float = 0.65
    pre_padding_ms: int = 120
    post_padding_ms: int = 180
    beep_frequency_hz: int = 1000


@dataclass(frozen=True, slots=True)
class WordTimestamp:
    """One transcribed word and its media timestamps."""

    word: str
    start: float
    end: float
    confidence: float


@dataclass(frozen=True, slots=True)
class ProfanityMatch:
    """A profanity rule matched to a word-level timestamp."""

    original_word: str
    normalized_word: str
    start: float
    end: float
    confidence: float
    matched_rule: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class ScanResult:
    """Complete backend result of a speech scan."""

    words: list[WordTimestamp]
    matches: list[ProfanityMatch]


@dataclass(frozen=True, slots=True)
class CensorInterval:
    """A safe media interval containing one or more matched detections."""

    start: float
    end: float
    matches: tuple[ProfanityMatch, ...]


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
    scan_settings: ScanSettings = field(default_factory=ScanSettings)
    word_timestamps: list[WordTimestamp] = field(default_factory=list)
    profanity_matches: list[ProfanityMatch] = field(default_factory=list)
    censor_intervals: list[CensorInterval] = field(default_factory=list)


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
