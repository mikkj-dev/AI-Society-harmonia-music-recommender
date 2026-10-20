"use client";

import { motion, useReducedMotion } from "framer-motion";

export function LoadingGrid({ count }: { count: number }) {
  return (
    <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-label="Loading recommendations" aria-busy="true">
      {Array.from({ length: count }).map((_, i) => (
        <li key={i} className="glass shimmer rounded-tile p-5 h-56" aria-hidden="true">
          <div className="h-5 w-10 rounded bg-white/10" />
          <div className="mt-8 h-6 w-3/4 rounded bg-white/10" />
          <div className="mt-3 h-4 w-1/2 rounded bg-white/[0.07]" />
          <div className="mt-10 h-1 w-full rounded bg-white/10" />
        </li>
      ))}
    </ul>
  );
}

export function EmptyState({ onExample }: { onExample: (q: string) => void }) {
  const reduce = useReducedMotion();
  const examples = ["Dancing Queen", "Yesterday", "Hallelujah", "Jolene"];
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.25, duration: 0.5 }}
      className="glass rounded-tile p-8 sm:p-10 text-center"
    >
      <p className="font-display text-2xl sm:text-3xl text-ink leading-tight">
        Start with a song you know
      </p>
      <p className="mt-3 text-ink-muted max-w-md mx-auto">
        Harmonia compares the words in titles, artists, genres and lyrics to find the closest tracks in the catalogue.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {examples.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onExample(q)}
            className="rounded-pill border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-ink-muted hover:text-ink hover:bg-white/[0.09] transition"
          >
            {q}
          </button>
        ))}
      </div>
    </motion.div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="glass rounded-tile p-6 sm:p-8 border-red-400/30">
      <p className="font-display text-xl text-ink">Nothing to show yet</p>
      <p className="mt-2 text-ink-muted">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-xl border border-white/15 px-4 py-2 text-sm text-ink hover:bg-white/[0.08] transition"
        >
          Try again
        </button>
      )}
    </div>
  );
}

export function BackendBanner({ detail, apiUrl }: { detail: string | null; apiUrl: string }) {
  return (
    <div role="status" className="glass rounded-2xl px-4 py-3 text-sm text-ink-muted border-amber-300/25">
      <span className="text-amber-200">The recommendation API isn’t ready.</span>{" "}
      {detail ?? `Expected it at ${apiUrl}. Start the backend (see README) — this page will reconnect automatically.`}
    </div>
  );
}
