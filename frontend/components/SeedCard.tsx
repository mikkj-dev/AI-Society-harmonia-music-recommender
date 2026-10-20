"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { RecommendResponse } from "@/lib/api";
import { GlassTile } from "./GlassTile";

const modeLabel: Record<string, string> = {
  song_name: "Matched by song name",
  song_id: "Matched by song ID",
  artist: "Matched by artist",
  random: "Random pick",
  text: "Custom description",
};

/**
 * The seed: the track (or text) every recommendation is measured against.
 * A spinning emerald→violet disc reads as a record; the label is the
 * title, artist, genre and ID straight from the dataset.
 */
export function SeedCard({ result }: { result: RecommendResponse }) {
  const reduce = useReducedMotion();
  const seed = result.seed;
  const unknownGenre = !seed?.genre || seed.genre.toLowerCase() === "unknown";

  return (
    <GlassTile flat className="rounded-tile p-6 sm:p-7 overflow-hidden">
      <div className="flex flex-col sm:flex-row gap-6 sm:items-center">
        <motion.div
          aria-hidden="true"
          className="relative shrink-0 h-28 w-28 sm:h-32 sm:w-32 rounded-full"
          style={{
            background:
              "conic-gradient(from 20deg, rgb(52 211 153), rgb(167 139 250), rgb(16 185 129), rgb(139 92 246), rgb(52 211 153))",
            boxShadow: "0 0 0 1px rgba(255,255,255,0.12), 0 20px 50px -14px rgba(167,139,250,0.55)",
          }}
          animate={reduce ? undefined : { rotate: 360 }}
          transition={reduce ? undefined : { duration: 28, repeat: Infinity, ease: "linear" }}
        >
          <div className="absolute inset-[6px] rounded-full bg-charcoal-950/80 backdrop-blur-sm" />
          <div className="absolute inset-[26%] rounded-full bg-charcoal-900 border border-white/10" />
          <div className="absolute inset-[46%] rounded-full bg-emerald-glow/80 shadow-[0_0_24px_rgba(52,211,153,0.6)]" />
        </motion.div>

        <div className="min-w-0 flex-1">
          <p className="text-sm text-ink-muted">{modeLabel[result.mode] ?? "Seed"}</p>
          {seed ? (
            <>
              <h2 className="mt-1 font-display text-3xl sm:text-4xl leading-[1.05] text-ink break-words">
                {seed.song}
              </h2>
              <p className="mt-2 text-base text-ink-muted">{seed.artist}</p>
              <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
                <span
                  className={`rounded-pill px-2.5 py-1 border whitespace-nowrap ${
                    unknownGenre
                      ? "border-white/10 text-ink-faint"
                      : "border-violet-glow/40 text-violet-glow bg-violet-glow/10"
                  }`}
                >
                  {unknownGenre ? "No genre" : seed.genre}
                </span>
                <span className="rounded-pill px-2.5 py-1 border border-white/10 text-ink-muted font-mono">
                  {seed.song_id}
                </span>
                {result.matches_total !== null && result.matches_total > 1 && (
                  <span className="text-ink-faint">
                    first of {result.matches_total.toLocaleString()} matches for “{result.query}”
                  </span>
                )}
              </div>
            </>
          ) : (
            <>
              <h2 className="mt-1 font-display italic text-2xl sm:text-3xl leading-snug text-ink break-words">
                “{result.query}”
              </h2>
              <p className="mt-3 text-sm text-ink-muted max-w-prose">
                Your words were vectorised with the same TF-IDF model as the catalogue and ranked by cosine
                similarity. Specific words that appear in titles, artists, genres or lyrics score highest.
              </p>
            </>
          )}
        </div>
      </div>
    </GlassTile>
  );
}
