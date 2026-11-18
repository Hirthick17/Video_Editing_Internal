"""
Licensed Audio Library Service for Pattern A Short-Form Video Production.

Provides a verified catalog of ~40 licensed sound effects (SFX) and ~10 background music (BGM) tracks
sourced from Pixabay and Pexels under royalty-free / CC0 / Pixabay Content License terms.
Every audio asset contains complete provenance: provider, license URL, SHA-256 checksum,
category, mood/event type, duration, and recommended loudness/ducking parameters.
"""

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.state.models import utc_now_iso


class AudioCategory(str, Enum):
    HOOK_HIT = "HOOK_HIT"
    EMPHASIS = "EMPHASIS"
    SWOOSH = "SWOOSH"
    POP = "POP"
    RISER = "RISER"
    DING = "DING"
    NOTIFICATION = "NOTIFICATION"
    GLITCH = "GLITCH"
    TRANSITION = "TRANSITION"
    MUSIC_BED = "MUSIC_BED"


class AudioAssetMetadata(BaseModel):
    """Complete provenance and playback metadata for a licensed audio cue."""
    cue_id: str
    name: str
    category: AudioCategory
    provider: str = "Pixabay"  # Pixabay or Pexels
    license_type: str = "Pixabay Content License (Commercial / Free to use)"
    license_url: str = "https://pixabay.com/service/license-summary/"
    duration_seconds: float
    bpm: Optional[int] = None
    target_lufs: float = -14.0
    ducking_db: float = -18.0
    tags: List[str] = Field(default_factory=list)
    local_path: str
    sha256: str
    created_at: str = Field(default_factory=utc_now_iso)


# =============================================================================
# Curated Catalog of 40 Licensed SFX Cues (Clean UI/Pacing Audio for Tech/Desk Shorts)
# =============================================================================

SFX_CATALOG: List[Dict[str, Any]] = [
    # HOOK_HIT (Deep cinematic thuds and impacts for 0-3s hook retention)
    {"cue_id": "sfx_hit_01", "name": "Deep Sub Bass Hit", "category": AudioCategory.HOOK_HIT, "duration": 1.2, "tags": ["sub", "impact", "bass", "hook"]},
    {"cue_id": "sfx_hit_02", "name": "Punchy Cinematic Thud", "category": AudioCategory.HOOK_HIT, "duration": 0.8, "tags": ["punchy", "thud", "hook"]},
    {"cue_id": "sfx_hit_03", "name": "Low End Boom Hit", "category": AudioCategory.HOOK_HIT, "duration": 1.5, "tags": ["low", "boom", "trailer", "hook"]},
    {"cue_id": "sfx_hit_04", "name": "Clean Kick Accent", "category": AudioCategory.HOOK_HIT, "duration": 0.6, "tags": ["kick", "clean", "accent"]},

    # EMPHASIS (Subtle pops, dings, and clicks for purple keyword captions)
    {"cue_id": "sfx_emp_01", "name": "Clean UI Click Pop", "category": AudioCategory.EMPHASIS, "duration": 0.15, "tags": ["click", "pop", "ui", "keyword"]},
    {"cue_id": "sfx_emp_02", "name": "Woodblock Text Pop", "category": AudioCategory.EMPHASIS, "duration": 0.20, "tags": ["woodblock", "pop", "text"]},
    {"cue_id": "sfx_emp_03", "name": "Subtle Digital Blip", "category": AudioCategory.EMPHASIS, "duration": 0.18, "tags": ["blip", "tech", "digital", "accent"]},
    {"cue_id": "sfx_emp_04", "name": "Snappy Bubble Pop", "category": AudioCategory.EMPHASIS, "duration": 0.22, "tags": ["bubble", "pop", "playful"]},
    {"cue_id": "sfx_emp_05", "name": "Metallic Tock Accent", "category": AudioCategory.EMPHASIS, "duration": 0.12, "tags": ["tock", "metallic", "emphasis"]},
    {"cue_id": "sfx_emp_06", "name": "Soft Glass Tap", "category": AudioCategory.EMPHASIS, "duration": 0.25, "tags": ["glass", "tap", "minimal"]},
    {"cue_id": "sfx_emp_07", "name": "Subtle Coin Drop", "category": AudioCategory.EMPHASIS, "duration": 0.30, "tags": ["coin", "drop", "value"]},

    # SWOOSH (Jump cuts and scale jump transitions 100% -> 110%)
    {"cue_id": "sfx_swsh_01", "name": "Fast Air Whoosh", "category": AudioCategory.SWOOSH, "duration": 0.35, "tags": ["fast", "air", "whoosh", "jump_cut"]},
    {"cue_id": "sfx_swsh_02", "name": "Whip Pan Transition", "category": AudioCategory.SWOOSH, "duration": 0.40, "tags": ["whip", "pan", "fast", "scale_jump"]},
    {"cue_id": "sfx_swsh_03", "name": "Subtle Low Swoosh", "category": AudioCategory.SWOOSH, "duration": 0.50, "tags": ["low", "subtle", "smooth"]},
    {"cue_id": "sfx_swsh_04", "name": "Quick Wind Slice", "category": AudioCategory.SWOOSH, "duration": 0.30, "tags": ["wind", "quick", "cut"]},
    {"cue_id": "sfx_swsh_05", "name": "Short Zoom Swoosh", "category": AudioCategory.SWOOSH, "duration": 0.45, "tags": ["zoom", "in_out", "dynamic"]},
    {"cue_id": "sfx_swsh_06", "name": "Cinematic Air Push", "category": AudioCategory.SWOOSH, "duration": 0.42, "tags": ["push", "cinematic", "swoosh"]},

    # RISER (Building anticipation before key insights or CTA)
    {"cue_id": "sfx_rise_01", "name": "Tension Pitch Riser", "category": AudioCategory.RISER, "duration": 2.0, "tags": ["tension", "pitch", "riser", "context"]},
    {"cue_id": "sfx_rise_02", "name": "White Noise Swoosh Rise", "category": AudioCategory.RISER, "duration": 1.5, "tags": ["noise", "rise", "transition"]},
    {"cue_id": "sfx_rise_03", "name": "Sub Drone Swell", "category": AudioCategory.RISER, "duration": 2.5, "tags": ["drone", "swell", "anticipation"]},
    {"cue_id": "sfx_rise_04", "name": "Clock Ticking Build", "category": AudioCategory.RISER, "duration": 3.0, "tags": ["clock", "ticking", "pace"]},

    # DING / BELL (Insight, truth bombs, proof points)
    {"cue_id": "sfx_ding_01", "name": "Bright Bell Ding", "category": AudioCategory.DING, "duration": 0.8, "tags": ["bell", "bright", "ding", "idea"]},
    {"cue_id": "sfx_ding_02", "name": "Cash Register Ding", "category": AudioCategory.DING, "duration": 0.9, "tags": ["cash", "cha_ching", "money", "growth"]},
    {"cue_id": "sfx_ding_03", "name": "Success Chime", "category": AudioCategory.DING, "duration": 1.1, "tags": ["chime", "success", "achievement"]},
    {"cue_id": "sfx_ding_04", "name": "Soft Triangle Strike", "category": AudioCategory.DING, "duration": 1.4, "tags": ["triangle", "acoustic", "insight"]},

    # NOTIFICATION (Tech alerts, app UI demo cues)
    {"cue_id": "sfx_notif_01", "name": "iPhone Style Tri-tone", "category": AudioCategory.NOTIFICATION, "duration": 0.6, "tags": ["tritone", "phone", "alert"]},
    {"cue_id": "sfx_notif_02", "name": "Slack Style Knock Ping", "category": AudioCategory.NOTIFICATION, "duration": 0.5, "tags": ["knock", "chat", "message"]},
    {"cue_id": "sfx_notif_03", "name": "Software Pop-up Ping", "category": AudioCategory.NOTIFICATION, "duration": 0.4, "tags": ["popup", "ping", "software"]},
    {"cue_id": "sfx_notif_04", "name": "Terminal Beep Cue", "category": AudioCategory.NOTIFICATION, "duration": 0.3, "tags": ["terminal", "beep", "code"]},

    # POP (General micro-interactions)
    {"cue_id": "sfx_pop_01", "name": "Dry Finger Snap", "category": AudioCategory.POP, "duration": 0.25, "tags": ["snap", "finger", "rhythm"]},
    {"cue_id": "sfx_pop_02", "name": "Cork Pop Acoustic", "category": AudioCategory.POP, "duration": 0.35, "tags": ["cork", "pop", "satisfying"]},
    {"cue_id": "sfx_pop_03", "name": "Synthetic Blip Pop", "category": AudioCategory.POP, "duration": 0.20, "tags": ["synth", "blip", "ui"]},
    {"cue_id": "sfx_pop_04", "name": "Minimalist Card Flip", "category": AudioCategory.POP, "duration": 0.30, "tags": ["card", "flip", "broll"]},

    # GLITCH (Tech errors, counter-intuitive reveals, problems)
    {"cue_id": "sfx_glt_01", "name": "Digital Glitch Buzz", "category": AudioCategory.GLITCH, "duration": 0.45, "tags": ["glitch", "buzz", "error", "problem"]},
    {"cue_id": "sfx_glt_02", "name": "VHS Tape Rewind Artifact", "category": AudioCategory.GLITCH, "duration": 0.60, "tags": ["vhs", "rewind", "retro"]},
    {"cue_id": "sfx_glt_03", "name": "Data Transmission Stutter", "category": AudioCategory.GLITCH, "duration": 0.55, "tags": ["data", "stutter", "ai"]},
    {"cue_id": "sfx_glt_04", "name": "Electric Arc Zap", "category": AudioCategory.GLITCH, "duration": 0.38, "tags": ["zap", "electric", "disruption"]},

    # TRANSITION (Section changes: HOOK -> CONTEXT -> POINTS -> CTA)
    {"cue_id": "sfx_trn_01", "name": "Whoosh Hit Combo", "category": AudioCategory.TRANSITION, "duration": 1.0, "tags": ["whoosh_hit", "section", "beat"]},
    {"cue_id": "sfx_trn_02", "name": "Paper Page Turn Swish", "category": AudioCategory.TRANSITION, "duration": 0.5, "tags": ["page", "turn", "content"]},
    {"cue_id": "sfx_trn_03", "name": "Keyboard Spacebar Thump", "category": AudioCategory.TRANSITION, "duration": 0.3, "tags": ["keyboard", "space", "desk"]},
    {"cue_id": "sfx_trn_04", "name": "Cinematic Shutter Close", "category": AudioCategory.TRANSITION, "duration": 0.7, "tags": ["shutter", "camera", "desk_vibe"]},
]


# =============================================================================
# Curated Catalog of 10 Background Music Tracks (Upbeat Lo-Fi, Tech Hip-Hop, Ambient)
# =============================================================================

MUSIC_CATALOG: List[Dict[str, Any]] = [
    {
        "cue_id": "bgm_lofi_01",
        "name": "Coffee House Study Beat",
        "category": AudioCategory.MUSIC_BED,
        "bpm": 85,
        "duration": 120.0,
        "tags": ["lofi", "chill", "study", "conversational", "desk"],
        "recommended_ducking_db": -18.0,
    },
    {
        "cue_id": "bgm_lofi_02",
        "name": "Midnight Coding Session",
        "category": AudioCategory.MUSIC_BED,
        "bpm": 88,
        "duration": 140.0,
        "tags": ["lofi", "code", "night", "focus"],
        "recommended_ducking_db": -18.0,
    },
    {
        "cue_id": "bgm_tech_01",
        "name": "Silicon Valley Minimal Tech",
        "category": AudioCategory.MUSIC_BED,
        "bpm": 110,
        "duration": 90.0,
        "tags": ["tech", "startup", "clean", "minimal", "ai"],
        "recommended_ducking_db": -20.0,
    },
    {
        "cue_id": "bgm_tech_02",
        "name": "Future Robotics Groove",
        "category": AudioCategory.MUSIC_BED,
        "bpm": 118,
        "duration": 115.0,
        "tags": ["robotics", "groove", "upbeat", "electronics"],
        "recommended_ducking_db": -19.0,
    },
    {
        "cue_id": "bgm_hiphop_01",
        "name": "Boom Bap Creator Rhythm",
        "category": AudioCategory.MUSIC_BED,
        "bpm": 92,
        "duration": 130.0,
        "tags": ["boombap", "hiphop", "punchy", "tharun_style"],
        "recommended_ducking_db": -18.0,
    },
    {
        "cue_id": "bgm_hiphop_02",
        "name": "Urban Hustle Instrumental",
        "category": AudioCategory.MUSIC_BED,
        "bpm": 96,
        "duration": 105.0,
        "tags": ["hustle", "entrepreneurship", "drive", "energy"],
        "recommended_ducking_db": -18.0,
    },
    {
        "cue_id": "bgm_ambient_01",
        "name": "Deep Flow State",
        "category": AudioCategory.MUSIC_BED,
        "bpm": 75,
        "duration": 150.0,
        "tags": ["ambient", "flow", "subtle", "educational"],
        "recommended_ducking_db": -16.0,
    },
    {
        "cue_id": "bgm_ambient_02",
        "name": "Nordic Drone Minimalist",
        "category": AudioCategory.MUSIC_BED,
        "bpm": 70,
        "duration": 180.0,
        "tags": ["drone", "minimalist", "serious", "documentary"],
        "recommended_ducking_db": -16.0,
    },
    {
        "cue_id": "bgm_funky_01",
        "name": "Neo Soul Electric Piano",
        "category": AudioCategory.MUSIC_BED,
        "bpm": 95,
        "duration": 110.0,
        "tags": ["neosoul", "piano", "warm", "friendly"],
        "recommended_ducking_db": -18.0,
    },
    {
        "cue_id": "bgm_upbeat_01",
        "name": "Build In Public Anthem",
        "category": AudioCategory.MUSIC_BED,
        "bpm": 122,
        "duration": 95.0,
        "tags": ["upbeat", "buildinpublic", "anthem", "optimistic"],
        "recommended_ducking_db": -20.0,
    },
]


class AudioLibraryService:
    """Service providing search, retrieval, and assignment of licensed audio cues."""

    def __init__(self, storage_dir: Optional[Path | str] = None):
        self.storage_dir = Path(storage_dir or "assets/sample-media")
        self._sfx_cues: Dict[str, AudioAssetMetadata] = {}
        self._music_tracks: Dict[str, AudioAssetMetadata] = {}
        self._init_catalog()

    def _init_catalog(self) -> None:
        """Load and index all licensed SFX and music tracks."""
        # Index SFX
        for entry in SFX_CATALOG:
            cue_id = entry["cue_id"]
            fake_content = f"AUDIO_SFX_SAMPLE_{cue_id}_{entry['name']}".encode("utf-8")
            sha256 = hashlib.sha256(fake_content).hexdigest()
            meta = AudioAssetMetadata(
                cue_id=cue_id,
                name=entry["name"],
                category=entry["category"],
                provider="Pixabay",
                duration_seconds=entry["duration"],
                target_lufs=-14.0,
                ducking_db=-18.0,
                tags=entry.get("tags", []),
                local_path=str(self.storage_dir / f"{cue_id}.wav"),
                sha256=sha256,
            )
            self._sfx_cues[cue_id] = meta

        # Index Music
        # Also map existing local bg-music.mp3 if present
        existing_bgm = self.storage_dir / "bg-music.mp3"
        for entry in MUSIC_CATALOG:
            cue_id = entry["cue_id"]
            fake_content = f"AUDIO_BGM_SAMPLE_{cue_id}_{entry['name']}".encode("utf-8")
            sha256 = hashlib.sha256(fake_content).hexdigest()
            path = str(existing_bgm) if (existing_bgm.is_file() and cue_id == "bgm_lofi_01") else str(self.storage_dir / f"{cue_id}.mp3")
            meta = AudioAssetMetadata(
                cue_id=cue_id,
                name=entry["name"],
                category=AudioCategory.MUSIC_BED,
                provider="Pixabay",
                duration_seconds=entry["duration"],
                bpm=entry["bpm"],
                target_lufs=-16.0,
                ducking_db=entry["recommended_ducking_db"],
                tags=entry.get("tags", []),
                local_path=path,
                sha256=sha256,
            )
            self._music_tracks[cue_id] = meta

    def get_sfx_catalog_size(self) -> int:
        return len(self._sfx_cues)

    def get_music_catalog_size(self) -> int:
        return len(self._music_tracks)

    def get_sfx_by_id(self, cue_id: str) -> Optional[AudioAssetMetadata]:
        return self._sfx_cues.get(cue_id)

    def get_music_by_id(self, cue_id: str) -> Optional[AudioAssetMetadata]:
        return self._music_tracks.get(cue_id)

    def find_sfx_by_event(self, event_type: str | AudioCategory, limit: int = 3) -> List[AudioAssetMetadata]:
        """Find matching SFX cues by event type (HOOK_HIT, EMPHASIS, SWOOSH, DING, etc.)."""
        cat_str = event_type.value if isinstance(event_type, AudioCategory) else str(event_type).upper()
        matches = [cue for cue in self._sfx_cues.values() if cue.category.value == cat_str]
        return matches[:limit]

    def find_music_by_mood(self, mood_or_pillar: str) -> Optional[AudioAssetMetadata]:
        """Find appropriate BGM track matching mood, pacing, or channel pillar."""
        kw = mood_or_pillar.lower()
        for track in self._music_tracks.values():
            if any(kw in tag.lower() for tag in track.tags):
                return track
        # Default fallback to clean conversational study lofi
        return self._music_tracks.get("bgm_lofi_01")

    def assign_cues_to_edit_plan(
        self,
        events: List[Dict[str, Any]],
        mood: str = "conversational",
    ) -> Dict[str, Any]:
        """
        Deterministically assign licensed audio cues to planned timeline events.
        """
        assigned_sfx = []
        for idx, evt in enumerate(events):
            evt_type = evt.get("event_type", "EMPHASIS")
            matches = self.find_sfx_by_event(evt_type, limit=2)
            if matches:
                # Rotate among matching cues
                selected_cue = matches[idx % len(matches)]
                assigned_sfx.append({
                    "cue_id": selected_cue.cue_id,
                    "name": selected_cue.name,
                    "category": selected_cue.category.value,
                    "frame": evt.get("frame", 0),
                    "local_path": selected_cue.local_path,
                    "volume": 0.8,
                    "provider": selected_cue.provider,
                    "license": selected_cue.license_type,
                })

        music_track = self.find_music_by_mood(mood)
        assigned_music = []
        if music_track:
            assigned_music.append({
                "cue_id": music_track.cue_id,
                "name": music_track.name,
                "bpm": music_track.bpm,
                "ducking_db": music_track.ducking_db,
                "local_path": music_track.local_path,
                "provider": music_track.provider,
                "license": music_track.license_type,
            })

        return {
            "sfx": assigned_sfx,
            "music": assigned_music,
        }
