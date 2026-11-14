# Short #13 Multi-Track Edit Plan & Rough-Cut Specification
**Hirthick’s Vision Studio | YouTube Shorts Production System**

**Plan Generated:** 2026-11-13T06:55:43.848239+00:00
**Timeline Dimensions:** 1080×1920 (9:16 Vertical) @ 30 FPS
**Total Timeline Duration:** Exactly 900 Integer Frames (30.00 Seconds)
**Validation Status:** VALIDATED & APPROVED

---

## 1. Track Architecture

| Track ID | Track Name | Media Type | Order | Primary Content & Mix Level |
| :--- | :--- | :--- | :--- | :--- |
| `track_v1_demo` | Main Product Video (TellOS) | VIDEO | 0 | N/A (Visual) |
| `track_v2_broll` | B-roll Overlay (Excel Pain) | VIDEO | 1 | N/A (Visual) |
| `track_a1_narration` | Voiceover Narration (0dB) | AUDIO | 2 | 0dB (Dialogue) |
| `track_a2_bgm` | Background Music (-18dB) | AUDIO | 3 | -18dB (Ducked) |
| `track_txt_captions` | Native Text Subtitles | TEXT | 4 | N/A (Visual) |

---

## 2. Multi-Track Timeline Diagram

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

---

## 3. Atomic Operations CutList

| Op ID | Type | Track | Frame Range | Source Range | Content / Parameters |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `op_add_track_v1_demo` | `ADD_TRACK` | `track_v1_demo` | `[0, 900)` | N/A | Add track Main Product Video (TellOS) |
| `op_add_track_v2_broll` | `ADD_TRACK` | `track_v2_broll` | `[0, 900)` | N/A | Add track B-roll Overlay (Excel Pain) |
| `op_add_track_a1_narration` | `ADD_TRACK` | `track_a1_narration` | `[0, 900)` | N/A | Add track Voiceover Narration (0dB) |
| `op_add_track_a2_bgm` | `ADD_TRACK` | `track_a2_bgm` | `[0, 900)` | N/A | Add track Background Music (-18dB) |
| `op_add_track_txt_captions` | `ADD_TRACK` | `track_txt_captions` | `[0, 900)` | N/A | Add track Native Text Subtitles |
| `op_ins_shot_01_hook_spreadsheet` | `INSERT_CLIP` | `track_v2_broll` | `[0, 150)` | `[0, 150)` | Clip: shot_01_hook_spreadsheet (vol: 0.0) |
| `op_ins_shot_02_tenant_receipt` | `INSERT_CLIP` | `track_v1_demo` | `[150, 360)` | `[150, 360)` | Clip: shot_02_tenant_receipt (vol: 0.0) |
| `op_ins_shot_03_bot_processing_ledger` | `INSERT_CLIP` | `track_v1_demo` | `[360, 660)` | `[420, 720)` | Clip: shot_03_bot_processing_ledger (vol: 0.0) |
| `op_ins_shot_04_dashboard_cta` | `INSERT_CLIP` | `track_v1_demo` | `[660, 900)` | `[720, 960)` | Clip: shot_04_dashboard_cta (vol: 0.0) |
| `op_ins_a1_narration` | `INSERT_CLIP` | `track_a1_narration` | `[0, 900)` | `[0, 900)` | Voiceover Narration (58 Words) (vol: 1.0) |
| `op_ins_a2_bgm` | `INSERT_CLIP` | `track_a2_bgm` | `[0, 900)` | `[0, 900)` | Background Music (Ducked -18dB) (vol: 0.125) |
| `op_cap_cue1_hook` | `ADD_CAPTION` | `track_txt_captions` | `[0, 150)` | N/A | "Managing 50 PG tenants and still tracking rent in Excel?" |
| `op_cap_cue2_problem` | `ADD_CAPTION` | `track_txt_captions` | `[150, 360)` | N/A | "Every month you chase WhatsApp screenshots, match UPI numbers, and waste hours updating spreadsheets." |
| `op_cap_cue3_solution` | `ADD_CAPTION` | `track_txt_captions` | `[360, 660)` | N/A | "With TellOS, the tenant sends the screenshot on WhatsApp. The bot reads the receipt, sends an instant confirmation, and updates your ledger automatically." |
| `op_cap_cue4_cta` | `ADD_CAPTION` | `track_txt_captions` | `[660, 900)` | N/A | "Zero manual typing. Zero missed rent. Automate your PG on WhatsApp today." |

---

## 4. Guardrail & Production Compliance

- **Authentic Video Sourcing:** 100% of video frames originate from `demo-recording-1.mp4` (Android TellOS mobile capture) and `broll-spreadsheet.mp4` (Pixabay commercial license).
- **Strict Zero-Synthetic Rule:** 0% AI-generated diffusion video, 0% synthetic images, and 0 vector SVG cards.
- **Speech-First Audio Architecture:** Voiceover speech at unity gain (0dB); background music ducked at -18dB (volume 0.125) to avoid masking dialogue.
- **Typographic Captions:** Clean native text captions rendered on safe margins without unapproved graphical cards.
