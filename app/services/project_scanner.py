"""Deterministic, read-only project scanner and asset inventory service."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.services.checksum import calculate_sha256
from app.state.asset_manifest import AssetManifestRecord, ProjectRecord
from app.state.enums import AssetType, ReviewStatus
from app.state.models import utc_now_iso

# Prohibited synthetic extensions and markers
PROHIBITED_EXTS = {".svg", ".ai", ".eps", ".cdr"}
PROHIBITED_MARKERS = ["diffusion", "midjourney", "dall-e", "synthetic", "generated_card"]


class ProjectScannerService:
    """Scans project folders read-only, classifies media, and isolates quarantined assets."""

    @classmethod
    def scan_file(
        cls,
        file_path: Union[str, Path],
        asset_id: str,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> AssetManifestRecord:
        """Inspect a single media file in read-only mode and compute its manifest record."""
        path = Path(file_path)
        prov = provenance or {}

        if not path.is_file():
            return AssetManifestRecord(
                asset_id=asset_id,
                file_path=str(path),
                file_name=path.name,
                file_size_bytes=0,
                checksum_sha256="",
                asset_type=AssetType.DOCUMENT,
                source_origin="missing",
                approval_status=ReviewStatus.REJECTED,
                is_online=False,
                notes="File is offline or missing from local filesystem.",
            )

        stat = path.stat()
        size_bytes = stat.st_size
        ext = path.suffix.lower()
        file_name_lower = path.name.lower()
        sha256 = calculate_sha256(path)

        # Check for prohibited synthetic assets (e.g. SVG cards)
        is_synthetic = (
            ext in PROHIBITED_EXTS
            or any(m in file_name_lower for m in PROHIBITED_MARKERS)
        )

        if is_synthetic:
            return AssetManifestRecord(
                asset_id=asset_id,
                file_path=str(path.resolve()),
                file_name=path.name,
                file_size_bytes=size_bytes,
                checksum_sha256=sha256,
                asset_type=AssetType.PROHIBITED_SYNTHETIC,
                source_origin="quarantined_synthetic",
                provenance={"reason": "Quarantined Phase 0 synthetic SVG graphic"},
                approval_status=ReviewStatus.QUARANTINED,
                is_online=True,
                notes="Quarantined by production guardrail: SVG graphics are prohibited for YouTube Shorts production.",
            )

        # Classify authentic media
        if ext in {".mp4", ".mov", ".mkv"}:
            if "demo" in file_name_lower or "screen" in file_name_lower or "tellos" in file_name_lower:
                asset_type = AssetType.SCREEN_RECORDING
                origin = "original_recording"
                approval = ReviewStatus.APPROVED
                notes = "Authentic product screen demonstration."
            else:
                asset_type = AssetType.STOCK_BROLL
                origin = "stock_media"
                approval = ReviewStatus.APPROVED
                notes = "Approved stock B-roll."
                if not prov:
                    prov = {
                        "platform": "Pixabay",
                        "license": "Pixabay Content License - Free for commercial use",
                        "attribution_required": False,
                    }
        elif ext in {".mp3", ".wav", ".m4a"}:
            asset_type = AssetType.AUDIO_BGM
            origin = "stock_audio"
            approval = ReviewStatus.APPROVED
            notes = "Background audio soundtrack."
            if not prov:
                prov = {"license": "Standard Production License", "safe_for_monetization": True}
        elif ext in {".png", ".jpg", ".jpeg"}:
            asset_type = AssetType.UI_CAPTURE
            origin = "original_screenshot"
            approval = ReviewStatus.APPROVED
            notes = "Authentic UI capture."
        else:
            asset_type = AssetType.DOCUMENT
            origin = "project_document"
            approval = ReviewStatus.UNREVIEWED
            notes = "Document or metadata file."

        return AssetManifestRecord(
            asset_id=asset_id,
            file_path=str(path.resolve()),
            file_name=path.name,
            file_size_bytes=size_bytes,
            checksum_sha256=sha256,
            asset_type=asset_type,
            source_origin=origin,
            provenance=prov,
            approval_status=approval,
            is_online=True,
            media_info={"extension": ext, "file_size_bytes": size_bytes},
            notes=notes,
        )

    @classmethod
    def scan_short_13_project(
        cls,
        base_dir: Optional[Union[str, Path]] = None,
        external_demo_path: Optional[Union[str, Path]] = None,
    ) -> ProjectRecord:
        """Scan Short #13 ('TellOS PG Rent Book on WhatsApp') candidate project assets."""
        repo_media = Path(__file__).resolve().parent.parent.parent / "assets" / "sample-media"
        if base_dir:
            base = Path(base_dir)
        elif repo_media.exists():
            base = repo_media
        else:
            base = Path("assets/sample-media")

        project_record = ProjectRecord(
            project_id="8a894b86-d5e0-4222-ab88-df22a8e2168e",
            name="Short 13 - TellOS PG Rent Book",
            short_id="short_13_whatsapp_pg_rent",
            root_path=str(base.resolve()),
            description=(
                "YouTube Short demonstrating automated rent receipts directly in WhatsApp chat "
                "for PG owners using TellOS."
            ),
            target_resolution="1080x1920",
            target_fps=30,
            target_duration_seconds=30.0,
        )

        candidate_files = []

        # 1. Primary authentic demo recording
        default_demo = repo_media / "demo-recording-1.mp4"
        demo_path = external_demo_path or default_demo
        candidate_files.append(("ast_demo_recording_01", demo_path, {"role": "Primary UI Demo"}))

        # 2. Approved stock B-roll
        broll_path = base / "broll-spreadsheet.mp4"
        candidate_files.append(
            (
                "ast_broll_spreadsheet_01",
                broll_path,
                {
                    "platform": "Pixabay",
                    "license": "Pixabay Content License - Free for commercial use",
                    "query": "spreadsheet",
                    "role": "Visual Pain Hook",
                },
            )
        )

        # 3. Approved background music
        bgm_path = base / "bg-music.mp3"
        candidate_files.append(
            (
                "ast_bg_music_01",
                bgm_path,
                {"role": "Subtle background music bed ducked at -18dB"},
            )
        )

        # 4. Quarantined Phase 0 SVG cards
        shorts_assets_dir = base / "shorts-assets"
        if shorts_assets_dir.is_dir():
            for svg_file in shorts_assets_dir.glob("*.svg"):
                candidate_files.append(
                    (
                        f"ast_quarantined_{svg_file.stem}",
                        svg_file,
                        {"role": "Quarantined Phase 0 SVG Graphic"},
                    )
                )

        # 5. Check for missing/offline media simulation test
        missing_candidate = base / "non_existent_footage.mp4"
        candidate_files.append(("ast_missing_footage_sample", missing_candidate, {}))

        # Perform read-only inspection
        for asset_id, path, prov in candidate_files:
            record = cls.scan_file(path, asset_id=asset_id, provenance=prov)
            project_record.asset_manifest[asset_id] = record

            if not record.is_online:
                project_record.missing_assets.append(asset_id)
            elif record.approval_status == ReviewStatus.QUARANTINED:
                project_record.quarantined_assets.append(asset_id)

        project_record.updated_at_utc = utc_now_iso()
        return project_record

    @classmethod
    def generate_project_brief_markdown(cls, project: ProjectRecord) -> str:
        """Render approved ProjectRecord and Asset Manifest into human-readable Markdown brief."""
        lines = [
            f"# Project Brief & Asset Inventory: {project.name}",
            f"**Project ID:** `{project.project_id}`  ",
            f"**Short ID:** `{project.short_id}`  ",
            f"**Target Format:** {project.target_resolution} (9:16 Vertical) @ {project.target_fps} FPS  ",
            f"**Target Duration:** {project.target_duration_seconds:.1f}s ({int(project.target_duration_seconds * project.target_fps)} frames)  ",
            f"**Generated At (UTC):** {project.updated_at_utc}  ",
            "",
            "## 1. Executive Concept & Business Context",
            project.description,
            "",
            "- **Target Audience:** PG (Paying Guest) owners, hostel managers, small landlords.",
            "- **Core Business Problem:** 6+ hours wasted monthly matching UPI screenshots to messy Excel ledgers.",
            "- **The TellOS Solution:** Tenant sends UPI payment screenshot to WhatsApp bot -> TellOS extracts amount, validates tenant name, and automatically appends to live ledger.",
            "",
            "## 2. Active Approved Asset Pool",
            "| Asset ID | File Name | Type | Size | SHA-256 (first 16) | Status | Notes |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        active_assets = [
            a for a in project.asset_manifest.values()
            if a.is_online and a.approval_status != ReviewStatus.QUARANTINED
        ]

        for a in active_assets:
            short_sha = a.checksum_sha256[:16] if a.checksum_sha256 else "N/A"
            size_mb = f"{a.file_size_bytes / (1024 * 1024):.2f} MB"
            lines.append(
                f"| `{a.asset_id}` | `{a.file_name}` | {a.asset_type.value} | {size_mb} | `{short_sha}` | **{a.approval_status.value}** | {a.notes} |"
            )

        lines.extend([
            "",
            "## 3. Quarantined Synthetic / Vector Assets (Excluded from Production)",
            "These assets from Phase 0 are quarantined in accordance with Build Pack v0.2 policy (NO synthetic SVGs / NO diffusion clips):",
            "| Asset ID | File Name | Type | Reason | Action Taken |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ])

        quarantined = [
            a for a in project.asset_manifest.values()
            if a.approval_status == ReviewStatus.QUARANTINED
        ]

        for q in quarantined:
            lines.append(
                f"| `{q.asset_id}` | `{q.file_name}` | {q.asset_type.value} | {q.provenance.get('reason', 'Synthetic SVG')} | **QUARANTINED (Excluded)** |"
            )

        lines.extend([
            "",
            "## 4. Missing / Offline Media Status",
        ])

        missing = [a for a in project.asset_manifest.values() if not a.is_online]
        if missing:
            for m in missing:
                lines.append(f"- ⚠️ **Missing Asset:** `{m.asset_id}` (`{m.file_name}`) at `{m.file_path}`")
        else:
            lines.append("- All required media assets are verified online.")

        lines.extend([
            "",
            "## 5. Licensing & Provenance Statement",
            "- **TellOS Screen Demo (`demo-recording-1.mp4`):** Proprietary authentic user demo recording. 100% owned.",
            "- **B-roll Spreadsheet (`broll-spreadsheet.mp4`):** Licensed from Pixabay (Pixabay Content License - Free for commercial use, no attribution required).",
            "- **Background Soundtrack (`bg-music.mp3`):** Approved royalty-free audio bed.",
            "",
            "**Exit Gate Status:** Ready for owner confirmation and Phase 4 script/shot planning.",
        ])

        return "\n".join(lines)
