"""Tests for Layer 01 — ShootingScriptAgent.

Covers:
- Full generation for Short #13 (5-cut PG tenant management SaaS)
- Section / approval-status assertions
- JSON serialisability
- PhilosophyViolationError is NOT raised for valid cuts
- Human-approval gate payload structure
"""

import json
from pathlib import Path

import pytest

from app.agents.shooting_script_agent import ShootingScript, ShootingScriptAgent
from app.philosophy import EditingPhilosophy, PhilosophyGuard, PhilosophyViolationError, philosophy
from app.state.models import ScriptRecord, ShotPlanRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def script_record() -> ScriptRecord:
    return ScriptRecord(
        hook_text="Managing 50 PG tenants and still tracking Excel?",
        problem_text=(
            "Every month it's the same chaos — WhatsApp UPI screenshots, "
            "missed payments, duplicate entries."
        ),
        solution_text="One tap. Instant ledger. Zero chasing.",
        cta_text="Link in bio. Try free.",
        full_narration=(
            "Managing 50 PG tenants and still tracking Excel? "
            "Every month it's chaos. TellOS fixes it. One tap. Link in bio."
        ),
        word_count=35,
        estimated_duration_seconds=30.0,
    )


@pytest.fixture()
def shot_plan() -> ShotPlanRecord:
    return ShotPlanRecord(
        total_target_duration_seconds=30.0,
    )


@pytest.fixture()
def agent() -> ShootingScriptAgent:
    return ShootingScriptAgent()


@pytest.fixture()
def shooting_script(agent, script_record, shot_plan) -> ShootingScript:
    return agent.generate(script_record, shot_plan, philosophy)


# ---------------------------------------------------------------------------
# Core generation tests
# ---------------------------------------------------------------------------

class TestShootingScriptGeneration:
    def test_generates_five_cuts(self, shooting_script):
        assert len(shooting_script.cuts) == 5

    def test_first_cut_is_hook(self, shooting_script):
        assert shooting_script.cuts[0].section == "HOOK"

    def test_cut_sections_in_order(self, shooting_script):
        expected = ["HOOK", "PROBLEM", "DEMO", "SOLUTION", "CTA"]
        actual = [c.section for c in shooting_script.cuts]
        assert actual == expected

    def test_cut_ids_sequential(self, shooting_script):
        ids = [c.cut_id for c in shooting_script.cuts]
        assert ids == ["CUT-001", "CUT-002", "CUT-003", "CUT-004", "CUT-005"]

    def test_approval_status_pending(self, shooting_script):
        assert shooting_script.approval_status == "PENDING"

    def test_total_cuts_field(self, shooting_script):
        assert shooting_script.total_cuts == 5

    def test_total_duration_matches_shot_plan(self, shooting_script):
        assert shooting_script.total_duration_seconds == 30.0

    def test_philosophy_constraints_present(self, shooting_script):
        pc = shooting_script.philosophy_constraints
        assert "font_family" in pc
        assert "bgm_duck_db" in pc
        assert pc["font_family"] == "Poppins"


# ---------------------------------------------------------------------------
# Cut-level field tests
# ---------------------------------------------------------------------------

class TestCutFields:
    def test_all_cuts_have_dialogues(self, shooting_script):
        for cut in shooting_script.cuts:
            assert cut.dialogue, f"{cut.cut_id} has empty dialogue"

    def test_all_cuts_have_camera_instructions(self, shooting_script):
        for cut in shooting_script.cuts:
            assert cut.camera_instruction, f"{cut.cut_id} missing camera instruction"

    def test_all_cuts_have_valid_zoom_direction(self, shooting_script):
        valid = {"STATIC", "SLOW_ZOOM_IN", "SLOW_ZOOM_OUT"}
        for cut in shooting_script.cuts:
            assert cut.zoom_direction in valid, f"{cut.cut_id} has invalid zoom: {cut.zoom_direction}"

    def test_cut_durations_non_zero(self, shooting_script):
        for cut in shooting_script.cuts:
            assert cut.duration_seconds > 0

    def test_hook_zoom_direction(self, shooting_script):
        hook = shooting_script.cuts[0]
        assert hook.zoom_direction == "SLOW_ZOOM_IN"

    def test_cta_cut_times(self, shooting_script):
        cta = shooting_script.cuts[4]
        assert cta.start_second == 27.0
        assert cta.end_second == 30.0

    def test_word_counts_positive(self, shooting_script):
        for cut in shooting_script.cuts:
            assert cut.word_count > 0


# ---------------------------------------------------------------------------
# Philosophy violation tests
# ---------------------------------------------------------------------------

class TestPhilosophyViolations:
    def test_no_violation_for_valid_cuts(self, shooting_script):
        """No PhilosophyViolationError should be raised for the Short #13 cuts."""
        for cut in shooting_script.cuts:
            frames = int(cut.duration_seconds * 30)
            # Should not raise
            PhilosophyGuard.validate_cut_duration(frames)

    def test_violation_raised_for_short_cut(self):
        """A cut shorter than 45 frames must raise PhilosophyViolationError."""
        with pytest.raises(PhilosophyViolationError, match="below the minimum"):
            PhilosophyGuard.validate_cut_duration(30)  # 1.0 s = 30 frames < 45

    def test_violation_raised_for_too_many_stock_clips(self):
        with pytest.raises(PhilosophyViolationError, match="exceeds hard cap"):
            PhilosophyGuard.validate_stock_clip_count(3)

    def test_no_violation_for_max_stock_clips(self):
        PhilosophyGuard.validate_stock_clip_count(2)  # exactly at the cap — OK

    def test_lut_violation(self):
        with pytest.raises(PhilosophyViolationError, match="LUT"):
            PhilosophyGuard.validate_no_lut(True)

    def test_svg_violation(self):
        with pytest.raises(PhilosophyViolationError, match="SVG"):
            PhilosophyGuard.validate_no_svg("assets/card.svg")

    def test_check_all_returns_empty_for_clean_ops(self):
        ops = [
            {"stock_clip_count": 1, "cut_duration_frames": 150, "has_lut": False, "asset_path": "clip.mp4"},
        ]
        violations = PhilosophyGuard.check_all(ops)
        assert violations == []

    def test_check_all_catches_multiple_violations(self):
        ops = [
            {"stock_clip_count": 5, "cut_duration_frames": 20, "has_lut": True, "asset_path": "card.svg"},
        ]
        violations = PhilosophyGuard.check_all(ops)
        assert len(violations) >= 4  # one per violated guard


# ---------------------------------------------------------------------------
# JSON serialisability
# ---------------------------------------------------------------------------

class TestJsonSerialisability:
    def test_shooting_script_serialises_to_json(self, shooting_script):
        """ShootingScript.model_dump() must round-trip through json.dumps without error."""
        payload = shooting_script.model_dump()
        serialised = json.dumps(payload)
        parsed = json.loads(serialised)
        assert parsed["total_cuts"] == 5
        assert parsed["approval_status"] == "PENDING"

    def test_to_json_writes_file(self, agent, shooting_script, tmp_path):
        dest = agent.to_json(shooting_script, tmp_path)
        assert dest.exists()
        content = json.loads(dest.read_text(encoding="utf-8"))
        assert content["total_cuts"] == 5

    def test_to_pdf_markdown_writes_file(self, agent, shooting_script, tmp_path):
        dest = agent.to_pdf_markdown(shooting_script, tmp_path)
        assert dest.exists()
        md = dest.read_text(encoding="utf-8")
        assert "HOOK" in md
        assert "CUT-001" in md


# ---------------------------------------------------------------------------
# Human approval gate payload
# ---------------------------------------------------------------------------

class TestHumanApprovalPayload:
    def test_gate_key(self, agent, shooting_script):
        payload = agent.get_human_approval_payload(shooting_script)
        assert payload["gate"] == "GATE_1_SHOOTING_SCRIPT"

    def test_decision_options(self, agent, shooting_script):
        payload = agent.get_human_approval_payload(shooting_script)
        assert "APPROVED" in payload["decision_options"]
        assert "REJECTED" in payload["decision_options"]

    def test_summary_has_five_entries(self, agent, shooting_script):
        payload = agent.get_human_approval_payload(shooting_script)
        assert len(payload["shooting_script_summary"]) == 5

    def test_philosophy_constraints_in_payload(self, agent, shooting_script):
        payload = agent.get_human_approval_payload(shooting_script)
        assert "font_family" in payload["philosophy_constraints"]


# ---------------------------------------------------------------------------
# Output files integration (uses real reports/ dir)
# ---------------------------------------------------------------------------

class TestOutputFilesIntegration:
    def test_writes_reports_json(self, agent, shooting_script):
        base = Path(__file__).resolve().parent.parent / "reports"
        dest = agent.to_json(shooting_script, base)
        assert dest.exists()

    def test_writes_reports_markdown(self, agent, shooting_script):
        base = Path(__file__).resolve().parent.parent / "reports"
        dest = agent.to_pdf_markdown(shooting_script, base)
        assert dest.exists()
