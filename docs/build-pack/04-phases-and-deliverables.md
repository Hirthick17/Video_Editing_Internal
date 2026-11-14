# 04 — Phases and Deliverables

Phases are gates, not a rigid linear runtime sequence. Build and validate them in this order, but the production graph must route between tasks non-linearly according to state and dependencies.

## Phase 0 — Reconcile and verify the existing integration

**Goal:** Avoid repeating completed work and identify what remains unproven.

Tasks:
- Read this build pack and the 12 November execution log.
- Inspect the actual ChatCut MCP catalogue and schemas.
- Verify the 80-tool claim from the running integration.
- Verify project/timeline read, asset import, stock search, timeline edit, and preview operations against actual tool responses.
- Record the exact CLI startup/configuration and dependency versions.
- Inspect the existing Short #13 project and identify the generated SVG items from the mistaken run.
- Do not delete or overwrite existing work; preserve it as a test artifact.
- Verify whether the current project has been saved and whether a real export exists.

Deliverable: `reports/phase-0-verification.md` with verified / unverified / failed status for each capability.

Exit gate: owner approves the integration report.

## Phase 1 — Backend foundation and graph state

**Goal:** Build the durable orchestration core before adding a large number of agents.

Tasks:
- Create repository structure and environment configuration.
- Define typed contracts for `ProductionState`, `EditorProject`, `EditorTimeline`, `EditorTrack`, `EditorItem`, `AssetRecord`, `Script`, `ShotPlan`, `EditPlan`, `EditOperation`, `ApprovalRecord`, `CritiqueReport`, and `ExportRecord`.
- Choose one graph orchestrator. Evaluate LangGraph against requirements; document the decision. Antigravity SDK remains the agent/tool integration specified by the project.
- Implement graph nodes, conditional edges, parallel branches, reducers/merge rules, interrupt/resume, bounded retries, and failure routing.
- Implement SQLite persistence, event log, versioned artifacts, and checkpoints.
- Add idempotency keys and tool-call audit logs.
- Add tests for restart/resume and graph branch routing.

Deliverable: runnable graph backend with a toy workflow and durable state; no production editing yet.

Exit gate: state survives process restart; graph can pause/resume; conditional branch and parallel merge tests pass.

## Phase 2 — ChatCut adapter and editor-state management

**Goal:** Make editor state explicit and safe.

Tasks:
- Build a typed ChatCut MCP adapter using only discovered tool schemas.
- Implement project/timeline/track/item inspection.
- Normalize ChatCut responses into editor-state contracts.
- Implement editor-state snapshots and revision/conflict detection.
- Implement edit operation validation and idempotency.
- Determine safe rollback strategy: native snapshot/restore, duplicate project, or another verified method.
- Implement read-before-write, write-batch, read-after-write verification.
- Add an editor lock/handoff protocol to prevent owner/agent simultaneous edits.
- Test a harmless edit in a duplicated/test project, verify it, then recover the prior state.

Deliverable: safe editor adapter plus verified state synchronization and recovery report.

Exit gate: a controlled edit is applied once, verified, and safely restored or reverted using a demonstrated method.

## Phase 3 — Project registry and asset inventory

**Goal:** Ingest one project without changing source files.

Tasks:
- Select one project folder (Short #13 candidate, if approved).
- Scan read-only and compute file checksums/metadata.
- Classify real user footage, screen recordings, audio, documents, and existing approved stock.
- Exclude unapproved generated SVG/video/image assets from the active asset pool.
- Record stock source/license/approval status.
- Create a project brief and asset manifest.
- Detect missing/offline media.

Deliverable: approved `ProjectRecord` and asset manifest.

Exit gate: owner confirms the selected project and asset inventory.

## Phase 4 — Research, script, and shot planning

**Goal:** Produce a factual, recordable Short.

Tasks:
- Research the problem and product context; save source URLs and evidence.
- Draft a short script for a non-technical business audience.
- Verify every factual claim; remove unsupported claims.
- Generate a practical shot list using real product recordings, phone footage, and screen recordings.
- Check shot feasibility against the actual script and available environment.
- Allow script and shot planning to loop when a shot is impractical.
- Ask owner to approve script and shot list.

Deliverable: approved script, source list, shot plan, and recording checklist.

Exit gate: owner approves the script and shot plan.

## Phase 5 — Footage intake, transcription, and media understanding

**Goal:** Understand real footage before editing.

Tasks:
- Wait for owner footage when required.
- Ingest copies/references into managed asset storage; never modify originals.
- Extract media metadata and thumbnails/previews where supported.
- Transcribe speech with word/segment timestamps when available.
- Inspect footage for scene changes, relevant screen content, framing, clarity, and usable segments.
- Match candidate clips to script beats.
- Report missing shots and request re-recording or owner-approved stock alternatives.
- Run transcription and visual inspection in parallel when dependencies allow.

Deliverable: footage inventory, transcript, clip/shot match report, and missing-footage report.

Exit gate: sufficient approved footage exists for an edit plan.

## Phase 6 — Edit planning and rough-cut approval

**Goal:** Convert creative intent into a deterministic edit plan.

Tasks:
- Build a frame-accurate EditPlan from approved script, transcript, footage, and stock.
- Plan pacing, trims, cut points, B-roll, captions, and audio treatment.
- Use only real user footage and approved stock.
- Do not create generated video, SVG, image, illustration, or motion-graphic assets.
- Validate source ranges, timeline ranges, media compatibility, and duration.
- Present a human-readable rough-cut plan and preview where available.
- Obtain owner approval before any substantial timeline write.

Deliverable: versioned EditPlan / CutList with operation IDs and approval record.

Exit gate: owner approves the rough cut.

## Phase 7 — ChatCut assembly and editor-state verification

**Goal:** Apply the approved edit plan safely.

Tasks:
- Read current ChatCut state and detect edit conflicts.
- Checkpoint/duplicate project using the verified recovery method.
- Apply bounded operation batches through MCP.
- Verify each batch by re-reading editor state.
- Add approved stock footage to appropriate tracks.
- Apply approved native captions/titles and transitions only where supported and consistent with brand rules.
- Preserve original audio and speech clarity; adjust levels only under approved rules.
- Verify timeline duration, track structure, clip positions, asset availability, and absence of unapproved generated assets.
- Pause if the editor differs unexpectedly from the workflow's expected state.

Deliverable: editable ChatCut timeline matching the approved EditPlan, plus state-diff report.

Exit gate: owner reviews and approves the assembled timeline.

## Phase 8 — Critique graph and targeted correction loop

**Goal:** Improve the edit without restarting the entire pipeline.

Independent critique branches may run in parallel:
- story clarity and business value;
- clip relevance and pacing;
- text/caption readability;
- audio quality;
- factual accuracy;
- brand consistency;
- timeline integrity and asset provenance.

Tasks:
- Produce issue-level critique with timestamps and severity.
- Route only relevant issues to targeted correction nodes.
- Require owner approval for meaningful creative changes.
- Apply approved fixes and re-run only affected checks.
- Maximum two correction rounds, then escalate.

Deliverable: critique reports, approved correction list, and final quality report.

Exit gate: blocking issues cleared and owner approves final review.

## Phase 9 — Export and publishing package

**Goal:** Produce a validated MP4 and publishing materials.

Tasks:
- Confirm final editor state and approved revision.
- Obtain explicit export approval.
- Export locally through verified ChatCut capability or a documented fallback.
- Validate file existence, decode, dimensions, frame rate, duration, audio, and checksum.
- Draft title options, description, hashtags, pinned comment, and publishing checklist.
- Prepare calendar entry as a draft only if calendar integration is configured and approved.
- Do not upload or publish automatically.

Deliverable: final MP4, export validation report, publishing package, and optional calendar draft.

Exit gate: owner accepts the export and publishing package.

## Phase 10 — Retrospective and controlled scaling

**Goal:** Learn from one complete production before scaling.

Record:
- total elapsed time;
- owner time required;
- model/tool cost and token usage if available;
- number of MCP operations;
- retries, failures, and recovery events;
- number of manual interventions;
- edit defects and rework;
- quality review outcome;
- lessons and changes to the graph.

Only after owner approval may the system be expanded to another project. Do not batch-process all 21 projects automatically.
