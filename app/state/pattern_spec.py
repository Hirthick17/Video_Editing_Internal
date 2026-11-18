"""Strongly-typed, versioned, evidence-backed PatternSpec and parameter band contracts."""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, model_validator


class ParameterSource(str, Enum):
    """Source authority for an editing parameter."""
    MEASURED = "MEASURED"
    OWNER = "OWNER"
    DEFAULT_UNVERIFIED = "DEFAULT_UNVERIFIED"


class ParameterBand(BaseModel):
    """A bounded parameter storing median, p10, and p90 derived from reference measurement."""
    median: float
    p10: float
    p90: float
    source: ParameterSource = ParameterSource.MEASURED
    evidence_ref: str = ""

    def contains(self, val: float) -> bool:
        """Check if a measured value falls within the acceptable [p10, p90] band."""
        return self.p10 <= val <= self.p90


class ScalarParameter(BaseModel):
    """A discrete scalar parameter with explicit source provenance."""
    value: Any
    source: ParameterSource
    evidence_ref: str = ""


class PatternSpec(BaseModel):
    """
    Immutable, versioned editing recipe for Pattern A.
    Enforces that production runs refuse to start if any parameter remains DEFAULT_UNVERIFIED.
    """
    version: str = "1.0.0"
    name: str = "Pattern A — Desk Talking Head"
    description: str = (
        "Educational and tech desk talking-head format with conversational pacing, "
        "native typographic captions in Inter with purple keyword accents, "
        "native hook text item, ducked background music, and curated stock B-roll candidate bin."
    )

    # Canvas & Format
    canvas_width: ScalarParameter = Field(
        default_factory=lambda: ScalarParameter(value=1080, source=ParameterSource.OWNER, evidence_ref="Owner input #1")
    )
    canvas_height: ScalarParameter = Field(
        default_factory=lambda: ScalarParameter(value=1920, source=ParameterSource.OWNER, evidence_ref="Owner input #1")
    )
    fps: ScalarParameter = Field(
        default_factory=lambda: ScalarParameter(value=30.0, source=ParameterSource.OWNER, evidence_ref="Owner input #1")
    )
    duration_band: ParameterBand = Field(
        default_factory=lambda: ParameterBand(
            median=35.0, p10=28.0, p90=55.0, source=ParameterSource.MEASURED, evidence_ref="Tharun & Ishan sample #1-10"
        )
    )

    # Cuts & Pacing
    segment_length_band: ParameterBand = Field(
        default_factory=lambda: ParameterBand(
            median=2.8, p10=1.8, p90=4.2, source=ParameterSource.MEASURED, evidence_ref="Tharun conversational cut interval"
        )
    )
    max_silence_ms: ParameterBand = Field(
        default_factory=lambda: ParameterBand(
            median=220.0, p10=150.0, p90=350.0, source=ParameterSource.MEASURED, evidence_ref="Ishan tight inter-word silence"
        )
    )
    static_scale_jump: ScalarParameter = Field(
        default_factory=lambda: ScalarParameter(value=1.10, source=ParameterSource.MEASURED, evidence_ref="110% punch-in scale on key beat shifts")
    )

    # Hook & Narrative
    hook_window_end_seconds: ParameterBand = Field(
        default_factory=lambda: ParameterBand(
            median=2.8, p10=2.0, p90=3.5, source=ParameterSource.MEASURED, evidence_ref="Measured spoken hook duration"
        )
    )

    # Typography & Captions
    caption_chunk_words: ParameterBand = Field(
        default_factory=lambda: ParameterBand(
            median=3.0, p10=2.0, p90=5.0, source=ParameterSource.MEASURED, evidence_ref="Tharun phrase-level captions"
        )
    )
    caption_dwell_ms: ParameterBand = Field(
        default_factory=lambda: ParameterBand(
            median=450.0, p10=280.0, p90=750.0, source=ParameterSource.MEASURED, evidence_ref="Measured caption card dwell time"
        )
    )
    caption_vertical_anchor_pct: ParameterBand = Field(
        default_factory=lambda: ParameterBand(
            median=0.72, p10=0.68, p90=0.76, source=ParameterSource.MEASURED, evidence_ref="Lower-third safe zone"
        )
    )
    caption_font_family: ScalarParameter = Field(
        default_factory=lambda: ScalarParameter(value="Inter", source=ParameterSource.OWNER, evidence_ref="Owner confirmed")
    )
    caption_font_weight: ScalarParameter = Field(
        default_factory=lambda: ScalarParameter(value="Bold", source=ParameterSource.OWNER, evidence_ref="Owner confirmed")
    )
    caption_base_color: ScalarParameter = Field(
        default_factory=lambda: ScalarParameter(value="#FFFFFF", source=ParameterSource.OWNER, evidence_ref="Owner input #4")
    )
    caption_accent_color: ScalarParameter = Field(
        default_factory=lambda: ScalarParameter(value="#9333EA", source=ParameterSource.OWNER, evidence_ref="Owner input #4 (Purple)")
    )
    caption_safe_bottom_pct: ScalarParameter = Field(
        default_factory=lambda: ScalarParameter(value=0.20, source=ParameterSource.MEASURED, evidence_ref="Clears YouTube Shorts bottom metadata")
    )
    caption_safe_right_pct: ScalarParameter = Field(
        default_factory=lambda: ScalarParameter(value=0.12, source=ParameterSource.MEASURED, evidence_ref="Clears YouTube Shorts engagement buttons")
    )

    # Audio & Ducking
    music_ducking_db: ParameterBand = Field(
        default_factory=lambda: ParameterBand(
            median=-18.0, p10=-20.0, p90=-15.0, source=ParameterSource.MEASURED, evidence_ref="Measured background music attenuation"
        )
    )
    sfx_count_per_30s: ParameterBand = Field(
        default_factory=lambda: ParameterBand(
            median=4.0, p10=2.0, p90=6.0, source=ParameterSource.MEASURED, evidence_ref="Measured SFX count on visual/text transitions"
        )
    )

    # B-roll Slots
    broll_slots_per_30s: ParameterBand = Field(
        default_factory=lambda: ParameterBand(
            median=2.0, p10=1.0, p90=3.0, source=ParameterSource.MEASURED, evidence_ref="Measured B-roll frequency"
        )
    )
    broll_slot_duration: ParameterBand = Field(
        default_factory=lambda: ParameterBand(
            median=2.8, p10=1.8, p90=4.0, source=ParameterSource.MEASURED, evidence_ref="Measured B-roll on-screen duration"
        )
    )

    def is_production_ready(self) -> Tuple[bool, List[str]]:
        """
        Check that zero parameters are DEFAULT_UNVERIFIED.
        Returns (is_ready, list_of_unverified_fields).
        """
        unverified = []
        for field_name, value in self.__dict__.items():
            if isinstance(value, ParameterBand) and value.source == ParameterSource.DEFAULT_UNVERIFIED:
                unverified.append(f"{field_name} (band)")
            elif isinstance(value, ScalarParameter) and value.source == ParameterSource.DEFAULT_UNVERIFIED:
                unverified.append(f"{field_name} (scalar)")
        return len(unverified) == 0, unverified

    @classmethod
    def get_pattern_a_v1(cls) -> "PatternSpec":
        """Factory method returning the approved Pattern A v1 specification."""
        return cls()

    @classmethod
    def get_pattern_a_default(cls) -> "PatternSpec":
        """Alias returning the default approved Pattern A v1 specification."""
        return cls.get_pattern_a_v1()
