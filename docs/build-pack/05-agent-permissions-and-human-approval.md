# 05 — Agent Permissions and Human Approval

## 1. Permission principle

Agents propose and execute only within explicitly granted permissions. The owner retains creative control. Tool access must be enforced in code, not merely described in prompts.

## 2. Suggested roles

### Orchestrator
- Owns graph routing, state validation, checkpointing, pause/resume and retries.
- Does not make unapproved creative decisions.
- Does not bypass approval gates.

### Research node
- Reads project context and approved external sources.
- Produces evidence-backed research.
- Cannot modify ChatCut.

### Script node
- Drafts and revises scripts using verified evidence.
- Cannot modify ChatCut or publish.

### Shot-planning node
- Creates practical shot instructions for real recording.
- Cannot generate visual assets or modify ChatCut.

### Asset/footage node
- Scans and classifies files read-only.
- Searches approved stock sources and records provenance.
- Cannot modify original files or approve its own stock selections.

### Transcription/media-analysis nodes
- Analyze real supplied footage and audio.
- Produce transcript, metadata, and segment descriptions.
- Cannot alter source footage or edit the timeline.

### Edit-planning node
- Produces typed EditPlan / EditOperations.
- Cannot write to ChatCut.

### Editing node
- Sole agent role allowed to invoke ChatCut write operations.
- Must receive an approved EditPlan and a valid editor lock.
- Must checkpoint before writes and verify after writes.
- Cannot create generated video, SVG, image, illustration, or motion-graphic assets.
- Cannot export without explicit owner approval.

### Critic nodes
- Produce timestamped, evidence-based issues.
- Cannot directly edit the timeline.
- Cannot change brand rules.

### Publishing-preparation node
- Drafts title, description, hashtags, pinned comment and calendar details.
- Cannot publish, upload, or schedule externally without a separate explicit authorization.

## 3. Human approval gates

- **G1 — Script:** owner approves script and factual claims.
- **G2 — Shot plan and footage:** owner approves shot list and any stock candidates.
- **G3 — Rough cut:** owner approves EditPlan before ChatCut write operations.
- **G4 — Corrections:** owner approves meaningful critique-driven changes.
- **G5 — Final timeline:** owner approves the final assembled timeline.
- **G6 — Export:** owner explicitly authorizes final export.
- **G7 — Publishing package:** owner approves metadata and any calendar draft.

Approval must be a durable record containing:
- approval ID;
- gate name;
- artifact ID and version/checksum;
- decision (`APPROVED`, `REJECTED`, `CHANGES_REQUESTED`);
- owner identity or session identity;
- timestamp;
- optional comment.

Approval of one artifact version does not approve a later modified version.

## 4. Stop conditions

Immediately pause and ask the owner when:
- the user and agent may be editing the same timeline;
- editor state differs from the expected revision;
- a requested operation is unsupported or ambiguous;
- a stock asset's license/source is unclear;
- a factual claim cannot be verified;
- required footage is missing;
- a proposed creative change materially changes the approved story;
- a generated visual asset appears in the asset pool or timeline;
- recovery cannot be guaranteed;
- retry limits are exhausted.

## 5. Security and operational controls

- Store credentials in environment secrets or a secure secret store, never in source files or logs.
- Use least-privilege tool access.
- Log every MCP call, arguments after secret redaction, result status, duration, and error.
- Do not log sensitive tokens or credentials.
- Restrict filesystem access to approved project roots and managed asset directories.
- Project scanner is read-only.
- Never delete or overwrite original footage.
- Enforce export and publishing approval in backend state transitions.
