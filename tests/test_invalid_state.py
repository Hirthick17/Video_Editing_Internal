"""Test 9: Rejection of corrupted, incomplete, or invalid state data."""

import pytest
from pydantic import ValidationError

from app.state.editor_contracts import ClipSpec, TimelineSpec
from app.state.enums import JobStatus
from app.state.production_state import ProductionState


def test_blank_identifier_rejection():
    """Verify that blank or empty identifiers are rejected by ProductionState."""
    with pytest.raises(ValidationError):
        ProductionState(job_id="", project_id="proj", short_id="short")

    with pytest.raises(ValidationError):
        ProductionState(job_id="job", project_id="   ", short_id="short")


def test_invalid_enum_rejection():
    """Verify that unsupported enum strings are rejected."""
    with pytest.raises(ValidationError):
        ProductionState(
            job_id="j",
            project_id="p",
            short_id="s",
            job_status="NON_EXISTENT_STATUS",  # type: ignore
        )


def test_invalid_timeline_dimensions():
    """Verify that negative or zero dimensions are rejected by TimelineSpec."""
    with pytest.raises(ValidationError):
        TimelineSpec(width=-1080, height=1920, fps=30)

    with pytest.raises(ValidationError):
        TimelineSpec(width=1080, height=1920, fps=0)


def test_invalid_frame_intervals():
    """Verify that inverted or zero-length frame intervals are rejected by ClipSpec."""
    # end_frame <= start_frame
    with pytest.raises(ValidationError):
        ClipSpec(
            item_id="clip_err",
            track_id="V1",
            asset_id="ast_1",
            start_frame=100,
            end_frame=100,
        )

    # inverted interval
    with pytest.raises(ValidationError):
        ClipSpec(
            item_id="clip_err",
            track_id="V1",
            asset_id="ast_1",
            start_frame=200,
            end_frame=100,
        )

    # negative start frame
    with pytest.raises(ValidationError):
        ClipSpec(
            item_id="clip_err",
            track_id="V1",
            asset_id="ast_1",
            start_frame=-10,
            end_frame=100,
        )

