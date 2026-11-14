"""Test 10: Asset guardrail enforcement (strict prohibition of synthetic/SVG assets)."""

from pathlib import Path
import pytest

from app.services.asset_guardrail import (
    AssetGuardrailService,
    AssetGuardrailViolationError,
)
from app.state.enums import AssetType, ReviewStatus


def test_svg_card_rejection(sample_media_files):
    """Verify that SVG cards (like Phase 0 card1_hook.svg) are strictly rejected."""
    svg_file = sample_media_files["svg"]
    with pytest.raises(AssetGuardrailViolationError, match="synthetic SVG / vector assets are prohibited"):
        AssetGuardrailService.validate_candidate_file(
            file_path=svg_file,
            asset_type=AssetType.SCREEN_RECORDING,
        )


def test_synthetic_keyword_tag_rejection(sample_media_files):
    """Verify that assets tagged with synthetic/diffusion markers are rejected."""
    mp4_file = sample_media_files["mp4"]
    with pytest.raises(AssetGuardrailViolationError, match="prohibited synthetic marker"):
        AssetGuardrailService.validate_candidate_file(
            file_path=mp4_file,
            asset_type=AssetType.SCREEN_RECORDING,
            tags=["stable_diffusion_v2", "broll"],
        )


def test_disguised_svg_header_rejection(tmp_path: Path):
    """Verify that an SVG file disguised with a .png extension is detected and rejected via header check."""
    disguised = tmp_path / "fake_screenshot.png"
    disguised.write_text("<?xml version='1.0'?><svg width='100' height='100'></svg>", encoding="utf-8")

    with pytest.raises(AssetGuardrailViolationError, match="revealed XML/SVG content"):
        AssetGuardrailService.validate_candidate_file(
            file_path=disguised,
            asset_type=AssetType.UI_CAPTURE,
        )


def test_authentic_media_acceptance(sample_media_files):
    """Verify that authentic MP4 screen recordings and PNG UI captures are accepted."""
    mp4_file = sample_media_files["mp4"]
    record = AssetGuardrailService.validate_candidate_file(
        file_path=mp4_file,
        asset_type=AssetType.SCREEN_RECORDING,
        tags=["tellos_demo", "screen_recording"],
    )
    assert record.review_status == ReviewStatus.APPROVED
    assert record.checksum_sha256 is not None
    assert len(record.checksum_sha256) == 64
    assert record.asset_type == AssetType.SCREEN_RECORDING

    png_file = sample_media_files["png"]
    record_png = AssetGuardrailService.validate_candidate_file(
        file_path=png_file,
        asset_type=AssetType.UI_CAPTURE,
    )
    assert record_png.review_status == ReviewStatus.APPROVED
    assert record_png.asset_type == AssetType.UI_CAPTURE

