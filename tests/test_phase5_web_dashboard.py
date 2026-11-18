"""
Phase 5 & 6 Test Suite: Web Dashboard API, Content Manager, and Channel Monitor.

Verifies:
1. GET /api/pattern-a/spec returns approved v1.0.0 specification with zero unverified fields.
2. GET /api/pattern-a/pilot-report returns the verified Pilot Handoff Report.
3. GET /api/pattern-a/audio-library returns catalog of >=40 SFX cues and >=10 music tracks.
4. GET /api/pattern-a/stock-candidates returns candidate B-rolls with CANDIDATES_ONLY hard prohibition.
5. POST /api/pattern-a/polish/start and complete measure owner polish time against the 30-min target.
6. GET /api/content-manager/schedule returns 2-Shorts/week calendar (8 slots/month) for Hirthick's Vision.
7. GET /api/channel-monitor/stats enforces strict READ_ONLY mode.
8. GET / returns HTML dashboard with 200 OK.
"""

import pytest
from fastapi.testclient import TestClient

from app.web.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_pattern_a_spec(client: TestClient):
    resp = client.get("/api/pattern-a/spec")
    assert resp.status_code == 200
    data = resp.json()
    assert data["production_ready"] is True
    assert len(data["unverified_fields"]) == 0
    assert data["colors"]["base"] == "#FFFFFF"
    assert data["colors"]["accent"] == "#9333EA"
    assert data["typography"]["font"] == "Inter"


def test_get_pilot_report(client: TestClient):
    resp = client.get("/api/pattern-a/pilot-report")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "DONE"
    assert data["measured_polish_minutes"] <= 30.0
    assert data["target_achieved"] is True
    assert data["total_cuts"] >= 4
    assert data["total_captions"] >= 10


def test_get_audio_library(client: TestClient):
    resp = client.get("/api/pattern-a/audio-library")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sfx_count"] >= 40
    assert data["music_count"] >= 10
    assert len(data["sfx_cues"]) >= 40
    assert len(data["music_tracks"]) >= 10


def test_get_stock_candidates(client: TestClient):
    resp = client.get("/api/pattern-a/stock-candidates")
    assert resp.status_code == 200
    data = resp.json()
    assert data["placement_mode"] == "CANDIDATES_ONLY"
    assert len(data["candidates"]) >= 2
    for c in data["candidates"]:
        assert c["width"] == 1080
        assert c["height"] == 1920


def test_polish_session_lifecycle(client: TestClient):
    # Start polish
    start_resp = client.post("/api/pattern-a/polish/start", json={"job_id": "test_job_polish"})
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "OWNER_EDITING"

    # Complete polish
    complete_resp = client.post("/api/pattern-a/polish/complete", json={"job_id": "test_job_polish", "polish_minutes": 22.0})
    assert complete_resp.status_code == 200
    data = complete_resp.json()
    assert data["status"] == "DONE"
    assert data["measured_polish_minutes"] == 22.0
    assert data["target_achieved"] is True
    assert data["time_saved_minutes"] >= 360.0


def test_content_manager_schedule(client: TestClient):
    resp = client.get("/api/content-manager/schedule")
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel"] == "Hirthick's Vision"
    assert "2 Shorts" in data["cadence"]
    assert len(data["monthly_slots"]) == 8
    assert "Build In Public" in data["pillars"]
    assert "Software & Architecture" in data["pillars"]


def test_channel_monitor_stats(client: TestClient):
    resp = client.get("/api/channel-monitor/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_mode"] == "READ_ONLY"
    assert "strictly forbidden" in data["hard_prohibition"]
    assert data["kpis"]["average_retention_pct"] > 70.0


def test_index_page_loads(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Hirthick's Vision Studio" in resp.text
