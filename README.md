# Hirthick’s Vision Studio | Video Editing Automation Backend

> **An enterprise-grade, resumable, graph-orchestrated backend for AI-assisted YouTube Shorts production using LangGraph, Pydantic, ChatCut Desktop MCP, SQLite, and an Inter-font kinetic typography animation engine.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-79%20passed-brightgreen.svg)](tests/)
[![Format](https://img.shields.io/badge/target-1080x1920%20%40%2030fps-orange.svg)]()
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)]()

---

## 📖 Overview

Hirthick’s Vision Studio automates the repetitive stages of high-engagement vertical YouTube Shorts production while maintaining human creative authority and deterministic engineering guardrails.

The backend delivers end-to-end orchestration:
- **Intake & Scanning:** Zero-mutation read-only project scanner with authentic asset verification.
- **Workflow Orchestration:** Single LangGraph StateGraph with parallel fan-out/fan-in branching, deterministic reducers, and interrupt-based human approval checkpoints.
- **Editor Co-Pilot:** 6-step transactional ChatCut Desktop MCP protocol with pre-edit rollback snapshots (`duplicate_project`), revision hashing, and drift reconciliation.
- **Strict Guardrails:** Strictly **zero synthetic AI diffusion video**, **zero generative images**, and **zero SVG vector cards** on the timeline. Authentic user recordings and licensed B-roll only.
- **Animation Render Engine:** High-performance Python Pillow + FFmpeg composition pipeline featuring Google **Inter** typography, kinetic word-by-word reveals, spring easing, frosted glass lower thirds, and audio ducking (-18dB).
- **Publishing Staging:** Hash-certified MP4 render, SEO-optimized title variants, description with timestamps, tags, and pinned engagement comment.

---

## 🏗️ Architecture

```
                                [ Human Operator ]
                                        |
                             Reviews / Resumes / Approves
                                        v
                       +---------------------------------+
                       | LangGraph Workflow Orchestrator |
                       |    (StateGraph + Interrupts)    |
                       +---------------------------------+
                                        |
                 +----------------------+----------------------+
                 |                                             |
                 v                                             v
     [ Canonical Pydantic State ]                 [ SQLite Checkpointer ]
     (Validated Models & Reducers)                (WAL Mode, Job Event Log)
                 |
                 +----------------------+
                                        v
                       +---------------------------------+
                       |      Deterministic Services     |
                       |  - AssetGuardrail (Anti-SVG)    |
                       |  - ProjectScanner (Read-only)   |
                       |  - MediaUnderstanding (ffprobe) |
                       |  - Script & Shot Planning       |
                       |  - EditPlanner (5-Track Layout) |
                       |  - CritiqueService (7 Aspects)  |
                       |  - RenderEngine (Inter Font)    |
                       |  - Export & Publishing Package  |
                       +---------------------------------+
                                        |
                                        v
                       +---------------------------------+
                       |  ChatCut MCP Integration Layer  |
                       |  - ChatCutMCPAdapter (CLI/stdio)|
                       |  - EditorLockManager (Lease)    |
                       |  - EditorController (6-step)    |
                       |  - EditorSynchronizer (Drift)   |
                       +---------------------------------+
```

---

## ⚡ Quickstart

### 1. Prerequisites
- **Python 3.11+**
- **FFmpeg & FFprobe** (in PATH or bundled via ChatCut)
- **Node.js v20+** (if running live ChatCut MCP via `@chatcut/cli`)
- **ChatCut Desktop v0.9.12.0** (optional for live mode; fallback simulator included)

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/Hirthick17/Video_Editing_Internal.git
cd Video_Editing_Internal

# Set up virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Test Suite
All 79 unit and integration tests run in ~9 seconds:
```powershell
pytest -v
```

### 4. Render the Animated Short #13
```powershell
python scripts/render_animated_short_13.py
```
Outputs the verified 1080×1920 30.0s MP4 with Inter font kinetic reveals to `reports/short-13-final-render.mp4`.

---

## 🎯 Case Study: Short #13

**Short #13: "Automating a PG's rent book on WhatsApp"**
- **Problem:** PG and coliving operators waste 6+ hours monthly chasing unstructured WhatsApp UPI screenshot receipts and typing them into Excel.
- **Solution:** TellOS WhatsApp bot uses OCR to read payment screenshots, issues instant branded receipts, and syncs a Google Sheets ledger in real time.
- **Timeline Specs:** 1080×1920, 30 FPS, exactly 900 frames / 30.00s.
- **Track Layout:**
  - `Track V1`: Main TellOS Android demo screen capture (`demo-recording-1.mp4`)
  - `Track V2`: Licensed Pixabay spreadsheet B-roll (`broll-spreadsheet.mp4`, 0–5s hook)
  - `Track A1`: Authentic dialogue audio at unity gain (0dB)
  - `Track A2`: Licensed background soundtrack (`bg-music.mp3`) ducked to -18dB
  - `Track TXT`: 4 native typographic caption cues with Inter font

---

## 📚 Documentation Links

- [Knowledge Transfer Document](docs/KNOWLEDGE_TRANSFER.md) — Comprehensive developer guide covering architecture, state flow, and extension patterns.
- [Video Automation Production Log](docs/video-automation-log.md) — Chronological engineering execution log from Phase 0 to Phase 10.
- [Build Pack Specifications](docs/build-pack/) — Original architectural requirements, MCP contracts, and operating standards.
- [Audit Deliverables & Reports](reports/) — Phase-by-phase verification reports, state-diff reports, and quality scorecards.

---

## 🧪 Test Coverage

| Test Module | Coverage Area | Tests | Status |
| :--- | :--- | :---: | :---: |
| `test_approval_rejection.py` | Human approval rejection routing | 1 | ✅ |
| `test_asset_guardrail.py` | Anti-SVG & synthetic media rejection | 4 | ✅ |
| `test_bounded_retries.py` | Bounded retries (limit: 3) & escalation | 2 | ✅ |
| `test_chatcut_contracts.py` | Half-open frame math & time conversions | 5 | ✅ |
| `test_editor_controller.py` | 6-step safe transactional editing | 4 | ✅ |
| `test_editor_lock.py` | SQLite lease lock & conflict protection | 3 | ✅ |
| `test_editor_normalization.py` | ChatCut project & timeline normalizers | 2 | ✅ |
| `test_event_traceability.py` | Append-only SQLite audit event trail | 1 | ✅ |
| `test_graph_execution.py` | Parallel branches, pause & resume | 1 | ✅ |
| `test_idempotency.py` | Duplicate job & edit operation prevention | 2 | ✅ |
| `test_invalid_state.py` | Pydantic validation & boundary checks | 4 | ✅ |
| `test_persistence_sqlite.py` | Relational SQLite CRUD & transactions | 7 | ✅ |
| `test_phase4_planning.py` | Script, beats, shot plan continuity | 6 | ✅ |
| `test_phase5_intake.py` | ffprobe, transcripts, clip matching | 5 | ✅ |
| `test_phase6_edit_planning.py`| Multi-track layout, 15 atomic ops | 6 | ✅ |
| `test_phase7_assembly.py` | ChatCut MCP assembly & state sync | 1 | ✅ |
| `test_phase8_critique.py` | 7-dimension critique scorecard & masking| 2 | ✅ |
| `test_phase9_export_publishing.py` | Export gates, post-render validation | 3 | ✅ |
| `test_phase10_retrospective.py`| Telemetry metrics & scaling policy | 1 | ✅ |
| `test_project_scanner.py` | Read-only scanner & SVG quarantine | 5 | ✅ |
| `test_reducers_parallel.py` | Conflict-free state reducers | 4 | ✅ |
| `test_render_engine.py` | Inter font, easing curves, word reveals | 4 | ✅ |
| `test_restart_recovery.py` | Job recovery across process restart | 1 | ✅ |
| `test_state_serialization.py` | ProductionState roundtrip & version bump | 2 | ✅ |
| `test_synchronizer_drift.py` | Timeline layout hash & drift detection | 3 | ✅ |
| **Total** | | **79** | **100% Pass** |

---

## 🔒 Security & Guardrails

- **Zero Diffusion Video:** Strictly enforced at file ingestion and timeline assembly.
- **Rollback Protection:** Every edit batch automatically creates a pre-edit project clone (`rollback_chk_<id>`).
- **Human Approval Gates:** Mandatory approval checkpoints before rough-cut timeline writing and before final MP4 export.
- **Zero Auto-Publishing:** Staging materials (titles, tags, descriptions) are generated for manual operator upload only.

---

*Hirthick’s Vision Studio | November 2026*

