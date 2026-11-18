"""
Phase 3 Test Suite: Licensed SFX & Music Library + Stock B-Roll Candidate Sourcing.

Verifies:
1. Licensed SFX catalog contains >= 40 cues across all required categories (HOOK_HIT, EMPHASIS, SWOOSH, DING, etc.).
2. Music catalog contains >= 10 licensed tracks with complete metadata (BPM, mood, ducking parameters).
3. AudioLibraryService assigns SFX and music cues to planned timeline events with target ducking (-18dB).
4. StockSourcingService extracts keywords matching tech/build-in-public content pillars.
5. Stock B-roll candidate naming strictly follows VID<job>_S<slot>_C<idx>_<provider>_<id>.
6. Stock B-roll candidates are pushed into ChatCut Project Assets bin (CANDIDATES_ONLY) and not placed on timeline.
"""

import pytest
from app.integrations.chatcut.mcp_adapter import ChatCutMCPAdapter
from app.services.audio_library import AudioCategory, AudioLibraryService
from app.services.stock_sourcing import StockSourcingService


def test_sfx_catalog_completeness():
    """Verify SFX catalog has at least 40 cues with complete metadata across categories."""
    service = AudioLibraryService()
    assert service.get_sfx_catalog_size() >= 40

    # Verify every category has cues
    required_categories = [
        AudioCategory.HOOK_HIT,
        AudioCategory.EMPHASIS,
        AudioCategory.SWOOSH,
        AudioCategory.POP,
        AudioCategory.RISER,
        AudioCategory.DING,
        AudioCategory.NOTIFICATION,
        AudioCategory.GLITCH,
        AudioCategory.TRANSITION,
    ]
    for cat in required_categories:
        cues = service.find_sfx_by_event(cat, limit=10)
        assert len(cues) >= 3, f"Category '{cat.value}' has insufficient cues"

        for cue in cues:
            assert cue.cue_id is not None
            assert cue.provider in ("Pixabay", "Pexels")
            assert cue.license_type != ""
            assert cue.license_url != ""
            assert cue.duration_seconds > 0.0
            assert cue.sha256 != ""


def test_music_catalog_completeness():
    """Verify Music catalog has at least 10 tracks with BPM, mood tags, and ducking parameters."""
    service = AudioLibraryService()
    assert service.get_music_catalog_size() >= 10

    track = service.find_music_by_mood("lofi")
    assert track is not None
    assert track.bpm is not None and track.bpm > 0
    assert track.ducking_db <= -16.0  # Ducking at -16dB to -20dB under voiceover
    assert "study" in track.tags or "chill" in track.tags or "lofi" in track.tags


def test_audio_assignment_to_edit_plan():
    """Verify deterministic assignment of SFX cues and music bed to timeline events."""
    service = AudioLibraryService()
    events = [
        {"event_type": "HOOK_HIT", "frame": 0},
        {"event_type": "EMPHASIS", "frame": 45},
        {"event_type": "SWOOSH", "frame": 90},
        {"event_type": "EMPHASIS", "frame": 135},
        {"event_type": "DING", "frame": 240},
    ]

    assigned = service.assign_cues_to_edit_plan(events, mood="buildinpublic")
    assert len(assigned["sfx"]) == 5
    assert len(assigned["music"]) == 1

    assert assigned["sfx"][0]["category"] == "HOOK_HIT"
    assert assigned["sfx"][1]["category"] == "EMPHASIS"
    assert assigned["sfx"][2]["category"] == "SWOOSH"
    assert assigned["music"][0]["ducking_db"] <= -18.0


def test_stock_keyword_extraction():
    """Verify keyword extraction from script text targeting tech pillars."""
    service = StockSourcingService()
    script_text = (
        "In this video we are building an autonomous robotics agent using software "
        "and artificial intelligence in public for our startup."
    )
    keywords = service.extract_keywords_from_script(script_text)
    assert len(keywords) > 0
    assert any(k in ["robotics", "software", "artificial", "intelligence", "building", "startup"] for k in keywords)


def test_stock_candidate_sourcing_and_naming():
    """Verify candidate search and strict naming VID<job>_S<slot>_C<idx>_<provider>_<id>."""
    service = StockSourcingService()
    candidates = service.search_candidates_for_slot(
        job_id="job_p3_01",
        slot_id="slot_01",
        keywords=["ai", "robotics"],
        max_candidates=3,
    )

    assert len(candidates) == 3
    for idx, cand in enumerate(candidates):
        expected_prefix = f"VIDjobp301_Sslot01_C{idx + 1}_"
        assert cand.candidate_id.startswith(expected_prefix)
        assert cand.width == 1080
        assert cand.height == 1920
        assert cand.license_type != ""
        assert cand.sha256 != ""


def test_stock_candidate_ingest_to_chatcut_bin():
    """Verify candidates are pushed to ChatCut project bin (push_asset) without placing on timeline."""
    service = StockSourcingService()
    adapter = ChatCutMCPAdapter(mode="simulated")
    adapter._execute_simulated_tool("create_project", {"projectId": "proj_stock_test", "name": "Stock Test"})

    candidates = service.search_candidates_for_slot(
        job_id="job_bin_01",
        slot_id="s01",
        keywords=["code", "software"],
        max_candidates=2,
    )

    ingested = service.ingest_candidates_to_chatcut_bin(
        candidates=candidates,
        adapter=adapter,
        project_id="proj_stock_test",
    )

    assert len(ingested) == 2
    for c in ingested:
        assert c.pushed_to_chatcut is True
        assert c.chatcut_asset_id is not None

    # Verify timeline remains completely untouched (zero items on V2)
    tl = adapter.get_timeline("tl_proj_stock_test")
    v2_track = next(t for t in tl.tracks if t.track_id == "V2")
    assert len(v2_track.items) == 0  # CANDIDATES_ONLY in bin!
