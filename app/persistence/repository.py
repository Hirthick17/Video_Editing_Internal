"""Typed SQLite repository for jobs, checkpoints, event logs, and approvals."""

import json
import uuid
from typing import Any, Dict, List, Optional

from app.persistence.database import DatabaseManager, default_db_manager
from app.state.enums import ApprovalStatus, JobStatus, ProductionStage
from app.state.models import ApprovalRecord, utc_now_iso
from app.state.production_state import ProductionState


class JobRepository:
    """Provides strongly typed CRUD and audit logging against SQLite storage."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or default_db_manager

    def create_job(self, state: ProductionState) -> ProductionState:
        """Persist a newly created job. Raises ValueError if job_id already exists."""
        state_json = json.dumps(state.to_dict())
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "SELECT job_id FROM jobs WHERE job_id = ?",
                (state.job_id,),
            )
            if cursor.fetchone() is not None:
                raise ValueError(f"Job with ID '{state.job_id}' already exists")

            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, project_id, short_id, status, stage,
                    state_version, state_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state.job_id,
                    state.project_id,
                    state.short_id,
                    state.job_status.value,
                    state.current_stage.value,
                    state.state_version,
                    state_json,
                    state.created_at,
                    state.updated_at,
                ),
            )

        self.record_event(
            job_id=state.job_id,
            event_type="JOB_CREATED",
            node_name=None,
            payload={"project_id": state.project_id, "short_id": state.short_id},
        )
        return state

    def get_job(self, job_id: str) -> Optional[ProductionState]:
        """Retrieve and deserialize a job by its job_id."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "SELECT state_json FROM jobs WHERE job_id = ?",
                (job_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            state_dict = json.loads(row["state_json"])
            return ProductionState.from_dict(state_dict)

    def update_job_state(self, state: ProductionState) -> None:
        """Update job state, bump version, and record state update."""
        state.touch()
        state_json = json.dumps(state.to_dict())
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                UPDATE jobs SET
                    status = ?,
                    stage = ?,
                    state_version = ?,
                    state_json = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (
                    state.job_status.value,
                    state.current_stage.value,
                    state.state_version,
                    state_json,
                    state.updated_at,
                    state.job_id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Job '{state.job_id}' not found for update")

    def save_checkpoint(
        self,
        job_id: str,
        stage: ProductionStage,
        state_version: int,
        state: ProductionState,
    ) -> str:
        """Store an immutable snapshot checkpoint for a job."""
        checkpoint_id = f"chk_{uuid.uuid4().hex[:12]}"
        snapshot_json = json.dumps(state.to_dict())
        now_utc = utc_now_iso()

        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO checkpoints (
                    checkpoint_id, job_id, stage, state_version, snapshot_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    checkpoint_id,
                    job_id,
                    stage.value,
                    state_version,
                    snapshot_json,
                    now_utc,
                ),
            )

        self.record_event(
            job_id=job_id,
            event_type="CHECKPOINT_SAVED",
            node_name=None,
            payload={"checkpoint_id": checkpoint_id, "stage": stage.value},
        )
        return checkpoint_id

    def get_checkpoints(self, job_id: str) -> List[Dict[str, Any]]:
        """List all checkpoints recorded for a job."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT checkpoint_id, stage, state_version, created_at
                FROM checkpoints
                WHERE job_id = ?
                ORDER BY created_at ASC
                """,
                (job_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def record_event(
        self,
        job_id: str,
        event_type: str,
        node_name: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Append an event to the immutable event log."""
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        payload_json = json.dumps(payload or {})
        now_utc = utc_now_iso()

        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO event_log (
                    event_id, job_id, event_type, node_name, payload_json, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    job_id,
                    event_type,
                    node_name,
                    payload_json,
                    now_utc,
                ),
            )
        return event_id

    def get_event_log(self, job_id: str) -> List[Dict[str, Any]]:
        """Retrieve full audit event log for a job ordered chronologically."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT event_id, job_id, event_type, node_name, payload_json, timestamp
                FROM event_log
                WHERE job_id = ?
                ORDER BY timestamp ASC
                """,
                (job_id,),
            )
            rows = []
            for row in cursor.fetchall():
                d = dict(row)
                d["payload"] = json.loads(d.pop("payload_json"))
                rows.append(d)
            return rows

    def save_approval(self, approval: ApprovalRecord, job_id: str) -> None:
        """Record or update a human approval decision."""
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO approval_records (
                    approval_id, job_id, stage, decision, reviewer, feedback, created_at, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(approval_id) DO UPDATE SET
                    decision = excluded.decision,
                    reviewer = excluded.reviewer,
                    feedback = excluded.feedback,
                    decided_at = excluded.decided_at
                """,
                (
                    approval.approval_id,
                    job_id,
                    approval.stage.value,
                    approval.decision.value,
                    approval.reviewer,
                    approval.feedback,
                    approval.created_at_utc,
                    approval.decided_at_utc,
                ),
            )

        self.record_event(
            job_id=job_id,
            event_type="APPROVAL_DECISION_SAVED",
            node_name=None,
            payload={
                "approval_id": approval.approval_id,
                "stage": approval.stage.value,
                "decision": approval.decision.value,
                "reviewer": approval.reviewer,
            },
        )

    def get_approvals(self, job_id: str) -> List[ApprovalRecord]:
        """Fetch all approval records for a given job."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT approval_id, stage, decision, reviewer, feedback, created_at, decided_at
                FROM approval_records
                WHERE job_id = ?
                ORDER BY created_at ASC
                """,
                (job_id,),
            )
            results = []
            for row in cursor.fetchall():
                results.append(
                    ApprovalRecord(
                        approval_id=row["approval_id"],
                        stage=ProductionStage(row["stage"]),
                        decision=ApprovalStatus(row["decision"]),
                        reviewer=row["reviewer"],
                        feedback=row["feedback"] or "",
                        created_at_utc=row["created_at"],
                        decided_at_utc=row["decided_at"],
                    )
                )
            return results

    def record_node_retry(self, job_id: str, node_name: str, error_message: str) -> int:
        """Increment retry count for a node and return updated count."""
        now_utc = utc_now_iso()
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO node_retries (job_id, node_name, retry_count, last_error, updated_at)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(job_id, node_name) DO UPDATE SET
                    retry_count = node_retries.retry_count + 1,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """,
                (job_id, node_name, error_message, now_utc),
            )
            cursor = conn.execute(
                "SELECT retry_count FROM node_retries WHERE job_id = ? AND node_name = ?",
                (job_id, node_name),
            )
            row = cursor.fetchone()
            return row["retry_count"] if row else 1

    def get_node_retries(self, job_id: str, node_name: str) -> int:
        """Get current retry count for a node."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "SELECT retry_count FROM node_retries WHERE job_id = ? AND node_name = ?",
                (job_id, node_name),
            )
            row = cursor.fetchone()
            return row["retry_count"] if row else 0

    def reset_node_retries(self, job_id: str, node_name: str) -> None:
        """Reset retry count for a node after success."""
        with self.db.transaction() as conn:
            conn.execute(
                "DELETE FROM node_retries WHERE job_id = ? AND node_name = ?",
                (job_id, node_name),
            )

