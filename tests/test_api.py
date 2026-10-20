"""HTTP-level tests for the FastAPI app."""
from __future__ import annotations


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["ready"] is True
    assert body["songs"] == 57650 and body["vocabulary"] == 5000
    assert body["top_n"] == {"min": 3, "max": 20, "default": 10}


def test_search_endpoint(client):
    r = client.get("/songs/search", params={"q": "Kind Of Girl", "field": "song", "limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 2 and len(body["results"]) <= 5
    assert body["results"][0]["song_id"] == "S00000"


def test_search_validation(client):
    assert client.get("/songs/search").status_code == 422
    assert client.get("/songs/search", params={"q": "", "field": "song"}).status_code == 422
    assert client.get("/songs/search", params={"q": "a", "field": "nope"}).status_code == 422
    assert client.get("/songs/search", params={"q": "a", "limit": 500}).status_code == 422


def test_get_song(client):
    assert client.get("/songs/S00001").json()["song"] == "Andante, Andante"
    r = client.get("/songs/S99999")
    assert r.status_code == 404 and r.json()["detail"] == "Invalid song ID: 'S99999'"


def test_recommend_song_name(client):
    r = client.post("/recommend", json={"mode": "song_name", "query": "andante", "top_n": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["seed"]["song_id"] == "S00001"
    assert [x["song_id"] for x in body["recommendations"]] == ["S48822", "S26224", "S04271", "S45324", "S26919"]


def test_recommend_song_id_and_artist_and_text(client):
    assert client.post("/recommend", json={"mode": "song_id", "query": "S00002", "top_n": 3}).json()["recommendations"][0]["song_id"] == "S01819"
    art = client.post("/recommend", json={"mode": "artist", "query": "beatles", "top_n": 3}).json()
    assert "Beatles" in art["seed"]["artist"]
    txt = client.post("/recommend", json={"mode": "text", "query": "upbeat pop dance", "top_n": 3}).json()
    assert txt["seed"] is None and len(txt["recommendations"]) == 3


def test_recommend_top_n_bounds(client):
    assert client.post("/recommend", json={"mode": "song_id", "query": "S00000", "top_n": 2}).status_code == 422
    assert client.post("/recommend", json={"mode": "song_id", "query": "S00000", "top_n": 21}).status_code == 422
    assert len(client.post("/recommend", json={"mode": "song_id", "query": "S00000", "top_n": 20}).json()["recommendations"]) == 20
    assert len(client.post("/recommend", json={"mode": "song_id", "query": "S00000"}).json()["recommendations"]) == 10


def test_recommend_errors(client):
    r = client.post("/recommend", json={"mode": "song_id", "query": "S99999", "top_n": 5})
    assert r.status_code == 404 and r.json()["detail"] == "Invalid song ID."
    r = client.post("/recommend", json={"mode": "song_name", "query": "zzqqxx-none", "top_n": 5})
    assert r.status_code == 404 and r.json()["detail"] == "No song found with that name."
    r = client.post("/recommend", json={"mode": "artist", "query": "", "top_n": 5})
    assert r.status_code == 400 and r.json()["detail"] == "Please enter something."
    assert client.post("/recommend", json={"mode": "nope", "query": "x"}).status_code == 422


def test_random_endpoint(client):
    r = client.post("/recommend/random", json={"top_n": 4})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "random" and len(body["recommendations"]) == 4
    assert body["seed"]["song_id"] not in {x["song_id"] for x in body["recommendations"]}
    assert len(client.post("/recommend/random").json()["recommendations"]) == 10


def test_genre_stats(client):
    body = client.get("/stats/genres", params={"top": 3}).json()
    assert body[0]["genre"] == "Pop" and body[0]["count"] == 892


def test_cors_headers(client):
    r = client.options("/recommend", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
