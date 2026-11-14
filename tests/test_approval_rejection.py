"""Test 5: Human approval rejection branch and workflow termination."""

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from app.orchestration.graph import build_production_graph
from app.state.enums import JobStatus, ProductionStage


def test_human_approval_rejection_routing():
    """Verify that a rejected human approval routes to rejection handler and halts execution."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()

    graph = build_production_graph(checkpointer=checkpointer)

    job_id = "test_job_rejection_01"
    config = {"configurable": {"thread_id": job_id}}

    initial_state = {
        "job_id": job_id,
        "project_id": "proj_001",
        "short_id": "short_13",
        "job_status": JobStatus.CREATED,
        "current_stage": ProductionStage.INITIALIZATION,
        "completed_nodes": [],
        "failed_nodes": [],
        "pending_approvals": [],
        "approved_stages": [],
        "rejected_stages": [],
        "asset_registry": {},
        "research_results": {},
        "errors": [],
        "retry_counts": {},
        "created_at": "2026-11-13T12:00:00Z",
        "updated_at": "2026-11-13T12:00:00Z",
        "state_version": 1,
    }

    # Run until approval interrupt
    graph.invoke(initial_state, config=config)

    # Resume with REJECTED decision
    rejection_payload = {
        "decision": "REJECTED",
        "reviewer": "hirthick",
        "feedback": "Hook text needs revision before continuing.",
    }
    graph.invoke(Command(resume=rejection_payload), config=config)

    # Verify state routed to rejection
    snapshot = graph.get_state(config)
    values = snapshot.values

    assert values["job_status"] == JobStatus.REJECTED
    assert ProductionStage.SCRIPTING in values["rejected_stages"]
    assert "handle_rejection_node" in values["completed_nodes"]
    assert "resume_workflow_node" not in values["completed_nodes"]
    assert "complete_job_node" not in values["completed_nodes"]

