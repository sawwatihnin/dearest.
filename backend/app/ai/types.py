"""Shared typed interfaces for AI pipeline components."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC


@dataclass(slots=True)
class NarrativeAnalysis:
    """Narrative-level heuristics extracted from a story."""

    summary: str
    opening: str
    closing: str
    estimated_read_time: int


@dataclass(slots=True)
class EmotionProfile:
    """Emotion model output for one story."""

    dominant_emotion: str
    emotion_scores: dict[str, int]
    confidence: float


@dataclass(slots=True)
class ThemeAnalysis:
    """Keyword and theme extraction output."""

    keywords: list[str]
    themes: list[str]
    keyword_scores: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class ArtifactMetadata:
    """Operational metadata attached to pipeline artifacts."""

    processing_version: str
    model_version: str
    latency_ms: float
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    status: str = "completed"
    input_hash: str = ""
    failure_reason: str | None = None


@dataclass(slots=True)
class ModerationResult:
    """Moderation flags and risk metadata."""

    safe: bool
    flags: list[str]
    risk_score: float
    metadata: ArtifactMetadata | None = None


@dataclass(slots=True)
class RedactionItem:
    """One detected piece of PII and its normalized type."""

    type: str
    value: str


@dataclass(slots=True)
class RedactionResult:
    """PII detection and redaction output for story content."""

    redacted_text: str
    redacted_title: str
    pii_detected: bool
    redactions: list[RedactionItem]
    model_name: str
    ner_executed: bool
    metadata: ArtifactMetadata | None = None


@dataclass(slots=True)
class EmbeddingResult:
    """Embedding generation result."""

    embedding_model: str
    vector: list[float] | None
    metadata: ArtifactMetadata | None = None


@dataclass(slots=True)
class RecommendationResult:
    """Recommendation preparation and ranking result."""

    similar_post_ids: list[int] = field(default_factory=list)
    scores: dict[int, float] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievalCandidate:
    """One candidate retrieved prior to final ranking."""

    post_id: int
    score: float
    dense_score: float
    emotion_score: float
    theme_score: float
    temporal_score: float
    narrative_score: float
    quality_score: float
    content_type: str
    metadata: ArtifactMetadata


@dataclass(slots=True)
class RankedRecommendation:
    """Final ranked recommendation with confidence and explanation inputs."""

    post_id: int
    score: float
    confidence_label: str
    supporting_excerpt: str
    shared_themes: list[str]
    shared_emotions: list[str]
    shared_keywords: list[str]
    metadata: ArtifactMetadata


@dataclass(slots=True)
class GroundedExplanation:
    """Grounded explanation for why a match was shown."""

    narrative_explanation: str
    supporting_excerpt: str
    metadata: ArtifactMetadata


@dataclass(slots=True)
class RecommendationBundle:
    """Bundle of retrieval, ranking, and explanation outputs."""

    candidates: list[RetrievalCandidate]
    recommendations: list[RankedRecommendation]
    explanations: dict[int, GroundedExplanation]
    metadata: ArtifactMetadata


@dataclass(slots=True)
class StageTrace:
    """Execution trace for one pipeline stage."""

    name: str
    duration_ms: float
    outcome: str = "completed"
    detail: str | None = None


@dataclass(slots=True)
class ProcessingTrace:
    """Versioned metadata describing how a story was processed."""

    pipeline_version: str
    embedding_backend: str
    moderation_safe: bool
    redaction_count: int
    total_duration_ms: float
    stages: list[StageTrace] = field(default_factory=list)


@dataclass(slots=True)
class SemanticProjection:
    """Human-readable projection of a story embedding."""

    semantic_profile: dict[str, float]
    emotion_distribution: dict[str, float]
    keyword_profile: dict[str, float]
    top_motifs: list[str]
    cluster: str | None


@dataclass(slots=True)
class MatchExplanation:
    """Explainable context for one recommended match."""

    embedding_similarity: float
    shared_concepts: list[str]
    top_motifs: list[str]
    matched_story_profile: dict[str, float]


@dataclass(slots=True)
class StoryAnalysis:
    """Top-level pipeline output for a single story."""

    title: str
    redaction: RedactionResult
    narrative: NarrativeAnalysis
    emotion: EmotionProfile
    themes: ThemeAnalysis
    embedding: EmbeddingResult
    semantic_projection: SemanticProjection
    moderation: ModerationResult
    recommendation: RecommendationResult
    processing_trace: ProcessingTrace
