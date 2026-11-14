"""Domain models for Project Registry, Asset Manifests, and Licensing."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.state.enums import AssetType, ReviewStatus
from app.state.models import utc_now_iso


class AssetManifestRecord(BaseModel):
    """Immutable audit record for an asset in the project inventory."""

    asset_id: str
    file_path: str
    file_name: str
    file_size_bytes: int
    checksum_sha256: str
    asset_type: AssetType
    source_origin: str  # "original_recording", "stock_media", "quarantined_synthetic"
    provenance: Dict[str, Any] = Field(default_factory=dict)
    approval_status: ReviewStatus = ReviewStatus.UNREVIEWED
    is_online: bool = True
    media_info: Dict[str, Any] = Field(default_factory=dict)
    notes: str = ""
    discovered_at_utc: str = Field(default_factory=utc_now_iso)


class ProjectRecord(BaseModel):
    """Canonical registry record for a production Short project."""

    project_id: str
    name: str
    short_id: str
    root_path: str
    description: str
    target_resolution: str = "1080x1920"
    target_fps: int = 30
    target_duration_seconds: float = 30.0
    asset_manifest: Dict[str, AssetManifestRecord] = Field(default_factory=dict)
    quarantined_assets: List[str] = Field(default_factory=list)
    missing_assets: List[str] = Field(default_factory=list)
    approved_by_owner: bool = False
    created_at_utc: str = Field(default_factory=utc_now_iso)
    updated_at_utc: str = Field(default_factory=utc_now_iso)

    @property
    def active_asset_count(self) -> int:
        """Count only non-quarantined, online, approved or pending assets."""
        return sum(
            1
            for a in self.asset_manifest.values()
            if a.is_online and a.approval_status != ReviewStatus.QUARANTINED
        )

    @property
    def asset_registry(self) -> Dict[str, Any]:
        """Convert asset_manifest to AssetRecord dictionary for compatibility with ProductionState."""
        from app.state.models import AssetRecord
        result = {}
        for aid, item in self.asset_manifest.items():
            result[aid] = AssetRecord(
                asset_id=item.asset_id,
                path=item.file_path,
                checksum_sha256=item.checksum_sha256,
                asset_type=item.asset_type,
                review_status=item.approval_status,
                metadata=item.media_info,
                notes=item.notes,
                discovered_at_utc=item.discovered_at_utc,
            )
        return result

