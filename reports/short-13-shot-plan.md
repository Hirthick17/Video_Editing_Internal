# Short #13 Frame-Accurate Shot Plan
**Hirthick’s Vision Studio | 30.0s Timeline Assembly Specification**

**Timeline Specification:** 1080×1920 (9:16 Vertical) @ 30 FPS  
**Total Timeline Duration:** Exactly 900 Integer Frames  
**Interval Math:** Half-open intervals `[start_frame, end_frame)` where `duration = end_frame - start_frame`  
**Media Sourcing Policy:** 100% Authentic Product Footage + Approved Stock B-roll (Strictly ZERO generated SVG cards / ZERO synthetic diffusion clips)

---

## 1. Frame-by-Frame Shot Sequence

```text
0s (f0)               5s (f150)             12s (f360)            22s (f660)            30s (f900)
├─────────────────────┼─────────────────────┼─────────────────────┼─────────────────────┤
│       Shot 1        │       Shot 2        │       Shot 3        │       Shot 4        │
│  Excel Pain Hook    │ WhatsApp UPI Intake │ Bot OCR & Live Sync │ Clean Ledger & CTA  │
│ [0, 150) | 150 f    │ [150, 360) | 210 f  │ [360, 660) | 300 f  │ [660, 900) | 240 f  │
│ Track V2 (Stock)    │ Track V1 (TellOS)   │ Track V1 (TellOS)   │ Track V1 (TellOS)   │
└─────────────────────┴─────────────────────┴─────────────────────┴─────────────────────┘
```

---

## 2. Shot Details & Asset Mapping

### Shot 1: Opening Hook — The Excel Nightmare
- **Interval:** `[0, 150)` (0.0s – 5.0s)
- **Duration:** 150 frames (5.0s)
- **Primary Track:** `V2` (B-roll Overlay)
- **Asset ID:** `ast_broll_spreadsheet_01` (`broll-spreadsheet.mp4`)
- **Visual Description:** High-angle camera moving over a chaotic spreadsheet with red highlights, unpaid tenant tags, and manual calculation errors.
- **Narration Line:** *"Managing 50 PG tenants and still tracking rent in Excel?"*
- **Audio Mix:** Voiceover on `A1` (0dB normalized) + subtle background music on `A2` (-18dB).

### Shot 2: Problem Escalation — WhatsApp Screenshot Chaos
- **Interval:** `[150, 360)` (5.0s – 12.0s)
- **Duration:** 210 frames (7.0s)
- **Primary Track:** `V1` (Main Product Demo)
- **Asset ID:** `ast_demo_recording_01` (`demo-recording-1.mp4`)
- **Visual Description:** Real mobile screen recording showing incoming tenant chat with UPI transaction screenshot, demonstrating the friction of manual verification.
- **Narration Line:** *"Every month you chase WhatsApp screenshots, match UPI numbers, and waste hours updating spreadsheets."*
- **Audio Mix:** Voiceover on `A1` + soft WhatsApp incoming notification pop.

### Shot 3: Core Solution — TellOS WhatsApp Bot & Instant Ledger Sync
- **Interval:** `[360, 660)` (12.0s – 22.0s)
- **Duration:** 300 frames (10.0s)
- **Primary Track:** `V1` (Main Product Demo)
- **Asset ID:** `ast_demo_recording_01` (`demo-recording-1.mp4`)
- **Visual Description:** TellOS automated bot parsing the UPI screenshot, extracting the ₹12,500 rent amount, returning an instant branded receipt to the tenant, while the corresponding row in the owner's Google Sheet updates automatically.
- **Narration Line:** *"With TellOS, the tenant sends the screenshot on WhatsApp. The bot reads the receipt, sends an instant confirmation, and updates your ledger automatically."*
- **Audio Mix:** Voiceover on `A1` + crisp confirmation chime cue.

### Shot 4: Outro & Call to Action — Clean Ledger Peace of Mind
- **Interval:** `[660, 900)` (22.0s – 30.0s)
- **Duration:** 240 frames (8.0s)
- **Primary Track:** `V1` (Main Product Demo)
- **Asset ID:** `ast_demo_recording_01` (`demo-recording-1.mp4`)
- **Visual Description:** Clean, organized TellOS dashboard showing all green "PAID" status indicators for the 50 beds, fading into closing CTA.
- **Narration Line:** *"Zero manual typing. Zero missed rent. Automate your PG on WhatsApp today."*
- **Audio Mix:** Voiceover on `A1` + music swell on `A2` resolving cleanly at frame 900.

---

## 3. Continuity & Feasibility Verification
- **Total Frames:** 150 + 210 + 300 + 240 = **900 frames** (30.00 seconds).
- **Contiguity:** Half-open intervals align with zero gaps and zero overlaps (`[0, 150) -> [150, 360) -> [360, 660) -> [660, 900)`).
- **Asset Coverage:** 100% of required visual shots are matched to verified online local assets in the active asset pool.
- **Guardrail Compliance:** 0% synthetic assets; zero vector SVG cards.

