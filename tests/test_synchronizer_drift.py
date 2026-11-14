"""Test 12: Editor state reconciliation, drift detection, and prohibited item alerting."""

from app.integrations.chatcut.synchronizer import EditorStateSynchronizer
from app.state.editor_contracts import ClipSpec


def test_perfectly_synchronized_timeline():
    """Verify clean reconciliation when actual timeline matches expected clips."""
    expected = [
        ClipSpec(item_id="clip_1", track_id="V1", asset_id="ast_demo", start_frame=0, end_frame=300),
        ClipSpec(item_id="clip_2", track_id="A1", asset_id="ast_vo", start_frame=0, end_frame=300),
    ]
    actual_timeline = {
        "tracks": [
            {
                "track_id": "V1",
                "items": [{"item_id": "clip_1", "start_frame": 0, "end_frame": 300, "name": "demo.mp4"}],
            },
            {
                "track_id": "A1",
                "items": [{"item_id": "clip_2", "start_frame": 0, "end_frame": 300, "name": "vo.mp3"}],
            },
        ]
    }

    report = EditorStateSynchronizer.reconcile(expected, actual_timeline)
    assert report.synced is True
    assert report.matched_clips == 2
    assert report.drift_count == 0
    assert len(report.missing_assets) == 0
    assert len(report.prohibited_items) == 0


def test_timeline_drift_and_missing_assets():
    """Verify detection when actual clip positions differ from expected."""
    expected = [
        ClipSpec(item_id="clip_1", track_id="V1", asset_id="ast_demo", start_frame=0, end_frame=300),
        ClipSpec(item_id="clip_2", track_id="V1", asset_id="ast_broll", start_frame=300, end_frame=600),
    ]
    actual_timeline = {
        "tracks": [
            {
                "track_id": "V1",
                # clip_1 start shifted to 15, clip_2 missing entirely
                "items": [{"item_id": "clip_1", "start_frame": 15, "end_frame": 300, "name": "demo.mp4"}],
            }
        ]
    }

    report = EditorStateSynchronizer.reconcile(expected, actual_timeline)
    assert report.synced is False
    assert report.drift_count == 1
    assert "ast_broll" in report.missing_assets


def test_prohibited_svg_detection_on_timeline():
    """Verify that any SVG or synthetic card found on the timeline flags a synchronization alert."""
    expected = []
    actual_timeline = {
        "tracks": [
            {
                "track_id": "V3",
                "items": [
                    {
                        "item_id": "item_svg_hook",
                        "start_frame": 0,
                        "end_frame": 90,
                        "name": "card1_hook.svg",
                    }
                ],
            }
        ]
    }

    report = EditorStateSynchronizer.reconcile(expected, actual_timeline)
    assert report.synced is False
    assert len(report.prohibited_items) == 1
    assert "card1_hook.svg" in report.prohibited_items[0]

