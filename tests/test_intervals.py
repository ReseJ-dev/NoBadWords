"""Tests for safe censorship interval construction."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.core.intervals import build_censor_intervals, total_censorship_duration
from app.core.models import MediaInfo, ProfanityMatch
from app.gui.main_window import MainWindow
from app.gui.review_table import ReviewColumn


def detection(
    start: float,
    end: float,
    *,
    word: str = "word",
    enabled: bool = True,
) -> ProfanityMatch:
    return ProfanityMatch(word, word, start, end, 0.9, "test", enabled)


def test_detection_at_beginning_is_clamped_to_zero() -> None:
    intervals = build_censor_intervals([detection(0.05, 0.3)], 10.0)

    assert intervals[0].start == 0.0
    assert intervals[0].end == pytest.approx(0.48)


def test_detection_at_end_is_clamped_to_media_duration() -> None:
    intervals = build_censor_intervals([detection(9.8, 10.0)], 10.0)

    assert intervals[0].start == pytest.approx(9.68)
    assert intervals[0].end == 10.0


def test_overlapping_intervals_merge_and_preserve_detections() -> None:
    first = detection(1.0, 1.4, word="first")
    second = detection(1.45, 1.8, word="second")

    intervals = build_censor_intervals([first, second], 10.0)

    assert len(intervals) == 1
    assert intervals[0].start == pytest.approx(0.88)
    assert intervals[0].end == pytest.approx(1.98)
    assert intervals[0].matches == (first, second)


def test_nearby_intervals_merge_with_configurable_gap() -> None:
    detections = [detection(1.0, 1.1), detection(1.5, 1.6)]

    separate = build_censor_intervals(
        detections, 10.0, pre_padding_ms=0, post_padding_ms=0, merge_gap_ms=300
    )
    merged = build_censor_intervals(
        detections, 10.0, pre_padding_ms=0, post_padding_ms=0, merge_gap_ms=400
    )

    assert len(separate) == 2
    assert len(merged) == 1


def test_disabled_and_invalid_detections_are_ignored() -> None:
    intervals = build_censor_intervals(
        [detection(1.0, 1.3, enabled=False), detection(2.0, 1.0)], 10.0
    )

    assert intervals == []


def test_edited_timestamps_and_multiple_detections_are_sorted() -> None:
    late = detection(5.0, 5.2, word="late")
    edited = detection(1.25, 1.75, word="edited")

    intervals = build_censor_intervals(
        [late, edited], 10.0, pre_padding_ms=100, post_padding_ms=200
    )

    assert [(interval.start, interval.end) for interval in intervals] == pytest.approx(
        [(1.15, 1.95), (4.9, 5.4)]
    )
    assert intervals[0].matches == (edited,)
    assert intervals[1].matches == (late,)


def test_total_duration_uses_merged_intervals() -> None:
    intervals = build_censor_intervals(
        [detection(1.0, 2.0), detection(1.5, 2.5)],
        10.0,
        pre_padding_ms=0,
        post_padding_ms=0,
    )

    assert total_censorship_duration(intervals) == pytest.approx(1.5)


def test_invalid_configuration_is_rejected() -> None:
    with pytest.raises(ValueError):
        build_censor_intervals([], -1.0)
    with pytest.raises(ValueError):
        build_censor_intervals([], 1.0, merge_gap_ms=-1)


def test_gui_displays_effective_censorship_duration() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.state.media_info = MediaInfo(10.0, 1920, 1080, 30.0, "h264", "aac", 1, 48000)

    window.review_widget.set_matches([detection(1.0, 2.0)])

    assert len(window.state.censor_intervals) == 1
    assert window.effective_duration_label.text() == "Effective censorship: 1.300 s"

    window.review_widget.model.setData(
        window.review_widget.model.index(0, ReviewColumn.START), 0.5
    )
    assert window.effective_duration_label.text() == "Effective censorship: 1.800 s"

    window.review_widget.model.setData(
        window.review_widget.model.index(0, ReviewColumn.ENABLED),
        0,
        Qt.ItemDataRole.CheckStateRole,
    )
    assert window.state.censor_intervals == []
    assert window.effective_duration_label.text() == "Effective censorship: 0.000 s"
    window.close()
    application.processEvents()
