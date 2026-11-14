"""Abstract contract and stub implementation for future ChatCut MCP integration."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.state.editor_contracts import ClipSpec, EditOperation, TimelineSpec, TrackSpec


class ChatCutAdapter(ABC):
    """Abstract interface defining the communication boundary with ChatCut MCP."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection with ChatCut MCP (named pipe or stdio)."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect and release resources."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if connection is active."""
        pass

    @abstractmethod
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Fetch project metadata."""
        pass

    @abstractmethod
    def get_timeline(self, timeline_id: str) -> Dict[str, Any]:
        """Fetch timeline structure, tracks, and clips."""
        pass

    @abstractmethod
    def push_asset(self, project_id: str, file_path: str) -> Dict[str, Any]:
        """Ingest a local media asset into ChatCut project storage."""
        pass

    @abstractmethod
    def apply_batch_operations(
        self,
        timeline_id: str,
        operations: List[EditOperation],
    ) -> List[Dict[str, Any]]:
        """Apply a batch of editing operations idempotently."""
        pass

    @abstractmethod
    def preview_timeline(self, timeline_id: str, frame: int) -> Dict[str, Any]:
        """Request visual frame preview for inspection."""
        pass

    @abstractmethod
    def duplicate_project(self, project_id: str, new_name: str) -> Dict[str, Any]:
        """Duplicate a project to establish a safe rollback checkpoint."""
        pass


class StubChatCutAdapter(ChatCutAdapter):
    """Deterministic stub implementation of ChatCutAdapter for Phase 1 testing and contract verification."""

    def __init__(self, connected: bool = True):
        self._connected = connected
        self.applied_operations: List[EditOperation] = []
        self.pushed_assets: List[str] = []

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_project(self, project_id: str) -> Dict[str, Any]:
        return {
            "project_id": project_id,
            "name": "Short 13 - TellOS PG Rent Book",
            "created_at": "2026-11-12T15:00:00Z",
            "active_timeline_id": "03501b27-ebf5-4aae-9eb6-6e7df21e0378",
        }

    def get_timeline(self, timeline_id: str) -> Dict[str, Any]:
        spec = TimelineSpec(width=1080, height=1920, fps=30)
        return {
            "timeline_id": timeline_id,
            "width": spec.width,
            "height": spec.height,
            "fps": spec.fps,
            "duration_frames": 900,
            "tracks": [
                {"track_id": "V1", "name": "Main Demo", "type": "video", "items": []},
                {"track_id": "V2", "name": "B-roll Stock", "type": "video", "items": []},
                {"track_id": "A1", "name": "Voiceover", "type": "audio", "items": []},
                {"track_id": "A2", "name": "BGM", "type": "audio", "items": []},
            ],
        }

    def push_asset(self, project_id: str, file_path: str) -> Dict[str, Any]:
        self.pushed_assets.append(file_path)
        return {
            "asset_id": f"ast_{len(self.pushed_assets)}",
            "project_id": project_id,
            "path": file_path,
            "status": "INGESTED",
        }

    def apply_batch_operations(
        self,
        timeline_id: str,
        operations: List[EditOperation],
    ) -> List[Dict[str, Any]]:
        results = []
        for op in operations:
            op.applied = True
            op.verified = True
            self.applied_operations.append(op)
            results.append({"operation_id": op.operation_id, "status": "SUCCESS"})
        return results

    def preview_timeline(self, timeline_id: str, frame: int) -> Dict[str, Any]:
        return {
            "timeline_id": timeline_id,
            "frame": frame,
            "preview_url": f"file:///preview/frame_{frame}.png",
        }

    def duplicate_project(self, project_id: str, new_name: str) -> Dict[str, Any]:
        return {
            "original_project_id": project_id,
            "duplicate_project_id": f"dup_{project_id}",
            "name": new_name,
            "status": "DUPLICATED",
        }

