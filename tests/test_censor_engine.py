"""Tests for Mute and Beep FFmpeg exports."""

from pathlib import Path
import threading
import time

import pytest
from PySide6.QtWidgets import QApplication

from app.core.censor_engine import (
    CensorEngine,
    CensorExportError,
    build_audio_filter,
    build_export_command,
    interval_expression,
)
from app.core.ffmpeg_utils import FFmpegTools
from app.core.models import CensorInterval, ExportRequest
from app.gui.main_window import MainWindow


def interval(start: float, end: float) -> CensorInterval:
    return CensorInterval(start, end, ())


def request(
    input_path: Path,
    output_path: Path,
    mode: str = "Mute",
    intervals: tuple[CensorInterval, ...] = (interval(1.0, 2.0),),
) -> ExportRequest:
    return ExportRequest(
        input_path=input_path,
        output_path=output_path,
        mode=mode,  # type: ignore[arg-type]
        intervals=intervals,
        media_duration=10.0,
        beep_frequency_hz=1250,
    )


def test_interval_expression_supports_many_intervals() -> None:
    expression = interval_expression([interval(0.1, 0.2), interval(2.5, 3.75)])

    assert expression == "between(t,0.1,0.2)+between(t,2.5,3.75)"


def test_mute_filter_silences_only_enabled_expression() -> None:
    audio_filter = build_audio_filter("Mute", [interval(1.0, 2.0)], 10.0)

    assert audio_filter == "[0:a:0]volume=0:enable='between(t,1,2)'[aout]"


def test_beep_filter_gates_configurable_tone_and_preserves_other_audio() -> None:
    audio_filter = build_audio_filter(
        "Beep", [interval(1.0, 2.0), interval(4.0, 4.5)], 10.0, 1250
    )

    assert "sine=frequency=1250" in audio_filter
    assert "duration=10" in audio_filter
    assert "volume=0:enable='not(" in audio_filter
    assert "amix=inputs=2:duration=first" in audio_filter
    assert "normalize=0" in audio_filter


def test_export_command_preserves_paths_and_copies_video(tmp_path: Path) -> None:
    source = tmp_path / "видео source.mp4"
    source.write_bytes(b"video")
    output = tmp_path / "clean output.mp4"

    command = build_export_command(
        Path(r"C:\FFmpeg Tools\ffmpeg.exe"), request(source, output, "Beep")
    )

    assert command[0] == r"C:\FFmpeg Tools\ffmpeg.exe"
    assert command[command.index("-i") + 1] == str(source)
    assert command[-1] == str(output)
    assert command[command.index("-c:v") + 1] == "copy"
    assert command[command.index("-c:a") + 1] == "aac"


def test_empty_intervals_copy_all_streams(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")

    command = build_export_command(
        "ffmpeg", request(source, tmp_path / "copy.mp4", intervals=())
    )

    assert "-filter_complex" not in command
    assert command[command.index("-c") + 1] == "copy"
    assert command[command.index("-map") + 1] == "0"


def test_mute_processes_every_audio_stream(tmp_path: Path) -> None:
    source = tmp_path / "source with audio.mkv"
    source.write_bytes(b"video")
    base_request = request(source, tmp_path / "output.mkv")
    export_request = ExportRequest(
        base_request.input_path, base_request.output_path, base_request.mode,
        base_request.intervals, base_request.media_duration,
        base_request.beep_frequency_hz, audio_stream_count=2,
    )
    command = build_export_command("ffmpeg", export_request)
    graph = command[command.index("-filter_complex") + 1]
    assert "[0:a:0]" in graph and "[0:a:1]" in graph
    assert "[aout0]" in command and "[aout1]" in command


def test_audio_modes_reject_video_without_audio(tmp_path: Path) -> None:
    source = tmp_path / "silent.mp4"
    source.write_bytes(b"video")
    export_request = ExportRequest(
        source, tmp_path / "output.mp4", "Mute", (interval(0.1, 0.2),), 1.0,
        audio_stream_count=0,
    )
    with pytest.raises(CensorExportError, match="require a source audio"):
        build_export_command("ffmpeg", export_request)


def test_export_engine_runs_argument_list_and_reports_stages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    output = tmp_path / "output.mp4"
    captured: list[list[str]] = []

    class FakeProcess:
        returncode = 0
        stdout = ["out_time_us=5000000\n", "progress=end\n"]
        stderr: list[str] = []

        def __init__(self, command: list[str], **kwargs: object) -> None:
            captured.append(command)

        def wait(self) -> int:
            return self.returncode

        def poll(self) -> int:
            return self.returncode

    monkeypatch.setattr("app.core.censor_engine.subprocess.Popen", FakeProcess)

    tools = FFmpegTools(tmp_path / "ffmpeg.exe", tmp_path / "ffprobe.exe")
    statuses: list[str] = []

    result = CensorEngine(tools).export(request(source, output), statuses.append)

    assert result == output
    assert isinstance(captured[0], list)
    assert statuses == ["Preparing filters", "Rendering video", "Finalizing output"]


def test_export_rejects_source_overwrite_and_surfaces_ffmpeg_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    tools = FFmpegTools(tmp_path / "ffmpeg.exe", tmp_path / "ffprobe.exe")

    with pytest.raises(CensorExportError, match="cannot be overwritten"):
        CensorEngine(tools).export(request(source, source))

    class FailedProcess:
        returncode = 1
        stdout: list[str] = []
        stderr = ["bad codec"]

        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def wait(self) -> int:
            return self.returncode

        def poll(self) -> int:
            return self.returncode

    monkeypatch.setattr("app.core.censor_engine.subprocess.Popen", FailedProcess)
    with pytest.raises(CensorExportError, match="bad codec"):
        CensorEngine(tools).export(request(source, tmp_path / "output.mp4"))


def test_export_rejects_intervals_outside_media_duration(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    invalid = request(
        source,
        tmp_path / "output.mp4",
        intervals=(interval(9.0, 11.0),),
    )

    with pytest.raises(CensorExportError, match="within the media duration"):
        build_export_command("ffmpeg", invalid)


def test_window_runs_export_outside_gui_thread(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    output = tmp_path / "output.mp4"
    release = threading.Event()

    class BlockingExporter:
        def export(
            self, export_request: ExportRequest, status_callback=None,
            cancellation_token=None, progress_callback=None,
        ) -> Path:
            if status_callback:
                status_callback("Rendering video")
            assert release.wait(timeout=2)
            return export_request.output_path

    window = MainWindow(exporter=BlockingExporter())
    window._start_export(request(source, output))
    assert window._export_thread is not None
    assert not window.choose_video_button.isEnabled()

    release.set()
    deadline = time.monotonic() + 2
    while window._export_thread is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)

    assert window.state.last_export_path == output
    assert "Complete" in window.export_controls.status_label.text()
    assert window.choose_video_button.isEnabled()
    window.close()
    application.processEvents()
