import { useCallback, useRef, useState } from "react";

import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

/**
 * Reveals an element once, the first time it enters the viewport.
 * Returns a ref + className to spread directly onto the element so no
 * extra wrapper DOM node is needed.
 *
 * Uses a callback ref (rather than useEffect + useRef) so that sections
 * mounted behind a loading/conditional gate -- where the node doesn't
 * exist yet at first render -- still get observed the moment they appear.
 */
export function useSectionReveal<T extends HTMLElement>() {
  const [visible, setVisible] = useState(false);
  const reducedMotion = usePrefersReducedMotion();
  const observerRef = useRef<IntersectionObserver | null>(null);

  const ref = useCallback(
    (node: T | null) => {
      observerRef.current?.disconnect();
      observerRef.current = null;

      if (!node) return;

      if (reducedMotion) {
        setVisible(true);
        return;
      }

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              setVisible(true);
              observer.disconnect();
            }
          });
        },
        { threshold: 0, rootMargin: "0px 0px -10% 0px" }
      );
      observer.observe(node);
      observerRef.current = observer;
    },
    [reducedMotion]
  );

  return { ref, className: visible ? "is-revealed" : "reveal-pending" };
}
