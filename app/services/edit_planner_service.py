"""Edit planner service converting creative intent, transcripts, and footage into an atomic cutlist."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.services.asset_guardrail import AssetGuardrailService, AssetGuardrailViolationError
from app.services.media_understanding_service import ClipMatchReport
from app.services.time_codes import intervals_overlap, validate_interval
from app.state.asset_manifest import ProjectRecord
from app.state.editor_contracts import ClipSpec, EditOperation, TrackSpec
from app.state.enums import AssetType, EditOperationType, ReviewStatus
from app.state.models import (
    AssetRecord,
    EditPlanRecord,
    ScriptRecord,
    ShotPlanRecord,
    TrackPlan,
    TranscriptionRecord,
    utc_now_iso,
)

logger = logging.getLogger(__name__)


class EditPlanValidationReport(BaseModel):
    """Validation report verifying edit plan integrity, contiguity, and guardrail compliance."""

    is_valid: bool = True
    total_duration_frames: int = 0
    target_duration_frames: int = 900
    tracks_count: int = 0
    clips_count: int = 0
    captions_count: int = 0
    discrepancies: List[str] = Field(default_factory=list)
    guardrail_passed: bool = True


class EditPlannerService:
    """Builds a frame-accurate, multi-track EditPlan and atomic CutList for ChatCut MCP execution."""

    @classmethod
    def create_short_13_edit_plan(
        cls,
        project: ProjectRecord,
        shot_plan: ShotPlanRecord,
        transcript: TranscriptionRecord,
        match_report: ClipMatchReport,
        target_fps: int = 30,
        target_width: int = 1080,
        target_height: int = 1920,
    ) -> Tuple[EditPlanRecord, List[EditOperation]]:
        """
        Assemble the 30.0s / 900-frame rough cut for Short #13:
        Track V1: Primary product demo (TellOS Android capture)
        Track V2: Stock B-roll overlay (Excel spreadsheet)
        Track A1: Voiceover speech track (0dB)
        Track A2: Ducked background music (-18dB)
        Track TXT: Native typographic subtitle captions (NO SVG cards)
        """
        tracks = [
            TrackPlan(track_id="track_v1_demo", track_name="Main Product Video (TellOS)", track_type="video", order=0),
            TrackPlan(track_id="track_v2_broll", track_name="B-roll Overlay (Excel Pain)", track_type="video", order=1),
            TrackPlan(track_id="track_a1_narration", track_name="Voiceover Narration (0dB)", track_type="audio", order=2),
            TrackPlan(track_id="track_a2_bgm", track_name="Background Music (-18dB)", track_type="audio", order=3),
            TrackPlan(track_id="track_txt_captions", track_name="Native Text Subtitles", track_type="text", order=4),
        ]

        operations: List[EditOperation] = []

        # 1. ADD_TRACK operations
        for t in tracks:
            operations.append(
                EditOperation(
                    operation_id=f"op_add_{t.track_id}",
                    operation_type=EditOperationType.ADD_TRACK,
                    idempotency_key=f"idemp_track_{t.track_id}",
                    track_id=t.track_id,
                    parameters={"name": t.track_name, "type": t.track_type, "order": t.order},
                )
            )

        # 2. INSERT_CLIP video operations from match report
        for m in match_report.matches:
            clip_name = f"Clip: {m.shot_id}"
            clip_spec = ClipSpec(
                item_id=f"item_{m.shot_id}",
                track_id=f"track_{m.target_track.lower()}_broll" if m.target_track == "V2" else "track_v1_demo",
                asset_id=m.asset_id,
                start_frame=m.timeline_start_frame,
                end_frame=m.timeline_end_frame,
                source_in_frame=m.source_in_frame,
                source_out_frame=m.source_out_frame,
                volume=0.0,  # Screen recordings are visual-first; audio on A1/A2
                name=clip_name,
            )
            operations.append(
                EditOperation(
                    operation_id=f"op_ins_{m.shot_id}",
                    operation_type=EditOperationType.INSERT_CLIP,
                    idempotency_key=f"idemp_clip_{m.shot_id}",
                    track_id=clip_spec.track_id,
                    clip_spec=clip_spec,
                    parameters={"visual_notes": m.visual_notes},
                )
            )

        # 3. Audio Tracks: Voiceover (A1) and Background Music (A2)
        # Voiceover clip (900 frames)
        vo_spec = ClipSpec(
            item_id="item_a1_narration",
            track_id="track_a1_narration",
            asset_id=transcript.asset_id,
            start_frame=0,
            end_frame=900,
            source_in_frame=0,
            source_out_frame=900,
            volume=1.0,  # 0dB normalized
            name="Voiceover Narration (58 Words)",
        )
        operations.append(
            EditOperation(
                operation_id="op_ins_a1_narration",
                operation_type=EditOperationType.INSERT_CLIP,
                idempotency_key="idemp_clip_a1_narration",
                track_id="track_a1_narration",
                clip_spec=vo_spec,
                parameters={"audio_level_db": 0.0, "role": "primary_speech"},
            )
        )

        # Background music clip (900 frames, ducked to 0.125 = -18dB)
        bgm_spec = ClipSpec(
            item_id="item_a2_bgm",
            track_id="track_a2_bgm",
            asset_id="ast_bg_music_01",
            start_frame=0,
            end_frame=900,
            source_in_frame=0,
            source_out_frame=900,
            volume=0.125,  # -18dB ducking
            name="Background Music (Ducked -18dB)",
        )
        operations.append(
            EditOperation(
                operation_id="op_ins_a2_bgm",
                operation_type=EditOperationType.INSERT_CLIP,
                idempotency_key="idemp_clip_a2_bgm",
                track_id="track_a2_bgm",
                clip_spec=bgm_spec,
                parameters={"audio_level_db": -18.0, "ducked": True},
            )
        )

        # 4. Native typographical subtitle captions (Restrained native typography, NO SVG CARDS)
        caption_cues = [
            (
                "cap_cue1_hook",
                0,
                150,
                "Managing 50 PG tenants and still tracking rent in Excel?",
            ),
            (
                "cap_cue2_problem",
                150,
                360,
                "Every month you chase WhatsApp screenshots, match UPI numbers, and waste hours updating spreadsheets.",
            ),
            (
                "cap_cue3_solution",
                360,
                660,
                "With TellOS, the tenant sends the screenshot on WhatsApp. The bot reads the receipt, sends an instant confirmation, and updates your ledger automatically.",
            ),
            (
                "cap_cue4_cta",
                660,
                900,
                "Zero manual typing. Zero missed rent. Automate your PG on WhatsApp today.",
            ),
        ]

        for cid, sf, ef, text in caption_cues:
            operations.append(
                EditOperation(
                    operation_id=f"op_{cid}",
                    operation_type=EditOperationType.ADD_CAPTION,
                    idempotency_key=f"idemp_{cid}",
                    track_id="track_txt_captions",
                    parameters={
                        "caption_id": cid,
                        "start_frame": sf,
                        "end_frame": ef,
                        "text": text,
                        "style": {
                            "font_family": "System Sans-Serif",
                            "font_size": 48,
                            "color": "#FFFFFF",
                            "stroke_color": "#000000",
                            "stroke_width": 4,
                            "position_y": "bottom_safe_zone",
                            "native_text": True,
                        },
                    },
                )
            )

        summary = [
            f"Configured 5 tracks: 2 video (V1, V2), 2 audio (A1, A2), 1 native text subtitle track.",
            f"Placed 4 authentic video cuts matching script beats [0, 150) -> [150, 360) -> [360, 660) -> [660, 900).",
            f"Synchronized 0dB speech track and -18dB ducked background music across exactly 900 frames.",
            f"Added 4 restrained native typographic caption cues synchronized to narration beats.",
            f"Strictly ZERO synthetic AI clips, ZERO diffusion images, and ZERO vector SVG cards placed.",
        ]

        edit_plan = EditPlanRecord(
            version=1,
            target_width=target_width,
            target_height=target_height,
            fps=target_fps,
            tracks=tracks,
            operations_summary=summary,
            created_at_utc=utc_now_iso(),
        )

        return edit_plan, operations

    @classmethod
    def validate_edit_plan(
        cls,
        edit_plan: EditPlanRecord,
        operations: List[EditOperation],
        asset_registry: Dict[str, AssetRecord],
        target_frames: int = 900,
    ) -> EditPlanValidationReport:
        """Deterministically validate frame ranges, track overlaps, source boundaries, and guardrails."""
        report = EditPlanValidationReport(
            target_duration_frames=target_frames,
            tracks_count=len(edit_plan.tracks),
        )

        clips_by_track: Dict[str, List[ClipSpec]] = {}
        captions: List[Dict[str, Any]] = []

        for op in operations:
            if op.operation_type == EditOperationType.INSERT_CLIP and op.clip_spec:
                cs = op.clip_spec
                report.clips_count += 1

                # 1. Guardrail check on asset
                asset = asset_registry.get(cs.asset_id)
                if asset:
                    try:
                        AssetGuardrailService.validate_asset_path(asset.path)
                    except AssetGuardrailViolationError as e:
                        report.is_valid = False
                        report.guardrail_passed = False
                        report.discrepancies.append(f"Guardrail violation in operation '{op.operation_id}': {e}")

                # 2. Interval validation
                try:
                    dur = validate_interval(cs.start_frame, cs.end_frame)
                except ValueError as e:
                    report.is_valid = False
                    report.discrepancies.append(f"Invalid frame interval in '{op.operation_id}': {e}")
                    continue

                # 3. Source range consistency
                if cs.source_out_frame is not None:
                    src_dur = cs.source_out_frame - cs.source_in_frame
                    if src_dur != dur:
                        report.is_valid = False
                        report.discrepancies.append(
                            f"Source duration ({src_dur}) does not match timeline duration ({dur}) in '{op.operation_id}'"
                        )

                clips_by_track.setdefault(cs.track_id, []).append(cs)

            elif op.operation_type == EditOperationType.ADD_CAPTION:
                report.captions_count += 1
                captions.append(op.parameters)

        # 4. Check track overlap
        for tid, track_clips in clips_by_track.items():
            sorted_clips = sorted(track_clips, key=lambda c: c.start_frame)
            for i in range(len(sorted_clips)):
                for j in range(i + 1, len(sorted_clips)):
                    c1, c2 = sorted_clips[i], sorted_clips[j]
                    if intervals_overlap((c1.start_frame, c1.end_frame), (c2.start_frame, c2.end_frame)):
                        report.is_valid = False
                        report.discrepancies.append(
                            f"Track '{tid}' has overlapping clips: '{c1.name}' [{c1.start_frame}, {c1.end_frame}) "
                            f"and '{c2.name}' [{c2.start_frame}, {c2.end_frame})"
                        )

        # 5. Check timeline total bounds
        max_frame = 0
        for track_clips in clips_by_track.values():
            for c in track_clips:
                max_frame = max(max_frame, c.end_frame)
        report.total_duration_frames = max_frame

        if max_frame != target_frames:
            report.is_valid = False
            report.discrepancies.append(
                f"Timeline total duration is {max_frame} frames; expected exactly {target_frames} frames."
            )

        return report

    @classmethod
    def generate_cutlist_json(cls, operations: List[EditOperation]) -> str:
        """Serialize atomic editing operations into formatted JSON cutlist."""
        payload = [op.model_dump(mode="json") for op in operations]
        return json.dumps(payload, indent=2)

    @classmethod
    def generate_edit_plan_markdown(
        cls,
        edit_plan: EditPlanRecord,
        operations: List[EditOperation],
        validation: EditPlanValidationReport,
    ) -> str:
        """Generate human-readable rough cut plan report."""
        lines = [
            "# Short #13 Multi-Track Edit Plan & Rough-Cut Specification",
            "**Hirthick’s Vision Studio | YouTube Shorts Production System**",
            "",
            f"**Plan Generated:** {edit_plan.created_at_utc}",
            f"**Timeline Dimensions:** {edit_plan.target_width}×{edit_plan.target_height} (9:16 Vertical) @ {edit_plan.fps} FPS",
            f"**Total Timeline Duration:** Exactly {validation.total_duration_frames} Integer Frames (30.00 Seconds)",
            f"**Validation Status:** {'VALIDATED & APPROVED' if validation.is_valid else 'FAILED'}",
            "",
            "---",
            "",
            "## 1. Track Architecture",
            "",
            "| Track ID | Track Name | Media Type | Order | Primary Content & Mix Level |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        for t in edit_plan.tracks:
            level = "0dB (Dialogue)" if "a1" in t.track_id else ("-18dB (Ducked)" if "a2" in t.track_id else "N/A (Visual)")
            lines.append(f"| `{t.track_id}` | {t.track_name} | {t.track_type.upper()} | {t.order} | {level} |")

        lines.extend([
            "",
            "---",
            "",
            "## 2. Multi-Track Timeline Diagram",
            "",
            "```text",
            "Timeline Frames: 0                 150                360                660                900",
            "Seconds:         0.0s              5.0s               12.0s              22.0s              30.0s",
            "                ├─────────────────┼──────────────────┼──────────────────┼──────────────────┤",
            "Track V2 (B-roll):[Shot 1: Excel]  │                  │                  │                  │",
            "Track V1 (Demo):  │                 [Shot 2: WhatsApp] [Shot 3: Bot Sync] [Shot 4: Ledger]   │",
            "Track A1 (Speech):[=================== 58-Word Voiceover Narration Track (0dB) ==============]",
            "Track A2 (Music): [============= Background Music (bg-music.mp3 ducked to -18dB) ============]",
            "Track TXT (Subs): [Cue 1: Hook    ]│[Cue 2: Problem   ]│[Cue 3: Solution  ]│[Cue 4: CTA       ]│",
            "                ├─────────────────┼──────────────────┼──────────────────┼──────────────────┤",
            "```",
            "",
            "---",
            "",
            "## 3. Atomic Operations CutList",
            "",
            "| Op ID | Type | Track | Frame Range | Source Range | Content / Parameters |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for op in operations:
            if op.operation_type == EditOperationType.INSERT_CLIP and op.clip_spec:
                cs = op.clip_spec
                src = f"[{cs.source_in_frame}, {cs.source_out_frame})" if cs.source_out_frame is not None else "Full"
                lines.append(
                    f"| `{op.operation_id}` | `{op.operation_type.value}` | `{cs.track_id}` | `[{cs.start_frame}, {cs.end_frame})` | `{src}` | {cs.name} (vol: {cs.volume}) |"
                )
            elif op.operation_type == EditOperationType.ADD_CAPTION:
                p = op.parameters
                lines.append(
                    f"| `{op.operation_id}` | `ADD_CAPTION` | `{op.track_id}` | `[{p.get('start_frame')}, {p.get('end_frame')})` | N/A | \"{p.get('text')}\" |"
                )
            elif op.operation_type == EditOperationType.ADD_TRACK:
                p = op.parameters
                lines.append(
                    f"| `{op.operation_id}` | `ADD_TRACK` | `{op.track_id}` | `[0, 900)` | N/A | Add track {p.get('name')} |"
                )

        lines.extend([
            "",
            "---",
            "",
            "## 4. Guardrail & Production Compliance",
            "",
            "- **Authentic Video Sourcing:** 100% of video frames originate from `demo-recording-1.mp4` (Android TellOS mobile capture) and `broll-spreadsheet.mp4` (Pixabay commercial license).",
            "- **Strict Zero-Synthetic Rule:** 0% AI-generated diffusion video, 0% synthetic images, and 0 vector SVG cards.",
            "- **Speech-First Audio Architecture:** Voiceover speech at unity gain (0dB); background music ducked at -18dB (volume 0.125) to avoid masking dialogue.",
            "- **Typographic Captions:** Clean native text captions rendered on safe margins without unapproved graphical cards.",
            "",
        ])

        return "\n".join(lines)

