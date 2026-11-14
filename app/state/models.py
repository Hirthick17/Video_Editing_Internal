"""Strongly typed nested Pydantic models for the production lifecycle."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.state.enums import (
    ApprovalStatus,
    AssetType,
    CritiqueAspect,
    ProductionStage,
    ReviewStatus,
)


def utc_now_iso() -> str:
    """Return the current UTC timestamp formatted as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


class AssetRecord(BaseModel):
    asset_id: str
    path: str
    checksum_sha256: str
    asset_type: AssetType
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    duration_frames: Optional[int] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    notes: str = ""
    discovered_at_utc: str = Field(default_factory=utc_now_iso)


class ScriptRecord(BaseModel):
    version: int = 1
    hook_text: str = ""
    problem_text: str = ""
    solution_text: str = ""
    cta_text: str = ""
    full_narration: str = ""
    claims: List[str] = Field(default_factory=list)
    word_count: int = 0
    estimated_duration_seconds: float = 0.0
    created_at_utc: str = Field(default_factory=utc_now_iso)


class ShotItem(BaseModel):
    shot_id: str
    start_frame: int
    end_frame: int
    description: str
    required_asset_type: AssetType
    matched_asset_id: Optional[str] = None
    visual_notes: str = ""


class ShotPlanRecord(BaseModel):
    version: int = 1
    shots: List[ShotItem] = Field(default_factory=list)
    total_target_duration_seconds: float = 30.0
    coverage_percentage: float = 0.0
    created_at_utc: str = Field(default_factory=utc_now_iso)


class TranscriptionWord(BaseModel):
    word: str
    start_seconds: float
    end_seconds: float
    confidence: float = 1.0


class TranscriptionRecord(BaseModel):
    asset_id: str
    text: str = ""
    language: str = "en"
    words: List[TranscriptionWord] = Field(default_factory=list)
    created_at_utc: str = Field(default_factory=utc_now_iso)


class TrackPlan(BaseModel):
    track_id: str
    track_name: str
    track_type: str  # "video" or "audio"
    order: int = 0


class EditPlanRecord(BaseModel):
    version: int = 1
    target_width: int = 1080
    target_height: int = 1920
    fps: int = 30
    tracks: List[TrackPlan] = Field(default_factory=list)
    operations_summary: List[str] = Field(default_factory=list)
    created_at_utc: str = Field(default_factory=utc_now_iso)


class CritiqueReportRecord(BaseModel):
    aspect: CritiqueAspect
    score: float  # 0.0 to 10.0
    findings: List[str] = Field(default_factory=list)
    passed: bool = True
    required_fixes: List[str] = Field(default_factory=list)
    evaluated_at_utc: str = Field(default_factory=utc_now_iso)


class PublishingPackageRecord(BaseModel):
    title: str = ""
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    thumbnail_source_frame: int = 0
    target_platform: str = "YouTube Shorts"
    created_at_utc: str = Field(default_factory=utc_now_iso)


class ApprovalRecord(BaseModel):
    approval_id: str
    stage: ProductionStage
    decision: ApprovalStatus = ApprovalStatus.PENDING
    reviewer: str = "system"
    feedback: str = ""
    created_at_utc: str = Field(default_factory=utc_now_iso)
    decided_at_utc: Optional[str] = None


class NodeErrorRecord(BaseModel):
    node_name: str
    error_type: str
    message: str
    retry_count: int = 0
    occurred_at_utc: str = Field(default_factory=utc_now_iso)


class EditorStateReference(BaseModel):
    chatcut_project_id: Optional[str] = None
    chatcut_timeline_id: Optional[str] = None
    expected_revision: Optional[str] = None
    last_observed_revision: Optional[str] = None
    snapshot_checksum: Optional[str] = None
    last_verified_at_utc: Optional[str] = None

