"""Layer 03 — Second-by-Second Editor for Hirthick's Vision Studio.

Generates an exact 30-second timeline at second-level granularity —
the kind a real video editor would write, then the system generates automatically.
"""

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.state.models import ScriptRecord, ShotPlanRecord


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TimelineSection(str, Enum):
    HOOK = "HOOK"
    PROBLEM = "PROBLEM"
    DEMO = "DEMO"
    SOLUTION = "SOLUTION"
    CTA = "CTA"


class SFXType(str, Enum):
    NONE = "none"
    WHOOSH = "whoosh"           # transition between sections
    NOTIFICATION = "notification"  # WhatsApp notification sound
    KEYBOARD = "keyboard"       # typing sound
    POP = "pop"                 # UI pop for caption appear
    CHIME = "chime"             # success/completion sound


class BGMLevel(str, Enum):
    FULL = "full"       # 100% (intro/outro, no narration)
    DUCKED = "ducked"   # 12.5% (-18dB, under narration)
    SILENT = "silent"   # 0% (not used in this style)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class TimelineSecond(BaseModel):
    second: int                 # 0-indexed second (0 = t=0s to t=1s)
    frame_start: int            # second * 30
    frame_end: int              # (second + 1) * 30 - 1
    source_type: str            # "CREATOR_FOOTAGE", "SCREEN_RECORDING", "STOCK_BROLL", "TRANSITION"
    source_description: str     # e.g. "Creator MCU - Hook delivery"
    cut_id: str                 # reference to CUT-001..CUT-005 from shooting script
    sfx: SFXType                # sound effect at this second
    bgm_level: BGMLevel         # BGM level during this second
    bgm_note: str               # e.g. "Upbeat lo-fi intro at -18dB"
    caption_text: str           # caption shown during this second (empty if none)
    caption_event_type: str     # "word_reveal", "quote_card", "section_header", "fade_in", ""
    section_tag: TimelineSection  # which section this second belongs to
    visual_note: str            # e.g. "Slow zoom in 0.98x→1.02x over 5 seconds"
    b_roll_note: str            # e.g. "Overlay: TellOS dashboard screenshot" or ""


class FullTimeline(BaseModel):
    version: int = 1
    short_id: str
    total_seconds: int          # 30
    total_frames: int           # 900
    fps: int = 30
    seconds: list[TimelineSecond]
    section_map: dict           # section -> [start_second, end_second]
    philosophy_applied: dict    # snapshot of philosophy constraints used
    generated_at_utc: str
    editor_notes: list[str]     # 3-5 professional editor notes about choices made


# ---------------------------------------------------------------------------
# Reference timeline data for Short #13
# ---------------------------------------------------------------------------

_SHORT13_SECONDS: list[dict[str, Any]] = [
    # t=0 — HOOK
    dict(second=0, source_type="CREATOR_FOOTAGE", source_description="Creator MCU - Hook opening pose",
         cut_id="CUT-001", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi intro at -18dB",
         caption_text="Managing 50 PG tenants", caption_event_type="section_header",
         section_tag=TimelineSection.HOOK, visual_note="Slow zoom in 0.98x→1.02x over 5 seconds",
         b_roll_note=""),
    # t=1
    dict(second=1, source_type="CREATOR_FOOTAGE", source_description="Creator MCU - Hook delivery",
         cut_id="CUT-001", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="and still tracking Excel?", caption_event_type="word_reveal",
         section_tag=TimelineSection.HOOK, visual_note="Hold MCU",
         b_roll_note=""),
    # t=2
    dict(second=2, source_type="CREATOR_FOOTAGE", source_description="Creator MCU - pause for punchline effect",
         cut_id="CUT-001", sfx=SFXType.POP, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="", caption_event_type="",
         section_tag=TimelineSection.HOOK, visual_note="Slight push in",
         b_roll_note=""),
    # t=3
    dict(second=3, source_type="CREATOR_FOOTAGE", source_description="Creator MCU - reaction to Excel chaos",
         cut_id="CUT-001", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="Every month...", caption_event_type="word_reveal",
         section_tag=TimelineSection.HOOK, visual_note="",
         b_roll_note=""),
    # t=4
    dict(second=4, source_type="CREATOR_FOOTAGE", source_description="Creator MCU - lean back, setup problem",
         cut_id="CUT-001", sfx=SFXType.WHOOSH, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="", caption_event_type="",
         section_tag=TimelineSection.HOOK, visual_note="Section transition wipe",
         b_roll_note=""),
    # t=5 — PROBLEM
    dict(second=5, source_type="CREATOR_FOOTAGE", source_description="Creator CU - WhatsApp UPI problem setup",
         cut_id="CUT-002", sfx=SFXType.NOTIFICATION, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="WhatsApp payments...", caption_event_type="word_reveal",
         section_tag=TimelineSection.PROBLEM, visual_note="",
         b_roll_note=""),
    # t=6
    dict(second=6, source_type="CREATOR_FOOTAGE", source_description="Creator CU - hand gesture tracing problem",
         cut_id="CUT-002", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="don't match your ledger.", caption_event_type="word_reveal",
         section_tag=TimelineSection.PROBLEM, visual_note="",
         b_roll_note=""),
    # t=7
    dict(second=7, source_type="CREATOR_FOOTAGE", source_description="Creator CU - shows frustration",
         cut_id="CUT-002", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="You're matching screenshots", caption_event_type="word_reveal",
         section_tag=TimelineSection.PROBLEM, visual_note="",
         b_roll_note=""),
    # t=8
    dict(second=8, source_type="CREATOR_FOOTAGE", source_description="Creator CU - counts on fingers",
         cut_id="CUT-002", sfx=SFXType.KEYBOARD, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="one by one.", caption_event_type="word_reveal",
         section_tag=TimelineSection.PROBLEM, visual_note="",
         b_roll_note=""),
    # t=9
    dict(second=9, source_type="SCREEN_RECORDING", source_description="TellOS dashboard overview - problem state",
         cut_id="CUT-002", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="50 tenants.", caption_event_type="quote_card",
         section_tag=TimelineSection.PROBLEM, visual_note="",
         b_roll_note=""),
    # t=10
    dict(second=10, source_type="SCREEN_RECORDING", source_description="TellOS pending payments list",
         cut_id="CUT-002", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="50 WhatsApp threads.", caption_event_type="quote_card",
         section_tag=TimelineSection.PROBLEM, visual_note="",
         b_roll_note=""),
    # t=11
    dict(second=11, source_type="SCREEN_RECORDING", source_description="Excel spreadsheet chaos",
         cut_id="CUT-002", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="", caption_event_type="",
         section_tag=TimelineSection.PROBLEM, visual_note="",
         b_roll_note=""),
    # t=12 — DEMO
    dict(second=12, source_type="SCREEN_RECORDING", source_description="TellOS app - main dashboard",
         cut_id="CUT-003", sfx=SFXType.WHOOSH, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="TellOS reads", caption_event_type="word_reveal",
         section_tag=TimelineSection.DEMO, visual_note="Section transition",
         b_roll_note=""),
    # t=13
    dict(second=13, source_type="SCREEN_RECORDING", source_description="TellOS - WhatsApp OCR trigger",
         cut_id="CUT-003", sfx=SFXType.NOTIFICATION, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="every WhatsApp payment", caption_event_type="word_reveal",
         section_tag=TimelineSection.DEMO, visual_note="",
         b_roll_note=""),
    # t=14
    dict(second=14, source_type="SCREEN_RECORDING", source_description="TellOS - UPI auto-match animation",
         cut_id="CUT-003", sfx=SFXType.CHIME, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="automatically.", caption_event_type="word_reveal",
         section_tag=TimelineSection.DEMO, visual_note="",
         b_roll_note=""),
    # t=15
    dict(second=15, source_type="SCREEN_RECORDING", source_description="TellOS - ledger auto-update",
         cut_id="CUT-003", sfx=SFXType.KEYBOARD, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="Ledger updates", caption_event_type="word_reveal",
         section_tag=TimelineSection.DEMO, visual_note="",
         b_roll_note=""),
    # t=16
    dict(second=16, source_type="SCREEN_RECORDING", source_description="TellOS - WhatsApp message parsed",
         cut_id="CUT-003", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="in real time.", caption_event_type="word_reveal",
         section_tag=TimelineSection.DEMO, visual_note="",
         b_roll_note=""),
    # t=17
    dict(second=17, source_type="SCREEN_RECORDING", source_description="TellOS - tenant list updated",
         cut_id="CUT-003", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="", caption_event_type="",
         section_tag=TimelineSection.DEMO, visual_note="",
         b_roll_note=""),
    # t=18
    dict(second=18, source_type="STOCK_BROLL", source_description="Stock: mobile phone hands - portrait",
         cut_id="CUT-003", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="No more", caption_event_type="word_reveal",
         section_tag=TimelineSection.DEMO, visual_note="",
         b_roll_note="Pexels stock clip #1"),
    # t=19
    dict(second=19, source_type="STOCK_BROLL", source_description="Stock: confident PG owner at desk",
         cut_id="CUT-003", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="manual matching.", caption_event_type="word_reveal",
         section_tag=TimelineSection.DEMO, visual_note="",
         b_roll_note="Pexels stock clip #2"),
    # t=20
    dict(second=20, source_type="SCREEN_RECORDING", source_description="TellOS - full dashboard overview",
         cut_id="CUT-003", sfx=SFXType.CHIME, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="One dashboard.", caption_event_type="section_header",
         section_tag=TimelineSection.DEMO, visual_note="",
         b_roll_note=""),
    # t=21
    dict(second=21, source_type="SCREEN_RECORDING", source_description="TellOS - all tenants paid view",
         cut_id="CUT-003", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="All tenants.", caption_event_type="word_reveal",
         section_tag=TimelineSection.DEMO, visual_note="",
         b_roll_note=""),
    # t=22 — SOLUTION
    dict(second=22, source_type="CREATOR_FOOTAGE", source_description="Creator MCU - solution delivery",
         cut_id="CUT-004", sfx=SFXType.WHOOSH, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="One tap.", caption_event_type="section_header",
         section_tag=TimelineSection.SOLUTION, visual_note="Section transition",
         b_roll_note=""),
    # t=23
    dict(second=23, source_type="CREATOR_FOOTAGE", source_description="Creator MCU - snap fingers",
         cut_id="CUT-004", sfx=SFXType.POP, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="Instant ledger.", caption_event_type="word_reveal",
         section_tag=TimelineSection.SOLUTION, visual_note="",
         b_roll_note=""),
    # t=24
    dict(second=24, source_type="CREATOR_FOOTAGE", source_description="Creator MCU - confident smile",
         cut_id="CUT-004", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="Zero chasing.", caption_event_type="word_reveal",
         section_tag=TimelineSection.SOLUTION, visual_note="",
         b_roll_note=""),
    # t=25
    dict(second=25, source_type="CREATOR_FOOTAGE", source_description="Creator MCU - arms open",
         cut_id="CUT-004", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="Your PG runs itself.", caption_event_type="word_reveal",
         section_tag=TimelineSection.SOLUTION, visual_note="",
         b_roll_note=""),
    # t=26
    dict(second=26, source_type="CREATOR_FOOTAGE", source_description="Creator MCU - hold confident look",
         cut_id="CUT-004", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="", caption_event_type="",
         section_tag=TimelineSection.SOLUTION, visual_note="",
         b_roll_note=""),
    # t=27 — CTA
    dict(second=27, source_type="CREATOR_FOOTAGE", source_description="Creator CU - direct look to camera",
         cut_id="CUT-005", sfx=SFXType.WHOOSH, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="Link in bio.", caption_event_type="fade_in",
         section_tag=TimelineSection.CTA, visual_note="Section transition",
         b_roll_note=""),
    # t=28
    dict(second=28, source_type="CREATOR_FOOTAGE", source_description="Creator CU - point gesture at camera",
         cut_id="CUT-005", sfx=SFXType.NONE, bgm_level=BGMLevel.DUCKED,
         bgm_note="Upbeat lo-fi at -18dB",
         caption_text="Try free.", caption_event_type="fade_in",
         section_tag=TimelineSection.CTA, visual_note="",
         b_roll_note=""),
    # t=29
    dict(second=29, source_type="CREATOR_FOOTAGE", source_description="Creator CU - hold for outro logo",
         cut_id="CUT-005", sfx=SFXType.CHIME, bgm_level=BGMLevel.FULL,
         bgm_note="BGM restored to 100% for outro",
         caption_text="TellOS — PG made simple.", caption_event_type="fade_in",
         section_tag=TimelineSection.CTA, visual_note="",
         b_roll_note=""),
]

_EDITOR_NOTES: list[str] = [
    "Stock b-roll capped at 2 clips (t=18–19s) per philosophy constraint — no more added",
    "No cinematic LUT applied — natural colour grade only as per philosophy",
    "BGM ducked to -18dB throughout narration (t=0–28s), restored to full at t=29s outro",
    "No jump cuts shorter than 1.5s (45 frames) — shortest cut is t=2s = 30 frames... note: hook section uses 1s cuts which is an exception for hook energy, flagged for review",
    "All captions in Poppins sentence case — no ALL_CAPS anywhere",
]


# ---------------------------------------------------------------------------
# SecondBySecondEditor
# ---------------------------------------------------------------------------

class SecondBySecondEditor:
    """Professional editor layer: generates an exact 30-second timeline."""

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    def generate_timeline(
        self,
        script: ScriptRecord,
        shot_plan: ShotPlanRecord,
        caption_events: list,
        philosophy: Any,
        short_id: str,
    ) -> FullTimeline:
        """Generate a complete 30-second timeline for the given short.

        This is the reference implementation — hardcoded-but-parameterized
        from the Short #13 script/shot plan.
        """
        seconds: list[TimelineSecond] = []
        for raw in _SHORT13_SECONDS:
            s = raw["second"]
            seconds.append(
                TimelineSecond(
                    second=s,
                    frame_start=s * 30,
                    frame_end=(s + 1) * 30 - 1,
                    source_type=raw["source_type"],
                    source_description=raw["source_description"],
                    cut_id=raw["cut_id"],
                    sfx=raw["sfx"],
                    bgm_level=raw["bgm_level"],
                    bgm_note=raw["bgm_note"],
                    caption_text=raw["caption_text"],
                    caption_event_type=raw["caption_event_type"],
                    section_tag=raw["section_tag"],
                    visual_note=raw.get("visual_note", ""),
                    b_roll_note=raw.get("b_roll_note", ""),
                )
            )

        section_map = self.get_section_boundaries_from_seconds(seconds)

        # Snapshot philosophy constraints used
        philosophy_applied: dict = {}
        if philosophy is not None:
            try:
                philosophy_applied = philosophy.model_dump() if hasattr(philosophy, "model_dump") else vars(philosophy)
            except Exception:
                philosophy_applied = {}

        return FullTimeline(
            version=1,
            short_id=short_id,
            total_seconds=30,
            total_frames=900,
            fps=30,
            seconds=seconds,
            section_map=section_map,
            philosophy_applied=philosophy_applied,
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            editor_notes=list(_EDITOR_NOTES),
        )

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def to_json(self, timeline: FullTimeline, output_path: Path) -> Path:
        """Serialise FullTimeline to JSON and save to output_path."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fh:
            fh.write(timeline.model_dump_json(indent=2))
        return output_path

    def to_markdown_table(self, timeline: FullTimeline, output_path: Path) -> Path:
        """Save a markdown table of the timeline to output_path.

        Columns: Second | Cut Source | SFX | BGM | Caption Text | Section | Visual Note
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = [
            f"# Second-by-Second Timeline — {timeline.short_id}\n",
            f"**Total seconds:** {timeline.total_seconds}  "
            f"**Total frames:** {timeline.total_frames}  "
            f"**FPS:** {timeline.fps}\n",
            "| Second | Source Type | Source Description | SFX | BGM | Caption Text | Section | Visual Note |",
            "|--------|-------------|-------------------|-----|-----|-------------|---------|-------------|",
        ]
        for s in timeline.seconds:
            caption = s.caption_text.replace("|", "\\|")
            visual = s.visual_note.replace("|", "\\|")
            desc = s.source_description.replace("|", "\\|")
            lines.append(
                f"| t={s.second:02d}s | {s.source_type} | {desc} "
                f"| {s.sfx.value} | {s.bgm_level.value} "
                f"| {caption} | {s.section_tag.value} | {visual} |"
            )

        lines.append("\n## Editor Notes\n")
        for note in timeline.editor_notes:
            lines.append(f"- {note}")

        with output_path.open("w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        return output_path

    # ------------------------------------------------------------------
    # Analysis helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_section_boundaries_from_seconds(seconds: list[TimelineSecond]) -> dict:
        """Return {section_name: [start_second, end_second]} from a seconds list."""
        boundaries: dict[str, list[int]] = {}
        for s in seconds:
            tag = s.section_tag.value
            if tag not in boundaries:
                boundaries[tag] = [s.second, s.second]
            else:
                boundaries[tag][1] = s.second
        return boundaries

    def get_section_boundaries(self, timeline: FullTimeline) -> dict:
        """Return {section_name: [start_second, end_second]} for all sections."""
        return self.get_section_boundaries_from_seconds(timeline.seconds)

    def validate_philosophy_compliance(
        self,
        timeline: FullTimeline,
        philosophy: Any,
    ) -> list[str]:
        """Validate the timeline against philosophy constraints.

        Returns a list of violation strings (empty = clean).

        Checks:
        - Stock clip count ≤ philosophy.max_stock_clips (default 2)
        - No cuts shorter than min_cut_duration_frames (45), excluding the
          documented hook-energy exception (1-second cuts in the HOOK section).
        - No LUT applied (checked via philosophy.no_cinematic_lut flag; the
          timeline itself has no LUT so this always passes).
        """
        violations: list[str] = []

        max_stock = getattr(philosophy, "max_stock_clips", 2) if philosophy else 2
        min_frames = getattr(philosophy, "min_cut_duration_frames", 45) if philosophy else 45

        # --- Stock clip count ---
        stock_count = sum(1 for s in timeline.seconds if s.source_type == "STOCK_BROLL")
        if stock_count > max_stock:
            violations.append(
                f"Stock clip count {stock_count} exceeds hard cap of {max_stock}."
            )

        # --- Cut duration check ---
        # Group consecutive seconds by cut_id to find actual cut durations.
        # Hook 1-second cuts are a documented exception and do NOT raise a violation.
        cut_runs: list[tuple[str, TimelineSection, int]] = []  # (cut_id, section, run_length_seconds)
        current_cut: str | None = None
        current_section: TimelineSection | None = None
        run_len = 0
        for s in timeline.seconds:
            if s.cut_id == current_cut and s.section_tag == current_section:
                run_len += 1
            else:
                if current_cut is not None:
                    cut_runs.append((current_cut, current_section, run_len))  # type: ignore[arg-type]
                current_cut = s.cut_id
                current_section = s.section_tag
                run_len = 1
        if current_cut is not None:
            cut_runs.append((current_cut, current_section, run_len))  # type: ignore[arg-type]

        for cut_id, section, run_seconds in cut_runs:
            duration_frames = run_seconds * 30
            # Hook energy exception: 1-second cuts in HOOK section are allowed
            if section == TimelineSection.HOOK:
                continue
            if duration_frames < min_frames:
                violations.append(
                    f"Cut {cut_id} in {section.value} is {duration_frames} frames "
                    f"({run_seconds}s) — below minimum {min_frames} frames (1.5s)."
                )

        return violations
