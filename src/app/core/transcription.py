"""Speech transcription backed by faster-whisper."""

from collections.abc import Callable
import logging
from pathlib import Path
from typing import Any, Protocol

from app.core.cancellation import CancellationToken, OperationCancelled
from app.core.models import Device, ScanSettings, WordTimestamp

StatusCallback = Callable[[str], None]
ModelFactory = Callable[..., Any]
LOGGER = logging.getLogger(__name__)


class TranscriptionError(RuntimeError):
    """Raised when speech transcription cannot be completed."""


class Transcriber(Protocol):
    """Interface consumed by the GUI background worker."""

    def transcribe(
        self,
        path: Path,
        settings: ScanSettings,
        status_callback: StatusCallback | None = None,
        cancellation_token: CancellationToken | None = None,
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


def _is_cuda_compatibility_error(error: Exception) -> bool:
    """Identify expected CUDA/backend errors that are safe to retry on CPU."""
    message = str(error).casefold()
    compatibility_markers = (
        "requested float16 compute type",
        "target device or backend",
        "cuda driver",
        "cuda runtime",
        "cuda error",
        "cudnn",
        "cublas",
        "no cuda capable device",
        "invalid device ordinal",
    )
    return any(marker in message for marker in compatibility_markers) or (
        "compute type" in message and "support" in message
    )


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
        cancellation_token: CancellationToken | None = None,
    ) -> list[WordTimestamp]:
        """Transcribe a media file and return word-level timestamps."""
        if not path.is_file():
            raise TranscriptionError("The selected video file no longer exists.")
        notify = status_callback or (lambda status: None)
        token = cancellation_token or CancellationToken()
        token.raise_if_cancelled()
        device, compute_type = resolve_device(settings.device, self._cuda_checker)
        LOGGER.info(
            "Whisper runtime selected: device=%s compute_type=%s",
            device,
            compute_type,
        )
        cache_key = (settings.whisper_model, device, compute_type)

        model = self._models.get(cache_key)
        if model is None:
            notify("Loading Whisper model")
            token.raise_if_cancelled()
            try:
                model = self._model_factory(
                    settings.whisper_model,
                    device=device,
                    compute_type=compute_type,
                )
            except Exception as error:
                if device != "cuda" or not _is_cuda_compatibility_error(error):
                    raise TranscriptionError(
                        f"Could not load the Whisper model: {error}"
                    ) from error
                LOGGER.warning(
                    "CUDA Whisper initialization failed; retrying with "
                    "device=cpu compute_type=int8",
                    exc_info=error,
                )
                notify("CUDA unavailable — using CPU fallback (int8)")
                token.raise_if_cancelled()
                device, compute_type = "cpu", "int8"
                cache_key = (settings.whisper_model, device, compute_type)
                model = self._models.get(cache_key)
                if model is None:
                    try:
                        model = self._model_factory(
                            settings.whisper_model,
                            device=device,
                            compute_type=compute_type,
                        )
                    except Exception as fallback_error:
                        raise TranscriptionError(
                            "Could not load the Whisper model after CPU fallback: "
                            f"{fallback_error}"
                        ) from fallback_error
                LOGGER.info(
                    "Whisper runtime fallback selected: device=cpu compute_type=int8"
                )
            self._models[cache_key] = model

        notify("Transcribing")
        token.raise_if_cancelled()
        language = {"Russian": "ru", "English": "en", "Auto": None}[settings.language]
        try:
            segments, _ = model.transcribe(
                str(path), language=language, word_timestamps=True
            )
            return self._collect_words(segments, token)
        except OperationCancelled:
            raise
        except Exception as error:
            raise TranscriptionError(f"Transcription failed: {error}") from error

    @staticmethod
    def _collect_words(
        segments: object, cancellation_token: CancellationToken
    ) -> list[WordTimestamp]:
        words: list[WordTimestamp] = []
        for segment in segments:
            cancellation_token.raise_if_cancelled()
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
