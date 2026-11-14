"""StateGraph construction and compilation for Hirthick's Vision Studio."""

import sqlite3
from typing import Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.orchestration.nodes import (
    complete_job_node,
    handle_failure_node,
    handle_rejection_node,
    human_approval_gate,
    load_project_node,
    merge_validation_node,
    resume_workflow_node,
    validate_asset_registry,
    validate_project_metadata,
)
from app.orchestration.routing import route_after_approval, route_after_validation
from app.state.production_state import ProductionGraphState


def create_production_graph_builder() -> StateGraph:
    """Build the uncompiled StateGraph topology with parallel branches and conditional edges."""
    builder = StateGraph(ProductionGraphState)

    # Register nodes
    builder.add_node("load_project_node", load_project_node)
    builder.add_node("validate_project_metadata", validate_project_metadata)
    builder.add_node("validate_asset_registry", validate_asset_registry)
    builder.add_node("merge_validation_node", merge_validation_node)
    builder.add_node("human_approval_gate", human_approval_gate)
    builder.add_node("resume_workflow_node", resume_workflow_node)
    builder.add_node("complete_job_node", complete_job_node)
    builder.add_node("handle_rejection_node", handle_rejection_node)
    builder.add_node("handle_failure_node", handle_failure_node)

    # Topology: Entry point to load_project
    builder.add_edge(START, "load_project_node")

    # Parallel branching: Node A and Node B
    builder.add_edge("load_project_node", "validate_project_metadata")
    builder.add_edge("load_project_node", "validate_asset_registry")

    # Fan-in merge
    builder.add_edge("validate_project_metadata", "merge_validation_node")
    builder.add_edge("validate_asset_registry", "merge_validation_node")

    # Conditional routing after validation (proceed to approval gate or failure)
    builder.add_conditional_edges(
        "merge_validation_node",
        route_after_validation,
        {
            "human_approval_gate": "human_approval_gate",
            "handle_failure_node": "handle_failure_node",
        },
    )

    # Conditional routing after human approval (proceed to resume or rejection)
    builder.add_conditional_edges(
        "human_approval_gate",
        route_after_approval,
        {
            "resume_workflow_node": "resume_workflow_node",
            "handle_rejection_node": "handle_rejection_node",
        },
    )

    # Downstream flow to completion
    builder.add_edge("resume_workflow_node", "complete_job_node")
    builder.add_edge("complete_job_node", END)
    builder.add_edge("handle_rejection_node", END)
    builder.add_edge("handle_failure_node", END)

    return builder


def build_production_graph(
    checkpointer: Optional[BaseCheckpointSaver] = None,
    sqlite_conn: Optional[sqlite3.Connection] = None,
):
    """
    Compile and return the runnable LangGraph workflow.
    If sqlite_conn is provided, wraps it with SqliteSaver.
    """
    builder = create_production_graph_builder()

    if checkpointer is None and sqlite_conn is not None:
        saver = SqliteSaver(sqlite_conn)
        saver.setup()
        checkpointer = saver

    return builder.compile(checkpointer=checkpointer)

