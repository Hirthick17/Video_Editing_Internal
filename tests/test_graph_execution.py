"""Test 3: End-to-end graph execution, parallel execution, human approval pause, and resume."""

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from app.orchestration.graph import build_production_graph
from app.services.asset_guardrail import AssetGuardrailService
from app.state.enums import AssetType, JobStatus, ProductionStage


def test_graph_parallel_branches_pause_and_resume(sample_media_files):
    """
    Test the full Phase 1 graph:
    Create Job -> Validate State (Parallel Node A & Node B) -> Merge -> Human Approval Gate (Interrupt) -> Resume -> Complete.
    """
    real_mp4 = sample_media_files["mp4"]
    asset = AssetGuardrailService.validate_candidate_file(
        file_path=real_mp4,
        asset_type=AssetType.SCREEN_RECORDING,
        asset_id="ast_tellos_demo",
    )

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()

    graph = build_production_graph(checkpointer=checkpointer)

    job_id = "test_job_full_flow_01"
    config = {"configurable": {"thread_id": job_id}}

    initial_state = {
        "job_id": job_id,
        "project_id": "proj_tellos_01",
        "short_id": "short_13",
        "job_status": JobStatus.CREATED,
        "current_stage": ProductionStage.INITIALIZATION,
        "completed_nodes": [],
        "failed_nodes": [],
        "pending_approvals": [],
        "approved_stages": [],
        "rejected_stages": [],
        "asset_registry": {"ast_tellos_demo": asset},
        "research_results": {},
        "errors": [],
        "retry_counts": {},
        "created_at": "2026-11-13T12:00:00Z",
        "updated_at": "2026-11-13T12:00:00Z",
        "state_version": 1,
    }

    # Step 1: Run graph up to the human approval interrupt
    graph.invoke(initial_state, config=config)

    # Inspect paused state
    snapshot = graph.get_state(config)
    paused_values = snapshot.values

    # Assert parallel branch completion and fan-in
    assert "load_project_node" in paused_values["completed_nodes"]
    assert "validate_project_metadata" in paused_values["completed_nodes"]
    assert "validate_asset_registry" in paused_values["completed_nodes"]
    assert "merge_validation_node" in paused_values["completed_nodes"]
    assert paused_values["job_status"] == JobStatus.PAUSED_FOR_APPROVAL
    assert "SCRIPT_APPROVAL" in paused_values["pending_approvals"]

    # Assert interrupt presence
    assert len(snapshot.tasks) > 0
    assert any(task.interrupts for task in snapshot.tasks)

    # Step 2: Resume with approved decision
    resume_payload = {
        "decision": "APPROVED",
        "reviewer": "hirthick",
        "feedback": "Metadata and TellOS demo verified.",
    }
    resumed_result = graph.invoke(Command(resume=resume_payload), config=config)

    # Assert downstream execution and completion
    final_snapshot = graph.get_state(config)
    final_values = final_snapshot.values

    assert final_values["job_status"] == JobStatus.COMPLETED
    assert final_values["current_stage"] == ProductionStage.EDITING
    assert "human_approval_gate" in final_values["completed_nodes"]
    assert "resume_workflow_node" in final_values["completed_nodes"]
    assert "complete_job_node" in final_values["completed_nodes"]
    assert ProductionStage.SCRIPTING in final_values["approved_stages"]
    assert len(final_values["failed_nodes"]) == 0

