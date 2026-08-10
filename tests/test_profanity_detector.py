"""Tests for conservative Russian profanity normalization and matching."""

import pytest

from app.core.models import WordTimestamp
from app.core.profanity_detector import ProfanityDetector, ProfanityRule
from app.core.text_normalizer import normalize_russian_token


def word(text: str, confidence: float = 0.9, start: float = 0.0) -> WordTimestamp:
    return WordTimestamp(text, start, start + 0.3, confidence)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("ХУЙ!", "хуй"),
        ("ЁБАНЫЙ", "ебаный"),
        ("хууууй", "хуй"),
        ("xуй", "хуй"),
        ("х-у-й", "хуй"),
        (" х у й ", "хуй"),
        ("п***ц", "п*ц"),
    ],
)
def test_russian_normalization(source: str, expected: str) -> None:
    assert normalize_russian_token(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        "хуй",
        "нахуй",
        "охуенно",
        "хуя",
        "пиздец",
        "блядь",
        "блять",
        "бля",
        "ёб",
        "заебал",
        "ёбаный",
        "сука",
        "мудаком",
        "пидорас",
        "х*й",
        "п***ц",
        "бл*дь",
    ],
)
def test_detects_profanity_and_variants(source: str) -> None:
    matches = ProfanityDetector().detect([word(source)], 0.65)

    assert len(matches) == 1
    assert matches[0].original_word == source
    assert matches[0].enabled is True


@pytest.mark.parametrize(
    "source",
    [
        "страхуй",
        "подстрахуй",
        "корабль",
        "ребёнок",
        "употреблять",
        "муравей",
        "сукачёв",
        "педагог",
    ],
)
def test_does_not_match_legitimate_words(source: str) -> None:
    assert ProfanityDetector().detect([word(source)], 0.65) == []


def test_confidence_threshold_is_respected() -> None:
    detector = ProfanityDetector()

    assert detector.detect([word("сука", confidence=0.64)], 0.65) == []
    assert len(detector.detect([word("сука", confidence=0.65)], 0.65)) == 1


def test_configurable_whitelist_suppresses_match() -> None:
    detector = ProfanityDetector(exclusions=["сука"])

    assert detector.detect([word("СУКА!")], 0.0) == []


def test_configurable_rules_use_whole_token_matching() -> None:
    detector = ProfanityDetector(rules=[ProfanityRule("test", r"мат")])

    assert len(detector.detect([word("мат")], 0.0)) == 1
    assert detector.detect([word("математика")], 0.0) == []


def test_separated_letters_are_joined_with_combined_timestamps() -> None:
    words = [
        word("х", start=1.0),
        word("у", start=1.35),
        word("й", start=1.7),
    ]

    match = ProfanityDetector().detect(words, 0.65)[0]

    assert match.original_word == "х у й"
    assert match.normalized_word == "хуй"
    assert match.start == 1.0
    assert match.end == 2.0
