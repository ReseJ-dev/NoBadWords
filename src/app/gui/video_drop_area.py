"""Reusable drag-and-drop target for video files."""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.core.video import is_supported_video


class VideoDropArea(QWidget):
    """Accept a single local video file through drag and drop."""

    video_dropped = Signal(Path)
    unsupported_file_dropped = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("videoDropArea")
        self.setAcceptDrops(True)
        self.setProperty("dragActive", False)

        layout = QVBoxLayout(self)
        prompt = QLabel("Drop a video file here")
        prompt.setObjectName("dropPrompt")
        prompt.setWordWrap(True)
        layout.addWidget(prompt)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        path = self._first_local_path(event.mimeData().urls())
        if path is None:
            event.ignore()
            return
        event.acceptProposedAction()
        self._set_drag_active(is_supported_video(path))

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:  # noqa: N802
        self._set_drag_active(False)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self._set_drag_active(False)
        path = self._first_local_path(event.mimeData().urls())
        if path is None:
            event.ignore()
            return
        if is_supported_video(path):
            event.acceptProposedAction()
            self.video_dropped.emit(path)
            return
        event.acceptProposedAction()
        self.unsupported_file_dropped.emit(path)

    @staticmethod
    def _first_local_path(urls: list) -> Path | None:
        for url in urls:
            if url.isLocalFile():
                return Path(url.toLocalFile())
        return None

    def _set_drag_active(self, active: bool) -> None:
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
