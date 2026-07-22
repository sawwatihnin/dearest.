"""Moderation service."""

from __future__ import annotations

import re

from .types import ModerationResult
from ..telemetry import registry

CONTENT_WARNING_TERMS = {
    "abuse",
    "abusive",
    "assault",
    "discrimination",
    "grief",
    "hurt myself",
    "identity",
    "illness",
    "self-harm",
    "self harm",
    "suicide",
    "trauma",
    "violent",
    "violence",
    "war",
}

BLOCK_PATTERNS = {
    "self_harm_intent": re.compile(
        r"\b(?:i|i'm|im|i’ve|i've|ive)\s+(?:want to|plan to|am going to|will|need to|should)\s+"
        r"(?:kill myself|hurt myself|end my life|commit suicide)\b"
    ),
    "self_harm_instruction": re.compile(
        r"\b(?:how to|best way to|ways to)\s+(?:kill myself|hurt myself|end my life|commit suicide)\b"
    ),
    "harassment_self_harm": re.compile(r"\b(?:kill yourself|go kill yourself|you should kill yourself)\b"),
    "violent_threat": re.compile(
        r"\b(?:i|we)\s+(?:want to|plan to|am going to|will|should)\s+"
        r"(?:kill|hurt|shoot|stab|beat)\s+(?:you|him|her|them|someone|people|my\s+\w+)\b"
    ),
    "violence_instruction": re.compile(
        r"\b(?:how to|best way to|ways to)\s+(?:kill|hurt|shoot|stab|beat)\s+(?:someone|people|him|her|them)\b"
    ),
}

MEMOIR_CONTEXT_PATTERNS = (
    re.compile(r"\b(?:i survived|i lived through|i remember|when i was|growing up|my childhood|my father|my mother)\b"),
    re.compile(r"\b(?:was abused|experienced abuse|survived abuse|saw violence|lived through war)\b"),
    re.compile(r"\b(?:grief|loss|heartbreak|trauma|identity|illness|discrimination)\b"),
)

SELF_HARM_REFERENCE_PATTERN = re.compile(
    r"\b(?:self[- ]harm(?:ing)?|suicid(?:e|al)|hurt(?:ing)? myself)\b"
)
SELF_HARM_RECOVERY_CONTEXT_PATTERN = re.compile(
    r"\b(?:surviv(?:e|ed|ing)|recover(?:ed|ing|y)|heal(?:ed|ing)|"
    r"years? ago|in the past|used to|no longer|formerly|previously)\b"
)


def is_safe_content(text: str) -> bool:
    """Moderate for active harm while allowing autobiographical and reflective writing."""
    return ModerationService().analyze(text).safe


class UnsafeContentError(ValueError):
    """Raised when a story fails moderation and must not be persisted."""


class ModerationService:
    """Separates moderation concerns from other AI analysis stages."""

    def analyze(self, text: str) -> ModerationResult:
        """Allow memoir and trauma narratives while blocking direct harm intent or instructions."""
        lowered = text.lower()
        flags = [term for term in sorted(CONTENT_WARNING_TERMS) if term in lowered]
        blocked_rules = [rule for rule, pattern in BLOCK_PATTERNS.items() if pattern.search(lowered)]
        memoir_context_hits = [pattern.pattern for pattern in MEMOIR_CONTEXT_PATTERNS if pattern.search(lowered)]

        # A bare/current self-harm disclosure is too ambiguous to publish safely. Preserve
        # clearly historical recovery writing, but otherwise escalate instead of treating
        # the phrase as a passive content note.
        if (
            SELF_HARM_REFERENCE_PATTERN.search(lowered)
            and not SELF_HARM_RECOVERY_CONTEXT_PATTERN.search(lowered)
            and "self_harm_reference" not in blocked_rules
        ):
            blocked_rules.append("self_harm_reference")

        # Memoir context softens narrative discussion of painful topics, but never overrides
        # direct self-harm intent, threats, or instructions.
        contextual_adjustment = 0.2 if memoir_context_hits and not blocked_rules else 0.0
        risk_score = round(min(len(flags) * 0.08 + len(blocked_rules) * 0.6 - contextual_adjustment, 1.0), 3)
        safe = not blocked_rules
        if not safe:
            registry.increment("dearest_moderation_blocks_total")
        return ModerationResult(
            safe=safe,
            flags=flags + blocked_rules,
            risk_score=max(risk_score, 0.0),
        )
