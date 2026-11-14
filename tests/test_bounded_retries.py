"""Test 7: Bounded node retries and error escalation."""

from app.orchestration.routing import should_retry
from app.persistence.repository import JobRepository
from app.state.enums import JobStatus, ProductionStage
from app.state.production_state import ProductionState


def test_bounded_retry_logic():
    """Verify that node retries are strictly bounded to max_retries (default 3)."""
    assert should_retry("inspect_media_node", current_retry_count=0, max_retries=3) is True
    assert should_retry("inspect_media_node", current_retry_count=1, max_retries=3) is True
    assert should_retry("inspect_media_node", current_retry_count=2, max_retries=3) is True
    assert should_retry("inspect_media_node", current_retry_count=3, max_retries=3) is False
    assert should_retry("inspect_media_node", current_retry_count=4, max_retries=3) is False


def test_repository_retry_escalation(temp_repo: JobRepository, sample_state: ProductionState):
    """Verify that SQLite tracks retries per node and allows resetting upon recovery."""
    temp_repo.create_job(sample_state)

    # Simulate 3 sequential failures
    for attempt in range(1, 4):
        count = temp_repo.record_node_retry(
            job_id=sample_state.job_id,
            node_name="transcribe_node",
            error_message=f"Network timeout attempt {attempt}",
        )
        assert count == attempt

    # Verify query
    current = temp_repo.get_node_retries(sample_state.job_id, "transcribe_node")
    assert current == 3
    assert should_retry("transcribe_node", current, max_retries=3) is False

    # Simulate eventual recovery and reset
    temp_repo.reset_node_retries(sample_state.job_id, "transcribe_node")
    assert temp_repo.get_node_retries(sample_state.job_id, "transcribe_node") == 0
    assert should_retry("transcribe_node", 0, max_retries=3) is True

