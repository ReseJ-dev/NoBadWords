"""FFprobe command construction and media metadata parsing."""

import json
import math
from pathlib import Path
import subprocess
from typing import Any, Mapping

from app.core.ffmpeg_utils import FFmpegTools, discover_ffmpeg_tools
from app.core.models import MediaInfo


class MediaInspectionError(RuntimeError):
    """Raised when media metadata cannot be read."""


def build_ffprobe_command(ffprobe: Path | str, media_path: Path) -> list[str]:
    """Build a safe FFprobe argument list for JSON metadata output."""
    return [
        str(ffprobe),
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(media_path),
    ]


def inspect_media(path: Path, tools: FFmpegTools | None = None) -> MediaInfo:
    """Inspect a media file with FFprobe."""
    resolved_tools = tools or discover_ffmpeg_tools()
    command = build_ffprobe_command(resolved_tools.ffprobe, path)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as error:
        raise MediaInspectionError(f"Could not start FFprobe: {error}") from error
    if result.returncode != 0:
        details = result.stderr.strip() or "FFprobe returned an unknown error."
        raise MediaInspectionError(f"Could not inspect the selected video: {details}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise MediaInspectionError("FFprobe returned invalid media information.") from error
    return parse_media_info(payload)


def parse_media_info(payload: Mapping[str, Any]) -> MediaInfo:
    """Convert FFprobe JSON data into a typed media model."""
    streams = payload.get("streams")
    if not isinstance(streams, list):
        raise MediaInspectionError("FFprobe output does not contain stream information.")

    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if not video_streams:
        raise MediaInspectionError("The selected file does not contain a video stream.")

    video = video_streams[0]
    audio = audio_streams[0] if audio_streams else None
    format_data = payload.get("format", {})
    duration_value = format_data.get("duration", video.get("duration"))
    try:
        duration = float(duration_value)
        width = int(video["width"])
        height = int(video["height"])
    except (KeyError, TypeError, ValueError) as error:
        raise MediaInspectionError("FFprobe output is missing required video metadata.") from error
    if not math.isfinite(duration) or duration <= 0 or width <= 0 or height <= 0:
        raise MediaInspectionError("FFprobe returned invalid video dimensions or duration.")

    frame_rate = _parse_frame_rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
    sample_rate = _parse_optional_int(audio.get("sample_rate")) if audio else None
    return MediaInfo(
        duration=duration,
        width=width,
        height=height,
        frame_rate=frame_rate,
        video_codec=str(video.get("codec_name") or "Unknown"),
        audio_codec=str(audio.get("codec_name") or "Unknown") if audio else None,
        audio_stream_count=len(audio_streams),
        sample_rate=sample_rate,
    )


def _parse_frame_rate(value: object) -> float:
    if not isinstance(value, str):
        return 0.0
    numerator, separator, denominator = value.partition("/")
    try:
        if separator:
            denominator_value = float(denominator)
            return float(numerator) / denominator_value if denominator_value else 0.0
        return float(numerator)
    except ValueError:
        return 0.0


def _parse_optional_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
