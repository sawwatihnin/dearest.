import { useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";

import type {
  ArchiveFilterOptions,
  EchoStep,
  MediaRecommendation,
  PostSummary,
  SimilarPost
} from "../types";

type ExplorerFilters = {
  theme: string;
  avoid_theme: string;
  emotion: string;
  content_note: string;
  avoid_content_note: string;
  tone: string;
  author: string;
  year: string;
  content_type: string;
  collection: string;
  sort: string;
};

export function ArchiveExplorerControls({
  filters,
  values,
  onChange
}: {
  filters: ArchiveFilterOptions;
  values: ExplorerFilters;
  onChange: (next: ExplorerFilters) => void;
}) {
  function handleSelect(event: ChangeEvent<HTMLSelectElement>) {
    onChange({ ...values, [event.target.name]: event.target.value });
  }

  return (
    <section className="archive-explorer-panel glass-panel">
      <div className="section-heading">
        <p className="section-kicker">Archive explorer</p>
        <h2>Follow the feeling, not only the title.</h2>
      </div>
      <div className="explorer-controls">
        <FilterSelect
          label="Theme"
          name="theme"
          value={values.theme}
          options={filters.themes}
          onChange={handleSelect}
        />
        <FilterSelect
          label="Avoid theme"
          name="avoid_theme"
          value={values.avoid_theme}
          options={filters.themes}
          onChange={handleSelect}
        />
        <FilterSelect
          label="Emotion"
          name="emotion"
          value={values.emotion}
          options={filters.emotions}
          onChange={handleSelect}
        />
        <FilterSelect
          label="Tone"
          name="tone"
          value={values.tone}
          options={filters.tones}
          onChange={handleSelect}
        />
        <FilterSelect
          label="Content note"
          name="content_note"
          value={values.content_note}
          options={filters.content_notes}
          onChange={handleSelect}
        />
        <FilterSelect
          label="Avoid trigger"
          name="avoid_content_note"
          value={values.avoid_content_note}
          options={filters.content_notes}
          onChange={handleSelect}
        />
        <FilterSelect
          label="Author"
          name="author"
          value={values.author}
          options={filters.authors}
          onChange={handleSelect}
        />
        <FilterSelect
          label="Year"
          name="year"
          value={values.year}
          options={filters.years}
          onChange={handleSelect}
        />
        <FilterSelect
          label="Content type"
          name="content_type"
          value={values.content_type}
          options={filters.content_types}
          onChange={handleSelect}
        />
        <FilterSelect
          label="Collection"
          name="collection"
          value={values.collection}
          options={filters.collections}
          onChange={handleSelect}
        />
        <FilterSelect
          label="Sort"
          name="sort"
          value={values.sort}
          options={filters.sort_options}
          onChange={handleSelect}
        />
      </div>
    </section>
  );
}

function FilterSelect({
  label,
  name,
  value,
  options,
  onChange
}: {
  label: string;
  name: keyof ExplorerFilters;
  value: string;
  options: string[];
  onChange: (event: ChangeEvent<HTMLSelectElement>) => void;
}) {
  return (
    <label className="journal-label explorer-filter">
      <span>{label}</span>
      <select name={name} value={value} onChange={onChange}>
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {formatLabel(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

export function AttributionPanel({ post }: { post: PostSummary }) {
  if (!post.attribution) {
    return null;
  }

  return (
    <div className="story-source-panel glass-panel">
      <p className="section-kicker">From the public archive</p>
      <h3>{post.attribution.author}</h3>
      <dl className="attribution-grid">
        <AttributionRow label="Work" value={post.attribution.work} />
        <AttributionRow label="Year" value={post.attribution.year} />
        <AttributionRow label="Source" value={post.attribution.source} />
        <AttributionRow label="Rights" value={post.attribution.rights_status} />
        <AttributionRow label="Notes" value={post.attribution.rights_notes} />
      </dl>
      <div className="story-source-actions">
        {post.attribution.url && (
          <a
            className="button secondary"
            href={post.attribution.url}
            target="_blank"
            rel="noreferrer"
          >
            View Original
          </a>
        )}
      </div>
    </div>
  );
}

export function ContentNotePanel({ post }: { post: PostSummary }) {
  if (!post.content_notes.length) {
    return null;
  }

  return (
    <details className="content-note-panel glass-panel">
      <summary>
        <span className="section-kicker">Content note</span>
        <span>This letter may touch on difficult material.</span>
      </summary>
      <div className="content-note-body">
        <div className="chip-row">
          {post.content_notes.map((note) => (
            <span key={`${post.id}-${note}`} className="chip">
              {formatLabel(note)}
            </span>
          ))}
        </div>
      </div>
    </details>
  );
}

export function ArchiveIntelligencePanel({ post }: { post: PostSummary }) {
  const visibleStages = post.processing.stages.slice(0, 6);

  return (
    <section className="glass-panel archive-intelligence-panel">
      <div className="section-heading">
        <p className="section-kicker">Archive intelligence</p>
        <h2>The quiet machinery behind this letter.</h2>
      </div>
      <p className="archive-intelligence-copy">
        Processed through moderation, privacy protection, narrative analysis, and semantic matching before it reached the shelf.
      </p>
      <div className="archive-intelligence-meta">
        <span className="chip">Pipeline {post.processing.pipeline_version}</span>
        <span className="chip">{post.processing.embedding_backend}</span>
        <span className="chip">{post.processing.redaction_count} redactions</span>
        <span className="chip">{Math.round(post.processing.total_duration_ms)} ms total</span>
      </div>
      <div className="processing-stage-list" role="list" aria-label="Processing stages">
        {visibleStages.map((stage) => (
          <div key={`${post.id}-${stage.name}`} className="processing-stage-item" role="listitem">
            <div>
              <strong>{formatLabel(stage.name)}</strong>
              {stage.detail ? <p>{stage.detail}</p> : null}
            </div>
            <span>{Math.round(stage.duration_ms)} ms</span>
          </div>
        ))}
      </div>
    </section>
  );
}

export function MediaRecommendationPanel({
  items
}: {
  items: MediaRecommendation[];
}) {
  if (!items.length) {
    return null;
  }

  const songs = items.filter((item) => item.kind === "song");
  const movies = items.filter((item) => item.kind === "movie");

  return (
    <section className="glass-panel media-panel">
      <div className="section-heading">
        <p className="section-kicker">After the letter</p>
        <h2>What else might understand this feeling.</h2>
      </div>
      <div className="media-section">
        <div>
          <h3>Songs</h3>
          <div className="media-list">
            {songs.map((item) => (
              <MediaCard key={`${item.kind}-${item.title}`} item={item} />
            ))}
          </div>
        </div>
        <div>
          <h3>Movies</h3>
          <div className="media-list">
            {movies.map((item) => (
              <MediaCard key={`${item.kind}-${item.title}`} item={item} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function MediaCard({ item }: { item: MediaRecommendation }) {
  return (
    <article className="media-card">
      <p className="source-chip">{item.kind === "song" ? "Song" : "Movie"}</p>
      <div className="post-meta">
        <span>{item.creator}</span>
        <span>{item.year}</span>
      </div>
      <h4>{item.title}</h4>
      <p>{item.explanation}</p>
      <div className="chip-row">
        {item.shared_themes.map((theme) => (
          <span key={`${item.title}-${theme}`} className="chip">
            {formatLabel(theme)}
          </span>
        ))}
        {item.shared_emotions.map((emotion) => (
          <span key={`${item.title}-${emotion}`} className="chip">
            {formatLabel(emotion)}
          </span>
        ))}
      </div>
      <a className="button secondary media-link" href={item.link} target="_blank" rel="noreferrer">
        Open
      </a>
    </article>
  );
}

function AttributionRow({ label, value }: { label: string; value: string | null }) {
  if (!value) {
    return null;
  }
  return (
    <>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </>
  );
}

export function SimilarityInsightCard({ item }: { item: SimilarPost }) {
  return (
    <article className="related-card glass-panel insight-card">
      <p className="source-chip">{item.post.source_label}</p>
      <div className="post-meta">
        <span>{formatLabel(item.post.detected_mood)}</span>
        <span>{item.confidence_label}</span>
      </div>
      <h3>{item.post.title}</h3>
      {item.post.attribution && (
        <p className="archive-attribution">
          {item.post.attribution.author}
          {item.post.attribution.work ? ` · ${item.post.attribution.work}` : ""}
          {item.post.attribution.year ? ` · ${item.post.attribution.year}` : ""}
        </p>
      )}
      <p>{item.narrative_explanation}</p>
      <p className="constellation-meta">{item.supporting_excerpt}</p>
      <div className="insight-stack">
        <InsightLine label="Shared themes" values={item.shared_themes} />
        <InsightLine label="Shared emotions" values={item.shared_emotions} />
        <InsightLine label="Keywords" values={item.shared_keywords} />
        <InsightLine label="Dominant tone" values={[item.dominant_tone]} />
      </div>
      <Link className="continue-reading related-link" to={`/archive/${item.post.id}`}>
        Continue Reading →
      </Link>
    </article>
  );
}

function InsightLine({ label, values }: { label: string; values: string[] }) {
  if (!values.length) {
    return null;
  }
  return (
    <div className="insight-line">
      <span>{label}</span>
      <div className="chip-row">
        {values.map((value) => (
          <span key={`${label}-${value}`} className="chip">
            {formatLabel(value)}
          </span>
        ))}
      </div>
    </div>
  );
}

export function ConnectionConstellation({
  centerPost,
  related
}: {
  centerPost: PostSummary;
  related: SimilarPost[];
}) {
  const width = 760;
  const height = 420;
  const centerX = width / 2;
  const centerY = height / 2;
  const constellation = related
    .slice(0, 7)
    .sort((left, right) => right.embedding_similarity - left.embedding_similarity);
  const [hoveredId, setHoveredId] = useState<number>(constellation[0]?.post.id ?? centerPost.id);
  const similarityValues = constellation.map((item) => item.embedding_similarity);
  const maxSimilarity = Math.max(...similarityValues, 1);
  const minSimilarity = Math.min(...similarityValues, 0);
  const nodes = constellation.map((item, index) => {
    const angle = (-Math.PI / 2) + (index * (Math.PI * 2)) / Math.max(constellation.length, 1);
    const normalized = maxSimilarity === minSimilarity
      ? 0.55
      : (item.embedding_similarity - minSimilarity) / (maxSimilarity - minSimilarity);
    const radius = 82 + (1 - normalized) * 148;
    return {
      item,
      normalized,
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius
    };
  });
  const hoveredNode = nodes.find((node) => node.item.post.id === hoveredId) ?? nodes[0] ?? null;

  return (
    <section className="glass-panel constellation-panel">
      <div className="section-heading">
        <p className="section-kicker">Connection graph</p>
        <h2>A quiet constellation around your letter.</h2>
      </div>
      <div className="constellation-layout">
        <svg viewBox={`0 0 ${width} ${height}`} className="constellation-graph" role="img" aria-label="Connection graph">
        <defs>
          <radialGradient id="nodeGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(229, 184, 174, 0.95)" />
            <stop offset="100%" stopColor="rgba(215, 196, 156, 0.15)" />
          </radialGradient>
        </defs>
        {nodes.map(({ item, x, y }) => (
          <g
            key={item.post.id}
            className="constellation-node-group"
            onMouseEnter={() => setHoveredId(item.post.id)}
            onFocus={() => setHoveredId(item.post.id)}
          >
            <path
              d={`M ${centerX} ${centerY} Q ${(centerX + x) / 2} ${(centerY + y) / 2 - 20} ${x} ${y}`}
              className="constellation-line"
            />
            <a href={`/archive/${item.post.id}`} aria-label={`Open ${item.post.title}`}>
              <circle cx={x} cy={y} r="10" className="constellation-node" />
              <circle cx={x} cy={y} r="34" className="constellation-node-halo" />
              <title>
                {item.post.title} — {item.post.source_label}; {Math.round(item.embedding_similarity * 100)}% similarity;
                themes: {item.shared_themes.join(", ") || "none"}; emotions: {item.shared_emotions.join(", ") || "none"}
              </title>
            </a>
          </g>
        ))}
        <circle cx={centerX} cy={centerY} r="13" className="constellation-node constellation-node-center" />
        <circle cx={centerX} cy={centerY} r="36" className="constellation-node-halo constellation-node-halo-center" />
        <text x={centerX} y={centerY + 68} textAnchor="middle" className="constellation-center-label">
          {centerPost.content_type === "community" ? "Your letter" : centerPost.title}
        </text>
        </svg>
        <div className="constellation-inspector glass-panel">
          {hoveredNode ? (
            <>
              <p className="source-chip">{hoveredNode.item.post.source_label}</p>
              <h3>{hoveredNode.item.post.title}</h3>
              <p>{hoveredNode.item.narrative_explanation}</p>
              <div className="chip-row">
                {hoveredNode.item.shared_themes.slice(0, 3).map((theme) => (
                  <span key={`theme-${hoveredNode.item.post.id}-${theme}`} className="chip">
                    {formatLabel(theme)}
                  </span>
                ))}
                {hoveredNode.item.shared_emotions.slice(0, 2).map((emotion) => (
                  <span key={`emotion-${hoveredNode.item.post.id}-${emotion}`} className="chip">
                    {formatLabel(emotion)}
                  </span>
                ))}
              </div>
              <p className="constellation-meta">
                {Math.round(hoveredNode.item.embedding_similarity * 100)}% similarity ·{" "}
                {getPreview(hoveredNode.item.post.raw_text, 1)}
              </p>
              <Link className="button secondary" to={`/archive/${hoveredNode.item.post.id}`}>
                Open writing
              </Link>
            </>
          ) : null}
        </div>
      </div>
      <div className="constellation-legend">
        {nodes.map(({ item }) => (
          <Link key={item.post.id} to={`/archive/${item.post.id}`} className="constellation-preview glass-panel">
            <p>{item.post.title}</p>
            <span>{item.post.source_label}</span>
            <span>{Math.round(item.embedding_similarity * 100)}% similarity</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

export function EchoesCarousel({
  chain,
  activeId,
  onSelect
}: {
  chain: EchoStep[];
  activeId: number;
  onSelect: (postId: number) => void;
}) {
  if (!chain.length) {
    return null;
  }

  return (
    <section className="glass-panel echoes-panel">
      <div className="section-heading">
        <p className="section-kicker">Echoes</p>
        <h2>One letter leading softly to the next.</h2>
      </div>
      <div className="echoes-journey" role="list" aria-label="Semantically connected writings">
        {chain.map((step, index) => {
          const nextStep = chain[index + 1];
          return (
            <div key={step.post.id} className="echo-stage">
              <button
                type="button"
                className={`echo-step echo-stage-card ${activeId === step.post.id ? "is-active" : ""}`}
                onClick={() => onSelect(step.post.id)}
              >
                <span className="echo-step-index">Step {step.step + 1}</span>
                <span className="echo-step-title">{step.post.title}</span>
                <span className="echo-step-source">{step.post.source_label}</span>
                <span className="echo-step-meta">{getPreview(step.post.raw_text, 1)}</span>
              </button>
              {nextStep ? (
                <div className="echo-transition">
                  <div className="echo-transition-line" aria-hidden="true" />
                  <p>{nextStep.relation_explanation ?? "A nearby feeling continues the thread."}</p>
                  <button type="button" className="ghost-button echo-inline-link" onClick={() => onSelect(nextStep.post.id)}>
                    Continue to {nextStep.post.title}
                  </button>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}

export function EmotionalTimeline({
  current,
  related,
  echoes
}: {
  current: PostSummary;
  related: SimilarPost[];
  echoes: EchoStep[];
}) {
  const entries = uniqueTimelineEntries(
    [current, ...related.map((item) => item.post), ...echoes.map((step) => step.post)].filter(
      (post) => post.timeline_year !== null
    )
  );
  if (!entries.length) {
    return null;
  }

  return (
    <section className="glass-panel timeline-panel">
      <div className="section-heading">
        <p className="section-kicker">Emotional timeline</p>
        <h2>The same feeling, crossing generations.</h2>
      </div>
      <div className="timeline-list">
        {entries.map((post) => (
          <Link key={post.id} to={`/archive/${post.id}`} className="timeline-item">
            <span className="timeline-year">{post.timeline_label}</span>
            <div>
              <p>{post.title}</p>
              <span>
                {post.attribution?.author ?? "Anonymous Dearest letter"} · {post.source_label}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

function uniqueTimelineEntries(posts: PostSummary[]) {
  const seen = new Set<number>();
  return posts
    .filter((post) => {
      if (seen.has(post.id)) {
        return false;
      }
      seen.add(post.id);
      return true;
    })
    .sort((left, right) => (left.timeline_year ?? 0) - (right.timeline_year ?? 0));
}

function formatLabel(value: string) {
  return value
    .split(/[_\s]+/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function getPreview(text: string, sentenceCount: number) {
  const sentences = text.match(/[^.!?]+[.!?]+/g) ?? [text];
  return sentences.slice(0, sentenceCount).join(" ").trim();
}
