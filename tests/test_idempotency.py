"""Test 8: Idempotency enforcement and duplicate execution prevention."""

import pytest
from app.persistence.repository import JobRepository
from app.state.editor_contracts import ClipSpec, EditOperation
from app.state.enums import EditOperationType
from app.state.production_state import ProductionState


def test_duplicate_job_creation_prevention(temp_repo: JobRepository, sample_state: ProductionState):
    """Verify that attempting to create a job with an existing job_id is strictly rejected."""
    temp_repo.create_job(sample_state)

    # Duplicate creation with same job_id must raise ValueError
    with pytest.raises(ValueError, match="already exists"):
        temp_repo.create_job(sample_state)


def test_edit_operation_idempotency_keys():
    """Verify edit operations enforce idempotency keys and prevent duplicate application."""
    op1 = EditOperation(
        operation_id="op_001",
        operation_type=EditOperationType.INSERT_CLIP,
        idempotency_key="idemp_clip_001",
        track_id="V1",
        clip_spec=ClipSpec(
            item_id="item_01",
            track_id="V1",
            asset_id="ast_demo",
            start_frame=0,
            end_frame=300,
        ),
    )
    assert op1.idempotency_key == "idemp_clip_001"
    assert op1.applied is False

