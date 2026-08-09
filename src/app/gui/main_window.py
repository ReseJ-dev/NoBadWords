"""Main application window."""

from pathlib import Path

from PySide6.QtCore import Qt

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

from app.core.models import ApplicationState, VideoFile
from app.core.video import SUPPORTED_VIDEO_EXTENSIONS, format_file_size, is_supported_video
from app.gui.video_drop_area import VideoDropArea


class MainWindow(QMainWindow):
    """Top-level window for the video profanity censor workflow."""

    def __init__(self) -> None:
        super().__init__()
        self.state = ApplicationState()
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
        sections.addWidget(self._create_section("scanSettings", "Scan settings"), 0, 1)
        sections.addWidget(
            self._create_section("detectedProfanity", "Detected profanity"), 1, 0
        )
        sections.addWidget(self._create_section("exportControls", "Export controls"), 1, 1)
        sections.setRowStretch(0, 1)
        sections.setRowStretch(1, 1)
        sections.setColumnStretch(0, 1)
        sections.setColumnStretch(1, 1)
        layout.addLayout(sections, 1)

        return central_widget

    def _create_video_input_section(self) -> QFrame:
        section = self._create_section("videoInput", "Video input", add_placeholder=False)
        layout = section.layout()

        self.video_drop_area = VideoDropArea()
        self.video_drop_area.video_dropped.connect(self.select_video)
        self.video_drop_area.unsupported_file_dropped.connect(
            self._show_unsupported_file_message
        )
        layout.addWidget(self.video_drop_area)

        choose_button = QPushButton("Choose Video")
        choose_button.setObjectName("chooseVideoButton")
        choose_button.clicked.connect(self._choose_video)
        layout.addWidget(choose_button)

        self.video_filename_label = QLabel("Filename: No video selected")
        self.video_filename_label.setObjectName("videoFilename")
        self.video_path_label = QLabel("Full path: Not selected")
        self.video_path_label.setObjectName("videoPath")
        self.video_path_label.setWordWrap(True)
        self.video_size_label = QLabel("File size: Not available")
        self.video_size_label.setObjectName("videoSize")
        self.video_duration_label = QLabel("Detected duration: Not scanned")
        self.video_duration_label.setObjectName("videoDuration")
        self.video_status_label = QLabel("Input status: Waiting for a video")
        self.video_status_label.setObjectName("videoStatus")
        for label in (
            self.video_filename_label,
            self.video_path_label,
            self.video_size_label,
            self.video_duration_label,
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
        self.video_filename_label.setText(f"Filename: {video.path.name}")
        self.video_path_label.setText(f"Full path: {video.path}")
        self.video_size_label.setText(f"File size: {format_file_size(video.size_bytes)}")
        self.video_duration_label.setText("Detected duration: Not scanned")
        self.video_status_label.setText("Input status: Ready to scan")
        self.statusBar().showMessage(f"Selected {video.path.name}")
        return True

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
