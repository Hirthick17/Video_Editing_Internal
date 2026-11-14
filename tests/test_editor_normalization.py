"""Test Phase 2: Editor state normalization from raw ChatCut MCP dictionaries."""

from app.state.editor_models import (
    EditorItem,
    EditorProject,
    EditorTimeline,
    EditorTrack,
    normalize_chatcut_project,
    normalize_chatcut_timeline,
)


def test_normalize_chatcut_project():
    """Verify raw target_project dict normalizes into validated EditorProject."""
    raw = {
        "projectId": "8a894b86-d5e0-4222-ab88-df22a8e2168e",
        "name": "Short 13 - TellOS PG Rent Book",
        "activeTimelineId": "03501b27-ebf5-4aae-9eb6-6e7df21e0378",
        "timelineIds": ["03501b27-ebf5-4aae-9eb6-6e7df21e0378"],
        "editorVersion": "0.9.12.0",
        "projectPath": "C:/Users/hirth/AppData/Roaming/ChatCut/projects/8a894b86",
    }
    proj = normalize_chatcut_project(raw)
    assert proj.project_id == "8a894b86-d5e0-4222-ab88-df22a8e2168e"
    assert proj.name == "Short 13 - TellOS PG Rent Book"
    assert proj.active_timeline_id == "03501b27-ebf5-4aae-9eb6-6e7df21e0378"
    assert proj.editor_version == "0.9.12.0"


def test_normalize_chatcut_timeline():
    """Verify raw preview_timeline dict normalizes into validated EditorTimeline."""
    raw = {
        "timelineId": "tl_001",
        "projectId": "proj_001",
        "width": 1080,
        "height": 1920,
        "fps": {"num": 30, "den": 1},
        "durationFrames": 900,
        "tracks": [
            {
                "trackId": "V1",
                "name": "Main Demo",
                "type": "video",
                "items": [
                    {
                        "itemId": "clip_v1_1",
                        "assetId": "ast_demo",
                        "startFrame": 0,
                        "endFrame": 900,
                        "name": "demo-recording-1.mp4",
                        "volume": 1.0,
                    }
                ],
            },
            {
                "trackId": "V2",
                "name": "B-roll Stock",
                "type": "video",
                "items": [
                    {
                        "itemId": "clip_v2_1",
                        "assetId": "ast_stock",
                        "startFrame": 0,
                        "endFrame": 150,
                        "name": "broll-spreadsheet.mp4",
                        "volume": 0.8,
                    }
                ],
            },
        ],
    }

    tl = normalize_chatcut_timeline(raw)
    assert tl.timeline_id == "tl_001"
    assert tl.width == 1080
    assert tl.height == 1920
    assert tl.fps == 30.0
    assert tl.duration_frames == 900
    assert len(tl.tracks) == 2

    # Check tracks and clips
    v1 = tl.tracks[0]
    assert v1.track_id == "V1"
    assert len(v1.items) == 1
    assert v1.items[0].timeline_start_frame == 0
    assert v1.items[0].timeline_end_frame == 900
    assert v1.items[0].duration_frames == 900

    v2 = tl.tracks[1]
    assert v2.track_id == "V2"
    assert v2.items[0].duration_frames == 150

    # Revision hash must be non-empty and deterministic
    assert len(tl.revision_hash) > 0
    h1 = tl.compute_revision_hash()
    h2 = tl.compute_revision_hash()
    assert h1 == h2

