"""Main application window."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence

from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.censor_engine import CensorEngine, VideoExporter
from app.core.config import SettingsStore
from app.core.intervals import build_censor_intervals, total_censorship_duration
from app.core.media_info import inspect_media
from app.core.models import (
    ApplicationState,
    ExportRequest,
    MediaInfo,
    ProfanityMatch,
    ScanResult,
    ScanSettings,
    VideoFile,
)
from app.core.profanity_detector import ProfanityDetector, ProfanityScanner
from app.core.transcription import Transcriber, TranscriptionService
from app.core.video import SUPPORTED_VIDEO_EXTENSIONS, format_file_size, is_supported_video
from app.gui.export_controls import ExportControlsWidget
from app.gui.preview_widget import VideoPreviewWidget
from app.gui.progress_widget import ProcessingProgressWidget
from app.gui.review_table import ProfanityReviewWidget
from app.gui.scan_settings import ScanSettingsWidget
from app.gui.video_drop_area import VideoDropArea
from app.gui.workers import ExportWorker, MediaInspectionWorker, TranscriptionWorker


class MainWindow(QMainWindow):
    """Top-level window for the video profanity censor workflow."""

    def __init__(
        self,
        media_inspector: Callable[[Path], MediaInfo] = inspect_media,
        settings_store: SettingsStore | None = None,
        transcriber: Transcriber | None = None,
        profanity_scanner: ProfanityScanner | None = None,
        exporter: VideoExporter | None = None,
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
        self._exporter = exporter if exporter is not None else CensorEngine()
        self._inspection_workers: dict[QThread, MediaInspectionWorker] = {}
        self._transcription_thread: QThread | None = None
        self._transcription_worker: TranscriptionWorker | None = None
        self._export_thread: QThread | None = None
        self._export_worker: ExportWorker | None = None
        self._close_when_idle = False
        self._scan_completed = False
        self.setWindowTitle("Video Profanity Censor")
        self.setMinimumSize(980, 680)
        self.setCentralWidget(self._create_central_widget())
        self._create_menus()
        self.statusBar().showMessage("Ready")

    def _create_central_widget(self) -> QWidget:
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(32, 24, 32, 28)
        layout.setSpacing(16)

        header = QHBoxLayout()
        heading = QLabel("Video Censor")
        heading.setObjectName("pageHeading")
        header.addWidget(heading)
        header.addStretch(1)
        self.settings_button = QPushButton("⚙")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setToolTip("Open advanced scan settings")
        self.settings_button.clicked.connect(self._show_advanced_settings)
        header.addWidget(self.settings_button)
        layout.addLayout(header)

        subtitle = QLabel(
            "Remove profanity from video automatically"
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.processing_progress = ProcessingProgressWidget()
        layout.addWidget(self.processing_progress)

        self.cancel_button = QPushButton("Cancel Processing")
        self.cancel_button.setObjectName("cancelProcessingButton")
        self.cancel_button.setProperty("danger", True)
        self.cancel_button.setToolTip("Safely stop the active scan or export")
        self.cancel_button.clicked.connect(self._cancel_active_operation)
        self.cancel_button.setVisible(False)
        layout.addWidget(self.cancel_button)

        self.video_input_section = self._create_video_input_section()
        layout.addWidget(self.video_input_section)
        self.scan_settings_section = self._create_scan_settings_section()
        layout.addWidget(self.scan_settings_section)

        self.review_stage = QWidget()
        review_layout = QGridLayout(self.review_stage)
        review_layout.setContentsMargins(0, 0, 0, 0)
        review_layout.setSpacing(16)
        self.preview_section = self._create_preview_section()
        self.results_section = self._create_results_section()
        review_layout.addWidget(self.preview_section, 0, 0)
        review_layout.addWidget(self.results_section, 0, 1)
        review_layout.setColumnStretch(0, 3)
        review_layout.setColumnStretch(1, 2)
        layout.addWidget(self.review_stage, 1)

        self.export_section = self._create_export_section()
        layout.addWidget(self.export_section)
        self._update_workflow_visibility()

        return central_widget

    def _create_preview_section(self) -> QFrame:
        section = self._create_section(
            "videoPreviewSection", "Video preview", add_placeholder=False
        )
        self.preview_widget = VideoPreviewWidget()
        section.layout().addWidget(self.preview_widget)
        return section

    def _create_menus(self) -> None:
        self.file_menu = self.menuBar().addMenu("&File")
        self.open_action = QAction("&Open Video...", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.setStatusTip("Choose a video to scan")
        self.open_action.triggered.connect(self._choose_video)
        self.file_menu.addAction(self.open_action)

        self.export_action = QAction("&Export Video...", self)
        self.export_action.setShortcut(QKeySequence("Ctrl+E"))
        self.export_action.setStatusTip("Export the reviewed censorship intervals")
        self.export_action.setEnabled(False)
        self.export_action.triggered.connect(self._choose_export_path)
        self.file_menu.addAction(self.export_action)
        self.file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

        self.tools_menu = self.menuBar().addMenu("&Tools")
        settings_action = QAction("&Settings", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.setStatusTip("Focus the scan and censorship settings")
        settings_action.triggered.connect(self._focus_settings)
        self.tools_menu.addAction(settings_action)

        self.help_menu = self.menuBar().addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        about_action.triggered.connect(self._show_about)
        self.help_menu.addAction(about_action)

    def _focus_settings(self) -> None:
        self.scan_settings_widget.language_combo.setFocus(
            Qt.FocusReason.ShortcutFocusReason
        )
        self.statusBar().showMessage("Scan and censorship settings")

    def _show_advanced_settings(self) -> None:
        if self.state.selected_video is None:
            self.statusBar().showMessage("Choose a video before configuring scan settings")
            return
        self.scan_settings_section.setVisible(True)
        self.scan_settings_widget.advanced_button.setChecked(True)
        self.scan_settings_widget.device_combo.setFocus(
            Qt.FocusReason.ShortcutFocusReason
        )

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About Video Profanity Censor",
            "Video Profanity Censor\n\n"
            "Scan speech, review detected profanity, and export a cleaned video.",
        )

    def _create_export_section(self) -> QFrame:
        section = self._create_section(
            "exportControls", "Export", add_placeholder=False
        )
        self.export_controls = ExportControlsWidget()
        self.export_controls.mode_combo.setCurrentText(
            self.state.scan_settings.censorship_mode
        )
        self.export_controls.mode_combo.currentTextChanged.connect(
            self.scan_settings_widget.mode_combo.setCurrentText
        )
        self.scan_settings_widget.mode_combo.currentTextChanged.connect(
            self.export_controls.mode_combo.setCurrentText
        )
        self.export_controls.export_button.clicked.connect(self._choose_export_path)
        section.layout().addWidget(self.export_controls)
        return section

    def _create_results_section(self) -> QFrame:
        section = self._create_section(
            "detectedProfanity", "Detections", add_placeholder=False
        )
        self.detection_count_label = QLabel(
            "No detections yet — scan a video to begin"
        )
        self.detection_count_label.setObjectName("detectionCount")
        self.detection_count_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        section.layout().addWidget(self.detection_count_label)
        self.effective_duration_label = QLabel("Effective censorship: 0.000 s")
        self.effective_duration_label.setObjectName("effectiveCensorshipDuration")
        self.effective_duration_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        section.layout().addWidget(self.effective_duration_label)
        self.review_widget = ProfanityReviewWidget()
        self.review_widget.matches_changed.connect(self._on_review_matches_changed)
        self.review_widget.detection_activated.connect(self._seek_to_detection)
        section.layout().addWidget(self.review_widget)
        return section

    def _on_review_matches_changed(self, matches: list[ProfanityMatch]) -> None:
        self.state.profanity_matches = list(matches)
        self.detection_count_label.setText(f"Detected profanity: {len(matches)}")
        self._refresh_censor_intervals()
        if hasattr(self, "preview_widget"):
            self.preview_widget.set_detections(matches)

    def _seek_to_detection(self, detection: ProfanityMatch) -> None:
        self.preview_widget.seek_to_detection(detection)

    def _create_scan_settings_section(self) -> QFrame:
        section = self._create_section(
            "scanSettings", "Scan settings", add_placeholder=False
        )
        self.scan_settings_widget = ScanSettingsWidget(self.state.scan_settings)
        self.scan_settings_widget.settings_changed.connect(self._on_scan_settings_changed)
        self.scan_settings_widget.scan_button.clicked.connect(self._start_scan)
        section.layout().addWidget(self.scan_settings_widget)
        return section

    def _on_scan_settings_changed(self, settings: ScanSettings) -> None:
        self.state.scan_settings = settings
        self._settings_store.save(settings)
        self._refresh_censor_intervals()

    def _create_video_input_section(self) -> QFrame:
        section = self._create_section(
            "videoInput", "", add_placeholder=False
        )
        layout = section.layout()

        self.video_drop_area = VideoDropArea()
        self.video_drop_area.video_dropped.connect(self.select_video)
        self.video_drop_area.unsupported_file_dropped.connect(
            self._show_unsupported_file_message
        )
        self.video_drop_area.choose_requested.connect(self._choose_video)
        layout.addWidget(self.video_drop_area)

        self.choose_video_button = self.video_drop_area.choose_button
        self.choose_video_button.setToolTip(
            "Choose an MP4, MOV, MKV, AVI, WEBM, or M4V file"
        )

        self.video_metadata = QWidget()
        metadata_layout = QGridLayout(self.video_metadata)
        metadata_layout.setContentsMargins(0, 8, 0, 0)

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
            position = metadata_layout.count()
            metadata_layout.addWidget(label, position // 2, position % 2)
        layout.addWidget(self.video_metadata)
        self.video_metadata.setVisible(False)
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
        self.state.word_timestamps.clear()
        self.state.profanity_matches.clear()
        self.state.censor_intervals.clear()
        self.state.last_export_path = None
        self._scan_completed = False
        self.export_controls.status_label.setText(
            "Export status: Waiting for enabled detections"
        )
        self.review_widget.set_matches([])
        self.preview_widget.set_source(video.path)
        self.export_controls.output_label.setText("Output: Not exported")
        self.video_filename_label.setText(f"Filename: {video.path.name}")
        self.video_path_label.setText(f"Full path: {video.path}")
        self.video_size_label.setText(f"File size: {format_file_size(video.size_bytes)}")
        self.video_duration_label.setText("Duration: Inspecting...")
        self.video_resolution_label.setText("Resolution: Inspecting...")
        self.video_codec_label.setText("Video codec: Inspecting...")
        self.audio_codec_label.setText("Audio codec: Inspecting...")
        self.video_status_label.setText("Input status: Inspecting media")
        self.video_metadata.setVisible(True)
        self._update_workflow_visibility()
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
        worker.cancelled.connect(self._on_media_inspection_cancelled)
        worker.completed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._release_inspection_thread(thread))
        self._inspection_workers[thread] = worker
        self.processing_progress.start("Inspecting media")
        self._update_cancel_button()
        thread.start()

    def _release_inspection_thread(self, thread: QThread) -> None:
        self._inspection_workers.pop(thread, None)
        thread.deleteLater()
        self._update_cancel_button()
        self._finish_pending_close_if_idle()
        if not self._has_active_work():
            self.processing_progress.finish()

    def _on_media_inspection_cancelled(self, path: Path) -> None:
        if self.state.selected_video is not None and self.state.selected_video.path == path:
            self.video_status_label.setText("Input status: Media inspection cancelled")
            self.statusBar().showMessage("Media inspection cancelled")

    def _on_media_inspected(self, path: Path, media_info: MediaInfo) -> None:
        if self.state.selected_video is None or self.state.selected_video.path != path:
            return
        self.state.media_info = media_info
        self._refresh_censor_intervals()
        self.video_duration_label.setText(f"Duration: {self._format_duration(media_info.duration)}")
        self.video_resolution_label.setText(
            f"Resolution: {media_info.width} x {media_info.height}"
        )
        self.video_codec_label.setText(f"Video codec: {media_info.video_codec}")
        audio_codec = media_info.audio_codec or "No audio"
        self.audio_codec_label.setText(f"Audio codec: {audio_codec}")
        self.video_status_label.setText("Input status: Ready to scan")
        self.statusBar().showMessage(f"Ready to scan {path.name}")
        self._update_workflow_visibility()

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
        self.scan_settings_widget.scan_button.setText("Scanning...")
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
        worker.status_changed.connect(self._on_processing_stage_changed)
        worker.succeeded.connect(self._on_transcription_succeeded)
        worker.failed.connect(self._on_transcription_failed)
        worker.cancelled.connect(self._on_transcription_cancelled)
        worker.completed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater)
        thread.finished.connect(self._release_transcription_thread)
        self._transcription_thread = thread
        self._transcription_worker = worker
        self.processing_progress.start("Loading Whisper model")
        self._update_cancel_button()
        thread.start()

    def _on_transcription_succeeded(self, result: ScanResult) -> None:
        self.state.word_timestamps = list(result.words)
        self.state.profanity_matches = list(result.matches)
        self.review_widget.set_matches(result.matches)
        count = len(result.matches)
        self.detection_count_label.setText(f"Detected profanity: {count}")
        self.statusBar().showMessage(f"Scan complete: {count} detections")
        self._scan_completed = True
        self._update_workflow_visibility()

    def _update_workflow_visibility(self) -> None:
        has_video = self.state.selected_video is not None
        has_results = self._scan_completed
        self.video_input_section.setVisible(not has_results)
        self.scan_settings_section.setVisible(has_video and not has_results)
        self.review_stage.setVisible(has_results)
        self.export_section.setVisible(has_results)

    def _refresh_censor_intervals(self) -> None:
        if self.state.media_info is None:
            self.state.censor_intervals = []
            self.effective_duration_label.setText(
                "Effective censorship: Media duration unavailable"
            )
            self._update_export_availability()
            return
        settings = self.state.scan_settings
        self.state.censor_intervals = build_censor_intervals(
            self.state.profanity_matches,
            self.state.media_info.duration,
            pre_padding_ms=settings.pre_padding_ms,
            post_padding_ms=settings.post_padding_ms,
        )
        duration = total_censorship_duration(self.state.censor_intervals)
        self.effective_duration_label.setText(
            f"Effective censorship: {duration:.3f} s"
        )
        self._update_export_availability()

    def _update_export_availability(self) -> None:
        if not hasattr(self, "export_controls"):
            return
        mode = self.state.scan_settings.censorship_mode
        ready = (
            self.state.selected_video is not None
            and self.state.media_info is not None
            and (
                self.state.media_info.audio_stream_count > 0 or mode == "Cut"
            )
            and bool(self.state.censor_intervals)
            and mode in ("Mute", "Beep", "Cut")
            and self._transcription_thread is None
            and self._export_thread is None
        )
        self.export_controls.export_button.setEnabled(ready)
        if hasattr(self, "export_action"):
            self.export_action.setEnabled(ready)
        if (
            self.state.media_info is not None
            and self.state.media_info.audio_stream_count == 0
            and mode != "Cut"
        ):
            status = "Export status: The source video has no audio stream"
        elif not self.state.censor_intervals:
            status = "Export status: Waiting for enabled detections"
        else:
            status = "Export status: Ready"
        current_status = self.export_controls.status_label.text()
        if self._export_thread is None and not current_status.endswith(
            ("Complete", "Failed")
        ):
            self.export_controls.status_label.setText(status)

    def _choose_export_path(self) -> None:
        if self.state.selected_video is None or self.state.media_info is None:
            return
        suggested = self.state.selected_video.path.with_name(
            f"{self.state.selected_video.path.stem}_censored.mp4"
        )
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Cleaned Video",
            str(suggested),
            "MP4 video (*.mp4)",
        )
        if not selected_path:
            return
        request = ExportRequest(
            input_path=self.state.selected_video.path,
            output_path=Path(selected_path),
            mode=self.state.scan_settings.censorship_mode,
            intervals=tuple(self.state.censor_intervals),
            media_duration=self.state.media_info.duration,
            beep_frequency_hz=self.state.scan_settings.beep_frequency_hz,
            audio_stream_count=self.state.media_info.audio_stream_count,
        )
        self._start_export(request)

    def _start_export(self, request: ExportRequest) -> None:
        if self._export_thread is not None:
            return
        self._set_scan_controls_enabled(False)
        self.export_controls.export_button.setText("Exporting...")
        self.export_controls.status_label.setText("Export status: Preparing")
        thread = QThread(self)
        worker = ExportWorker(request, self._exporter)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.status_changed.connect(self._on_export_status_changed)
        worker.progress_changed.connect(self.processing_progress.set_fraction)
        worker.succeeded.connect(self._on_export_succeeded)
        worker.failed.connect(self._on_export_failed)
        worker.cancelled.connect(self._on_export_cancelled)
        worker.completed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater)
        thread.finished.connect(self._release_export_thread)
        self._export_thread = thread
        self._export_worker = worker
        self.processing_progress.start("Preparing filters")
        self._update_cancel_button()
        thread.start()

    def _on_export_status_changed(self, status: str) -> None:
        self.processing_progress.set_stage(status)
        self.export_controls.status_label.setText(f"Export status: {status}")
        self.statusBar().showMessage(status)

    def _on_export_succeeded(self, output_path: Path) -> None:
        self.state.last_export_path = output_path
        self.export_controls.status_label.setText("Export status: Complete")
        self.export_controls.output_label.setText(f"Output: {output_path}")
        self.statusBar().showMessage(f"Export complete: {output_path.name}")

    def _on_export_failed(self, message: str) -> None:
        self.export_controls.status_label.setText("Export status: Failed")
        self.statusBar().showMessage("Export failed")
        QMessageBox.warning(self, "Could not export video", message)

    def _on_export_cancelled(self) -> None:
        self.export_controls.status_label.setText("Export status: Cancelled")
        self.export_controls.output_label.setText("Output: No file created")
        self.statusBar().showMessage("Export cancelled safely")

    def _release_export_thread(self) -> None:
        thread = self._export_thread
        self._export_thread = None
        self._export_worker = None
        self.export_controls.export_button.setText("Export Video")
        self._set_scan_controls_enabled(True)
        self._update_cancel_button()
        self._finish_pending_close_if_idle()
        self.processing_progress.finish()
        if thread is not None:
            thread.deleteLater()

    def _on_transcription_failed(self, message: str) -> None:
        self.statusBar().showMessage("Transcription failed")
        QMessageBox.warning(self, "Could not scan video", message)

    def _on_transcription_cancelled(self) -> None:
        self.detection_count_label.setText("Scan cancelled — no results changed")
        self.statusBar().showMessage("Scan cancelled safely")

    def _release_transcription_thread(self) -> None:
        thread = self._transcription_thread
        self._transcription_thread = None
        self._transcription_worker = None
        self.scan_settings_widget.scan_button.setText("Scan Video")
        self._set_scan_controls_enabled(True)
        self._update_cancel_button()
        self._finish_pending_close_if_idle()
        self.processing_progress.finish()
        if thread is not None:
            thread.deleteLater()

    def _set_scan_controls_enabled(self, enabled: bool) -> None:
        self.video_drop_area.setEnabled(enabled)
        self.choose_video_button.setEnabled(enabled)
        self.scan_settings_widget.setEnabled(enabled)
        self.review_widget.setEnabled(enabled)
        self.preview_widget.setEnabled(enabled)
        self.export_controls.setEnabled(enabled)
        if hasattr(self, "open_action"):
            self.open_action.setEnabled(enabled)
            if not enabled:
                self.export_action.setEnabled(False)
        if enabled:
            self._update_export_availability()

    def _on_processing_stage_changed(self, status: str) -> None:
        self.processing_progress.set_stage(status)
        self.statusBar().showMessage(status)

    def _has_active_work(self) -> bool:
        return bool(
            self._inspection_workers
            or self._transcription_thread is not None
            or self._export_thread is not None
        )

    def _update_cancel_button(self) -> None:
        active = self._has_active_work()
        self.cancel_button.setVisible(active)
        self.cancel_button.setEnabled(active)
        self.cancel_button.setText("Cancel Processing")

    def _cancel_active_operation(self) -> None:
        if not self._has_active_work():
            return
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Cancelling...")
        self.statusBar().showMessage("Cancelling active processing...")
        for worker in tuple(self._inspection_workers.values()):
            worker.cancel()
        if self._transcription_worker is not None:
            self._transcription_worker.cancel()
        if self._export_worker is not None:
            self._export_worker.cancel()

    def _finish_pending_close_if_idle(self) -> None:
        if self._close_when_idle and not self._has_active_work():
            QTimer.singleShot(0, self.close)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if not self._has_active_work():
            self.preview_widget.player.stop()
            event.accept()
            return
        response = QMessageBox.question(
            self,
            "Cancel processing and exit?",
            "A background operation is still running. Cancel it safely and close?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response == QMessageBox.StandardButton.Yes:
            self._close_when_idle = True
            self._cancel_active_operation()
        event.ignore()

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
        if title:
            title_label = QLabel(title)
            title_label.setProperty("sectionTitle", True)
            layout.addWidget(title_label)

        if add_placeholder:
            placeholder = QLabel("Coming in a later step")
            placeholder.setProperty("placeholder", True)
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder, 1)
        return section
