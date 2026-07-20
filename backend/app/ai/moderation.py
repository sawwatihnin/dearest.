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
