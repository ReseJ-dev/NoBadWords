"""Small dialogs used by the desktop workflow."""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)


class ManualDetectionDialog(QDialog):
    """Collect timestamps and an optional label for a manual detection."""

    def __init__(self, maximum_time: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Manual Detection")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.start_spin = self._time_spin(maximum_time)
        self.end_spin = self._time_spin(maximum_time)
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("Optional label")
        form.addRow("Start (seconds)", self.start_spin)
        form.addRow("End (seconds)", self.end_spin)
        form.addRow("Label", self.label_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _time_spin(maximum_time: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(3)
        spin.setRange(0.0, max(0.0, maximum_time))
        spin.setSingleStep(0.1)
        return spin

    def _validate_and_accept(self) -> None:
        if self.end_spin.value() <= self.start_spin.value():
            QMessageBox.warning(
                self,
                "Invalid timestamps",
                "The end time must be later than the start time.",
            )
            return
        self.accept()

