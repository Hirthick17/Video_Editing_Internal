"""Deterministic and agent node functions for graph workflow execution."""

from pathlib import Path
from typing import Any, Dict
from langgraph.types import interrupt

from app.services.asset_guardrail import AssetGuardrailService, AssetGuardrailViolationError
from app.state.enums import ApprovalStatus, AssetType, JobStatus, ProductionStage
from app.state.models import NodeErrorRecord, utc_now_iso
from app.state.production_state import ProductionGraphState


def load_project_node(state: ProductionGraphState) -> Dict[str, Any]:
    """Initialize or load project context and set running status."""
    return {
        "job_status": JobStatus.RUNNING,
        "current_stage": ProductionStage.INITIALIZATION,
        "completed_nodes": ["load_project_node"],
        "updated_at": utc_now_iso(),
    }


def validate_project_metadata(state: ProductionGraphState) -> Dict[str, Any]:
    """Parallel Node A: Validate project metadata, identifiers, and format."""
    project_id = state.get("project_id", "")
    short_id = state.get("short_id", "")

    if not project_id or not short_id:
        error = NodeErrorRecord(
            node_name="validate_project_metadata",
            error_type="ValidationError",
            message="Missing required project_id or short_id",
        )
        return {
            "failed_nodes": ["validate_project_metadata"],
            "errors": [error],
            "updated_at": utc_now_iso(),
        }

    meta_results = {
        "metadata_validated": True,
        "target_aspect_ratio": "9:16",
        "target_resolution": "1080x1920",
        "target_fps": 30,
        "target_duration_seconds": 30.0,
    }

    return {
        "completed_nodes": ["validate_project_metadata"],
        "research_results": meta_results,
        "updated_at": utc_now_iso(),
    }


def validate_asset_registry(state: ProductionGraphState) -> Dict[str, Any]:
    """Parallel Node B: Validate assets against authentic media guardrails (rejecting SVGs/synthetic clips)."""
    registry = state.get("asset_registry", {})
    failed = False
    errors = []

    for asset_id, asset in registry.items():
        # Check against guardrail
        try:
            p = Path(asset.path)
            if p.is_file():
                # Runs extension, XML header, and keyword checks
                AssetGuardrailService.validate_candidate_file(
                    file_path=p,
                    asset_type=asset.asset_type,
                    tags=asset.metadata.get("tags", []),
                    asset_id=asset.asset_id,
                )
            elif asset.asset_type == AssetType.PROHIBITED_SYNTHETIC or p.suffix.lower() == ".svg":
                raise AssetGuardrailViolationError(
                    f"Asset '{asset.path}' is flagged as prohibited synthetic media / SVG."
                )
        except Exception as e:
            failed = True
            errors.append(
                NodeErrorRecord(
                    node_name="validate_asset_registry",
                    error_type=type(e).__name__,
                    message=str(e),
                )
            )

    if failed:
        return {
            "failed_nodes": ["validate_asset_registry"],
            "errors": errors,
            "updated_at": utc_now_iso(),
        }

    return {
        "completed_nodes": ["validate_asset_registry"],
        "research_results": {"asset_registry_validated": True, "asset_count": len(registry)},
        "updated_at": utc_now_iso(),
    }


def merge_validation_node(state: ProductionGraphState) -> Dict[str, Any]:
    """Merge parallel validation branch results and set up human approval stage."""
    failed_nodes = state.get("failed_nodes", [])
    if failed_nodes:
        return {
            "job_status": JobStatus.FAILED,
            "completed_nodes": ["merge_validation_node"],
            "updated_at": utc_now_iso(),
        }

    return {
        "job_status": JobStatus.PAUSED_FOR_APPROVAL,
        "current_stage": ProductionStage.SCRIPTING,
        "pending_approvals": ["SCRIPT_APPROVAL"],
        "completed_nodes": ["merge_validation_node"],
        "updated_at": utc_now_iso(),
    }


def human_approval_gate(state: ProductionGraphState) -> Dict[str, Any]:
    """
    Pause execution for human approval review via LangGraph interrupt.
    When resumed with a Command(resume={...}), records decision and routes workflow.
    """
    pending = state.get("pending_approvals", [])
    current_stage = state.get("current_stage", ProductionStage.INITIALIZATION)

    # Interrupt execution and wait for human input
    resume_payload = interrupt(
        {
            "job_id": state.get("job_id"),
            "stage": current_stage.value if hasattr(current_stage, "value") else str(current_stage),
            "pending_approvals": pending,
            "prompt": f"Review and approve stage '{current_stage}' before proceeding.",
        }
    )

    # Normalize resume payload
    if isinstance(resume_payload, dict):
        decision_str = str(resume_payload.get("decision", "APPROVED")).upper()
        reviewer = resume_payload.get("reviewer", "human_operator")
        feedback = resume_payload.get("feedback", "")
    elif isinstance(resume_payload, str):
        decision_str = resume_payload.upper()
        reviewer = "human_operator"
        feedback = ""
    else:
        decision_str = "APPROVED"
        reviewer = "human_operator"
        feedback = ""

    if decision_str == "APPROVED":
        return {
            "job_status": JobStatus.RUNNING,
            "approved_stages": [current_stage],
            "pending_approvals": [],
            "completed_nodes": ["human_approval_gate"],
            "research_results": {
                "last_approval": {
                    "decision": "APPROVED",
                    "reviewer": reviewer,
                    "feedback": feedback,
                }
            },
            "updated_at": utc_now_iso(),
        }
    else:
        return {
            "job_status": JobStatus.REJECTED,
            "rejected_stages": [current_stage],
            "pending_approvals": [],
            "failed_nodes": ["human_approval_gate"],
            "research_results": {
                "last_approval": {
                    "decision": "REJECTED",
                    "reviewer": reviewer,
                    "feedback": feedback,
                }
            },
            "updated_at": utc_now_iso(),
        }


def resume_workflow_node(state: ProductionGraphState) -> Dict[str, Any]:
    """Post-approval workflow node advancing to downstream production."""
    return {
        "current_stage": ProductionStage.EDITING,
        "completed_nodes": ["resume_workflow_node"],
        "updated_at": utc_now_iso(),
    }


def complete_job_node(state: ProductionGraphState) -> Dict[str, Any]:
    """Mark production job as successfully completed."""
    return {
        "job_status": JobStatus.COMPLETED,
        "completed_nodes": ["complete_job_node"],
        "updated_at": utc_now_iso(),
    }


def handle_rejection_node(state: ProductionGraphState) -> Dict[str, Any]:
    """Handle rejection branch when human operator declines approval."""
    return {
        "job_status": JobStatus.REJECTED,
        "completed_nodes": ["handle_rejection_node"],
        "updated_at": utc_now_iso(),
    }


def handle_failure_node(state: ProductionGraphState) -> Dict[str, Any]:
    """Handle fatal failure or unrecoverable node errors."""
    return {
        "job_status": JobStatus.FAILED,
        "completed_nodes": ["handle_failure_node"],
        "updated_at": utc_now_iso(),
    }

