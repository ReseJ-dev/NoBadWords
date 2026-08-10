"""Tests for video preview timing and detection navigation."""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

from app.core.models import ProfanityMatch
from app.gui.main_window import MainWindow
from app.gui.preview_widget import VideoPreviewWidget, detection_seek_position_ms


def match(start: float, end: float, word: str = "word") -> ProfanityMatch:
    return ProfanityMatch(word, word, start, end, 0.9, "test")


def test_detection_seek_includes_context_and_clamps_to_zero() -> None:
    assert detection_seek_position_ms(match(5.0, 5.2)) == 4000
    assert detection_seek_position_ms(match(0.4, 0.6)) == 0


def test_preview_loads_local_source_and_formats_timeline(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])
    video = tmp_path / "видео preview.mp4"
    video.write_bytes(b"video")
    preview = VideoPreviewWidget()

    preview.set_source(video)
    preview._on_duration_changed(65_000)
    preview._on_position_changed(5_000)

    assert preview.player.source() == QUrl.fromLocalFile(str(video.resolve()))
    assert preview.timeline_slider.maximum() == 65_000
    assert preview.current_time_label.text() == "00:05"
    assert preview.duration_label.text() == "01:05"
    preview.close()
    application.processEvents()


def test_detection_navigation_emits_context_seek_positions() -> None:
    application = QApplication.instance() or QApplication([])
    preview = VideoPreviewWidget()
    seeks: list[int] = []
    preview.seek_requested.connect(seeks.append)
    preview.set_detections([match(2.0, 2.2, "first"), match(5.0, 5.2, "second")])

    preview.next_detection()
    preview.next_detection()
    preview.previous_detection()

    assert seeks[-3:] == [1000, 4000, 1000]
    assert preview.play_detection_button.isEnabled()
    preview.close()
    application.processEvents()


def test_activating_review_detection_seeks_preview() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    detection = match(5.0, 5.2)
    window.review_widget.set_matches([detection])
    seeks: list[int] = []
    window.preview_widget.seek_requested.connect(seeks.append)

    window.review_widget._activate_detection(
        window.review_widget.model.index(0, 0)
    )

    assert seeks[-1] == 4000
    window.close()
    application.processEvents()
