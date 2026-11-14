"""Test 11: Future ChatCut contracts, half-open frame math, and adapter stubs."""

from app.integrations.chatcut.adapter_interface import StubChatCutAdapter
from app.services.time_codes import (
    frames_to_seconds,
    intervals_overlap,
    seconds_to_frames,
    validate_interval,
)
from app.state.editor_contracts import ClipSpec, EditOperation, TimelineSpec, TrackSpec
from app.state.enums import EditOperationType


def test_half_open_frame_math():
    """Verify half-open interval math [start, end) where duration = end - start."""
    duration = validate_interval(0, 90)
    assert duration == 90

    # Overlaps
    assert intervals_overlap((0, 100), (50, 150)) is True
    assert intervals_overlap((0, 100), (100, 200)) is False  # Adjacent intervals do NOT overlap
    assert intervals_overlap((100, 200), (0, 100)) is False
    assert intervals_overlap((0, 50), (100, 150)) is False


def test_timecode_conversions():
    """Verify frame to second conversions at 30 FPS."""
    assert frames_to_seconds(900, fps=30) == 30.0
    assert frames_to_seconds(45, fps=30) == 1.5
    assert seconds_to_frames(30.0, fps=30) == 900
    assert seconds_to_frames(1.5, fps=30) == 45


def test_timeline_spec_shorts_format():
    """Verify standard YouTube Shorts profile (1080x1920 @ 30 FPS)."""
    spec = TimelineSpec(width=1080, height=1920, fps=30)
    assert spec.width == 1080
    assert spec.height == 1920
    assert spec.fps == 30


def test_clip_spec_duration():
    """Verify ClipSpec duration property matches half-open frame interval."""
    clip = ClipSpec(
        item_id="clip_01",
        track_id="V1",
        asset_id="ast_tellos",
        start_frame=30,
        end_frame=150,
    )
    assert clip.duration_frames == 120


def test_stub_chatcut_adapter():
    """Verify StubChatCutAdapter contract compliance for Phase 1 without external side effects."""
    adapter = StubChatCutAdapter(connected=True)
    assert adapter.is_connected() is True

    proj = adapter.get_project("proj_test")
    assert proj["project_id"] == "proj_test"

    timeline = adapter.get_timeline("tl_test")
    assert timeline["width"] == 1080
    assert timeline["height"] == 1920
    assert timeline["fps"] == 30

    op = EditOperation(
        operation_id="op_1",
        operation_type=EditOperationType.INSERT_CLIP,
        idempotency_key="idemp_1",
    )
    results = adapter.apply_batch_operations("tl_test", [op])
    assert len(results) == 1
    assert results[0]["status"] == "SUCCESS"
    assert op.applied is True

    dup = adapter.duplicate_project("proj_test", "proj_test_backup")
    assert dup["status"] == "DUPLICATED"

