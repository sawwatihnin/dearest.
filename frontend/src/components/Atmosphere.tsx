import { useEffect, useRef } from "react";

import { usePrefersReducedMotion } from "../hooks/usePrefersReducedMotion";

interface Star {
  x: number; // 0-1, relative to viewport
  y: number; // 0-1, relative to viewport
  radius: number;
  baseOpacity: number;
  twinkle: boolean;
  speed: number;
  phase: number;
  warm: boolean;
  glow: boolean;
}

// Deterministic PRNG so the star layout is stable across renders/resizes
// instead of reshuffling every time the component mounts.
function mulberry32(seed: number) {
  return function random() {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// A soft diagonal band (roughly through the moon's corner of the sky) that a
// portion of the stars cluster around, so the field reads as a denser
// star-cluster/milky-way drift rather than a uniform scatter.
const CLUSTER_FROM = { x: 0.52, y: -0.05 };
const CLUSTER_TO = { x: 1.02, y: 0.62 };
const CLUSTER_SPREAD = 0.16;

function generateStars(count: number, seed: number): Star[] {
  const random = mulberry32(seed);
  const stars: Star[] = [];
  for (let i = 0; i < count; i += 1) {
    const clustered = random() < 0.4;
    let x: number;
    let y: number;

    if (clustered) {
      const t = random();
      const jitter = (random() - 0.5) * CLUSTER_SPREAD * (0.3 + random());
      const perpX = -(CLUSTER_TO.y - CLUSTER_FROM.y);
      const perpY = CLUSTER_TO.x - CLUSTER_FROM.x;
      x = CLUSTER_FROM.x + (CLUSTER_TO.x - CLUSTER_FROM.x) * t + perpX * jitter;
      y = CLUSTER_FROM.y + (CLUSTER_TO.y - CLUSTER_FROM.y) * t + perpY * jitter;
      x = Math.min(1, Math.max(0, x));
      y = Math.min(1, Math.max(0, y));
    } else {
      x = random();
      y = random();
    }

    const isNear = random() < 0.34;
    const twinkle = isNear && random() < 0.55;
    const warm = random() < 0.09;
    stars.push({
      x,
      y,
      radius: isNear ? 0.9 + random() * 1.2 : 0.4 + random() * 0.5,
      baseOpacity: isNear ? 0.5 + random() * 0.42 : 0.22 + random() * 0.28,
      twinkle,
      speed: 0.00006 + random() * 0.00012,
      phase: random() * Math.PI * 2,
      warm,
      glow: isNear && random() < 0.6
    });
  }
  return stars;
}

function StarField() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const reducedMotion = usePrefersReducedMotion();

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    let stars: Star[] = [];
    let width = 0;
    let height = 0;
    let dpr = 1;
    let frameId = 0;

    function resize() {
      width = window.innerWidth;
      height = window.innerHeight;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas!.width = width * dpr;
      canvas!.height = height * dpr;
      const starCount = width < 640 ? 90 : width < 1100 ? 150 : 210;
      stars = generateStars(starCount, 1337);
      draw(performance.now());
    }

    function draw(time: number) {
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx!.clearRect(0, 0, width, height);
      for (const star of stars) {
        let opacity = star.baseOpacity;
        if (star.twinkle && !reducedMotion) {
          opacity = star.baseOpacity * (0.55 + 0.45 * Math.sin(time * star.speed + star.phase));
        }
        opacity = Math.max(0, Math.min(1, opacity));
        const color = star.warm ? "215, 196, 156" : "245, 238, 223";
        const px = star.x * width;
        const py = star.y * height;

        if (star.glow) {
          ctx!.shadowBlur = star.radius * 4.5;
          ctx!.shadowColor = `rgba(${color}, ${(opacity * 0.8).toFixed(3)})`;
        } else {
          ctx!.shadowBlur = 0;
        }

        ctx!.beginPath();
        ctx!.fillStyle = `rgba(${color}, ${opacity.toFixed(3)})`;
        ctx!.arc(px, py, star.radius, 0, Math.PI * 2);
        ctx!.fill();
      }
      ctx!.shadowBlur = 0;
    }

    function loop(time: number) {
      draw(time);
      frameId = window.requestAnimationFrame(loop);
    }

    resize();
    window.addEventListener("resize", resize);

    function handleVisibility() {
      if (document.hidden) {
        window.cancelAnimationFrame(frameId);
      } else if (!reducedMotion) {
        frameId = window.requestAnimationFrame(loop);
      }
    }

    if (!reducedMotion) {
      frameId = window.requestAnimationFrame(loop);
    }
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", handleVisibility);
      window.cancelAnimationFrame(frameId);
    };
  }, [reducedMotion]);

  return <canvas ref={canvasRef} className="star-canvas" aria-hidden="true" />;
}

function CloudLayer() {
  return (
    <div className="cloud-layer" aria-hidden="true">
      <div className="cloud cloud-a" />
      <div className="cloud cloud-b" />
      <div className="cloud cloud-c" />
    </div>
  );
}

function MistLayer() {
  return (
    <div className="mist-layer" aria-hidden="true">
      <div className="mist mist-a" />
      <div className="mist mist-b" />
      <div className="mist-scrim" />
    </div>
  );
}

function GrainOverlay() {
  return (
    <svg className="grain-overlay" aria-hidden="true">
      <filter id="dearestGrain">
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#dearestGrain)" />
    </svg>
  );
}

export function Atmosphere() {
  return (
    <div className="atmosphere" aria-hidden="true">
      <div className="atmosphere-wash" />
      <div className="nebula-glow" />
      <StarField />
      <CloudLayer />
      <MistLayer />
      <GrainOverlay />
      <div className="vignette" />
    </div>
  );
}
