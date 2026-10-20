"""Runtime configuration for the Harmonia recommendation API.

Every path is project-relative by default and can be overridden with an
environment variable, so nothing here depends on the layout of a particular
development machine. See `.env.example` at the repository root.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# <repo>/backend/app/config.py -> <repo>
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    if not raw:
        return default
    p = Path(raw).expanduser()
    return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """All tunables for the API process."""

    # Source dataset (CSV with artist, song, link, text, genre)
    data_path: Path = field(
        default_factory=lambda: _env_path(
            "HARMONIA_DATA_PATH", PROJECT_ROOT / "data" / "spotify_millsongdata_with_genres.csv"
        )
    )
    # Vectorizer saved by the original notebook; used when compatible.
    notebook_vectorizer_path: Path = field(
        default_factory=lambda: _env_path(
            "HARMONIA_NOTEBOOK_VECTORIZER_PATH",
            PROJECT_ROOT / "data" / "tfidf_vectorizer_contentonly.pkl",
        )
    )
    # Generated artifacts (vectorizer, sparse TF-IDF matrix, song catalogue).
    artifacts_dir: Path = field(
        default_factory=lambda: _env_path("HARMONIA_ARTIFACTS_DIR", PROJECT_ROOT / "artifacts")
    )
    # Build artifacts at startup when they are missing (instead of failing).
    build_on_startup: bool = field(
        default_factory=lambda: _env_bool("HARMONIA_BUILD_ON_STARTUP", True)
    )
    # Browser origins allowed to call the API (comma-separated in env).
    cors_origins: list[str] = field(
        default_factory=lambda: _env_list(
            "HARMONIA_CORS_ORIGINS", ["http://localhost:3000", "http://127.0.0.1:3000"]
        )
    )
    # Top-N bounds mirror the notebook slider (3..20).
    min_top_n: int = 3
    max_top_n: int = 20
    default_top_n: int = 10
    # Hard cap for /songs/search result pages.
    max_search_limit: int = 50
    # TF-IDF hyper-parameters from the notebook; used when rebuilding.
    tfidf_max_features: int = 5000
    tfidf_stop_words: str = "english"


def get_settings() -> Settings:
    return Settings()
