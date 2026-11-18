"""Tests for Pattern A specification contracts, parameter bands, and the Pattern Linter."""

import pytest
from app.state.editor_models import EditorItem, EditorTimeline, EditorTrack
from app.state.pattern_spec import ParameterBand, ParameterSource, PatternSpec, ScalarParameter
from app.services.pattern_linter import PatternLinter


def test_pattern_a_production_readiness():
    """Verify Pattern A v1 has zero DEFAULT_UNVERIFIED parameters and is production ready."""
    spec = PatternSpec.get_pattern_a_v1()
    is_ready, unverified = spec.is_production_ready()
    assert is_ready is True
    assert len(unverified) == 0
    assert spec.caption_font_family.value == "Inter"
    assert spec.caption_base_color.value == "#FFFFFF"
    assert spec.caption_accent_color.value == "#9333EA"  # Purple


def test_pattern_spec_rejects_unverified_fields():
    """Verify production readiness check catches any unverified parameter."""
    spec = PatternSpec.get_pattern_a_v1()
    spec.caption_base_color = ScalarParameter(
        value="#FFFFFF", source=ParameterSource.DEFAULT_UNVERIFIED, evidence_ref="None"
    )
    is_ready, unverified = spec.is_production_ready()
    assert is_ready is False
    assert any("caption_base_color" in u for u in unverified)


def test_parameter_band_containment():
    """Verify parameter band interval logic [p10, p90]."""
    band = ParameterBand(median=2.8, p10=1.8, p90=4.2)
    assert band.contains(2.8) is True
    assert band.contains(1.8) is True
    assert band.contains(4.2) is True
    assert band.contains(1.5) is False
    assert band.contains(5.0) is False


def test_pattern_linter_passes_clean_timeline():
    """Verify Pattern Linter passes a compliant timeline."""
    spec = PatternSpec.get_pattern_a_v1()
    timeline = EditorTimeline(
        timeline_id="tl_test_clean",
        project_id="proj_clean",
        width=1080,
        height=1920,
        fps_num=30,
        fps_den=1,
        duration_frames=1050,  # 35s
        tracks=[
            EditorTrack(
                track_id="V1",
                name="A-Roll",
                track_type="video",
                order=0,
                items=[
                    EditorItem(
                        item_id="clip_1",
                        track_id="V1",
                        name="take1.mp4",
                        timeline_start_frame=0,
                        timeline_end_frame=90,  # 3.0s
                    ),
                    EditorItem(
                        item_id="clip_2",
                        track_id="V1",
                        name="take2.mp4",
                        timeline_start_frame=90,
                        timeline_end_frame=180,  # 3.0s
                    ),
                ],
            )
        ],
    )

    report = PatternLinter.lint_timeline(timeline, spec, placement_mode="CANDIDATES_ONLY")
    assert report.passed is True
    assert report.blocking_violations == 0


def test_pattern_linter_catches_prohibited_svg():
    """Verify Pattern Linter catches prohibited SVG cards on timeline."""
    spec = PatternSpec.get_pattern_a_v1()
    timeline = EditorTimeline(
        timeline_id="tl_test_bad",
        project_id="proj_bad",
        tracks=[
            EditorTrack(
                track_id="V2",
                name="Overlays",
                items=[
                    EditorItem(
                        item_id="bad_svg_1",
                        track_id="V2",
                        name="card1_hook.svg",
                        timeline_start_frame=0,
                        timeline_end_frame=90,
                    )
                ],
            )
        ],
    )

    report = PatternLinter.lint_timeline(timeline, spec)
    assert report.passed is False
    assert report.blocking_violations >= 1
    assert any("card1_hook.svg" in v.message for v in report.violations)


def test_pattern_linter_catches_unapproved_stock_placement():
    """Verify Pattern Linter flags stock clips placed while placement_mode is CANDIDATES_ONLY."""
    spec = PatternSpec.get_pattern_a_v1()
    timeline = EditorTimeline(
        timeline_id="tl_test_stock",
        project_id="proj_stock",
        tracks=[
            EditorTrack(
                track_id="V2",
                name="B-Roll Lane",
                items=[
                    EditorItem(
                        item_id="stock_item_1",
                        track_id="V2",
                        name="stock_video_pexels_123.mp4",
                        timeline_start_frame=0,
                        timeline_end_frame=90,
                    )
                ],
            )
        ],
    )

    report = PatternLinter.lint_timeline(timeline, spec, placement_mode="CANDIDATES_ONLY")
    assert report.passed is False
    assert any(v.rule_code == "UNAPPROVED_STOCK_PLACEMENT" for v in report.violations)
