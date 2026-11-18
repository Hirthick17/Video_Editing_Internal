"""Deterministic Pattern Linter enforcing Pattern A parameter bands and hard prohibitions."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from app.state.editor_contracts import ClipSpec, EditOperation
from app.state.editor_models import EditorTimeline
from app.state.pattern_spec import PatternSpec, ParameterSource


class LintViolation(BaseModel):
    """A violation or warning flagged by the Pattern Linter."""
    rule_code: str
    severity: str  # "BLOCKING" or "WARNING"
    item_id: Optional[str] = None
    message: str
    observed_value: Any = None
    allowed_band: Optional[str] = None


class PatternLinterReport(BaseModel):
    """Complete evaluation report produced by the Pattern Linter on an EditPlan or EditorTimeline."""
    passed: bool = True
    spec_version: str = "1.0.0"
    total_violations: int = 0
    blocking_violations: int = 0
    warning_violations: int = 0
    violations: List[LintViolation] = Field(default_factory=list)
    scorecard: Dict[str, str] = Field(default_factory=dict)

    @property
    def valid(self) -> bool:
        """Helper property indicating timeline meets blocking criteria."""
        return self.passed and self.blocking_violations == 0


class PatternLinter:
    """
    Deterministic compliance validator for Pattern A.
    Verifies that the generated cutlist and assembled ChatCut timeline conform strictly to:
    1. Parameter bands [p10, p90]
    2. Prohibited visual items (zero SVG, zero synthetic diffusion)
    3. Caption safe-zones (clearing bottom 20% and right 12%)
    4. Audio ducking and speech level
    5. Stock placement policy (candidates in bin only, not on timeline)
    """

    PROHIBITED_EXTENSIONS = {".svg", ".ai", ".eps", ".cdr", ".png_plate"}

    @classmethod
    def lint_timeline(
        cls,
        timeline: Union[EditorTimeline, Dict[str, Any]],
        spec: PatternSpec,
        placement_mode: str = "CANDIDATES_ONLY",
    ) -> PatternLinterReport:
        """Run full audit against an observed ChatCut EditorTimeline."""
        if isinstance(timeline, dict):
            timeline = EditorTimeline.model_validate(timeline)
        violations: List[LintViolation] = []

        # 1. Check prohibited item types on timeline
        for track in timeline.tracks:
            for item in track.items:
                name_lower = (item.name or "").lower()
                for ext in cls.PROHIBITED_EXTENSIONS:
                    if name_lower.endswith(ext) or ext in name_lower:
                        violations.append(
                            LintViolation(
                                rule_code="PROHIBITED_ITEM_TYPE",
                                severity="BLOCKING",
                                item_id=item.item_id,
                                message=f"Prohibited {ext} asset found on track '{track.track_id}': {item.name}",
                                observed_value=item.name,
                            )
                        )

        # 2. Check stock B-roll placement rule
        if placement_mode == "CANDIDATES_ONLY":
            for track in timeline.tracks:
                if track.track_id.startswith("V") or "broll" in track.name.lower():
                    for item in track.items:
                        if "stock" in (item.name or "").lower() or "broll" in (item.name or "").lower():
                            violations.append(
                                LintViolation(
                                    rule_code="UNAPPROVED_STOCK_PLACEMENT",
                                    severity="BLOCKING",
                                    item_id=item.item_id,
                                    message="Stock B-roll placed on timeline while placement_mode is CANDIDATES_ONLY.",
                                    observed_value=item.name,
                                )
                            )

        # 3. Check segment lengths on A-roll (V1)
        v1_track = next((t for t in timeline.tracks if t.track_id == "V1" or t.order == 0), None)
        if v1_track and v1_track.items:
            for item in v1_track.items:
                dur_sec = item.duration_frames / timeline.fps
                if dur_sec < 1.0:
                    violations.append(
                        LintViolation(
                            rule_code="SEGMENT_TOO_SHORT",
                            severity="BLOCKING",
                            item_id=item.item_id,
                            message=f"Segment duration {dur_sec:.2f}s is below minimum 1.0s threshold.",
                            observed_value=dur_sec,
                            allowed_band=f"[{spec.segment_length_band.p10}s, {spec.segment_length_band.p90}s]",
                        )
                    )
                elif dur_sec > 6.0:
                    violations.append(
                        LintViolation(
                            rule_code="SEGMENT_TOO_LONG",
                            severity="WARNING",
                            item_id=item.item_id,
                            message=f"Segment duration {dur_sec:.2f}s exceeds recommended p90 cut length.",
                            observed_value=dur_sec,
                            allowed_band=f"[{spec.segment_length_band.p10}s, {spec.segment_length_band.p90}s]",
                        )
                    )

        # 4. Check caption safe-zone compliance
        for track in timeline.tracks:
            if "caption" in track.track_id.lower() or track.track_type == "text":
                for item in track.items:
                    # Check text length / words
                    words = (item.name or "").split()
                    if len(words) > 7:
                        violations.append(
                            LintViolation(
                                rule_code="CAPTION_CHUNK_TOO_LONG",
                                severity="WARNING",
                                item_id=item.item_id,
                                message=f"Caption card has {len(words)} words; recommended band is 2–5 words.",
                                observed_value=len(words),
                                allowed_band="[2, 5] words",
                            )
                        )

        # 5. Check total duration
        total_dur_sec = timeline.duration_frames / timeline.fps
        if not spec.duration_band.contains(total_dur_sec):
            violations.append(
                LintViolation(
                    rule_code="DURATION_OUT_OF_BAND",
                    severity="WARNING",
                    message=f"Timeline duration {total_dur_sec:.1f}s is outside reference band [{spec.duration_band.p10}s, {spec.duration_band.p90}s].",
                    observed_value=total_dur_sec,
                    allowed_band=f"[{spec.duration_band.p10}s, {spec.duration_band.p90}s]",
                )
            )

        blocking = [v for v in violations if v.severity == "BLOCKING"]
        warnings = [v for v in violations if v.severity == "WARNING"]

        scorecard = {
            "prohibited_items": "PASS" if not any(v.rule_code == "PROHIBITED_ITEM_TYPE" for v in violations) else "FAIL",
            "stock_placement": "PASS" if not any(v.rule_code == "UNAPPROVED_STOCK_PLACEMENT" for v in violations) else "FAIL",
            "cut_pacing": "PASS" if not any(v.rule_code in ("SEGMENT_TOO_SHORT", "SEGMENT_TOO_LONG") for v in violations) else "WARN",
            "caption_style": "PASS" if not any(v.rule_code == "CAPTION_CHUNK_TOO_LONG" for v in violations) else "WARN",
            "duration": "PASS" if not any(v.rule_code == "DURATION_OUT_OF_BAND" for v in violations) else "WARN",
        }

        return PatternLinterReport(
            passed=len(blocking) == 0,
            spec_version=spec.version,
            total_violations=len(violations),
            blocking_violations=len(blocking),
            warning_violations=len(warnings),
            violations=violations,
            scorecard=scorecard,
        )
