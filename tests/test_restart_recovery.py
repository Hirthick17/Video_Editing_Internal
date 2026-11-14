"""Test 6: Process restart recovery and resumption from persisted SQLite checkpoints."""

import sqlite3
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from app.orchestration.graph import build_production_graph
from app.state.enums import JobStatus, ProductionStage


def test_resume_across_process_restart(tmp_path: Path):
    """Verify that a paused job survives application restart and resumes from persisted SQLite state."""
    db_file = tmp_path / "restart_checkpoint_test.db"

    # =========================================================================
    # Process 1: Start job and run until interrupt
    # =========================================================================
    conn1 = sqlite3.connect(str(db_file), check_same_thread=False)
    checkpointer1 = SqliteSaver(conn1)
    checkpointer1.setup()

    graph1 = build_production_graph(checkpointer=checkpointer1)
    job_id = "job_restart_recovery_01"
    config = {"configurable": {"thread_id": job_id}}

    initial_state = {
        "job_id": job_id,
        "project_id": "proj_p1",
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

    graph1.invoke(initial_state, config=config)

    # Verify process 1 reached approval gate
    state1 = graph1.get_state(config)
    assert state1.values["job_status"] == JobStatus.PAUSED_FOR_APPROVAL
    assert "merge_validation_node" in state1.values["completed_nodes"]

    # Terminate process 1
    conn1.close()
    del graph1
    del checkpointer1
    del conn1

    # =========================================================================
    # Process 2: Fresh start, reconnect to existing SQLite checkpoint file
    # =========================================================================
    conn2 = sqlite3.connect(str(db_file), check_same_thread=False)
    checkpointer2 = SqliteSaver(conn2)
    # Checkpointer reads existing schema without data destruction
    checkpointer2.setup()

    graph2 = build_production_graph(checkpointer=checkpointer2)

    # Recover state without re-running initialization
    recovered_state = graph2.get_state(config)
    assert recovered_state.values is not None
    assert recovered_state.values["job_id"] == job_id
    assert recovered_state.values["job_status"] == JobStatus.PAUSED_FOR_APPROVAL
    assert "load_project_node" in recovered_state.values["completed_nodes"]
    assert "validate_project_metadata" in recovered_state.values["completed_nodes"]
    assert "validate_asset_registry" in recovered_state.values["completed_nodes"]

    # Resume execution in process 2
    resume_payload = {
        "decision": "APPROVED",
        "reviewer": "hirthick_recovery_test",
        "feedback": "Resumed post-restart.",
    }
    graph2.invoke(Command(resume=resume_payload), config=config)

    final_state = graph2.get_state(config)
    assert final_state.values["job_status"] == JobStatus.COMPLETED
    assert "resume_workflow_node" in final_state.values["completed_nodes"]
    assert "complete_job_node" in final_state.values["completed_nodes"]

    conn2.close()

