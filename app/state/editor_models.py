"""Strongly typed ChatCut editor models and response normalizers."""

import hashlib
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

from app.state.editor_contracts import ClipSpec, TimelineSpec


class EditorItem(BaseModel):
    """Normalized representation of a single timeline item/clip in ChatCut."""

    item_id: str
    track_id: str
    asset_id: Optional[str] = None
    name: str = ""
    item_type: str = "video"  # "video", "audio", "text", "effect"
    timeline_start_frame: int = Field(..., ge=0)
    timeline_end_frame: int = Field(..., gt=0)
    source_in_frame: int = Field(default=0, ge=0)
    source_out_frame: Optional[int] = None
    volume: float = Field(default=1.0, ge=0.0, le=2.0)
    properties: Dict[str, Any] = Field(default_factory=dict)

    @property
    def duration_frames(self) -> int:
        return self.timeline_end_frame - self.timeline_start_frame

    @model_validator(mode="after")
    def validate_interval(self) -> "EditorItem":
        if self.timeline_end_frame <= self.timeline_start_frame:
            raise ValueError(
                f"timeline_end_frame ({self.timeline_end_frame}) must exceed "
                f"timeline_start_frame ({self.timeline_start_frame})"
            )
        return self

    def to_clip_spec(self) -> ClipSpec:
        """Convert normalized EditorItem to ClipSpec contract."""
        return ClipSpec(
            item_id=self.item_id,
            track_id=self.track_id,
            asset_id=self.asset_id or "",
            start_frame=self.timeline_start_frame,
            end_frame=self.timeline_end_frame,
            source_in_frame=self.source_in_frame,
            source_out_frame=self.source_out_frame,
            volume=self.volume,
            name=self.name,
        )


class EditorTrack(BaseModel):
    """Normalized representation of a ChatCut timeline track."""

    track_id: str
    name: str = ""
    track_type: str = "video"  # "video" or "audio"
    order: int = 0
    items: List[EditorItem] = Field(default_factory=list)
    muted: bool = False
    locked: bool = False


class EditorTimeline(BaseModel):
    """Normalized snapshot of a ChatCut timeline."""

    timeline_id: str
    project_id: str
    width: int = 1080
    height: int = 1920
    fps_num: int = 30
    fps_den: int = 1
    duration_frames: int = 0
    tracks: List[EditorTrack] = Field(default_factory=list)
    revision_hash: str = ""
    saved_at: Optional[str] = None

    @property
    def fps(self) -> float:
        return self.fps_num / float(self.fps_den)

    def compute_revision_hash(self) -> str:
        """Generate a deterministic SHA-256 hash representing current timeline layout."""
        layout_elements = []
        for track in sorted(self.tracks, key=lambda t: t.order):
            for item in sorted(track.items, key=lambda i: i.timeline_start_frame):
                layout_elements.append(
                    f"{track.track_id}:{item.item_id}:{item.asset_id}:"
                    f"{item.timeline_start_frame}-{item.timeline_end_frame}"
                )
        raw_repr = "|".join(layout_elements)
        return hashlib.sha256(raw_repr.encode("utf-8")).hexdigest()[:16]


class EditorProject(BaseModel):
    """Normalized representation of a ChatCut project."""

    project_id: str
    name: str
    timeline_ids: List[str] = Field(default_factory=list)
    active_timeline_id: Optional[str] = None
    editor_version: Optional[str] = "0.9.12.0"
    project_path: Optional[str] = None


# ============================================================================
# Response Normalizer Functions
# ============================================================================

def normalize_chatcut_project(raw: Dict[str, Any]) -> EditorProject:
    """Normalize raw ChatCut target_project or list_projects dictionary into EditorProject."""
    if isinstance(raw, dict) and "content" in raw and isinstance(raw["content"], list):
        for c in raw["content"]:
            if isinstance(c, dict) and c.get("type") == "text":
                try:
                    import json
                    parsed = json.loads(c["text"])
                    if isinstance(parsed, dict) and ("projectId" in parsed or "project_id" in parsed):
                        raw = parsed
                        break
                except Exception:
                    pass

    project_id = raw.get("projectId") or raw.get("project_id") or raw.get("id", "")
    name = raw.get("name") or raw.get("projectName") or "Untitled Project"
    active_tl = raw.get("activeTimelineId") or raw.get("active_timeline_id") or raw.get("timelineId")
    timeline_ids = raw.get("timelineIds") or raw.get("timeline_ids") or []
    if active_tl and active_tl not in timeline_ids:
        timeline_ids.append(active_tl)

    return EditorProject(
        project_id=str(project_id),
        name=str(name),
        timeline_ids=[str(tid) for tid in timeline_ids],
        active_timeline_id=str(active_tl) if active_tl else None,
        editor_version=raw.get("editorVersion", "0.9.12.0"),
        project_path=raw.get("projectPath"),
    )


def parse_chatcut_text_preview(text: str, project_id: str = "") -> Dict[str, Any]:
    """Parse text output from ChatCut MCP preview_timeline into structured dict."""
    import re
    lines = [line.rstrip() for line in text.strip().splitlines() if line.strip()]
    header = lines[0] if lines else ""
    tl_id_m = re.search(r'Timeline\s+"[^"]*"\s+([0-9a-fA-F-]+)', header)
    timeline_id = tl_id_m.group(1) if tl_id_m else ""

    dim_m = re.search(r'(\d+)x(\d+)', header)
    width = int(dim_m.group(1)) if dim_m else 1080
    height = int(dim_m.group(2)) if dim_m else 1920

    fps_m = re.search(r'(\d+)fps', header)
    fps = int(fps_m.group(1)) if fps_m else 30

    dur_m = re.search(r'(\d+)f\s*\(', header)
    duration_frames = int(dur_m.group(1)) if dur_m else 900

    tracks = []
    current_track = None

    track_header_pattern = re.compile(r'^([VvAa]\d+|[A-Za-z0-9_-]+)\s+([0-9a-fA-F]+)\s+(video|audio)\s+order=(\d+)')
    item_pattern = re.compile(r'^\s+\[(\d+),(\d+)\)\s+(video|audio)\s+([0-9a-fA-F]+)\s+placed\s+"([^"]*)"\s+asset\s+([0-9a-fA-F]+)')

    for line in lines[1:]:
        t_match = track_header_pattern.match(line)
        if t_match:
            alias, t_id, t_type, order = t_match.groups()
            current_track = {
                "trackId": alias,
                "name": alias,
                "type": t_type,
                "order": int(order),
                "items": []
            }
            tracks.append(current_track)
            continue

        i_match = item_pattern.match(line)
        if i_match and current_track:
            start_f, end_f, i_type, item_id, name, asset_id = i_match.groups()
            current_track["items"].append({
                "itemId": item_id,
                "assetId": asset_id,
                "name": name,
                "type": i_type,
                "startFrame": int(start_f),
                "endFrame": int(end_f),
                "trackId": current_track["trackId"],
            })

    return {
        "timelineId": timeline_id,
        "projectId": project_id,
        "width": width,
        "height": height,
        "fps": fps,
        "durationFrames": duration_frames,
        "tracks": tracks
    }


def normalize_chatcut_timeline(raw: Any, project_id: str = "") -> EditorTimeline:
    """Normalize raw ChatCut preview_timeline or timeline JSON into EditorTimeline."""
    if isinstance(raw, str):
        raw = parse_chatcut_text_preview(raw, project_id=project_id)
    elif isinstance(raw, dict):
        if "content" in raw and isinstance(raw["content"], list):
            for c in raw["content"]:
                if isinstance(c, dict) and c.get("type") == "text" and "Timeline " in c.get("text", ""):
                    raw = parse_chatcut_text_preview(c["text"], project_id=project_id)
                    break
        elif "tracks" not in raw and "text" in raw:
            raw = parse_chatcut_text_preview(raw["text"], project_id=project_id)

    timeline_id = str(raw.get("timelineId") or raw.get("timeline_id") or raw.get("id", ""))
    proj_id = str(raw.get("projectId") or raw.get("project_id") or project_id)
    width = int(raw.get("width") or 1080)
    height = int(raw.get("height") or 1920)

    # Frame rate extraction
    fps_raw = raw.get("fps") or 30
    if isinstance(fps_raw, dict):
        fps_num = int(fps_raw.get("num", 30))
        fps_den = int(fps_raw.get("den", 1))
    elif isinstance(fps_raw, (int, float)):
        fps_num = int(fps_raw)
        fps_den = 1
    else:
        fps_num = 30
        fps_den = 1

    tracks: List[EditorTrack] = []
    raw_tracks = raw.get("tracks") or []

    for order_idx, t in enumerate(raw_tracks):
        track_id = str(t.get("trackId") or t.get("track_id") or t.get("id", f"T{order_idx}"))
        track_name = str(t.get("name") or t.get("trackName") or f"Track {order_idx}")
        track_type = str(t.get("type") or t.get("trackType") or "video").lower()
        muted = bool(t.get("muted", False))
        locked = bool(t.get("locked", False))

        items: List[EditorItem] = []
        raw_items = t.get("items") or t.get("clips") or []

        for item in raw_items:
            item_id = str(item.get("itemId") or item.get("item_id") or item.get("id", ""))
            asset_id = item.get("assetId") or item.get("asset_id")
            name = str(item.get("name") or "")
            item_type = str(item.get("type") or item.get("itemType") or track_type).lower()

            start_f = int(item.get("startFrame") or item.get("start_frame") or item.get("start") or 0)
            end_f = int(
                item.get("endFrame")
                or item.get("end_frame")
                or item.get("end")
                or (start_f + int(item.get("duration", 30)))
            )

            # Enforce half-open interval constraint
            if end_f <= start_f:
                end_f = start_f + 1

            source_in = int(item.get("sourceInFrame") or item.get("source_in") or 0)
            source_out = item.get("sourceOutFrame") or item.get("source_out")
            volume = float(item.get("volume", 1.0))

            items.append(
                EditorItem(
                    item_id=item_id,
                    track_id=track_id,
                    asset_id=str(asset_id) if asset_id else None,
                    name=name,
                    item_type=item_type,
                    timeline_start_frame=start_f,
                    timeline_end_frame=end_f,
                    source_in_frame=source_in,
                    source_out_frame=int(source_out) if source_out is not None else None,
                    volume=volume,
                    properties=item.get("properties", {}),
                )
            )

        tracks.append(
            EditorTrack(
                track_id=track_id,
                name=track_name,
                track_type=track_type,
                order=order_idx,
                items=items,
                muted=muted,
                locked=locked,
            )
        )

    duration_frames = int(raw.get("durationFrames") or raw.get("duration_frames") or 0)
    if duration_frames == 0 and tracks:
        for t in tracks:
            for i in t.items:
                if i.timeline_end_frame > duration_frames:
                    duration_frames = i.timeline_end_frame

    timeline = EditorTimeline(
        timeline_id=timeline_id,
        project_id=proj_id,
        width=width,
        height=height,
        fps_num=fps_num,
        fps_den=fps_den,
        duration_frames=duration_frames,
        tracks=tracks,
        saved_at=raw.get("savedAt") or raw.get("saved_at"),
    )
    timeline.revision_hash = timeline.compute_revision_hash()
    return timeline

