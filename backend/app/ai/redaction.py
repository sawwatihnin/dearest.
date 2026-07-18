"""PII detection and typed redaction service."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache

import spacy
from spacy.language import Language

from .types import RedactionItem, RedactionResult

SPACY_MODEL_CANDIDATES = ("en_core_web_lg", "en_core_web_md", "en_core_web_sm")
SPACY_ENTITY_TYPES = {"PERSON", "ORG", "GPE", "LOC", "FAC"}
PLACEHOLDER_BY_TYPE = {
    "PERSON": "[PERSON]",
    "ORG": "[ORGANIZATION]",
    "GPE": "[LOCATION]",
    "LOC": "[LOCATION]",
    "FAC": "[LOCATION]",
    "EMAIL": "[EMAIL]",
    "PHONE": "[PHONE]",
    "URL": "[URL]",
    "INSTAGRAM_HANDLE": "[INSTAGRAM_HANDLE]",
    "TWITTER_HANDLE": "[TWITTER_HANDLE]",
    "DISCORD_USERNAME": "[DISCORD_USERNAME]",
    "ADDRESS": "[ADDRESS]",
    "CREDIT_CARD": "[CREDIT_CARD]",
    "SSN": "[SSN]",
}

EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?!\w)")
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}(?!\d)"
)
URL_PATTERN = re.compile(r"(?:(?:https?://)|(?:www\.))[^\s]+", re.IGNORECASE)
INSTAGRAM_PATTERN = re.compile(
    r"(?i)\b(?:instagram|insta|ig)\s*[:\-]?\s*@([A-Za-z0-9._]{1,30})\b"
)
TWITTER_PATTERN = re.compile(
    r"(?i)\b(?:twitter|x)\s*[:\-]?\s*@([A-Za-z0-9_]{1,15})\b"
)
DISCORD_PATTERN = re.compile(r"(?<!\w)[A-Za-z0-9._]{2,32}#[0-9]{4}(?!\w)")
ADDRESS_PATTERN = re.compile(
    r"\b\d{1,6}\s+(?:[A-Za-z0-9.'-]+\s){0,5}"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl|Terrace|Ter|Circle|Cir)\b"
    r"(?:,?\s+[A-Za-z.\- ]+)?",
    re.IGNORECASE,
)
SSN_PATTERN = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
CREDIT_CARD_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _SpanMatch:
    start: int
    end: int
    pii_type: str
    value: str


class RedactionService:
    """Detect and redact PII before any public persistence or analysis."""

    def sanitize_story(self, text: str, title: str | None = None) -> RedactionResult:
        """Detect and redact PII across story text and title."""
        model = self._load_model()
        body_matches = self.detect(text)
        redacted_text = self._apply_redactions(text, body_matches)

        title_text = title or ""
        title_matches = self.detect(title_text) if title_text else []
        redacted_title = self._apply_redactions(title_text, title_matches) if title_text else ""

        combined_redactions = self._unique_redactions(
            [self._to_redaction_item(match) for match in body_matches]
            + [self._to_redaction_item(match) for match in title_matches]
        )
        return RedactionResult(
            redacted_text=redacted_text,
            redacted_title=redacted_title,
            pii_detected=bool(combined_redactions),
            redactions=combined_redactions,
            model_name=self._model_name(model),
            ner_executed=model.has_pipe("ner"),
        )

    def pass_through_story(self, text: str, title: str | None = None) -> RedactionResult:
        """Return trusted-source text unchanged while preserving pipeline shape."""
        model = self._load_model()
        return RedactionResult(
            redacted_text=text,
            redacted_title=title or "",
            pii_detected=False,
            redactions=[],
            model_name=self._model_name(model),
            ner_executed=False,
        )

    def detect(self, text: str) -> list[_SpanMatch]:
        """Return non-overlapping PII detections from spaCy and regex rules."""
        if not text:
            return []

        matches = self._detect_spacy_entities(text)
        matches.extend(self._detect_regex_entities(text))
        return self._coalesce_matches(matches)

    def _detect_spacy_entities(self, text: str) -> list[_SpanMatch]:
        model = self._load_model()
        doc = model(text)
        matches = [
            _SpanMatch(
                start=entity.start_char,
                end=entity.end_char,
                pii_type=entity.label_,
                value=entity.text,
            )
            for entity in doc.ents
            if entity.label_ in SPACY_ENTITY_TYPES
        ]
        return self._merge_adjacent_person_entities(text, matches)

    def _detect_regex_entities(self, text: str) -> list[_SpanMatch]:
        matches: list[_SpanMatch] = []
        matches.extend(self._find_pattern_matches(text, EMAIL_PATTERN, "EMAIL"))
        matches.extend(self._find_pattern_matches(text, PHONE_PATTERN, "PHONE"))
        matches.extend(self._find_pattern_matches(text, URL_PATTERN, "URL"))
        matches.extend(self._find_capture_group_matches(text, INSTAGRAM_PATTERN, "INSTAGRAM_HANDLE", group=1))
        matches.extend(self._find_capture_group_matches(text, TWITTER_PATTERN, "TWITTER_HANDLE", group=1))
        matches.extend(self._find_pattern_matches(text, DISCORD_PATTERN, "DISCORD_USERNAME"))
        matches.extend(self._find_pattern_matches(text, ADDRESS_PATTERN, "ADDRESS"))
        matches.extend(self._find_valid_credit_cards(text))
        matches.extend(self._find_pattern_matches(text, SSN_PATTERN, "SSN"))
        return matches

    def _apply_redactions(self, text: str, matches: list[_SpanMatch]) -> str:
        if not matches:
            return text

        redacted_text = text
        for match in sorted(matches, key=lambda item: item.start, reverse=True):
            placeholder = PLACEHOLDER_BY_TYPE.get(match.pii_type, "[REDACTED]")
            redacted_text = (
                redacted_text[: match.start] + placeholder + redacted_text[match.end :]
            )
        return redacted_text

    def _find_pattern_matches(
        self, text: str, pattern: re.Pattern[str], pii_type: str
    ) -> list[_SpanMatch]:
        matches: list[_SpanMatch] = []
        for match in pattern.finditer(text):
            start = match.start()
            end = match.end()
            value = match.group(0)
            if pii_type == "URL":
                value = value.rstrip(".,!?;:)]}")
                end = start + len(value)
            matches.append(
                _SpanMatch(
                    start=start,
                    end=end,
                    pii_type=pii_type,
                    value=value,
                )
            )
        return matches

    def _find_capture_group_matches(
        self,
        text: str,
        pattern: re.Pattern[str],
        pii_type: str,
        *,
        group: int,
    ) -> list[_SpanMatch]:
        matches: list[_SpanMatch] = []
        for match in pattern.finditer(text):
            start, end = match.span(group)
            value = match.group(group)
            matches.append(_SpanMatch(start=start, end=end, pii_type=pii_type, value=value))
        return matches

    def _find_valid_credit_cards(self, text: str) -> list[_SpanMatch]:
        matches: list[_SpanMatch] = []
        for match in CREDIT_CARD_PATTERN.finditer(text):
            candidate = match.group(0)
            digits_only = re.sub(r"\D", "", candidate)
            if 13 <= len(digits_only) <= 19 and self._passes_luhn(digits_only):
                matches.append(
                    _SpanMatch(
                        start=match.start(),
                        end=match.end(),
                        pii_type="CREDIT_CARD",
                        value=candidate,
                    )
                )
        return matches

    def _coalesce_matches(self, matches: list[_SpanMatch]) -> list[_SpanMatch]:
        if not matches:
            return []

        ordered = sorted(matches, key=lambda match: (match.start, -(match.end - match.start)))
        resolved: list[_SpanMatch] = []
        seen: set[tuple[int, int, str, str]] = set()
        cursor = -1
        for match in ordered:
            identity = (match.start, match.end, match.pii_type, match.value)
            if identity in seen:
                continue
            seen.add(identity)
            if match.start < cursor:
                continue
            resolved.append(match)
            cursor = match.end
        return resolved

    def _merge_adjacent_person_entities(
        self, text: str, matches: list[_SpanMatch]
    ) -> list[_SpanMatch]:
        if not matches:
            return []

        ordered = sorted(matches, key=lambda match: (match.start, match.end))
        merged: list[_SpanMatch] = []
        current: _SpanMatch | None = None

        for match in ordered:
            if current is None:
                current = match
                continue

            if (
                current.pii_type == "PERSON"
                and match.pii_type == "PERSON"
                and self._contains_only_name_joiners(text[current.end : match.start])
            ):
                current = _SpanMatch(
                    start=current.start,
                    end=match.end,
                    pii_type="PERSON",
                    value=text[current.start : match.end],
                )
                continue

            merged.append(current)
            current = match

        if current is not None:
            merged.append(current)
        return merged

    def _contains_only_name_joiners(self, separator: str) -> bool:
        stripped = separator.strip()
        if not stripped:
            return True
        return bool(re.fullmatch(r"[\s.'-]+", separator))

    def _to_redaction_item(self, match: _SpanMatch) -> RedactionItem:
        pii_type = match.pii_type
        if pii_type in {"GPE", "LOC", "FAC"}:
            pii_type = "LOCATION"
        elif pii_type == "ORG":
            pii_type = "ORGANIZATION"
        return RedactionItem(type=pii_type, value=match.value)

    def _unique_redactions(self, items: list[RedactionItem]) -> list[RedactionItem]:
        unique: list[RedactionItem] = []
        seen: set[tuple[str, str]] = set()
        for item in items:
            key = (item.type, item.value)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _passes_luhn(self, digits: str) -> bool:
        total = 0
        reverse_digits = digits[::-1]
        for index, character in enumerate(reverse_digits):
            number = int(character)
            if index % 2 == 1:
                number *= 2
                if number > 9:
                    number -= 9
            total += number
        return total % 10 == 0

    @lru_cache(maxsize=1)
    def _load_model(self) -> Language:
        """Load the strongest available English spaCy model once per process."""
        for model_name in SPACY_MODEL_CANDIDATES:
            try:
                model = spacy.load(model_name)
                logger.info("Dearest redaction model loaded: %s", self._model_name(model))
                return model
            except OSError:
                continue
        fallback = spacy.blank("en")
        logger.warning("Dearest redaction model fallback loaded: %s", self._model_name(fallback))
        return fallback

    def _model_name(self, model: Language) -> str:
        return str(model.meta.get("name") or model.lang or "unknown")
