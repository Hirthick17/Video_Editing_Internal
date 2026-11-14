"""Test Phase 4: Research verification, script drafting, and shot plan feasibility."""

from pathlib import Path
from app.services.project_scanner import ProjectScannerService
from app.services.research_service import ResearchService
from app.services.script_service import ScriptService
from app.services.shot_planner_service import ShotPlannerService
from app.state.models import ShotItem
from app.state.enums import AssetType


def test_research_context_and_claims_verification():
    """Verify research context and factual claims validation."""
    context = ResearchService.get_short_13_research()
    assert len(context.verified_claims) >= 4
    assert all(c.verified for c in context.verified_claims)

    valid_script = "Managing 50 PG tenants on WhatsApp? TellOS automates rent receipts into Excel."
    ok, unsupported = ResearchService.verify_script_claims(valid_script, context)
    assert ok is True
    assert len(unsupported) == 0

    invalid_script = "TellOS makes you a millionaire overnight with 100% free forever software."
    bad_ok, bad_unsupported = ResearchService.verify_script_claims(invalid_script, context)
    assert bad_ok is False
    assert len(bad_unsupported) == 2


def test_script_creation_pacing_and_beats():
    """Verify script drafting, word count, timing, and narrative beat decomposition."""
    script = ScriptService.create_short_13_script()
    assert script.word_count >= 50 and script.word_count <= 65
    assert script.estimated_duration_seconds >= 24.0 and script.estimated_duration_seconds <= 29.0
    assert len(script.claims) >= 3

    beats = ScriptService.decompose_beats(script)
    assert len(beats) == 4
    beat_names = [b.beat_name for b in beats]
    assert beat_names == ["Hook", "Problem", "Solution", "CTA"]
    assert sum(b.estimated_duration_seconds for b in beats) == 30.0


def test_shot_plan_continuity_and_intervals(tmp_path: Path):
    """Verify shot plan half-open intervals [start, end) are strictly contiguous and total 900 frames."""
    demo_file = tmp_path / "tellos_demo.mp4"
    demo_file.write_bytes(b"\x00" * 1024)

    project = ProjectScannerService.scan_short_13_project(
        base_dir=tmp_path,
        external_demo_path=demo_file,
    )

    shot_plan = ShotPlannerService.create_short_13_shot_plan(project)
    assert len(shot_plan.shots) == 4
    assert shot_plan.total_target_duration_seconds == 30.0

    # Verify contiguous half-open intervals
    assert (shot_plan.shots[0].start_frame, shot_plan.shots[0].end_frame) == (0, 150)
    assert (shot_plan.shots[1].start_frame, shot_plan.shots[1].end_frame) == (150, 360)
    assert (shot_plan.shots[2].start_frame, shot_plan.shots[2].end_frame) == (360, 660)
    assert (shot_plan.shots[3].start_frame, shot_plan.shots[3].end_frame) == (660, 900)

    # Durations: 150 + 210 + 300 + 240 = 900 frames
    durations = [s.end_frame - s.start_frame for s in shot_plan.shots]
    assert sum(durations) == 900


def test_shot_plan_feasibility_validation(tmp_path: Path):
    """Verify 100% asset coverage when all required assets are online."""
    demo_file = tmp_path / "tellos_demo.mp4"
    demo_file.write_bytes(b"\x00" * 1024)
    broll_file = tmp_path / "broll-spreadsheet.mp4"
    broll_file.write_bytes(b"\x00" * 1024)

    project = ProjectScannerService.scan_short_13_project(
        base_dir=tmp_path,
        external_demo_path=demo_file,
    )

    shot_plan = ShotPlannerService.create_short_13_shot_plan(project)
    report = ShotPlannerService.validate_shot_plan_feasibility(shot_plan, project)

    assert report.is_feasible is True
    assert report.coverage_percentage == 100.0
    assert report.total_frames == 900
    assert len(report.missing_shots) == 0


def test_shot_plan_detects_unmatched_asset(tmp_path: Path):
    """Verify feasibility fails if a shot refers to an unapproved or offline asset."""
    project = ProjectScannerService.scan_short_13_project(base_dir=tmp_path)
    shot_plan = ShotPlannerService.create_short_13_shot_plan(project)

    # Corrupt a shot to reference a non-existent asset
    shot_plan.shots[0].matched_asset_id = "ast_non_existent"
    report = ShotPlannerService.validate_shot_plan_feasibility(shot_plan, project)

    assert report.is_feasible is False
    assert "shot_01_hook_spreadsheet" in report.missing_shots


def test_owner_recording_checklist_generation(tmp_path: Path):
    """Verify recording checklist output formatting."""
    project = ProjectScannerService.scan_short_13_project(base_dir=tmp_path)
    shot_plan = ShotPlannerService.create_short_13_shot_plan(project)

    checklist_md = ShotPlannerService.generate_owner_recording_checklist(shot_plan)
    assert "# Supplementary Recording Checklist" in checklist_md
    assert "Vertical 9:16 (1080×1920) at 30 FPS" in checklist_md
    assert "shot_01_hook_spreadsheet" in checklist_md
    assert "shot_04_dashboard_cta" in checklist_md

