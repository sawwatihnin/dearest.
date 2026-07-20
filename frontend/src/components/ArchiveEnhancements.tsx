import { type ChangeEvent } from "react";
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

export function MediaRecommendationPanel({
  items
}: {
  items: MediaRecommendation[];
}) {
  if (!items.length) {
    return null;
  }

  return (
    <section className="glass-panel media-panel">
      <div className="section-heading">
        <p className="section-kicker">After the letter</p>
        <h2>A few songs and films nearby.</h2>
      </div>
      <div className="media-section media-section-compact">
        {items.slice(0, 6).map((item) => (
          <MediaCard key={`${item.kind}-${item.title}`} item={item} />
        ))}
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
      <p className="media-card-copy">{item.explanation}</p>
      <div className="chip-row">
        {item.shared_themes.slice(0, 2).map((theme) => (
          <span key={`${item.title}-${theme}`} className="chip">
            {formatLabel(theme)}
          </span>
        ))}
        {item.shared_emotions.slice(0, 1).map((emotion) => (
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
      <p className="insight-copy">{item.narrative_explanation}</p>
      <p className="supporting-excerpt">{item.supporting_excerpt}</p>
      <div className="insight-stack compact-insight-stack">
        <InsightLine label="Shared themes" values={item.shared_themes.slice(0, 2)} />
        <InsightLine label="Shared emotions" values={item.shared_emotions.slice(0, 2)} />
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
        <p className="section-kicker">Archival sequels and prequels to your work</p>
        <h2>Letters that come before and after yours.</h2>
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
        <p className="section-kicker">Letters like yours throughout the years</p>
        <h2>The same feeling, crossing generations.</h2>
      </div>
      <div className="timeline-list">
        {entries.map((post) => (
          <Link key={post.id} to={`/archive/${post.id}`} className="timeline-item">
              <span className="timeline-year">{post.timeline_label}</span>
              <div>
                <p>{post.title}</p>
                <span>
                  {post.attribution?.author ?? <>Anonymous <em>Dearest</em> letter</>} · {post.source_label}
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
