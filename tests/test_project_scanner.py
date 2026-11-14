"""Test Phase 3: Project scanner, asset manifest classification, and quarantine enforcement."""

import os
from pathlib import Path
from app.services.project_scanner import ProjectScannerService
from app.state.enums import AssetType, ReviewStatus


def test_project_scanner_readonly_integrity(tmp_path: Path):
    """Verify scanning never alters, overwrites, or touches source file timestamps."""
    test_video = tmp_path / "original_demo.mp4"
    test_video.write_bytes(b"\x00\x00\x00\x20ftypmp42" + b"\x00" * 1024)

    initial_stat = test_video.stat()
    initial_mtime = initial_stat.st_mtime_ns
    initial_size = initial_stat.st_size

    # Scan the file
    record = ProjectScannerService.scan_file(test_video, asset_id="ast_test_demo")

    after_stat = test_video.stat()
    assert after_stat.st_mtime_ns == initial_mtime
    assert after_stat.st_size == initial_size
    assert record.is_online is True
    assert record.file_size_bytes == initial_size
    assert len(record.checksum_sha256) == 64


def test_project_scanner_classification(tmp_path: Path):
    """Verify correct classification of authentic footage, stock media, and audio."""
    demo_file = tmp_path / "tellos_demo_recording.mp4"
    demo_file.write_bytes(b"\x00\x00\x00\x20ftypmp42" + b"\x01" * 512)

    stock_file = tmp_path / "broll_office.mp4"
    stock_file.write_bytes(b"\x00\x00\x00\x20ftypmp42" + b"\x02" * 512)

    audio_file = tmp_path / "bg_music.mp3"
    audio_file.write_bytes(b"ID3\x03\x00\x00\x00" + b"\x03" * 512)

    rec_demo = ProjectScannerService.scan_file(demo_file, "ast_demo")
    assert rec_demo.asset_type == AssetType.SCREEN_RECORDING
    assert rec_demo.approval_status == ReviewStatus.APPROVED

    rec_stock = ProjectScannerService.scan_file(stock_file, "ast_stock")
    assert rec_stock.asset_type == AssetType.STOCK_BROLL
    assert "Pixabay" in rec_stock.provenance.get("platform", "")
    assert rec_stock.approval_status == ReviewStatus.APPROVED

    rec_audio = ProjectScannerService.scan_file(audio_file, "ast_audio")
    assert rec_audio.asset_type == AssetType.AUDIO_BGM
    assert rec_audio.approval_status == ReviewStatus.APPROVED


def test_project_scanner_svg_quarantine(tmp_path: Path):
    """Verify SVG cards are strictly quarantined and excluded from active asset counts."""
    svg_file = tmp_path / "card1_hook.svg"
    svg_file.write_text("<svg><text>Hook</text></svg>", encoding="utf-8")

    rec_svg = ProjectScannerService.scan_file(svg_file, "ast_svg")
    assert rec_svg.asset_type == AssetType.PROHIBITED_SYNTHETIC
    assert rec_svg.approval_status == ReviewStatus.QUARANTINED
    assert "Quarantined" in rec_svg.notes


def test_project_scanner_missing_media_detection(tmp_path: Path):
    """Verify that offline or non-existent files are detected and reported."""
    non_existent = tmp_path / "missing_file.mp4"
    rec = ProjectScannerService.scan_file(non_existent, "ast_missing")
    assert rec.is_online is False
    assert rec.approval_status == ReviewStatus.REJECTED


def test_project_scanner_brief_generation(tmp_path: Path):
    """Verify Markdown brief generation contains expected sections and asset tables."""
    # Create sample project structure
    demo_file = tmp_path / "tellos_demo.mp4"
    demo_file.write_bytes(b"\x00" * 1024)
    svg_file = tmp_path / "shorts-assets" / "card1.svg"
    svg_file.parent.mkdir(parents=True, exist_ok=True)
    svg_file.write_text("<svg></svg>", encoding="utf-8")

    project = ProjectScannerService.scan_short_13_project(
        base_dir=tmp_path,
        external_demo_path=demo_file,
    )

    brief_md = ProjectScannerService.generate_project_brief_markdown(project)
    assert "# Project Brief & Asset Inventory: Short 13 - TellOS PG Rent Book" in brief_md
    assert "Active Approved Asset Pool" in brief_md
    assert "Quarantined Synthetic / Vector Assets" in brief_md
    assert "Missing / Offline Media Status" in brief_md
    assert "Pixabay Content License" in brief_md

