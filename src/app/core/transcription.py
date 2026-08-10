"""Speech transcription backed by faster-whisper."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from app.core.models import Device, ScanSettings, WordTimestamp

StatusCallback = Callable[[str], None]
ModelFactory = Callable[..., Any]


class TranscriptionError(RuntimeError):
    """Raised when speech transcription cannot be completed."""


class Transcriber(Protocol):
    """Interface consumed by the GUI background worker."""

    def transcribe(
        self,
        path: Path,
        settings: ScanSettings,
        status_callback: StatusCallback | None = None,
    ) -> list[WordTimestamp]: ...


def cuda_is_usable() -> bool:
    """Return whether CTranslate2 reports at least one usable CUDA device."""
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except (ImportError, OSError, RuntimeError):
        return False


def resolve_device(
    requested: Device, cuda_checker: Callable[[], bool] = cuda_is_usable
) -> tuple[str, str]:
    """Resolve a user device choice to faster-whisper device and compute type."""
    if requested == "Auto":
        requested = "CUDA" if cuda_checker() else "CPU"
    if requested == "CUDA":
        return "cuda", "float16"
    return "cpu", "int8"


def _default_model_factory(model_name: str, **kwargs: object) -> Any:
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise TranscriptionError(
            "faster-whisper is not installed. Install the application dependencies "
            "and try again."
        ) from error
    return WhisperModel(model_name, **kwargs)


class TranscriptionService:
    """Load, cache, and run faster-whisper models."""

    def __init__(
        self,
        model_factory: ModelFactory = _default_model_factory,
        cuda_checker: Callable[[], bool] = cuda_is_usable,
    ) -> None:
        self._model_factory = model_factory
        self._cuda_checker = cuda_checker
        self._models: dict[tuple[str, str, str], Any] = {}

    def transcribe(
        self,
        path: Path,
        settings: ScanSettings,
        status_callback: StatusCallback | None = None,
    ) -> list[WordTimestamp]:
        """Transcribe a media file and return word-level timestamps."""
        if not path.is_file():
            raise TranscriptionError("The selected video file no longer exists.")
        notify = status_callback or (lambda status: None)
        device, compute_type = resolve_device(settings.device, self._cuda_checker)
        cache_key = (settings.whisper_model, device, compute_type)

        model = self._models.get(cache_key)
        if model is None:
            notify("Loading Whisper model")
            try:
                model = self._model_factory(
                    settings.whisper_model,
                    device=device,
                    compute_type=compute_type,
                )
            except TranscriptionError:
                raise
            except Exception as error:
                raise TranscriptionError(f"Could not load the Whisper model: {error}") from error
            self._models[cache_key] = model

        notify("Transcribing")
        language = {"Russian": "ru", "English": "en", "Auto": None}[settings.language]
        try:
            segments, _ = model.transcribe(
                str(path), language=language, word_timestamps=True
            )
            return self._collect_words(segments)
        except Exception as error:
            raise TranscriptionError(f"Transcription failed: {error}") from error

    @staticmethod
    def _collect_words(segments: object) -> list[WordTimestamp]:
        words: list[WordTimestamp] = []
        for segment in segments:
            for word in getattr(segment, "words", None) or ():
                start = getattr(word, "start", None)
                end = getattr(word, "end", None)
                text = str(getattr(word, "word", "")).strip()
                if start is None or end is None or not text:
                    continue
                words.append(
                    WordTimestamp(
                        word=text,
                        start=float(start),
                        end=float(end),
                        confidence=float(getattr(word, "probability", 0.0) or 0.0),
                    )
                )
        return words

