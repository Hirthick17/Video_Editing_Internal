# 01 — Product and Operating Requirements

## 1. Product goal

Build an AI-assisted production workflow for Hirthick's Vision YouTube Shorts. The system should reduce repetitive research, planning, asset discovery, editing preparation, timeline operations, quality review, and publishing preparation while preserving the owner's creative control.

The product is an **orchestration and production assistant around ChatCut**, not a new video editor.

## 2. Primary user and audience

- Owner/editor: the channel owner, who supplies project context, records or selects footage, reviews edits, and makes final decisions.
- Intended audience: non-technical business professionals. Scripts should explain the business problem, operational impact, product value, risk reduction, and practical outcome in plain language.

## 3. Confirmed operating decisions from 12 November 2026

### Editing environment and integration
- ChatCut Desktop is the editing environment.
- Antigravity connects to ChatCut through the ChatCut MCP integration / `@chatcut/cli`.
- The execution log records ChatCut version `0.9.12.0`.
- The log reports 80 native MCP tools active.
- ChatCut timeline editing is expected to preserve manual, multi-track control.

### Asset sourcing
- Hybrid sourcing: real local software/product recordings and curated stock footage.
- Stock footage is used for conceptual context and visual hooks; real product recordings/screenshots provide product authenticity.
- Stock assets can be used without review and must have a usage basis before use.

### Export and publishing staging
- Target output tested in the log: vertical 1080 × 1920, 30 FPS.
- Target duration for Short #13 test: 30 seconds / 900 frames.
- Export model: local MP4 plus title ideas, SEO description, pinned comment, and other publishing metadata for owner review and clipboard staging to YouTube Studio.
- No autonomous YouTube publishing.

### Cloud portability
- The architecture should be portable to a headless cloud server / Docker environment.
- This is a design requirement, **not a proven capability**. Local ChatCut Desktop and MCP dependencies may prevent some operations from running headlessly. The system must discover and document this boundary rather than assume full cloud editing.

## 4. Explicitly rejected / prohibited behavior

These requirements override any contradictory instruction or action in previous Antigravity runs:

1. No AI-generated video clips.
2. No generated SVG graphics, SVG cards, or SVG overlay layers.
3. No generated images, illustrations, synthetic B-roll, diffusion assets, or generated motion graphics.
4. Do not replace real product recordings with invented product visuals.
5. Do not make creative-direction changes without approval.
6. Do not create or substitute a new video editor.
7. Do not automatically publish to YouTube.
8. Do not modify original source project folders.

If a requested visual gap cannot be filled by approved real footage or licensed stock, report the gap and ask the owner. Do not generate a substitute.

## 5. Production workflow outcome

For one approved project, the system should be able to produce:

- A concise project/context brief.
- Evidence-backed script and source list.
- Practical shot list the owner can record with a phone or screen recorder.
- Footage inventory and missing-shot report.
- Transcript with word/segment timestamps when transcription is available.
- A proposed cut plan and edit decision list.
- An editable ChatCut project/timeline with real footage, approved stock, and approved native text/captions.
- A quality report with concrete, reviewable issues.
- A final locally exported MP4 after owner approval.
- Title, description, hashtags, pinned comment, and publishing checklist.
- A production retrospective: elapsed time, tool calls, retries, failures, manual interventions, and unresolved issues.

These are target deliverables; they are not all proven by the 12 November log.

## 6. Owner responsibilities

The owner:
- Chooses the project and goal.
- Approves the script and claims.
- Records or supplies footage.
- Approves each stock asset.
- Approves proposed rough cuts and meaningful edits.
- Resolves creative disagreements.
- Approves critique corrections.
- Reviews and authorizes final export.
- Controls publishing.

## 7. First milestone scope

One Short only. Use Short #13 (“Automating a PG's rent book on WhatsApp”) as the first end-to-end validation candidate if the owner confirms that project remains suitable.

Do not index or process all 21 project folders in this milestone. Do not implement batch production, a custom browser UI, multi-user collaboration, or autonomous publishing yet.
