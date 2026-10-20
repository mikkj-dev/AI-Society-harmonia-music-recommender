"use client";

import { AnimatePresence, LayoutGroup, motion, useReducedMotion } from "framer-motion";
import { useEffect, useId, useRef, useState } from "react";
import { api, type Mode, type Song } from "@/lib/api";
import { GlassTile } from "./GlassTile";

export interface ConsoleSubmit {
  mode: Mode;
  query: string;
  topN: number;
  seedSongId: string | null;
}

interface Props {
  busy: boolean;
  topNBounds: { min: number; max: number };
  initialTopN: number;
  value: { mode: Mode; query: string; seedSongId: string | null };
  onChange: (v: { mode: Mode; query: string; seedSongId: string | null }) => void;
  onSubmit: (s: ConsoleSubmit) => void;
  onRandom: (topN: number) => void;
}

const MODES: { id: Mode; label: string; placeholder: string; hint: string }[] = [
  {
    id: "song_name",
    label: "Song",
    placeholder: "Dancing Queen, Yesterday, Hallelujah…",
    hint: "Partial, case-insensitive. The first matching song becomes the seed; pick another from the list if you like.",
  },
  {
    id: "artist",
    label: "Artist",
    placeholder: "ABBA, The Beatles, Dolly Parton…",
    hint: "Matches any artist containing your text. The artist's first song in the catalogue is the seed.",
  },
  {
    id: "song_id",
    label: "Song ID",
    placeholder: "S00000 … S57649",
    hint: "Exact catalogue ID. Every card shows its ID so you can come back to it.",
  },
  {
    id: "text",
    label: "Describe",
    placeholder: "upbeat pop dance, rainy night piano, heartbreak country…",
    hint: "Free text is scored against titles, artists, genres and lyrics with the same TF-IDF model.",
  },
];

export function SearchConsole({ busy, topNBounds, initialTopN, value, onChange, onSubmit, onRandom }: Props) {
  const reduce = useReducedMotion();
  const [topN, setTopN] = useState(initialTopN);
  const [matches, setMatches] = useState<Song[]>([]);
  const [matchTotal, setMatchTotal] = useState(0);
  const [showMatches, setShowMatches] = useState(false);
  const [searching, setSearching] = useState(false);
  const inputId = useId();
  const listId = useId();
  const sliderId = useId();
  const inputRef = useRef<HTMLInputElement>(null);

  const mode = MODES.find((m) => m.id === value.mode) ?? MODES[0];
  const searchable = value.mode === "song_name" || value.mode === "artist";

  // Live matches for song / artist modes (debounced + abortable).
  useEffect(() => {
    if (!searchable || value.query.trim().length < 2) {
      setMatches([]);
      setMatchTotal(0);
      return;
    }
    const ctrl = new AbortController();
    const t = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await api.search(value.query, value.mode === "artist" ? "artist" : "song", 8, ctrl.signal);
        setMatches(res.results);
        setMatchTotal(res.total);
      } catch {
        /* a failed suggestion lookup is not an error state; the main submit will report problems */
      } finally {
        setSearching(false);
      }
    }, 220);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [value.query, value.mode, searchable]);

  const pct = ((topN - topNBounds.min) / (topNBounds.max - topNBounds.min)) * 100;

  function submit() {
    setShowMatches(false);
    onSubmit({ mode: value.mode, query: value.query, topN, seedSongId: value.seedSongId });
  }

  function chooseMatch(s: Song) {
    onChange({ ...value, query: s.song, seedSongId: s.song_id });
    setShowMatches(false);
    onSubmit({ mode: value.mode, query: s.song, topN, seedSongId: s.song_id });
  }

  return (
    <GlassTile flat className="rounded-tile p-5 sm:p-7">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="space-y-6"
        aria-busy={busy}
      >
        {/* Mode switcher */}
        <LayoutGroup>
          <div
            role="tablist"
            aria-label="Search mode"
            className="glass-inset rounded-2xl p-1 grid grid-cols-2 sm:grid-cols-4 gap-1"
          >
            {MODES.map((m) => {
              const active = m.id === value.mode;
              return (
                <button
                  key={m.id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => {
                    onChange({ mode: m.id, query: "", seedSongId: null });
                    setMatches([]);
                    requestAnimationFrame(() => inputRef.current?.focus());
                  }}
                  className={`relative rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                    active ? "text-charcoal-950" : "text-ink-muted hover:text-ink"
                  }`}
                >
                  {active && (
                    <motion.span
                      layoutId="mode-pill"
                      className="absolute inset-0 rounded-xl bg-gradient-to-br from-emerald-glow to-violet-glow shadow-[0_8px_24px_-8px_rgba(52,211,153,0.6)]"
                      transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 400, damping: 32 }}
                    />
                  )}
                  <span className="relative">{m.label}</span>
                </button>
              );
            })}
          </div>
        </LayoutGroup>

        {/* Query */}
        <div className="relative">
          <label htmlFor={inputId} className="block text-sm text-ink-muted mb-2">
            {value.mode === "text" ? "Describe what you want to hear" : `Search by ${mode.label.toLowerCase()}`}
          </label>
          <div className="glass-inset rounded-2xl flex items-center gap-2 pl-4 pr-2 py-1.5 focus-within:border-emerald-glow/50 transition-colors">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="text-ink-faint shrink-0">
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8" />
              <path d="M20 20l-3.5-3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
            <input
              ref={inputRef}
              id={inputId}
              type="text"
              inputMode={value.mode === "song_id" ? "text" : "search"}
              autoComplete="off"
              spellCheck={false}
              value={value.query}
              placeholder={mode.placeholder}
              onChange={(e) => {
                onChange({ ...value, query: e.target.value, seedSongId: null });
                setShowMatches(true);
              }}
              onFocus={() => setShowMatches(true)}
              onBlur={() => setTimeout(() => setShowMatches(false), 120)}
              onKeyDown={(e) => {
                if (e.key === "Escape") setShowMatches(false);
              }}
              aria-controls={searchable ? listId : undefined}
              aria-expanded={searchable && showMatches && matches.length > 0}
              aria-autocomplete={searchable ? "list" : undefined}
              className="w-full bg-transparent py-2.5 text-base text-ink placeholder:text-ink-faint focus:outline-none"
            />
            <button
              type="submit"
              disabled={busy}
              className="shrink-0 rounded-xl bg-ink text-charcoal-950 px-4 py-2.5 text-sm font-semibold transition hover:bg-white active:scale-[0.98] disabled:opacity-50 disabled:cursor-wait"
            >
              {busy ? "Finding…" : "Recommend"}
            </button>
          </div>
          <p className="mt-2 text-xs text-ink-faint leading-relaxed">{mode.hint}</p>

          {/* Live matches */}
          <AnimatePresence>
            {searchable && showMatches && (matches.length > 0 || searching) && (
              <motion.ul
                id={listId}
                role="listbox"
                aria-label="Matching songs"
                initial={reduce ? false : { opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduce ? undefined : { opacity: 0, y: -6 }}
                transition={{ duration: 0.18 }}
                className="glass absolute left-0 right-0 z-20 mt-2 max-h-72 overflow-auto rounded-2xl p-1.5"
              >
                {matches.map((s, i) => (
                  <li key={s.song_id} role="option" aria-selected={false}>
                    <button
                      type="button"
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => chooseMatch(s)}
                      className="w-full text-left rounded-xl px-3 py-2 hover:bg-white/[0.07] focus:bg-white/[0.07] transition-colors flex items-center gap-3"
                    >
                      <span className="text-xs text-ink-faint font-mono w-14 shrink-0">{s.song_id}</span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm text-ink truncate">{s.song}</span>
                        <span className="block text-xs text-ink-muted truncate">{s.artist}</span>
                      </span>
                      {i === 0 && <span className="text-[11px] text-emerald-glow/80 shrink-0">default seed</span>}
                    </button>
                  </li>
                ))}
                {matchTotal > matches.length && (
                  <li className="px-3 py-1.5 text-xs text-ink-faint">
                    {matchTotal.toLocaleString()} matches in total — keep typing to narrow it down.
                  </li>
                )}
              </motion.ul>
            )}
          </AnimatePresence>
        </div>

        {/* Top-N + random */}
        <div className="grid gap-5 sm:grid-cols-[1fr_auto] sm:items-end">
          <div>
            <div className="flex items-baseline justify-between mb-3">
              <label htmlFor={sliderId} className="text-sm text-ink-muted">
                Results to show
              </label>
              <span className="font-display text-2xl tabular-nums text-ink leading-none">{topN}</span>
            </div>
            <input
              id={sliderId}
              type="range"
              className="topn"
              min={topNBounds.min}
              max={topNBounds.max}
              step={1}
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
              style={{ ["--pct" as string]: `${pct}%` }}
              aria-valuetext={`${topN} songs`}
            />
            <div className="mt-1.5 flex justify-between text-[11px] text-ink-faint tabular-nums">
              <span>{topNBounds.min}</span>
              <span>{topNBounds.max}</span>
            </div>
          </div>
          <button
            type="button"
            disabled={busy}
            onClick={() => onRandom(topN)}
            className="rounded-2xl border border-violet-glow/40 bg-violet-glow/10 px-5 py-3 text-sm font-semibold text-violet-glow transition hover:bg-violet-glow/20 active:scale-[0.98] disabled:opacity-50 disabled:cursor-wait"
          >
            Surprise me
          </button>
        </div>
      </form>
    </GlassTile>
  );
}
