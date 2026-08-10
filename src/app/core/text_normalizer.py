"""Russian text normalization for conservative profanity matching."""

import re
import unicodedata

_CYRILLIC_RE = re.compile(r"[а-яё]", re.IGNORECASE)
_DISALLOWED_RE = re.compile(r"[^а-яa-z0-9*#@\-\s]", re.IGNORECASE)
_SEPARATORS_RE = re.compile(r"[\s\-]+")
_REPEATED_RE = re.compile(r"(.)\1+", re.IGNORECASE)
_LATIN_LOOKALIKES = str.maketrans(
    {"a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у"}
)


def normalize_russian_token(text: str) -> str:
    """Normalize one Russian token or a deliberately separated spelling."""
    normalized = unicodedata.normalize("NFKC", text).casefold().replace("ё", "е")
    normalized = _DISALLOWED_RE.sub("", normalized)
    if _CYRILLIC_RE.search(normalized):
        normalized = normalized.translate(_LATIN_LOOKALIKES)
    normalized = _SEPARATORS_RE.sub("", normalized)
    normalized = re.sub(r"^йо", "е", normalized)
    return _REPEATED_RE.sub(r"\1", normalized)

