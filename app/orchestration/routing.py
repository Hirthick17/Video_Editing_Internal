"""Conditional routing predicates and retry logic for the LangGraph workflow."""

from app.config import settings
from app.state.enums import JobStatus
from app.state.production_state import ProductionGraphState


def route_after_validation(state: ProductionGraphState) -> str:
    """Route to human approval gate if valid, or failure handler if validation failed."""
    if state.get("job_status") == JobStatus.FAILED or state.get("failed_nodes"):
        return "handle_failure_node"
    return "human_approval_gate"


def route_after_approval(state: ProductionGraphState) -> str:
    """Route downstream if human approved, or rejection handler if declined."""
    if state.get("job_status") == JobStatus.REJECTED or "human_approval_gate" in state.get(
        "failed_nodes", []
    ):
        return "handle_rejection_node"
    return "resume_workflow_node"


def should_retry(
    node_name: str,
    current_retry_count: int,
    max_retries: int = settings.max_node_retries,
) -> bool:
    """Determine whether a node failure is eligible for bounded retry."""
    return current_retry_count < max_retries

