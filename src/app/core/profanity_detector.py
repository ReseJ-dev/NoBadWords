"""Configurable, timestamp-aware Russian profanity detection."""

from dataclasses import dataclass
import re
from typing import Protocol, Sequence

from app.core.models import ProfanityMatch, WordTimestamp
from app.core.text_normalizer import normalize_russian_token


@dataclass(frozen=True, slots=True)
class ProfanityRule:
    """An anchored regular expression describing one profanity family."""

    name: str
    pattern: str


DEFAULT_RULES: tuple[ProfanityRule, ...] = (
    ProfanityRule("хуй", r"(?:на|по|за)?ху(?:й|я|е|ю|и|ем|ями|ев)"),
    ProfanityRule(
        "охуеть", r"оху(?:еть|ел|ела|ели|еный|еная|еное|еные|ено)"
    ),
    ProfanityRule("хуй-маска", r"х[*#@]й"),
    ProfanityRule(
        "пизда",
        r"(?:рас|от|за)?пизд(?:а|ы|е|у|ой|ою|ами|ец|ецом|еть|юк|юля|атый|атая|атое|ато)",
    ),
    ProfanityRule("пизда-маска", r"п[*#@](?:ц|зда|дец)"),
    ProfanityRule(
        "блядь", r"(?:бля|бл(?:яд|ят)(?:ь|и|ью|ей|я|ина|ство|ский)?|блеат(?:ь)?)"
    ),
    ProfanityRule("блядь-маска", r"бл[*#@](?:дь|ть)"),
    ProfanityRule(
        "ебать",
        r"(?:за|на|по|про|вы|до|пере)?еб(?:ать|ал|ала|али|ало|аный|аная|аное|аные|ану|анул|анула|ет|ут|ешь|ись|ло|ля|учий|учая|учее|учие)",
    ),
    ProfanityRule("еб", r"еб"),
    ProfanityRule("ебать-маска", r"е[*#@]ть"),
    ProfanityRule("сука", r"сук(?:а|и|у|е|ой|ою)"),
    ProfanityRule("мудак", r"мудак(?:а|у|ом|и|ов)?"),
    ProfanityRule("пидор", r"пид(?:ор|ар)(?:а|у|ом|ы|ов|ас)?"),
    ProfanityRule("гандон", r"гандон(?:а|у|ом|ы|ов)?"),
)


class ProfanityScanner(Protocol):
    """Interface used by the background scan worker."""

    def detect(
        self, words: Sequence[WordTimestamp], minimum_confidence: float
    ) -> list[ProfanityMatch]: ...


class ProfanityDetector:
    """Match normalized whole tokens against configurable Russian rules."""

    def __init__(
        self,
        rules: Sequence[ProfanityRule] = DEFAULT_RULES,
        exclusions: Sequence[str] = (),
        separated_letter_gap: float = 0.5,
    ) -> None:
        self._rules = tuple(
            (rule.name, re.compile(rf"^(?:{rule.pattern})$", re.IGNORECASE))
            for rule in rules
        )
        self._exclusions = {normalize_russian_token(word) for word in exclusions}
        self._separated_letter_gap = separated_letter_gap

    def detect(
        self, words: Sequence[WordTimestamp], minimum_confidence: float = 0.65
    ) -> list[ProfanityMatch]:
        """Return profanity matches while preserving source timestamps."""
        matches: list[ProfanityMatch] = []
        index = 0
        while index < len(words):
            word = words[index]
            normalized = normalize_russian_token(word.word)
            match = self._match_candidate(
                word.word,
                normalized,
                word.start,
                word.end,
                word.confidence,
                minimum_confidence,
            )
            if match is not None:
                matches.append(match)
                index += 1
                continue

            separated = self._match_separated_letters(words, index, minimum_confidence)
            if separated is not None:
                match, consumed = separated
                matches.append(match)
                index += consumed
                continue
            index += 1
        return matches

    def _match_separated_letters(
        self,
        words: Sequence[WordTimestamp],
        start_index: int,
        minimum_confidence: float,
    ) -> tuple[ProfanityMatch, int] | None:
        candidates: list[WordTimestamp] = []
        for word in words[start_index : start_index + 6]:
            normalized = normalize_russian_token(word.word)
            if len(normalized) != 1:
                break
            if candidates and word.start - candidates[-1].end > self._separated_letter_gap:
                break
            candidates.append(word)

        for length in range(len(candidates), 1, -1):
            group = candidates[:length]
            normalized = "".join(normalize_russian_token(word.word) for word in group)
            confidence = min(word.confidence for word in group)
            match = self._match_candidate(
                " ".join(word.word for word in group),
                normalized,
                group[0].start,
                group[-1].end,
                confidence,
                minimum_confidence,
            )
            if match is not None:
                return match, length
        return None

    def _match_candidate(
        self,
        original: str,
        normalized: str,
        start: float,
        end: float,
        confidence: float,
        minimum_confidence: float,
    ) -> ProfanityMatch | None:
        if not normalized or normalized in self._exclusions or confidence < minimum_confidence:
            return None
        for rule_name, pattern in self._rules:
            if pattern.fullmatch(normalized):
                return ProfanityMatch(
                    original_word=original,
                    normalized_word=normalized,
                    start=start,
                    end=end,
                    confidence=confidence,
                    matched_rule=rule_name,
                )
        return None
