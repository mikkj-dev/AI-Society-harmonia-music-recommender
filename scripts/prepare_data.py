#!/usr/bin/env python3
"""Prepare Harmonia model artifacts from the raw dataset.

Produces, in the artifacts directory (default: <repo>/artifacts):
    tfidf_vectorizer.pkl   fitted TfidfVectorizer (5000 features, english stop words)
    tfidf_matrix.npz       sparse TF-IDF matrix (rows = songs)
    songs.csv              catalogue without lyrics (song_id, song, artist, genre, link)
    manifest.json          provenance (row/feature counts, vectorizer source, timestamp)

Usage (from the repository root):
    python scripts/prepare_data.py            # use notebook vectorizer if compatible
    python scripts/prepare_data.py --refit    # always refit from scratch
    python scripts/prepare_data.py --verify   # also check against the notebook's reference CSV
Environment variables HARMONIA_DATA_PATH / HARMONIA_ARTIFACTS_DIR override locations.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings  # noqa: E402
from backend.app.engine import RecommendationEngine, build_artifacts, save_artifacts  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("prepare_data")


def verify(engine: RecommendationEngine, reference_csv: Path) -> bool:
    ref = pd.read_csv(reference_csv)
    ok = True
    for seed_id, grp in ref.groupby("seed_song_id", sort=False):
        grp = grp.sort_values("rank")
        recs = engine.recommend_by_song(seed_id, top_n=len(grp))
        got_ids = [r["song_id"] for r in recs]
        got_scores = np.array([r["score"] for r in recs])
        exp_ids = grp["rec_song_id"].tolist()
        exp_scores = grp["score"].to_numpy()
        if got_ids != exp_ids or not np.allclose(got_scores, exp_scores, atol=1e-6):
            ok = False
            log.error("Mismatch for %s: expected %s got %s", seed_id, exp_ids, got_ids)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refit", action="store_true", help="ignore the notebook vectorizer and refit TF-IDF")
    ap.add_argument("--verify", action="store_true", help="compare results against the reference CSV")
    ap.add_argument("--reference", type=Path, default=ROOT / "data" / "example_recommendations_top5_for_first10.csv")
    args = ap.parse_args()

    settings = get_settings()
    log.info("Dataset:   %s", settings.data_path)
    log.info("Artifacts: %s", settings.artifacts_dir)

    artifacts = build_artifacts(settings, prefer_notebook_vectorizer=not args.refit)
    save_artifacts(artifacts, settings.artifacts_dir)
    engine = RecommendationEngine(artifacts, settings)
    log.info("Engine ready: %d songs, %d features", len(engine), engine.vocabulary_size)

    if args.verify:
        if not args.reference.exists():
            log.error("Reference CSV not found: %s", args.reference)
            return 2
        if verify(engine, args.reference):
            log.info("Verification passed: results match the notebook reference exactly.")
        else:
            log.error("Verification FAILED.")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
