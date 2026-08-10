"""Tests for faster-whisper transcription without downloading models."""

from pathlib import Path
import threading
import time
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from app.core.models import ScanSettings, VideoFile, WordTimestamp
from app.core.transcription import TranscriptionError, TranscriptionService, resolve_device
from app.gui.main_window import MainWindow


class FakeModel:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, bool]] = []

    def transcribe(
        self, path: str, *, language: object, word_timestamps: bool
    ) -> tuple[list[object], object]:
        self.calls.append((path, language, word_timestamps))
        words = [
            SimpleNamespace(word=" hello ", start=0.1, end=0.4, probability=0.91),
            SimpleNamespace(word="world", start=0.5, end=0.9, probability=0.82),
        ]
        return [SimpleNamespace(words=words)], SimpleNamespace()


def test_resolve_auto_device_uses_cuda_only_when_usable() -> None:
    assert resolve_device("Auto", lambda: True) == ("cuda", "float16")
    assert resolve_device("Auto", lambda: False) == ("cpu", "int8")
    assert resolve_device("CPU", lambda: True) == ("cpu", "int8")
    assert resolve_device("CUDA", lambda: False) == ("cuda", "float16")


def test_transcription_returns_word_timestamps(tmp_path: Path) -> None:
    video = tmp_path / "видео с пробелами.mp4"
    video.write_bytes(b"video")
    model = FakeModel()
    factory_calls: list[tuple[str, dict[str, object]]] = []

    def factory(name: str, **kwargs: object) -> FakeModel:
        factory_calls.append((name, kwargs))
        return model

    statuses: list[str] = []
    service = TranscriptionService(factory, cuda_checker=lambda: False)

    words = service.transcribe(
        video, ScanSettings(language="Russian", whisper_model="small"), statuses.append
    )

    assert words == [
        WordTimestamp("hello", 0.1, 0.4, 0.91),
        WordTimestamp("world", 0.5, 0.9, 0.82),
    ]
    assert factory_calls == [("small", {"device": "cpu", "compute_type": "int8"})]
    assert model.calls == [(str(video), "ru", True)]
    assert statuses == ["Loading Whisper model", "Transcribing"]


def test_identical_model_is_cached(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    models: list[FakeModel] = []

    def factory(name: str, **kwargs: object) -> FakeModel:
        model = FakeModel()
        models.append(model)
        return model

    service = TranscriptionService(factory, cuda_checker=lambda: False)
    settings = ScanSettings(whisper_model="tiny")

    service.transcribe(video, settings)
    service.transcribe(video, settings)

    assert len(models) == 1
    assert len(models[0].calls) == 2


def test_missing_input_is_reported_without_loading_model(tmp_path: Path) -> None:
    service = TranscriptionService(lambda *args, **kwargs: pytest.fail("loaded model"))

    with pytest.raises(TranscriptionError, match="no longer exists"):
        service.transcribe(tmp_path / "missing.mp4", ScanSettings())


def test_window_runs_transcription_in_background_and_restores_controls(
    tmp_path: Path,
) -> None:
    application = QApplication.instance() or QApplication([])
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    release = threading.Event()

    class BlockingTranscriber:
        def transcribe(self, path: Path, settings: ScanSettings, status_callback=None):
            if status_callback:
                status_callback("Transcribing")
            assert release.wait(timeout=2)
            return [WordTimestamp("hello", 0.0, 0.4, 0.9)]

    window = MainWindow(transcriber=BlockingTranscriber())
    window.state.selected_video = VideoFile.from_path(video)

    window.scan_settings_widget.scan_button.click()
    assert not window.choose_video_button.isEnabled()
    assert window._transcription_thread is not None

    release.set()
    deadline = time.monotonic() + 2
    while window._transcription_thread is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)

    assert window.state.word_timestamps == [WordTimestamp("hello", 0.0, 0.4, 0.9)]
    assert window.choose_video_button.isEnabled()
    assert "Transcription complete" in window.statusBar().currentMessage()

    window.close()
    application.processEvents()
