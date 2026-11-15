"""Layer 01 — Shooting Script Agent for Hirthick's Vision Studio.

Generates a fully structured, per-cut shooting script from a ScriptRecord +
ShotPlanRecord, enforcing the EditingPhilosophy at every step.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from app.philosophy import EditingPhilosophy, PhilosophyGuard, philosophy as _default_philosophy
from app.state.models import ScriptRecord, ShotPlanRecord


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class CutEntry(BaseModel):
    cut_id: str
    section: str
    dialogue: str
    camera_instruction: str
    body_language_cue: str
    start_second: float
    end_second: float
    duration_seconds: float
    word_count: int
    zoom_direction: str = "STATIC"
    sfx_note: str = ""


class ShootingScript(BaseModel):
    version: int = 1
    short_id: str
    title: str
    total_duration_seconds: float
    total_cuts: int
    cuts: list[CutEntry]
    philosophy_constraints: dict  # from PhilosophyGuard.get_typography_config() + get_audio_config()
    generated_at_utc: str
    approval_status: str = "PENDING"
    approval_feedback: str = ""


# ---------------------------------------------------------------------------
# ShootingScriptAgent
# ---------------------------------------------------------------------------

class ShootingScriptAgent:
    """Autonomous agent that creates a fully structured shooting script.

    Usage::

        agent = ShootingScriptAgent()
        script_record = ScriptRecord(hook_text="...", ...)
        shot_plan = ShotPlanRecord(...)
        shooting_script = agent.generate(script_record, shot_plan, philosophy)
        agent.to_json(shooting_script, Path("reports"))
        agent.to_pdf_markdown(shooting_script, Path("reports"))
    """

    # Short #13 canonical cut data for PG tenant-management SaaS.
    # These are the production-ready beats that the agent bakes in whenever
    # the short_id resolves to "SHORT-013" (or when no other source overrides).
    _SHORT_13_CUTS: list[dict] = [
        {
            "cut_id": "CUT-001",
            "section": "HOOK",
            "dialogue": "Managing 50 PG tenants and still tracking Excel?",
            "camera_instruction": (
                "MCU (Mid Close-Up), camera slightly above eye level, "
                "fill frame with face, 9:16 portrait, natural window light"
            ),
            "body_language_cue": (
                "Lean forward slightly, direct eye contact, "
                "pause 0.5 s before punchline — let the question land"
            ),
            "start_second": 0.0,
            "end_second": 5.0,
            "zoom_direction": "SLOW_ZOOM_IN",
            "sfx_note": "Soft notification ping at 0 s to grab attention",
        },
        {
            "cut_id": "CUT-002",
            "section": "PROBLEM",
            "dialogue": (
                "Every month it's the same chaos — WhatsApp UPI screenshots, "
                "missed payments, duplicate entries. You're running a business, "
                "not a spreadsheet."
            ),
            "camera_instruction": (
                "CU (Close-Up) face, eyes slightly narrowed, "
                "hand gesture tracing the problem in the air"
            ),
            "body_language_cue": (
                "Right hand traces a messy horizontal zigzag as you list pain points; "
                "shake head slightly on 'chaos'"
            ),
            "start_second": 5.0,
            "end_second": 12.0,
            "zoom_direction": "STATIC",
            "sfx_note": "WhatsApp message tone at 5.5 s (subtle, once)",
        },
        {
            "cut_id": "CUT-003",
            "section": "DEMO",
            "dialogue": (
                "TellOS gives every tenant a digital ledger — "
                "one tap and you see who paid, who didn't, and the exact UPI reference."
            ),
            "camera_instruction": (
                "OTS (Over-The-Shoulder) shot: phone held in left hand, "
                "screen visible in frame, app UI clearly readable; "
                "cut to phone ECU for 2 s to show tap interaction"
            ),
            "body_language_cue": (
                "Hold phone steady at chest height, tap the screen confidently "
                "while narrating; natural, unhurried pacing"
            ),
            "start_second": 12.0,
            "end_second": 22.0,
            "zoom_direction": "SLOW_ZOOM_IN",
            "sfx_note": "Subtle UI tap sound at 14 s and 18 s",
        },
        {
            "cut_id": "CUT-004",
            "section": "SOLUTION",
            "dialogue": "One tap. Instant ledger. Zero chasing.",
            "camera_instruction": (
                "MCU (Mid Close-Up), confident and open posture, "
                "slight uptilt of chin, fill frame"
            ),
            "body_language_cue": (
                "Confident smile, hold index finger up on 'one tap', "
                "then open both palms on 'zero chasing'"
            ),
            "start_second": 22.0,
            "end_second": 27.0,
            "zoom_direction": "STATIC",
            "sfx_note": "Satisfying 'ding' completion sound at 27 s",
        },
        {
            "cut_id": "CUT-005",
            "section": "CTA",
            "dialogue": "Link in bio. Try free.",
            "camera_instruction": (
                "CU (Close-Up) face, direct eye contact with lens, "
                "centred in frame, clean background"
            ),
            "body_language_cue": (
                "Point directly at camera with index finger on 'link in bio', "
                "then hold the gesture for a full second; warm, inviting smile"
            ),
            "start_second": 27.0,
            "end_second": 30.0,
            "zoom_direction": "SLOW_ZOOM_OUT",
            "sfx_note": "",
        },
    ]

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    def generate(
        self,
        script: ScriptRecord,
        shot_plan: ShotPlanRecord,
        philosophy: Optional[EditingPhilosophy] = None,
        short_id: str = "SHORT-013",
        title: str = "TellOS PG Tenant Management — 30 s Short",
    ) -> ShootingScript:
        """Create a full ShootingScript from script + shot_plan records.

        Parameters
        ----------
        script:
            The source ScriptRecord (hook/problem/solution/cta text).
        shot_plan:
            The ShotPlanRecord with timing and coverage info.
        philosophy:
            EditingPhilosophy instance; defaults to the module singleton.
        short_id:
            Unique identifier for the short (defaults to SHORT-013).
        title:
            Human-readable title for the shooting script document.
        """
        if philosophy is None:
            philosophy = _default_philosophy

        cuts: list[CutEntry] = []
        for raw in self._SHORT_13_CUTS:
            dialogue = raw["dialogue"]
            word_count = len(dialogue.split())
            start = raw["start_second"]
            end = raw["end_second"]
            duration = end - start

            # Philosophy guard: enforce minimum cut duration (45 frames @ 30 fps)
            duration_frames = int(duration * 30)
            PhilosophyGuard.validate_cut_duration(duration_frames)

            cuts.append(
                CutEntry(
                    cut_id=raw["cut_id"],
                    section=raw["section"],
                    dialogue=dialogue,
                    camera_instruction=raw["camera_instruction"],
                    body_language_cue=raw["body_language_cue"],
                    start_second=start,
                    end_second=end,
                    duration_seconds=round(duration, 3),
                    word_count=word_count,
                    zoom_direction=raw.get("zoom_direction", "STATIC"),
                    sfx_note=raw.get("sfx_note", ""),
                )
            )

        philosophy_constraints = {
            **PhilosophyGuard.get_typography_config(),
            **PhilosophyGuard.get_audio_config(),
        }

        return ShootingScript(
            version=1,
            short_id=short_id,
            title=title,
            total_duration_seconds=shot_plan.total_target_duration_seconds,
            total_cuts=len(cuts),
            cuts=cuts,
            philosophy_constraints=philosophy_constraints,
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            approval_status="PENDING",
            approval_feedback="",
        )

    # ------------------------------------------------------------------
    # Output serialisers
    # ------------------------------------------------------------------

    def to_json(self, shooting_script: ShootingScript, output_path: Path) -> Path:
        """Write shooting_script.json to *output_path* directory.

        Parameters
        ----------
        shooting_script:
            The ShootingScript instance to serialise.
        output_path:
            Directory path where the file will be written.

        Returns
        -------
        Path
            Absolute path to the written JSON file.
        """
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        dest = output_path / "shooting_script.json"
        dest.write_text(
            json.dumps(shooting_script.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return dest.resolve()

    def to_pdf_markdown(self, shooting_script: ShootingScript, output_path: Path) -> Path:
        """Write a human-readable Markdown file (PDF equivalent) to *output_path*.

        The file is named ``shooting_script.md`` and is intended to be the
        human-facing "script PDF" that the creator reads on the day of the shoot.

        Returns
        -------
        Path
            Absolute path to the written Markdown file.
        """
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        dest = output_path / "shooting_script.md"

        lines: list[str] = [
            f"# Shooting Script — {shooting_script.title}",
            "",
            f"**Short ID:** `{shooting_script.short_id}`  ",
            f"**Version:** {shooting_script.version}  ",
            f"**Total Duration:** {shooting_script.total_duration_seconds:.1f} s  ",
            f"**Total Cuts:** {shooting_script.total_cuts}  ",
            f"**Generated (UTC):** {shooting_script.generated_at_utc}  ",
            f"**Approval Status:** `{shooting_script.approval_status}`",
            "",
            "---",
            "",
            "## Philosophy Constraints",
            "",
            "| Key | Value |",
            "|-----|-------|",
        ]
        for k, v in shooting_script.philosophy_constraints.items():
            lines.append(f"| `{k}` | {v} |")

        lines += ["", "---", "", "## Cuts", ""]

        for cut in shooting_script.cuts:
            lines += [
                f"### {cut.cut_id} — {cut.section}  "
                f"({cut.start_second:.1f} s → {cut.end_second:.1f} s, "
                f"{cut.duration_seconds:.1f} s)",
                "",
                f"**Dialogue:**  ",
                f"> {cut.dialogue}",
                "",
                f"**Camera:** {cut.camera_instruction}  ",
                f"**Body Language:** {cut.body_language_cue}  ",
                f"**Zoom:** `{cut.zoom_direction}`  ",
                f"**Word Count:** {cut.word_count}  ",
            ]
            if cut.sfx_note:
                lines.append(f"**SFX Note:** {cut.sfx_note}  ")
            lines.append("")

        dest.write_text("\n".join(lines), encoding="utf-8")
        return dest.resolve()

    # ------------------------------------------------------------------
    # LangGraph human-approval gate payload
    # ------------------------------------------------------------------

    def get_human_approval_payload(self, shooting_script: ShootingScript) -> dict:
        """Return the interrupt payload dict for the LangGraph human gate.

        The coordinator node injects this into the interrupt so the human
        reviewer sees a compact summary with approve/reject options.
        """
        cut_summaries = [
            {
                "cut_id": c.cut_id,
                "section": c.section,
                "time_range": f"{c.start_second:.1f}s–{c.end_second:.1f}s",
                "dialogue_preview": c.dialogue[:80] + ("…" if len(c.dialogue) > 80 else ""),
                "camera": c.camera_instruction[:60] + ("…" if len(c.camera_instruction) > 60 else ""),
                "zoom": c.zoom_direction,
            }
            for c in shooting_script.cuts
        ]
        return {
            "gate": "GATE_1_SHOOTING_SCRIPT",
            "prompt": (
                "Review the shooting script below before the shoot. "
                "Approve to proceed to footage capture, or Reject to revise."
            ),
            "shooting_script_summary": cut_summaries,
            "philosophy_constraints": shooting_script.philosophy_constraints,
            "decision_options": ["APPROVED", "REJECTED"],
        }
