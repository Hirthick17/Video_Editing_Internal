"""Test 4: SQLite persistence, transactions, and event log auditing."""

import pytest
from app.persistence.database import DatabaseManager
from app.persistence.repository import JobRepository
from app.state.enums import ApprovalStatus, JobStatus, ProductionStage
from app.state.models import ApprovalRecord
from app.state.production_state import ProductionState


def test_job_create_and_get(temp_repo: JobRepository, sample_state: ProductionState):
    """Verify job can be created and retrieved from SQLite."""
    created = temp_repo.create_job(sample_state)
    assert created.job_id == sample_state.job_id

    retrieved = temp_repo.get_job(sample_state.job_id)
    assert retrieved is not None
    assert retrieved.job_id == sample_state.job_id
    assert retrieved.project_id == sample_state.project_id
    assert retrieved.job_status == JobStatus.CREATED


def test_job_state_update(temp_repo: JobRepository, sample_state: ProductionState):
    """Verify job state can be updated, bumped, and retrieved."""
    temp_repo.create_job(sample_state)

    sample_state.job_status = JobStatus.RUNNING
    sample_state.current_stage = ProductionStage.SCRIPTING
    sample_state.completed_nodes = ["load_project_node"]
    temp_repo.update_job_state(sample_state)

    updated = temp_repo.get_job(sample_state.job_id)
    assert updated.job_status == JobStatus.RUNNING
    assert updated.current_stage == ProductionStage.SCRIPTING
    assert updated.state_version == 2
    assert "load_project_node" in updated.completed_nodes


def test_checkpoint_saving(temp_repo: JobRepository, sample_state: ProductionState):
    """Verify checkpoints are saved and queryable."""
    temp_repo.create_job(sample_state)

    chk_id = temp_repo.save_checkpoint(
        job_id=sample_state.job_id,
        stage=ProductionStage.INITIALIZATION,
        state_version=1,
        state=sample_state,
    )
    assert chk_id.startswith("chk_")

    checkpoints = temp_repo.get_checkpoints(sample_state.job_id)
    assert len(checkpoints) == 1
    assert checkpoints[0]["checkpoint_id"] == chk_id
    assert checkpoints[0]["stage"] == "INITIALIZATION"


def test_event_log_audit(temp_repo: JobRepository, sample_state: ProductionState):
    """Verify event log records all lifecycle events chronologically."""
    temp_repo.create_job(sample_state)
    temp_repo.record_event(
        job_id=sample_state.job_id,
        event_type="NODE_EXECUTED",
        node_name="node_a",
        payload={"duration_ms": 42},
    )

    events = temp_repo.get_event_log(sample_state.job_id)
    # 1 event from create_job + 1 explicit event
    assert len(events) >= 2
    assert events[0]["event_type"] == "JOB_CREATED"
    assert events[1]["event_type"] == "NODE_EXECUTED"
    assert events[1]["node_name"] == "node_a"
    assert events[1]["payload"]["duration_ms"] == 42


def test_approval_record_persistence(temp_repo: JobRepository, sample_state: ProductionState):
    """Verify approval records persist and reflect reviewer decisions."""
    temp_repo.create_job(sample_state)

    record = ApprovalRecord(
        approval_id="appr_01",
        stage=ProductionStage.SCRIPTING,
        decision=ApprovalStatus.APPROVED,
        reviewer="hirthick",
        feedback="Script is engaging and strictly factual.",
        decided_at_utc="2026-11-13T12:00:00Z",
    )
    temp_repo.save_approval(record, job_id=sample_state.job_id)

    approvals = temp_repo.get_approvals(sample_state.job_id)
    assert len(approvals) == 1
    assert approvals[0].approval_id == "appr_01"
    assert approvals[0].decision == ApprovalStatus.APPROVED
    assert approvals[0].reviewer == "hirthick"


def test_node_retries_tracking(temp_repo: JobRepository, sample_state: ProductionState):
    """Verify retry counting, incrementing, and resetting."""
    temp_repo.create_job(sample_state)

    c1 = temp_repo.record_node_retry(sample_state.job_id, "render_node", "timeout")
    assert c1 == 1
    c2 = temp_repo.record_node_retry(sample_state.job_id, "render_node", "timeout 2")
    assert c2 == 2

    assert temp_repo.get_node_retries(sample_state.job_id, "render_node") == 2

    temp_repo.reset_node_retries(sample_state.job_id, "render_node")
    assert temp_repo.get_node_retries(sample_state.job_id, "render_node") == 0


def test_transaction_rollback_on_error(temp_db: DatabaseManager):
    """Verify that failed transactions roll back cleanly."""
    with pytest.raises(RuntimeError):
        with temp_db.transaction() as conn:
            conn.execute(
                "INSERT INTO jobs (job_id, project_id, short_id, status, stage, state_version, state_json, created_at, updated_at) "
                "VALUES ('fail_job', 'p', 's', 'CREATED', 'INITIALIZATION', 1, '{}', 'now', 'now')"
            )
            raise RuntimeError("Forced simulation error")

    with temp_db.transaction() as conn:
        cursor = conn.execute("SELECT * FROM jobs WHERE job_id = 'fail_job'")
        assert cursor.fetchone() is None

