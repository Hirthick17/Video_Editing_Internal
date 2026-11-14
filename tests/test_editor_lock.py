"""Test Phase 2: Editor lock and concurrent modification prevention."""

import time
import pytest
from app.integrations.chatcut.editor_lock import (
    EditorLockConflictError,
    EditorLockManager,
)
from app.persistence.database import DatabaseManager


def test_editor_lock_acquisition_and_release(temp_db: DatabaseManager):
    """Verify acquiring and releasing exclusive editing leases."""
    mgr = EditorLockManager(temp_db)
    project_id = "proj_lock_01"

    # Initially unlocked
    locked, lock = mgr.is_locked(project_id)
    assert locked is False
    assert lock is None

    # Acquire lock
    l1 = mgr.acquire_lock(project_id, holder_id="agent_1", holder_role="agent", ttl_seconds=10.0)
    assert l1.holder_id == "agent_1"

    locked, active_lock = mgr.is_locked(project_id)
    assert locked is True
    assert active_lock.holder_id == "agent_1"

    # Release lock
    mgr.release_lock(l1)
    locked_after, _ = mgr.is_locked(project_id)
    assert locked_after is False


def test_editor_lock_prevents_concurrent_editing(temp_db: DatabaseManager):
    """Verify that a second holder is blocked while an active lock is held."""
    mgr = EditorLockManager(temp_db)
    project_id = "proj_lock_conflict"

    # Human owner acquires lock
    mgr.acquire_lock(project_id, holder_id="owner_hirthick", holder_role="owner", ttl_seconds=60.0)

    # Agent tries to acquire lock -> must raise EditorLockConflictError
    with pytest.raises(EditorLockConflictError, match="locked by owner 'owner_hirthick'"):
        mgr.acquire_lock(project_id, holder_id="agent_1", holder_role="agent", ttl_seconds=60.0)


def test_editor_lock_expiration(temp_db: DatabaseManager):
    """Verify that expired locks clear cleanly without deadlocking."""
    mgr = EditorLockManager(temp_db)
    project_id = "proj_lock_expiry"

    # Acquire lock with tiny TTL
    mgr.acquire_lock(project_id, holder_id="agent_crashed", holder_role="agent", ttl_seconds=0.1)

    time.sleep(0.15)

    # Lock must be recognized as expired
    locked, _ = mgr.is_locked(project_id)
    assert locked is False

    # New holder can acquire immediately
    l2 = mgr.acquire_lock(project_id, holder_id="agent_recovered", holder_role="agent", ttl_seconds=60.0)
    assert l2.holder_id == "agent_recovered"

