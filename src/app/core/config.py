"""Desktop application configuration."""

import logging
from typing import cast

from PySide6.QtCore import QSettings

from app.core.models import CensorshipMode, Device, Language, ScanSettings, WhisperModel

DEFAULT_LOG_LEVEL: int = logging.INFO
LOG_FORMAT: str = "%(asctime)s %(levelname)s %(name)s: %(message)s"

LANGUAGES: tuple[str, ...] = ("Russian", "English", "Auto")
WHISPER_MODELS: tuple[str, ...] = ("tiny", "base", "small", "medium", "large-v3")
DEVICES: tuple[str, ...] = ("Auto", "CPU", "CUDA")
CENSORSHIP_MODES: tuple[str, ...] = ("Beep", "Mute", "Cut")


def configure_logging(level: int = DEFAULT_LOG_LEVEL) -> None:
    """Configure application-wide logging."""
    logging.basicConfig(level=level, format=LOG_FORMAT)


class SettingsStore:
    """Persist scan preferences through Qt's platform settings API."""

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings if settings is not None else QSettings()

    def load(self) -> ScanSettings:
        """Load preferences, falling back safely when stored values are invalid."""
        defaults = ScanSettings()
        return ScanSettings(
            language=cast(
                Language, self._choice("language", defaults.language, LANGUAGES)
            ),
            whisper_model=cast(
                WhisperModel,
                self._choice("whisper_model", defaults.whisper_model, WHISPER_MODELS),
            ),
            device=cast(Device, self._choice("device", defaults.device, DEVICES)),
            censorship_mode=cast(
                CensorshipMode,
                self._choice(
                    "censorship_mode", defaults.censorship_mode, CENSORSHIP_MODES
                ),
            ),
            confidence=self._float("confidence", defaults.confidence, 0.0, 1.0),
            pre_padding_ms=self._int(
                "pre_padding_ms", defaults.pre_padding_ms, 0, 5000
            ),
            post_padding_ms=self._int(
                "post_padding_ms", defaults.post_padding_ms, 0, 5000
            ),
            beep_frequency_hz=self._int(
                "beep_frequency_hz", defaults.beep_frequency_hz, 100, 20000
            ),
        )

    def save(self, settings: ScanSettings) -> None:
        """Write all supported preferences."""
        for key, value in (
            ("language", settings.language),
            ("whisper_model", settings.whisper_model),
            ("device", settings.device),
            ("censorship_mode", settings.censorship_mode),
            ("confidence", settings.confidence),
            ("pre_padding_ms", settings.pre_padding_ms),
            ("post_padding_ms", settings.post_padding_ms),
            ("beep_frequency_hz", settings.beep_frequency_hz),
        ):
            self._settings.setValue(f"scan/{key}", value)
        self._settings.sync()

    def _choice(self, key: str, default: str, allowed: tuple[str, ...]) -> str:
        value = str(self._settings.value(f"scan/{key}", default))
        return value if value in allowed else default

    def _float(self, key: str, default: float, minimum: float, maximum: float) -> float:
        try:
            value = float(self._settings.value(f"scan/{key}", default))
        except (TypeError, ValueError):
            return default
        return value if minimum <= value <= maximum else default

    def _int(self, key: str, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(self._settings.value(f"scan/{key}", default))
        except (TypeError, ValueError):
            return default
        return value if minimum <= value <= maximum else default
