/**
 * Typed client for the Harmonia recommendation API.
 *
 * The backend base URL comes from NEXT_PUBLIC_API_URL (see .env.example).
 * It is read in exactly one place so the app can be re-pointed at a
 * production backend without touching component code.
 */

export type Mode = "song_name" | "song_id" | "artist" | "text";
export type SearchField = "song" | "artist" | "any";

export interface Song {
  song_id: string;
  song: string;
  artist: string;
  genre: string;
  link: string;
}

export interface Recommendation extends Song {
  score: number;
  rank: number;
}

export interface RecommendResponse {
  mode: Mode | "random";
  query: string;
  seed: Song | null;
  matches_total: number | null;
  recommendations: Recommendation[];
}

export interface SearchResponse {
  query: string;
  field: SearchField;
  total: number;
  results: Song[];
}

export interface Health {
  status: "ok" | "loading" | "error";
  ready: boolean;
  songs: number | null;
  vocabulary: number | null;
  vectorizer_source: string | null;
  artifacts_built_at: string | null;
  top_n: { min: number; max: number; default: number };
  detail: string | null;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const DEFAULT_DEV_API = "http://localhost:8000";

export function apiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL;
  const url = raw && raw.trim() ? raw.trim() : DEFAULT_DEV_API;
  return url.replace(/\/+$/, "");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      `Can't reach the recommendation API at ${apiBaseUrl()}. Start the backend or check NEXT_PUBLIC_API_URL.`,
      0,
    );
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) detail = String(body.detail[0].msg);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => request<Health>("/health"),

  search: (q: string, field: SearchField = "song", limit = 8, signal?: AbortSignal) =>
    request<SearchResponse>(
      `/songs/search?q=${encodeURIComponent(q)}&field=${field}&limit=${limit}`,
      { signal },
    ),

  recommend: (body: { mode: Mode; query: string; top_n: number; seed_song_id?: string | null }) =>
    request<RecommendResponse>("/recommend", { method: "POST", body: JSON.stringify(body) }),

  random: (top_n: number) =>
    request<RecommendResponse>("/recommend/random", {
      method: "POST",
      body: JSON.stringify({ top_n }),
    }),
};
