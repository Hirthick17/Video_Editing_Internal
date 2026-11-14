"""Test Phase 7: ChatCut timeline assembly, state synchronization, and verification."""

from pathlib import Path
from app.integrations.chatcut.mcp_adapter import ChatCutMCPAdapter
from app.services.assembly_service import AssemblyService
from app.services.edit_planner_service import EditPlannerService
from app.services.media_understanding_service import MediaUnderstandingService
from app.services.project_scanner import ProjectScannerService
from app.services.script_service import ScriptService
from app.services.shot_planner_service import ShotPlannerService


def test_short_13_timeline_assembly_and_sync(tmp_path: Path):
    """Verify safe 6-step timeline assembly applies all 15 operations and verifies layout."""
    demo_file = tmp_path / "tellos_demo.mp4"
    demo_file.write_bytes(b"\x00" * 1024)
    broll_file = tmp_path / "broll-spreadsheet.mp4"
    broll_file.write_bytes(b"\x00" * 1024)

    project = ProjectScannerService.scan_short_13_project(
        base_dir=tmp_path,
        external_demo_path=demo_file,
    )
    script = ScriptService.create_short_13_script()
    shot_plan = ShotPlannerService.create_short_13_shot_plan(project)
    transcript = MediaUnderstandingService.generate_word_timed_transcript(script)

    segments = []
    segments.extend(MediaUnderstandingService.detect_usable_segments(demo_file, "ast_demo_recording_01"))
    segments.extend(MediaUnderstandingService.detect_usable_segments(broll_file, "ast_broll_spreadsheet_01"))

    match_report = MediaUnderstandingService.match_clips_to_shots(
        shot_plan, segments, project.asset_registry
    )

    edit_plan, operations = EditPlannerService.create_short_13_edit_plan(
        project, shot_plan, transcript, match_report
    )

    adapter = ChatCutMCPAdapter(mode="simulated")
    assembly_svc = AssemblyService(adapter=adapter)

    project_id = "8a894b86-d5e0-4222-ab88-df22a8e2168e"
    timeline_id = "03501b27-ebf5-4aae-9eb6-6e7df21e0378"

    res = assembly_svc.assemble_short_13(
        project_id=project_id,
        timeline_id=timeline_id,
        edit_plan=edit_plan,
        operations=operations,
    )

    assert res.success is True
    assert res.project_id == project_id
    assert res.timeline_id == timeline_id
    assert res.applied_operations_count == 15
    assert res.total_tracks_observed >= 5
    assert res.total_clips_observed == 6  # 4 video + 2 audio
    assert res.total_captions_observed == 4  # 4 native captions
    assert res.duration_frames_observed == 900
    assert res.quarantined_svgs_count == 0
    assert res.rollback_snapshot_id is not None
    assert res.pre_edit_revision != res.post_edit_revision

