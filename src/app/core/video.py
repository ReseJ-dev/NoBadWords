"""Video file validation and display helpers."""

from pathlib import Path

SUPPORTED_VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
)


def is_supported_video(path: str | Path) -> bool:
    """Return whether a path has a supported video extension."""
    return Path(path).suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS


def format_file_size(size_bytes: int) -> str:
    """Format a byte count for display to the user."""
    size = float(size_bytes)
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    raise AssertionError("unreachable")

