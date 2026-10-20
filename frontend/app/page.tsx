"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, apiBaseUrl, ApiError, type Health, type Mode, type Recommendation, type RecommendResponse } from "@/lib/api";
import { SearchConsole, type ConsoleSubmit } from "@/components/SearchConsole";
import { SeedCard } from "@/components/SeedCard";
import { RecommendationCard } from "@/components/RecommendationCard";
import { BackendBanner, EmptyState, ErrorState, LoadingGrid } from "@/components/StateViews";

const FALLBACK_BOUNDS = { min: 3, max: 20, default: 10 };

const gridVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.055, delayChildren: 0.08 } },
};

export default function Page() {
  const reduce = useReducedMotion();
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [form, setForm] = useState<{ mode: Mode; query: string; seedSongId: string | null }>({
    mode: "song_name",
    query: "",
    seedSongId: null,
  });
  const [result, setResult] = useState<RecommendResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastTopN, setLastTopN] = useState(FALLBACK_BOUNDS.default);
  const resultsRef = useRef<HTMLDivElement>(null);
  const lastAction = useRef<(() => void) | null>(null);

  // Poll /health until the engine is ready, then stop.
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const h = await api.health();
        if (cancelled) return;
        setHealth(h);
        setHealthError(null);
        if (!h.ready) timer = setTimeout(poll, 2500);
      } catch (e) {
        if (cancelled) return;
        setHealthError(e instanceof Error ? e.message : "Unknown error");
        timer = setTimeout(poll, 4000);
      }
    };
    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  const bounds = health?.top_n ?? FALLBACK_BOUNDS;
  const ready = Boolean(health?.ready);

  const run = useCallback(
    async (fn: () => Promise<RecommendResponse>, topN: number) => {
      setLoading(true);
      setError(null);
      setLastTopN(topN);
      lastAction.current = () => run(fn, topN);
      try {
        const r = await fn();
        setResult(r);
        requestAnimationFrame(() =>
          resultsRef.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" }),
        );
      } catch (e) {
        setResult(null);
        setError(e instanceof ApiError || e instanceof Error ? e.message : "Something went wrong.");
      } finally {
        setLoading(false);
      }
    },
    [reduce],
  );

  const onSubmit = useCallback(
    (s: ConsoleSubmit) => {
      if (!s.query.trim() && !s.seedSongId) {
        setError("Please enter something.");
        setResult(null);
        return;
      }
      run(() => api.recommend({ mode: s.mode, query: s.query, top_n: s.topN, seed_song_id: s.seedSongId }), s.topN);
    },
    [run],
  );

  const onRandom = useCallback((topN: number) => run(() => api.random(topN), topN), [run]);

  const useAsSeed = useCallback(
    (song: Recommendation) => {
      setForm({ mode: "song_id", query: song.song_id, seedSongId: null });
      run(() => api.recommend({ mode: "song_id", query: song.song_id, top_n: lastTopN }), lastTopN);
      window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
    },
    [run, lastTopN, reduce],
  );

  const onExample = useCallback(
    (q: string) => {
      setForm({ mode: "song_name", query: q, seedSongId: null });
      run(() => api.recommend({ mode: "song_name", query: q, top_n: lastTopN }), lastTopN);
    },
    [run, lastTopN],
  );

  return (
    <main className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pb-24 pt-[max(1.5rem,env(safe-area-inset-top))]">
      <a href="#results" className="sr-only-focusable fixed left-4 top-4 z-50 rounded-xl bg-ink px-3 py-2 text-sm text-charcoal-950">
        Skip to results
      </a>

      {/* Header */}
      <header className="flex items-center justify-between py-4">
        <div className="flex items-center gap-3">
          <span
            aria-hidden="true"
            className="h-8 w-8 rounded-full bg-[conic-gradient(from_20deg,#34d399,#a78bfa,#10b981,#8b5cf6,#34d399)] shadow-[0_0_24px_-4px_rgba(167,139,250,0.7)]"
          />
          <span className="font-display text-xl tracking-tight">Harmonia</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-ink-muted">
          <span
            className={`h-2 w-2 rounded-full ${ready ? "bg-emerald-glow shadow-[0_0_10px_rgba(52,211,153,0.9)]" : healthError ? "bg-red-400" : "bg-amber-300 animate-pulse"}`}
            aria-hidden="true"
          />
          <span>{ready ? "Engine ready" : healthError ? "API offline" : "Loading model…"}</span>
        </div>
      </header>

      {/* Hero */}
      <section className="pt-10 pb-10 sm:pt-16 sm:pb-14 max-w-3xl">
        <motion.h1
          initial={reduce ? false : { opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="font-display font-light text-[clamp(2.6rem,7vw,5.25rem)] leading-[0.98] tracking-[-0.02em] text-ink"
        >
          Songs that sound like
          <br />
          <em className="not-italic text-gradient">the one in your head.</em>
        </motion.h1>
        <motion.p
          initial={reduce ? false : { opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.12, ease: [0.22, 1, 0.36, 1] }}
          className="mt-6 text-lg text-ink-muted max-w-xl leading-relaxed"
        >
          Harmonia reads titles, artists, genres and lyrics
          {health?.songs ? ` across ${health.songs.toLocaleString()} tracks` : ""} and ranks the closest matches by
          cosine similarity. No accounts, no streaming — just the catalogue.
        </motion.p>
      </section>

      {!ready && (
        <div className="mb-6">
          <BackendBanner detail={health?.detail ?? null} apiUrl={apiBaseUrl()} />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,420px)_1fr] lg:items-start">
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          className="lg:sticky lg:top-6"
        >
          <SearchConsole
            busy={loading || !ready}
            topNBounds={bounds}
            initialTopN={bounds.default}
            value={form}
            onChange={setForm}
            onSubmit={onSubmit}
            onRandom={onRandom}
          />
        </motion.div>

        <div id="results" ref={resultsRef} className="scroll-mt-6 space-y-5 min-w-0" aria-live="polite">
          {loading ? (
            <>
              <div className="glass shimmer rounded-tile h-40" aria-hidden="true" />
              <LoadingGrid count={Math.min(lastTopN, 6)} />
            </>
          ) : error ? (
            <ErrorState message={error} onRetry={lastAction.current ? () => lastAction.current?.() : undefined} />
          ) : result ? (
            <AnimatePresence mode="wait">
              <motion.div
                key={`${result.mode}-${result.seed?.song_id ?? result.query}-${result.recommendations.length}`}
                initial={reduce ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-5"
              >
                <SeedCard result={result} />
                <div className="flex items-baseline justify-between px-1">
                  <h2 className="font-display text-xl text-ink">
                    {result.recommendations.length} closest {result.recommendations.length === 1 ? "track" : "tracks"}
                  </h2>
                  <span className="text-xs text-ink-faint">Seed track excluded</span>
                </div>
                {result.recommendations.length === 0 ? (
                  <ErrorState message="The engine returned no recommendations for this seed." />
                ) : (
                  <motion.ul
                    variants={reduce ? undefined : gridVariants}
                    initial={reduce ? false : "hidden"}
                    animate="show"
                    className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
                  >
                    {result.recommendations.map((item) => (
                      <RecommendationCard key={item.song_id} item={item} onUseAsSeed={useAsSeed} />
                    ))}
                  </motion.ul>
                )}
                {result.mode === "text" && result.recommendations.every((r) => r.score === 0) && (
                  <p className="text-sm text-ink-faint px-1">
                    None of those words appear in the model vocabulary, so every score is zero. Try more concrete words —
                    a genre, a mood, or lyrics you remember.
                  </p>
                )}
              </motion.div>
            </AnimatePresence>
          ) : (
            <EmptyState onExample={onExample} />
          )}
        </div>
      </div>

      <footer className="mt-20 text-xs text-ink-faint flex flex-wrap gap-x-6 gap-y-2">
        <span>Content-based recommender · TF-IDF (5,000 features) · cosine similarity</span>
        {health?.vectorizer_source && <span>Vectorizer: {health.vectorizer_source}</span>}
      </footer>
    </main>
  );
}
