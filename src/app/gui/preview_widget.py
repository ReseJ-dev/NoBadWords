"""Qt Multimedia video preview and detection navigation."""

from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.core.models import ProfanityMatch

DETECTION_CONTEXT_MS = 1000


def detection_seek_position_ms(
    detection: ProfanityMatch, context_ms: int = DETECTION_CONTEXT_MS
) -> int:
    """Return a non-negative seek position before a detection."""
    return max(0, round(detection.start * 1000) - context_ms)


class VideoPreviewWidget(QWidget):
    """Play media, seek its timeline, and navigate reviewed detections."""

    seek_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("videoPreview")
        self._detections: list[ProfanityMatch] = []
        self._current_detection_index = -1

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.video_output = QVideoWidget(self)
        self.video_output.setMinimumHeight(240)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_output)
        self.seek_requested.connect(self.player.setPosition)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.source_label = QLabel("Select a video to enable preview")
        self.source_label.setObjectName("previewSourceStatus")
        self.source_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.source_label)
        layout.addWidget(self.video_output, 1)

        timeline = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setObjectName("previewTimeline")
        self.timeline_slider.setRange(0, 0)
        self.duration_label = QLabel("00:00")
        timeline.addWidget(self.current_time_label)
        timeline.addWidget(self.timeline_slider, 1)
        timeline.addWidget(self.duration_label)
        layout.addLayout(timeline)

        playback = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.previous_detection_button = QPushButton("Previous Detection")
        self.next_detection_button = QPushButton("Next Detection")
        self.play_detection_button = QPushButton("Play Detection")
        for button in (
            self.play_button,
            self.pause_button,
            self.previous_detection_button,
            self.next_detection_button,
            self.play_detection_button,
        ):
            playback.addWidget(button)
        layout.addLayout(playback)

        self.play_button.clicked.connect(self.player.play)
        self.pause_button.clicked.connect(self.player.pause)
        self.timeline_slider.sliderMoved.connect(self.seek_requested)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.previous_detection_button.clicked.connect(self.previous_detection)
        self.next_detection_button.clicked.connect(self.next_detection)
        self.play_detection_button.clicked.connect(self.play_detection)
        self.play_button.setToolTip("Play the selected video")
        self.pause_button.setToolTip("Pause playback")
        self.previous_detection_button.setToolTip("Seek to the previous detection")
        self.next_detection_button.setToolTip("Seek to the next detection")
        self.play_detection_button.setToolTip("Play from one second before the detection")
        self.play_button.setShortcut("Space")
        self._update_navigation_buttons()

    def set_source(self, path: Path) -> None:
        """Load a local video without automatically starting playback."""
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        self.source_label.setText(f"Previewing: {path.name}")
        self.timeline_slider.setValue(0)
        self.current_time_label.setText("00:00")

    def set_detections(self, detections: Sequence[ProfanityMatch]) -> None:
        self._detections = list(detections)
        self._current_detection_index = -1
        self._update_navigation_buttons()

    def seek_to_detection(self, detection: ProfanityMatch) -> None:
        """Seek approximately one second before a detection."""
        try:
            self._current_detection_index = self._detections.index(detection)
        except ValueError:
            self._current_detection_index = -1
        self.seek_requested.emit(detection_seek_position_ms(detection))
        self._update_navigation_buttons()

    def previous_detection(self) -> None:
        if not self._detections:
            return
        if self._current_detection_index <= 0:
            self._current_detection_index = 0
        else:
            self._current_detection_index -= 1
        self.seek_to_detection(self._detections[self._current_detection_index])

    def next_detection(self) -> None:
        if not self._detections:
            return
        self._current_detection_index = min(
            self._current_detection_index + 1, len(self._detections) - 1
        )
        self.seek_to_detection(self._detections[self._current_detection_index])

    def play_detection(self) -> None:
        if not self._detections:
            return
        if self._current_detection_index < 0:
            self._current_detection_index = 0
        self.seek_to_detection(self._detections[self._current_detection_index])
        self.player.play()

    def _on_position_changed(self, position_ms: int) -> None:
        if not self.timeline_slider.isSliderDown():
            self.timeline_slider.setValue(position_ms)
        self.current_time_label.setText(self._format_time(position_ms))

    def _on_duration_changed(self, duration_ms: int) -> None:
        self.timeline_slider.setRange(0, max(0, duration_ms))
        self.duration_label.setText(self._format_time(duration_ms))

    def _update_navigation_buttons(self) -> None:
        has_detections = bool(self._detections)
        self.previous_detection_button.setEnabled(
            has_detections and self._current_detection_index > 0
        )
        self.next_detection_button.setEnabled(
            has_detections
            and self._current_detection_index < len(self._detections) - 1
        )
        self.play_detection_button.setEnabled(has_detections)

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        total_seconds = max(0, milliseconds) // 1000
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"
