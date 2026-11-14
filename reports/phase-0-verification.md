# Phase 0 Verification Report: ChatCut MCP & Integration Baseline

**Date:** 2026-11-13  
**Status:** Complete  
**Target Milestone:** Single-Short Validation (Short #13 — "Automating a PG's rent book on WhatsApp")

---

## 1. System & Dependency Environment

| Component | Reported Value | Verified Status | Evidence |
| :--- | :--- | :--- | :--- |
| **OS** | Windows 10/11 x64 | **Verified** | Windows 10+ PowerShell runtime |
| **Node.js** | v22.14.0 | **Verified** | CLI requires Node 22+; doctor check passed |
| **ChatCut Desktop** | `0.9.12.0` | **Verified** | Binary at `C:\Users\hirth\AppData\Local\Programs\ChatCut\ChatCut.exe` |
| **ChatCut CLI** | `@chatcut/cli@0.1.3` | **Verified** | `npx @chatcut/cli --version` output: `0.1.3` |
| **MCP Launcher** | `chatcut-mcp.cmd` | **Verified** | Script at `C:\Users\hirth\AppData\Roaming\ChatCut\chatcut-mcp.cmd` |
| **MCP Protocol** | `2025-11-25` | **Verified** | ChatCut MCP server declaration |
| **Active MCP Tools** | 64 Headless / 80 Live | **Verified** | 64 tools via standalone stdio; 80 tools when Desktop named pipe active |

---

## 2. Capability Verification Matrix

| Capability / Tool | MCP Tool Name | Status | Verified Behavior & Evidence |
| :--- | :--- | :--- | :--- |
| **MCP Connection** | `doctor` / `connect` | **VERIFIED** | Connected via stdio server (`chatcut_desktop`, version `0.2.0`). |
| **Project Creation** | `create_project` | **VERIFIED** | Created project `8a894b86-d5e0-4222-ab88-df22a8e2168e` and timeline `03501b27-ebf5-4aae-9eb6-6e7df21e0378`. |
| **Project Reading** | `list_projects`, `get_active_project` | **VERIFIED** | Discovered active projects and read metadata from disk JSON. |
| **Local Asset Ingest** | `push_asset` | **VERIFIED** | Imported `demo-recording-1.mp4` (video) and `bg-music.mp3` (audio) with valid asset IDs. |
| **Stock Media Search** | `search_stock_media` | **VERIFIED** | Successfully queried Pixabay API for "spreadsheet" video; returned direct download candidate URLs. |
| **Multi-Track Editing**| `edit_item` | **VERIFIED** | Placed video on V1 (`demo-recording-1`), V2 (`broll-spreadsheet`), and SVG cards on V3 with frame-accurate start/duration. |
| **Timeline Preview** | `preview_timeline` | **VERIFIED** | Returned structural tracks and rendered JPEG contact sheet (`fabf4e42-cb8a-4636-817d-0f15930a94e6.jpg`). |
| **Project Persistence**| Local Disk Sync | **VERIFIED** | Observed serialized timeline on disk at `AppData\Roaming\ChatCut\projects\<id>\project.chatcutproject\timelines\<id>.json`. |
| **Editor Rollback** | Undo / Snapshot | **UNVERIFIED** | Safe rollback/restore of live editor state via MCP is unverified. Duplicate project method required. |
| **Native Captions** | `edit_captions` | **UNVERIFIED** | Tool schema discovered; actual caption rendering on track has not been exercised. |
| **Final MP4 Export** | `export` | **UNVERIFIED** | No final MP4 export was generated or verified in previous run. |
| **Cloud Portability** | Headless Linux/Docker | **UNVERIFIED** | Windows native pipe and Electron binary prevent direct headless Linux execution without container adaptation. |

---

## 3. Inspection of Existing Short #13 Project

- **Project ID:** `8a894b86-d5e0-4222-ab88-df22a8e2168e`
- **Timeline ID:** `03501b27-ebf5-4aae-9eb6-6e7df21e0378`
- **Current Tracks on Disk:**
  - `V1`: `demo-recording-1.mp4` (asset `d4fc846950`, frames 0–900 / 30s)
  - `V2`: `broll-spreadsheet.mp4` (asset `7e28965802`, frames 0–150 / 5s)
  - `V3`: **4 Unapproved SVG Cards** from previous run:
    1. `card1_hook.svg` (asset `2224839778`, frames 0–150)
    2. `card2_solution.svg` (asset `e83c72a489`, frames 150–450)
    3. `card3_insight.svg` (asset `5c69a83e6b`, frames 450–720)
    4. `card4_cta.svg` (asset `521ce7fb06`, frames 720–900)
  - `A1`: Linked audio from demo recording (frames 0–900)
- **Export Status:** **NO EXPORT EXISTS.** No MP4 file was rendered.
- **Project Preservation:** In accordance with Build Pack v0.2 instructions, this existing project is preserved as a test artifact and will not be destructively deleted.

---

## 4. Key Architectural Discoveries & Boundaries

1. **Dual-Mode MCP Execution:**
   - When Desktop GUI is closed, the standalone Node MCP server (`server.js`) runs with 64 core tools.
   - When Desktop GUI is launched, a named pipe IPC (`\\.\pipe\chatcut-mcp-...`) connects the live UI, enabling 80 tools (including live window inspection `inspect_app`).
2. **Strict Guardrail Enforcement:**
   - All synthetic visual generation (AI video, diffusion, SVG cards) is blocked and quarantined.
   - Future production runs will use only real recordings, screen captures, and approved stock clips.

---

## 5. Phase 0 Exit Recommendation

**Phase 0 is COMPLETE.** 
All baseline dependencies, MCP tool capabilities, and existing project artifacts have been audited.

**Proposed Next Step:** Proceed to **Phase 1 (Backend Foundation and Graph State)** to implement the typed Pydantic models, SQLite persistence, and resumable graph orchestrator.
