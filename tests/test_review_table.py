"""Tests for profanity review data-model behavior."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.core.models import ProfanityMatch
from app.gui.main_window import MainWindow
from app.gui.review_table import ProfanityTableModel, ReviewColumn


def match(
    word: str, start: float, end: float, *, enabled: bool = True
) -> ProfanityMatch:
    return ProfanityMatch(word, word, start, end, 0.8, "test", enabled)


def test_model_exposes_required_columns_and_values() -> None:
    application = QApplication.instance() or QApplication([])
    model = ProfanityTableModel([match("слово", 1.25, 1.75)])

    assert model.columnCount() == 6
    assert [
        model.headerData(column, Qt.Orientation.Horizontal)
        for column in range(model.columnCount())
    ] == ["Enabled", "Time", "Word", "Confidence", "Start", "End"]
    assert model.data(model.index(0, ReviewColumn.TIME)) == "00:01.250"
    assert model.data(model.index(0, ReviewColumn.WORD)) == "слово"
    application.processEvents()


def test_enabled_state_and_timestamps_are_editable() -> None:
    model = ProfanityTableModel([match("word", 1.0, 2.0)])

    assert model.setData(
        model.index(0, ReviewColumn.ENABLED),
        Qt.CheckState.Unchecked.value,
        Qt.ItemDataRole.CheckStateRole,
    )
    assert model.setData(model.index(0, ReviewColumn.START), 0.75)
    assert model.setData(model.index(0, ReviewColumn.END), 2.25)

    updated = model.matches[0]
    assert updated.enabled is False
    assert (updated.start, updated.end) == (0.75, 2.25)
    assert not model.setData(model.index(0, ReviewColumn.START), 3.0)
    assert not model.setData(model.index(0, ReviewColumn.END), -1.0)


def test_select_all_and_deselect_all() -> None:
    model = ProfanityTableModel(
        [match("one", 0.0, 0.2, enabled=False), match("two", 1.0, 1.2)]
    )

    model.set_all_enabled(True)
    assert all(item.enabled for item in model.matches)
    model.set_all_enabled(False)
    assert not any(item.enabled for item in model.matches)


def test_delete_selected_rows_and_add_manual_detection() -> None:
    model = ProfanityTableModel([match("one", 0.0, 0.2), match("two", 1.0, 1.2)])

    model.delete_rows([0])
    model.add_manual_detection(2.0, 2.5, "manual label")

    assert [item.original_word for item in model.matches] == ["two", "manual label"]
    assert model.matches[-1].matched_rule == "manual"
    assert model.matches[-1].confidence == 1.0
    with pytest.raises(ValueError):
        model.add_manual_detection(3.0, 2.0)


def test_timestamp_sorting() -> None:
    model = ProfanityTableModel([match("late", 5.0, 5.2), match("early", 1.0, 1.2)])

    model.sort(ReviewColumn.TIME, Qt.SortOrder.AscendingOrder)
    assert [item.original_word for item in model.matches] == ["early", "late"]
    model.sort(ReviewColumn.START, Qt.SortOrder.DescendingOrder)
    assert [item.original_word for item in model.matches] == ["late", "early"]


def test_review_changes_update_application_state() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.review_widget.set_matches([match("word", 1.0, 1.2)])

    window.review_widget.model.set_all_enabled(False)

    assert len(window.state.profanity_matches) == 1
    assert window.state.profanity_matches[0].enabled is False
    assert window.detection_count_label.text() == "Detected profanity: 1"
    window.close()
    application.processEvents()
