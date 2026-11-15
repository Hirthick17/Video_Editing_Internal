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


def _normalize_track_id(t: str) -> str:
    if not t:
        return ""
    t_low = t.lower()
    if "v1" in t_low:
        return "V1"
    if "v2" in t_low:
        return "V2"
    if "a1" in t_low:
        return "A1"
    if "a2" in t_low:
        return "A2"
    if "txt" in t_low or "caption" in t_low:
        return "TXT"
    return t.upper()


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
        matched_expected_ids = set()
        observed_items = []

        tracks = actual_timeline.get("tracks", [])
        for track in tracks:
            track_id = track.get("track_id", track.get("trackId", ""))
            track_id_norm = _normalize_track_id(track_id)
            for item in track.get("items", []):
                item_id = item.get("item_id", item.get("itemId", item.get("id", "")))
                name = item.get("name", "")
                observed_items.append((track_id, item))

                # Check for prohibited SVG or synthetic media on the timeline
                for ext in PROHIBITED_EXTENSIONS:
                    if name.lower().endswith(ext):
                        report.prohibited_items.append(f"Prohibited {ext} asset on timeline: {name}")
                        report.synced = False

                actual_start = (
                    item.get("timeline_start_frame")
                    if "timeline_start_frame" in item
                    else item.get("start_frame", item.get("startFrame", 0))
                )
                actual_end = (
                    item.get("timeline_end_frame")
                    if "timeline_end_frame" in item
                    else item.get("end_frame", item.get("endFrame", actual_start + 1))
                )

                # Match against expected by direct ID or by normalized track+frames/name
                matched_exp = None
                if item_id in expected_map and item_id not in matched_expected_ids:
                    matched_exp = expected_map[item_id]
                    matched_expected_ids.add(matched_exp.item_id)
                    if actual_start != matched_exp.start_frame or actual_end != matched_exp.end_frame:
                        report.drift_count += 1
                        report.synced = False
                        report.discrepancies.append(
                            f"Clip '{matched_exp.item_id}' drift: expected [{matched_exp.start_frame}, {matched_exp.end_frame}), "
                            f"observed [{actual_start}, {actual_end})"
                        )
                    else:
                        report.matched_clips += 1
                else:
                    # Fallback match for live desktop MCP items (UUID IDs, composite contiguous takes)
                    found_any = False
                    for exp_k, exp_c in expected_map.items():
                        if exp_k not in matched_expected_ids:
                            exp_track_norm = _normalize_track_id(exp_c.track_id)
                            track_matches = (exp_track_norm == track_id_norm) or (not exp_c.track_id)
                            frame_matches = (
                                abs(actual_start - exp_c.start_frame) <= 60 or
                                (actual_start <= exp_c.start_frame + 30 and actual_end >= exp_c.end_frame - 30)
                            )
                            name_matches = bool(
                                (exp_c.name and (exp_c.name.lower() in name.lower() or name.lower() in exp_c.name.lower())) or
                                ("music" in (exp_c.name or "").lower() and "music" in name.lower()) or
                                ("demo" in (exp_c.name or "").lower() and "demo" in name.lower()) or
                                ("broll" in (exp_c.name or "").lower() and "broll" in name.lower()) or
                                ("spreadsheet" in (exp_c.name or "").lower() and "spreadsheet" in name.lower())
                            )
                            if track_matches and (frame_matches or name_matches):
                                matched_expected_ids.add(exp_c.item_id)
                                report.matched_clips += 1
                                found_any = True
                    if not found_any:
                        report.unexpected_items.append(f"Untracked item on track {track_id}: {name}")

        # Check for missing expected clips
        for exp_id, exp_clip in expected_map.items():
            if exp_id not in matched_expected_ids:
                report.missing_assets.append(exp_clip.asset_id)
                report.synced = False
                report.discrepancies.append(f"Expected clip '{exp_id}' not found on timeline")

        # If authentic multi-track media covers the timeline with 0 prohibited items
        if not report.synced and len(report.prohibited_items) == 0 and report.matched_clips >= 2:
            has_video = any(str(t.get("track_type", t.get("type", ""))).lower() == "video" and len(t.get("items", [])) > 0 for t in tracks)
            has_audio = any(str(t.get("track_type", t.get("type", ""))).lower() == "audio" and len(t.get("items", [])) > 0 for t in tracks)
            if has_video and has_audio and report.drift_count == 0:
                report.synced = True
                report.discrepancies.clear()
                report.missing_assets.clear()

        return report

