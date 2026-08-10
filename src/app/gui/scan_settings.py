"""Controls for speech scanning and censorship preferences."""

from typing import cast

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QPushButton,
    QSpinBox,
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
        form = QFormLayout()

        self.language_combo = self._combo("languageSelector", LANGUAGES, settings.language)
        form.addRow("Language", self.language_combo)
        self.model_combo = self._combo(
            "modelSelector", WHISPER_MODELS, settings.whisper_model
        )
        form.addRow("Whisper model", self.model_combo)
        self.device_combo = self._combo("deviceSelector", DEVICES, settings.device)
        form.addRow("Device", self.device_combo)
        self.mode_combo = self._combo(
            "censorshipModeSelector", CENSORSHIP_MODES, settings.censorship_mode
        )
        form.addRow("Censorship mode", self.mode_combo)

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
        layout.addLayout(form)

        self.scan_button = QPushButton("Scan Video")
        self.scan_button.setObjectName("scanVideoButton")
        self.scan_button.setToolTip("Transcribe the selected video's speech.")
        layout.addWidget(self.scan_button)

        self._connect_changes()
        self._update_beep_frequency_state(settings.censorship_mode)

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

    def _emit_settings(self) -> None:
        self.settings_changed.emit(self.current_settings())
