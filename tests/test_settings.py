"""Tests for scan configuration defaults, persistence, and GUI behavior."""

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QComboBox

from app.core.config import SettingsStore
from app.core.models import ScanSettings
from app.gui.main_window import MainWindow


def create_store(path: Path) -> SettingsStore:
    return SettingsStore(QSettings(str(path), QSettings.Format.IniFormat))


def test_scan_settings_defaults() -> None:
    settings = ScanSettings()

    assert settings.language == "Russian"
    assert settings.whisper_model == "base"
    assert settings.device == "Auto"
    assert settings.censorship_mode == "Beep"
    assert settings.confidence == 0.65
    assert settings.pre_padding_ms == 120
    assert settings.post_padding_ms == 180
    assert settings.beep_frequency_hz == 1000


def test_settings_store_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "preferences.ini"
    expected = ScanSettings(
        language="English",
        whisper_model="small",
        device="CPU",
        censorship_mode="Mute",
        confidence=0.8,
        pre_padding_ms=90,
        post_padding_ms=210,
        beep_frequency_hz=1200,
    )

    create_store(path).save(expected)

    assert create_store(path).load() == expected


def test_invalid_persisted_values_fall_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "invalid.ini"
    settings = QSettings(str(path), QSettings.Format.IniFormat)
    settings.setValue("scan/language", "Klingon")
    settings.setValue("scan/confidence", 7)
    settings.setValue("scan/pre_padding_ms", -1)
    settings.sync()

    restored = create_store(path).load()

    assert restored.language == "Russian"
    assert restored.confidence == 0.65
    assert restored.pre_padding_ms == 120


def test_window_restores_settings_and_controls_beep_input(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])
    store = create_store(tmp_path / "window.ini")
    store.save(ScanSettings(censorship_mode="Mute", beep_frequency_hz=1500))
    window = MainWindow(settings_store=store)
    controls = window.scan_settings_widget

    assert controls.mode_combo.currentText() == "Mute"
    assert controls.beep_frequency_spin.value() == 1500
    assert not controls.beep_frequency_spin.isEnabled()

    controls.mode_combo.setCurrentText("Beep")
    application.processEvents()

    assert controls.beep_frequency_spin.isEnabled()
    assert window.state.scan_settings.censorship_mode == "Beep"
    assert create_store(tmp_path / "window.ini").load().censorship_mode == "Beep"

    window.close()
    application.processEvents()


def test_scan_controls_offer_required_choices(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=create_store(tmp_path / "choices.ini"))
    controls = window.scan_settings_widget

    def items(combo: QComboBox) -> list[str]:
        return [combo.itemText(index) for index in range(combo.count())]

    assert items(controls.language_combo) == ["Russian", "English", "Auto"]
    assert items(controls.model_combo) == ["tiny", "base", "small", "medium", "large-v3"]
    assert items(controls.device_combo) == ["Auto", "CPU", "CUDA"]
    assert items(controls.mode_combo) == ["Beep", "Mute", "Cut"]
    assert controls.scan_button.text() == "Scan Video"

    window.close()
    application.processEvents()
