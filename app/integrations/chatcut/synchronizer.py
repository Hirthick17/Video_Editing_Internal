"""Editor state synchronization and drift reconciliation contract."""

from typing import Any, Dict, List
from pydantic import BaseModel, Field

# Prohibited extensions for synthetic/vector graphics
PROHIBITED_EXTENSIONS = {".svg", ".ai", ".eps", ".cdr"}
from app.state.editor_contracts import ClipSpec


class EditorSyncReport(BaseModel):
    """Reconciliation report comparing expected workflow state with observed editor state."""

    synced: bool = True
    matched_clips: int = 0
    drift_count: int = 0
    missing_assets: List[str] = Field(default_factory=list)
    unexpected_items: List[str] = Field(default_factory=list)
    prohibited_items: List[str] = Field(default_factory=list)
    discrepancies: List[str] = Field(default_factory=list)


class EditorStateSynchronizer:
    """Detects discrepancies, unauthorized edits, and prohibited synthetic assets in the timeline."""

    @classmethod
    def reconcile(
        cls,
        expected_clips: List[ClipSpec],
        actual_timeline: Dict[str, Any],
    ) -> EditorSyncReport:
        """Compare expected clips against the timeline observed from ChatCut MCP."""
        report = EditorSyncReport()
        expected_map = {c.item_id: c for c in expected_clips}
        observed_items = []

        tracks = actual_timeline.get("tracks", [])
        for track in tracks:
            for item in track.get("items", []):
                item_id = item.get("item_id", item.get("id", ""))
                name = item.get("name", "")
                observed_items.append((track.get("track_id"), item))

                # Check for prohibited SVG or synthetic media on the timeline
                for ext in PROHIBITED_EXTENSIONS:
                    if name.lower().endswith(ext):
                        report.prohibited_items.append(f"Prohibited {ext} asset on timeline: {name}")
                        report.synced = False

                # Compare against expected
                if item_id in expected_map:
                    exp = expected_map[item_id]
                    actual_start = (
                        item.get("timeline_start_frame")
                        if "timeline_start_frame" in item
                        else item.get("start_frame")
                    )
                    actual_end = (
                        item.get("timeline_end_frame")
                        if "timeline_end_frame" in item
                        else item.get("end_frame")
                    )

                    if actual_start != exp.start_frame or actual_end != exp.end_frame:
                        report.drift_count += 1
                        report.synced = False
                        report.discrepancies.append(
                            f"Clip '{item_id}' drift: expected [{exp.start_frame}, {exp.end_frame}), "
                            f"observed [{actual_start}, {actual_end})"
                        )
                    else:
                        report.matched_clips += 1
                else:
                    report.unexpected_items.append(f"Untracked item on track {track.get('track_id')}: {name}")

        # Check for missing expected clips
        observed_ids = {
            item.get("item_id", item.get("id"))
            for track in tracks
            for item in track.get("items", [])
        }
        for exp_id, exp_clip in expected_map.items():
            if exp_id not in observed_ids:
                report.missing_assets.append(exp_clip.asset_id)
                report.synced = False
                report.discrepancies.append(f"Expected clip '{exp_id}' not found on timeline")

        return report

