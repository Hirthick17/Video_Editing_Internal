# Short #13 Footage Intake & Media Inventory Report
**Hirthick’s Vision Studio | TellOS PG Automation Case Study**

**Report Generated:** 2026-11-13T06:51:29.911263+00:00
**Production Guardrail:** Strictly 100% Authentic Product & Licensed Stock Footage. Zero AI/SVG assets.

---

## 1. Physical Source Media Inventory

| Asset ID | File Name | Type | Resolution | Duration | FPS | Audio Info | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ast_demo_recording_01` | `demo-recording-1.mp4` | SCREEN_RECORDING | 1080x2400 | 59.02s | 30.00 | aac (1ch, 48000Hz) | **APPROVED** |
| `ast_broll_spreadsheet_01` | `broll-spreadsheet.mp4` | STOCK_BROLL | 960x540 | 20.40s | 30.00 | Silent / None | **APPROVED** |
| `ast_bg_music_01` | `bg-music.mp3` | AUDIO_BGM | N/A | 96.03s | 30.00 | mp3 (2ch, 44100Hz) | **APPROVED** |
| `ast_quarantined_card1_hook` | `card1_hook.svg` | PROHIBITED_SYNTHETIC | N/A | 0.00s | 25.00 | Silent / None | **QUARANTINED** |
| `ast_quarantined_card2_solution` | `card2_solution.svg` | PROHIBITED_SYNTHETIC | N/A | 0.00s | 25.00 | Silent / None | **QUARANTINED** |
| `ast_quarantined_card3_insight` | `card3_insight.svg` | PROHIBITED_SYNTHETIC | N/A | 0.00s | 25.00 | Silent / None | **QUARANTINED** |
| `ast_quarantined_card4_cta` | `card4_cta.svg` | PROHIBITED_SYNTHETIC | N/A | 0.00s | 25.00 | Silent / None | **QUARANTINED** |
| `ast_missing_footage_sample` | `non_existent_footage.mp4` | DOCUMENT | N/A | N/A | N/A | Silent / None | **REJECTED** |

---

## 2. Detected Usable Footage Segments

| Segment ID | Source Asset | Time Range | Frames | Framing | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ast_demo_recording_01_seg_whatsapp_intake` | `ast_demo_recording_01` | `5.0s – 12.0s` | `[150, 360)` | portrait_mobile | Incoming tenant chat with UPI transaction screenshot and friction point |
| `ast_demo_recording_01_seg_bot_ocr_and_sync` | `ast_demo_recording_01` | `14.0s – 24.0s` | `[420, 720)` | portrait_mobile | TellOS bot verifies receipt amount and syncs live Google Sheets ledger |
| `ast_demo_recording_01_seg_ledger_summary_paid` | `ast_demo_recording_01` | `24.0s – 32.0s` | `[720, 960)` | portrait_mobile | Complete 50-tenant ledger showing green verified status badges |
| `ast_broll_spreadsheet_01_seg_excel_frustration` | `ast_broll_spreadsheet_01` | `0.0s – 5.0s` | `[0, 150)` | landscape_desktop | Overhead camera reviewing complex financial spreadsheet report |

---

## 3. Media Verification Summary

- **TellOS Demo Recording (`demo-recording-1.mp4`):** Authentic Android 16 mobile capture (1080x2400). Contains full WhatsApp transaction lifecycle from incoming screenshot to bot confirmation and ledger sync.
- **Excel B-roll (`broll-spreadsheet.mp4`):** 1080p-scaled financial spreadsheet analysis footage under Pixabay commercial license.
- **Background Music (`bg-music.mp3`):** 96.0s ambient instrumental track at 44.1kHz stereo, ready for ducking to -18dB under speech.
- **Quarantine Enforcement:** 4 SVG card files in `shorts-assets/` remain quarantined; excluded from editor timeline.
