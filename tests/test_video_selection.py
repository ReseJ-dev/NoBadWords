"""Tests for video validation and application selection state."""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app.core.video import is_supported_video
from app.gui.main_window import MainWindow


@pytest.mark.parametrize("extension", ["mp4", "mov", "mkv", "avi", "webm", "m4v"])
def test_supported_video_extensions(extension: str) -> None:
    assert is_supported_video(f"example.{extension}")
    assert is_supported_video(f"example.{extension.upper()}")


@pytest.mark.parametrize("filename", ["video.txt", "video.mp3", "video", "video.mp4.exe"])
def test_unsupported_video_extensions(filename: str) -> None:
    assert not is_supported_video(filename)


def test_selecting_video_updates_application_state(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])
    video_path = tmp_path / "sample video.mp4"
    video_path.write_bytes(b"video data")
    window = MainWindow()

    selected = window.select_video(video_path)

    assert selected is True
    assert window.state.selected_video is not None
    assert window.state.selected_video.path == video_path.resolve()
    assert window.state.selected_video.size_bytes == len(b"video data")
    assert window.state.selected_video.duration_seconds is None
    assert "sample video.mp4" in window.video_filename_label.text()
    assert "Ready to scan" in window.video_status_label.text()

    window.close()
    application.processEvents()

