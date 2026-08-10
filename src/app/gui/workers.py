"""Background workers used by the desktop interface."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from app.core.models import MediaInfo, ScanSettings
from app.core.transcription import Transcriber


class MediaInspectionWorker(QObject):
    """Inspect one video without blocking the Qt main thread."""

    succeeded = Signal(Path, object)
    failed = Signal(Path, str)
    completed = Signal()

    def __init__(
        self, path: Path, inspector: Callable[[Path], MediaInfo], parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._path = path
        self._inspector = inspector

    @Slot()
    def run(self) -> None:
        try:
            media_info = self._inspector(self._path)
        except Exception as error:
            self.failed.emit(self._path, str(error))
        else:
            self.succeeded.emit(self._path, media_info)
        finally:
            self.completed.emit()


class TranscriptionWorker(QObject):
    """Run model loading and transcription outside the GUI thread."""

    status_changed = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)
    completed = Signal()

    def __init__(
        self,
        path: Path,
        settings: ScanSettings,
        transcriber: Transcriber,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._path = path
        self._settings = settings
        self._transcriber = transcriber

    @Slot()
    def run(self) -> None:
        try:
            words = self._transcriber.transcribe(
                self._path, self._settings, self.status_changed.emit
            )
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.succeeded.emit(words)
        finally:
            self.completed.emit()
