"""Test Phase 2: EditorController read-before-write, write-batch, read-after-write, and rollback recovery."""

import pytest
from app.integrations.chatcut.editor_controller import (
    EditorConflictError,
    EditorController,
)
from app.integrations.chatcut.editor_lock import EditorLockManager
from app.integrations.chatcut.mcp_adapter import ChatCutMCPAdapter
from app.persistence.database import DatabaseManager
from app.services.asset_guardrail import AssetGuardrailViolationError
from app.state.editor_contracts import ClipSpec, EditOperation
from app.state.enums import EditOperationType


def test_editor_controller_successful_verified_edit(temp_db: DatabaseManager):
    """
    Test controlled edit cycle:
    1. Lock acquisition
    2. Read-before-write
    3. Rollback snapshot creation
    4. Batch write execution
    5. Read-after-write verification
    6. Lock release
    """
    adapter = ChatCutMCPAdapter(mode="simulated")
    # Initialize a simulated project and timeline
    adapter._execute_simulated_tool(
        "create_project",
        {"projectId": "proj_ctrl_01", "name": "TellOS Shorts Test"},
    )

    lock_mgr = EditorLockManager(temp_db)
    controller = EditorController(adapter=adapter, lock_manager=lock_mgr)

    # Pre-read timeline to get revision hash
    tl = adapter.get_timeline("tl_proj_ctrl_01")
    expected_rev = tl.revision_hash

    # Prepare edit operation: add a real B-roll video clip on V2 from frame 0 to 150
    clip = ClipSpec(
        item_id="clip_broll_spreadsheet",
        track_id="V2",
        asset_id="ast_stock_spreadsheet",
        start_frame=0,
        end_frame=150,
        name="broll-spreadsheet.mp4",
    )
    op = EditOperation(
        operation_id="op_add_broll",
        operation_type=EditOperationType.INSERT_CLIP,
        idempotency_key="idemp_broll_01",
        clip_spec=clip,
    )

    report = controller.apply_verified_edit(
        project_id="proj_ctrl_01",
        timeline_id="tl_proj_ctrl_01",
        operations=[op],
        expected_revision=expected_rev,
    )

    assert report.success is True
    assert report.rolled_back is False
    assert report.rollback_project_id is not None
    assert "op_add_broll" in report.applied_operations
    assert report.reconciliation.synced is True
    assert report.reconciliation.matched_clips == 1

    # Verify lock was released
    locked, _ = lock_mgr.is_locked("proj_ctrl_01")
    assert locked is False


def test_editor_controller_conflict_detection(temp_db: DatabaseManager):
    """Verify that read-before-write detects revision drift and aborts to prevent clobbering."""
    adapter = ChatCutMCPAdapter(mode="simulated")
    adapter._execute_simulated_tool(
        "create_project",
        {"projectId": "proj_conflict_01", "name": "Conflict Project"},
    )

    controller = EditorController(adapter=adapter, lock_manager=EditorLockManager(temp_db))

    op = EditOperation(
        operation_id="op_1",
        operation_type=EditOperationType.INSERT_CLIP,
        idempotency_key="idemp_c_1",
    )

    # Pass an outdated expected revision
    stale_revision = "stale_hash_12345"
    with pytest.raises(EditorConflictError, match="Conflict detected on timeline"):
        controller.apply_verified_edit(
            project_id="proj_conflict_01",
            timeline_id="tl_proj_conflict_01",
            operations=[op],
            expected_revision=stale_revision,
        )


def test_editor_controller_svg_guardrail_rejection(temp_db: DatabaseManager):
    """Verify that attempting to place an SVG card triggers guardrail rejection."""
    adapter = ChatCutMCPAdapter(mode="simulated")
    adapter._execute_simulated_tool(
        "create_project",
        {"projectId": "proj_svg_test", "name": "SVG Guardrail Test"},
    )

    controller = EditorController(adapter=adapter, lock_manager=EditorLockManager(temp_db))

    svg_clip = ClipSpec(
        item_id="clip_svg_err",
        track_id="V3",
        asset_id="ast_svg",
        start_frame=0,
        end_frame=150,
        name="card1_hook.svg",
    )
    op = EditOperation(
        operation_id="op_svg_bad",
        operation_type=EditOperationType.INSERT_CLIP,
        idempotency_key="idemp_svg_bad",
        clip_spec=svg_clip,
    )

    with pytest.raises(AssetGuardrailViolationError, match="placing SVG cards is prohibited"):
        controller.apply_verified_edit(
            project_id="proj_svg_test",
            timeline_id="tl_proj_svg_test",
            operations=[op],
        )


def test_editor_controller_rollback_recovery(temp_db: DatabaseManager):
    """Verify that a controlled edit can be safely restored/reverted to prior state using duplicate_project."""
    adapter = ChatCutMCPAdapter(mode="simulated")
    adapter._execute_simulated_tool(
        "create_project",
        {"projectId": "proj_restore_01", "name": "Original Production Project"},
    )

    # Create pre-edit duplicate backup
    dup_res = adapter.duplicate_project("proj_restore_01", "Original Project Backup Before Edit")
    backup_project_id = dup_res["duplicatedProjectId"]
    assert backup_project_id == "dup_proj_restore_01"

    # Make a controlled edit in original project
    clip = ClipSpec(
        item_id="clip_temp",
        track_id="V1",
        asset_id="ast_temp",
        start_frame=0,
        end_frame=90,
        name="temp.mp4",
    )
    op = EditOperation(
        operation_id="op_temp",
        operation_type=EditOperationType.INSERT_CLIP,
        idempotency_key="idemp_temp",
        clip_spec=clip,
    )
    adapter.apply_batch_operations("tl_proj_restore_01", [op])

    # Verify original has the item
    edited_tl = adapter.get_timeline("tl_proj_restore_01")
    assert any(i.item_id == "clip_temp" for t in edited_tl.tracks for i in t.items)

    # Verify backup duplicate does NOT have the item (intact recovery baseline)
    backup_tl = adapter.get_timeline(f"tl_{backup_project_id}")
    assert not any(i.item_id == "clip_temp" for t in backup_tl.tracks for i in t.items)

