"""Controls for speech scanning and censorship preferences."""

from typing import cast

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.core.config import CENSORSHIP_MODES, DEVICES, LANGUAGES, WHISPER_MODELS
from app.core.models import CensorshipMode, Device, Language, ScanSettings, WhisperModel


class ScanSettingsWidget(QWidget):
    """Edit typed scan settings without performing a scan."""

    settings_changed = Signal(object)

    def __init__(
        self, settings: ScanSettings, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("scanSettingsControls")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        quick = QHBoxLayout()
        quick.setSpacing(12)

        self.language_combo = self._combo("languageSelector", LANGUAGES, settings.language)
        quick.addWidget(self._quick_field("Language", self.language_combo))
        self.model_combo = self._combo(
            "modelSelector", WHISPER_MODELS, settings.whisper_model
        )
        quick.addWidget(self._quick_field("Model", self.model_combo))
        self.device_combo = self._combo("deviceSelector", DEVICES, settings.device)
        self.mode_combo = self._combo(
            "censorshipModeSelector", CENSORSHIP_MODES, settings.censorship_mode
        )
        quick.addWidget(self._quick_field("Censor with", self.mode_combo))
        layout.addLayout(quick)

        sensitivity = QHBoxLayout()
        sensitivity.addWidget(QLabel("Sensitivity"))
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(0, 100)
        self.sensitivity_slider.setValue(round(settings.confidence * 100))
        sensitivity.addWidget(self.sensitivity_slider, 1)
        self.sensitivity_value = QLabel(f"{round(settings.confidence * 100)}%")
        sensitivity.addWidget(self.sensitivity_value)
        layout.addLayout(sensitivity)

        self.advanced_button = QToolButton()
        self.advanced_button.setObjectName("advancedSettingsButton")
        self.advanced_button.setText("Advanced settings")
        self.advanced_button.setCheckable(True)
        self.advanced_button.setArrowType(Qt.ArrowType.RightArrow)
        layout.addWidget(self.advanced_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.advanced_panel = QWidget()
        form = QFormLayout(self.advanced_panel)
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        form.addRow("Device", self.device_combo)

        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setObjectName("confidenceInput")
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.setDecimals(2)
        self.confidence_spin.setValue(settings.confidence)
        form.addRow("Confidence", self.confidence_spin)

        self.pre_padding_spin = self._millisecond_spin(
            "prePaddingInput", settings.pre_padding_ms
        )
        form.addRow("Pre-padding", self.pre_padding_spin)
        self.post_padding_spin = self._millisecond_spin(
            "postPaddingInput", settings.post_padding_ms
        )
        form.addRow("Post-padding", self.post_padding_spin)

        self.beep_frequency_spin = QSpinBox()
        self.beep_frequency_spin.setObjectName("beepFrequencyInput")
        self.beep_frequency_spin.setRange(100, 20000)
        self.beep_frequency_spin.setSuffix(" Hz")
        self.beep_frequency_spin.setValue(settings.beep_frequency_hz)
        form.addRow("Beep frequency", self.beep_frequency_spin)
        self.advanced_panel.setVisible(False)
        layout.addWidget(self.advanced_panel)

        self.scan_button = QPushButton("Scan Video")
        self.scan_button.setObjectName("scanVideoButton")
        self.scan_button.setProperty("primary", True)
        self.scan_button.setToolTip("Transcribe the selected video's speech.")
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.scan_button)
        layout.addLayout(actions)

        self._connect_changes()
        self.advanced_button.toggled.connect(self._toggle_advanced)
        self.sensitivity_slider.valueChanged.connect(self._on_sensitivity_changed)
        self.confidence_spin.valueChanged.connect(self._on_confidence_changed)
        self._update_beep_frequency_state(settings.censorship_mode)
        self.language_combo.setToolTip("Speech language expected in the video")
        self.model_combo.setToolTip("Larger models are more accurate but slower")
        self.device_combo.setToolTip("Auto uses CUDA when available, otherwise CPU")
        self.mode_combo.setToolTip("Choose how reviewed profanity will be removed")
        self.confidence_spin.setToolTip(
            "Ignore words below this recognition confidence"
        )
        self.pre_padding_spin.setToolTip("Censor this much audio before each word")
        self.post_padding_spin.setToolTip("Censor this much audio after each word")
        self.beep_frequency_spin.setToolTip("Frequency of the censor tone")

    def current_settings(self) -> ScanSettings:
        """Build an immutable settings snapshot from the controls."""
        return ScanSettings(
            language=cast(Language, self.language_combo.currentText()),
            whisper_model=cast(WhisperModel, self.model_combo.currentText()),
            device=cast(Device, self.device_combo.currentText()),
            censorship_mode=cast(CensorshipMode, self.mode_combo.currentText()),
            confidence=self.confidence_spin.value(),
            pre_padding_ms=self.pre_padding_spin.value(),
            post_padding_ms=self.post_padding_spin.value(),
            beep_frequency_hz=self.beep_frequency_spin.value(),
        )

    @staticmethod
    def _combo(object_name: str, choices: tuple[str, ...], current: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName(object_name)
        combo.addItems(choices)
        combo.setCurrentText(current)
        return combo

    @staticmethod
    def _quick_field(label: str, control: QWidget) -> QWidget:
        field = QWidget()
        layout = QVBoxLayout(field)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        caption = QLabel(label)
        caption.setProperty("fieldCaption", True)
        layout.addWidget(caption)
        layout.addWidget(control)
        return field

    @staticmethod
    def _millisecond_spin(object_name: str, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setObjectName(object_name)
        spin.setRange(0, 5000)
        spin.setSuffix(" ms")
        spin.setValue(value)
        return spin

    def _connect_changes(self) -> None:
        for combo in (
            self.language_combo,
            self.model_combo,
            self.device_combo,
            self.mode_combo,
        ):
            combo.currentTextChanged.connect(self._emit_settings)
        self.mode_combo.currentTextChanged.connect(self._update_beep_frequency_state)
        for spin in (
            self.confidence_spin,
            self.pre_padding_spin,
            self.post_padding_spin,
            self.beep_frequency_spin,
        ):
            spin.valueChanged.connect(self._emit_settings)

    def _update_beep_frequency_state(self, mode: str) -> None:
        self.beep_frequency_spin.setEnabled(mode == "Beep")

    def _toggle_advanced(self, expanded: bool) -> None:
        self.advanced_panel.setVisible(expanded)
        self.advanced_button.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )

    def _on_sensitivity_changed(self, value: int) -> None:
        self.sensitivity_value.setText(f"{value}%")
        self.confidence_spin.setValue(value / 100)

    def _on_confidence_changed(self, value: float) -> None:
        slider_value = round(value * 100)
        if self.sensitivity_slider.value() != slider_value:
            self.sensitivity_slider.setValue(slider_value)

    def _emit_settings(self) -> None:
        self.settings_changed.emit(self.current_settings())
