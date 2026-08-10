"""Cancellation and recovery regression tests."""

from pathlib import Path
import threading
import time

import pytest
from PySide6.QtWidgets import QApplication

from app.core.cancellation import CancellationToken, OperationCancelled
from app.core.censor_engine import CensorEngine
from app.core.ffmpeg_utils import FFmpegTools
from app.core.models import CensorInterval, ExportRequest, ScanSettings, VideoFile
from app.gui.main_window import MainWindow


def test_cancellation_token_is_idempotent_and_notifies_once() -> None:
    token = CancellationToken()
    calls: list[str] = []
    token.add_callback(lambda: calls.append("cancelled"))

    token.cancel()
    token.cancel()

    assert calls == ["cancelled"]
    with pytest.raises(OperationCancelled):
        token.raise_if_cancelled()


def test_export_cancellation_terminates_process_and_removes_partial_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    output = tmp_path / "partial.mp4"
    started = threading.Event()
    stopped = threading.Event()

    class BlockingProcess:
        returncode = -15

        def __init__(self, *args: object, **kwargs: object) -> None:
            output.write_bytes(b"partial")
            started.set()

        def communicate(self) -> tuple[str, str]:
            assert stopped.wait(timeout=2)
            return "", "terminated"

        def poll(self) -> int | None:
            return self.returncode if stopped.is_set() else None

        def terminate(self) -> None:
            stopped.set()

        def kill(self) -> None:
            stopped.set()

    monkeypatch.setattr("app.core.censor_engine.subprocess.Popen", BlockingProcess)
    request = ExportRequest(
        source, output, "Mute", (CensorInterval(0.1, 0.2, ()),), 1.0
    )
    token = CancellationToken()
    errors: list[BaseException] = []

    def export() -> None:
        try:
            CensorEngine(FFmpegTools(Path("ffmpeg"), Path("ffprobe"))).export(
                request, cancellation_token=token
            )
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=export)
    thread.start()
    assert started.wait(timeout=2)
    token.cancel()
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert stopped.is_set()
    assert len(errors) == 1 and isinstance(errors[0], OperationCancelled)
    assert source.exists()
    assert not output.exists()


def test_cancel_scan_restores_window_controls(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])
    source = tmp_path / "video.mp4"
    source.write_bytes(b"video")
    started = threading.Event()

    class BlockingTranscriber:
        def transcribe(
            self, path: Path, settings: ScanSettings, status_callback=None,
            cancellation_token: CancellationToken | None = None,
        ):
            assert cancellation_token is not None
            started.set()
            while not cancellation_token.is_cancelled:
                time.sleep(0.005)
            cancellation_token.raise_if_cancelled()

    window = MainWindow(transcriber=BlockingTranscriber())
    window.state.selected_video = VideoFile.from_path(source)
    window.scan_settings_widget.scan_button.click()
    assert started.wait(timeout=2)

    window.cancel_button.click()
    deadline = time.monotonic() + 2
    while window._transcription_thread is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.005)

    assert window._transcription_thread is None
    assert window.choose_video_button.isEnabled()
    assert window.cancel_button.isHidden()
    assert "cancelled" in window.statusBar().currentMessage().lower()
    window.close()
    application.processEvents()
