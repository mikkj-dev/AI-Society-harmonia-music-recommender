"use client";

import { useEffect } from "react";

/**
 * Floating gradient orbs + a pointer-reactive radial light.
 * Pointer tracking is rAF-throttled and writes two CSS variables; the
 * gradients themselves are pure CSS so nothing re-renders in React.
 */
export function AmbientBackground() {
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const coarse = window.matchMedia("(hover: none)").matches;
    if (reduce || coarse) return;

    let frame = 0;
    let x = 0;
    let y = 0;
    const root = document.documentElement;
    const onMove = (e: PointerEvent) => {
      x = e.clientX;
      y = e.clientY;
      if (!frame) {
        frame = requestAnimationFrame(() => {
          root.style.setProperty("--mx", `${x}px`);
          root.style.setProperty("--my", `${y}px`);
          frame = 0;
        });
      }
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <div className="scene" aria-hidden="true">
      <div className="orb orb-a" />
      <div className="orb orb-b" />
      <div className="orb orb-c" />
      <div className="grain" />
    </div>
  );
}
