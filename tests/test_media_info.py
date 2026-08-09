"""Tests for FFprobe command creation and response parsing."""

from pathlib import Path

import pytest

from app.core.ffmpeg_utils import FFmpegNotFoundError, discover_ffmpeg_tools
from app.core.media_info import MediaInspectionError, build_ffprobe_command, parse_media_info


def test_ffprobe_command_preserves_unicode_path_with_spaces() -> None:
    media_path = Path(r"C:\Видео файлы\мой ролик.mp4")

    command = build_ffprobe_command(Path(r"C:\FFmpeg Tools\ffprobe.exe"), media_path)

    assert command[0] == r"C:\FFmpeg Tools\ffprobe.exe"
    assert command[-1] == str(media_path)
    assert command[-2] == "-show_streams"


def test_parse_media_info_with_video_and_multiple_audio_streams() -> None:
    payload = {
        "format": {"duration": "65.25"},
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "avg_frame_rate": "30000/1001",
            },
            {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
            {"codec_type": "audio", "codec_name": "ac3", "sample_rate": "48000"},
        ],
    }

    info = parse_media_info(payload)

    assert info.duration == 65.25
    assert (info.width, info.height) == (1920, 1080)
    assert info.frame_rate == pytest.approx(29.97, rel=0.001)
    assert info.video_codec == "h264"
    assert info.audio_codec == "aac"
    assert info.audio_stream_count == 2
    assert info.sample_rate == 48000


def test_parse_media_info_supports_video_without_audio() -> None:
    info = parse_media_info(
        {
            "format": {"duration": "1.5"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "vp9",
                    "width": 640,
                    "height": 360,
                    "r_frame_rate": "25/1",
                }
            ],
        }
    )

    assert info.audio_codec is None
    assert info.audio_stream_count == 0
    assert info.sample_rate is None


def test_parse_media_info_rejects_missing_video_stream() -> None:
    with pytest.raises(MediaInspectionError, match="video stream"):
        parse_media_info({"format": {"duration": "2"}, "streams": []})


def test_ffmpeg_discovery_reports_missing_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.ffmpeg_utils.shutil.which", lambda name: None)

    with pytest.raises(FFmpegNotFoundError, match="FFmpeg and FFprobe"):
        discover_ffmpeg_tools()


def test_ffmpeg_discovery_resolves_both_tools(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tool_paths = {
        "ffmpeg": str(tmp_path / "ffmpeg.exe"),
        "ffprobe": str(tmp_path / "ffprobe.exe"),
    }
    monkeypatch.setattr(
        "app.core.ffmpeg_utils.shutil.which", lambda name: tool_paths.get(name)
    )

    tools = discover_ffmpeg_tools()

    assert tools.ffmpeg == (tmp_path / "ffmpeg.exe").resolve()
    assert tools.ffprobe == (tmp_path / "ffprobe.exe").resolve()
