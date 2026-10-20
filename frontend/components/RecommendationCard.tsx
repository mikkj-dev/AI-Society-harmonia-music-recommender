"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { Recommendation } from "@/lib/api";
import { GlassTile } from "./GlassTile";

interface Props {
  item: Recommendation;
  onUseAsSeed: (song: Recommendation) => void;
}

export const cardVariants = {
  hidden: { opacity: 0, y: 26, scale: 0.97 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring" as const, stiffness: 260, damping: 26, mass: 0.7 },
  },
};

function formatScore(s: number) {
  return s.toFixed(3);
}

export function RecommendationCard({ item, onUseAsSeed }: Props) {
  const reduce = useReducedMotion();
  const pct = Math.max(0, Math.min(1, item.score)) * 100;
  const unknownGenre = !item.genre || item.genre.toLowerCase() === "unknown";

  return (
    <motion.li variants={reduce ? undefined : cardVariants} className="list-none h-full">
      <GlassTile as="article" className="rounded-tile p-5 h-full flex flex-col gap-4">
        <div className="flex items-start justify-between gap-3" style={{ transform: "translateZ(18px)" }}>
          <span
            className="font-display text-2xl leading-none text-ink-muted tabular-nums"
            aria-label={`Rank ${item.rank}`}
          >
            {item.rank}
          </span>
          <span className="text-xs text-ink-faint font-mono tracking-wide" title="Song ID">
            {item.song_id}
          </span>
        </div>

        <div className="min-h-0 flex-1" style={{ transform: "translateZ(24px)" }}>
          <h3 className="font-display text-[1.35rem] leading-[1.15] text-ink line-clamp-2" title={item.song}>
            {item.song}
          </h3>
          <p className="mt-1.5 text-sm text-ink-muted line-clamp-1" title={item.artist}>
            {item.artist}
          </p>
        </div>

        <div className="space-y-2.5" style={{ transform: "translateZ(12px)" }}>
          <div className="flex items-center justify-between text-xs">
            <span
              className={`rounded-pill px-2.5 py-1 border whitespace-nowrap ${
                unknownGenre
                  ? "border-white/10 text-ink-faint"
                  : "border-emerald-glow/30 text-emerald-glow bg-emerald-glow/10"
              }`}
            >
              {unknownGenre ? "No genre" : item.genre}
            </span>
            <span className="tabular-nums text-ink-muted whitespace-nowrap">
              <span className="text-ink font-semibold">{formatScore(item.score)}</span> similarity
            </span>
          </div>
          <div className="sim-track" role="meter" aria-valuemin={0} aria-valuemax={1} aria-valuenow={item.score} aria-label="Cosine similarity">
            <motion.div
              className="sim-fill"
              initial={reduce ? { scaleX: pct / 100 } : { scaleX: 0 }}
              animate={{ scaleX: pct / 100 }}
              transition={{ type: "spring", stiffness: 120, damping: 20, delay: 0.1 }}
            />
          </div>
          <button
            type="button"
            onClick={() => onUseAsSeed(item)}
            className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-ink-muted transition hover:bg-white/[0.09] hover:text-ink active:scale-[0.99]"
          >
            Find songs like this
          </button>
        </div>
      </GlassTile>
    </motion.li>
  );
}
