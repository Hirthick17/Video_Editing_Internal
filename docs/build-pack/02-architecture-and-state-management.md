# 02 — Architecture and Graph-Based State Management

## 1. Core architecture

Use the Antigravity SDK as the agent/tool execution integration specified by the project. Use ChatCut MCP as the editor tool interface. Add a durable graph-based workflow orchestrator around them.

**Important:** “Graph-based state management” is an architectural requirement. Do not assume that the Antigravity SDK itself provides LangGraph semantics. Select and document a compatible graph orchestration implementation during Phase 1. LangGraph may be evaluated as an option, but do not add it automatically or run two competing orchestrators.

Recommended logical layers:

1. **Workflow graph / orchestrator** — owns task routing, dependencies, retries, conditional branches, approval pauses, and resume.
2. **Typed workflow state** — one canonical, validated state object for the current production job.
3. **Agent nodes** — research, script, shot planning, footage analysis, edit planning, editing, critique, publishing preparation.
4. **Deterministic services** — file scanning, media metadata, transcription, frame/time conversion, validation, FFmpeg inspection, scoring arithmetic, checksums.
5. **ChatCut adapter** — wraps MCP calls and normalizes tool responses.
6. **Editor-state synchronizer** — reads ChatCut project/timeline state and reconciles it with the workflow's expected state.
7. **Persistence/checkpoint layer** — SQLite for job state and event log in the first milestone; media files remain in managed asset storage.
8. **Human approval interface** — initially  web UI 

## 2. Do not make the workflow a linear script

The workflow must be a directed graph with conditional routing and resumable state, not a fixed sequence of “agent 1 then agent 2 then agent 3”.

Examples:
- Research and project asset inventory can run in parallel after project selection.
- Script writing waits for sufficient research/context, but can be sent back to research if a factual claim is unsupported.
- Shot planning can run after a draft script and can trigger a script revision if a shot is impossible to record.
- Footage ingest and metadata extraction can run in parallel for independent files.
- Transcription and visual media inspection can run in parallel.
- Edit planning waits for approved script plus available footage/transcript.
- If footage is missing, route to a `MISSING_ASSETS` state and ask the owner for additional footage or approve a stock substitute.
- Editing can only start after the rough-cut plan is approved.
- Critique can branch into audio, pacing, readability, factual accuracy, and brand checks. Independent checks may run in parallel.
- A failed check routes only the relevant correction task back to planning/editing, not necessarily to the beginning.
- Final export waits for all blocking checks and owner approval.
- Publishing metadata can be drafted in parallel with final review, but cannot be treated as published.

## 3. Canonical workflow state

Use a typed schema (Pydantic or equivalent). Minimum fields:

```python
class ProductionState:
    job_id: str
    project_id: str
    workflow_version: str
    graph_version: str
    status: str
    current_node: str | None

    project_context: dict
    research: dict
    script: dict
    shot_plan: dict
    assets: list[dict]
    transcript: dict | None
    edit_plan: dict | None

    editor_snapshot: dict | None
    expected_editor_revision: str | None
    last_observed_editor_revision: str | None
    pending_editor_operations: list[dict]
    applied_editor_operations: list[dict]

    critique_reports: list[dict]
    approval_records: list[dict]
    export_record: dict | None
    publishing_package: dict | None

    retry_counts: dict
    warnings: list[str]
    blockers: list[str]
    event_sequence: int
    created_at: str
    updated_at: str
```

Use explicit typed models for important nested objects rather than leaving production data as arbitrary dictionaries in the final implementation. The sketch above is illustrative.

## 4. Separate three kinds of state

### A. Workflow state
What the production system believes is happening:
- current node and status;
- approved script version;
- assets and their review status;
- edit-plan version;
- pending approval;
- retry count;
- next eligible graph nodes.

### B. Editor state
What actually exists inside ChatCut:
- project and timeline IDs;
- timeline dimensions, frame rate and duration;
- tracks and track order;
- clip/item IDs;
- source asset IDs and source paths/URIs;
- timeline start/end frames;
- source in/out frames;
- mute/volume/transform/crop/scale properties where supported;
- text/caption/title elements where supported and approved;
- transitions and effects where supported;
- selected timeline and editor revision/snapshot;
- save/export status.

### C. Asset state
What media exists and whether it can be used:
- original source path and immutable checksum;
- managed copy/reference;
- media type, codec, duration, dimensions, frame rate;
- transcript/metadata;
- source/license and approval;
- used/unused status;
- missing/offline status.

Never treat these three state domains as interchangeable.

## 5. Graph node design

Suggested nodes (names can change if documented):

- `START`
- `LOAD_PROJECT`
- `PARALLEL_RESEARCH`
- `SCAN_PROJECT_ASSETS`
- `BUILD_PROJECT_BRIEF`
- `DRAFT_SCRIPT`
- `VERIFY_SCRIPT_CLAIMS`
- `OWNER_APPROVES_SCRIPT`
- `BUILD_SHOT_PLAN`
- `WAIT_FOR_OWNER_FOOTAGE`
- `INGEST_ASSETS`
- `TRANSCRIBE_MEDIA`
- `INSPECT_MEDIA`
- `BUILD_EDIT_PLAN`
- `OWNER_APPROVES_ROUGH_CUT`
- `SYNC_EDITOR_STATE`
- `CHECK_EDIT_CONFLICT`
- `APPLY_EDIT_BATCH`
- `VERIFY_EDIT_RESULT`
- `PARALLEL_CRITIQUE`
- `PLAN_TARGETED_FIXES`
- `OWNER_APPROVES_FIXES`
- `APPLY_APPROVED_FIXES`
- `FINAL_EDITOR_SYNC`
- `OWNER_APPROVES_EXPORT`
- `EXPORT_VIDEO`
- `VALIDATE_EXPORT`
- `BUILD_PUBLISHING_PACKAGE`
- `RETROSPECTIVE`
- `PAUSED_FOR_OWNER`
- `BLOCKED`
- `FAILED`
- `DONE`

Conditional edges must use explicit state predicates. Example: `if missing_required_assets -> WAIT_FOR_OWNER_FOOTAGE`; `if script_claims_unverified -> DRAFT_SCRIPT`; `if edit_conflict -> PAUSED_FOR_OWNER`; `if blocking_critique_issues -> PLAN_TARGETED_FIXES`.

## 6. Graph execution rules

- Nodes must declare required input fields and the state fields they are allowed to update.
- Nodes should return typed state updates/events, not mutate arbitrary global state.
- Use immutable/versioned artifacts for script, shot plan, edit plan, critique and export.
- Persist state after every completed node and before/after every external side effect.
- Use a durable event log so a job can resume after process restart.
- Use idempotency keys for side-effecting ChatCut operations. If a tool call times out, inspect editor state before retrying; do not blindly repeat an operation.
- Bound retries per node and per external tool. After the configured limit, pause and request owner intervention.
- Support pause/resume at any owner approval gate.
- Keep a maximum of two critique/correction rounds unless the owner explicitly changes the limit.
- Parallel nodes must write to separate state namespaces or return mergeable updates. Define conflict resolution; never let two nodes overwrite the same state field without a reducer/merge rule.
- Record model, prompt/version, tool, inputs/outputs, duration, retry count and error for each node/tool invocation.
- Do not let an LLM invent tool success. Verify important editor operations by reading ChatCut state after the operation.

## 7. Checkpoint and recovery

Checkpoint at:
- job start;
- after project/asset scan;
- after script approval;
- after shot/asset approval;
- before any ChatCut write batch;
- after each verified ChatCut write batch;
- before export;
- after export validation.

Checkpoint contents:
- workflow state and graph version;
- artifact version IDs and checksums;
- editor project/timeline identifiers;
- last observed editor revision/snapshot where available;
- pending operation list and completed operation IDs;
- event sequence number.

Restoration must distinguish:
1. restoring the workflow database state;
2. restoring/reopening the actual ChatCut timeline state.

A workflow checkpoint alone does not roll back ChatCut. Verify whether ChatCut supports native undo, snapshots, duplicate project, save-as, or timeline restore. If no safe rollback exists, create a project duplicate or snapshot before editing. Never claim rollback is supported until tested.

## 8. LangChain / LangGraph decision

The user requested LangChain-like state management. Interpret this as **graph orchestration with shared typed state, conditional edges, checkpointing, and human-in-the-loop interrupts**.

During Phase 1, evaluate whether LangGraph is the best fit for this graph. If selected:
- use it as the single workflow graph orchestrator;
- use Antigravity SDK for the specified agent/tool execution integration;
- use ChatCut MCP for editor operations;
- do not create a second orchestration loop inside every agent;
- document how graph checkpointing and external ChatCut state reconciliation work together.

If another graph engine is selected, it must meet the same requirements and the decision must be documented. Do not use a simple linear chain as a substitute.

## 9. Architecture boundary

The first milestone can run locally with ChatCut Desktop. Keep the workflow backend, contracts, persistence, and ChatCut adapter separable so cloud deployment can be evaluated later. A headless cloud editor is not assumed. Cloud deployment must be a separate capability test.
