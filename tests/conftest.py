"""Shared pytest fixtures for Hirthick's Vision Studio Phase 1 test suite."""

import os
import tempfile
from pathlib import Path
from typing import Generator
import pytest

from app.persistence.database import DatabaseManager
from app.persistence.repository import JobRepository
from app.state.enums import AssetType, JobStatus, ProductionStage, ReviewStatus
from app.state.models import AssetRecord
from app.state.production_state import ProductionState


@pytest.fixture
def temp_db() -> Generator[DatabaseManager, None, None]:
    """Provide a fresh in-memory SQLite database initialized with schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name

    db = DatabaseManager(temp_path)
    db.initialize_schema()
    try:
        yield db
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@pytest.fixture
def temp_repo(temp_db: DatabaseManager) -> JobRepository:
    """Provide a JobRepository connected to the temporary database."""
    return JobRepository(temp_db)


@pytest.fixture
def sample_state() -> ProductionState:
    """Provide a valid canonical ProductionState fixture."""
    return ProductionState(
        job_id="job_short_13_test",
        project_id="8a894b86-d5e0-4222-ab88-df22a8e2168e",
        short_id="short_13_whatsapp_pg_rent",
        job_status=JobStatus.CREATED,
        current_stage=ProductionStage.INITIALIZATION,
    )


@pytest.fixture
def sample_media_files(tmp_path: Path):
    """Provide temporary test files: authentic MP4, PNG, and a prohibited SVG."""
    real_mp4 = tmp_path / "tellos_demo_recording.mp4"
    # Write a dummy MP4 header/bytes
    real_mp4.write_bytes(b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41" + b"\x00" * 1024)

    real_png = tmp_path / "ui_screenshot.png"
    # Write dummy PNG bytes
    real_png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 512)

    prohibited_svg = tmp_path / "card1_hook.svg"
    prohibited_svg.write_text("<svg width='1080' height='1920'><text>Hook Card</text></svg>", encoding="utf-8")

    return {
        "mp4": real_mp4,
        "png": real_png,
        "svg": prohibited_svg,
    }

