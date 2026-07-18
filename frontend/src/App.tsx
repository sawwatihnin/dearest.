import { FormEvent, useEffect, useState } from "react";
import {
  BrowserRouter,
  Link,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams
} from "react-router-dom";

import { createPost, fetchArchiveExplorer, fetchEchoes, fetchJobStatus, fetchPost, fetchSimilarPosts } from "./api";
import {
  ArchiveIntelligencePanel,
  ArchiveExplorerControls,
  AttributionPanel,
  ConnectionConstellation,
  ContentNotePanel,
  EchoesCarousel,
  EmotionalTimeline,
  MediaRecommendationPanel,
  SimilarityInsightCard
} from "./components/ArchiveEnhancements";
import { Atmosphere } from "./components/Atmosphere";
import { BehindArchiveExperience } from "./components/BehindArchiveExperience";
import { FeatherIcon } from "./components/Icons";
import { usePointerGlow } from "./hooks/usePointerGlow";
import { usePrefersReducedMotion } from "./hooks/usePrefersReducedMotion";
import { useSectionReveal } from "./hooks/useSectionReveal";
import type {
  ArchiveExplorerResponse,
  EchoesResponse,
  Mood,
  PostSummary,
  SimilarPostsResponse
} from "./types";

const moodOptions: Mood[] = [
  "heartbreak",
  "longing",
  "anger",
  "nostalgia",
  "confusion",
  "healing",
  "love",
  "grief",
  "other"
];

const LETTER_MIN_LENGTH = 20;
const LETTER_MAX_LENGTH = 5000;
const PRIVATE_SUBJECT_MAX_LENGTH = 255;
const CONTENT_NOTE_OPTIONS = [
  "abuse",
  "war",
  "violence",
  "grief",
  "illness",
  "heartbreak",
  "identity",
  "trauma",
  "discrimination",
  "self-harm"
] as const;
const SUBMIT_PROGRESS_STEPS = [
  "Reading the letter",
  "Protecting private details",
  "Tracing themes and emotion",
  "Finding nearby writings"
] as const;

function App() {
  return (
    <BrowserRouter>
      <ScrollToTopAndHash />
      <div className="app-shell">
        <Atmosphere />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/write" element={<WritePage />} />
          <Route path="/archive" element={<ArchivePage />} />
          <Route path="/archive/:id" element={<StoryPage />} />
          <Route path="/post/:id" element={<StoryPage />} />
          <Route path="/behind-the-archive" element={<BehindArchivePage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

function HomePage() {
  const reducedMotion = usePrefersReducedMotion();
  const heroGlowRef = usePointerGlow<HTMLElement>(!reducedMotion);

  useDocumentTitle("Dearest.");

  return (
    <div className="page page-fade home-page">
      <SiteHeader />
      <main className="home-main">
        <section className="hero hero-home" ref={heroGlowRef}>
          <div className="hero-copy hero-copy-home">
            <p className="eyebrow eyebrow-tight">Anonymous letters for the unfinished heart.</p>
            <BrandMark className="hero-brand" />
            <div className="hero-divider" aria-hidden="true">
              <span />
            </div>
            <h1>Write what you could never say.</h1>
            <p className="hero-text">
              Not a feed. A collection.
            </p>
            <div className="hero-actions">
              <Link className="button primary" to="/write">
                <FeatherIcon /> Begin a letter
              </Link>
              <Link className="button secondary" to="/archive">
                Browse the Archive
              </Link>
            </div>
            <blockquote className="atmospheric-quote">
              "There are feelings that look better in moonlight."
            </blockquote>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

function WritePage() {
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [about, setAbout] = useState("");
  const [mood, setMood] = useState<Mood>("longing");
  const [contentNotes, setContentNotes] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitStage, setSubmitStage] = useState(0);
  const [pendingJobId, setPendingJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useDocumentTitle("Write a Letter — Dearest.");

  useEffect(() => {
    if (!submitting) {
      setSubmitStage(0);
      return;
    }
    const timers = SUBMIT_PROGRESS_STEPS.map((_, index) =>
      window.setTimeout(() => setSubmitStage(index), index * 700)
    );
    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [submitting]);

  useEffect(() => {
    if (!pendingJobId) {
      return;
    }
    const interval = window.setInterval(async () => {
      try {
        const result = await fetchJobStatus(pendingJobId);
        if (result.status === "COMPLETED" && result.post) {
          window.clearInterval(interval);
          setPendingJobId(null);
          setSubmitting(false);
          navigate(`/archive/${result.post.id}`);
        } else if (result.status === "FAILED") {
          window.clearInterval(interval);
          setPendingJobId(null);
          setSubmitting(false);
          setError(result.error ?? "Unable to publish letter.");
        }
      } catch (jobError) {
        window.clearInterval(interval);
        setPendingJobId(null);
        setSubmitting(false);
        setError(jobError instanceof Error ? jobError.message : "Unable to publish letter.");
      }
    }, 1200);
    return () => window.clearInterval(interval);
  }, [navigate, pendingJobId]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmedText = text.trim();
    const trimmedAbout = about.trim();
    let awaitingJob = false;

    if (trimmedText.length < LETTER_MIN_LENGTH) {
      setError(`Your letter needs at least ${LETTER_MIN_LENGTH} characters.`);
      return;
    }
    if (trimmedText.length > LETTER_MAX_LENGTH) {
      setError(`Your letter must stay under ${LETTER_MAX_LENGTH} characters.`);
      return;
    }
    if (trimmedAbout.length > PRIVATE_SUBJECT_MAX_LENGTH) {
      setError(`Private subject must stay under ${PRIVATE_SUBJECT_MAX_LENGTH} characters.`);
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      const response = await createPost({
        text: trimmedText,
        about: trimmedAbout || undefined,
        mood,
        content_notes: contentNotes
      });
      if (response.status === "PENDING" && response.job_id) {
        awaitingJob = true;
        setPendingJobId(response.job_id);
        return;
      }
      if (response.post) {
        navigate(`/archive/${response.post.id}`);
        return;
      }
      throw new Error("The letter was accepted, but no story was returned yet.");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to publish letter.");
    } finally {
      if (!awaitingJob) {
        setSubmitting(false);
      }
    }
  }

  return (
    <div className="page page-fade">
      <SiteHeader compact />
      <main className="write-shell">
        <section className="journal-intro">
          <p className="section-kicker">Write a letter</p>
          <h1 className="journal-title">Open the page. Stay long enough to mean it.</h1>
          <p className="journal-quote">"Some truths arrive softly."</p>
        </section>

        <form onSubmit={handleSubmit} className="journal-form glass-panel">
          <label className="journal-label journal-canvas-label">
            <span>Your letter</span>
            <textarea
              className="journal-canvas"
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Write the sentence you have been carrying."
              minLength={LETTER_MIN_LENGTH}
              maxLength={LETTER_MAX_LENGTH}
              required
            />
          </label>

          <div className="journal-controls">
            <label className="journal-label">
              <span>Mood</span>
              <select value={mood} onChange={(event) => setMood(event.target.value as Mood)}>
                {moodOptions.map((option) => (
                  <option key={option} value={option}>
                    {formatMood(option)}
                  </option>
                ))}
              </select>
            </label>
            <label className="journal-label">
              <span>Private subject</span>
              <input
                value={about}
                onChange={(event) => setAbout(event.target.value)}
                placeholder="Never shown publicly."
                maxLength={PRIVATE_SUBJECT_MAX_LENGTH}
              />
            </label>
          </div>

          <div className="journal-label content-note-picker">
            <span>Optional content notes</span>
            <div className="content-note-options">
              {CONTENT_NOTE_OPTIONS.map((note) => {
                const checked = contentNotes.includes(note);
                return (
                  <label key={note} className={`content-note-option ${checked ? "is-selected" : ""}`}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() =>
                        setContentNotes((current) =>
                          checked ? current.filter((value) => value !== note) : [...current, note]
                        )
                      }
                    />
                    <span>{formatMood(note)}</span>
                  </label>
                );
              })}
            </div>
            <p className="disclaimer">Suggested notes may also be added automatically from the story itself.</p>
          </div>

          <div className="journal-actions">
            <p className="disclaimer">
              Leave out identifying details. {text.trim().length}/{LETTER_MAX_LENGTH}
            </p>
            <button className="button primary submit-button" disabled={submitting}>
              {submitting ? "Placing it in the archive..." : "Publish"}
            </button>
          </div>

          {submitting ? (
            <div className="submit-progress-panel" aria-live="polite">
              <p className="section-kicker">Processing</p>
              <div className="submit-progress-list">
                {SUBMIT_PROGRESS_STEPS.map((step, index) => (
                  <div
                    key={step}
                    className={`submit-progress-item ${index <= submitStage ? "is-active" : ""}`}
                  >
                    <span>{step}</span>
                    <span>{index < submitStage ? "Done" : index === submitStage ? "Working" : "Waiting"}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </form>
      </main>
      <SiteFooter />
      {error && <div className="error-banner">{error}</div>}
    </div>
  );
}

function ArchivePage() {
  const location = useLocation();
  const relatedTo = Number(new URLSearchParams(location.search).get("relatedTo"));
  const [explorer, setExplorer] = useState<ArchiveExplorerResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    theme: "",
    avoid_theme: "",
    emotion: "",
    content_note: "",
    avoid_content_note: "",
    tone: "",
    author: "",
    year: "",
    content_type: "",
    collection: "",
    sort: Number.isFinite(relatedTo) ? "semantic_similarity" : "newest"
  });
  const archiveReveal = useSectionReveal<HTMLElement>();

  useDocumentTitle("The Archive — Dearest.");

  useEffect(() => {
    void loadPosts();
  }, [location.search, filters]);

  useEffect(() => {
    setFilters((current) => ({
      ...current,
      sort: Number.isFinite(relatedTo) ? "semantic_similarity" : current.sort || "newest"
    }));
  }, [relatedTo]);

  async function loadPosts() {
    try {
      setLoading(true);
      setError(null);
      const response = await fetchArchiveExplorer({
        ...filters,
        semantic_to_post_id: Number.isFinite(relatedTo) ? relatedTo : undefined
      });
      setExplorer(response);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load the archive.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page page-fade">
      <SiteHeader compact />
      <main className="archive-shell">
        <section className={`archive-hero ${archiveReveal.className}`} ref={archiveReveal.ref}>
          <p className="section-kicker">The Archive</p>
          <h1 className="archive-title">Shelves of letters, still warm to the touch.</h1>
          <p className="archive-copy">
            {Number.isFinite(relatedTo) ? "Arranged by emotional closeness." : "Read slowly."}
          </p>
        </section>

        {loading ? (
          <PostSkeletonGrid />
        ) : !explorer ? (
          <div className="glass-panel empty-state">The shelves are momentarily dim.</div>
        ) : (
          <>
            <ArchiveExplorerControls
              filters={explorer.filters}
              values={filters}
              onChange={(next) => setFilters(next)}
            />
            {explorer.posts.length === 0 ? (
              <div className="glass-panel empty-state">
                <BrandInline /> is quiet tonight.
              </div>
            ) : (
              <div className="post-grid archive-grid">
                {explorer.posts.map((post) => (
                  <ArchiveCard key={post.id} post={post} />
                ))}
              </div>
            )}
          </>
        )}
      </main>
      <SiteFooter />
      {error && <div className="error-banner">{error}</div>}
    </div>
  );
}

function StoryPage() {
  const { id } = useParams();
  const postId = Number(id);
  const navigate = useNavigate();
  const [post, setPost] = useState<PostSummary | null>(null);
  const [related, setRelated] = useState<SimilarPostsResponse | null>(null);
  const [echoes, setEchoes] = useState<EchoesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fingerprintReveal = useSectionReveal<HTMLElement>();
  const relatedReveal = useSectionReveal<HTMLElement>();
  const constellationReveal = useSectionReveal<HTMLElement>();
  const echoesReveal = useSectionReveal<HTMLElement>();
  const timelineReveal = useSectionReveal<HTMLElement>();
  const featuredMatch = related?.similar_posts[0] ?? null;

  useDocumentTitle(post ? `${post.title} — Dearest.` : "Dearest.");

  useEffect(() => {
    if (!Number.isFinite(postId)) {
      setError("Story not found.");
      setLoading(false);
      return;
    }
    void loadStory();
  }, [postId]);

  async function loadStory() {
    try {
      setLoading(true);
      setError(null);
      const [story, matches, echoChain] = await Promise.all([
        fetchPost(postId),
        fetchSimilarPosts(postId, 6),
        fetchEchoes(postId, 5)
      ]);
      setPost(story);
      setRelated(matches);
      setEchoes(echoChain);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load the story.");
    } finally {
      setLoading(false);
    }
  }

  const semanticAxes = post ? getTopSemanticConcepts(post.semantic_profile, 5) : [];

  return (
    <div className="page page-fade story-page">
      <SiteHeader compact />
      <main className="story-shell">
        {loading ? (
          <ArticleSkeleton />
        ) : error || !post ? (
          <div className="glass-panel empty-state article-empty">
            <p>{error ?? "This story could not be found."}</p>
            <button className="button secondary" onClick={() => navigate("/archive")}>
              Return to the Archive
            </button>
          </div>
        ) : (
          <>
            <article className="story-article">
              <header className="story-header">
                <p className="section-kicker">The Archive</p>
                <p className="source-chip story-source-chip">{post.source_label}</p>
                <h1 className="article-title">{post.title}</h1>
                {post.attribution && (
                  <div className="story-attribution">
                    <span>{post.attribution.author}</span>
                    {post.attribution.work && <span>{post.attribution.work}</span>}
                    {post.attribution.year && <span>{post.attribution.year}</span>}
                    {post.attribution.source && <span>{post.attribution.source}</span>}
                  </div>
                )}
                <div className="meta-row article-meta">
                  <span className="pill pill-accent">{formatMood(post.detected_mood)}</span>
                  <span>{getReadingTime(post.raw_text)} min read</span>
                </div>
              </header>

              <div className="story-body">
                <StoryText text={post.raw_text} />
              </div>
            </article>

            <AttributionPanel post={post} />
            <ContentNotePanel post={post} />
            <MediaRecommendationPanel items={related?.media_recommendations ?? []} />
            <ArchiveIntelligencePanel post={post} />

            <section
              className={`story-fingerprint glass-panel ${fingerprintReveal.className}`}
              ref={fingerprintReveal.ref}
            >
              <div className="section-heading">
                <p className="section-kicker">Emotional fingerprint</p>
                <h2>The feeling, held still.</h2>
              </div>
              <div className="fingerprint-visual">
                <FingerprintRadar
                  axes={semanticAxes}
                  sourceProfile={post.semantic_profile}
                  matchedProfile={featuredMatch?.matched_story_profile}
                />
                {featuredMatch && (
                  <div className="fingerprint-stats">
                    <p className="similarity-value">
                      {Math.round(featuredMatch.embedding_similarity * 100)}%
                    </p>
                    <p className="similarity-label">Overall Similarity</p>
                    <div className="chip-row">
                      {featuredMatch.shared_concepts.map((concept) => (
                        <span key={concept} className="chip">
                          {formatMood(concept)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="fingerprint-grid">
                <div>
                  <h3>Summary</h3>
                  <p>{post.summary}</p>
                </div>
                <div>
                  <h3>Shared concepts</h3>
                  <div className="chip-row">
                    {(featuredMatch?.shared_concepts.length
                      ? featuredMatch.shared_concepts
                      : semanticAxes
                    ).map((concept) => (
                      <span key={concept} className="chip">
                        {formatMood(concept)}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <h3>Detected motifs</h3>
                  <div className="chip-row">
                    {post.top_motifs.map((motif) => (
                      <span key={motif} className="chip">
                        {motif}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </section>

            <section
              className={`story-related constellation-shell ${constellationReveal.className}`}
              ref={constellationReveal.ref}
            >
              <ConnectionConstellation centerPost={post} related={related?.similar_posts ?? []} />
            </section>

            <section className={`story-related ${relatedReveal.className}`} ref={relatedReveal.ref}>
              <div className="section-heading">
                <p className="section-kicker">Similar letters</p>
                <h2>Some stories quietly find each other.</h2>
              </div>
              {related?.similar_posts.length ? (
            <div className="related-grid">
              {related.similar_posts.slice(0, 4).map((item) => (
                <SimilarityInsightCard key={item.post.id} item={item} />
              ))}
                </div>
              ) : (
                <div className="glass-panel empty-state">
                  The shelf beside this one is still waiting.
                </div>
              )}
            </section>

            {echoes && (
              <section className={echoesReveal.className} ref={echoesReveal.ref}>
                <EchoesCarousel
                  chain={echoes.chain}
                  activeId={post.id}
                  onSelect={(nextId) => navigate(`/archive/${nextId}`)}
                />
              </section>
            )}

            {related && echoes && (
              <section className={timelineReveal.className} ref={timelineReveal.ref}>
                <EmotionalTimeline current={post} related={related.similar_posts} echoes={echoes.chain} />
              </section>
            )}

            <section className="story-explore">
              <Link className="button secondary" to={`/archive?relatedTo=${post.id}`}>
                Continue exploring
              </Link>
            </section>
          </>
        )}
      </main>
      <SiteFooter />
    </div>
  );
}

function BehindArchivePage() {
  useDocumentTitle("Behind the Archive — Dearest.");

  return (
    <div className="page page-fade">
      <SiteHeader compact />
      <BehindArchiveExperience />
      <SiteFooter />
    </div>
  );
}

function SiteHeader({ compact = false }: { compact?: boolean }) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    function handleScroll() {
      setScrolled(window.scrollY > 24);
    }
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <header className={`site-header ${compact ? "compact" : ""}`}>
      <nav className={`topbar ${scrolled ? "is-scrolled" : ""}`}>
        <Link to="/" className="brand-link" aria-label="Go to Dearest.">
          <BrandMark />
        </Link>
        <div className="topbar-links">
          <NavLink to="/write">Write</NavLink>
          <NavLink to="/archive">The Archive</NavLink>
          <NavLink to="/behind-the-archive">Behind the Archive</NavLink>
        </div>
        <Link to="/write" className="button primary nav-cta">
          Begin a letter
        </Link>
      </nav>
    </header>
  );
}

function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-inner glass-panel">
        <p>Please do not include identifying private information.</p>
      </div>
    </footer>
  );
}

function ArchiveCard({ post }: { post: PostSummary }) {
  return (
    <article className="diary-card glass-panel archive-card">
      <Link to={`/archive/${post.id}`} className="card-link" aria-label={`Read ${post.title}`} />
      <p className="source-chip">{post.source_label}</p>
      <div className="post-meta">
        <span>{formatMood(post.detected_mood)}</span>
        <span>{formatDate(post.created_at)}</span>
        <span>{getReadingTime(post.raw_text)} min read</span>
      </div>
      <h3>{post.title}</h3>
      {post.attribution && (
        <p className="archive-attribution">
          {post.attribution.author}
          {post.attribution.work ? ` · ${post.attribution.work}` : ""}
          {post.attribution.year ? ` · ${post.attribution.year}` : ""}
        </p>
      )}
      <p className="post-preview">{getPreview(post.raw_text, 1)}</p>
      <div className="chip-row archive-card-tags">
        {post.collections.slice(0, 2).map((collection) => (
          <span key={`${post.id}-${collection}`} className="chip">
            {collection}
          </span>
        ))}
      </div>
      <div className="post-footer archive-card-footer">
        <span className="continue-reading">Continue Reading →</span>
      </div>
    </article>
  );
}

function FingerprintRadar({
  axes,
  sourceProfile,
  matchedProfile
}: {
  axes: string[];
  sourceProfile: Record<string, number>;
  matchedProfile?: Record<string, number>;
}) {
  const size = 320;
  const center = size / 2;
  const radius = 104;
  const rings = [0.25, 0.5, 0.75, 1];

  if (!axes.length) {
    return <div className="fingerprint-empty">The archive is still learning this shape.</div>;
  }

  return (
    <div className="radar-wrap">
      <svg viewBox={`0 0 ${size} ${size}`} className="radar-chart" role="img" aria-label="Emotional fingerprint">
        {rings.map((ring) => (
          <polygon
            key={ring}
            points={buildRadarPoints(axes, radius * ring, center)}
            className="radar-ring"
          />
        ))}
        {axes.map((axis, index) => {
          const angle = (Math.PI * 2 * index) / axes.length - Math.PI / 2;
          const x = center + Math.cos(angle) * radius;
          const y = center + Math.sin(angle) * radius;
          const labelX = center + Math.cos(angle) * (radius + 26);
          const labelY = center + Math.sin(angle) * (radius + 26);
          return (
            <g key={axis}>
              <line x1={center} y1={center} x2={x} y2={y} className="radar-axis" />
              <text x={labelX} y={labelY} className="radar-label" textAnchor="middle">
                {formatMood(axis)}
              </text>
            </g>
          );
        })}
        {matchedProfile && (
          <polygon
            points={buildRadarValuePoints(axes, matchedProfile, radius, center)}
            className="radar-shape radar-shape-match"
          />
        )}
        <polygon
          points={buildRadarValuePoints(axes, sourceProfile, radius, center)}
          className="radar-shape radar-shape-source"
        />
      </svg>
      <div className="radar-legend">
        <span className="legend-item">
          <i className="legend-swatch legend-source" />
          Current Story
        </span>
        {matchedProfile && (
          <span className="legend-item">
            <i className="legend-swatch legend-match" />
            Matched Story
          </span>
        )}
      </div>
    </div>
  );
}

function StoryText({ text }: { text: string }) {
  return (
    <div className="story-text">
      {text.split("\n\n").map((paragraph) => (
        <p key={paragraph.slice(0, 40)}>{paragraph}</p>
      ))}
    </div>
  );
}

function PostSkeletonGrid() {
  return (
    <div className="post-grid archive-grid">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="glass-panel skeleton-card">
          <div className="skeleton-line short" />
          <div className="skeleton-line medium" />
          <div className="skeleton-line long" />
          <div className="skeleton-line long" />
        </div>
      ))}
    </div>
  );
}

function ArticleSkeleton() {
  return (
    <div className="story-article">
      <div className="story-header glass-panel skeleton-card">
        <div className="skeleton-line short" />
        <div className="skeleton-line long" />
        <div className="skeleton-line medium" />
      </div>
      <div className="story-body glass-panel skeleton-card">
        {Array.from({ length: 8 }).map((_, index) => (
          <div key={index} className="skeleton-line long" />
        ))}
      </div>
    </div>
  );
}

function BrandMark({ className = "" }: { className?: string }) {
  return (
    <span className={`brand ${className}`.trim()}>
      <strong>
        <em>Dearest.</em>
      </strong>
    </span>
  );
}

function BrandInline() {
  return (
    <>
      <strong>
        <em>Dearest.</em>
      </strong>
    </>
  );
}

function ScrollToTopAndHash() {
  const location = useLocation();

  useEffect(() => {
    if (location.hash) {
      const element = document.querySelector(location.hash);
      if (element) {
        window.requestAnimationFrame(() => {
          element.scrollIntoView({ behavior: "smooth", block: "start" });
        });
        return;
      }
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [location.pathname, location.hash]);

  return null;
}

function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = title;
  }, [title]);
}

function formatMood(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric"
  });
}

function getReadingTime(text: string) {
  return Math.max(1, Math.ceil(text.trim().split(/\s+/).length / 180));
}

function getPreview(text: string, sentenceCount: number) {
  const sentences = text.match(/[^.!?]+[.!?]+/g) ?? [text];
  return sentences.slice(0, sentenceCount).join(" ").trim();
}

function getTopSemanticConcepts(profile: Record<string, number>, limit: number) {
  return Object.entries(profile)
    .sort((left, right) => right[1] - left[1])
    .slice(0, limit)
    .map(([concept]) => concept);
}

function buildRadarPoints(axes: string[], radius: number, center: number) {
  return axes
    .map((_, index) => {
      const angle = (Math.PI * 2 * index) / axes.length - Math.PI / 2;
      const x = center + Math.cos(angle) * radius;
      const y = center + Math.sin(angle) * radius;
      return `${x},${y}`;
    })
    .join(" ");
}

function buildRadarValuePoints(
  axes: string[],
  profile: Record<string, number>,
  radius: number,
  center: number
) {
  return axes
    .map((axis, index) => {
      const angle = (Math.PI * 2 * index) / axes.length - Math.PI / 2;
      const value = profile[axis] ?? 0;
      const x = center + Math.cos(angle) * radius * value;
      const y = center + Math.sin(angle) * radius * value;
      return `${x},${y}`;
    })
    .join(" ");
}

export default App;
