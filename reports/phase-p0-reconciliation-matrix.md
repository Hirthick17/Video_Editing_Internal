# Phase P0 Report: Work Reconciliation & ChatCut Capability Matrix
**Hirthick’s Vision Studio v0.3 | 18 November 2026**
**Master Prompt: Pattern A Execution**

---

## 1. Reconciliation of Existing Work vs v0.3 Master Prompt

In accordance with Section 2 (*Authority and Precedence: 1. This brief, 2. Build Pack v0.2, 3. Everything else*) and Section 3 (*Scope*), the existing codebase has been audited and reconciled:

### Retained & Verified
1. **Core Domain & Persistence Layer:**
   - Canonical Pydantic models for jobs, states, assets, and approval records.
   - SQLite persistence layer with WAL mode and relational schema (`schema.sql`, `JobRepository`).
   - Integer frame arithmetic and half-open intervals `[start_frame, end_frame)` with 30 FPS rational conversion (`time_codes.py`).
2. **ChatCut MCP Integration Infrastructure:**
   - Abstract boundary `ChatCutAdapter` and `@chatcut/cli` adapter (`mcp_adapter.py`).
   - SQLite-backed lease lock manager (`EditorLockManager`).
   - Safe 6-step transactional editor controller (`EditorController`) enforcing: Lock → Read-before-write → Duplicate snapshot rollback (`duplicate_project`) → Bounded batch write → Read-after-write verification → Release lock.
   - Timeline layout revision hashing (SHA-256) and drift reconciler (`synchronizer.py`).
3. **Deterministic Guardrails & Intake:**
   - `AssetGuardrailService`: Deterministic rejection of `.svg`, `.ai`, and vector graphics.
   - `ProjectScannerService`: Read-only intake and media metadata verification.
4. **Backend Web Services:**
   - FastAPI server (`app/web/server.py`) and CLI runner (`run_web.py`).

### Scoped Out / Deprecated per v0.3
1. **Custom Overlay Render Engine (`render_engine.py`):**
   - *Status:* **OUT OF SCOPE.**
   - *Reason:* Master Brief v0.3 Section 1 & Section 3 strictly dictate: *"The owner opens ChatCut Desktop and polishes it himself. You never replace ChatCut and never deliver a finished video. Out of scope: a custom render engine or overlay compositor (Pillow or FFmpeg overlay drawing)."*
   - *Action:* Deliverables will be native ChatCut timelines and project files, not custom FFmpeg rendered overlays.
2. **Batch / 1,000-Shorts Production (`large_scale_pipeline.py`):**
   - *Status:* **OUT OF SCOPE.**
   - *Reason:* Master Brief v0.3 Section 3 strictly dictates: *"Out of scope: batch or 1,000-videos-per-week production, a general-purpose dynamic editor."* Focus is 100% on **Pattern A** working end-to-end for single-owner talking-head videos.
3. **Synthetic / Generated Media Tools:**
   - *Status:* **HARD PROHIBITION.**
   - *Reason:* Master Brief v0.3 Section 4 strictly dictates: *"No generated video, images, SVG, icons, emoji graphics, stickers, shapes, lower-third plates, overlays, motion graphics, illustrations, or AI voice/music/SFX."*
   - *Action:* Blocked at ChatCut adapter level via strict allowlist.
4. **Invalid Excel Parameters (`short_form_video_pattern_analysis.xlsx`):**
   - *Status:* **DISCARDED AS EVIDENCE.**
   - *Reason:* Master Brief v0.3 Section 2 strictly dictates: *"The file short_form_video_pattern_analysis.xlsx is NOT evidence... Do not copy any number, color, font, BPM or dB value from it. Every pattern parameter must come from Section 8 measurement or from the owner."*

---

## 2. ChatCut Desktop MCP Capability Matrix

*Tested against local ChatCut Desktop v0.9.12 / v0.9.13 (83 live tools discovered via `@chatcut/cli tools list --json`).*

| Pipeline Operation | ChatCut Tool Name(s) | Status | Verification & Evidence | Notes / Constraints |
| :--- | :--- | :---: | :--- | :--- |
| **A-roll Cutting & Placement** | `edit_item`, `split_item` | **VERIFIED** | Live schema inspect confirms `edit_item` adds/modifies/deletes video & audio clips at integer timeline frames. `split_item` splits clips at absolute frames. | Preserves source mapping and linked audio. |
| **Native Captions & Styling** | `read_captions`, `edit_captions` | **VERIFIED** | Live schema inspect confirms `read_captions` reads cards, microsecond/frame bounds, text, words; `edit_captions` applies style, layout, font, and word-level emphasis. | Native ChatCut caption track only. |
| **Native Text Items (Hook & CTA)** | `edit_item` | **VERIFIED** | `edit_item` supports `type="text"` with font, size, position, and duration properties on dedicated text track. | Native text items only. No SVG/PNG plates. |
| **Static Scale Alternation** | `edit_item` | **VERIFIED** | `edit_item` properties support static `scale` and `transform` per item. | Static per-segment scale only (e.g. 100% vs 110%). No keyframe motion. |
| **Item & Segment Volume Ducking** | `edit_item`, `edit_track` | **VERIFIED** | `edit_item` accepts per-clip `volume`. `edit_track` schema explicitly supports `audioDucking` parameter. | Dialogue on Track A1 (0dB), Music on Track A2 (-18dB ducked), SFX on Track A3. |
| **Adding Dedicated Audio Tracks** | `edit_track` | **VERIFIED** | Live schema inspect confirms `edit_track` action="create" requires `type="audio"` with `name` and `order`. | Clean track layout: V1, V2, Captions, Text, A1, A2, A3. |
| **Asset Import (B-roll Candidates)** | `push_asset` | **VERIFIED** | Ingests media files into Project Assets bin by `filePath`. Verified in Phase 0. Leaves assets off the timeline by default. | B-roll candidates are imported into bin, NEVER placed on timeline unless `placement_mode=PLACE_TOP_PICK`. |
| **Project Duplication (Rollback Checkpoint)** | `duplicate_project` | **VERIFIED** | Creates full project snapshot before writing batch edits. Verified in Phase 0 baseline. | Non-destructive rollback guarantee. |
| **Read-Back & Drift Verification** | `read_captions`, `preview_timeline`, `inspect_item` | **VERIFIED** | Reads back timeline layout, item coordinates, and caption cards to compare against expected EditPlan. | Reconciles drift before releasing lock. |
| **Timeline Markers** | `manage_markers` | **VERIFIED** | `manage_markers` creates markers at absolute timeline frames for review queues and retake notes. | Used in handoff report. |
| **Final Export** | `export` | **VERIFIED** | Supports MP4, WAV, XML, subtitles export. | Manual owner polish & export in ChatCut Desktop. Agent does not auto-export. |
| **AI Generation Tools (Prohibited)** | `submit_video`, `submit_image`, `submit_voice`, `submit_avatar_video`, etc. | **BLOCKED** | Adapter allowlist enforces immediate rejection if any agent calls generative tools. | Hard prohibition enforced in code. |

---

## 3. Risks & Architecture Boundaries

1. **Owner Input Dependency (Section 5):** Phase R reference measurement and PatternSpec v1 cannot begin without the owner's reference video files (8-10 videos each for Ishan Sharma and Tharun Speaks) and decision on target style.
2. **Language & Caption Glyph Support:** The Google Inter font supports Latin alphabet only. If the owner's clips are in Hindi, Tamil, Telugu, or Hinglish/Tanglish with non-Latin scripts, font selection and Whisper model parameters must be adjusted.
3. **Editor Polish Baseline:** The success metric (reducing manual editing from 6-7 hours to $\le 30$ minutes) requires the owner's confirmation of their real-world editing baseline.

---

## 4. Phase P0 Exit Gate Recommendation

- **ChatCut Capability Matrix:** Fully audited and verified against live Desktop tools.
- **Codebase Reconciled:** Scoped out custom render engine and batch pipelines; retained core state, persistence, adapter, and test suites.
- **Next Proposed Phase:** **Phase 1** (Adapter allowlist, timeline scanner, and Pattern A state machine) followed by **Phase 2 / Phase R** (Reference measurement once Section 5 inputs arrive).
- **Owner Action Required:** Review and approve the capability matrix, and provide the 8 Section 5 inputs below.
