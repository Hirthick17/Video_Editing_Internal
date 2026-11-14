# Phase 6 Deliverable: Edit Planning and Rough-Cut Assembly
**Hirthick’s Vision Studio | YouTube Shorts Production System**  
**Milestone:** Short #13 — "Automating a PG's rent book on WhatsApp"  
**Date:** 13 November 2026 | **Status:** 100% COMPLETE & APPROVED

---

## 1. Executive Summary

Phase 6 translates creative intent, verified claims, narration timing, and empirical media intake into a frame-accurate, deterministic edit plan and an atomic cutlist. The resulting rough cut adheres strictly to half-open integer intervals `[start_frame, end_frame)`, zero-synthetic production guardrails, and speech-first audio engineering.

### Phase 6 Milestones Achieved:
1. **Frame-Accurate Multi-Track Timeline:** Engineered a 5-track layout for vertical YouTube Shorts (1080×1920 @ 30 FPS, exactly 900 frames / 30.0s).
2. **Deterministic Half-Open Interval Sequencing:** Sequenced 4 visual cuts without gaps or overlaps (`[0, 150) -> [150, 360) -> [360, 660) -> [660, 900)`).
3. **Speech-First Audio Mixing:** Voiceover narration on Track A1 at unity gain (0dB), with background music on Track A2 ducked to -18dB (volume 0.125) to prevent dialogue masking.
4. **Native Typographic Captions:** Designed 4 readable, restrained subtitle cues bound to narration beats on Track TXT; strictly 0 vector SVG cards.
5. **Atomic Idempotent CutList:** Generated 15 verified `EditOperation` instances with unique idempotency keys ready for ChatCut MCP execution.
6. **Rough-Cut Human Approval Gate:** Persisted approval records in SQLite database via `ApprovalService`, ready for Phase 7 timeline writing.

---

## 2. Multi-Track Timeline Architecture

```text
Timeline Frames: 0                 150                360                660                900
Seconds:         0.0s              5.0s               12.0s              22.0s              30.0s
                ├─────────────────┼──────────────────┼──────────────────┼──────────────────┤
Track V2 (B-roll):[Shot 1: Excel]  │                  │                  │                  │
Track V1 (Demo):  │                 [Shot 2: WhatsApp] [Shot 3: Bot Sync] [Shot 4: Ledger]   │
Track A1 (Speech):[=================== 58-Word Voiceover Narration Track (0dB) ==============]
Track A2 (Music): [============= Background Music (bg-music.mp3 ducked to -18dB) ============]
Track TXT (Subs): [Cue 1: Hook    ]│[Cue 2: Problem   ]│[Cue 3: Solution  ]│[Cue 4: CTA       ]│
                ├─────────────────┼──────────────────┼──────────────────┼──────────────────┤
```

### Track Details:
| Track ID | Track Name | Type | Order | Volume / Level | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `track_v1_demo` | Main Product Video | Video | 0 | 0.0 (Muted) | Authentic Android 16 TellOS screen recording |
| `track_v2_broll` | B-roll Overlay | Video | 1 | 0.0 (Muted) | Pixabay licensed overhead Excel spreadsheet review |
| `track_a1_narration` | Voiceover Narration | Audio | 2 | 1.0 (0dB) | 58-word conversational narration (26.85s spoken) |
| `track_a2_bgm` | Background Music | Audio | 3 | 0.125 (-18dB) | Instrumental backing track ducked under dialogue |
| `track_txt_captions` | Native Subtitles | Text | 4 | N/A | Typographic sans-serif subtitles with dark stroke |

---

## 3. Video Cuts & Pacing Breakdown

| Shot Beat | Target Track | Interval `[start, end)` | Duration | Source In/Out | Content & Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Shot 1: Excel Pain Hook** | `track_v2_broll` | `[0, 150)` | 150 f (5.0s) | `[0, 150)` | Overhead view of chaotic spreadsheet with unpaid tags |
| **Shot 2: WhatsApp Intake** | `track_v1_demo` | `[150, 360)` | 210 f (7.0s) | `[150, 360)` | Real mobile view of incoming tenant UPI receipt screenshot |
| **Shot 3: Bot OCR & Sync** | `track_v1_demo` | `[360, 660)` | 300 f (10.0s) | `[420, 720)` | TellOS bot auto-replies with receipt & triggers live sheet row |
| **Shot 4: Clean Ledger CTA** | `track_v1_demo` | `[660, 900)` | 240 f (8.0s) | `[720, 960)` | 50-bed green PAID dashboard & final action prompt |

- **Sum of Video Frames:** 150 + 210 + 300 + 240 = **900 frames** (30.00 seconds).
- **Contiguity Verification:** 0 gaps, 0 overlaps across timeline.

---

## 4. Audio Treatment & Level Calibration

- **Speech Intelligibility:** Narration is placed on `track_a1_narration` at volume 1.0 (unity gain / 0dB target), spanning frames `[0, 900)`.
- **Music Ducking:** `bg-music.mp3` is placed on `track_a2_bgm` at volume 0.125 (-18dB attenuation) to guarantee the non-technical audience clearly hears every word of the case study.
- **Source Audio Handling:** Screen recording audio on `track_v1_demo` and stock video on `track_v2_broll` are muted (volume 0.0) to eliminate ambient hiss or digital noise.

---

## 5. Native Typographic Captions (No SVGs)

4 caption cues are placed on `track_txt_captions`:
1. **Cue 1 `[0, 150)`:** *"Managing 50 PG tenants and still tracking rent in Excel?"*
2. **Cue 2 `[150, 360)`:** *"Every month you chase WhatsApp screenshots, match UPI numbers, and waste hours updating spreadsheets."*
3. **Cue 3 `[360, 660)`:** *"With TellOS, the tenant sends the screenshot on WhatsApp. The bot reads the receipt, sends an instant confirmation, and updates your ledger automatically."*
4. **Cue 4 `[660, 900)`:** *"Zero manual typing. Zero missed rent. Automate your PG on WhatsApp today."*

**Style Attributes:** System Sans-Serif, 48pt, White (`#FFFFFF`) with 4px black drop shadow / outline, placed in bottom third mobile safe zone (above platform UI buttons).

---

## 6. Atomic CutList Operations Summary

Total operations: **15 atomic operations**
- **5 `ADD_TRACK` operations:** `op_add_track_v1_demo`, `op_add_track_v2_broll`, `op_add_track_a1_narration`, `op_add_track_a2_bgm`, `op_add_track_txt_captions`
- **6 `INSERT_CLIP` operations:**
  - `op_ins_shot_01_hook_spreadsheet`
  - `op_ins_shot_02_tenant_receipt`
  - `op_ins_shot_03_tellos_bot_sync`
  - `op_ins_shot_04_clean_ledger_cta`
  - `op_ins_a1_narration`
  - `op_ins_a2_bgm`
- **4 `ADD_CAPTION` operations:**
  - `op_cap_cue1_hook`
  - `op_cap_cue2_problem`
  - `op_cap_cue3_solution`
  - `op_cap_cue4_cta`

All operations include deterministic `idempotency_key` parameters ensuring safe retry without timeline pollution.

---

## 7. Phase 6 Deliverable Artifacts

1. [short-13-edit-plan.md](file:///C:/Users/hirth/hirthick-professional/video-editor/hirthicks-vision-studio/reports/short-13-edit-plan.md)
2. [short-13-cutlist.json](file:///C:/Users/hirth/hirthick-professional/video-editor/hirthicks-vision-studio/reports/short-13-cutlist.json)
3. [test_phase6_edit_planning.py](file:///C:/Users/hirth/hirthick-professional/video-editor/hirthicks-vision-studio/tests/test_phase6_edit_planning.py)

---

## 8. Exit Gate Verification

- [x] Frame-accurate EditPlan constructed from approved script, transcript, footage, and stock.
- [x] Contiguity, trims, cut points, B-roll, captions, and audio treatment verified.
- [x] Strictly 0% synthetic AI clips, 0% diffusion images, and 0 vector SVG cards.
- [x] Source ranges, timeline ranges, media compatibility, and 900-frame duration validated.
- [x] Atomic CutList serialized with operation IDs and unique idempotency keys.
- [x] Rough-cut approval gate verified in SQLite repository (`ApprovalService`).

**Conclusion:** Phase 6 is COMPLETE and APPROVED. Ready for Phase 7 ChatCut Timeline Assembly.

