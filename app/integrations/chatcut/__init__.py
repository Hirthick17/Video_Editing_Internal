"""ChatCut integration contracts, adapter interfaces, lock management, and controller."""

from app.integrations.chatcut.adapter_interface import ChatCutAdapter, StubChatCutAdapter
from app.integrations.chatcut.editor_controller import (
    EditorConflictError,
    EditorController,
    EditorExecutionReport,
)
from app.integrations.chatcut.editor_lock import (
    EditorLock,
    EditorLockConflictError,
    EditorLockManager,
)
from app.integrations.chatcut.mcp_adapter import ChatCutMCPAdapter
from app.integrations.chatcut.synchronizer import EditorStateSynchronizer, EditorSyncReport

__all__ = [
    "ChatCutAdapter",
    "StubChatCutAdapter",
    "ChatCutMCPAdapter",
    "EditorController",
    "EditorConflictError",
    "EditorExecutionReport",
    "EditorLock",
    "EditorLockConflictError",
    "EditorLockManager",
    "EditorStateSynchronizer",
    "EditorSyncReport",
]
