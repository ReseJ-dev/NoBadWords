"""FFmpeg command construction and rendering for censorship exports."""

from collections.abc import Callable, Sequence
from pathlib import Path
import subprocess
from typing import Protocol

from app.core.ffmpeg_utils import FFmpegTools, discover_ffmpeg_tools
from app.core.models import (
    CensorInterval,
    CensorshipMode,
    ExportRequest,
    TimelineSegment,
)

ExportStatusCallback = Callable[[str], None]


class CensorExportError(RuntimeError):
    """Raised when an export request cannot be completed."""


class VideoExporter(Protocol):
    """Interface consumed by the background export worker."""

    def export(
        self,
        request: ExportRequest,
        status_callback: ExportStatusCallback | None = None,
    ) -> Path: ...


def interval_expression(intervals: Sequence[CensorInterval]) -> str:
    """Build a safe FFmpeg enable expression for censorship intervals."""
    if not intervals:
        return "0"
    return "+".join(
        f"between(t,{_number(interval.start)},{_number(interval.end)})"
        for interval in intervals
    )


def build_audio_filter(
    mode: CensorshipMode,
    intervals: Sequence[CensorInterval],
    media_duration: float,
    beep_frequency_hz: int = 1000,
    sample_rate: int = 48_000,
) -> str:
    """Build an audio filter graph for Mute or Beep mode."""
    expression = interval_expression(intervals)
    muted = f"[0:a:0]volume=0:enable='{expression}'[clean]"
    if mode == "Mute":
        return muted.removesuffix("[clean]") + "[aout]"
    if mode == "Beep":
        if not 100 <= beep_frequency_hz <= 20_000:
            raise ValueError("Beep frequency must be between 100 and 20000 Hz.")
        return (
            f"{muted};"
            f"sine=frequency={beep_frequency_hz}:sample_rate={sample_rate}:"
            f"duration={_number(media_duration)}[beep];"
            f"[beep]volume=0:enable='not({expression})'[tone];"
            "[clean][tone]amix=inputs=2:duration=first:dropout_transition=0:"
            "normalize=0[aout]"
        )
    raise ValueError(f"Audio filter mode is not supported: {mode}")


def build_keep_segments(
    intervals: Sequence[CensorInterval], media_duration: float
) -> list[TimelineSegment]:
    """Return the synchronized source segments left after all cuts."""
    if media_duration <= 0:
        raise ValueError("Media duration must be greater than zero.")
    ranges = sorted((interval.start, interval.end) for interval in intervals)
    for start, end in ranges:
        if start < 0 or end <= start or end > media_duration:
            raise ValueError("Cut intervals must be within the media duration.")

    merged: list[tuple[float, float]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    retained: list[TimelineSegment] = []
    source_cursor = 0.0
    output_cursor = 0.0
    for cut_start, cut_end in merged:
        if cut_start > source_cursor:
            duration = cut_start - source_cursor
            retained.append(
                TimelineSegment(
                    source_start=source_cursor,
                    source_end=cut_start,
                    output_start=output_cursor,
                    output_end=output_cursor + duration,
                )
            )
            output_cursor += duration
        source_cursor = max(source_cursor, cut_end)
    if source_cursor < media_duration:
        duration = media_duration - source_cursor
        retained.append(
            TimelineSegment(
                source_start=source_cursor,
                source_end=media_duration,
                output_start=output_cursor,
                output_end=output_cursor + duration,
            )
        )
    return retained


def build_cut_filter(
    intervals: Sequence[CensorInterval], media_duration: float
) -> str:
    """Build synchronized trim and concat filters for Cut mode."""
    segments = build_keep_segments(intervals, media_duration)
    if not segments:
        raise CensorExportError("The selected cuts would remove the entire video.")
    filters: list[str] = []
    concat_inputs: list[str] = []
    for index, segment in enumerate(segments):
        start = _number(segment.source_start)
        end = _number(segment.source_end)
        filters.extend(
            (
                f"[0:v:0]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{index}]",
                f"[0:a:0]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{index}]",
            )
        )
        concat_inputs.append(f"[v{index}][a{index}]")
    filters.append(
        "".join(concat_inputs)
        + f"concat=n={len(segments)}:v=1:a=1[vout][aout]"
    )
    return ";".join(filters)


def build_export_command(ffmpeg: Path | str, request: ExportRequest) -> list[str]:
    """Build a safe FFmpeg argument list for a censorship export."""
    _validate_request(request)
    base = [str(ffmpeg), "-hide_banner", "-n", "-i", str(request.input_path)]
    if not request.intervals:
        return base + [
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-c",
            "copy",
            str(request.output_path),
        ]
    if request.mode == "Cut":
        return base + [
            "-filter_complex",
            build_cut_filter(request.intervals, request.media_duration),
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(request.output_path),
        ]
    audio_filter = build_audio_filter(
        request.mode,
        request.intervals,
        request.media_duration,
        request.beep_frequency_hz,
    )
    return base + [
        "-filter_complex",
        audio_filter,
        "-map",
        "0:v:0",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(request.output_path),
    ]


class CensorEngine:
    """Render Mute, Beep, and Cut exports with FFmpeg."""

    def __init__(self, tools: FFmpegTools | None = None) -> None:
        self._tools = tools

    def export(
        self,
        request: ExportRequest,
        status_callback: ExportStatusCallback | None = None,
    ) -> Path:
        notify = status_callback or (lambda status: None)
        notify("Preparing filters")
        tools = self._tools or discover_ffmpeg_tools()
        command = build_export_command(tools.ffmpeg, request)
        notify("Rendering video")
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
            raise CensorExportError(f"Could not start FFmpeg: {error}") from error
        if result.returncode != 0:
            details = result.stderr.strip() or "FFmpeg returned an unknown error."
            raise CensorExportError(f"Video export failed: {details}")
        notify("Finalizing output")
        return request.output_path


def _validate_request(request: ExportRequest) -> None:
    if request.mode not in ("Mute", "Beep", "Cut"):
        raise CensorExportError(f"Unsupported censorship mode: {request.mode}")
    if not request.input_path.is_file():
        raise CensorExportError("The source video no longer exists.")
    if request.input_path.resolve() == request.output_path.resolve():
        raise CensorExportError("The source video cannot be overwritten.")
    if request.output_path.exists():
        raise CensorExportError("The output file already exists. Choose another name.")
    if request.media_duration <= 0:
        raise CensorExportError("The media duration must be greater than zero.")
    if any(
        interval.start < 0
        or interval.end <= interval.start
        or interval.end > request.media_duration
        for interval in request.intervals
    ):
        raise CensorExportError("Censorship intervals must be within the media duration.")


def _number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"
