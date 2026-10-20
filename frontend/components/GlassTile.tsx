"use client";

import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

interface GlassTileProps {
  children: ReactNode;
  className?: string;
  /** max tilt in degrees */
  tilt?: number;
  /** disable tilt/lift (used for the console panel) */
  flat?: boolean;
  as?: "div" | "article" | "section";
}

/**
 * A translucent glass tile that tilts toward the cursor in 3D and carries
 * a local specular highlight. Tilt is spring-smoothed, uses only transform
 * (compositor-friendly), and is disabled for touch devices and users who
 * prefer reduced motion.
 */
export function GlassTile({ children, className = "", tilt = 7, flat = false, as = "div" }: GlassTileProps) {
  const reduce = useReducedMotion();
  const [hoverCapable, setHoverCapable] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setHoverCapable(window.matchMedia("(hover: hover) and (pointer: fine)").matches);
  }, []);

  const interactive = hoverCapable && !reduce && !flat;

  const px = useMotionValue(0.5);
  const py = useMotionValue(0.5);
  const spring = { stiffness: 220, damping: 22, mass: 0.6 };
  const rotateX = useSpring(useTransform(py, [0, 1], [tilt, -tilt]), spring);
  const rotateY = useSpring(useTransform(px, [0, 1], [-tilt, tilt]), spring);
  const lift = useSpring(1, { stiffness: 260, damping: 20 });

  const onMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const el = ref.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width;
      const y = (e.clientY - r.top) / r.height;
      px.set(x);
      py.set(y);
      el.style.setProperty("--lx", `${x * 100}%`);
      el.style.setProperty("--ly", `${y * 100}%`);
    },
    [px, py],
  );

  const onEnter = useCallback(() => {
    lift.set(1.02);
    ref.current?.style.setProperty("--lit", "1");
  }, [lift]);

  const onLeave = useCallback(() => {
    px.set(0.5);
    py.set(0.5);
    lift.set(1);
    ref.current?.style.setProperty("--lit", "0");
  }, [px, py, lift]);

  const MotionTag = as === "article" ? motion.article : as === "section" ? motion.section : motion.div;

  return (
    <div style={{ perspective: interactive ? 1000 : undefined }} className="h-full">
      <MotionTag
        ref={ref as React.Ref<HTMLDivElement>}
        className={`glass ${interactive ? "glass-lit" : ""} ${className}`}
        style={
          interactive
            ? { rotateX, rotateY, scale: lift, transformStyle: "preserve-3d" }
            : undefined
        }
        onPointerMove={interactive ? onMove : undefined}
        onPointerEnter={interactive ? onEnter : undefined}
        onPointerLeave={interactive ? onLeave : undefined}
      >
        {children}
      </MotionTag>
    </div>
  );
}
