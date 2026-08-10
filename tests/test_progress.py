"""Tests for truthful processing progress."""

from PySide6.QtWidgets import QApplication

from app.core.censor_engine import parse_ffmpeg_progress
from app.gui.progress_widget import ProcessingProgressWidget


def test_ffmpeg_progress_uses_output_duration() -> None:
    assert parse_ffmpeg_progress("out_time_us=2500000", 10.0) == 0.25
    assert parse_ffmpeg_progress("progress=end", 10.0) == 1.0
    assert parse_ffmpeg_progress("frame=10", 10.0) is None
    assert parse_ffmpeg_progress("out_time_us=invalid", 10.0) is None


def test_progress_widget_switches_from_indeterminate_to_real_percentage() -> None:
    QApplication.instance() or QApplication([])
    widget = ProcessingProgressWidget()

    widget.start("Transcribing")
    assert widget.progress_bar.minimum() == 0
    assert widget.progress_bar.maximum() == 0
    assert widget.stage_label.text() == "Transcribing"

    widget.set_fraction(0.42)
    assert widget.progress_bar.maximum() == 100
    assert widget.progress_bar.value() == 42

    widget.finish()
    assert widget.isHidden()
