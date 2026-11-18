"""
Phase 1 Test Suite: Pattern A Persisted State Machine, Adapter Hardening, and Guardrails.

Verifies:
1. End-to-end happy path: INTAKE -> ANALYSING -> PLANNED -> WAITING_OWNER -> ASSETS_READY -> APPLYING -> HANDED_OFF -> OWNER_EDITING -> DONE.
2. Rejection of invalid state transitions.
3. Gate G3 owner rejection routes back to PLANNED for revision.
4. Automatic BLOCKED state when unverified spec parameters exist, and resumption after owner approval.
5. Hard prohibition: automated edits strictly blocked during OWNER_EDITING state.
6. SQLite persistence, versioning, checkpoint snapshots, and full job recovery.
7. Adapter allowlist strictly blocks generative/synthetic tools (submit_video, submit_image, submit_voice).
8. Hard prohibition: emoji characters in caption/text strings are rejected with AssetGuardrailViolationError.
9. Stock B-roll candidates remain in bin and cannot be placed on visual tracks when placement_mode=CANDIDATES_ONLY.
10. Post-write PatternLinter verification triggers automated rollback upon rule violation.
"""

import os
import tempfile
from pathlib import Path
import pytest

from app.integrations.chatcut.editor_controller import (
    EditorController,
    EditorExecutionReport,
)
from app.integrations.chatcut.editor_lock import EditorLockConflictError, EditorLockManager
from app.integrations.chatcut.mcp_adapter import (
    ChatCutAllowlistViolationError,
    ChatCutMCPAdapter,
    contains_emoji,
)
from app.orchestration.state_machine import (
    InvalidStateTransitionError,
    PatternAJobState,
    PatternAStateBlockedError,
    PatternAStateMachine,
    compute_file_sha256,
)
from app.persistence.database import DatabaseManager
from app.services.asset_guardrail import AssetGuardrailViolationError
from app.state.editor_contracts import ClipSpec, EditOperation
from app.state.enums import EditOperationType, PatternAState
from app.state.pattern_spec import ParameterSource, PatternSpec, ScalarParameter


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    manager = DatabaseManager(db_path)
    manager.initialize_schema()
    yield manager
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


@pytest.fixture
def temp_clip_file():
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"RAW_ARANGE_CLIP_DATA_PLACEHOLDER_FOR_TESTING_1234567890")
        f_path = f.name
    yield f_path
    if os.path.exists(f_path):
        try:
            os.remove(f_path)
        except OSError:
            pass


def test_full_happy_path_lifecycle(temp_db: DatabaseManager, temp_clip_file: str):
    """
    Test complete lifecycle from INTAKE to DONE:
    INTAKE -> ANALYSING -> PLANNED -> WAITING_OWNER -> ASSETS_READY -> APPLYING -> HANDED_OFF -> OWNER_EDITING -> DONE
    """
    sm = PatternAStateMachine.create_new_job(
        job_id="job_happy_01",
        project_id="proj_happy_01",
        short_id="short_happy_01",
        db_manager=temp_db,
    )
    assert sm.state.state == PatternAState.INTAKE

    # 1. Intake raw clips
    clips = sm.intake_raw_clips([temp_clip_file])
    assert len(clips) == 1
    assert clips[0].checksum_verified is True
    assert clips[0].sha256 == compute_file_sha256(temp_clip_file)
    assert sm.state.state == PatternAState.ANALYSING

    # 2. Record analysis
    analysis_data = {
        "transcript": "Hello world this is Hirthick and today we build an AI agent",
        "words": [
            {"word": "Hello", "start": 0.0, "end": 0.3},
            {"word": "world", "start": 0.3, "end": 0.6},
            {"word": "this", "start": 0.6, "end": 0.8},
        ],
        "silences": [[1.2, 1.4]],
        "loudness_lufs": -16.2,
        "selected_take": "take_01",
    }
    sm.record_analysis(analysis_data)
    assert sm.state.state == PatternAState.PLANNED

    # 3. Build & lint plan
    plan = {
        "cuts": [
            {"start_frame": 0, "end_frame": 84, "scale": 1.0},
            {"start_frame": 84, "end_frame": 180, "scale": 1.1},
        ],
        "captions": [
            {"start_frame": 0, "end_frame": 27, "text": "Hello world this", "accent_word": "world"},
        ],
        "hook_text": {"start_frame": 0, "end_frame": 60, "text": "Stop Building Alone"},
        "cta_text": {"start_frame": 900, "end_frame": 1050, "text": "Subscribe for more builds"},
    }
    sm.build_plan(plan)
    assert sm.state.state == PatternAState.WAITING_OWNER

    # 4. Gate G3: Owner approves rough-cut plan
    sm.submit_owner_decision(approved=True, feedback="Pacing looks tight. Proceed.")
    assert sm.state.state == PatternAState.ASSETS_READY

    # 5. Prepare assets (candidates only for stock)
    sfx = [{"cue_id": "sfx_woosh", "file": "whoosh.wav", "frame": 0}]
    music = [{"track_id": "bgm_lofi", "file": "ambient.mp3", "ducking_db": -18.0}]
    broll = [{"slot_id": "slot_01", "keyword": "ai robotics", "provider": "pixabay", "asset_id": "ast_robot_01"}]
    sm.prepare_assets(sfx_cues=sfx, music_cues=music, broll_candidates=broll, placement_mode="CANDIDATES_ONLY")
    assert sm.state.state == PatternAState.APPLYING
    assert sm.state.placement_mode == "CANDIDATES_ONLY"

    # 6. Apply timeline with adapter and controller
    adapter = ChatCutMCPAdapter(mode="simulated")
    adapter._execute_simulated_tool("create_project", {"projectId": "proj_happy_01", "name": "Happy Project"})
    controller = EditorController(adapter=adapter, lock_manager=EditorLockManager(temp_db))

    ops = [
        EditOperation(
            operation_id="op_a_roll_01",
            operation_type=EditOperationType.INSERT_CLIP,
            idempotency_key="idemp_aroll_1",
            clip_spec=ClipSpec(
                item_id="clip_aroll_1",
                track_id="V1",
                asset_id="ast_raw_01",
                start_frame=0,
                end_frame=150,
                name="aroll_desk_01.mp4",
            ),
        ),
        EditOperation(
            operation_id="op_cap_01",
            operation_type=EditOperationType.ADD_CAPTION,
            idempotency_key="idemp_cap_1",
            parameters={
                "caption_id": "cap_01",
                "start_frame": 0,
                "end_frame": 30,
                "text": "Stop building alone",
                "style": {"font": "Inter", "color": "#FFFFFF", "accent": "#9333EA"},
            },
        ),
    ]

    report = sm.apply_timeline(
        adapter=adapter,
        controller=controller,
        operations=ops,
        timeline_id="tl_proj_happy_01",
        project_id="proj_happy_01",
    )
    assert report.success is True
    assert sm.state.state == PatternAState.HANDED_OFF
    assert sm.state.handoff_report is not None
    assert sm.state.handoff_report["status"] == "READY_FOR_OWNER_POLISH"

    # 7. Start owner polish
    sm.start_owner_polish()
    assert sm.state.state == PatternAState.OWNER_EDITING
    assert sm.state.polish_started_at is not None

    # 8. Complete owner polish (simulating 21.5 minutes hands-on polish)
    metrics = sm.complete_owner_polish(polish_minutes=21.5)
    assert sm.state.state == PatternAState.DONE
    assert metrics["measured_polish_minutes"] == 21.5
    assert metrics["target_achieved"] is True  # 21.5 <= 30.0 target!
    assert metrics["time_saved_minutes"] > 300.0  # Saved > 5 hours vs baseline!


def test_invalid_state_transitions_rejected(temp_db: DatabaseManager):
    """Verify that jumping across lifecycle states without passing intermediate gates is rejected."""
    sm = PatternAStateMachine.create_new_job(
        job_id="job_invalid_trans",
        project_id="proj_inv",
        short_id="short_inv",
        db_manager=temp_db,
    )
    assert sm.state.state == PatternAState.INTAKE

    # Cannot jump directly from INTAKE to APPLYING
    with pytest.raises(InvalidStateTransitionError, match="Cannot transition from 'INTAKE' to 'APPLYING'"):
        sm._transition_to(PatternAState.APPLYING)

    # Cannot jump directly from INTAKE to DONE
    with pytest.raises(InvalidStateTransitionError, match="Cannot transition from 'INTAKE' to 'DONE'"):
        sm._transition_to(PatternAState.DONE)


def test_gate_g3_owner_rejection_routes_back_to_planned(temp_db: DatabaseManager, temp_clip_file: str):
    """Gate G3 rejection must route state back to PLANNED for cutlist revision."""
    sm = PatternAStateMachine.create_new_job(
        job_id="job_gate_g3_rej",
        project_id="proj_g3",
        short_id="short_g3",
        db_manager=temp_db,
    )
    sm.intake_raw_clips([temp_clip_file])
    sm.record_analysis({"transcript": "Test speech content"})
    sm.build_plan({"cuts": [{"start_frame": 0, "end_frame": 90}]})
    assert sm.state.state == PatternAState.WAITING_OWNER

    # Owner rejects cutlist with revision feedback
    sm.submit_owner_decision(approved=False, feedback="Hook cut is too abrupt; extend by 10 frames.")
    assert sm.state.state == PatternAState.PLANNED
    assert "Hook cut is too abrupt" in sm.state.history[-1].reason


def test_blocked_state_on_unverified_spec_parameter(temp_db: DatabaseManager, temp_clip_file: str):
    """When a PatternSpec parameter is DEFAULT_UNVERIFIED, build_plan must transition to BLOCKED."""
    unverified_spec = PatternSpec.get_pattern_a_default()
    # Artificially set an unverified parameter
    unverified_spec.caption_accent_color = ScalarParameter(
        value="#FF0000",
        source=ParameterSource.DEFAULT_UNVERIFIED,
        evidence_ref="unverified_guess",
    )

    sm = PatternAStateMachine.create_new_job(
        job_id="job_blocked_01",
        project_id="proj_blk",
        short_id="short_blk",
        spec=unverified_spec,
        db_manager=temp_db,
    )
    sm.intake_raw_clips([temp_clip_file])
    sm.record_analysis({"transcript": "Test content"})

    sm.build_plan({"cuts": []})
    assert sm.state.state == PatternAState.BLOCKED
    assert "unverified parameters" in sm.state.blocked_reason

    # Attempting intake while blocked raises PatternAStateBlockedError
    with pytest.raises(PatternAStateBlockedError):
        sm.intake_raw_clips([temp_clip_file])

    # Unblocking returns to previous state
    sm.unblock()
    assert sm.state.state == PatternAState.PLANNED


def test_prohibition_never_edit_timeline_during_owner_editing(temp_db: DatabaseManager):
    """
    Hard prohibition: Never edit a timeline that is in OWNER_EDITING state.
    Calling apply_timeline or apply_verified_edit must raise EditorLockConflictError.
    """
    sm = PatternAStateMachine.create_new_job(
        job_id="job_owner_edit_guard",
        project_id="proj_guard",
        short_id="short_guard",
        db_manager=temp_db,
    )
    # Force state to OWNER_EDITING
    sm.state.state = PatternAState.OWNER_EDITING

    adapter = ChatCutMCPAdapter(mode="simulated")
    controller = EditorController(adapter=adapter, lock_manager=EditorLockManager(temp_db))

    with pytest.raises(EditorLockConflictError, match="currently in OWNER_EDITING state"):
        sm.apply_timeline(
            adapter=adapter,
            controller=controller,
            operations=[],
            timeline_id="tl_proj_guard",
        )

    # Calling controller directly with job_status="OWNER_EDITING" also raises EditorLockConflictError
    with pytest.raises(EditorLockConflictError, match="currently in OWNER_EDITING state"):
        controller.apply_verified_edit(
            project_id="proj_guard",
            timeline_id="tl_proj_guard",
            operations=[],
            job_status="OWNER_EDITING",
        )


def test_sqlite_persistence_and_job_recovery(temp_db: DatabaseManager, temp_clip_file: str):
    """Verify that state transitions, checkpoints, and event logs persist to SQLite and recover accurately."""
    sm = PatternAStateMachine.create_new_job(
        job_id="job_persist_test_01",
        project_id="proj_persist_01",
        short_id="short_persist_01",
        db_manager=temp_db,
    )
    sm.intake_raw_clips([temp_clip_file])
    sm.record_analysis({"transcript": "Persistence test speech", "duration": 40.0})

    # Reload from SQLite
    loaded_sm = PatternAStateMachine.load_from_db("job_persist_test_01", db_manager=temp_db)
    assert loaded_sm is not None
    assert loaded_sm.state.job_id == "job_persist_test_01"
    assert loaded_sm.state.state == PatternAState.PLANNED
    assert loaded_sm.state.analysis_data["transcript"] == "Persistence test speech"
    assert len(loaded_sm.state.raw_clips) == 1
    assert loaded_sm.state.state_version >= 2

    # Verify checkpoints recorded in SQLite
    checkpoints = loaded_sm.repo.get_checkpoints("job_persist_test_01")
    assert len(checkpoints) >= 2


def test_adapter_allowlist_blocks_generative_tools():
    """Verify that generative AI and diffusion tools are strictly rejected by the adapter allowlist."""
    adapter = ChatCutMCPAdapter(mode="simulated")

    # Prohibited generative tools must raise ChatCutAllowlistViolationError
    prohibited_calls = [
        "submit_video",
        "submit_image",
        "submit_voice",
        "generate_screen_from_text",
        "generate_motion_graphics",
    ]
    for tool in prohibited_calls:
        with pytest.raises(ChatCutAllowlistViolationError, match="strictly prohibited by Pattern A allowlist"):
            adapter._execute_simulated_tool(tool, {})

        with pytest.raises(ChatCutAllowlistViolationError, match="strictly prohibited by Pattern A allowlist"):
            adapter._execute_cli_tool(tool, {})


def test_adapter_emoji_guardrail_rejection():
    """Verify that emoji characters in caption or text strings trigger immediate guardrail rejection."""
    assert contains_emoji("Awesome video! 🔥") is True
    assert contains_emoji("Clean Inter font text") is False

    adapter = ChatCutMCPAdapter(mode="simulated")
    op_bad_emoji = EditOperation(
        operation_id="op_emoji_err",
        operation_type=EditOperationType.ADD_CAPTION,
        idempotency_key="idemp_emoji_err",
        parameters={"text": "Check this out! 🚀"},
    )

    with pytest.raises(AssetGuardrailViolationError, match="emoji characters inside caption or text strings"):
        adapter.apply_batch_operations("tl_test", [op_bad_emoji])


def test_adapter_broll_placement_guardrail_candidates_only():
    """Stock B-roll candidates must not be placed on visual tracks when placement_mode=CANDIDATES_ONLY."""
    adapter = ChatCutMCPAdapter(mode="simulated")

    broll_op = EditOperation(
        operation_id="op_stock_err",
        operation_type=EditOperationType.INSERT_CLIP,
        idempotency_key="idemp_stock_err",
        clip_spec=ClipSpec(
            item_id="clip_stock_01",
            track_id="V2",
            asset_id="ast_stock_broll_pixabay",
            start_frame=0,
            end_frame=90,
            name="stock_broll_ai_chip.mp4",
        ),
    )

    # When placement_mode is CANDIDATES_ONLY, placing stock B-roll on visual track raises violation
    with pytest.raises(AssetGuardrailViolationError, match="placement_mode='CANDIDATES_ONLY'"):
        adapter.apply_batch_operations(
            timeline_id="tl_test",
            operations=[broll_op],
            placement_mode="CANDIDATES_ONLY",
        )


def test_pattern_linter_post_write_rollback_in_controller(temp_db: DatabaseManager):
    """
    If a write batch creates a timeline that violates Pattern A (e.g. prohibited SVG item),
    EditorController read-after-write verification fails and auto-rolls back.
    """
    adapter = ChatCutMCPAdapter(mode="simulated")
    adapter._execute_simulated_tool("create_project", {"projectId": "proj_lint_fail", "name": "Lint Fail Project"})
    controller = EditorController(adapter=adapter, lock_manager=EditorLockManager(temp_db))

    spec = PatternSpec.get_pattern_a_default()

    # Pre-read revision
    tl = adapter.get_timeline("tl_proj_lint_fail")
    rev = tl.revision_hash

    # Create an item on timeline that violates PatternLinter (stock B-roll placed while CANDIDATES_ONLY)
    adapter._sim_timelines["tl_proj_lint_fail"]["tracks"][0]["items"].append({
        "itemId": "illegal_stock_placement",
        "assetId": "ast_stock_broll",
        "name": "stock_broll_clip.mp4",
        "startFrame": 0,
        "endFrame": 60,
    })

    # Legitimate operation
    normal_op = EditOperation(
        operation_id="op_norm",
        operation_type=EditOperationType.INSERT_CLIP,
        idempotency_key="idemp_norm_01",
        clip_spec=ClipSpec(
            item_id="clip_norm",
            track_id="V1",
            asset_id="ast_norm",
            start_frame=0,
            end_frame=60,
            name="aroll.mp4",
        ),
    )

    report = controller.apply_verified_edit(
        project_id="proj_lint_fail",
        timeline_id="tl_proj_lint_fail",
        operations=[normal_op],
        pattern_spec=spec,
        placement_mode="CANDIDATES_ONLY",
    )

    # Verification fails due to illegal stock B-roll placement and rolls back!
    assert report.success is False
    assert report.rolled_back is True
    assert "PatternLinter verification failed post-write" in report.error
    assert "Stock B-roll placed on timeline" in report.error
