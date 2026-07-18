import { useEffect, useRef } from "react";

/**
 * Tracks the pointer over an element and exposes its position as CSS
 * custom properties (--pointer-x / --pointer-y), throttled to one update
 * per animation frame. Mutates the DOM directly instead of React state so
 * pointer movement never triggers a re-render.
 */
export function usePointerGlow<T extends HTMLElement>(enabled: boolean) {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node || !enabled) return;
    if (!window.matchMedia("(pointer: fine)").matches) return;

    let frame = 0;

    function handlePointerMove(event: PointerEvent) {
      if (frame) return;
      frame = window.requestAnimationFrame(() => {
        frame = 0;
        if (!node) return;
        const rect = node.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width) * 100;
        const y = ((event.clientY - rect.top) / rect.height) * 100;
        node.style.setProperty("--pointer-x", `${x}%`);
        node.style.setProperty("--pointer-y", `${y}%`);
      });
    }

    function handlePointerLeave() {
      if (!node) return;
      node.style.removeProperty("--pointer-x");
      node.style.removeProperty("--pointer-y");
    }

    node.addEventListener("pointermove", handlePointerMove);
    node.addEventListener("pointerleave", handlePointerLeave);

    return () => {
      node.removeEventListener("pointermove", handlePointerMove);
      node.removeEventListener("pointerleave", handlePointerLeave);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [enabled]);

  return ref;
}
