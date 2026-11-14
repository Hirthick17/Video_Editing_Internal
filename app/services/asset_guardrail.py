"""Deterministic guardrail enforcing the strict prohibition of synthetic/SVG assets."""

import os
import uuid
from pathlib import Path
from typing import List, Optional, Set, Union

from app.services.checksum import calculate_sha256
from app.state.enums import AssetType, ReviewStatus
from app.state.models import AssetRecord

PROHIBITED_EXTENSIONS: Set[str] = {".svg", ".ai", ".eps", ".cdr"}
PROHIBITED_KEYWORDS: Set[str] = {
    "diffusion",
    "midjourney",
    "dall-e",
    "synthetic_card",
    "generated_card",
    "ai_generated",
}
ALLOWED_EXTENSIONS: Set[str] = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".png",
    ".jpg",
    ".jpeg",
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
}


class AssetGuardrailViolationError(ValueError):
    """Raised when an asset violates authentic media and branding guardrails."""
    pass


class AssetGuardrailService:
    """Validates that all ingested assets are authentic recordings or approved stock."""

    @classmethod
    def validate_asset_path(cls, file_path: Union[str, Path]) -> None:
        """Validate an asset file path without requiring an existing file on disk."""
        path = Path(file_path)
        ext = path.suffix.lower()
        if ext in PROHIBITED_EXTENSIONS:
            raise AssetGuardrailViolationError(
                f"Asset '{path.name}' rejected: synthetic SVG/vector assets ({ext}) are prohibited."
            )
        file_name_lower = path.name.lower()
        for kw in PROHIBITED_KEYWORDS:
            if kw in file_name_lower:
                raise AssetGuardrailViolationError(
                    f"Asset '{path.name}' rejected: filename contains prohibited synthetic marker '{kw}'."
                )

    @classmethod
    def validate_candidate_file(
        cls,
        file_path: Union[str, Path],
        asset_type: AssetType,
        tags: Optional[List[str]] = None,
        asset_id: Optional[str] = None,
    ) -> AssetRecord:
        """Inspect and validate a candidate media file against production guardrails."""
        path = Path(file_path)
        tags = tags or []

        # 1. Existence check
        if not path.is_file():
            raise FileNotFoundError(f"Media file not found on disk: {file_path}")

        # 2. Non-empty check
        if path.stat().st_size == 0:
            raise AssetGuardrailViolationError(f"Media file is empty: {file_path}")

        ext = path.suffix.lower()
        file_name_lower = path.name.lower()

        # 3. Prohibited extension check (Quarantine SVG and vector cards)
        if ext in PROHIBITED_EXTENSIONS or asset_type == AssetType.PROHIBITED_SYNTHETIC:
            raise AssetGuardrailViolationError(
                f"Asset '{path.name}' rejected: synthetic SVG / vector assets are prohibited "
                "by production guardrails. Only real screen recordings, UI captures, or approved "
                "stock footage are allowed."
            )

        # 4. Keyword / synthetic metadata inspection
        for kw in PROHIBITED_KEYWORDS:
            if kw in file_name_lower:
                raise AssetGuardrailViolationError(
                    f"Asset '{path.name}' rejected: filename contains prohibited synthetic marker '{kw}'."
                )
            for tag in tags:
                if kw in tag.lower():
                    raise AssetGuardrailViolationError(
                        f"Asset '{path.name}' rejected: tag contains prohibited synthetic marker '{kw}'."
                    )

        # 5. Content header check (ensuring SVGs aren't disguised with valid extensions)
        try:
            with open(path, "rb") as f:
                header = f.read(256).lower()
                if b"<svg" in header or b"<?xml" in header:
                    raise AssetGuardrailViolationError(
                        f"Asset '{path.name}' rejected: header inspection revealed XML/SVG content."
                    )
        except OSError as e:
            raise AssetGuardrailViolationError(f"Failed to inspect file header for '{path.name}': {e}")

        # 6. Allowed extension check
        if ext not in ALLOWED_EXTENSIONS:
            raise AssetGuardrailViolationError(
                f"Asset '{path.name}' rejected: extension '{ext}' is not in allowed media formats: "
                f"{sorted(ALLOWED_EXTENSIONS)}"
            )

        # Compute deterministic checksum
        sha256 = calculate_sha256(path)
        actual_asset_id = asset_id or f"ast_{uuid.uuid4().hex[:10]}"

        return AssetRecord(
            asset_id=actual_asset_id,
            path=str(path.resolve()),
            checksum_sha256=sha256,
            asset_type=asset_type,
            review_status=ReviewStatus.APPROVED,
            metadata={"file_size_bytes": path.stat().st_size, "tags": tags},
            notes="Passed deterministic asset guardrail inspection.",
        )

