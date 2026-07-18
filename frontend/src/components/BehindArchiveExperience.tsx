import {
  CompassIcon,
  HeartOutlineIcon,
  LockIcon,
  ShieldIcon,
  TagIcon,
  ThemeIcon
} from "./Icons";
import { useSectionReveal } from "../hooks/useSectionReveal";

const processSteps = [
  {
    number: "1.",
    title: "You write",
    description: "You pour your heart into a letter. It stays anonymous.",
    visual: <LetterPreview />
  },
  {
    number: "2.",
    title: "We understand",
    description: "We identify the themes, feelings, and ideas within your words.",
    visual: <UnderstandingPreview />
  },
  {
    number: "3.",
    title: "We translate",
    description: "Your letter becomes a unique mathematical representation of its meaning.",
    visual: <TranslationPreview />
  },
  {
    number: "4.",
    title: "We search",
    description: "We search the archive for letters with similar meaning, not just similar words.",
    visual: <SearchPreview />
  },
  {
    number: "5.",
    title: "We rank",
    description: "Results are ranked by semantic closeness and emotional resonance.",
    visual: <RankingPreview />
  },
  {
    number: "6.",
    title: "You discover",
    description: "You are shown stories that quietly understand you.",
    visual: <DiscoveryPreview />
  }
] as const;

const extractedItems = [
  {
    title: "Themes",
    body: "The deeper ideas inside your letter.",
    icon: <ThemeIcon />
  },
  {
    title: "Emotions",
    body: "The feelings behind your words.",
    icon: <HeartOutlineIcon />
  },
  {
    title: "Keywords",
    body: "The important words and phrases.",
    icon: <TagIcon />
  },
  {
    title: "Intent",
    body: "What your letter is trying to express.",
    icon: <CompassIcon />
  }
] as const;

const promiseItems = [
  {
    title: "Your letter is always anonymous.",
    body: "We never show your letter to other users, only meaningful connections.",
    icon: <LockIcon />
  },
  {
    title: "Built with care.",
    body: "Our system is designed to be safe, respectful, and emotionally intelligent.",
    icon: <ShieldIcon />
  }
] as const;

export function BehindArchiveExperience() {
  const processReveal = useSectionReveal<HTMLElement>();
  const connectionReveal = useSectionReveal<HTMLElement>();
  const detailReveal = useSectionReveal<HTMLElement>();

  return (
    <main className="behind-shell">
      <section className="behind-hero behind-hero-centered">
        <p className="section-kicker">Behind the Archive</p>
        <h1 className="behind-title">A quiet system beneath the letters.</h1>
        <p className="behind-copy behind-copy-wide">
          Every letter you share is gently processed to help it find the stories it is meant to echo.
        </p>
      </section>

      <section className={`behind-process ${processReveal.className}`} ref={processReveal.ref}>
        <p className="section-kicker">How it works</p>
        <ol className="process-flow" aria-label="How Dearest processes a letter">
          {processSteps.map((step, index) => (
            <li key={step.title} className="process-step">
              <div className="process-step-header">
                <span className="process-step-number">{step.number}</span>
                <h2>{step.title}</h2>
              </div>
              <div className="process-visual glass-panel">{step.visual}</div>
              <p className="process-copy">{step.description}</p>
              {index < processSteps.length - 1 && <span className="process-connector" aria-hidden="true" />}
            </li>
          ))}
        </ol>
      </section>

      <section className={`connection-section ${connectionReveal.className}`} ref={connectionReveal.ref}>
        <div className="section-heading behind-section-heading">
          <p className="section-kicker">A visual of connection</p>
          <h2>Letters gather by nearness, not noise.</h2>
        </div>
        <div className="connection-layout">
          <div className="glass-panel connection-graph-panel">
            <ConnectionGraph />
          </div>
          <aside className="glass-panel connection-note">
            <p className="connection-metric">Similarity: 0.91</p>
            <p>
              <strong>Shared themes:</strong> loneliness, rain, memory
            </p>
            <p>
              <strong>Emotional tone:</strong> melancholic, nostalgic
            </p>
          </aside>
        </div>
      </section>

      <section className={`behind-details ${detailReveal.className}`} ref={detailReveal.ref}>
        <div className="glass-panel extract-panel">
          <div className="section-heading behind-section-heading">
            <p className="section-kicker">What we extract</p>
            <h2>Meaning leaves a trace.</h2>
          </div>
          <div className="extract-list">
            {extractedItems.map((item) => (
              <article key={item.title} className="extract-item">
                <div className="extract-icon">{item.icon}</div>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.body}</p>
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="glass-panel promise-panel">
          <div className="section-heading behind-section-heading">
            <p className="section-kicker">Our promise</p>
            <h2>Care is part of the system.</h2>
          </div>
          <div className="promise-list">
            {promiseItems.map((item) => (
              <article key={item.title} className="promise-item">
                <div className="extract-icon">{item.icon}</div>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.body}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <p className="behind-closing">
        Technology fades into the background. What remains is what matters most:{" "}
        <em>connection.</em>
      </p>
    </main>
  );
}

function LetterPreview() {
  return (
    <div className="letter-preview" aria-hidden="true">
      <p>Tonight the rain reminds me of you.</p>
      <p>Some days the silence is louder than the memories.</p>
    </div>
  );
}

function UnderstandingPreview() {
  const tags = ["rain", "silence", "memories", "lonely", "longing"];

  return (
    <div className="understanding-preview" aria-hidden="true">
      <div className="understanding-lines">
        {Array.from({ length: 6 }).map((_, index) => (
          <span key={index} style={{ width: `${72 - index * 8}%` }} />
        ))}
      </div>
      <div className="understanding-tags">
        {tags.map((tag) => (
          <span key={tag} className="micro-tag">
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}

function TranslationPreview() {
  return (
    <div className="translation-preview" aria-hidden="true">
      <span className="translation-core" />
      <span className="translation-ring translation-ring-a" />
      <span className="translation-ring translation-ring-b" />
      <span className="translation-particle particle-a" />
      <span className="translation-particle particle-b" />
      <span className="translation-particle particle-c" />
      <span className="translation-particle particle-d" />
    </div>
  );
}

function SearchPreview() {
  return (
    <svg viewBox="0 0 220 160" className="search-preview" role="img" aria-label="Archive similarity search">
      <circle cx="110" cy="80" r="18" className="search-preview-core" />
      {[36, 58, 78].map((ring) => (
        <circle key={ring} cx="110" cy="80" r={ring} className="search-preview-ring" />
      ))}
      {[
        [52, 42],
        [70, 118],
        [150, 52],
        [174, 104],
        [120, 26],
        [92, 132]
      ].map(([x, y], index) => (
        <circle key={index} cx={x} cy={y} r="3.4" className="search-preview-point" />
      ))}
    </svg>
  );
}

function RankingPreview() {
  const rows = [
    ["#1", "0.92", 92],
    ["#2", "0.87", 87],
    ["#3", "0.82", 82],
    ["#4", "0.76", 76]
  ] as const;

  return (
    <div className="ranking-preview" aria-hidden="true">
      {rows.map(([label, score, width]) => (
        <div key={label} className="ranking-row">
          <span>{label}</span>
          <i>
            <b style={{ width: `${width}%` }} />
          </i>
          <span>{score}</span>
        </div>
      ))}
    </div>
  );
}

function DiscoveryPreview() {
  return (
    <div className="discovery-preview" aria-hidden="true">
      <p className="discovery-quote">Maybe happiness was never meant to be permanent.</p>
      <p className="discovery-score">0.92 similarity</p>
      <div className="discovery-tags">
        {["longing", "loss", "memory"].map((tag) => (
          <span key={tag} className="micro-tag">
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}

function ConnectionGraph() {
  const nodes: Array<{ x: number; y: number; size: number; active?: boolean }> = [
    { x: 54, y: 74, size: 4.5 },
    { x: 86, y: 44, size: 4 },
    { x: 118, y: 88, size: 4 },
    { x: 164, y: 56, size: 4 },
    { x: 188, y: 102, size: 4.5 },
    { x: 152, y: 144, size: 4 },
    { x: 90, y: 150, size: 4.5 },
    { x: 44, y: 126, size: 4 },
    { x: 120, y: 112, size: 10, active: true },
    { x: 204, y: 148, size: 3.5 },
    { x: 204, y: 78, size: 3.5 },
    { x: 24, y: 28, size: 3.5 }
  ];

  const edges = [
    [0, 1],
    [0, 8],
    [1, 2],
    [1, 3],
    [2, 4],
    [2, 8],
    [3, 8],
    [4, 8],
    [5, 8],
    [6, 8],
    [7, 8],
    [5, 10],
    [7, 11],
    [6, 9]
  ] as const;

  return (
    <svg viewBox="0 0 240 180" className="connection-graph" role="img" aria-label="Network of related letters">
      {edges.map(([from, to], index) => (
        <line
          key={index}
          x1={nodes[from].x}
          y1={nodes[from].y}
          x2={nodes[to].x}
          y2={nodes[to].y}
          className="connection-edge"
        />
      ))}
      {nodes.map((node, index) => (
        <circle
          key={index}
          cx={node.x}
          cy={node.y}
          r={node.size}
          className={node.active ? "connection-node is-active" : "connection-node"}
        />
      ))}
      <text x="138" y="118" className="connection-label">
        Your letter
      </text>
    </svg>
  );
}
