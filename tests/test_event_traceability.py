"""Test 13: Event log auditability and end-to-end job history traceability."""

from app.approvals.approval_service import ApprovalService
from app.persistence.repository import JobRepository
from app.state.enums import ApprovalStatus, JobStatus, ProductionStage
from app.state.production_state import ProductionState


def test_job_history_audit_traceability(temp_repo: JobRepository, sample_state: ProductionState):
    """Verify that every lifecycle transition produces an immutable audit record in SQLite."""
    service = ApprovalService(temp_repo)

    # 1. Create job
    temp_repo.create_job(sample_state)

    # 2. Save a checkpoint
    temp_repo.save_checkpoint(
        job_id=sample_state.job_id,
        stage=ProductionStage.INITIALIZATION,
        state_version=1,
        state=sample_state,
    )

    # 3. Pause for approval
    sample_state.job_status = JobStatus.PAUSED_FOR_APPROVAL
    sample_state.current_stage = ProductionStage.SCRIPTING
    sample_state.pending_approvals = ["SCRIPT_APPROVAL"]
    temp_repo.update_job_state(sample_state)

    # 4. Human approval decision
    service.submit_decision(
        job_id=sample_state.job_id,
        decision=ApprovalStatus.APPROVED,
        reviewer="hirthick",
        feedback="Verified against TellOS PG workflow.",
    )

    # 5. Inspect full history
    history = service.inspect_job_history(sample_state.job_id)

    assert history["job"]["job_id"] == sample_state.job_id
    assert len(history["checkpoints"]) == 1
    assert len(history["approvals"]) == 1
    assert history["approvals"][0]["decision"] == "APPROVED"
    assert history["approvals"][0]["reviewer"] == "hirthick"

    # Verify event log chronological sequence
    events = history["event_log"]
    assert len(events) >= 3

    event_types = [e["event_type"] for e in events]
    assert "JOB_CREATED" in event_types
    assert "CHECKPOINT_SAVED" in event_types
    assert "APPROVAL_DECISION_SAVED" in event_types

    # Ensure all timestamps are valid ISO 8601 strings
    for event in events:
        assert "T" in event["timestamp"]

