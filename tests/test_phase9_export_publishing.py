"""Test Phase 9: Export validation, render certification, and publishing package creation."""

from pathlib import Path
import pytest
from app.integrations.chatcut.mcp_adapter import ChatCutMCPAdapter
from app.services.export_publishing_service import ExportService, PublishingService
from app.services.script_service import ScriptService


def test_export_blocked_without_explicit_approval():
    """Verify export is strictly blocked with PermissionError if owner approval is absent."""
    adapter = ChatCutMCPAdapter(mode="simulated")
    tl = adapter.get_timeline("03501b27-ebf5-4aae-9eb6-6e7df21e0378")

    with pytest.raises(PermissionError) as exc_info:
        ExportService.execute_export(
            timeline=tl,
            output_path=Path("dummy_export.mp4"),
            owner_approved=False,
        )
    assert "explicit owner approval is required" in str(exc_info.value)


def test_export_execution_and_post_render_validation(tmp_path: Path):
    """Verify approved export produces valid MP4 metadata, dimensions, duration, and checksum."""
    adapter = ChatCutMCPAdapter(mode="simulated")
    tl = adapter.get_timeline("03501b27-ebf5-4aae-9eb6-6e7df21e0378")
    out_file = tmp_path / "short-13-test-render.mp4"

    export_rec = ExportService.execute_export(
        timeline=tl,
        output_path=out_file,
        owner_approved=True,
    )

    assert export_rec.is_valid is True
    assert export_rec.width == 1080
    assert export_rec.height == 1920
    assert export_rec.fps == 30.0
    assert export_rec.duration_frames == 900
    assert export_rec.checksum_sha256 != ""
    assert Path(export_rec.output_path).exists()
    assert export_rec.file_size_bytes > 0


def test_publishing_package_generation():
    """Verify high-converting title options, full description, tags, and pinned comment."""
    script = ScriptService.create_short_13_script()
    pkg = PublishingService.generate_publishing_package(script)

    assert len(pkg.titles) == 3
    assert any("TellOS" in t for t in pkg.titles)
    assert any("WhatsApp" in t for t in pkg.titles)
    assert "#Shorts" in pkg.description
    assert len(pkg.tags) >= 5
    assert "WhatsApp" in pkg.pinned_comment
    assert pkg.thumbnail_timestamp_seconds == 18.0
    assert len(pkg.manual_upload_checklist) >= 5

