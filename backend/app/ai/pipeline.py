"""Story processing pipeline orchestration."""

from __future__ import annotations

from time import perf_counter

import logging

from .embeddings import EmbeddingService
from .emotion import EmotionAnalyzer
from .explainability import ExplainabilityService
from .moderation import ModerationService, UnsafeContentError
from .narrative import NarrativeAnalyzer
from .redaction import RedactionService
from .recommendation import RecommendationService
from ..settings import get_settings
from .themes import ThemeExtractor
from .types import ProcessingTrace, StageTrace, StoryAnalysis

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "2026.07.portfolio-v1"


class StoryProcessingPipeline:
    """Coordinates AI modules without containing AI logic itself."""

    def __init__(
        self,
        narrative_analyzer: NarrativeAnalyzer,
        emotion_analyzer: EmotionAnalyzer,
        theme_extractor: ThemeExtractor,
        embedding_service: EmbeddingService,
        explainability_service: ExplainabilityService,
        moderation_service: ModerationService,
        redaction_service: RedactionService,
        recommendation_service: RecommendationService,
    ) -> None:
        self._narrative_analyzer = narrative_analyzer
        self._emotion_analyzer = emotion_analyzer
        self._theme_extractor = theme_extractor
        self._embedding_service = embedding_service
        self._explainability_service = explainability_service
        self._moderation_service = moderation_service
        self._redaction_service = redaction_service
        self._recommendation_service = recommendation_service

    def process_story(
        self,
        text: str,
        selected_mood: str | None = None,
        title: str | None = None,
        enforce_moderation: bool = True,
        redact_pii: bool = True,
    ) -> StoryAnalysis:
        """Run moderation first, redaction second, then the remaining analysis stages."""
        pipeline_started = perf_counter()
        stages: list[StageTrace] = []
        recommendation = self._recommendation_service.prepare()

        moderation_started = perf_counter()
        moderation = self._moderation_service.analyze(text)
        stages.append(
            StageTrace(
                name="moderation",
                duration_ms=round((perf_counter() - moderation_started) * 1000, 3),
                outcome="completed" if moderation.safe else "blocked",
                detail=f"risk={moderation.risk_score:.3f}; flags={len(moderation.flags)}",
            )
        )
        if enforce_moderation and not moderation.safe:
            raise UnsafeContentError("Story contains unsafe content and cannot be saved.")

        redaction_started = perf_counter()
        redaction = (
            self._redaction_service.sanitize_story(text, title=title)
            if redact_pii
            else self._redaction_service.pass_through_story(text, title=title)
        )
        stages.append(
            StageTrace(
                name="redaction",
                duration_ms=round((perf_counter() - redaction_started) * 1000, 3),
                detail=f"model={redaction.model_name}; entities={len(redaction.redactions)}",
            )
        )
        cleaned_text = redaction.redacted_text
        cleaned_title = redaction.redacted_title or self.generate_title(cleaned_text)

        narrative_started = perf_counter()
        narrative = self._narrative_analyzer.analyze(cleaned_text)
        stages.append(
            StageTrace(
                name="narrative",
                duration_ms=round((perf_counter() - narrative_started) * 1000, 3),
                detail=f"summary_chars={len(narrative.summary)}",
            )
        )

        emotion_started = perf_counter()
        emotion = self._emotion_analyzer.analyze(cleaned_text, selected_mood=selected_mood)
        stages.append(
            StageTrace(
                name="emotion",
                duration_ms=round((perf_counter() - emotion_started) * 1000, 3),
                detail=f"dominant={emotion.dominant_emotion}; confidence={emotion.confidence:.3f}",
            )
        )

        theme_started = perf_counter()
        themes = self._theme_extractor.analyze(cleaned_text)
        stages.append(
            StageTrace(
                name="themes",
                duration_ms=round((perf_counter() - theme_started) * 1000, 3),
                detail=f"keywords={len(themes.keywords)}",
            )
        )

        embedding_started = perf_counter()
        embedding = self._embedding_service.generate_embedding(cleaned_text)
        stages.append(
            StageTrace(
                name="embedding",
                duration_ms=round((perf_counter() - embedding_started) * 1000, 3),
                detail=f"backend={embedding.embedding_model}",
            )
        )

        projection_started = perf_counter()
        semantic_projection = self._explainability_service.project_story(
            text=cleaned_text,
            embedding=embedding,
            emotion=emotion,
            themes=themes,
        )
        stages.append(
            StageTrace(
                name="projection",
                duration_ms=round((perf_counter() - projection_started) * 1000, 3),
                detail=f"cluster={semantic_projection.cluster or 'none'}",
            )
        )
        processing_trace = ProcessingTrace(
            pipeline_version=PIPELINE_VERSION,
            embedding_backend=embedding.embedding_model,
            moderation_safe=moderation.safe,
            redaction_count=len(redaction.redactions),
            total_duration_ms=round((perf_counter() - pipeline_started) * 1000, 3),
            stages=stages,
        )
        self._log_trace(
            original_text=text,
            redaction=redaction,
            cleaned_text=cleaned_text,
            cleaned_title=cleaned_title,
            keywords=themes.keywords,
            summary=narrative.summary,
            embedding_model=embedding.embedding_model,
            semantic_projection=semantic_projection.semantic_profile,
            processing_trace=processing_trace,
        )
        return StoryAnalysis(
            title=cleaned_title,
            redaction=redaction,
            narrative=narrative,
            emotion=emotion,
            themes=themes,
            embedding=embedding,
            semantic_projection=semantic_projection,
            moderation=moderation,
            recommendation=recommendation,
            processing_trace=processing_trace,
        )

    def generate_title(self, text: str) -> str:
        """Expose title generation through the pipeline boundary."""
        return self._narrative_analyzer.generate_title(text)

    def sanitize_text(self, text: str) -> str:
        """Expose text-only sanitization for auxiliary fields."""
        return self._redaction_service.sanitize_story(text).redacted_text

    def _log_trace(
        self,
        *,
        original_text: str,
        redaction,
        cleaned_text: str,
        cleaned_title: str,
        keywords: list[str],
        summary: str,
        embedding_model: str,
        semantic_projection: dict[str, float],
        processing_trace: ProcessingTrace,
    ) -> None:
        if not get_settings().pipeline_trace_mode:
            return
        logger.info(
            "Dearest pipeline trace\n"
            "Original Text: %s\n"
            "NER Model: %s\n"
            "NER Executed: %s\n"
            "Detected Entities: %s\n"
            "Redacted Text: %s\n"
            "Redacted Title: %s\n"
            "Generated Keywords: %s\n"
            "Generated Summary: %s\n"
            "Semantic Profile: %s\n"
            "Embedding Model: %s\n"
            "Processing Trace: %s",
            original_text,
            redaction.model_name,
            redaction.ner_executed,
            [(item.type, item.value) for item in redaction.redactions],
            cleaned_text,
            cleaned_title,
            keywords,
            summary,
            semantic_projection,
            embedding_model,
            [
                {
                    "name": stage.name,
                    "duration_ms": stage.duration_ms,
                    "outcome": stage.outcome,
                    "detail": stage.detail,
                }
                for stage in processing_trace.stages
            ],
        )
