"""Tests for synchronized Cut-mode timeline and FFmpeg construction."""

from pathlib import Path

import pytest

from app.core.censor_engine import (
    CensorExportError,
    build_cut_filter,
    build_export_command,
    build_keep_segments,
)
from app.core.models import CensorInterval, ExportRequest, TimelineSegment


def cut(start: float, end: float) -> CensorInterval:
    return CensorInterval(start, end, ())


def test_cut_at_beginning() -> None:
    assert build_keep_segments([cut(0.0, 2.0)], 10.0) == [
        TimelineSegment(2.0, 10.0, 0.0, 8.0)
    ]


def test_cut_at_end() -> None:
    assert build_keep_segments([cut(8.0, 10.0)], 10.0) == [
        TimelineSegment(0.0, 8.0, 0.0, 8.0)
    ]


def test_multiple_cuts_calculate_contiguous_output_timeline() -> None:
    segments = build_keep_segments([cut(2.0, 3.0), cut(6.0, 8.0)], 10.0)

    assert segments == [
        TimelineSegment(0.0, 2.0, 0.0, 2.0),
        TimelineSegment(3.0, 6.0, 2.0, 5.0),
        TimelineSegment(8.0, 10.0, 5.0, 7.0),
    ]


def test_overlapping_and_adjacent_cuts_are_merged() -> None:
    segments = build_keep_segments(
        [cut(2.0, 4.0), cut(3.0, 5.0), cut(5.0, 6.0)], 10.0
    )

    assert segments == [
        TimelineSegment(0.0, 2.0, 0.0, 2.0),
        TimelineSegment(6.0, 10.0, 2.0, 6.0),
    ]


def test_no_cuts_retains_full_timeline() -> None:
    assert build_keep_segments([], 5.0) == [TimelineSegment(0.0, 5.0, 0.0, 5.0)]


@pytest.mark.parametrize(
    "intervals",
    [
        [cut(-1.0, 1.0)],
        [cut(2.0, 1.0)],
        [cut(1.0, 11.0)],
    ],
)
def test_invalid_cut_ranges_are_rejected(intervals: list[CensorInterval]) -> None:
    with pytest.raises(ValueError, match="within the media duration"):
        build_keep_segments(intervals, 10.0)


def test_entire_timeline_cut_is_rejected() -> None:
    assert build_keep_segments([cut(0.0, 10.0)], 10.0) == []
    with pytest.raises(CensorExportError, match="entire video"):
        build_cut_filter([cut(0.0, 10.0)], 10.0)


def test_cut_filter_trims_audio_and_video_and_concatenates() -> None:
    filter_graph = build_cut_filter([cut(2.0, 3.0)], 5.0)

    assert "[0:v:0]trim=start=0:end=2,setpts=PTS-STARTPTS[v0]" in filter_graph
    assert "[0:a:0]atrim=start=0:end=2,asetpts=PTS-STARTPTS[a0]" in filter_graph
    assert "trim=start=3:end=5" in filter_graph
    assert "[v0][a0][v1][a1]concat=n=2:v=1:a=1[vout][aout]" in filter_graph


def test_cut_command_maps_filtered_streams_and_reencodes_video(tmp_path: Path) -> None:
    source = tmp_path / "source video.mp4"
    source.write_bytes(b"video")
    output = tmp_path / "cut output.mp4"
    request = ExportRequest(source, output, "Cut", (cut(1.0, 2.0),), 5.0)

    command = build_export_command("ffmpeg", request)

    assert command[command.index("-map") + 1] == "[vout]"
    assert "[aout]" in command
    assert command[command.index("-c:v") + 1] == "libx264"
    assert "copy" not in command
    assert command[-1] == str(output)


def test_cut_supports_video_without_audio(tmp_path: Path) -> None:
    source = tmp_path / "silent source.webm"
    source.write_bytes(b"video")
    request = ExportRequest(
        source, tmp_path / "silent cut.mp4", "Cut", (cut(1.0, 2.0),), 5.0,
        audio_stream_count=0,
    )
    command = build_export_command("ffmpeg", request)
    graph = command[command.index("-filter_complex") + 1]
    assert "concat=n=2:v=1:a=0[vout]" in graph
    assert "[0:a:" not in graph
    assert "[aout]" not in command


def test_cut_keeps_multiple_audio_streams_synchronized(tmp_path: Path) -> None:
    source = tmp_path / "медиа с дорожками.mkv"
    source.write_bytes(b"video")
    request = ExportRequest(
        source, tmp_path / "clean output.mkv", "Cut", (cut(1.0, 2.0),), 5.0,
        audio_stream_count=2,
    )
    command = build_export_command("ffmpeg", request)
    graph = command[command.index("-filter_complex") + 1]
    assert "[0:a:0]atrim" in graph and "[0:a:1]atrim" in graph
    assert "concat=n=2:v=1:a=2[vout][aout0][aout1]" in graph
    assert "[aout0]" in command and "[aout1]" in command
