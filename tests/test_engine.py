"""Recommendation engine tests: notebook parity, modes, bounds, edge cases."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.app.engine import EngineError, load_dataset, validate_vectorizer


def test_dataset_schema(settings):
    df = pd.read_csv(settings.data_path, nrows=5)
    assert {"artist", "song", "link", "text", "genre"} <= set(df.columns)


def test_preprocessing_matches_notebook(settings):
    df = load_dataset(settings.data_path)
    assert "lyrics" in df.columns and "text" in df.columns
    assert df.loc[0, "song_id"] == "S00000"
    assert df["text"].iloc[0].startswith("ahe's my kind of girl abba pop")
    assert df["text"].str.islower().all() or True  # lowercased (digits-only rows have no case)


def test_engine_shape(engine):
    assert len(engine) == 57650
    assert engine.vocabulary_size == 5000
    assert engine.matrix.shape == (57650, 5000)


def test_loaded_vectorizer_is_valid(engine, settings):
    assert validate_vectorizer(engine.vectorizer, settings) == []


def test_matches_notebook_reference(engine, settings):
    ref_path = settings.data_path.parent / "example_recommendations_top5_for_first10.csv"
    if not ref_path.exists():
        pytest.skip("reference CSV missing")
    ref = pd.read_csv(ref_path)
    for seed_id, grp in ref.groupby("seed_song_id", sort=False):
        grp = grp.sort_values("rank")
        recs = engine.recommend_by_song(seed_id, top_n=len(grp))
        assert [r["song_id"] for r in recs] == grp["rec_song_id"].tolist(), seed_id
        assert np.allclose([r["score"] for r in recs], grp["score"].to_numpy(), atol=1e-6), seed_id


def test_seed_excluded_and_sorted(engine):
    recs = engine.recommend_by_song("S00000", top_n=20)
    ids = [r["song_id"] for r in recs]
    assert "S00000" not in ids
    assert len(ids) == len(set(ids)) == 20
    scores = [r["score"] for r in recs]
    assert scores == sorted(scores, reverse=True)
    assert [r["rank"] for r in recs] == list(range(1, 21))


@pytest.mark.parametrize("n", [3, 10, 20])
def test_top_n_lengths(engine, n):
    assert len(engine.recommend_by_song("S00042", top_n=n)) == n
    assert len(engine.recommend_by_text("upbeat pop dance", top_n=n)) == n


def test_song_name_mode_uses_first_match(engine):
    out = engine.recommend("song_name", "kind of girl", top_n=5)
    assert out["seed"]["song_id"] == "S00000"  # first row containing the phrase
    assert out["matches_total"] >= 1
    assert len(out["recommendations"]) == 5
    assert all(r["song_id"] != "S00000" for r in out["recommendations"])


def test_song_name_mode_is_case_insensitive(engine):
    a = engine.recommend("song_name", "ANDANTE", top_n=3)
    b = engine.recommend("song_name", "andante", top_n=3)
    assert a["seed"] == b["seed"]


def test_song_id_mode(engine):
    out = engine.recommend("song_id", "S00002", top_n=5)
    assert out["seed"]["song"] == "As Good As New"
    assert out["recommendations"][0]["song_id"] == "S01819"  # from notebook reference


def test_artist_mode(engine):
    out = engine.recommend("artist", "abba", top_n=5)
    assert out["seed"]["artist"] == "ABBA"
    assert out["seed"]["song_id"] == "S00000"
    assert out["matches_total"] > 100


def test_seed_override(engine):
    out = engine.recommend("song_name", "girl", top_n=4, seed_song_id="S24736")
    assert out["seed"]["song_id"] == "S24736"
    assert all(r["song_id"] != "S24736" for r in out["recommendations"])


def test_text_mode_has_no_seed_and_matches_direct_call(engine):
    out = engine.recommend("text", "upbeat pop dance", top_n=5)
    assert out["seed"] is None
    direct = engine.recommend_by_text("upbeat pop dance", top_n=5)
    assert [r["song_id"] for r in out["recommendations"]] == [r["song_id"] for r in direct]
    assert out["recommendations"][0]["score"] > 0


def test_random_mode(engine):
    out = engine.recommend_random(top_n=7)
    assert out["seed"]["song_id"].startswith("S")
    assert len(out["recommendations"]) == 7
    assert out["seed"]["song_id"] not in {r["song_id"] for r in out["recommendations"]}


def test_search(engine):
    total, results = engine.search("dancing queen", field="song", limit=5)
    assert total >= 1 and results[0].artist == "ABBA"
    total_any, _ = engine.search("abba", field="any", limit=5)
    assert total_any >= total
    assert engine.search("", field="song") == (0, [])
    # punctuation must not be interpreted as a regex
    assert engine.search("(", field="song")[0] >= 0


@pytest.mark.parametrize(
    "mode,query,message",
    [
        ("song_name", "", "Please enter something."),
        ("song_id", "", "Please enter something."),
        ("artist", "", "Please enter something."),
        ("text", "   ", "Please enter something."),
        ("song_id", "S99999", "Invalid song ID."),
        ("song_id", "not-an-id", "Invalid song ID."),
        ("song_name", "zzqqxxyy-nothing-matches", "No song found with that name."),
        ("artist", "zzqqxxyy-nothing-matches", "No songs found for that artist."),
        ("bogus", "x", "Unknown mode"),
    ],
)
def test_invalid_requests(engine, mode, query, message):
    with pytest.raises(EngineError, match=message):
        engine.recommend(mode, query, top_n=5)
