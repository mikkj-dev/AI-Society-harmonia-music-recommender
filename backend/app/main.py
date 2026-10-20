"""Harmonia recommendation API (FastAPI).

Run from the repository root:
    uvicorn backend.app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .engine import EngineError, RecommendationEngine
from . import schemas

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("harmonia.api")


class EngineState:
    """Thread-safe holder so /health can report while the model loads."""

    def __init__(self) -> None:
        self.engine: RecommendationEngine | None = None
        self.error: str | None = None
        self._lock = threading.Lock()

    def load(self, settings: Settings) -> None:
        with self._lock:
            if self.engine is not None:
                return
            try:
                self.engine = RecommendationEngine.from_settings(
                    settings, allow_build=settings.build_on_startup
                )
                self.error = None
            except Exception as exc:  # noqa: BLE001
                self.error = str(exc)
                log.exception("Failed to initialise recommendation engine")


def create_app(settings: Settings | None = None, *, engine: RecommendationEngine | None = None) -> FastAPI:
    settings = settings or get_settings()
    state = EngineState()
    if engine is not None:
        state.engine = engine

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if state.engine is None:
            # Load synchronously so the first request is never served by a half-built engine.
            state.load(settings)
        yield

    app = FastAPI(
        title="Harmonia Recommendation API",
        version="1.0.0",
        description="Content-based music recommendations (TF-IDF + cosine similarity).",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.engine_state = state

    def require_engine() -> RecommendationEngine:
        if state.engine is None:
            raise HTTPException(status_code=503, detail=state.error or "Recommendation engine is still loading.")
        return state.engine

    @app.exception_handler(EngineError)
    async def _engine_error(_: Request, exc: EngineError) -> JSONResponse:
        # Invalid IDs / no matches are client errors; mirror the notebook messages.
        return JSONResponse(status_code=404 if "No song" in str(exc) or "Invalid song ID" in str(exc) else 400,
                            content={"detail": str(exc)})

    # ------------------------------------------------------------------ #
    @app.get("/health", response_model=schemas.HealthResponse, tags=["system"])
    def health() -> schemas.HealthResponse:
        bounds = {"min": settings.min_top_n, "max": settings.max_top_n, "default": settings.default_top_n}
        if state.engine is None:
            return schemas.HealthResponse(
                status="error" if state.error else "loading", ready=False, top_n=bounds, detail=state.error
            )
        e = state.engine
        return schemas.HealthResponse(
            status="ok",
            ready=True,
            songs=len(e),
            vocabulary=e.vocabulary_size,
            vectorizer_source=e.manifest.get("vectorizer_source"),
            artifacts_built_at=e.manifest.get("built_at"),
            top_n=bounds,
        )

    @app.get("/songs/search", response_model=schemas.SearchResponse, tags=["songs"])
    def search_songs(
        q: str = Query(..., min_length=1, max_length=200, description="Case-insensitive substring"),
        field: Literal["song", "artist", "any"] = Query("song"),
        limit: int = Query(10, ge=1, le=settings.max_search_limit),
    ) -> schemas.SearchResponse:
        engine = require_engine()
        total, results = engine.search(q, field=field, limit=limit)
        return schemas.SearchResponse(query=q.strip(), field=field, total=total, results=[r.as_dict() for r in results])

    @app.get("/songs/random", response_model=schemas.SongOut, tags=["songs"])
    def random_song() -> schemas.SongOut:
        return schemas.SongOut(**require_engine().random_song().as_dict())

    @app.get("/songs/{song_id}", response_model=schemas.SongOut, tags=["songs"],
             responses={404: {"model": schemas.ErrorResponse}})
    def get_song(song_id: str) -> schemas.SongOut:
        return schemas.SongOut(**require_engine().get_song(song_id).as_dict())

    @app.get("/stats/genres", response_model=list[schemas.GenreCount], tags=["songs"])
    def genre_stats(top: int = Query(10, ge=1, le=50), exclude_unknown: bool = True) -> list[schemas.GenreCount]:
        return [schemas.GenreCount(**g) for g in require_engine().genre_counts(top=top, exclude_unknown=exclude_unknown)]

    @app.post("/recommend", response_model=schemas.RecommendResponse, tags=["recommend"],
              responses={400: {"model": schemas.ErrorResponse}, 404: {"model": schemas.ErrorResponse}})
    def recommend(body: schemas.RecommendRequest) -> schemas.RecommendResponse:
        engine = require_engine()
        result = engine.recommend(body.mode, body.query, body.top_n, seed_song_id=body.seed_song_id)
        return schemas.RecommendResponse(**result)

    @app.post("/recommend/random", response_model=schemas.RecommendResponse, tags=["recommend"])
    def recommend_random(body: schemas.RandomRequest | None = None) -> schemas.RecommendResponse:
        top_n = body.top_n if body else settings.default_top_n
        return schemas.RecommendResponse(**require_engine().recommend_random(top_n))

    return app


app = create_app()
