"""Content-based music recommender (TF-IDF + cosine similarity).

This module is a faithful port of the authoritative notebook
(`docs/original_notebook.ipynb`). The preprocessing, feature construction,
song-ID scheme, similarity computation and ranking are kept identical so the
API returns the same results as the notebook:

    text    = lower(song + " " + artist + " " + genre + " " + lyrics)
    tfidf   = TfidfVectorizer(max_features=5000, stop_words="english")
    X       = tfidf.fit_transform(text)
    song_id = "S" + zero-padded row index (S00000, S00001, ...)

    recommend_by_song: cosine(X[idx], X), seed set to -1, argpartition top-N
    recommend_by_text: cosine(tfidf.transform([query.lower()]), X), top-N

The matrix is built once (or loaded from cached artifacts) and kept in memory
for the lifetime of the process; requests never recompute it.
"""

from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import joblib
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import Settings, get_settings

log = logging.getLogger("harmonia.engine")

ARTIFACT_FORMAT_VERSION = 1
VECTORIZER_FILE = "tfidf_vectorizer.pkl"
MATRIX_FILE = "tfidf_matrix.npz"
CATALOG_FILE = "songs.csv"
MANIFEST_FILE = "manifest.json"

SearchField = Literal["song", "artist", "any"]


class EngineError(RuntimeError):
    """Raised for invalid recommendation requests (bad ID, no match, ...)."""


@dataclass(frozen=True)
class Song:
    song_id: str
    song: str
    artist: str
    genre: str
    link: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "song_id": self.song_id,
            "song": self.song,
            "artist": self.artist,
            "genre": self.genre,
            "link": self.link,
        }


# --------------------------------------------------------------------------- #
# Dataset preparation (identical to the notebook)
# --------------------------------------------------------------------------- #
def load_dataset(csv_path: Path) -> pd.DataFrame:
    """Load the CSV and apply the notebook's exact preprocessing."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found at {csv_path}")
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower() for c in df.columns]
    if "text" in df.columns and "lyrics" not in df.columns:
        df = df.rename(columns={"text": "lyrics"})
    expected = {"artist", "song", "genre", "lyrics"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in CSV: {missing}. Required: {expected}")
    if "link" not in df.columns:
        df["link"] = ""

    for col in ("artist", "song", "genre", "lyrics", "link"):
        df[col] = df[col].astype(str).fillna("").str.strip()

    df["text"] = (
        df["song"] + " " + df["artist"] + " " + df["genre"] + " " + df["lyrics"]
    ).str.lower()
    df = df.reset_index(drop=True)
    df["song_id"] = df.index.map(lambda x: f"S{str(x).zfill(5)}")
    return df


def new_vectorizer(settings: Settings) -> TfidfVectorizer:
    return TfidfVectorizer(
        max_features=settings.tfidf_max_features, stop_words=settings.tfidf_stop_words
    )


def validate_vectorizer(obj: Any, settings: Settings) -> list[str]:
    """Return a list of problems with a loaded vectorizer (empty == valid)."""
    problems: list[str] = []
    if not isinstance(obj, TfidfVectorizer):
        return [f"object is {type(obj).__name__}, not TfidfVectorizer"]
    if not hasattr(obj, "vocabulary_") or not hasattr(obj, "idf_"):
        problems.append("vectorizer is not fitted (missing vocabulary_/idf_)")
        return problems
    if obj.max_features != settings.tfidf_max_features:
        problems.append(f"max_features={obj.max_features} != {settings.tfidf_max_features}")
    if obj.stop_words != settings.tfidf_stop_words:
        problems.append(f"stop_words={obj.stop_words!r} != {settings.tfidf_stop_words!r}")
    if len(obj.vocabulary_) != len(obj.idf_):
        problems.append("vocabulary_/idf_ size mismatch")
    if len(obj.vocabulary_) > settings.tfidf_max_features:
        problems.append("vocabulary larger than max_features")
    return problems


def load_notebook_vectorizer(settings: Settings) -> TfidfVectorizer | None:
    """Load the notebook's saved vectorizer if it exists and is compatible."""
    path = settings.notebook_vectorizer_path
    if not path.exists():
        log.info("Notebook vectorizer not present at %s", path)
        return None
    try:
        obj = joblib.load(path)
    except Exception as exc:  # noqa: BLE001 - any unpickling failure means "rebuild"
        log.warning("Could not load notebook vectorizer (%s); will refit", exc)
        return None
    problems = validate_vectorizer(obj, settings)
    if problems:
        log.warning("Notebook vectorizer rejected: %s; will refit", "; ".join(problems))
        return None
    return obj


# --------------------------------------------------------------------------- #
# Artifact building / loading
# --------------------------------------------------------------------------- #
@dataclass
class Artifacts:
    vectorizer: TfidfVectorizer
    matrix: sp.csr_matrix
    catalog: pd.DataFrame  # song_id, song, artist, genre, link (no lyrics)
    manifest: dict[str, Any]


def build_artifacts(
    settings: Settings | None = None, *, prefer_notebook_vectorizer: bool = True
) -> Artifacts:
    """Build the TF-IDF matrix and catalogue from the raw CSV."""
    settings = settings or get_settings()
    t0 = time.perf_counter()
    df = load_dataset(settings.data_path)
    log.info("Loaded %d rows from %s", len(df), settings.data_path)

    vectorizer: TfidfVectorizer | None = None
    source = "refit"
    if prefer_notebook_vectorizer:
        vectorizer = load_notebook_vectorizer(settings)
        if vectorizer is not None:
            source = "notebook"

    if vectorizer is not None:
        # The notebook vectorizer was fitted on this same corpus, so transform()
        # reproduces fit_transform() exactly.
        matrix = vectorizer.transform(df["text"])
    else:
        vectorizer = new_vectorizer(settings)
        matrix = vectorizer.fit_transform(df["text"])
    matrix = sp.csr_matrix(matrix, dtype=np.float64)

    catalog = df[["song_id", "song", "artist", "genre", "link"]].copy()
    manifest = {
        "format_version": ARTIFACT_FORMAT_VERSION,
        "rows": int(matrix.shape[0]),
        "features": int(matrix.shape[1]),
        "vectorizer_source": source,
        "data_path": str(settings.data_path),
        "data_size_bytes": settings.data_path.stat().st_size,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "build_seconds": round(time.perf_counter() - t0, 2),
    }
    log.info("Built TF-IDF matrix %s in %.1fs (vectorizer: %s)", matrix.shape, manifest["build_seconds"], source)
    return Artifacts(vectorizer=vectorizer, matrix=matrix, catalog=catalog, manifest=manifest)


def save_artifacts(artifacts: Artifacts, artifacts_dir: Path) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifacts.vectorizer, artifacts_dir / VECTORIZER_FILE)
    sp.save_npz(artifacts_dir / MATRIX_FILE, artifacts.matrix, compressed=True)
    artifacts.catalog.to_csv(artifacts_dir / CATALOG_FILE, index=False)
    (artifacts_dir / MANIFEST_FILE).write_text(json.dumps(artifacts.manifest, indent=2))
    log.info("Saved artifacts to %s", artifacts_dir)


def artifacts_present(artifacts_dir: Path) -> bool:
    return all(
        (artifacts_dir / f).exists()
        for f in (VECTORIZER_FILE, MATRIX_FILE, CATALOG_FILE, MANIFEST_FILE)
    )


def load_artifacts(settings: Settings) -> Artifacts:
    """Load cached artifacts and check they are consistent with each other."""
    d = settings.artifacts_dir
    manifest = json.loads((d / MANIFEST_FILE).read_text())
    if manifest.get("format_version") != ARTIFACT_FORMAT_VERSION:
        raise ValueError("artifact format version mismatch")
    vectorizer = joblib.load(d / VECTORIZER_FILE)
    problems = validate_vectorizer(vectorizer, settings)
    if problems:
        raise ValueError("cached vectorizer invalid: " + "; ".join(problems))
    matrix = sp.load_npz(d / MATRIX_FILE).tocsr()
    catalog = pd.read_csv(d / CATALOG_FILE, keep_default_na=False, dtype=str)
    if matrix.shape[0] != len(catalog):
        raise ValueError("matrix rows do not match catalogue rows")
    if matrix.shape[1] != len(vectorizer.vocabulary_):
        raise ValueError("matrix columns do not match vectorizer vocabulary")
    if settings.data_path.exists() and manifest.get("data_size_bytes") != settings.data_path.stat().st_size:
        raise ValueError("dataset changed since artifacts were built")
    return Artifacts(vectorizer=vectorizer, matrix=matrix, catalog=catalog, manifest=manifest)


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #
class RecommendationEngine:
    """Holds the fitted model in memory and answers recommendation queries."""

    def __init__(self, artifacts: Artifacts, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.vectorizer = artifacts.vectorizer
        self.matrix = artifacts.matrix
        self.catalog = artifacts.catalog.reset_index(drop=True)
        self.manifest = artifacts.manifest
        self._songid_to_idx = {sid: i for i, sid in enumerate(self.catalog["song_id"])}
        self._song_lower = self.catalog["song"].str.lower()
        self._artist_lower = self.catalog["artist"].str.lower()
        self._rng = random.Random()

    # ---- construction helpers -------------------------------------------- #
    @classmethod
    def from_settings(cls, settings: Settings | None = None, *, allow_build: bool = True) -> "RecommendationEngine":
        settings = settings or get_settings()
        if artifacts_present(settings.artifacts_dir):
            try:
                return cls(load_artifacts(settings), settings)
            except Exception as exc:  # noqa: BLE001
                log.warning("Cached artifacts unusable (%s); rebuilding", exc)
        if not allow_build:
            raise FileNotFoundError(
                f"No valid artifacts in {settings.artifacts_dir}. Run `python scripts/prepare_data.py`."
            )
        artifacts = build_artifacts(settings)
        try:
            save_artifacts(artifacts, settings.artifacts_dir)
        except OSError as exc:
            log.warning("Could not persist artifacts: %s", exc)
        return cls(artifacts, settings)

    # ---- basic accessors -------------------------------------------------- #
    def __len__(self) -> int:
        return int(self.matrix.shape[0])

    @property
    def vocabulary_size(self) -> int:
        return len(self.vectorizer.vocabulary_)

    def song_at(self, idx: int) -> Song:
        row = self.catalog.iloc[idx]
        return Song(
            song_id=str(row["song_id"]),
            song=str(row["song"]),
            artist=str(row["artist"]),
            genre=str(row["genre"]),
            link=str(row["link"]),
        )

    def get_song(self, song_id: str) -> Song:
        idx = self._songid_to_idx.get(song_id)
        if idx is None:
            raise EngineError(f"Invalid song ID: {song_id!r}")
        return self.song_at(idx)

    def has_song(self, song_id: str) -> bool:
        return song_id in self._songid_to_idx

    def genre_counts(self, top: int = 10, exclude_unknown: bool = True) -> list[dict[str, Any]]:
        counts = self.catalog["genre"].value_counts()
        if exclude_unknown:
            counts = counts[counts.index != "Unknown"]
        return [{"genre": g, "count": int(c)} for g, c in counts.head(top).items()]

    # ---- search ----------------------------------------------------------- #
    def search(self, query: str, field: SearchField = "song", limit: int = 10) -> tuple[int, list[Song]]:
        """Case-insensitive substring search.

        Returns (total_matches, first `limit` matches in dataset order), which
        mirrors the notebook's `df[col].str.contains(text, case=False)` and
        its "first match is the seed" rule. Plain substring matching is used
        (regex=False) so punctuation in queries cannot break the search.
        """
        q = query.strip().lower()
        if not q:
            return 0, []
        if field == "song":
            mask = self._song_lower.str.contains(q, regex=False, na=False)
        elif field == "artist":
            mask = self._artist_lower.str.contains(q, regex=False, na=False)
        else:
            mask = self._song_lower.str.contains(q, regex=False, na=False) | self._artist_lower.str.contains(
                q, regex=False, na=False
            )
        idxs = np.flatnonzero(mask.to_numpy())
        return int(idxs.size), [self.song_at(int(i)) for i in idxs[:limit]]

    # ---- ranking core (verbatim notebook semantics) ----------------------- #
    def _top_n(self, sims: np.ndarray, top_n: int) -> np.ndarray:
        k = min(top_n, sims.size)
        top_idx = np.argpartition(-sims, range(k))[:k]
        return top_idx[np.argsort(-sims[top_idx])]

    def _rows(self, order: np.ndarray, sims: np.ndarray) -> list[dict[str, Any]]:
        out = []
        for rank, i in enumerate(order, start=1):
            d = self.song_at(int(i)).as_dict()
            d["score"] = float(sims[i])
            d["rank"] = rank
            out.append(d)
        return out

    def recommend_by_index(self, idx: int, top_n: int) -> list[dict[str, Any]]:
        sims = cosine_similarity(self.matrix[idx], self.matrix).flatten()
        sims[idx] = -1  # exclude the seed from its own recommendations
        return self._rows(self._top_n(sims, top_n), sims)

    def recommend_by_song(self, song_id: str, top_n: int) -> list[dict[str, Any]]:
        idx = self._songid_to_idx.get(song_id)
        if idx is None:
            raise EngineError(f"Invalid song ID: {song_id!r}")
        return self.recommend_by_index(idx, top_n)

    def recommend_by_text(self, seed_text: str, top_n: int) -> list[dict[str, Any]]:
        text = seed_text.strip()
        if not text:
            raise EngineError("Query text is empty.")
        vec = self.vectorizer.transform([text.lower()])
        sims = cosine_similarity(vec, self.matrix).flatten()
        return self._rows(self._top_n(sims, top_n), sims)

    def random_song(self) -> Song:
        return self.song_at(self._rng.randrange(len(self)))

    # ---- high-level modes (mirror the notebook UI handlers) ---------------- #
    def recommend(self, mode: str, query: str, top_n: int, *, seed_song_id: str | None = None) -> dict[str, Any]:
        """Dispatch one of the notebook's four modes.

        `seed_song_id` lets a client pick a specific match from a search
        (instead of the first one) while keeping the notebook's default.
        """
        q = query.strip()
        if mode == "text":
            if not q:
                raise EngineError("Please enter something.")
            return {
                "mode": mode,
                "query": q,
                "seed": None,
                "matches_total": None,
                "recommendations": self.recommend_by_text(q, top_n),
            }

        if mode == "song_id":
            if not q:
                raise EngineError("Please enter something.")
            if not self.has_song(q):
                raise EngineError("Invalid song ID.")
            seed = self.get_song(q)
            total = 1
        elif mode in ("song_name", "artist"):
            if not q and seed_song_id is None:
                raise EngineError("Please enter something.")
            field: SearchField = "song" if mode == "song_name" else "artist"
            total, matches = self.search(q, field=field, limit=1) if q else (0, [])
            if seed_song_id is not None:
                if not self.has_song(seed_song_id):
                    raise EngineError("Invalid song ID.")
                seed = self.get_song(seed_song_id)
            elif not matches:
                raise EngineError(
                    "No song found with that name." if mode == "song_name" else "No songs found for that artist."
                )
            else:
                seed = matches[0]
        else:
            raise EngineError(f"Unknown mode: {mode!r}")

        return {
            "mode": mode,
            "query": q,
            "seed": seed.as_dict(),
            "matches_total": total,
            "recommendations": self.recommend_by_song(seed.song_id, top_n),
        }

    def recommend_random(self, top_n: int) -> dict[str, Any]:
        seed = self.random_song()
        return {
            "mode": "random",
            "query": "",
            "seed": seed.as_dict(),
            "matches_total": None,
            "recommendations": self.recommend_by_song(seed.song_id, top_n),
        }
