"""Canonical typed ProductionState and LangGraph state channels with conflict-free reducers."""

from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field, field_validator

from app.state.enums import (
    ApprovalStatus,
    JobStatus,
    ProductionStage,
)
from app.state.models import (
    ApprovalRecord,
    AssetRecord,
    CritiqueReportRecord,
    EditPlanRecord,
    EditorStateReference,
    NodeErrorRecord,
    PublishingPackageRecord,
    ScriptRecord,
    ShotPlanRecord,
    TranscriptionRecord,
    utc_now_iso,
)


# ============================================================================
# Reducer functions for parallel graph branches
# ============================================================================

def append_unique_strings(current: Optional[List[str]], update: Optional[List[str]]) -> List[str]:
    """Merge lists preserving insertion order while preventing duplicates."""
    curr_list = current or []
    upd_list = update or []
    seen = set(curr_list)
    result = list(curr_list)
    for item in upd_list:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def append_unique_stages(
    current: Optional[List[ProductionStage]], update: Optional[List[ProductionStage]]
) -> List[ProductionStage]:
    """Merge stage lists while preventing duplicates."""
    curr_list = current or []
    upd_list = update or []
    seen = set(curr_list)
    result = list(curr_list)
    for item in upd_list:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def merge_asset_registry(
    current: Optional[Dict[str, AssetRecord]], update: Optional[Dict[str, AssetRecord]]
) -> Dict[str, AssetRecord]:
    """Deterministically merge asset records by asset_id without clobbering existing metadata."""
    result = dict(current or {})
    if update:
        for k, v in update.items():
            if k in result:
                # Merge metadata dictionaries if present
                existing_record = result[k]
                merged_meta = dict(existing_record.metadata)
                merged_meta.update(v.metadata)
                merged_record = v.model_copy(update={"metadata": merged_meta})
                result[k] = merged_record
            else:
                result[k] = v
    return result


def append_error_records(
    current: Optional[List[NodeErrorRecord]], update: Optional[List[NodeErrorRecord]]
) -> List[NodeErrorRecord]:
    """Append node errors."""
    return (current or []) + (update or [])


def append_critique_records(
    current: Optional[List[CritiqueReportRecord]], update: Optional[List[CritiqueReportRecord]]
) -> List[CritiqueReportRecord]:
    """Append critique reports."""
    return (current or []) + (update or [])


def merge_retry_counts(
    current: Optional[Dict[str, int]], update: Optional[Dict[str, int]]
) -> Dict[str, int]:
    """Merge node retry count maps taking maximum count."""
    result = dict(current or {})
    if update:
        for k, v in update.items():
            result[k] = max(result.get(k, 0), v)
    return result


def merge_generic_dicts(
    current: Optional[Dict[str, Any]], update: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Shallow merge generic dictionaries."""
    result = dict(current or {})
    if update:
        result.update(update)
    return result


def replace_or_keep(current: Any, update: Any) -> Any:
    """Take latest non-null value or keep current."""
    if update is not None:
        return update
    return current


def latest_timestamp_reducer(current: Optional[str], update: Optional[str]) -> str:
    """Deterministic timestamp reducer selecting the latest UTC timestamp."""
    if not current:
        return update or utc_now_iso()
    if not update:
        return current
    return max(current, update)


def max_version_reducer(current: Optional[int], update: Optional[int]) -> int:
    """Deterministic version reducer taking the maximum version."""
    return max(current or 1, update or 1)


# ============================================================================
# Canonical Pydantic ProductionState
# ============================================================================

class ProductionState(BaseModel):
    """The canonical, strongly-typed state object for a production job."""

    job_id: str
    project_id: str
    short_id: str
    job_status: JobStatus = JobStatus.CREATED
    current_stage: ProductionStage = ProductionStage.INITIALIZATION

    completed_nodes: List[str] = Field(default_factory=list)
    failed_nodes: List[str] = Field(default_factory=list)
    pending_approvals: List[str] = Field(default_factory=list)
    approved_stages: List[ProductionStage] = Field(default_factory=list)
    rejected_stages: List[ProductionStage] = Field(default_factory=list)

    asset_registry: Dict[str, AssetRecord] = Field(default_factory=dict)
    research_results: Dict[str, Any] = Field(default_factory=dict)
    script: Optional[ScriptRecord] = None
    shot_plan: Optional[ShotPlanRecord] = None
    transcription: Optional[TranscriptionRecord] = None
    edit_plan: Optional[EditPlanRecord] = None
    critique_report: List[CritiqueReportRecord] = Field(default_factory=list)
    publishing_package: Optional[PublishingPackageRecord] = None
    editor_state_reference: Optional[EditorStateReference] = None

    errors: List[NodeErrorRecord] = Field(default_factory=list)
    retry_counts: Dict[str, int] = Field(default_factory=dict)

    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    state_version: int = 1

    @field_validator("job_id", "project_id", "short_id")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Identifier must not be empty or blank")
        return v.strip()

    def touch(self) -> None:
        """Bump state version and update modification timestamp."""
        self.state_version += 1
        self.updated_at = utc_now_iso()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize canonical state to dictionary with ISO timestamps."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductionState":
        """Deserialize and validate dictionary into ProductionState."""
        return cls.model_validate(data)


# ============================================================================
# LangGraph ProductionGraphState (with Annotated Reducers)
# ============================================================================

class ProductionGraphState(TypedDict, total=False):
    """LangGraph state schema with channel reducers for parallel branch execution."""

    job_id: str
    project_id: str
    short_id: str
    job_status: Annotated[JobStatus, replace_or_keep]
    current_stage: Annotated[ProductionStage, replace_or_keep]

    completed_nodes: Annotated[List[str], append_unique_strings]
    failed_nodes: Annotated[List[str], append_unique_strings]
    pending_approvals: Annotated[List[str], append_unique_strings]
    approved_stages: Annotated[List[ProductionStage], append_unique_stages]
    rejected_stages: Annotated[List[ProductionStage], append_unique_stages]

    asset_registry: Annotated[Dict[str, AssetRecord], merge_asset_registry]
    research_results: Annotated[Dict[str, Any], merge_generic_dicts]
    script: Annotated[Optional[ScriptRecord], replace_or_keep]
    shot_plan: Annotated[Optional[ShotPlanRecord], replace_or_keep]
    transcription: Annotated[Optional[TranscriptionRecord], replace_or_keep]
    edit_plan: Annotated[Optional[EditPlanRecord], replace_or_keep]
    critique_report: Annotated[List[CritiqueReportRecord], append_critique_records]
    publishing_package: Annotated[Optional[PublishingPackageRecord], replace_or_keep]
    editor_state_reference: Annotated[Optional[EditorStateReference], replace_or_keep]

    errors: Annotated[List[NodeErrorRecord], append_error_records]
    retry_counts: Annotated[Dict[str, int], merge_retry_counts]

    created_at: str
    updated_at: Annotated[str, latest_timestamp_reducer]
    state_version: Annotated[int, max_version_reducer]
