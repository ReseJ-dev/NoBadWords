"""Compact display for truthful background-operation progress."""

from PySide6.QtCore import QElapsedTimer, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget


class ProcessingProgressWidget(QWidget):
    """Show the current stage, elapsed time, and optional real percentage."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._elapsed = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._refresh_elapsed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.stage_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.elapsed_label = QLabel("Elapsed: 00:00")
        layout.addWidget(self.stage_label)
        layout.addWidget(self.progress_bar, 1)
        layout.addWidget(self.elapsed_label)
        self.setVisible(False)

    def start(self, stage: str) -> None:
        self.stage_label.setText(stage)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("Working…")
        self.elapsed_label.setText("Elapsed: 00:00")
        self._elapsed.start()
        self._timer.start()
        self.setVisible(True)

    def set_stage(self, stage: str) -> None:
        self.stage_label.setText(stage)

    def set_fraction(self, fraction: float) -> None:
        percent = round(max(0.0, min(1.0, fraction)) * 100)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setValue(percent)

    def finish(self) -> None:
        self._timer.stop()
        self._refresh_elapsed()
        self.setVisible(False)

    def _refresh_elapsed(self) -> None:
        elapsed_seconds = max(0, self._elapsed.elapsed() // 1000)
        minutes, seconds = divmod(elapsed_seconds, 60)
        self.elapsed_label.setText(f"Elapsed: {minutes:02d}:{seconds:02d}")
