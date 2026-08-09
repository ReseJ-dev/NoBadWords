"""Discovery helpers for FFmpeg command-line tools."""

from dataclasses import dataclass
from pathlib import Path
import shutil


class FFmpegNotFoundError(RuntimeError):
    """Raised when FFmpeg or FFprobe cannot be located."""


@dataclass(frozen=True, slots=True)
class FFmpegTools:
    """Resolved paths to the required media executables."""

    ffmpeg: Path
    ffprobe: Path


def find_executable(name: str) -> Path | None:
    """Return the executable found on PATH, if any."""
    resolved = shutil.which(name)
    return Path(resolved).resolve() if resolved else None


def discover_ffmpeg_tools() -> FFmpegTools:
    """Locate FFmpeg and FFprobe or raise an actionable error."""
    ffmpeg = find_executable("ffmpeg")
    ffprobe = find_executable("ffprobe")
    missing = [
        name
        for name, executable in (("FFmpeg", ffmpeg), ("FFprobe", ffprobe))
        if executable is None
    ]
    if missing:
        missing_names = " and ".join(missing)
        raise FFmpegNotFoundError(
            f"{missing_names} could not be found. Install FFmpeg and ensure its bin "
            "folder is available on PATH."
        )
    return FFmpegTools(ffmpeg=ffmpeg, ffprobe=ffprobe)

