# Developer Knowledge Transfer (KT) Document
## Hirthick’s Vision Studio | Video Editing Backend & Automation System

---

## 1. Executive Summary & Purpose

**Hirthick’s Vision Studio** is an enterprise-grade, resumable, graph-orchestrated video production backend designed to automate repetitive stages of YouTube Shorts production while enforcing strict guardrails and retaining human creative authority.

### Key Capabilities
- **Orchestration Engine:** Built on **LangGraph** (`StateGraph`) with SQLite-backed checkpointing (`SqliteSaver`), supporting parallel fan-out/fan-in branching, deterministic conflict-free reducers, and explicit human-in-the-loop pause/resume gates.
- **Editor Co-Pilot:** Integrates with **ChatCut Desktop** (v0.9.12.0) via Model Context Protocol (MCP) using a safe 6-step transactional editing protocol with pre-edit rollback snapshots.
- **Strict Brand Guardrails:** Zero AI-generated video diffusion, zero synthetic imagery, and zero SVG vector cards on the timeline. All visuals derive exclusively from authentic user screen recordings and licensed B-roll.
- **Deterministic Services:** 100% testable deterministic Python services for file scanning, SHA-256 checksumming, ffprobe technical metadata extraction, word-timed transcript generation, half-open interval math, multi-track cutlist assembly, and multi-dimensional quality critique.
- **Dynamic Animation Engine:** Python Pillow + FFmpeg composition pipeline featuring Google **Inter** typography, word-by-word kinetic reveals, spring physics easing curves, frosted glass lower-thirds, dynamic progress bar, Ken Burns zoom, and automatic -18dB audio ducking.
- **Quality Assurance:** 25 test suites with 79 tests passing in ~9 seconds with 100% pass rate.

---

## 2. System Architecture

The studio follows a layered, decoupled architecture separating orchestration, state management, deterministic logic, editor integration, and persistence.

```
                           +--------------------------------------+
                           |          Human Operator / UI         |
                           +--------------------------------------+
                                      |                ^
                             Approvals / Reviews    Inspection
                                      v                |
                           +--------------------------------------+
                           |   LangGraph Production Orchestrator  |
                           |       (StateGraph + Interrupts)      |
                           +--------------------------------------+
                                      |                |
                     +----------------+                +----------------+
                     v                                                  v
         +-----------------------+                          +-----------------------+
         | Canonical Pydantic    |                          | SQLite Checkpointer   |
         | ProductionState       |                          | (WAL Mode + Audit Log)|
         +-----------------------+                          +-----------------------+
                     |
                     v
   +---------------------------------------------------------------------------------+
   |                             Deterministic Services                              |
   |                                                                                 |
   |  [ProjectScanner]    -> Reads project assets without mutations                  |
   |  [AssetGuardrail]    -> Quarantines SVGs, enforces authentic media only         |
   |  [MediaUnderstanding]-> Technical ffprobe, scene segmentation, word timing     |
   |  [ResearchService]   -> Validates facts against tested product reality          |
   |  [ScriptService]     -> Calibrates words for target WPM and narrative curve     |
   |  [ShotPlanner]       -> Frame-accurate half-open intervals [start, end)        |
   |  [EditPlanner]       -> 5-track layout (V1/V2/A1/A2/TXT), 15 atomic operations  |
   |  [CritiqueService]   -> 7-dimension quality scorecard (threshold >= 9.0/10)     |
   |  [RenderEngine]      -> Inter font kinetic typography, overlays, audio ducking  |
   |  [ExportPublishing]  -> Hash-certified MP4 render, metadata packaging          |
   +---------------------------------------------------------------------------------+
                                      |
                                      v
   +---------------------------------------------------------------------------------+
   |                          ChatCut MCP Integration Layer                          |
   |                                                                                 |
   |  [ChatCutMCPAdapter]   -> Stdio/CLI transport (@chatcut/cli) + simulated mode    |
   |  [EditorLockManager]   -> SQLite lease locks preventing concurrent edits        |
   |  [EditorController]    -> 6-step safe transactional editing protocol             |
   |  [EditorSynchronizer]  -> Layout hash comparison & frame drift detection        |
   +---------------------------------------------------------------------------------+
```

---

## 3. Directory Structure & Key Files

```
hirthicks-vision-studio/
├── app/
│   ├── approvals/
│   │   ├── __init__.py
│   │   └── approval_service.py       # Human gatekeeper: inspect, approve, reject, resume
│   ├── config.py                     # Environment settings (Pydantic Settings)
│   ├── integrations/
│   │   └── chatcut/
│   │       ├── __init__.py
│   │       ├── adapter_interface.py  # Abstract boundary (ChatCutAdapter) & StubAdapter
│   │       ├── editor_controller.py  # 6-step transactional editor controller with rollback
│   │       ├── editor_lock.py        # SQLite lease locks for concurrent edit protection
│   │       ├── mcp_adapter.py        # Production MCP adapter (@chatcut/cli) & simulator
│   │       └── synchronizer.py       # Layout reconciliation & drift detection
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── graph.py                  # LangGraph StateGraph builder with SqliteSaver
│   │   ├── nodes.py                  # Graph execution nodes (parallel branches, fan-in)
│   │   └── routing.py                # Conditional edges (approval, validation, failure)
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── database.py               # SQLite connection factory & migration runner
│   │   ├── repository.py             # Transactional JobRepository (jobs, checkpoints, audit)
│   │   └── schema.sql                # Relational DDL (WAL mode, indexes, foreign keys)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── assembly_service.py       # Phase 7: ChatCut assembly & state verification
│   │   ├── asset_guardrail.py        # Strict guardrail: rejects SVGs & synthetic media
│   │   ├── checksum.py               # Chunked SHA-256 for large files & byte strings
│   │   ├── critique_service.py       # Phase 8: 7-dimension critique scorecard
│   │   ├── edit_planner_service.py   # Phase 6: Multi-track timeline assembly & cutlists
│   │   ├── export_publishing_service.py # Phase 9: Verified MP4 render & SEO package
│   │   ├── media_understanding_service.py # Phase 5: ffprobe, transcripts, clip matching
│   │   ├── project_scanner.py        # Phase 3: Zero-mutation project & asset scanner
│   │   ├── render_engine.py          # Pillow + FFmpeg animation engine with Inter font
│   │   ├── research_service.py       # Phase 4: Research context & claim verification
│   │   ├── retrospective_service.py  # Phase 10: Production metrics & scaling governance
│   │   ├── script_service.py         # Phase 4: 58-word calibrated script (4 beats)
│   │   ├── shot_planner_service.py   # Phase 4: 4-shot continuity plan [start, end)
│   │   └── time_codes.py             # Integer frame conversions & interval math
│   └── state/
│       ├── __init__.py
│       ├── asset_manifest.py         # Asset and project registry models
│       ├── editor_contracts.py       # ClipSpec, TrackSpec, EditOperation, TimelineSpec
│       ├── editor_models.py          # ChatCut response models & layout revision hashing
│       ├── enums.py                  # JobStatus, ProductionStage, EditOperationType, etc.
│       ├── models.py                 # Core domain models (Script, Shot, Edit, Critique)
│       └── production_state.py       # Canonical ProductionState & annotated channel reducers
├── assets/
│   ├── fonts/
│   │   └── Inter-Variable.ttf        # Google Inter font for kinetic typography
│   └── sample-media/
│       ├── bg-music.mp3              # Authentic licensed background audio
│       └── broll-spreadsheet.mp4     # Authentic licensed Pixabay stock B-roll
├── data/
│   └── studio_persistence.db         # Runtime SQLite database (WAL mode, git-ignored)
├── docs/
│   ├── KNOWLEDGE_TRANSFER.md         # This comprehensive guide
│   ├── video-automation-log.md       # Chronological session engineering log
│   └── build-pack/                   # Build Pack v0.2 specifications (01 to 08)
├── reports/                          # Phase 0-10 audit deliverables & sample renders
├── scripts/
│   ├── generate_phase7_10_reports.py # Report generation script
│   └── render_animated_short_13.py   # Full animation render runner
├── tests/                            # 25 test suites, 79 passing tests
├── pytest.ini                        # Pytest configuration (pythonpath = .)
├── README.md                         # Project overview and quickstart
└── requirements.txt                  # Python dependencies
```

---

## 4. Core Concepts & Technical Invariants

### 4.1 Strict Authentic Media Guardrail (Non-Negotiable)
The studio strictly forbids synthetic, diffusion-generated, or vector graphics overlays:
- **Prohibited:** AI-generated video (Sora/Runway/Kling/Pika), diffusion images (Midjourney/DALL-E), and SVG vector cards (`.svg`, `.ai`, `.eps`).
- **Enforced via:** `AssetGuardrailService.validate_candidate_file()`. Files with forbidden extensions or XML/SVG header bytes (`<svg`, `xml`) are rejected with `AssetGuardrailViolationError`.
- **Legacy Phase 0 SVGs:** 4 early test cards (`card1_hook.svg`, `card2_solution.svg`, etc.) are isolated in a quarantine registry and permanently excluded from timeline assembly.

### 4.2 Integer Frame Positions & Half-Open Intervals
All video timing uses **integer frame counts** with **half-open intervals** `[start_frame, end_frame)`:
- Duration in frames: $\text{duration} = \text{end\_frame} - \text{start\_frame}$
- Two intervals $[s_1, e_1)$ and $[s_2, e_2)$ do NOT overlap if $e_1 \le s_2$ or $e_2 \le s_1$.
- Target format: **1080×1920 (9:16 vertical), exactly 30.00 FPS, exactly 900 frames (30.0s)**.

### 4.3 Safe 6-Step Transactional Editing Protocol
Editing a timeline in ChatCut follows a strict protocol implemented in `EditorController.apply_verified_edit()`:
1. **Lock Acquisition:** `EditorLockManager.acquire_lock()` acquires an exclusive lease lock.
2. **Read-Before-Write:** MCP `get_timeline()` inspects the current timeline and computes its SHA-256 layout hash. If conflict detected, write aborts.
3. **Rollback Snapshot:** MCP `duplicate_project()` creates an immutable pre-edit project clone (`rollback_chk_<id>`).
4. **Idempotent Batch Execution:** Operations with previously applied idempotency keys are skipped. New operations execute sequentially.
5. **Read-After-Write Verification:** The timeline is read back and reconciled via `EditorStateSynchronizer.reconcile()`. If drift or prohibited assets are detected, automatic rollback is triggered.
6. **Lock Release:** Lock is released in a guaranteed `finally` block.

---

## 5. State Management & LangGraph Workflow

### 5.1 State Reducers (`app/state/production_state.py`)
In LangGraph, parallel branches can return partial state updates. Custom reducers prevent overwrites:
```python
def append_unique_strings(existing: List[str], new_items: List[str]) -> List[str]:
    """Preserves order, deduplicates items across branches."""

def merge_asset_registry(existing: Dict[str, AssetRecord], new_assets: Dict[str, AssetRecord]) -> Dict[str, AssetRecord]:
    """Deterministically merges asset dictionaries."""

def append_error_records(existing: List[NodeErrorRecord], new_errors: List[NodeErrorRecord]) -> List[NodeErrorRecord]:
    """Maintains an immutable append-only error trail."""
```

### 5.2 LangGraph Graph Construction (`app/orchestration/graph.py`)
```
[load_project] -> [parallel: validate_metadata & validate_assets] -> [merge_validation]
                       |
                       v
              [human_approval_gate] (LangGraph interrupt)
                       |
           +-----------+-----------+
           |                       |
     (APPROVED)               (REJECTED)
           v                       v
    [resume_workflow]       [handle_rejection]
           |
           v
    [complete_job]
```

Human approval pauses execution using LangGraph's native `interrupt()`. Resuming requires passing a valid `ApprovalRecord` via `Command(resume=...)`.

---

## 6. The Animation Engine (`render_engine.py`)

The dynamic rendering engine produces high-engagement YouTube Shorts without synthetic diffusion:

### Architecture
1. **Pillow Frame Generator:** Pre-computes 900 transparent RGBA PNG frames (30 FPS × 30s) containing:
   - **Kinetic Word Reveals:** Staggered entrance with 20px slide-up and cubic easing (`Easing.ease_out_cubic`).
   - **Accent Highlighting:** Key impact terms (e.g., *"50 PG tenants"*, *"hours wasted"*, *"TellOS"*) highlighted in WhatsApp Green (`#25D366`).
   - **Lower-Third Badges:** Glassmorphic translucent cards entering with spring physics (`Easing.ease_out_back`).
   - **Progress Bar:** 4px bottom bar with glowing position indicator.
2. **FFmpeg Compositor:** Single complex filter execution:
   - Scales and crops the authentic demo recording to 1080×1920.
   - Overlays the spreadsheet B-roll on frames 0–150 (0–5s) with a 0.5s fade-out.
   - Applies a continuous slow Ken Burns zoom (`1.0x → 1.03x`) and perimeter vignette (`vignette=PI/5`).
   - Overlays the 900 transparent animated PNG frames.
   - Mixes dialogue audio at unity gain (0dB) with background music ducked to -18dB (volume: `0.125`).

---

## 7. Developer Setup & Quickstart

### 7.1 Prerequisites
- **OS:** Windows 10/11 x64 (ChatCut Desktop environment) or Linux/macOS for headless simulation.
- **Python:** 3.11, 3.12, or 3.13.
- **Node.js:** v20+ (for `@chatcut/cli`).
- **ChatCut Desktop:** 0.9.12.0 (optional for live MCP mode; simulated mode runs without it).
- **FFmpeg & FFprobe:** Installed in PATH or bundled via ChatCut (`node_modules/ffmpeg-ffprobe-static`).

### 7.2 Installation
```powershell
# Clone the repository
git clone https://github.com/Hirthick17/Video_Editing_Internal.git
cd Video_Editing_Internal

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 7.3 Running Tests
All 79 tests run in ~9 seconds:
```powershell
pytest -v
```

### 7.4 Running the Animated Video Render
```powershell
python scripts/render_animated_short_13.py
```
Output MP4 will be saved to `reports/short-13-final-render.mp4`.

### 7.5 Generating Phase Reports
```powershell
python scripts/generate_phase7_10_reports.py
```

---

## 8. Case Study Milestone: Short #13

- **Title:** *"Automating a PG's rent book on WhatsApp"*
- **Target Audience:** Coliving and paying-guest (PG) accommodation operators in India.
- **Core Pain Point:** Chasing unstructured WhatsApp UPI screenshot receipts and manually typing them into Excel spreadsheets (6+ hours wasted monthly).
- **Solution Demoed:** TellOS WhatsApp bot reads incoming receipts via OCR, issues instant branded confirmations, and synchronizes a Google Sheets ledger in real time.
- **Authentic Assets Used:**
  - `demo-recording-1.mp4`: Real TellOS Android app screen recording.
  - `broll-spreadsheet.mp4`: Licensed Pixabay stock footage of accountant reviewing spreadsheet.
  - `bg-music.mp3`: Licensed background soundtrack.
- **Output:** Exactly 900 frames, 30.00 seconds, 1080×1920 vertical format.

---

## 9. Extending the System (How-To Guide)

### Adding a New Short (e.g., Short #14)
1. Add raw screen recordings to `assets/` and stock B-roll to `assets/sample-media/`.
2. Define the script in `app/services/script_service.py` adhering to the 4-beat structure (Hook, Problem, Solution, CTA) and ~130 WPM pacing.
3. Define the shot plan in `app/services/shot_planner_service.py` using half-open frame intervals summing to 900 frames.
4. Run `ProjectScannerService` to validate and register media into `AssetManifestRecord`.
5. Run `EditPlannerService` to generate the 5-track cutlist.
6. Assemble via `AssemblyService` or render animated overlays via `RenderPipeline`.

### Adding a New Critique Dimension
1. Open `app/services/critique_service.py`.
2. Implement a new classmethod: `evaluate_<dimension>(...) -> AspectCritique`.
3. Add the evaluation call inside `CritiqueService.run_comprehensive_critique()`.
4. Add the dimension to `ComprehensiveQualityScorecard`.
5. Add corresponding test in `tests/test_phase8_critique.py`.

---

## 10. Troubleshooting & FAQ

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| `AssetGuardrailViolationError` on file intake | File has `.svg` extension or SVG XML tags | The system strictly forbids SVGs. Use authentic MP4 recordings and native typographic captions. |
| `EditorConflictError` during write | Timeline was edited externally; revision hash mismatch | Another user edited the timeline in ChatCut. Fetch latest timeline revision before applying edits. |
| ChatCut CLI tool fails | ChatCut Desktop is not running | The adapter automatically falls back to deterministic simulation. To use live mode, launch ChatCut Desktop. |
| Text overflows screen | Caption text exceeds ~85% frame width | Adjust `font_size` in `FontConfig` or break text into multiple lines in `CaptionAnimation`. |

---

*Document Author: Hirthick’s Vision Studio Engineering Team*  
*Last Updated: November 2026*

