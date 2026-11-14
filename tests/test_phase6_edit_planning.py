"""Test Phase 6: Edit planning, multi-track timeline specification, cutlist generation, and rough-cut approval."""

import json
from pathlib import Path
from app.approvals.approval_service import ApprovalService
from app.persistence.database import DatabaseManager
from app.persistence.repository import JobRepository
from app.services.edit_planner_service import EditPlannerService
from app.services.media_understanding_service import MediaUnderstandingService
from app.services.project_scanner import ProjectScannerService
from app.services.script_service import ScriptService
from app.services.shot_planner_service import ShotPlannerService
from app.state.editor_contracts import ClipSpec, EditOperation
from app.state.enums import (
    ApprovalStatus,
    AssetType,
    EditOperationType,
    JobStatus,
    ProductionStage,
)
from app.state.models import AssetRecord
from app.state.production_state import ProductionState


def test_create_short_13_edit_plan(tmp_path: Path):
    """Verify edit plan assembly contains 5 tracks, 4 video cuts, 2 audio tracks, and 4 native captions."""
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

    assert edit_plan.target_width == 1080
    assert edit_plan.target_height == 1920
    assert edit_plan.fps == 30
    assert len(edit_plan.tracks) == 5

    # Verify operations breakdown
    track_ops = [op for op in operations if op.operation_type == EditOperationType.ADD_TRACK]
    clip_ops = [op for op in operations if op.operation_type == EditOperationType.INSERT_CLIP]
    caption_ops = [op for op in operations if op.operation_type == EditOperationType.ADD_CAPTION]

    assert len(track_ops) == 5
    assert len(clip_ops) == 6  # 4 video cuts + 1 voiceover + 1 BGM
    assert len(caption_ops) == 4  # 4 native captions

    # Verify audio levels
    vo_op = next(op for op in clip_ops if op.clip_spec.item_id == "item_a1_narration")
    bgm_op = next(op for op in clip_ops if op.clip_spec.item_id == "item_a2_bgm")
    assert vo_op.clip_spec.volume == 1.0  # 0dB
    assert bgm_op.clip_spec.volume == 0.125  # -18dB ducking


def test_validate_edit_plan_contiguity_and_bounds(tmp_path: Path):
    """Verify edit plan validation confirms exact 900 frame duration and 0 discrepancies."""
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

    validation = EditPlannerService.validate_edit_plan(
        edit_plan, operations, project.asset_registry, target_frames=900
    )

    assert validation.is_valid is True
    assert validation.total_duration_frames == 900
    assert validation.guardrail_passed is True
    assert len(validation.discrepancies) == 0


def test_validate_edit_plan_detects_track_overlap(tmp_path: Path):
    """Verify validation detects overlapping clips on the same track."""
    demo_file = tmp_path / "tellos_demo.mp4"
    demo_file.write_bytes(b"\x00" * 1024)

    project = ProjectScannerService.scan_short_13_project(
        base_dir=tmp_path,
        external_demo_path=demo_file,
    )
    script = ScriptService.create_short_13_script()
    shot_plan = ShotPlannerService.create_short_13_shot_plan(project)
    transcript = MediaUnderstandingService.generate_word_timed_transcript(script)

    segments = MediaUnderstandingService.detect_usable_segments(demo_file, "ast_demo_recording_01")
    match_report = MediaUnderstandingService.match_clips_to_shots(
        shot_plan, segments, project.asset_registry
    )

    edit_plan, operations = EditPlannerService.create_short_13_edit_plan(
        project, shot_plan, transcript, match_report
    )

    # Invalidate by inserting an overlapping clip on track_v1_demo
    bad_clip = ClipSpec(
        item_id="item_conflict",
        track_id="track_v1_demo",
        asset_id="ast_demo_recording_01",
        start_frame=200,
        end_frame=400,
        source_in_frame=0,
        source_out_frame=200,
        name="Conflicting Clip",
    )
    operations.append(
        EditOperation(
            operation_id="op_conflict",
            operation_type=EditOperationType.INSERT_CLIP,
            idempotency_key="idemp_conflict",
            track_id="track_v1_demo",
            clip_spec=bad_clip,
        )
    )

    validation = EditPlannerService.validate_edit_plan(
        edit_plan, operations, project.asset_registry, target_frames=900
    )
    assert validation.is_valid is False
    assert any("overlapping" in d.lower() for d in validation.discrepancies)


def test_validate_edit_plan_rejects_svg_guardrail(tmp_path: Path):
    """Verify validation rejects an edit plan containing any SVG card assets."""
    demo_file = tmp_path / "tellos_demo.mp4"
    demo_file.write_bytes(b"\x00" * 1024)

    project = ProjectScannerService.scan_short_13_project(
        base_dir=tmp_path,
        external_demo_path=demo_file,
    )
    script = ScriptService.create_short_13_script()
    shot_plan = ShotPlannerService.create_short_13_shot_plan(project)
    transcript = MediaUnderstandingService.generate_word_timed_transcript(script)

    segments = MediaUnderstandingService.detect_usable_segments(demo_file, "ast_demo_recording_01")
    match_report = MediaUnderstandingService.match_clips_to_shots(
        shot_plan, segments, project.asset_registry
    )

    edit_plan, operations = EditPlannerService.create_short_13_edit_plan(
        project, shot_plan, transcript, match_report
    )

    # Inject SVG card asset into registry and operation
    svg_registry = dict(project.asset_registry)
    svg_registry["ast_bad_svg"] = AssetRecord(
        asset_id="ast_bad_svg",
        path="shorts-assets/card1_hook.svg",
        checksum_sha256="abc",
        asset_type=AssetType.PROHIBITED_SYNTHETIC,
    )

    svg_clip = ClipSpec(
        item_id="item_svg_bad",
        track_id="track_v2_broll",
        asset_id="ast_bad_svg",
        start_frame=0,
        end_frame=150,
        source_in_frame=0,
        source_out_frame=150,
        name="Bad SVG Card",
    )
    operations.append(
        EditOperation(
            operation_id="op_bad_svg",
            operation_type=EditOperationType.INSERT_CLIP,
            idempotency_key="idemp_bad_svg",
            track_id="track_v2_broll",
            clip_spec=svg_clip,
        )
    )

    validation = EditPlannerService.validate_edit_plan(
        edit_plan, operations, svg_registry, target_frames=900
    )
    assert validation.is_valid is False
    assert validation.guardrail_passed is False
    assert any("prohibited" in d.lower() for d in validation.discrepancies)


def test_cutlist_serialization_and_idempotency_keys(tmp_path: Path):
    """Verify cutlist JSON serializes cleanly and all operations have unique idempotency keys."""
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

    cutlist_json = EditPlannerService.generate_cutlist_json(operations)
    data = json.loads(cutlist_json)
    assert len(data) == len(operations)

    idemp_keys = [op["idempotency_key"] for op in data]
    assert len(idemp_keys) == len(set(idemp_keys)), "Duplicate idempotency keys detected"


def test_rough_cut_human_approval_gate(temp_repo: JobRepository):
    """Verify human approval gate records rough cut review and approves transition in SQLite."""
    approval_svc = ApprovalService(temp_repo)

    state = ProductionState(
        job_id="job_short13_phase6",
        project_id="8a894b86-d5e0-4222-ab88-df22a8e2168e",
        short_id="short_13_whatsapp_pg_rent",
        job_status=JobStatus.PAUSED_FOR_APPROVAL,
        current_stage=ProductionStage.EDITING,
        pending_approvals=["rough_cut_review"],
    )
    temp_repo.create_job(state)

    # Inspect pending approval
    pending = approval_svc.get_pending_approval("job_short13_phase6")
    assert pending is not None
    assert pending["current_stage"] == ProductionStage.EDITING.value
    assert "rough_cut_review" in pending["pending_approvals"]

    # Submit owner approval
    resumed_state = approval_svc.submit_decision(
        job_id="job_short13_phase6",
        decision=ApprovalStatus.APPROVED,
        reviewer="hirthick",
        feedback="Rough cut approved. Frame-accurate cuts and ducked audio verified.",
    )

    assert resumed_state.job_status == JobStatus.RUNNING
    assert ProductionStage.EDITING in resumed_state.approved_stages
    assert "rough_cut_review" not in resumed_state.pending_approvals

    # Verify audit record persisted in SQLite
    reloaded = temp_repo.get_job("job_short13_phase6")
    assert reloaded is not None
    assert ProductionStage.EDITING in reloaded.approved_stages
