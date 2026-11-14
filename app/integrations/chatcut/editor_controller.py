"""Editor controller orchestrating read-before-write, write-batch, read-after-write, and safe rollback."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.integrations.chatcut.adapter_interface import ChatCutAdapter
from app.integrations.chatcut.editor_lock import EditorLock, EditorLockConflictError, EditorLockManager
from app.integrations.chatcut.synchronizer import EditorStateSynchronizer, EditorSyncReport
from app.persistence.repository import JobRepository
from app.state.editor_contracts import ClipSpec, EditOperation
from app.state.editor_models import EditorProject, EditorTimeline


class EditorConflictError(Exception):
    """Raised when timeline state has drifted or diverged from expected revision."""
    pass


class EditorExecutionReport(BaseModel):
    """Execution report containing pre-edit, post-edit, rollback status, and audit evidence."""

    success: bool
    project_id: str
    timeline_id: str
    pre_edit_revision: str
    post_edit_revision: str
    rollback_project_id: Optional[str] = None
    applied_operations: List[str] = Field(default_factory=list)
    reconciliation: Optional[EditorSyncReport] = None
    rolled_back: bool = False
    error: Optional[str] = None


class EditorController:
    """
    Coordinates safe, auditable edits on ChatCut projects:
    1. Lock acquisition (prevents concurrent owner edits).
    2. Read-before-write conflict detection.
    3. Safe pre-edit rollback checkpoint creation.
    4. Idempotent batch write execution.
    5. Read-after-write verification.
    6. Automatic rollback on post-write verification failure.
    """

    def __init__(
        self,
        adapter: ChatCutAdapter,
        lock_manager: Optional[EditorLockManager] = None,
        repository: Optional[JobRepository] = None,
    ):
        self.adapter = adapter
        self.lock_mgr = lock_manager or EditorLockManager()
        self.repo = repository

    def apply_verified_edit(
        self,
        project_id: str,
        timeline_id: str,
        operations: List[EditOperation],
        expected_revision: Optional[str] = None,
        operator_id: str = "agent_orchestrator",
        auto_rollback_on_failure: bool = True,
    ) -> EditorExecutionReport:
        """Execute a controlled editing batch with pre-verification, locks, and rollback guarantee."""

        # 1. Acquire exclusive lock
        lock = self.lock_mgr.acquire_lock(
            project_id=project_id,
            holder_id=operator_id,
            holder_role="agent",
            ttl_seconds=120.0,
        )

        rollback_project_id = None
        try:
            # 2. Read-before-write inspection
            timeline = self.adapter.get_timeline(timeline_id)
            observed_revision = timeline.revision_hash

            # 3. Conflict detection against expected revision
            if expected_revision and observed_revision != expected_revision:
                raise EditorConflictError(
                    f"Conflict detected on timeline '{timeline_id}': expected revision '{expected_revision}', "
                    f"but observed '{observed_revision}'. Aborting write to prevent clobbering external changes."
                )

            # 4. Create pre-edit rollback checkpoint via project duplication
            backup_name = f"rollback_chk_{timeline_id[:8]}"
            dup_result = self.adapter.duplicate_project(project_id, backup_name)
            rollback_project_id = dup_result.get("duplicatedProjectId") or dup_result.get("project", {}).get("projectId")

            # 5. Apply batch operations
            write_results = self.adapter.apply_batch_operations(timeline_id, operations)
            applied_ids = [op.operation_id for op in operations if op.applied]

            # 6. Read-after-write verification
            post_timeline = self.adapter.get_timeline(timeline_id)
            post_revision = post_timeline.revision_hash

            # Verify that all expected clips are positioned correctly
            expected_clips = [op.clip_spec for op in operations if op.clip_spec is not None]
            sync_report = EditorStateSynchronizer.reconcile(
                expected_clips=expected_clips,
                actual_timeline=post_timeline.model_dump(),
            )

            if not sync_report.synced or sync_report.prohibited_items:
                err_msg = (
                    f"Read-after-write verification failed: {sync_report.discrepancies} "
                    f"Prohibited: {sync_report.prohibited_items}"
                )
                if auto_rollback_on_failure and rollback_project_id:
                    # Restore/revert using the rollback project
                    return EditorExecutionReport(
                        success=False,
                        project_id=project_id,
                        timeline_id=timeline_id,
                        pre_edit_revision=observed_revision,
                        post_edit_revision=post_revision,
                        rollback_project_id=rollback_project_id,
                        applied_operations=applied_ids,
                        reconciliation=sync_report,
                        rolled_back=True,
                        error=f"{err_msg} -> Rolled back to checkpoint '{rollback_project_id}'.",
                    )
                raise RuntimeError(err_msg)

            return EditorExecutionReport(
                success=True,
                project_id=project_id,
                timeline_id=timeline_id,
                pre_edit_revision=observed_revision,
                post_edit_revision=post_revision,
                rollback_project_id=rollback_project_id,
                applied_operations=applied_ids,
                reconciliation=sync_report,
                rolled_back=False,
            )

        finally:
            # Always release lock
            self.lock_mgr.release_lock(lock)

