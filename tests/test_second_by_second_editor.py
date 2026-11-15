"""Tests for Layer 03 — Second-by-Second Editor.

Verifies:
  - Timeline generation: 30 seconds, 900 frames, proper FPS
  - Section mapping and second tags
  - Stock B-roll count constraint compliance (<= 2)
  - Philosophy compliance validation
  - JSON and Markdown table generation
"""

from pathlib import Path
import pytest

from app.agents.second_by_second_editor import (
    FullTimeline,
    SecondBySecondEditor,
    TimelineSection,
)
from app.philosophy import EditingPhilosophy
from app.state.models import ScriptRecord, ShotPlanRecord


@pytest.fixture
def philosophy():
    return EditingPhilosophy()


@pytest.fixture
def sample_script():
    return ScriptRecord(
        version=1,
        hook_text="Managing 50 PG tenants and still tracking Excel?",
        problem_text="Every month you chase rent on WhatsApp.",
        solution_text="Tellos automates rent collection.",
        cta_text="Link in bio. Try free.",
        claims=["50 tenants automated"],
        full_narration="Managing 50 PG tenants and still tracking Excel? Tellos automates rent collection.",
        word_count=52,
        estimated_duration_seconds=30.0,
    )


@pytest.fixture
def sample_shot_plan():
    return ShotPlanRecord(
        version=1,
        shots=[],
        total_target_duration_seconds=30.0,
    )


def test_second_by_second_timeline_structure(sample_script, sample_shot_plan, philosophy):
    editor = SecondBySecondEditor()
    timeline = editor.generate_timeline(
        script=sample_script,
        shot_plan=sample_shot_plan,
        caption_events=[],
        philosophy=philosophy,
        short_id="short-13",
    )

    assert isinstance(timeline, FullTimeline)
    assert len(timeline.seconds) == 30
    assert timeline.total_seconds == 30
    assert timeline.total_frames == 900
    assert timeline.fps == 30

    # Verify first and last second tags
    assert timeline.seconds[0].second == 0
    assert timeline.seconds[0].section_tag == TimelineSection.HOOK
    assert timeline.seconds[29].second == 29
    assert timeline.seconds[29].section_tag == TimelineSection.CTA

    # No empty section tag
    for s in timeline.seconds:
        assert s.section_tag is not None
        assert s.section_tag.value in ["HOOK", "PROBLEM", "DEMO", "SOLUTION", "CTA"]
        assert s.frame_start == s.second * 30
        assert s.frame_end == (s.second + 1) * 30 - 1


def test_stock_broll_limit(sample_script, sample_shot_plan, philosophy):
    editor = SecondBySecondEditor()
    timeline = editor.generate_timeline(
        script=sample_script,
        shot_plan=sample_shot_plan,
        caption_events=[],
        philosophy=philosophy,
        short_id="short-13",
    )

    stock_seconds = [s for s in timeline.seconds if s.source_type == "STOCK_BROLL"]
    assert len(stock_seconds) <= philosophy.max_stock_clips


def test_philosophy_compliance(sample_script, sample_shot_plan, philosophy):
    editor = SecondBySecondEditor()
    timeline = editor.generate_timeline(
        script=sample_script,
        shot_plan=sample_shot_plan,
        caption_events=[],
        philosophy=philosophy,
        short_id="short-13",
    )

    violations = editor.validate_philosophy_compliance(timeline, philosophy)
    assert violations == []


def test_timeline_serialization(sample_script, sample_shot_plan, philosophy, tmp_path):
    editor = SecondBySecondEditor()
    timeline = editor.generate_timeline(
        script=sample_script,
        shot_plan=sample_shot_plan,
        caption_events=[],
        philosophy=philosophy,
        short_id="short-13",
    )

    json_path = tmp_path / "timeline.json"
    md_path = tmp_path / "timeline.md"

    editor.to_json(timeline, json_path)
    editor.to_markdown_table(timeline, md_path)

    assert json_path.exists()
    assert md_path.exists()
    assert "Managing 50 PG tenants" in md_path.read_text(encoding="utf-8")
    assert len(timeline.editor_notes) >= 3
