"""FFmpeg command construction and rendering for censorship exports."""

from collections.abc import Callable, Sequence
from pathlib import Path
import subprocess
import threading
from typing import Protocol

from app.core.cancellation import CancellationToken, OperationCancelled
from app.core.ffmpeg_utils import FFmpegTools, discover_ffmpeg_tools
from app.core.models import (
    CensorInterval,
    CensorshipMode,
    ExportRequest,
    TimelineSegment,
)

ExportStatusCallback = Callable[[str], None]
ExportProgressCallback = Callable[[float], None]


class CensorExportError(RuntimeError):
    """Raised when an export request cannot be completed."""


class VideoExporter(Protocol):
    """Interface consumed by the background export worker."""

    def export(
        self,
        request: ExportRequest,
        status_callback: ExportStatusCallback | None = None,
        cancellation_token: CancellationToken | None = None,
        progress_callback: ExportProgressCallback | None = None,
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
    stream_index: int = 0,
    output_label: str = "aout",
) -> str:
    """Build an audio filter graph for Mute or Beep mode."""
    expression = interval_expression(intervals)
    clean_label = "clean" if stream_index == 0 else f"clean{stream_index}"
    muted = f"[0:a:{stream_index}]volume=0:enable='{expression}'[{clean_label}]"
    if mode == "Mute":
        return muted.removesuffix(f"[{clean_label}]") + f"[{output_label}]"
    if mode == "Beep":
        if not 100 <= beep_frequency_hz <= 20_000:
            raise ValueError("Beep frequency must be between 100 and 20000 Hz.")
        beep_label = "beep" if stream_index == 0 else f"beep{stream_index}"
        tone_label = "tone" if stream_index == 0 else f"tone{stream_index}"
        return (
            f"{muted};"
            f"sine=frequency={beep_frequency_hz}:sample_rate={sample_rate}:"
            f"duration={_number(media_duration)}[{beep_label}];"
            f"[{beep_label}]volume=0:enable='not({expression})'[{tone_label}];"
            f"[{clean_label}][{tone_label}]amix=inputs=2:duration=first:"
            f"dropout_transition=0:normalize=0[{output_label}]"
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
    intervals: Sequence[CensorInterval], media_duration: float,
    audio_stream_count: int = 1,
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
        filters.append(
            f"[0:v:0]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{index}]"
        )
        audio_inputs = ""
        for audio_index in range(audio_stream_count):
            label = f"a{audio_index}_{index}" if audio_stream_count > 1 else f"a{index}"
            filters.append(
                f"[0:a:{audio_index}]atrim=start={start}:end={end},"
                f"asetpts=PTS-STARTPTS[{label}]"
            )
            audio_inputs += f"[{label}]"
        concat_inputs.append(f"[v{index}]{audio_inputs}")
    output_labels = "".join(
        f"[aout{index}]" if audio_stream_count > 1 else "[aout]"
        for index in range(audio_stream_count)
    )
    filters.append(
        "".join(concat_inputs)
        + f"concat=n={len(segments)}:v=1:a={audio_stream_count}[vout]{output_labels}"
    )
    return ";".join(filters)


def build_export_command(ffmpeg: Path | str, request: ExportRequest) -> list[str]:
    """Build a safe FFmpeg argument list for a censorship export."""
    _validate_request(request)
    base = [str(ffmpeg), "-hide_banner", "-n", "-i", str(request.input_path)]
    progress = ["-progress", "pipe:1", "-nostats"]
    if not request.intervals:
        return base + [
            "-map",
            "0",
            "-c",
            "copy",
        ] + progress + [str(request.output_path)]
    if request.mode == "Cut":
        return base + [
            "-filter_complex",
            build_cut_filter(
                request.intervals, request.media_duration, request.audio_stream_count
            ),
            "-map",
            "[vout]",
        ] + _audio_map_arguments(request.audio_stream_count) + [
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
        ] + progress + [str(request.output_path)]
    if request.audio_stream_count == 0:
        raise CensorExportError("Mute and Beep require a source audio stream.")
    audio_filter = ";".join(
        build_audio_filter(
            request.mode, request.intervals, request.media_duration,
            request.beep_frequency_hz, stream_index=index,
            output_label="aout" if request.audio_stream_count == 1 else f"aout{index}",
        )
        for index in range(request.audio_stream_count)
    )
    return base + [
        "-filter_complex",
        audio_filter,
        "-map",
        "0:v:0",
    ] + _audio_map_arguments(request.audio_stream_count) + [
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
    ] + progress + [str(request.output_path)]


class CensorEngine:
    """Render Mute, Beep, and Cut exports with FFmpeg."""

    def __init__(self, tools: FFmpegTools | None = None) -> None:
        self._tools = tools

    def export(
        self,
        request: ExportRequest,
        status_callback: ExportStatusCallback | None = None,
        cancellation_token: CancellationToken | None = None,
        progress_callback: ExportProgressCallback | None = None,
    ) -> Path:
        notify = status_callback or (lambda status: None)
        token = cancellation_token or CancellationToken()
        token.raise_if_cancelled()
        notify("Preparing filters")
        tools = self._tools or discover_ffmpeg_tools()
        command = build_export_command(tools.ffmpeg, request)
        token.raise_if_cancelled()
        notify("Rendering video")
        process: subprocess.Popen[str] | None = None
        terminate_callback: Callable[[], None] | None = None
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            terminate_callback = lambda: _terminate_process(process)
            token.add_callback(terminate_callback)
            stderr_lines: list[str] = []
            stderr_thread = threading.Thread(
                target=_collect_stream, args=(process.stderr, stderr_lines), daemon=True
            )
            stderr_thread.start()
            duration = _output_duration(request)
            if process.stdout is not None:
                for line in process.stdout:
                    token.raise_if_cancelled()
                    progress = parse_ffmpeg_progress(line, duration)
                    if progress is not None and progress_callback is not None:
                        progress_callback(progress)
            process.wait()
            stderr_thread.join(timeout=1)
            stderr = "".join(stderr_lines)
            token.raise_if_cancelled()
        except OSError as error:
            _cleanup_incomplete_output(request)
            raise CensorExportError(f"Could not start FFmpeg: {error}") from error
        except OperationCancelled:
            _cleanup_incomplete_output(request)
            raise
        finally:
            if terminate_callback is not None:
                token.remove_callback(terminate_callback)
        if process.returncode != 0:
            _cleanup_incomplete_output(request)
            details = stderr.strip() or "FFmpeg returned an unknown error."
            raise CensorExportError(f"Video export failed: {details}")
        notify("Finalizing output")
        try:
            token.raise_if_cancelled()
        except OperationCancelled:
            _cleanup_incomplete_output(request)
            raise
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
    if request.audio_stream_count < 0:
        raise CensorExportError("Audio stream count cannot be negative.")


def _audio_map_arguments(count: int) -> list[str]:
    arguments: list[str] = []
    for index in range(count):
        label = "[aout]" if count == 1 else f"[aout{index}]"
        arguments.extend(("-map", label))
    return arguments


def _number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


def parse_ffmpeg_progress(line: str, duration: float) -> float | None:
    """Return a normalized value for an FFmpeg progress output line."""
    key, separator, value = line.strip().partition("=")
    if not separator or duration <= 0:
        return None
    if key == "progress" and value == "end":
        return 1.0
    if key not in {"out_time_us", "out_time_ms"}:
        return None
    try:
        # FFmpeg currently reports both fields in microseconds despite the legacy name.
        elapsed = float(value) / 1_000_000
    except ValueError:
        return None
    return max(0.0, min(1.0, elapsed / duration))


def _output_duration(request: ExportRequest) -> float:
    if request.mode != "Cut":
        return request.media_duration
    return sum(
        segment.source_end - segment.source_start
        for segment in build_keep_segments(request.intervals, request.media_duration)
    )


def _collect_stream(stream: object, lines: list[str]) -> None:
    if stream is not None:
        lines.extend(stream)  # type: ignore[arg-type]


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
    except OSError:
        return

    def kill_if_running() -> None:
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass

    timer = threading.Timer(2.0, kill_if_running)
    timer.daemon = True
    timer.start()


def _cleanup_incomplete_output(request: ExportRequest) -> None:
    try:
        request.output_path.unlink(missing_ok=True)
    except OSError:
        pass
