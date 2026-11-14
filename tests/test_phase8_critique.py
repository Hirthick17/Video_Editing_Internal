"""Test Phase 8: Multi-branch quality critique and targeted correction loops."""

from pathlib import Path
from app.integrations.chatcut.mcp_adapter import ChatCutMCPAdapter
from app.services.assembly_service import AssemblyService
from app.services.critique_service import CritiqueService
from app.services.edit_planner_service import EditPlannerService
from app.services.media_understanding_service import MediaUnderstandingService
from app.services.project_scanner import ProjectScannerService
from app.services.script_service import ScriptService
from app.services.shot_planner_service import ShotPlannerService
from app.state.editor_contracts import ClipSpec, EditOperation
from app.state.enums import EditOperationType


def test_comprehensive_critique_scorecard_passing(tmp_path: Path):
    """Verify all 7 quality dimensions pass with an overall score >= 9.0 and zero blocking issues."""
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

    assembly_res = assembly_svc.assemble_short_13(
        project_id=project_id,
        timeline_id=timeline_id,
        edit_plan=edit_plan,
        operations=operations,
    )
    post_tl = adapter.get_timeline(timeline_id)

    scorecard = CritiqueService.run_comprehensive_critique(
        job_id="job_short13_critique_test",
        script=script,
        shot_plan=shot_plan,
        edit_plan=edit_plan,
        transcript=transcript,
        operations=operations,
        asset_registry=project.asset_registry,
        post_timeline=post_tl,
    )

    assert scorecard.passed_quality_gate is True
    assert scorecard.overall_score >= 9.0
    assert scorecard.blocking_issues_count == 0
    assert len(scorecard.aspect_evaluations) == 7
    assert all(ev.passed for ev in scorecard.aspect_evaluations.values())


def test_critique_catches_audio_masking():
    """Verify critique detects audio masking if music volume exceeds acceptable ducking threshold."""
    bad_music_clip = ClipSpec(
        item_id="item_loud_bgm",
        track_id="track_a2_bgm",
        asset_id="ast_bg_music_01",
        start_frame=0,
        end_frame=900,
        source_in_frame=0,
        source_out_frame=900,
        volume=0.8,  # Loud music masks dialogue!
        name="Loud BGM",
    )
    bad_op = EditOperation(
        operation_id="op_loud_bgm",
        operation_type=EditOperationType.INSERT_CLIP,
        idempotency_key="idemp_loud",
        track_id="track_a2_bgm",
        clip_spec=bad_music_clip,
    )

    critique = CritiqueService.evaluate_audio_quality([bad_op])
    assert critique.passed is False
    assert any("masking" in i.message.lower() for i in critique.issues)

