"""Export controls for rendering a cleaned video."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.config import CENSORSHIP_MODES


class ExportControlsWidget(QWidget):
    """Present export action, current stage, and output location."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.export_button = QPushButton("Export Video")
        self.export_button.setObjectName("exportVideoButton")
        self.export_button.setProperty("primary", True)
        self.export_button.setToolTip("Save a cleaned copy of the selected video.")
        self.export_button.setEnabled(False)
        action_row = QHBoxLayout()
        action_row.addWidget(QLabel("Censor with"))
        self.mode_combo = QComboBox()
        self.mode_combo.setObjectName("exportModeSelector")
        self.mode_combo.addItems(CENSORSHIP_MODES)
        action_row.addWidget(self.mode_combo)
        action_row.addStretch(1)
        action_row.addWidget(self.export_button)
        layout.addLayout(action_row)

        self.status_label = QLabel("Export status: Waiting for reviewed detections")
        self.status_label.setObjectName("exportStatus")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.status_label)

        self.output_label = QLabel("Output: Not exported")
        self.output_label.setObjectName("exportOutput")
        self.output_label.setWordWrap(True)
        layout.addWidget(self.output_label)
