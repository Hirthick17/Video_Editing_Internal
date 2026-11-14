"""Test Phase 5: Footage intake, media understanding, transcription, and clip matching."""

from pathlib import Path
from app.services.media_understanding_service import (
    ClipMatchReport,
    MediaUnderstandingService,
    MissingFootageReport,
)
from app.services.project_scanner import ProjectScannerService
from app.services.script_service import ScriptService
from app.services.shot_planner_service import ShotPlannerService
from app.state.enums import AssetType, ReviewStatus


def test_extract_media_metadata_real_assets():
    """Verify ffprobe metadata extraction on real local files."""
    broll_path = Path(r"C:\Users\hirth\hirthick-professional\video-editor\broll-spreadsheet.mp4")
    if broll_path.exists():
        meta = MediaUnderstandingService.extract_media_metadata(broll_path)
        assert meta.width == 960
        assert meta.height == 540
        assert meta.has_video is True
        assert meta.duration_seconds > 20.0
        assert meta.video_codec == "h264"


def test_detect_usable_segments():
    """Verify scene segmentation returns valid half-open intervals for demo and b-roll."""
    demo_path = Path("demo-recording-1.mp4")
    segments = MediaUnderstandingService.detect_usable_segments(demo_path, "ast_demo_recording_01")

    assert len(segments) == 3
    labels = [s.label for s in segments]
    assert "WhatsApp Receipt Intake" in labels
    assert "TellOS Bot OCR & Live Sheet Update" in labels
    assert "Clean Paid Ledger Summary" in labels

    for seg in segments:
        assert seg.start_frame < seg.end_frame
        assert seg.start_seconds < seg.end_seconds
        assert seg.visual_clarity_score == 1.0


def test_generate_word_timed_transcript_monotonicity():
    """Verify word-timed transcript generation for the 58-word script has non-overlapping monotonic timings."""
    script = ScriptService.create_short_13_script()
    transcript = MediaUnderstandingService.generate_word_timed_transcript(script)

    assert transcript.asset_id == "ast_voiceover_short13"
    assert len(transcript.words) == script.word_count
    assert transcript.words[0].word.startswith("Managing")
    assert transcript.words[-1].word.startswith("today")

    # Verify monotonic, non-overlapping intervals
    for i in range(len(transcript.words)):
        w = transcript.words[i]
        assert w.start_seconds < w.end_seconds
        assert w.confidence > 0.95
        if i > 0:
            prev_w = transcript.words[i - 1]
            assert w.start_seconds >= prev_w.end_seconds, (
                f"Overlap detected: '{prev_w.word}' ({prev_w.start_seconds}-{prev_w.end_seconds}) "
                f"vs '{w.word}' ({w.start_seconds}-{w.end_seconds})"
            )


def test_clip_matching_and_coverage(tmp_path: Path):
    """Verify clip matching against 4-shot plan achieves 100% coverage and rough-cut readiness."""
    demo_file = tmp_path / "tellos_demo.mp4"
    demo_file.write_bytes(b"\x00" * 1024)
    broll_file = tmp_path / "broll-spreadsheet.mp4"
    broll_file.write_bytes(b"\x00" * 1024)

    project = ProjectScannerService.scan_short_13_project(
        base_dir=tmp_path,
        external_demo_path=demo_file,
    )

    shot_plan = ShotPlannerService.create_short_13_shot_plan(project)

    # Collect candidate segments from both assets
    segments = []
    segments.extend(MediaUnderstandingService.detect_usable_segments(demo_file, "ast_demo_recording_01"))
    segments.extend(MediaUnderstandingService.detect_usable_segments(broll_file, "ast_broll_spreadsheet_01"))

    match_report = MediaUnderstandingService.match_clips_to_shots(
        shot_plan, segments, project.asset_registry
    )

    assert match_report.is_complete is True
    assert match_report.total_shots_matched == 4
    assert len(match_report.unmatched_shots) == 0

    # Track placement checks
    v2_matches = [m for m in match_report.matches if m.target_track == "V2"]
    v1_matches = [m for m in match_report.matches if m.target_track == "V1"]
    assert len(v2_matches) == 1  # Shot 1 on V2
    assert len(v1_matches) == 3  # Shots 2, 3, 4 on V1

    missing_report = MediaUnderstandingService.check_missing_footage(
        shot_plan, match_report, project.asset_registry
    )

    assert missing_report.ready_for_edit is True
    assert missing_report.coverage_percentage == 100.0
    assert missing_report.missing_count == 0


def test_missing_footage_detection_on_unmatched():
    """Verify missing footage reporting when a shot cannot be matched."""
    script = ScriptService.create_short_13_script()
    project = ProjectScannerService.scan_short_13_project()
    shot_plan = ShotPlannerService.create_short_13_shot_plan(project)

    # Empty segments list -> nothing matches
    match_report = MediaUnderstandingService.match_clips_to_shots(
        shot_plan, [], project.asset_registry
    )
    assert match_report.is_complete is False
    assert match_report.total_shots_matched == 0
    assert len(match_report.unmatched_shots) == 4

    missing_report = MediaUnderstandingService.check_missing_footage(
        shot_plan, match_report, project.asset_registry
    )
    assert missing_report.ready_for_edit is False
    assert missing_report.coverage_percentage == 0.0
    assert missing_report.missing_count == 4

