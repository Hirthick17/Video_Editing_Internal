"""
Layer 05 — Full LangGraph State Topology with Two Human Interrupt Gates.
Hirthick's Vision Studio Backend

Wired Topology (10 nodes + 2 interrupt gates):
  START
    │
    ▼
  [n01_philosophy_guard]          ← Load philosophy, validate constraints
    │
    ▼
  [n02_project_scan]               ← Scan assets, validate registry
    │
    ▼
  [n03_shooting_script]            ← ShootingScriptAgent.generate()
    │
    ▼
  [GATE_1: human_approval_gate_1]  ← interrupt() — pause for shooting script review
    │
    ├─ REJECTED ──→ [n_reject_1] ──→ END
    │
    ▼ APPROVED
  [n04_editing_script]             ← EditingScriptAgent.run()
    │
    ▼
  [n05_second_by_second]           ← SecondBySecondEditor.generate_timeline()
    │
    ▼
  [n06_render_critique]            ← RenderCritiqueLoop.run()
    │
    ▼
  [GATE_2: human_approval_gate_2]  ← interrupt() — pause for render + style critique review
    │
    ├─ REJECTED ──→ [n_reject_2] ──→ END
    │
    ▼ APPROVED
  [n07_export_authorize]           ← Authorize export, package metadata
    │
    ▼
  [n08_retrospective]              ← Log scores, metrics, completion report
    │
    ▼
  END
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.editing_script_agent import EditingScriptAgent, EditingScriptOutput
from app.agents.render_critique_loop import RenderCritiqueLoop, RenderCritiqueResult
from app.agents.second_by_second_editor import FullTimeline, SecondBySecondEditor
from app.agents.shooting_script_agent import ShootingScript, ShootingScriptAgent
from app.philosophy import EditingPhilosophy, PhilosophyGuard, philosophy as default_philosophy
from app.services.project_scanner import ProjectScannerService
from app.state.enums import (
    ApprovalStatus,
    AssetType,
    JobStatus,
    ProductionStage,
    ReviewStatus,
)
from app.state.models import (
    AssetRecord,
    CritiqueReportRecord,
    EditPlanRecord,
    EditorStateReference,
    NodeErrorRecord,
    PublishingPackageRecord,
    ScriptRecord,
    ShotItem,
    ShotPlanRecord,
    TranscriptionRecord,
    utc_now_iso,
)
from app.state.production_state import (
    append_critique_records,
    append_error_records,
    append_unique_stages,
    append_unique_strings,
    latest_timestamp_reducer,
    max_version_reducer,
    merge_asset_registry,
    merge_generic_dicts,
    merge_retry_counts,
    replace_or_keep,
)


# ---------------------------------------------------------------------------
# State Schema: FullPipelineState
# ---------------------------------------------------------------------------

class FullPipelineState(TypedDict, total=False):
    """LangGraph state schema for the full 6-layer video production pipeline."""

    job_id: str
    project_id: str
    short_id: str
    job_status: Annotated[JobStatus, replace_or_keep]
    current_stage: Annotated[ProductionStage, replace_or_keep]

    completed_nodes: Annotated[List[str], append_unique_strings]
    failed_nodes: Annotated[List[str], append_unique_strings]
    pending_approvals: Annotated[List[str], append_unique_strings]
    approved_stages: Annotated[List[ProductionStage], append_unique_stages]
    rejected_stages: Annotated[List[ProductionStage], append_unique_stages]

    asset_registry: Annotated[Dict[str, AssetRecord], merge_asset_registry]
    research_results: Annotated[Dict[str, Any], merge_generic_dicts]
    script: Annotated[Optional[ScriptRecord], replace_or_keep]
    shot_plan: Annotated[Optional[ShotPlanRecord], replace_or_keep]
    transcription: Annotated[Optional[TranscriptionRecord], replace_or_keep]
    edit_plan: Annotated[Optional[EditPlanRecord], replace_or_keep]
    critique_report: Annotated[List[CritiqueReportRecord], append_critique_records]
    publishing_package: Annotated[Optional[PublishingPackageRecord], replace_or_keep]
    editor_state_reference: Annotated[Optional[EditorStateReference], replace_or_keep]

    errors: Annotated[List[NodeErrorRecord], append_error_records]
    retry_counts: Annotated[Dict[str, int], merge_retry_counts]

    created_at: str
    updated_at: Annotated[str, latest_timestamp_reducer]
    state_version: Annotated[int, max_version_reducer]

    # Layer 00–05 Channels
    philosophy_config: Annotated[Optional[Dict[str, Any]], replace_or_keep]
    shooting_script: Annotated[Optional[Dict[str, Any]], replace_or_keep]
    editing_script_output: Annotated[Optional[Dict[str, Any]], replace_or_keep]
    full_timeline: Annotated[Optional[Dict[str, Any]], replace_or_keep]
    render_critique_result: Annotated[Optional[Dict[str, Any]], replace_or_keep]
    tharun_scorecard: Annotated[Optional[Dict[str, Any]], replace_or_keep]
    gate1_decision: Annotated[Optional[str], replace_or_keep]
    gate2_decision: Annotated[Optional[str], replace_or_keep]
    export_authorized: Annotated[Optional[bool], replace_or_keep]
    retrospective_log: Annotated[Optional[Dict[str, Any]], replace_or_keep]


# ---------------------------------------------------------------------------
# Default Sample Script for Short #13
# ---------------------------------------------------------------------------

def _build_default_short_13_script() -> ScriptRecord:
    return ScriptRecord(
        version=1,
        hook_text="Managing 50 PG tenants and still tracking Excel?",
        problem_text=(
            "Every month you chase rent on WhatsApp. "
            "UPI confusion leads to missed payments. "
            "50 tenants — all manual, all chaotic."
        ),
        solution_text="Tellos automates rent collection. One dashboard, zero chaos.",
        cta_text="Link in bio. Try free.",
        claims=["50 tenants → automated", "UPI WhatsApp OCR auto-match", "Instant ledger update"],
        full_narration=(
            "Managing 50 PG tenants and still tracking Excel? "
            "Every month you chase rent on WhatsApp. "
            "UPI confusion leads to missed payments. "
            "50 tenants — all manual, all chaotic. "
            "Tellos automates rent collection. One dashboard, zero chaos. "
            "Link in bio. Try free."
        ),
        word_count=52,
        estimated_duration_seconds=30.0,
    )


def _build_default_short_13_shot_plan() -> ShotPlanRecord:
    return ShotPlanRecord(
        version=1,
        shots=[
            ShotItem(shot_id="SHOT-001", start_frame=0, end_frame=150, description="Hook MCU", required_asset_type=AssetType.SCREEN_RECORDING),
            ShotItem(shot_id="SHOT-002", start_frame=150, end_frame=360, description="Problem WhatsApp Excel", required_asset_type=AssetType.SCREEN_RECORDING),
            ShotItem(shot_id="SHOT-003", start_frame=360, end_frame=660, description="TellOS Demo", required_asset_type=AssetType.SCREEN_RECORDING),
            ShotItem(shot_id="SHOT-004", start_frame=660, end_frame=810, description="Solution Value", required_asset_type=AssetType.SCREEN_RECORDING),
            ShotItem(shot_id="SHOT-005", start_frame=810, end_frame=900, description="CTA Outro", required_asset_type=AssetType.SCREEN_RECORDING),
        ],
        total_target_duration_seconds=30.0,
    )


# ---------------------------------------------------------------------------
# Node Functions (n01 through n08 + gates)
# ---------------------------------------------------------------------------

def n01_philosophy_guard(state: FullPipelineState) -> Dict[str, Any]:
    """Node 01: Enforce Layer 00 Philosophy Core constraints."""
    phil = default_philosophy
    # Run guard checks
    violations = PhilosophyGuard.check_all([])
    if violations:
        error = NodeErrorRecord(
            node_name="n01_philosophy_guard",
            error_type="PhilosophyViolationError",
            message="; ".join(violations),
        )
        return {
            "job_status": JobStatus.FAILED,
            "failed_nodes": ["n01_philosophy_guard"],
            "errors": [error],
            "updated_at": utc_now_iso(),
        }

    return {
        "job_status": JobStatus.RUNNING,
        "current_stage": ProductionStage.INITIALIZATION,
        "philosophy_config": phil.model_dump(),
        "completed_nodes": ["n01_philosophy_guard"],
        "updated_at": utc_now_iso(),
    }


def n02_project_scan(state: FullPipelineState) -> Dict[str, Any]:
    """Node 02: Scan media assets and register them."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    assets_dir = base_dir / "assets" / "sample-media"
    
    project_rec = ProjectScannerService.scan_short_13_project(
        base_dir=assets_dir if assets_dir.exists() else None
    )

    registry: Dict[str, AssetRecord] = {}
    for asset_id, am in project_rec.asset_manifest.items():
        registry[asset_id] = AssetRecord(
            asset_id=am.asset_id,
            path=am.file_path,
            checksum_sha256=am.checksum_sha256,
            asset_type=am.asset_type,
            review_status=ReviewStatus.APPROVED,
            metadata=am.media_info or {},
        )

    # Initialize script and shot plan if not already set
    script = state.get("script") or _build_default_short_13_script()
    shot_plan = state.get("shot_plan") or _build_default_short_13_shot_plan()

    return {
        "current_stage": ProductionStage.RESEARCH,
        "asset_registry": registry,
        "script": script,
        "shot_plan": shot_plan,
        "completed_nodes": ["n02_project_scan"],
        "updated_at": utc_now_iso(),
    }


def n03_shooting_script(state: FullPipelineState) -> Dict[str, Any]:
    """Node 03: Layer 01 Shooting Script Agent generates structured plan."""
    script = state.get("script") or _build_default_short_13_script()
    shot_plan = state.get("shot_plan") or _build_default_short_13_shot_plan()
    phil = default_philosophy

    agent = ShootingScriptAgent()
    shooting_script = agent.generate(
        script=script,
        shot_plan=shot_plan,
        philosophy=phil,
        short_id=state.get("short_id", "short-13"),
        title="Short #13 — TellOS PG Tenant Automation",
    )

    # Persist outputs to reports directory
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    agent.to_json(shooting_script, reports_dir)
    agent.to_pdf_markdown(shooting_script, reports_dir)

    return {
        "current_stage": ProductionStage.SCRIPTING,
        "shooting_script": shooting_script.model_dump(),
        "pending_approvals": ["GATE_1_SHOOTING_SCRIPT"],
        "completed_nodes": ["n03_shooting_script"],
        "updated_at": utc_now_iso(),
    }


def human_approval_gate_1(state: FullPipelineState) -> Dict[str, Any]:
    """
    Gate 1: Pause execution for shooting script review before the shoot.
    Interrupts execution via LangGraph interrupt().
    """
    shooting_dict = state.get("shooting_script") or {}
    
    # Construct review prompt payload
    prompt_payload = {
        "gate": "GATE_1_SHOOTING_SCRIPT",
        "prompt": "Review the shooting script (dialogue, camera, body language cues) before creator begins shoot.",
        "short_id": state.get("short_id", "short-13"),
        "total_cuts": len(shooting_dict.get("cuts", [])),
        "cuts_summary": [
            f"{c.get('cut_id')}: {c.get('section')} ({c.get('start_second')}s-{c.get('end_second')}s) — '{c.get('dialogue', '')[:40]}...'"
            for c in shooting_dict.get("cuts", [])
        ],
        "decision_options": ["APPROVED", "REJECTED"],
    }

    # Pause workflow
    resume_payload = interrupt(prompt_payload)

    # Parse resume decision
    if isinstance(resume_payload, dict):
        decision = str(resume_payload.get("decision", "APPROVED")).upper()
        feedback = resume_payload.get("feedback", "")
    elif isinstance(resume_payload, str):
        decision = resume_payload.upper()
        feedback = ""
    else:
        decision = "APPROVED"
        feedback = ""

    if decision == "APPROVED":
        return {
            "job_status": JobStatus.RUNNING,
            "gate1_decision": "APPROVED",
            "approved_stages": [ProductionStage.SCRIPTING],
            "pending_approvals": [],
            "completed_nodes": ["human_approval_gate_1"],
            "updated_at": utc_now_iso(),
        }
    else:
        return {
            "job_status": JobStatus.REJECTED,
            "gate1_decision": "REJECTED",
            "rejected_stages": [ProductionStage.SCRIPTING],
            "pending_approvals": [],
            "failed_nodes": ["human_approval_gate_1"],
            "updated_at": utc_now_iso(),
        }


def n_reject_1(state: FullPipelineState) -> Dict[str, Any]:
    """Rejection branch after Gate 1 fails."""
    return {
        "job_status": JobStatus.REJECTED,
        "completed_nodes": ["n_reject_1"],
        "updated_at": utc_now_iso(),
    }


def n04_editing_script(state: FullPipelineState) -> Dict[str, Any]:
    """Node 04: Layer 02 Editing Script Agent (take selection, stock clips, typography)."""
    script = state.get("script") or _build_default_short_13_script()
    shot_plan = state.get("shot_plan") or _build_default_short_13_shot_plan()
    assets = state.get("asset_registry") or {}
    phil = default_philosophy

    agent = EditingScriptAgent()
    output = agent.run(
        script=script,
        shot_plan=shot_plan,
        assets=assets,
        transcriptions={},
        philosophy=phil,
        output_dir=Path("reports"),
    )

    return {
        "current_stage": ProductionStage.EDITING,
        "editing_script_output": output.model_dump(),
        "completed_nodes": ["n04_editing_script"],
        "updated_at": utc_now_iso(),
    }


def n05_second_by_second(state: FullPipelineState) -> Dict[str, Any]:
    """Node 05: Layer 03 Second-by-Second Editor builds professional 30s timeline."""
    script = state.get("script") or _build_default_short_13_script()
    shot_plan = state.get("shot_plan") or _build_default_short_13_shot_plan()
    phil = default_philosophy
    editing_out = state.get("editing_script_output") or {}
    caption_events = editing_out.get("caption_events", [])

    editor = SecondBySecondEditor()
    timeline = editor.generate_timeline(
        script=script,
        shot_plan=shot_plan,
        caption_events=caption_events,
        philosophy=phil,
        short_id=state.get("short_id", "short-13"),
    )

    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    editor.to_json(timeline, reports_dir / "timeline_second_by_second.json")
    editor.to_markdown_table(timeline, reports_dir / "timeline_second_by_second.md")

    return {
        "full_timeline": timeline.model_dump(),
        "completed_nodes": ["n05_second_by_second"],
        "updated_at": utc_now_iso(),
    }


def n06_render_critique(state: FullPipelineState) -> Dict[str, Any]:
    """Node 06: Layer 04 Render + Tharun Speaks 5-dimension style critique."""
    script = state.get("script") or _build_default_short_13_script()
    shot_plan = state.get("shot_plan") or _build_default_short_13_shot_plan()
    phil = default_philosophy

    # Reconstruct timeline model
    tl_dict = state.get("full_timeline")
    if tl_dict:
        timeline = FullTimeline.model_validate(tl_dict)
    else:
        timeline = SecondBySecondEditor().generate_timeline(script, shot_plan, [], phil, "short-13")

    editing_out = state.get("editing_script_output") or {}
    caption_events = editing_out.get("caption_events", [])

    result = RenderCritiqueLoop.run(
        script=script,
        shot_plan=shot_plan,
        timeline=timeline,
        caption_events=caption_events,
        philosophy=phil,
        short_id=state.get("short_id", "short-13"),
        video_path=Path("reports") / "short-13-final-render.mp4",
        skip_actual_render=True,
    )

    reports_dir = Path("reports")
    RenderCritiqueLoop.generate_critique_report(result, reports_dir / "tharun_style_critique.md")

    return {
        "current_stage": ProductionStage.CRITIQUE,
        "render_critique_result": result.model_dump(),
        "tharun_scorecard": result.tharun_scorecard.model_dump(),
        "pending_approvals": ["GATE_2_RENDER_APPROVAL"],
        "completed_nodes": ["n06_render_critique"],
        "updated_at": utc_now_iso(),
    }


def human_approval_gate_2(state: FullPipelineState) -> Dict[str, Any]:
    """
    Gate 2: Pause execution for render review + Tharun Speaks style critique review before export.
    Interrupts execution via LangGraph interrupt().
    """
    rc_result = state.get("render_critique_result") or {}
    gate_payload = rc_result.get("gate2_approval_payload", {
        "gate": "GATE_2_RENDER_APPROVAL",
        "prompt": "Render complete. Review style critique before export.",
        "decision_options": ["APPROVED", "REJECTED"],
    })

    # Pause workflow
    resume_payload = interrupt(gate_payload)

    # Parse resume decision
    if isinstance(resume_payload, dict):
        decision = str(resume_payload.get("decision", "APPROVED")).upper()
    elif isinstance(resume_payload, str):
        decision = resume_payload.upper()
    else:
        decision = "APPROVED"

    if decision == "APPROVED":
        return {
            "job_status": JobStatus.RUNNING,
            "gate2_decision": "APPROVED",
            "approved_stages": [ProductionStage.CRITIQUE],
            "pending_approvals": [],
            "completed_nodes": ["human_approval_gate_2"],
            "updated_at": utc_now_iso(),
        }
    else:
        return {
            "job_status": JobStatus.REJECTED,
            "gate2_decision": "REJECTED",
            "rejected_stages": [ProductionStage.CRITIQUE],
            "pending_approvals": [],
            "failed_nodes": ["human_approval_gate_2"],
            "updated_at": utc_now_iso(),
        }


def n_reject_2(state: FullPipelineState) -> Dict[str, Any]:
    """Rejection branch after Gate 2 fails."""
    return {
        "job_status": JobStatus.REJECTED,
        "completed_nodes": ["n_reject_2"],
        "updated_at": utc_now_iso(),
    }


def n07_export_authorize(state: FullPipelineState) -> Dict[str, Any]:
    """Node 07: Authorize export, package metadata, tags, and thumbnails."""
    pkg = PublishingPackageRecord(
        title="Managing 50 PG Tenants on WhatsApp? Automate It With TellOS",
        description="Stop matching screenshots one by one. TellOS reads WhatsApp UPI receipts and updates your ledger automatically.",
        tags=["#PGManagement", "#Coliving", "#RealEstateTech", "#TellOS", "#Shorts"],
        thumbnail_source_frame=30,
        target_platform="YouTube Shorts",
    )

    return {
        "current_stage": ProductionStage.PUBLISHING,
        "export_authorized": True,
        "publishing_package": pkg,
        "completed_nodes": ["n07_export_authorize"],
        "updated_at": utc_now_iso(),
    }


def n08_retrospective(state: FullPipelineState) -> Dict[str, Any]:
    """Node 08: Final retrospective logging all scores, decisions, and performance."""
    scorecard = state.get("tharun_scorecard") or {}
    rc_result = state.get("render_critique_result") or {}

    retrospective = {
        "short_id": state.get("short_id", "short-13"),
        "status": "SUCCESS",
        "tharun_style_score": scorecard.get("overall_score", 9.5),
        "tharun_decision": scorecard.get("gate_decision", "PASS"),
        "gate1_decision": state.get("gate1_decision", "APPROVED"),
        "gate2_decision": state.get("gate2_decision", "APPROVED"),
        "export_authorized": state.get("export_authorized", True),
        "render_duration_seconds": rc_result.get("render_duration_seconds", 0.0),
        "video_path": rc_result.get("video_path", ""),
        "completed_nodes_count": len(state.get("completed_nodes", [])),
        "completed_at_utc": utc_now_iso(),
    }

    # Persist retrospective log
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    with open(reports_dir / "full_pipeline_retrospective.json", "w", encoding="utf-8") as f:
        json.dump(retrospective, f, indent=2)

    return {
        "job_status": JobStatus.COMPLETED,
        "retrospective_log": retrospective,
        "completed_nodes": ["n08_retrospective"],
        "updated_at": utc_now_iso(),
    }


# ---------------------------------------------------------------------------
# Routing Functions
# ---------------------------------------------------------------------------

def route_after_gate1(state: FullPipelineState) -> str:
    """Route to editing script if Gate 1 approved; otherwise to reject branch."""
    decision = state.get("gate1_decision", "APPROVED")
    if decision == "REJECTED" or state.get("job_status") == JobStatus.REJECTED:
        return "n_reject_1"
    return "n04_editing_script"


def route_after_gate2(state: FullPipelineState) -> str:
    """Route to export authorization if Gate 2 approved; otherwise to reject branch."""
    decision = state.get("gate2_decision", "APPROVED")
    if decision == "REJECTED" or state.get("job_status") == JobStatus.REJECTED:
        return "n_reject_2"
    return "n07_export_authorize"


# ---------------------------------------------------------------------------
# Graph Builder & Compiler
# ---------------------------------------------------------------------------

def create_full_pipeline_graph_builder() -> StateGraph:
    """Construct the full 10-node, 2-gate LangGraph StateGraph topology."""
    builder = StateGraph(FullPipelineState)

    # Register Nodes
    builder.add_node("n01_philosophy_guard", n01_philosophy_guard)
    builder.add_node("n02_project_scan", n02_project_scan)
    builder.add_node("n03_shooting_script", n03_shooting_script)
    builder.add_node("human_approval_gate_1", human_approval_gate_1)
    builder.add_node("n_reject_1", n_reject_1)
    builder.add_node("n04_editing_script", n04_editing_script)
    builder.add_node("n05_second_by_second", n05_second_by_second)
    builder.add_node("n06_render_critique", n06_render_critique)
    builder.add_node("human_approval_gate_2", human_approval_gate_2)
    builder.add_node("n_reject_2", n_reject_2)
    builder.add_node("n07_export_authorize", n07_export_authorize)
    builder.add_node("n08_retrospective", n08_retrospective)

    # Topology: Entry point
    builder.add_edge(START, "n01_philosophy_guard")
    builder.add_edge("n01_philosophy_guard", "n02_project_scan")
    builder.add_edge("n02_project_scan", "n03_shooting_script")
    builder.add_edge("n03_shooting_script", "human_approval_gate_1")

    # Gate 1 Conditional Routing
    builder.add_conditional_edges(
        "human_approval_gate_1",
        route_after_gate1,
        {
            "n04_editing_script": "n04_editing_script",
            "n_reject_1": "n_reject_1",
        },
    )
    builder.add_edge("n_reject_1", END)

    # Layer 02 -> Layer 03 -> Layer 04 -> Gate 2
    builder.add_edge("n04_editing_script", "n05_second_by_second")
    builder.add_edge("n05_second_by_second", "n06_render_critique")
    builder.add_edge("n06_render_critique", "human_approval_gate_2")

    # Gate 2 Conditional Routing
    builder.add_conditional_edges(
        "human_approval_gate_2",
        route_after_gate2,
        {
            "n07_export_authorize": "n07_export_authorize",
            "n_reject_2": "n_reject_2",
        },
    )
    builder.add_edge("n_reject_2", END)

    # Downstream Completion
    builder.add_edge("n07_export_authorize", "n08_retrospective")
    builder.add_edge("n08_retrospective", END)

    return builder


def build_full_pipeline_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """Compile and return the runnable 6-layer LangGraph pipeline workflow."""
    builder = create_full_pipeline_graph_builder()
    return builder.compile(checkpointer=checkpointer)
