# 07 — Acceptance Tests and Definition of Done

## 1. Phase 0 / integration tests

- [ ] Antigravity can launch/connect to the configured ChatCut MCP server.
- [ ] Actual tool catalogue and schemas are captured.
- [ ] ChatCut version and integration version are recorded.
- [ ] Project/timeline can be read.
- [ ] Asset import can be performed in a test project.
- [ ] Stock search returns candidates with source/provenance information.
- [ ] Timeline edit can be applied to a disposable/duplicated project.
- [ ] Preview operation returns usable evidence.
- [ ] Existing timeline can be inspected after application restart.
- [ ] No generated SVG/video/image assets are added by the workflow.

## 2. Graph and state tests

- [ ] Graph routes conditionally based on typed state.
- [ ] Independent research and asset scan branches can run in parallel.
- [ ] Parallel state updates merge without overwriting unrelated fields.
- [ ] Unsupported/missing data routes to a blocker or owner interrupt.
- [ ] Human approval pauses execution and resumes from the same checkpoint.
- [ ] Process restart restores workflow state and pending work.
- [ ] Node retries are bounded.
- [ ] Tool timeout triggers editor-state inspection before retry.
- [ ] Side-effecting operations are idempotent or reconciled before retry.
- [ ] Critique loop is bounded to two rounds by default.
- [ ] Every state transition and tool call is auditable.

## 3. Editor-state tests

- [ ] Editor project/timeline/track/item state is normalized.
- [ ] Frame ranges use integer half-open intervals.
- [ ] Read-before-write conflict detection works.
- [ ] Concurrent owner/agent editing is prevented.
- [ ] A pre-edit checkpoint/snapshot is created.
- [ ] A controlled edit is applied exactly once.
- [ ] Read-after-write confirms the expected result.
- [ ] A tested recovery method restores the prior editor state.
- [ ] Missing/offline assets are detected.
- [ ] Unexpected timeline items are detected.
- [ ] Generated SVG/video/image assets are rejected or quarantined.

## 4. Export tests

- [ ] Export is blocked without explicit owner approval.
- [ ] MP4 exists and can be decoded.
- [ ] Resolution matches approved settings.
- [ ] Frame rate matches approved settings.
- [ ] Duration matches expected timeline duration within documented tolerance.
- [ ] Audio stream exists and is intelligible.
- [ ] No black/blank/missing sections are present.
- [ ] Export checksum and metadata are recorded.
- [ ] Export is tied to the exact approved timeline revision.

## 5. First end-to-end definition of done

One Short is complete only when:
1. The project and asset inventory are owner-approved.
2. The script and claims are approved.
3. The shot plan and stock selections are approved.
4. The edit plan is approved.
5. ChatCut timeline assembly is verified against the edit plan.
6. Critique checks are completed and blocking issues resolved.
7. Owner approves final timeline and export.
8. MP4 passes deterministic validation and human playback review.
9. Publishing metadata is delivered as a draft.
10. Retrospective records time, cost, failures, retries, and manual interventions.

A successful MCP tool response alone is not sufficient evidence of a completed deliverable.
