"""Editor lock and owner handoff protocol to prevent concurrent editing collisions."""

import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple
from pydantic import BaseModel, Field

from app.persistence.database import DatabaseManager, default_db_manager


class EditorLockConflictError(Exception):
    """Raised when an editing operation is attempted while an active lock is held by another entity."""
    pass


class EditorLock(BaseModel):
    """Active lease lock record representing editing rights on a ChatCut project."""

    lock_id: str
    project_id: str
    holder_id: str
    holder_role: str = "agent"  # "agent" or "owner"
    acquired_at_epoch: float
    expires_at_epoch: float

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at_epoch


class EditorLockManager:
    """Manages project-level leases preventing concurrent agent/human modifications."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or default_db_manager
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create lock table if not exists."""
        with self.db.transaction() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS editor_locks (
                    project_id TEXT PRIMARY KEY,
                    lock_id TEXT NOT NULL,
                    holder_id TEXT NOT NULL,
                    holder_role TEXT NOT NULL,
                    acquired_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )

    def is_locked(self, project_id: str) -> Tuple[bool, Optional[EditorLock]]:
        """Check if project has an active, non-expired lock."""
        now = time.time()
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "SELECT lock_id, project_id, holder_id, holder_role, acquired_at, expires_at "
                "FROM editor_locks WHERE project_id = ?",
                (project_id,),
            )
            row = cursor.fetchone()
            if not row:
                return False, None

            lock = EditorLock(
                lock_id=row["lock_id"],
                project_id=row["project_id"],
                holder_id=row["holder_id"],
                holder_role=row["holder_role"],
                acquired_at_epoch=row["acquired_at"],
                expires_at_epoch=row["expires_at"],
            )

            if lock.is_expired:
                # Clean up expired lock
                conn.execute("DELETE FROM editor_locks WHERE project_id = ?", (project_id,))
                return False, None

            return True, lock

    def acquire_lock(
        self,
        project_id: str,
        holder_id: str,
        holder_role: str = "agent",
        ttl_seconds: float = 60.0,
    ) -> EditorLock:
        """Acquire or renew an exclusive editing lock on a project."""
        now = time.time()
        locked, existing = self.is_locked(project_id)

        if locked and existing is not None:
            if existing.holder_id != holder_id:
                raise EditorLockConflictError(
                    f"Project '{project_id}' is locked by {existing.holder_role} "
                    f"'{existing.holder_id}' until epoch {existing.expires_at_epoch:.1f}."
                )

        lock_id = existing.lock_id if (existing and existing.holder_id == holder_id) else f"lck_{uuid.uuid4().hex[:10]}"
        expires_at = now + ttl_seconds

        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO editor_locks (project_id, lock_id, holder_id, holder_role, acquired_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    lock_id = excluded.lock_id,
                    holder_id = excluded.holder_id,
                    holder_role = excluded.holder_role,
                    expires_at = excluded.expires_at
                """,
                (project_id, lock_id, holder_id, holder_role, now, expires_at),
            )

        return EditorLock(
            lock_id=lock_id,
            project_id=project_id,
            holder_id=holder_id,
            holder_role=holder_role,
            acquired_at_epoch=now,
            expires_at_epoch=expires_at,
        )

    def refresh_lock(self, lock: EditorLock, extend_seconds: float = 60.0) -> EditorLock:
        """Extend the TTL of an actively held lock."""
        return self.acquire_lock(
            project_id=lock.project_id,
            holder_id=lock.holder_id,
            holder_role=lock.holder_role,
            ttl_seconds=extend_seconds,
        )

    def release_lock(self, lock: EditorLock) -> None:
        """Release an exclusive lock."""
        with self.db.transaction() as conn:
            conn.execute(
                "DELETE FROM editor_locks WHERE project_id = ? AND lock_id = ?",
                (lock.project_id, lock.lock_id),
            )

