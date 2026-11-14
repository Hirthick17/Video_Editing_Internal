"""Human approval gatekeeper service managing review, decisions, and graph resumption."""

import uuid
from typing import Any, Dict, Optional
from langgraph.types import Command

from app.persistence.repository import JobRepository
from app.state.enums import ApprovalStatus, JobStatus, ProductionStage
from app.state.models import ApprovalRecord, utc_now_iso
from app.state.production_state import ProductionState


class ApprovalService:
    """Coordinates human review requests, audit records, and workflow resumption."""

    def __init__(self, repository: Optional[JobRepository] = None):
        self.repo = repository or JobRepository()

    def get_pending_approval(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Fetch details of a pending approval gate for the specified job."""
        job = self.repo.get_job(job_id)
        if not job:
            raise ValueError(f"Job '{job_id}' not found")

        if job.job_status != JobStatus.PAUSED_FOR_APPROVAL and not job.pending_approvals:
            return None

        return {
            "job_id": job.job_id,
            "project_id": job.project_id,
            "short_id": job.short_id,
            "current_stage": job.current_stage.value,
            "pending_approvals": job.pending_approvals,
            "state_version": job.state_version,
            "updated_at": job.updated_at,
        }

    def submit_decision(
        self,
        job_id: str,
        decision: ApprovalStatus,
        reviewer: str,
        feedback: str = "",
        graph: Optional[Any] = None,
    ) -> ProductionState:
        """Record human approval decision and resume graph execution."""
        job = self.repo.get_job(job_id)
        if not job:
            raise ValueError(f"Job '{job_id}' not found")

        approval_id = f"appr_{uuid.uuid4().hex[:10]}"
        now_utc = utc_now_iso()

        record = ApprovalRecord(
            approval_id=approval_id,
            stage=job.current_stage,
            decision=decision,
            reviewer=reviewer,
            feedback=feedback,
            created_at_utc=now_utc,
            decided_at_utc=now_utc,
        )
        self.repo.save_approval(record, job_id=job_id)

        # Resume the graph if provided
        if graph is not None:
            config = {"configurable": {"thread_id": job_id}}
            resume_cmd = Command(
                resume={
                    "decision": decision.value,
                    "reviewer": reviewer,
                    "feedback": feedback,
                }
            )
            result = graph.invoke(resume_cmd, config=config)

            # Update job state in repository
            updated_job = self.repo.get_job(job_id) or job
            if isinstance(result, dict):
                if "job_status" in result:
                    updated_job.job_status = result["job_status"]
                if "current_stage" in result:
                    updated_job.current_stage = result["current_stage"]
                if "completed_nodes" in result:
                    for n in result["completed_nodes"]:
                        if n not in updated_job.completed_nodes:
                            updated_job.completed_nodes.append(n)
                if "failed_nodes" in result:
                    for n in result["failed_nodes"]:
                        if n not in updated_job.failed_nodes:
                            updated_job.failed_nodes.append(n)
                if decision == ApprovalStatus.APPROVED:
                    if updated_job.current_stage not in updated_job.approved_stages:
                        updated_job.approved_stages.append(updated_job.current_stage)
                    updated_job.pending_approvals = []
                elif decision == ApprovalStatus.REJECTED:
                    if updated_job.current_stage not in updated_job.rejected_stages:
                        updated_job.rejected_stages.append(updated_job.current_stage)
                    updated_job.pending_approvals = []

            self.repo.update_job_state(updated_job)
            return updated_job

        # Standalone update when no runtime graph instance is provided
        if decision == ApprovalStatus.APPROVED:
            job.job_status = JobStatus.RUNNING
            if job.current_stage not in job.approved_stages:
                job.approved_stages.append(job.current_stage)
            job.pending_approvals = []
        elif decision == ApprovalStatus.REJECTED:
            job.job_status = JobStatus.REJECTED
            if job.current_stage not in job.rejected_stages:
                job.rejected_stages.append(job.current_stage)
            job.pending_approvals = []

        self.repo.update_job_state(job)
        return job

    def inspect_job_history(self, job_id: str) -> Dict[str, Any]:
        """Return the comprehensive audit trail and history of a production job."""
        job = self.repo.get_job(job_id)
        if not job:
            raise ValueError(f"Job '{job_id}' not found")

        events = self.repo.get_event_log(job_id)
        checkpoints = self.repo.get_checkpoints(job_id)
        approvals = self.repo.get_approvals(job_id)

        return {
            "job": job.to_dict(),
            "checkpoints": checkpoints,
            "approvals": [a.model_dump() for a in approvals],
            "event_log": events,
        }

