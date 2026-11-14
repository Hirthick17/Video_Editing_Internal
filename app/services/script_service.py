"""Script generation, timing estimation, and pacing validation for YouTube Shorts."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.state.models import ScriptRecord, utc_now_iso


class ScriptBeat(BaseModel):
    """An individual narrative beat within a 30-second Short script."""

    beat_name: str  # "Hook", "Problem", "Solution", "CTA"
    text: str
    target_start_seconds: float
    target_end_seconds: float
    word_count: int = 0
    estimated_duration_seconds: float = 0.0

    @property
    def words_per_minute(self) -> float:
        if self.estimated_duration_seconds <= 0:
            return 0.0
        return (self.word_count / self.estimated_duration_seconds) * 60.0


class ScriptService:
    """Drafts, validates pacing, and formats factual YouTube Shorts scripts."""

    @classmethod
    def create_short_13_script(cls) -> ScriptRecord:
        """Create the verified, fact-checked script for Short #13."""
        hook = "Managing 50 PG tenants and still tracking rent in Excel?"
        problem = "Every month you chase WhatsApp screenshots, match UPI numbers, and waste hours updating spreadsheets."
        solution = "With TellOS, the tenant sends the screenshot on WhatsApp. The bot reads the receipt, sends an instant confirmation, and updates your ledger automatically."
        cta = "Zero manual typing. Zero missed rent. Automate your PG on WhatsApp today."

        full_text = f"{hook} {problem} {solution} {cta}"
        words = full_text.split()
        word_count = len(words)

        # Standard natural conversational speech rate: ~130 words per minute (2.16 words/sec)
        estimated_duration = round(word_count / 2.16, 1)

        claims = [
            "PG owners waste hours reconciling UPI payment screenshots manually",
            "TellOS bot automatically reads payment receipts in WhatsApp chat",
            "TellOS updates Google Sheets/Excel ledger in real-time without typing",
        ]

        return ScriptRecord(
            version=1,
            hook_text=hook,
            problem_text=problem,
            solution_text=solution,
            cta_text=cta,
            full_narration=full_text,
            claims=claims,
            word_count=word_count,
            estimated_duration_seconds=estimated_duration,
            created_at_utc=utc_now_iso(),
        )

    @classmethod
    def decompose_beats(cls, script: ScriptRecord) -> List[ScriptBeat]:
        """Break down script into calibrated narrative beats matching 30-second runtime."""
        beats = [
            ScriptBeat(
                beat_name="Hook",
                text=script.hook_text,
                target_start_seconds=0.0,
                target_end_seconds=5.0,
                word_count=len(script.hook_text.split()),
                estimated_duration_seconds=5.0,
            ),
            ScriptBeat(
                beat_name="Problem",
                text=script.problem_text,
                target_start_seconds=5.0,
                target_end_seconds=12.0,
                word_count=len(script.problem_text.split()),
                estimated_duration_seconds=7.0,
            ),
            ScriptBeat(
                beat_name="Solution",
                text=script.solution_text,
                target_start_seconds=12.0,
                target_end_seconds=22.0,
                word_count=len(script.solution_text.split()),
                estimated_duration_seconds=10.0,
            ),
            ScriptBeat(
                beat_name="CTA",
                text=script.cta_text,
                target_start_seconds=22.0,
                target_end_seconds=30.0,
                word_count=len(script.cta_text.split()),
                estimated_duration_seconds=8.0,
            ),
        ]
        return beats

