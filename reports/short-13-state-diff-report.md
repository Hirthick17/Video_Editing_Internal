# Short #13 ChatCut Assembly & State-Diff Report
**Hirthick’s Vision Studio | Safe MCP Timeline Verification**

**Audit Timestamp:** 2026-11-13T07:11:13.309936+00:00
**Target Project:** `8a894b86-d5e0-4222-ab88-df22a8e2168e`
**Target Timeline:** `03501b27-ebf5-4aae-9eb6-6e7df21e0378`
**Pre-Edit Revision:** `e3b0c44298fc1c14`
**Post-Edit Revision:** `d5c8e0c64c6dbd3b`
**Rollback Checkpoint ID:** `dup_8a894b86-d5e0-4222-ab88-df22a8e2168e`
**Assembly Status:** VERIFIED & SYNCHRONIZED

---

## 1. Observed Track & Timeline Structure

- **Observed Dimensions:** 1080×1920 @ 30.0 FPS
- **Observed Duration:** 900 frames (30.00 seconds)
- **Observed Tracks:** 9

| Track ID | Track Name | Type | Items Count | Status |
| :--- | :--- | :--- | :--- | :--- |
| `V1` | Main Demo | VIDEO | 0 | **VERIFIED** |
| `V2` | B-roll Stock | VIDEO | 0 | **VERIFIED** |
| `A1` | Voiceover | AUDIO | 0 | **VERIFIED** |
| `A2` | BGM | AUDIO | 0 | **VERIFIED** |
| `track_v1_demo` | Main Product Video (TellOS) | VIDEO | 3 | **VERIFIED** |
| `track_v2_broll` | B-roll Overlay (Excel Pain) | VIDEO | 1 | **VERIFIED** |
| `track_a1_narration` | Voiceover Narration (0dB) | AUDIO | 1 | **VERIFIED** |
| `track_a2_bgm` | Background Music (-18dB) | AUDIO | 1 | **VERIFIED** |
| `track_txt_captions` | Native Text Subtitles | TEXT | 4 | **VERIFIED** |

---

## 2. Placed Timeline Items Audit

| Item ID | Track ID | Asset ID | Interval `[start, end)` | Volume | Name / Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `item_shot_02_tenant_receipt` | `track_v1_demo` | `ast_demo_recording_01` | `[150, 360)` | 0.00 | Clip: shot_02_tenant_receipt |
| `item_shot_03_bot_processing_ledger` | `track_v1_demo` | `ast_demo_recording_01` | `[360, 660)` | 0.00 | Clip: shot_03_bot_processing_ledger |
| `item_shot_04_dashboard_cta` | `track_v1_demo` | `ast_demo_recording_01` | `[660, 900)` | 0.00 | Clip: shot_04_dashboard_cta |
| `item_shot_01_hook_spreadsheet` | `track_v2_broll` | `ast_broll_spreadsheet_01` | `[0, 150)` | 0.00 | Clip: shot_01_hook_spreadsheet |
| `item_a1_narration` | `track_a1_narration` | `ast_voiceover_short13` | `[0, 900)` | 1.00 | Voiceover Narration (58 Words) |
| `item_a2_bgm` | `track_a2_bgm` | `ast_bg_music_01` | `[0, 900)` | 0.12 | Background Music (Ducked -18dB) |
| `cap_cue1_hook` | `track_txt_captions` | `text` | `[0, 150)` | 0.00 | Managing 50 PG tenants and still tracking rent in Excel? |
| `cap_cue2_problem` | `track_txt_captions` | `text` | `[150, 360)` | 0.00 | Every month you chase WhatsApp screenshots, match UPI numbers, and waste hours updating spreadsheets. |
| `cap_cue3_solution` | `track_txt_captions` | `text` | `[360, 660)` | 0.00 | With TellOS, the tenant sends the screenshot on WhatsApp. The bot reads the receipt, sends an instant confirmation, and updates your ledger automatically. |
| `cap_cue4_cta` | `track_txt_captions` | `text` | `[660, 900)` | 0.00 | Zero manual typing. Zero missed rent. Automate your PG on WhatsApp today. |

---

## 3. State Diff & Safety Invariants

- [x] Assembled 9 tracks: ['V1', 'V2', 'A1', 'A2', 'track_v1_demo', 'track_v2_broll', 'track_a1_narration', 'track_a2_bgm', 'track_txt_captions']
- [x] Placed 6 media clips and 4 typographic caption cues.
- [x] Timeline duration: 900 frames (30.0s @ 30 FPS).
- [x] Revision hash changed: e3b0c44298fc1c14 -> d5c8e0c64c6dbd3b
- [x] Pre-edit rollback snapshot created: 'dup_8a894b86-d5e0-4222-ab88-df22a8e2168e'.
- [x] Strict guardrail check: 0 SVG cards detected, 0 synthetic diffusion assets.
