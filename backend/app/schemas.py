from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field
from typing import Literal


ContentType = Literal["community", "public_archive"]


class PostCreate(BaseModel):
    text: str = Field(min_length=20, max_length=5000)
    about: str | None = Field(default=None, max_length=255)
    mood: str | None = Field(default=None, max_length=64)
    content_notes: list[str] = Field(default_factory=list, max_length=8)


class PublicArchiveAttribution(BaseModel):
    author: str
    work: str | None = None
    year: str | None = None
    source: str | None = None
    url: str | None = None
    rights_status: str | None = None
    rights_notes: str | None = None


class ProcessingStage(BaseModel):
    name: str
    duration_ms: float
    outcome: str
    detail: str | None = None


class ProcessingMetadata(BaseModel):
    pipeline_version: str
    embedding_backend: str
    moderation_safe: bool
    redaction_count: int
    total_duration_ms: float
    stages: list[ProcessingStage]


class PostSummary(BaseModel):
    id: int
    content_type: ContentType
    source_label: str
    tone: str
    collections: list[str]
    primary_themes: list[str]
    timeline_year: int | None = None
    timeline_label: str | None = None
    title: str
    raw_text: str
    summary: str
    attribution: PublicArchiveAttribution | None = None
    selected_mood: str | None
    detected_mood: str
    detected_emotions: list[str]
    emotion_distribution: dict[str, float]
    keywords: list[str]
    keyword_profile: dict[str, float]
    semantic_profile: dict[str, float]
    top_motifs: list[str]
    cluster: str | None
    warning_terms: list[str]
    content_notes: list[str]
    suggested_content_notes: list[str]
    embedding_model: str
    processing: ProcessingMetadata
    created_at: datetime


class SimilarPost(BaseModel):
    post: PostSummary
    similarity_score: float
    confidence_label: str
    calibrated_confidence: float | None = None
    embedding_similarity: float
    supporting_excerpt: str
    semantic_profile: dict[str, float]
    matched_story_profile: dict[str, float]
    shared_concepts: list[str]
    shared_themes: list[str]
    shared_emotions: list[str]
    shared_keywords: list[str]
    dominant_tone: str
    narrative_explanation: str
    top_motifs: list[str]


class MediaRecommendation(BaseModel):
    kind: Literal["song", "movie"]
    title: str
    creator: str
    year: int
    link: str
    artwork_hint: str
    confidence_label: str
    shared_themes: list[str]
    shared_emotions: list[str]
    explanation: str


class RedactionPayload(BaseModel):
    type: str
    value: str


class PostCreateResponse(BaseModel):
    post: PostSummary | None = None
    similar_posts: list[SimilarPost] = Field(default_factory=list)
    media_recommendations: list[MediaRecommendation] = Field(default_factory=list)
    explanation: str | None = None
    pii_detected: bool = False
    redactions: list[RedactionPayload] = Field(default_factory=list)
    job_id: str | None = None
    status: str | None = None


class SimilarPostsResponse(BaseModel):
    source_post: PostSummary
    similar_posts: list[SimilarPost]
    media_recommendations: list[MediaRecommendation]
    explanation: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    post: PostSummary | None = None
    similar_posts: list[SimilarPost] = Field(default_factory=list)
    media_recommendations: list[MediaRecommendation] = Field(default_factory=list)
    explanation: str | None = None
    pii_detected: bool = False
    redactions: list[RedactionPayload] = Field(default_factory=list)
    error: str | None = None


class EchoStep(BaseModel):
    step: int
    relation_score: float | None
    relation_explanation: str | None
    post: PostSummary


class EchoesResponse(BaseModel):
    source_post: PostSummary
    chain: list[EchoStep]


class ArchiveFilterOptions(BaseModel):
    themes: list[str]
    emotions: list[str]
    content_notes: list[str]
    tones: list[str]
    authors: list[str]
    years: list[str]
    content_types: list[ContentType]
    collections: list[str]
    sort_options: list[str]


class ArchiveExplorerResponse(BaseModel):
    posts: list[PostSummary]
    filters: ArchiveFilterOptions
