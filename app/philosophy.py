"""Philosophy Core — hard-constraint editing guardrails for Hirthick's Vision Studio.

Every agent reads these constraints before taking any action.
Violations raise PhilosophyViolationError and must be caught at node boundaries.
"""

from typing import Any
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Custom Exception
# ---------------------------------------------------------------------------

class PhilosophyViolationError(Exception):
    """Raised when an operation violates the editing philosophy constraints."""


# ---------------------------------------------------------------------------
# EditingPhilosophy model
# ---------------------------------------------------------------------------

class EditingPhilosophy(BaseModel):
    # Typography
    typography_first: bool = True          # Always prefer native text over graphic cards
    font_family: str = "Poppins"
    font_weight_primary: int = 700         # Bold for hooks/headers
    font_weight_body: int = 400
    text_case: str = "sentence_case"       # never ALL_CAPS
    caption_style: str = "word_reveal"     # kinetic stagger default

    # Stock footage hard limits
    max_stock_clips: int = 2               # Hard cap: at most 2 stock b-roll clips per short
    stock_sources: list[str] = ["pexels", "pixabay"]  # Only these two allowed

    # Visual guardrails (absolute prohibitions)
    no_cinematic_lut: bool = True          # No colour grading LUT filters
    no_aggressive_jump_cuts: bool = True   # No cuts shorter than 1.5s (45 frames)
    no_svg_cards: bool = True              # Reaffirm zero SVG
    no_ai_diffusion: bool = True           # No AI-generated imagery
    no_zoom_cut_combo: bool = True         # No simultaneous zoom + cut
    min_cut_duration_frames: int = 45      # 1.5s at 30fps minimum cut

    # Audio
    bgm_duck_db: float = -18.0             # BGM ducked to -18dB under narration
    narration_target_wpm: tuple[int, int] = (110, 150)  # WPM range

    # Accent colour
    accent_color_hex: str = "#25D366"      # WhatsApp Green
    accent_color_name: str = "WhatsApp Green"


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------

philosophy = EditingPhilosophy()


# ---------------------------------------------------------------------------
# PhilosophyGuard — class-method validators
# ---------------------------------------------------------------------------

class PhilosophyGuard:
    """Stateless guard that validates operations against the editing philosophy."""

    # --- individual validators ---

    @classmethod
    def validate_stock_clip_count(cls, count: int) -> None:
        """Raise PhilosophyViolationError if count exceeds max_stock_clips (2)."""
        if count > philosophy.max_stock_clips:
            raise PhilosophyViolationError(
                f"Stock clip count {count} exceeds hard cap of "
                f"{philosophy.max_stock_clips}. Philosophy: max_stock_clips={philosophy.max_stock_clips}."
            )

    @classmethod
    def validate_cut_duration(cls, frames: int) -> None:
        """Raise PhilosophyViolationError if cut is shorter than min_cut_duration_frames (45)."""
        if frames < philosophy.min_cut_duration_frames:
            raise PhilosophyViolationError(
                f"Cut duration {frames} frames is below the minimum "
                f"{philosophy.min_cut_duration_frames} frames (1.5 s at 30 fps). "
                "Philosophy: no_aggressive_jump_cuts=True."
            )

    @classmethod
    def validate_no_lut(cls, has_lut: bool) -> None:
        """Raise PhilosophyViolationError if a cinematic LUT filter is applied."""
        if has_lut and philosophy.no_cinematic_lut:
            raise PhilosophyViolationError(
                "Cinematic LUT filter detected. Philosophy: no_cinematic_lut=True — "
                "colour grading LUT filters are strictly prohibited."
            )

    @classmethod
    def validate_no_svg(cls, asset_path: str) -> None:
        """Raise PhilosophyViolationError if the asset is an SVG file."""
        if asset_path.lower().endswith(".svg") and philosophy.no_svg_cards:
            raise PhilosophyViolationError(
                f"SVG asset detected: '{asset_path}'. Philosophy: no_svg_cards=True — "
                "SVG graphic cards are strictly prohibited."
            )

    # --- config accessors ---

    @classmethod
    def get_typography_config(cls) -> dict:
        """Return font/typography settings dict."""
        return {
            "typography_first": philosophy.typography_first,
            "font_family": philosophy.font_family,
            "font_weight_primary": philosophy.font_weight_primary,
            "font_weight_body": philosophy.font_weight_body,
            "text_case": philosophy.text_case,
            "caption_style": philosophy.caption_style,
            "accent_color_hex": philosophy.accent_color_hex,
            "accent_color_name": philosophy.accent_color_name,
        }

    @classmethod
    def get_audio_config(cls) -> dict:
        """Return BGM/narration audio settings dict."""
        return {
            "bgm_duck_db": philosophy.bgm_duck_db,
            "narration_target_wpm_min": philosophy.narration_target_wpm[0],
            "narration_target_wpm_max": philosophy.narration_target_wpm[1],
        }

    # --- bulk check ---

    @classmethod
    def check_all(cls, operations: list[Any]) -> list[str]:
        """Run all guards over a list of operation dicts; return list of violation strings.

        Each operation dict may carry any subset of keys:
            stock_clip_count (int)
            cut_duration_frames (int)
            has_lut (bool)
            asset_path (str)

        Returns an empty list if all guards pass (clean run).
        """
        violations: list[str] = []
        for op in operations:
            if not isinstance(op, dict):
                continue
            # Stock clip count
            count = op.get("stock_clip_count")
            if count is not None:
                try:
                    cls.validate_stock_clip_count(int(count))
                except PhilosophyViolationError as exc:
                    violations.append(str(exc))
            # Cut duration
            frames = op.get("cut_duration_frames")
            if frames is not None:
                try:
                    cls.validate_cut_duration(int(frames))
                except PhilosophyViolationError as exc:
                    violations.append(str(exc))
            # LUT
            has_lut = op.get("has_lut")
            if has_lut is not None:
                try:
                    cls.validate_no_lut(bool(has_lut))
                except PhilosophyViolationError as exc:
                    violations.append(str(exc))
            # SVG
            asset_path = op.get("asset_path", "")
            if asset_path:
                try:
                    cls.validate_no_svg(str(asset_path))
                except PhilosophyViolationError as exc:
                    violations.append(str(exc))
        return violations


default_philosophy = philosophy
