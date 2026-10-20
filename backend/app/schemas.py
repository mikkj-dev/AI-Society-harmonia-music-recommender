"""Request and response models for the Harmonia API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .config import get_settings

_s = get_settings()

Mode = Literal["song_name", "song_id", "artist", "text"]


class SongOut(BaseModel):
    song_id: str
    song: str
    artist: str
    genre: str
    link: str = ""


class RecommendationOut(SongOut):
    score: float = Field(..., description="Cosine similarity to the seed (0..1)")
    rank: int


class RecommendRequest(BaseModel):
    mode: Mode = Field(..., description="song_name | song_id | artist | text")
    query: str = Field("", max_length=2000, description="Song name, song ID, artist name or free text")
    top_n: int = Field(_s.default_top_n, ge=_s.min_top_n, le=_s.max_top_n)
    seed_song_id: str | None = Field(
        None,
        max_length=16,
        description="Optional: use this exact song as the seed instead of the first search match",
    )

    @field_validator("query")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class RandomRequest(BaseModel):
    top_n: int = Field(_s.default_top_n, ge=_s.min_top_n, le=_s.max_top_n)


class RecommendResponse(BaseModel):
    mode: str
    query: str
    seed: SongOut | None
    matches_total: int | None = Field(
        None, description="How many catalogue rows matched the search (song_name/artist modes)"
    )
    recommendations: list[RecommendationOut]


class SearchResponse(BaseModel):
    query: str
    field: Literal["song", "artist", "any"]
    total: int
    results: list[SongOut]


class GenreCount(BaseModel):
    genre: str
    count: int


class HealthResponse(BaseModel):
    status: Literal["ok", "loading", "error"]
    ready: bool
    songs: int | None = None
    vocabulary: int | None = None
    vectorizer_source: str | None = None
    artifacts_built_at: str | None = None
    top_n: dict[str, int]
    detail: str | None = None


class ErrorResponse(BaseModel):
    detail: str
