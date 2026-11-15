"""Tests for Layer 04 (Render + Tharun Critique Loop) and Layer 05 (Full LangGraph State Topology).

Verifies:
  - Tharun Speaks 5-dimension style critique scoring (>= 8.5 threshold)
  - RenderCritiqueLoop orchestration and Gate 2 interrupt payload
  - Full LangGraph 10-node StateGraph compilation
  - Gate 1 and Gate 2 routing logic (APPROVED vs REJECTED)
  - Node transitions across all 6 layers
"""

from pathlib import Path
import pytest

from app.agents.render_critique_loop import (
    RenderCritiqueLoop,
    RenderCritiqueResult,
    TharunDimension,
    TharunStyleScorer,
)
from app.agents.second_by_second_editor import SecondBySecondEditor
from app.orchestration.full_pipeline_graph import (
    FullPipelineState,
    _build_default_short_13_script,
    _build_default_short_13_shot_plan,
    build_full_pipeline_graph,
    create_full_pipeline_graph_builder,
    n01_philosophy_guard,
    n02_project_scan,
    n03_shooting_script,
    n04_editing_script,
    n05_second_by_second,
    n06_render_critique,
    n07_export_authorize,
    n08_retrospective,
    route_after_gate1,
    route_after_gate2,
)
from app.philosophy import EditingPhilosophy
from app.state.enums import JobStatus, ProductionStage


@pytest.fixture
def philosophy():
    return EditingPhilosophy()


@pytest.fixture
def sample_script():
    return _build_default_short_13_script()


@pytest.fixture
def sample_shot_plan():
    return _build_default_short_13_shot_plan()


@pytest.fixture
def sample_timeline(sample_script, sample_shot_plan, philosophy):
    editor = SecondBySecondEditor()
    return editor.generate_timeline(
        script=sample_script,
        shot_plan=sample_shot_plan,
        caption_events=[],
        philosophy=philosophy,
        short_id="short-13",
    )


# ===========================================================================
# Layer 04: Tharun Speaks Style Scorer & Render Loop Tests
# ===========================================================================

def test_tharun_conversational_hook_scoring(sample_script):
    score = TharunStyleScorer.score_conversational_hook(sample_script)
    assert score.dimension == TharunDimension.CONVERSATIONAL_HOOK
    assert score.score >= 8.5
    assert score.passed is True


def test_tharun_story_tension_scoring(sample_script):
    score = TharunStyleScorer.score_story_tension(sample_script)
    assert score.dimension == TharunDimension.STORY_TENSION
    assert score.score >= 8.5
    assert score.passed is True


def test_tharun_visual_rhythm_scoring(sample_timeline):
    score = TharunStyleScorer.score_visual_rhythm(sample_timeline)
    assert score.dimension == TharunDimension.VISUAL_RHYTHM
    assert score.score >= 8.5
    assert score.passed is True


def test_tharun_caption_energy_scoring():
    from app.agents.editing_script_agent import CaptionEvent, CaptionEventType
    events = [
        CaptionEvent(
            event_id="e1",
            event_type=CaptionEventType.QUOTE_CARD,
            text="50 tenants automated.",
            start_second=9.0,
            end_second=11.0,
            accent_word="automated",
        )
    ]
    score = TharunStyleScorer.score_caption_energy(events)
    assert score.dimension == TharunDimension.CAPTION_ENERGY
    assert score.score >= 8.5
    assert score.passed is True


def test_tharun_authentic_voice_scoring(sample_script):
    score = TharunStyleScorer.score_authentic_voice(sample_script)
    assert score.dimension == TharunDimension.AUTHENTIC_VOICE
    assert score.score >= 8.5
    assert score.passed is True


def test_tharun_full_critique_scorecard(sample_script, sample_timeline):
    scorecard = TharunStyleScorer.run_full_style_critique(
        script=sample_script,
        timeline=sample_timeline,
        caption_events=[],
        short_id="short-13",
    )
    assert scorecard.overall_score >= 8.5
    assert scorecard.passed is True
    assert scorecard.gate_decision == "PASS"
    assert len(scorecard.dimension_scores) == 5
    assert len(scorecard.failing_dimensions) == 0


def test_render_critique_loop_run(sample_script, sample_shot_plan, sample_timeline, philosophy, tmp_path):
    video_mock = tmp_path / "mock_render.mp4"
    video_mock.write_bytes(b"dummy_mp4_bytes")

    result = RenderCritiqueLoop.run(
        script=sample_script,
        shot_plan=sample_shot_plan,
        timeline=sample_timeline,
        caption_events=[],
        philosophy=philosophy,
        short_id="short-13",
        video_path=video_mock,
        skip_actual_render=True,
    )

    assert isinstance(result, RenderCritiqueResult)
    assert result.video_exists is True
    assert result.video_size_bytes == 15
    assert result.tharun_passed is True

    # Validate Gate 2 approval payload
    payload = result.gate2_approval_payload
    assert payload["gate"] == "GATE_2_RENDER_APPROVAL"
    assert payload["overall_score"] >= 8.5
    assert payload["decision_options"] == ["APPROVED", "REJECTED"]
    assert "tharun_scorecard_summary" in payload


# ===========================================================================
# Layer 05: Full LangGraph Pipeline Topology & Routing Tests
# ===========================================================================

def test_full_pipeline_graph_compilation():
    builder = create_full_pipeline_graph_builder()
    assert builder is not None

    graph = build_full_pipeline_graph()
    assert graph is not None


def test_gate1_routing_approved():
    state: FullPipelineState = {"gate1_decision": "APPROVED", "job_status": JobStatus.RUNNING}
    dest = route_after_gate1(state)
    assert dest == "n04_editing_script"


def test_gate1_routing_rejected():
    state: FullPipelineState = {"gate1_decision": "REJECTED", "job_status": JobStatus.REJECTED}
    dest = route_after_gate1(state)
    assert dest == "n_reject_1"


def test_gate2_routing_approved():
    state: FullPipelineState = {"gate2_decision": "APPROVED", "job_status": JobStatus.RUNNING}
    dest = route_after_gate2(state)
    assert dest == "n07_export_authorize"


def test_gate2_routing_rejected():
    state: FullPipelineState = {"gate2_decision": "REJECTED", "job_status": JobStatus.REJECTED}
    dest = route_after_gate2(state)
    assert dest == "n_reject_2"


def test_nodes_step_by_step_execution():
    """Verify that node functions can be invoked sequentially."""
    state: FullPipelineState = {
        "job_id": "test_job_1",
        "project_id": "short_13_proj",
        "short_id": "short-13",
        "job_status": JobStatus.RUNNING,
        "completed_nodes": [],
    }

    # Node 1: Philosophy Guard
    res1 = n01_philosophy_guard(state)
    assert "n01_philosophy_guard" in res1["completed_nodes"]
    assert res1["philosophy_config"]["font_family"] == "Poppins"
    state.update(res1)

    # Node 2: Project Scan
    res2 = n02_project_scan(state)
    assert "n02_project_scan" in res2["completed_nodes"]
    assert res2["script"].hook_text != ""
    state.update(res2)

    # Node 3: Shooting Script Agent (Layer 01)
    res3 = n03_shooting_script(state)
    assert "n03_shooting_script" in res3["completed_nodes"]
    assert "cuts" in res3["shooting_script"]
    state.update(res3)

    # Simulate Gate 1 Approval
    state["gate1_decision"] = "APPROVED"

    # Node 4: Editing Script Agent (Layer 02)
    res4 = n04_editing_script(state)
    assert "n04_editing_script" in res4["completed_nodes"]
    assert "caption_events" in res4["editing_script_output"]
    state.update(res4)

    # Node 5: Second-by-Second Editor (Layer 03)
    res5 = n05_second_by_second(state)
    assert "n05_second_by_second" in res5["completed_nodes"]
    assert len(res5["full_timeline"]["seconds"]) == 30
    state.update(res5)

    # Node 6: Render & Tharun Critique (Layer 04)
    res6 = n06_render_critique(state)
    assert "n06_render_critique" in res6["completed_nodes"]
    assert res6["tharun_scorecard"]["overall_score"] >= 8.5
    state.update(res6)

    # Simulate Gate 2 Approval
    state["gate2_decision"] = "APPROVED"

    # Node 7: Export Authorize
    res7 = n07_export_authorize(state)
    assert "n07_export_authorize" in res7["completed_nodes"]
    assert res7["export_authorized"] is True
    state.update(res7)

    # Node 8: Retrospective
    res8 = n08_retrospective(state)
    assert "n08_retrospective" in res8["completed_nodes"]
    assert res8["job_status"] == JobStatus.COMPLETED
    assert res8["retrospective_log"]["status"] == "SUCCESS"
