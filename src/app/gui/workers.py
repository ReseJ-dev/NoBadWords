"""Background workers used by the desktop interface."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from app.core.censor_engine import VideoExporter
from app.core.models import ExportRequest, MediaInfo, ScanResult, ScanSettings
from app.core.profanity_detector import ProfanityScanner
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
        profanity_scanner: ProfanityScanner,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._path = path
        self._settings = settings
        self._transcriber = transcriber
        self._profanity_scanner = profanity_scanner

    @Slot()
    def run(self) -> None:
        try:
            words = self._transcriber.transcribe(
                self._path, self._settings, self.status_changed.emit
            )
            self.status_changed.emit("Detecting profanity")
            matches = self._profanity_scanner.detect(
                words, self._settings.confidence
            )
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.succeeded.emit(ScanResult(words=words, matches=matches))
        finally:
            self.completed.emit()


class ExportWorker(QObject):
    """Render a censored video without blocking the GUI thread."""

    status_changed = Signal(str)
    succeeded = Signal(Path)
    failed = Signal(str)
    completed = Signal()

    def __init__(
        self,
        request: ExportRequest,
        exporter: VideoExporter,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._request = request
        self._exporter = exporter

    @Slot()
    def run(self) -> None:
        try:
            output_path = self._exporter.export(
                self._request, self.status_changed.emit
            )
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.succeeded.emit(output_path)
        finally:
            self.completed.emit()
