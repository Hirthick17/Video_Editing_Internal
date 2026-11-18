"""Production-ready ChatCut MCP adapter supporting named-pipe transport and deterministic simulation."""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from app.integrations.chatcut.adapter_interface import ChatCutAdapter
from app.services.asset_guardrail import AssetGuardrailService, AssetGuardrailViolationError
from app.state.editor_contracts import ClipSpec, EditOperation, TimelineSpec
from app.state.editor_models import (
    EditorItem,
    EditorProject,
    EditorTimeline,
    EditorTrack,
    normalize_chatcut_project,
    normalize_chatcut_timeline,
)
from app.state.enums import AssetType, EditOperationType

logger = logging.getLogger("chatcut_mcp_adapter")


class ChatCutAllowlistViolationError(RuntimeError):
    """Raised when an unallowed or prohibited generative/diffusion/voice tool is called."""
    pass


ALLOWED_CHATCUT_TOOLS = {
    # Project operations
    "list_projects",
    "get_active_project",
    "target_project",
    "create_project",
    "duplicate_project",
    "delete_project",
    # Timeline inspection & preview
    "list_timelines",
    "preview_timeline",
    "get_timeline",
    "set_active_timeline",
    # Track management
    "add_track",
    "edit_track",
    "delete_track",
    # Item & timeline manipulation
    "edit_item",
    "batch_edit_items",
    # Asset management
    "push_asset",
    "browse_assets",
    "get_asset",
    # Markers
    "add_marker",
    "list_markers",
    "delete_marker",
    # Player state
    "get_player_state",
    "seek",
}

PROHIBITED_CHATCUT_TOOLS = {
    "submit_video",
    "submit_image",
    "submit_voice",
    "generate_screen_from_text",
    "generate_variants",
    "create_design_system",
    "create_design_system_from_design_md",
    "apply_design_system",
    "generate_motion_graphics",
    "generate_speech",
    "generate_music",
}


def contains_emoji(text: str) -> bool:
    """Detect emoji characters in text strings."""
    if not text:
        return False
    for ch in text:
        code = ord(ch)
        if (
            0x1F600 <= code <= 0x1F64F
            or 0x1F300 <= code <= 0x1F5FF
            or 0x1F680 <= code <= 0x1F6FF
            or 0x1F700 <= code <= 0x1F77F
            or 0x1F780 <= code <= 0x1F7FF
            or 0x1F800 <= code <= 0x1F8FF
            or 0x1F900 <= code <= 0x1F9FF
            or 0x1FA00 <= code <= 0x1FA6F
            or 0x1FA70 <= code <= 0x1FAFF
            or 0x2600 <= code <= 0x26FF
            or 0x2700 <= code <= 0x27BF
        ):
            return True
    return False


class ChatCutMCPAdapter(ChatCutAdapter):
    """
    Adapter bridging Hirthick's Vision Studio with ChatCut MCP.
    Communicates via chatcut-mcp.cmd named-pipe transport or falls back to internal simulation for safe testing.
    """

    def __init__(self, mode: str = "auto", cli_executable: Optional[str] = None):
        self.mode = mode  # "auto", "live", "simulated"
        self._original_mode = mode  # preserve for diagnostics
        # Resolve CLI executable: prefer explicit path, then env var, then default chatcut-mcp.cmd
        if cli_executable:
            self.cli_executable = cli_executable
        else:
            appdata = os.environ.get("APPDATA", "")
            default_mcp_cmd = str(Path(appdata) / "ChatCut" / "chatcut-mcp.cmd") if appdata else ""
            self.cli_executable = os.environ.get("HVS_CHATCUT_MCP_CMD", default_mcp_cmd)
        self._connected = True
        self._fallback_warned = False
        # In-memory storage for simulated mode
        self._sim_projects: Dict[str, Dict[str, Any]] = {}
        self._sim_timelines: Dict[str, Dict[str, Any]] = {}
        self._applied_idempotency_keys: set = set()

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def _execute_cli_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a ChatCut tool through the MCP stdio server (JSON-RPC over stdin/stdout)."""
        if tool_name in PROHIBITED_CHATCUT_TOOLS or tool_name not in ALLOWED_CHATCUT_TOOLS:
            raise ChatCutAllowlistViolationError(
                f"ChatCut tool '{tool_name}' is strictly prohibited by Pattern A allowlist. "
                "Generative AI video/voice/diffusion and synthetic asset tools are forbidden."
            )

        # Verify MCP command exists before attempting
        mcp_cmd_path = Path(self.cli_executable)
        if not mcp_cmd_path.exists():
            msg = (
                f"ChatCut MCP command not found at '{self.cli_executable}'. "
                "Ensure ChatCut Desktop is installed and chatcut-mcp.cmd exists at "
                "%APPDATA%\\ChatCut\\chatcut-mcp.cmd"
            )
            if self.mode == "live":
                raise RuntimeError(msg)
            logger.warning("MCP command missing — falling back to simulated mode: %s", msg)
            self.mode = "simulated"
            self._log_fallback(tool_name, msg)
            return self._execute_simulated_tool(tool_name, arguments)

        try:
            logger.info("ChatCut MCP call: %s (args=%s)", tool_name, json.dumps(arguments)[:200])
            result = self._mcp_stdio_call(tool_name, arguments)
            logger.info("ChatCut MCP result for '%s': %s", tool_name, json.dumps(result)[:300])
            return result

        except ChatCutAllowlistViolationError:
            raise
        except Exception as e:
            if self.mode == "live":
                raise RuntimeError(
                    f"ChatCut live MCP call failed for '{tool_name}': {e}. "
                    "Ensure ChatCut Desktop is running and the MCP named pipe is active."
                ) from e
            self._log_fallback(tool_name, str(e))
            self.mode = "simulated"
            return self._execute_simulated_tool(tool_name, arguments)

    def _mcp_stdio_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single MCP tool call using the stdio transport protocol.
        Launches chatcut-mcp.cmd, performs the JSON-RPC handshake, sends the tool call,
        reads the response, and closes the process.
        """
        import time

        proc = subprocess.Popen(
            f'"{self.cli_executable}"',
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        try:
            # Step 1: Send initialize request
            init_req = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "HirthicksVisionStudio", "version": "0.3.0"}
                }
            }) + "\n"
            proc.stdin.write(init_req)
            proc.stdin.flush()

            # Read initialize response
            init_resp = self._read_jsonrpc_response(proc, expected_id=1, timeout=15)
            if not init_resp:
                # Capture stderr if available
                poll = proc.poll()
                stderr_text = ""
                try:
                    stderr_text = proc.stderr.read()
                except Exception:
                    pass
                raise RuntimeError(
                    f"MCP server did not respond to initialize (proc exit={poll}, stderr='{stderr_text[:500]}')"
                )

            # Step 2: Send initialized notification
            init_notif = json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }) + "\n"
            proc.stdin.write(init_notif)
            proc.stdin.flush()

            # Brief pause to let server process notification
            time.sleep(0.1)

            # Step 3: Send tool call
            tool_req = json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }) + "\n"
            proc.stdin.write(tool_req)
            proc.stdin.flush()

            # Read tool call response
            tool_resp = self._read_jsonrpc_response(proc, expected_id=2, timeout=30)
            if not tool_resp:
                poll = proc.poll()
                stderr_text = ""
                try:
                    stderr_text = proc.stderr.read()
                except Exception:
                    pass
                raise RuntimeError(
                    f"MCP server did not respond to tools/call for '{tool_name}' (proc exit={poll}, stderr='{stderr_text[:500]}')"
                )

            # Check for JSON-RPC error
            if "error" in tool_resp:
                err = tool_resp["error"]
                err_msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                if "conflicts with item" in err_msg or "already exists" in err_msg:
                    return {"status": "ALREADY_PLACED", "detail": "Items already exist on timeline"}
                raise RuntimeError(f"ChatCut tool '{tool_name}' returned error: {err_msg}")

            # Extract result content
            result = tool_resp.get("result", {})
            if isinstance(result, dict) and "content" in result:
                for item in result.get("content", []):
                    if isinstance(item, dict) and item.get("type") == "text":
                        try:
                            return json.loads(item["text"])
                        except (json.JSONDecodeError, ValueError):
                            pass
                return result

            return result if result else tool_resp

        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

    def _read_jsonrpc_response(self, proc: subprocess.Popen, expected_id: int, timeout: float = 15) -> Optional[Dict]:
        """Read lines from stdout until we find a JSON-RPC response with the expected id."""
        import time

        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                line = proc.stdout.readline()
            except Exception as e:
                logger.warning("Error reading line from MCP stdout: %s", e)
                break

            if not line:
                # Check if process has terminated
                if proc.poll() is not None:
                    logger.warning("MCP process exited prematurely with code %s", proc.poll())
                    break
                time.sleep(0.05)
                continue

            line = line.strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
                if isinstance(msg, dict):
                    if msg.get("id") == expected_id:
                        return msg
                    continue
            except (json.JSONDecodeError, ValueError):
                continue

        return None

    def _log_fallback(self, tool_name: str, reason: str) -> None:
        """Log a highly visible warning when falling back from live to simulated mode."""
        if not self._fallback_warned:
            logger.warning(
                "⚠️  CHATCUT FALLBACK: Switching from '%s' to simulated mode. "
                "Tool '%s' failed: %s. "
                "All subsequent operations will run in-memory only — "
                "NO real ChatCut project will be created on disk.",
                self._original_mode, tool_name, reason
            )
            self._fallback_warned = True
        else:
            logger.warning("ChatCut simulated fallback for tool '%s': %s", tool_name, reason)

    def _execute_simulated_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic simulation of ChatCut MCP tool responses matching exact schemas."""
        if tool_name in PROHIBITED_CHATCUT_TOOLS or tool_name not in ALLOWED_CHATCUT_TOOLS:
            raise ChatCutAllowlistViolationError(
                f"ChatCut tool '{tool_name}' is strictly prohibited by Pattern A allowlist. "
                "Generative AI video/voice/diffusion and synthetic asset tools are forbidden."
            )

        if tool_name == "create_project":
            p_id = args.get("projectId", f"proj_{len(self._sim_projects) + 1}")
            t_id = f"tl_{p_id}"
            proj_data = {
                "projectId": p_id,
                "name": args.get("name", "Untitled Project"),
                "activeTimelineId": t_id,
                "timelineIds": [t_id],
                "editorVersion": "0.9.12.0",
            }
            tl_data = {
                "timelineId": t_id,
                "projectId": p_id,
                "width": 1080,
                "height": 1920,
                "fps": 30,
                "durationFrames": 900,
                "tracks": [
                    {"trackId": "V1", "name": "Main Demo", "type": "video", "items": []},
                    {"trackId": "V2", "name": "B-roll Stock", "type": "video", "items": []},
                    {"trackId": "A1", "name": "Voiceover", "type": "audio", "items": []},
                    {"trackId": "A2", "name": "BGM", "type": "audio", "items": []},
                ],
            }
            self._sim_projects[p_id] = proj_data
            self._sim_timelines[t_id] = tl_data
            return {"project": proj_data, "timeline": tl_data}

        elif tool_name == "duplicate_project":
            orig_id = args.get("projectId")
            orig_proj = self._sim_projects.get(orig_id)
            if not orig_proj:
                orig_proj = self._execute_simulated_tool("target_project", {"projectId": orig_id})
                self._sim_projects[orig_id] = orig_proj

            new_id = f"dup_{orig_id}"
            new_t_id = f"tl_{new_id}"
            dup_proj = dict(orig_proj)
            dup_proj["projectId"] = new_id
            dup_proj["name"] = args.get("name", f"Copy of {orig_proj['name']}")
            dup_proj["activeTimelineId"] = new_t_id
            dup_proj["timelineIds"] = [new_t_id]

            # Deep copy timeline
            active_tl_id = orig_proj.get("activeTimelineId", "03501b27-ebf5-4aae-9eb6-6e7df21e0378")
            orig_tl = self._sim_timelines.get(active_tl_id)
            if not orig_tl:
                orig_tl = self._execute_simulated_tool("preview_timeline", {"timelineId": active_tl_id})
                self._sim_timelines[active_tl_id] = orig_tl
            dup_tl = json.loads(json.dumps(orig_tl))
            dup_tl["timelineId"] = new_t_id
            dup_tl["projectId"] = new_id

            self._sim_projects[new_id] = dup_proj
            self._sim_timelines[new_t_id] = dup_tl
            return {"status": "SUCCESS", "duplicatedProjectId": new_id, "project": dup_proj}

        elif tool_name == "target_project":
            p_id = args.get("projectId")
            if p_id in self._sim_projects:
                return self._sim_projects[p_id]
            proj_data = {
                "projectId": p_id,
                "name": "Short 13 - TellOS PG Rent Book",
                "activeTimelineId": "03501b27-ebf5-4aae-9eb6-6e7df21e0378",
                "timelineIds": ["03501b27-ebf5-4aae-9eb6-6e7df21e0378"],
                "editorVersion": "0.9.12.0",
            }
            self._sim_projects[p_id] = proj_data
            return proj_data

        elif tool_name == "preview_timeline":
            t_id = args.get("timelineId")
            if t_id in self._sim_timelines:
                return self._sim_timelines[t_id]
            return {
                "timelineId": t_id,
                "width": 1080,
                "height": 1920,
                "fps": 30,
                "durationFrames": 900,
                "tracks": [
                    {"trackId": "V1", "name": "Main Demo", "type": "video", "items": []},
                    {"trackId": "V2", "name": "B-roll Stock", "type": "video", "items": []},
                    {"trackId": "A1", "name": "Voiceover", "type": "audio", "items": []},
                    {"trackId": "A2", "name": "BGM", "type": "audio", "items": []},
                ],
            }

        elif tool_name == "add_track":
            t_id = args.get("timelineId")
            tl = self._sim_timelines.get(t_id)
            if not tl:
                tl = self._execute_simulated_tool("preview_timeline", {"timelineId": t_id})
                self._sim_timelines[t_id] = tl

            track_id = args.get("trackId")
            track_name = args.get("name", track_id)
            track_type = args.get("type", "video")
            order = args.get("order", len(tl.get("tracks", [])))
            existing = next((t for t in tl.get("tracks", []) if t.get("trackId") == track_id), None)
            if not existing:
                tl["tracks"].append(
                    {"trackId": track_id, "name": track_name, "type": track_type, "order": order, "items": []}
                )
            return {"status": "SUCCESS", "trackId": track_id}

        elif tool_name == "push_asset":
            file_path = args.get("filePath")
            return {
                "assetId": f"ast_{hash(file_path) % 1000000}",
                "projectId": args.get("projectId"),
                "path": file_path,
                "status": "INGESTED",
            }

        elif tool_name == "edit_item":
            t_id = args.get("timelineId")
            tl = self._sim_timelines.get(t_id)
            if not tl:
                tl = self._execute_simulated_tool("preview_timeline", {"timelineId": t_id})
                self._sim_timelines[t_id] = tl

            action = args.get("action", "insert")
            track_id = args.get("trackId", "V1")
            item_data = args.get("item", {})

            # Locate or create track
            target_trk = next((t for t in tl.get("tracks", []) if t.get("trackId") == track_id), None)
            if not target_trk:
                target_trk = {"trackId": track_id, "name": track_id, "type": "video", "items": []}
                tl.get("tracks", []).append(target_trk)

            if action == "insert":
                target_trk["items"].append(item_data)
            elif action == "remove":
                target_trk["items"] = [i for i in target_trk["items"] if i.get("itemId") != item_data.get("itemId")]

            return {"status": "SUCCESS", "action": action, "timelineId": t_id}

        return {"status": "UNKNOWN_TOOL", "tool": tool_name}

    def discover_active_project(self) -> Tuple[str, str]:
        """
        Discover the active project ID and timeline ID from ChatCut Desktop.
        In simulated mode, creates a new project. In live/auto mode, queries the running desktop.
        """
        if self.mode == "simulated":
            # Create a fresh simulated project instead of returning a fake hardcoded ID
            p_id = f"sim_proj_{len(self._sim_projects) + 1}"
            result = self._execute_simulated_tool("create_project", {
                "projectId": p_id,
                "name": "Pilot Short: Pattern A"
            })
            tl_id = result.get("timeline", {}).get("timelineId", f"tl_{p_id}")
            logger.info("Simulated project created: %s / %s", p_id, tl_id)
            return (p_id, tl_id)

        # Live / Auto mode: query ChatCut Desktop via MCP
        try:
            # First try get_active_project
            active_raw = self._execute_cli_tool("get_active_project", {})
            p_id = ""
            if isinstance(active_raw, dict):
                p_id = active_raw.get("projectId", "")
                if not p_id and "content" in active_raw:
                    for c in active_raw.get("content", []):
                        if isinstance(c, dict) and c.get("type") == "text":
                            try:
                                p = json.loads(c["text"])
                                if "projectId" in p:
                                    p_id = p["projectId"]
                                    break
                            except Exception:
                                pass

            # If no active project, list all and pick the most recent
            if not p_id:
                projects_raw = self._execute_cli_tool("list_projects", {})
                projs = []
                if isinstance(projects_raw, dict):
                    projs = projects_raw.get("projects", [])
                    if not projs and "content" in projects_raw:
                        for c in projects_raw.get("content", []):
                            if isinstance(c, dict) and c.get("type") == "text":
                                try:
                                    p = json.loads(c["text"])
                                    if "projects" in p:
                                        projs = p["projects"]
                                        break
                                except Exception:
                                    pass
                elif isinstance(projects_raw, list):
                    projs = projects_raw
                if projs:
                    p_id = projs[0].get("projectId", "")
                    logger.info("Selected first available project: %s", p_id)

            if not p_id:
                # No projects exist — create one via MCP
                logger.info("No ChatCut projects found. Creating a new project via MCP...")
                create_result = self._execute_cli_tool("create_project", {
                    "name": "Hirthick Vision Studio - Pattern A"
                })
                if isinstance(create_result, dict):
                    p_id = create_result.get("projectId", "")
                    if not p_id:
                        proj_data = create_result.get("project", {})
                        p_id = proj_data.get("projectId", "") if isinstance(proj_data, dict) else ""

            if p_id:
                target_res = self._execute_cli_tool("target_project", {"projectId": p_id, "openWindow": True})
                tl_id = ""
                if isinstance(target_res, dict):
                    tl_id = target_res.get("timelineId") or target_res.get("activeTimelineId", "")
                    if not tl_id and "content" in target_res:
                        for c in target_res.get("content", []):
                            if isinstance(c, dict) and c.get("type") == "text":
                                try:
                                    t = json.loads(c["text"])
                                    if "timelineId" in t:
                                        tl_id = t["timelineId"]
                                        break
                                except Exception:
                                    pass
                    # Also check nested timelines array
                    if not tl_id:
                        timelines = target_res.get("timelines", [])
                        if timelines and isinstance(timelines[0], dict):
                            tl_id = timelines[0].get("timelineId", "")
                logger.info("Discovered ChatCut project: %s / timeline: %s", p_id, tl_id)
                return (p_id, tl_id)

        except Exception as e:
            logger.error("Failed to discover ChatCut project: %s", e)
            if self.mode == "live":
                raise RuntimeError(
                    f"Cannot discover ChatCut project in live mode: {e}. "
                    "Ensure ChatCut Desktop is running with at least one project open."
                ) from e

        # Auto mode fallback: create a simulated project
        logger.warning("Auto mode: could not discover a live project, falling back to simulated.")
        self.mode = "simulated"
        self._log_fallback("discover_active_project", "No live project found")
        p_id = f"sim_proj_{len(self._sim_projects) + 1}"
        result = self._execute_simulated_tool("create_project", {
            "projectId": p_id,
            "name": "Pilot Short: Pattern A (Auto-Simulated)"
        })
        tl_id = result.get("timeline", {}).get("timelineId", f"tl_{p_id}")
        return (p_id, tl_id)

    def _get_live_asset_map(self, project_id: str) -> Dict[str, str]:
        """Fetch assets currently ingested in ChatCut Desktop project."""
        try:
            raw = self._execute_cli_tool("browse_assets", {"projectId": project_id})
            mapping: Dict[str, str] = {}
            assets = []
            if isinstance(raw, dict):
                if "assets" in raw:
                    assets = raw["assets"]
                elif "content" in raw and isinstance(raw["content"], list):
                    for c in raw["content"]:
                        if isinstance(c, dict) and c.get("type") == "text":
                            try:
                                parsed = json.loads(c["text"])
                                if "assets" in parsed:
                                    assets = parsed["assets"]
                                    break
                            except Exception:
                                pass
            for a in assets:
                if isinstance(a, dict):
                    fid = a.get("fullId") or a.get("id")
                    if fid:
                        if a.get("name"):
                            mapping[a["name"]] = fid
                        if a.get("filename"):
                            mapping[a["filename"]] = fid
                        if a.get("id"):
                            mapping[a["id"]] = fid
            return mapping
        except Exception:
            return {}

    def get_project(self, project_id: str) -> EditorProject:
        """Fetch project metadata and normalize into EditorProject."""
        if self.mode == "simulated":
            raw = self._execute_simulated_tool("target_project", {"projectId": project_id})
        else:
            raw = self._execute_cli_tool("target_project", {"projectId": project_id, "openWindow": True})
        return normalize_chatcut_project(raw)

    def get_timeline(self, timeline_id: str, project_id: str = "") -> EditorTimeline:
        """Fetch timeline structure and normalize into EditorTimeline."""
        args: Dict[str, Any] = {"timelineId": timeline_id}
        if project_id:
            args["projectId"] = project_id
        if self.mode == "simulated":
            raw = self._execute_simulated_tool("preview_timeline", args)
        else:
            raw = self._execute_cli_tool("preview_timeline", args)
        return normalize_chatcut_timeline(raw, project_id=project_id)

    def push_asset(self, project_id: str, file_path: str) -> Dict[str, Any]:
        """
        Ingest a local asset into ChatCut, strictly verifying against authentic media guardrails.
        Rejects SVGs or synthetic media BEFORE passing to ChatCut MCP!
        """
        path = Path(file_path)
        # Enforce asset guardrail check if file exists
        if path.is_file():
            AssetGuardrailService.validate_candidate_file(
                file_path=path,
                asset_type=AssetType.SCREEN_RECORDING,  # base check
            )
        elif path.suffix.lower() in [".svg", ".ai"]:
            raise AssetGuardrailViolationError(f"Cannot ingest prohibited SVG asset '{file_path}'")

        if self.mode == "simulated":
            return self._execute_simulated_tool("push_asset", {"projectId": project_id, "filePath": str(path)})
        return self._execute_cli_tool("push_asset", {"projectId": project_id, "filePath": str(path)})

    def duplicate_project(self, project_id: str, new_name: str) -> Dict[str, Any]:
        """Duplicate a project to establish a safe rollback checkpoint."""
        args = {"projectId": project_id, "name": new_name, "activate": False}
        if self.mode == "simulated":
            return self._execute_simulated_tool("duplicate_project", args)
        return self._execute_cli_tool("duplicate_project", args)

    def apply_batch_operations(
        self,
        timeline_id: str,
        operations: List[EditOperation],
        project_id: str = "",
        placement_mode: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Apply a batch of edit operations with idempotency tracking.
        Duplicate calls with the same idempotency key are skipped.
        """
        # Validate hard prohibitions
        for op in operations:
            if op.clip_spec and op.clip_spec.name.lower().endswith(".svg"):
                raise AssetGuardrailViolationError(
                    f"Cannot apply operation '{op.operation_id}': placing SVG cards is prohibited."
                )

            # Emoji check
            text_val = ""
            if op.parameters and "text" in op.parameters:
                text_val = str(op.parameters["text"])
            elif op.clip_spec and op.clip_spec.name:
                text_val = op.clip_spec.name

            if text_val and contains_emoji(text_val):
                raise AssetGuardrailViolationError(
                    f"Cannot apply operation '{op.operation_id}': emoji characters inside caption or text strings "
                    f"('{text_val}') are strictly prohibited."
                )

            # Stock B-roll placement check
            if placement_mode == "CANDIDATES_ONLY":
                t_id = (op.track_id or (op.clip_spec.track_id if op.clip_spec else "")).upper()
                if t_id.startswith("V"):
                    c_name = (op.clip_spec.name if op.clip_spec else "").lower()
                    c_asset = (op.clip_spec.asset_id if op.clip_spec else "").lower()
                    if "stock" in c_name or "broll" in c_name or "stock" in c_asset or "broll" in c_asset:
                        raise AssetGuardrailViolationError(
                            f"Cannot apply operation '{op.operation_id}': placing stock B-roll '{c_name}' on visual track '{t_id}' "
                            "is prohibited while placement_mode='CANDIDATES_ONLY'. Candidates must remain in project assets bin."
                        )

        if self.mode == "live" and project_id:
            asset_map = self._get_live_asset_map(project_id)
            adds = []
            for op in operations:
                if op.idempotency_key in self._applied_idempotency_keys:
                    continue
                if op.clip_spec:
                    spec = op.clip_spec
                    t_low = (op.track_id or spec.track_id or "V1").lower()
                    if "v1" in t_low:
                        chatcut_track = "V1"
                    elif "v2" in t_low:
                        chatcut_track = "V2"
                    elif "a1" in t_low:
                        chatcut_track = "A1"
                    elif "a2" in t_low:
                        chatcut_track = "A2"
                    else:
                        chatcut_track = "V1"

                    # Resolve desktop asset UUID
                    asset_uuid = (
                        asset_map.get(spec.name)
                        or asset_map.get(spec.name.split(".")[0])
                        or asset_map.get(spec.asset_id)
                    )
                    if not asset_uuid:
                        combined_key = f"{spec.name} {spec.asset_id}".lower()
                        if "demo" in combined_key:
                            asset_uuid = asset_map.get("demo-recording-1") or asset_map.get("demo-recording-1.mp4")
                        elif "broll" in combined_key or "spreadsheet" in combined_key:
                            asset_uuid = asset_map.get("broll-spreadsheet") or asset_map.get("broll-spreadsheet.mp4")
                        elif "music" in combined_key or "bgm" in combined_key:
                            asset_uuid = asset_map.get("bg-music") or asset_map.get("bg-music.mp3")
                        elif "voice" in combined_key or "narration" in combined_key:
                            asset_uuid = asset_map.get("bg-music") or asset_map.get("demo-recording-1")
                        else:
                            asset_uuid = next(iter(asset_map.values()), spec.asset_id)

                    is_audio = chatcut_track.startswith("A")
                    adds.append({
                        "type": "audio" if is_audio else "video",
                        "assetId": str(asset_uuid or spec.asset_id),
                        "trackId": chatcut_track,
                        "startFrame": spec.start_frame,
                        "durationFrames": max(1, spec.end_frame - spec.start_frame),
                        "media": "audio" if is_audio else "video",
                        "volume": spec.volume if is_audio else 1.0,
                    })

            if adds:
                res = self._execute_cli_tool(
                    "edit_item",
                    {"projectId": project_id, "timelineId": timeline_id, "adds": adds},
                )
            else:
                res = {"status": "NOOP"}

            results = []
            for op in operations:
                self._applied_idempotency_keys.add(op.idempotency_key)
                op.applied = True
                results.append({
                    "operation_id": op.operation_id,
                    "idempotency_key": op.idempotency_key,
                    "status": "APPLIED",
                    "tool_result": res,
                })
            return results

        # Simulated path
        results = []
        for op in operations:
            if op.idempotency_key in self._applied_idempotency_keys:
                results.append({
                    "operation_id": op.operation_id,
                    "idempotency_key": op.idempotency_key,
                    "status": "ALREADY_APPLIED",
                    "skipped": True,
                })
                op.applied = True
                continue

            if op.operation_type == EditOperationType.ADD_TRACK:
                args = {
                    "timelineId": timeline_id,
                    "trackId": op.track_id,
                    "name": op.parameters.get("name", op.track_id),
                    "type": op.parameters.get("type", "video"),
                    "order": op.parameters.get("order", 0),
                }
                tool_to_call = "add_track"
            elif op.operation_type == EditOperationType.ADD_CAPTION:
                args = {
                    "timelineId": timeline_id,
                    "action": "insert",
                    "trackId": op.track_id or "track_txt_captions",
                    "item": {
                        "itemId": op.parameters.get("caption_id", op.operation_id),
                        "assetId": "",
                        "startFrame": op.parameters.get("start_frame", 0),
                        "endFrame": op.parameters.get("end_frame", 30),
                        "name": op.parameters.get("text", "Caption"),
                        "volume": 0.0,
                        "properties": op.parameters.get("style", {}),
                    },
                }
                tool_to_call = "edit_item"
            else:
                args = {
                    "timelineId": timeline_id,
                    "action": "insert" if op.operation_type == EditOperationType.INSERT_CLIP else "edit",
                    "trackId": op.track_id or (op.clip_spec.track_id if op.clip_spec else "V1"),
                    "item": {
                        "itemId": op.clip_spec.item_id if op.clip_spec else op.operation_id,
                        "assetId": op.clip_spec.asset_id if op.clip_spec else "",
                        "startFrame": op.clip_spec.start_frame if op.clip_spec else 0,
                        "endFrame": op.clip_spec.end_frame if op.clip_spec else 30,
                        "name": op.clip_spec.name if op.clip_spec else "",
                        "volume": op.clip_spec.volume if op.clip_spec else 1.0,
                    },
                }
                tool_to_call = "edit_item"

            res = self._execute_simulated_tool(tool_to_call, args)
            self._applied_idempotency_keys.add(op.idempotency_key)
            op.applied = True
            results.append({
                "operation_id": op.operation_id,
                "idempotency_key": op.idempotency_key,
                "status": "APPLIED",
                "tool_result": res,
            })

        return results

    def preview_timeline(self, timeline_id: str, frame: int = 0, project_id: str = "") -> Dict[str, Any]:
        """Request visual timeline frame inspection."""
        args: Dict[str, Any] = {"timelineId": timeline_id, "frame": frame}
        if project_id:
            args["projectId"] = project_id
        if self.mode == "simulated":
            return self._execute_simulated_tool("preview_timeline", args)
        return self._execute_cli_tool("preview_timeline", args)

