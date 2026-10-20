"""Shared fixtures: one engine for the whole test session (built from artifacts)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings  # noqa: E402
from backend.app.engine import RecommendationEngine  # noqa: E402
from backend.app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="session")
def engine(settings) -> RecommendationEngine:
    if not settings.data_path.exists():
        pytest.skip(f"dataset not found at {settings.data_path}")
    return RecommendationEngine.from_settings(settings, allow_build=True)


@pytest.fixture(scope="session")
def client(engine, settings) -> TestClient:
    app = create_app(settings, engine=engine)
    with TestClient(app) as c:
        yield c
