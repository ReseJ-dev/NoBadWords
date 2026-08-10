"""Main application window."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QThread, Qt

from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.config import SettingsStore
from app.core.media_info import inspect_media
from app.core.models import (
    ApplicationState,
    MediaInfo,
    ProfanityMatch,
    ScanResult,
    ScanSettings,
    VideoFile,
)
from app.core.profanity_detector import ProfanityDetector, ProfanityScanner
from app.core.transcription import Transcriber, TranscriptionService
from app.core.video import SUPPORTED_VIDEO_EXTENSIONS, format_file_size, is_supported_video
from app.gui.review_table import ProfanityReviewWidget
from app.gui.scan_settings import ScanSettingsWidget
from app.gui.video_drop_area import VideoDropArea
from app.gui.workers import MediaInspectionWorker, TranscriptionWorker


class MainWindow(QMainWindow):
    """Top-level window for the video profanity censor workflow."""

    def __init__(
        self,
        media_inspector: Callable[[Path], MediaInfo] = inspect_media,
        settings_store: SettingsStore | None = None,
        transcriber: Transcriber | None = None,
        profanity_scanner: ProfanityScanner | None = None,
    ) -> None:
        super().__init__()
        self._settings_store = settings_store or SettingsStore()
        self.state = ApplicationState(scan_settings=self._settings_store.load())
        self._media_inspector = media_inspector
        self._transcriber = (
            transcriber if transcriber is not None else TranscriptionService()
        )
        self._profanity_scanner = (
            profanity_scanner if profanity_scanner is not None else ProfanityDetector()
        )
        self._inspection_workers: dict[QThread, MediaInspectionWorker] = {}
        self._transcription_thread: QThread | None = None
        self._transcription_worker: TranscriptionWorker | None = None
        self.setWindowTitle("Video Profanity Censor")
        self.setMinimumSize(960, 640)
        self.setCentralWidget(self._create_central_widget())
        self.statusBar().showMessage("Ready")

    def _create_central_widget(self) -> QWidget:
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        heading = QLabel("Video Profanity Censor")
        heading.setObjectName("pageHeading")
        layout.addWidget(heading)

        subtitle = QLabel(
            "Import a video, scan its speech, review detections, and export a clean copy."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        sections = QGridLayout()
        sections.setSpacing(16)
        sections.addWidget(self._create_video_input_section(), 0, 0)
        sections.addWidget(self._create_scan_settings_section(), 0, 1)
        sections.addWidget(self._create_results_section(), 1, 0)
        sections.addWidget(self._create_section("exportControls", "Export controls"), 1, 1)
        sections.setRowStretch(0, 1)
        sections.setRowStretch(1, 1)
        sections.setColumnStretch(0, 1)
        sections.setColumnStretch(1, 1)
        layout.addLayout(sections, 1)

        return central_widget

    def _create_results_section(self) -> QFrame:
        section = self._create_section(
            "detectedProfanity", "Detected profanity", add_placeholder=False
        )
        self.detection_count_label = QLabel("No scan results")
        self.detection_count_label.setObjectName("detectionCount")
        self.detection_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        section.layout().addWidget(self.detection_count_label)
        self.review_widget = ProfanityReviewWidget()
        self.review_widget.matches_changed.connect(self._on_review_matches_changed)
        section.layout().addWidget(self.review_widget)
        return section

    def _on_review_matches_changed(self, matches: list[ProfanityMatch]) -> None:
        self.state.profanity_matches = list(matches)
        self.detection_count_label.setText(f"Detected profanity: {len(matches)}")

    def _create_scan_settings_section(self) -> QFrame:
        section = self._create_section("scanSettings", "Scan settings", add_placeholder=False)
        self.scan_settings_widget = ScanSettingsWidget(self.state.scan_settings)
        self.scan_settings_widget.settings_changed.connect(self._on_scan_settings_changed)
        self.scan_settings_widget.scan_button.clicked.connect(self._start_scan)
        section.layout().addWidget(self.scan_settings_widget)
        return section

    def _on_scan_settings_changed(self, settings: ScanSettings) -> None:
        self.state.scan_settings = settings
        self._settings_store.save(settings)

    def _create_video_input_section(self) -> QFrame:
        section = self._create_section("videoInput", "Video input", add_placeholder=False)
        layout = section.layout()

        self.video_drop_area = VideoDropArea()
        self.video_drop_area.video_dropped.connect(self.select_video)
        self.video_drop_area.unsupported_file_dropped.connect(
            self._show_unsupported_file_message
        )
        layout.addWidget(self.video_drop_area)

        self.choose_video_button = QPushButton("Choose Video")
        self.choose_video_button.setObjectName("chooseVideoButton")
        self.choose_video_button.clicked.connect(self._choose_video)
        layout.addWidget(self.choose_video_button)

        self.video_filename_label = QLabel("Filename: No video selected")
        self.video_filename_label.setObjectName("videoFilename")
        self.video_path_label = QLabel("Full path: Not selected")
        self.video_path_label.setObjectName("videoPath")
        self.video_path_label.setWordWrap(True)
        self.video_size_label = QLabel("File size: Not available")
        self.video_size_label.setObjectName("videoSize")
        self.video_duration_label = QLabel("Detected duration: Not scanned")
        self.video_duration_label.setObjectName("videoDuration")
        self.video_resolution_label = QLabel("Resolution: Not inspected")
        self.video_resolution_label.setObjectName("videoResolution")
        self.video_codec_label = QLabel("Video codec: Not inspected")
        self.video_codec_label.setObjectName("videoCodec")
        self.audio_codec_label = QLabel("Audio codec: Not inspected")
        self.audio_codec_label.setObjectName("audioCodec")
        self.video_status_label = QLabel("Input status: Waiting for a video")
        self.video_status_label.setObjectName("videoStatus")
        for label in (
            self.video_filename_label,
            self.video_path_label,
            self.video_size_label,
            self.video_duration_label,
            self.video_resolution_label,
            self.video_codec_label,
            self.audio_codec_label,
            self.video_status_label,
        ):
            layout.addWidget(label)
        return section

    def _choose_video(self) -> None:
        extension_pattern = " ".join(
            f"*{extension}" for extension in sorted(SUPPORTED_VIDEO_EXTENSIONS)
        )
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Video",
            "",
            f"Video files ({extension_pattern});;All files (*)",
        )
        if selected_path:
            self.select_video(Path(selected_path))

    def select_video(self, path: Path) -> bool:
        """Validate and store a user-selected video without starting a scan."""
        if not is_supported_video(path):
            self._show_unsupported_file_message(path)
            return False
        if not path.is_file():
            QMessageBox.warning(
                self,
                "Video unavailable",
                "The selected video file could not be found. Please choose another file.",
            )
            return False

        video = VideoFile.from_path(path)
        self.state.selected_video = video
        self.state.media_info = None
        self.video_filename_label.setText(f"Filename: {video.path.name}")
        self.video_path_label.setText(f"Full path: {video.path}")
        self.video_size_label.setText(f"File size: {format_file_size(video.size_bytes)}")
        self.video_duration_label.setText("Duration: Inspecting...")
        self.video_resolution_label.setText("Resolution: Inspecting...")
        self.video_codec_label.setText("Video codec: Inspecting...")
        self.audio_codec_label.setText("Audio codec: Inspecting...")
        self.video_status_label.setText("Input status: Inspecting media")
        self.statusBar().showMessage(f"Inspecting {video.path.name}")
        self._start_media_inspection(video.path)
        return True

    def _start_media_inspection(self, path: Path) -> None:
        thread = QThread(self)
        worker = MediaInspectionWorker(path, self._media_inspector)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._on_media_inspected)
        worker.failed.connect(self._on_media_inspection_failed)
        worker.completed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._release_inspection_thread(thread))
        self._inspection_workers[thread] = worker
        thread.start()

    def _release_inspection_thread(self, thread: QThread) -> None:
        self._inspection_workers.pop(thread, None)
        thread.deleteLater()

    def _on_media_inspected(self, path: Path, media_info: MediaInfo) -> None:
        if self.state.selected_video is None or self.state.selected_video.path != path:
            return
        self.state.media_info = media_info
        self.video_duration_label.setText(f"Duration: {self._format_duration(media_info.duration)}")
        self.video_resolution_label.setText(
            f"Resolution: {media_info.width} x {media_info.height}"
        )
        self.video_codec_label.setText(f"Video codec: {media_info.video_codec}")
        audio_codec = media_info.audio_codec or "No audio"
        self.audio_codec_label.setText(f"Audio codec: {audio_codec}")
        self.video_status_label.setText("Input status: Ready to scan")
        self.statusBar().showMessage(f"Ready to scan {path.name}")

    def _start_scan(self) -> None:
        if self.state.selected_video is None:
            QMessageBox.information(
                self,
                "Select a video",
                "Choose or drop a video before starting a scan.",
            )
            return
        if self._transcription_thread is not None:
            return

        self.state.word_timestamps.clear()
        self.state.profanity_matches.clear()
        self.review_widget.set_matches([])
        self.detection_count_label.setText("Scanning...")
        self._set_scan_controls_enabled(False)
        self.statusBar().showMessage("Preparing transcription")

        thread = QThread(self)
        worker = TranscriptionWorker(
            self.state.selected_video.path,
            self.state.scan_settings,
            self._transcriber,
            self._profanity_scanner,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.status_changed.connect(self.statusBar().showMessage)
        worker.succeeded.connect(self._on_transcription_succeeded)
        worker.failed.connect(self._on_transcription_failed)
        worker.completed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater)
        thread.finished.connect(self._release_transcription_thread)
        self._transcription_thread = thread
        self._transcription_worker = worker
        thread.start()

    def _on_transcription_succeeded(self, result: ScanResult) -> None:
        self.state.word_timestamps = list(result.words)
        self.state.profanity_matches = list(result.matches)
        self.review_widget.set_matches(result.matches)
        count = len(result.matches)
        self.detection_count_label.setText(f"Detected profanity: {count}")
        self.statusBar().showMessage(f"Scan complete: {count} detections")

    def _on_transcription_failed(self, message: str) -> None:
        self.statusBar().showMessage("Transcription failed")
        QMessageBox.warning(self, "Could not scan video", message)

    def _release_transcription_thread(self) -> None:
        thread = self._transcription_thread
        self._transcription_thread = None
        self._transcription_worker = None
        self._set_scan_controls_enabled(True)
        if thread is not None:
            thread.deleteLater()

    def _set_scan_controls_enabled(self, enabled: bool) -> None:
        self.video_drop_area.setEnabled(enabled)
        self.choose_video_button.setEnabled(enabled)
        self.scan_settings_widget.setEnabled(enabled)

    def _on_media_inspection_failed(self, path: Path, message: str) -> None:
        if self.state.selected_video is None or self.state.selected_video.path != path:
            return
        self.video_duration_label.setText("Duration: Unavailable")
        self.video_resolution_label.setText("Resolution: Unavailable")
        self.video_codec_label.setText("Video codec: Unavailable")
        self.audio_codec_label.setText("Audio codec: Unavailable")
        self.video_status_label.setText("Input status: Media inspection failed")
        self.statusBar().showMessage("Media inspection failed")
        QMessageBox.warning(self, "Media inspection unavailable", message)

    @staticmethod
    def _format_duration(duration: float) -> str:
        total_seconds = max(0, round(duration))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _show_unsupported_file_message(self, path: Path) -> None:
        supported = ", ".join(
            extension.removeprefix(".").upper()
            for extension in sorted(SUPPORTED_VIDEO_EXTENSIONS)
        )
        QMessageBox.warning(
            self,
            "Unsupported video format",
            f"{path.name} is not a supported video file.\n\nSupported formats: {supported}.",
        )

    def _create_section(
        self, object_name: str, title: str, *, add_placeholder: bool = True
    ) -> QFrame:
        section = QFrame()
        section.setObjectName(object_name)
        section.setProperty("section", True)
        section.setFrameShape(QFrame.Shape.StyledPanel)
        section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(18, 16, 18, 16)
        title_label = QLabel(title)
        title_label.setProperty("sectionTitle", True)
        layout.addWidget(title_label)

        if add_placeholder:
            placeholder = QLabel("Coming in a later step")
            placeholder.setProperty("placeholder", True)
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder, 1)
        return section
