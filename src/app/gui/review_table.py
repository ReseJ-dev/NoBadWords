"""Profanity review table and its editable data model."""

from dataclasses import replace
from enum import IntEnum
from typing import Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.core.models import ProfanityMatch
from app.core.text_normalizer import normalize_russian_token
from app.gui.dialogs import ManualDetectionDialog


class ReviewColumn(IntEnum):
    ENABLED = 0
    TIME = 1
    WORD = 2
    CONFIDENCE = 3
    START = 4
    END = 5


HEADERS: tuple[str, ...] = ("Enabled", "Time", "Word", "Confidence", "Start", "End")


class ProfanityTableModel(QAbstractTableModel):
    """Editable collection of profanity detections."""

    matches_changed = Signal(object)

    def __init__(
        self,
        matches: Sequence[ProfanityMatch] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._matches = list(matches)

    @property
    def matches(self) -> list[ProfanityMatch]:
        return list(self._matches)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._matches)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(HEADERS)

    def headerData(  # noqa: N802
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return HEADERS[section] if 0 <= section < len(HEADERS) else None
        return super().headerData(section, orientation, role)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self._matches):
            return None
        match = self._matches[index.row()]
        column = ReviewColumn(index.column())
        if column == ReviewColumn.ENABLED and role == Qt.ItemDataRole.CheckStateRole:
            return Qt.CheckState.Checked if match.enabled else Qt.CheckState.Unchecked
        if role == Qt.ItemDataRole.EditRole:
            if column == ReviewColumn.START:
                return match.start
            if column == ReviewColumn.END:
                return match.end
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        return {
            ReviewColumn.ENABLED: "",
            ReviewColumn.TIME: self._format_timestamp(match.start),
            ReviewColumn.WORD: match.original_word,
            ReviewColumn.CONFIDENCE: f"{match.confidence:.0%}",
            ReviewColumn.START: f"{match.start:.3f}",
            ReviewColumn.END: f"{match.end:.3f}",
        }[column]

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        column = ReviewColumn(index.column())
        if column == ReviewColumn.ENABLED:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        elif column in (ReviewColumn.START, ReviewColumn.END):
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(  # noqa: N802
        self, index: QModelIndex, value: object, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        if not index.isValid() or not 0 <= index.row() < len(self._matches):
            return False
        match = self._matches[index.row()]
        column = ReviewColumn(index.column())
        updated: ProfanityMatch | None = None
        if column == ReviewColumn.ENABLED and role == Qt.ItemDataRole.CheckStateRole:
            updated = replace(
                match,
                enabled=value in (Qt.CheckState.Checked, Qt.CheckState.Checked.value),
            )
        elif column in (ReviewColumn.START, ReviewColumn.END) and role == Qt.ItemDataRole.EditRole:
            try:
                timestamp = float(value)
            except (TypeError, ValueError):
                return False
            if timestamp < 0:
                return False
            if column == ReviewColumn.START and timestamp < match.end:
                updated = replace(match, start=timestamp)
            elif column == ReviewColumn.END and timestamp > match.start:
                updated = replace(match, end=timestamp)
        if updated is None:
            return False
        self._matches[index.row()] = updated
        self.dataChanged.emit(index, index, [role])
        self._emit_matches()
        return True

    def sort(
        self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
    ) -> None:
        if not 0 <= column < len(HEADERS):
            return
        key_functions = {
            ReviewColumn.ENABLED: lambda match: match.enabled,
            ReviewColumn.TIME: lambda match: match.start,
            ReviewColumn.WORD: lambda match: match.original_word.casefold(),
            ReviewColumn.CONFIDENCE: lambda match: match.confidence,
            ReviewColumn.START: lambda match: match.start,
            ReviewColumn.END: lambda match: match.end,
        }
        self.layoutAboutToBeChanged.emit()
        self._matches.sort(
            key=key_functions[ReviewColumn(column)],
            reverse=order == Qt.SortOrder.DescendingOrder,
        )
        self.layoutChanged.emit()
        self._emit_matches()

    def set_matches(self, matches: Sequence[ProfanityMatch]) -> None:
        self.beginResetModel()
        self._matches = list(matches)
        self.endResetModel()
        self._emit_matches()

    def set_all_enabled(self, enabled: bool) -> None:
        if not self._matches:
            return
        self._matches = [replace(match, enabled=enabled) for match in self._matches]
        self.dataChanged.emit(
            self.index(0, ReviewColumn.ENABLED),
            self.index(len(self._matches) - 1, ReviewColumn.ENABLED),
            [Qt.ItemDataRole.CheckStateRole],
        )
        self._emit_matches()

    def delete_rows(self, rows: Sequence[int]) -> None:
        valid_rows = sorted({row for row in rows if 0 <= row < len(self._matches)}, reverse=True)
        for row in valid_rows:
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._matches[row]
            self.endRemoveRows()
        if valid_rows:
            self._emit_matches()

    def add_manual_detection(self, start: float, end: float, label: str = "") -> None:
        if start < 0 or end <= start:
            raise ValueError("Manual detection end time must be later than its start time.")
        display_label = label.strip() or "Manual detection"
        match = ProfanityMatch(
            original_word=display_label,
            normalized_word=normalize_russian_token(display_label),
            start=start,
            end=end,
            confidence=1.0,
            matched_rule="manual",
        )
        row = len(self._matches)
        self.beginInsertRows(QModelIndex(), row, row)
        self._matches.append(match)
        self.endInsertRows()
        self._emit_matches()

    def _emit_matches(self) -> None:
        self.matches_changed.emit(self.matches)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        milliseconds = round(max(0.0, seconds) * 1000)
        minutes, remainder = divmod(milliseconds, 60_000)
        whole_seconds, milliseconds = divmod(remainder, 1000)
        return f"{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"


class ProfanityReviewWidget(QWidget):
    """Table and controls for reviewing detected profanity."""

    matches_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.model = ProfanityTableModel(parent=self)
        self.model.matches_changed.connect(self.matches_changed)
        self.table = QTableView()
        self.table.setObjectName("profanityReviewTable")
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        controls = QHBoxLayout()
        self.select_all_button = QPushButton("Select All")
        self.deselect_all_button = QPushButton("Deselect All")
        self.delete_button = QPushButton("Delete Selected")
        self.add_button = QPushButton("Add Manual Detection")
        for button in (
            self.select_all_button,
            self.deselect_all_button,
            self.delete_button,
            self.add_button,
        ):
            controls.addWidget(button)
        layout.addLayout(controls)

        self.select_all_button.clicked.connect(lambda: self.model.set_all_enabled(True))
        self.deselect_all_button.clicked.connect(
            lambda: self.model.set_all_enabled(False)
        )
        self.delete_button.clicked.connect(self._delete_selected)
        self.add_button.clicked.connect(self._show_manual_dialog)

    def set_matches(self, matches: Sequence[ProfanityMatch]) -> None:
        self.model.set_matches(matches)

    def _delete_selected(self) -> None:
        self.model.delete_rows([index.row() for index in self.table.selectionModel().selectedRows()])

    def _show_manual_dialog(self) -> None:
        window = self.window()
        media_info = getattr(getattr(window, "state", None), "media_info", None)
        maximum_time = media_info.duration if media_info is not None else 86_400.0
        dialog = ManualDetectionDialog(maximum_time, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.model.add_manual_detection(
                dialog.start_spin.value(),
                dialog.end_spin.value(),
                dialog.label_input.text(),
            )
