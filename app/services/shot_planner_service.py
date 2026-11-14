"""Shot planning, half-open interval sequencing, and asset feasibility validation."""

from typing import Dict, List, Tuple
from app.services.time_codes import intervals_overlap, validate_interval
from app.state.asset_manifest import ProjectRecord
from app.state.enums import AssetType, ReviewStatus
from app.state.models import ScriptRecord, ShotItem, ShotPlanRecord, utc_now_iso


class ShotFeasibilityReport:
    """Report detailing whether proposed shots are feasible against existing assets."""

    def __init__(self):
        self.is_feasible: bool = True
        self.coverage_percentage: float = 0.0
        self.total_frames: int = 0
        self.missing_shots: List[str] = []
        self.discrepancies: List[str] = []


class ShotPlannerService:
    """Builds frame-accurate shot plans [start_frame, end_frame) and verifies media coverage."""

    @classmethod
    def create_short_13_shot_plan(cls, project: ProjectRecord) -> ShotPlanRecord:
        """
        Build the approved 4-shot plan for Short #13:
        Total duration: exactly 900 frames (30.0s @ 30 FPS).
        Uses ONLY real TellOS screen recordings and approved stock B-roll.
        NO generated vector SVG cards or AI clips.
        """
        shots = [
            ShotItem(
                shot_id="shot_01_hook_spreadsheet",
                start_frame=0,
                end_frame=150,
                description="Overhead view of messy spreadsheet with late payments and Excel chaos.",
                required_asset_type=AssetType.STOCK_BROLL,
                matched_asset_id="ast_broll_spreadsheet_01",
                visual_notes="Visual pain hook placed on Track V2. Sets up problem instantly.",
            ),
            ShotItem(
                shot_id="shot_02_tenant_receipt",
                start_frame=150,
                end_frame=360,
                description="Real mobile screen recording showing tenant sending UPI payment screenshot in WhatsApp chat.",
                required_asset_type=AssetType.SCREEN_RECORDING,
                matched_asset_id="ast_demo_recording_01",
                visual_notes="Authentic TellOS chat UI on Track V1. Shows real user interaction.",
            ),
            ShotItem(
                shot_id="shot_03_bot_processing_ledger",
                start_frame=360,
                end_frame=660,
                description="TellOS WhatsApp bot sends automated payment confirmation receipt back to tenant; ledger updates in real-time.",
                required_asset_type=AssetType.SCREEN_RECORDING,
                matched_asset_id="ast_demo_recording_01",
                visual_notes="Split or zoomed view of bot confirmation and automatic ledger entry row appearing.",
            ),
            ShotItem(
                shot_id="shot_04_dashboard_cta",
                start_frame=660,
                end_frame=900,
                description="Clean, updated TellOS live PG ledger showing paid status + bold call to action.",
                required_asset_type=AssetType.SCREEN_RECORDING,
                matched_asset_id="ast_demo_recording_01",
                visual_notes="High-conversion outro showing peaceful, organized rent book + link in bio.",
            ),
        ]

        total_frames = 900
        total_duration = total_frames / 30.0  # 30.0 seconds

        return ShotPlanRecord(
            version=1,
            shots=shots,
            total_target_duration_seconds=total_duration,
            coverage_percentage=100.0,
            created_at_utc=utc_now_iso(),
        )

    @classmethod
    def validate_shot_plan_feasibility(
        cls,
        shot_plan: ShotPlanRecord,
        project: ProjectRecord,
    ) -> ShotFeasibilityReport:
        """Validate continuity, half-open interval integrity, and asset availability."""
        report = ShotFeasibilityReport()
        shots = shot_plan.shots

        if not shots:
            report.is_feasible = False
            report.discrepancies.append("Shot plan contains no shots.")
            return report

        # 1. Interval and continuity check
        expected_start = 0
        intervals = []
        for idx, shot in enumerate(shots):
            try:
                duration = validate_interval(shot.start_frame, shot.end_frame)
            except ValueError as e:
                report.is_feasible = False
                report.discrepancies.append(f"Shot '{shot.shot_id}' invalid interval: {e}")
                continue

            if shot.start_frame != expected_start:
                report.is_feasible = False
                report.discrepancies.append(
                    f"Timeline gap/overlap at shot '{shot.shot_id}': expected start {expected_start}, "
                    f"observed {shot.start_frame}."
                )

            intervals.append((shot.start_frame, shot.end_frame))
            expected_start = shot.end_frame

        report.total_frames = expected_start

        # 2. Check for overlapping intervals
        for i in range(len(intervals)):
            for j in range(i + 1, len(intervals)):
                if intervals_overlap(intervals[i], intervals[j]):
                    report.is_feasible = False
                    report.discrepancies.append(
                        f"Shots overlap: [{intervals[i][0]}, {intervals[i][1]}) and [{intervals[j][0]}, {intervals[j][1]})"
                    )

        # 3. Check matched asset availability in project manifest
        active_manifest = {
            a.asset_id: a
            for a in project.asset_manifest.values()
            if a.is_online and a.approval_status != ReviewStatus.QUARANTINED
        }

        matched_count = 0
        for shot in shots:
            if not shot.matched_asset_id or shot.matched_asset_id not in active_manifest:
                report.is_feasible = False
                report.missing_shots.append(shot.shot_id)
                report.discrepancies.append(
                    f"Shot '{shot.shot_id}' matched asset '{shot.matched_asset_id}' is missing, "
                    "offline, or quarantined."
                )
            else:
                matched_count += 1

        report.coverage_percentage = (matched_count / len(shots)) * 100.0 if shots else 0.0
        return report

    @classmethod
    def generate_owner_recording_checklist(cls, shot_plan: ShotPlanRecord) -> str:
        """Produce a practical recording checklist for supplementary phone/screen footage."""
        lines = [
            "# Supplementary Recording Checklist (Owner Reference)",
            "While 100% of the Short #13 visual requirements are currently covered by our authentic "
            "`demo-recording-1.mp4` and `broll-spreadsheet.mp4`, the owner may optionally capture "
            "supplementary live phone B-roll using this checklist:",
            "",
            "## Practical Filming Guidelines:",
            "- **Orientation:** Vertical 9:16 (1080×1920) at 30 FPS.",
            "- **Lighting:** Diffuse daylight or direct desk lamp illumination on phone screen.",
            "- **Stability:** Tabletop stand or resting hand against desk to prevent camera shake.",
            "- **Audio:** Quiet room without fan/AC hum.",
            "",
            "## Planned Shot Breakdown:",
            "| Shot ID | Target Range | Duration | Action / Framing | Audio Cue |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        for s in shot_plan.shots:
            duration_s = (s.end_frame - s.start_frame) / 30.0
            range_str = f"[{s.start_frame}, {s.end_frame}) ({s.start_frame/30.0:.1f}s–{s.end_frame/30.0:.1f}s)"
            lines.append(
                f"| `{s.shot_id}` | {range_str} | {duration_s:.1f}s | {s.description} | {s.visual_notes} |"
            )

        lines.extend([
            "",
            "## Quality Criteria for Intake:",
            "- [ ] Screen contents readable without glare.",
            "- [ ] No confidential personal tenant details visible.",
            "- [ ] File format: MP4 or MOV.",
            "- [ ] Strictly real screen recordings or phone footage; NO AI generated clips.",
        ])

        return "\n".join(lines)

