"""Future ChatCut editor contracts, timeline specs, and half-open frame validation rules."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from app.state.enums import EditOperationType


class TimelineSpec(BaseModel):
    """Timeline specifications for vertical YouTube Shorts."""

    width: int = 1080
    height: int = 1920
    fps: int = 30
    timebase: str = "30/1"

    @model_validator(mode="after")
    def validate_shorts_dimensions(self) -> "TimelineSpec":
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Timeline dimensions must be positive integers")
        if self.fps <= 0:
            raise ValueError("Timeline FPS must be positive")
        return self


class ClipSpec(BaseModel):
    """Specification for a clip placed on a timeline track using half-open integer intervals [start_frame, end_frame)."""

    item_id: str
    track_id: str
    asset_id: str
    start_frame: int = Field(..., ge=0)
    end_frame: int = Field(..., gt=0)
    source_in_frame: int = Field(default=0, ge=0)
    source_out_frame: Optional[int] = None
    volume: float = Field(default=1.0, ge=0.0, le=2.0)
    name: str = ""

    @property
    def duration_frames(self) -> int:
        """Calculate duration in frames according to half-open interval math."""
        return self.end_frame - self.start_frame

    @model_validator(mode="after")
    def validate_frame_interval(self) -> "ClipSpec":
        if self.end_frame <= self.start_frame:
            raise ValueError(
                f"end_frame ({self.end_frame}) must be strictly greater than "
                f"start_frame ({self.start_frame}) in half-open interval [start, end)"
            )
        if self.source_out_frame is not None and self.source_out_frame <= self.source_in_frame:
            raise ValueError(
                f"source_out_frame ({self.source_out_frame}) must be strictly greater "
                f"than source_in_frame ({self.source_in_frame})"
            )
        return self


class TrackSpec(BaseModel):
    """Specification for a track containing sequential or non-overlapping clips."""

    track_id: str
    track_name: str
    track_type: str  # "video" or "audio"
    order: int = 0
    clips: List[ClipSpec] = Field(default_factory=list)

    @field_validator("track_type")
    @classmethod
    def validate_track_type(cls, v: str) -> str:
        if v.lower() not in {"video", "audio", "text"}:
            raise ValueError("track_type must be 'video', 'audio', or 'text'")
        return v.lower()


class EditOperation(BaseModel):
    """Atomic editing operation intended for ChatCut MCP execution."""

    operation_id: str
    operation_type: EditOperationType
    idempotency_key: str
    track_id: Optional[str] = None
    clip_spec: Optional[ClipSpec] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    applied: bool = False
    verified: bool = False

