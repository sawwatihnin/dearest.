export type Mood =
  | "heartbreak"
  | "longing"
  | "anger"
  | "nostalgia"
  | "confusion"
  | "healing"
  | "love"
  | "grief"
  | "other";

export type ContentType = "community" | "public_archive";

export interface PublicArchiveAttribution {
  author: string;
  work: string | null;
  year: string | null;
  source: string | null;
  url: string | null;
  rights_status: string | null;
  rights_notes: string | null;
}

export interface ProcessingStage {
  name: string;
  duration_ms: number;
  outcome: string;
  detail: string | null;
}

export interface ProcessingMetadata {
  pipeline_version: string;
  embedding_backend: string;
  moderation_safe: boolean;
  redaction_count: number;
  total_duration_ms: number;
  stages: ProcessingStage[];
}

export interface PostSummary {
  id: number;
  content_type: ContentType;
  source_label: string;
  tone: string;
  collections: string[];
  primary_themes: string[];
  timeline_year: number | null;
  timeline_label: string | null;
  title: string;
  raw_text: string;
  summary: string;
  attribution: PublicArchiveAttribution | null;
  selected_mood: string | null;
  detected_mood: string;
  detected_emotions: string[];
  emotion_distribution: Record<string, number>;
  keywords: string[];
  keyword_profile: Record<string, number>;
  semantic_profile: Record<string, number>;
  top_motifs: string[];
  cluster: string | null;
  warning_terms: string[];
  content_notes: string[];
  suggested_content_notes: string[];
  embedding_model: string;
  processing: ProcessingMetadata;
  created_at: string;
}

export interface SimilarPost {
  post: PostSummary;
  similarity_score: number;
  confidence_label: string;
  calibrated_confidence: number | null;
  embedding_similarity: number;
  supporting_excerpt: string;
  semantic_profile: Record<string, number>;
  matched_story_profile: Record<string, number>;
  shared_concepts: string[];
  shared_themes: string[];
  shared_emotions: string[];
  shared_keywords: string[];
  dominant_tone: string;
  narrative_explanation: string;
  top_motifs: string[];
}

export interface MediaRecommendation {
  kind: "song" | "movie";
  title: string;
  creator: string;
  year: number;
  link: string;
  artwork_hint: string;
  confidence_label: string;
  shared_themes: string[];
  shared_emotions: string[];
  explanation: string;
}

export interface PostCreateResponse {
  post: PostSummary | null;
  similar_posts: SimilarPost[];
  media_recommendations: MediaRecommendation[];
  explanation: string | null;
  job_id: string | null;
  status: string | null;
  pii_detected?: boolean;
  redactions?: Array<{ type: string; value: string }>;
}

export interface SimilarPostsResponse {
  source_post: PostSummary;
  similar_posts: SimilarPost[];
  media_recommendations: MediaRecommendation[];
  explanation: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  post: PostSummary | null;
  similar_posts: SimilarPost[];
  media_recommendations: MediaRecommendation[];
  explanation: string | null;
  pii_detected: boolean;
  redactions: Array<{ type: string; value: string }>;
  error: string | null;
}

export interface EchoStep {
  step: number;
  relation_score: number | null;
  relation_explanation: string | null;
  post: PostSummary;
}

export interface EchoesResponse {
  source_post: PostSummary;
  chain: EchoStep[];
}

export interface ArchiveFilterOptions {
  themes: string[];
  emotions: string[];
  content_notes: string[];
  tones: string[];
  authors: string[];
  years: string[];
  content_types: ContentType[];
  collections: string[];
  sort_options: string[];
}

export interface ArchiveExplorerResponse {
  posts: PostSummary[];
  filters: ArchiveFilterOptions;
}
