"""Main application window."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Top-level window for the video profanity censor workflow."""

    def __init__(self) -> None:
        super().__init__()
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
        sections.addWidget(self._create_section("videoInput", "Video input"), 0, 0)
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

    def _create_section(self, object_name: str, title: str) -> QFrame:
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

        placeholder = QLabel("Coming in a later step")
        placeholder.setProperty("placeholder", True)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder, 1)
        return section

