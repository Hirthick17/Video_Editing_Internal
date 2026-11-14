# 03 — ChatCut Editor State and MCP Contract

## 1. Purpose

ChatCut is the editing engine. The workflow backend must understand, inspect, plan, modify, and verify ChatCut's project/timeline state without assuming undocumented tool behavior.

The editor state is a first-class domain model, not merely a collection of MCP calls.

## 2. Evidence from 12 November execution log

The log reports:
- ChatCut Desktop `0.9.12.0`, local process PID `7132`.
- Antigravity connected through `@chatcut/cli`.
- 80 native MCP tools reported active.
- `create_project` created project `8a894b86-d5e0-4222-ab88-df22a8e2168e` and timeline `03501b27-ebf5-4aae-9eb6-6e7df21e0378`.
- `push_asset` imported `demo-recording-1.mp4` and `broll-spreadsheet.mp4`.
- `search_stock_media` returned a Pixabay spreadsheet clip.
- `edit_item` was used for multi-track placement.
- `preview_timeline` was used to inspect the result.
- A timeline JSON file was observed on disk.

These are reported execution results, not an independent audit of the tool schemas or resulting rendered video.

## 3. Editor state model

Create typed structures equivalent to:

```python
class EditorProject:
    project_id: str
    name: str
    timeline_ids: list[str]
    active_timeline_id: str | None
    editor_version: str | None

class EditorTimeline:
    timeline_id: str
    project_id: str
    width: int
    height: int
    fps_num: int
    fps_den: int
    duration_frames: int
    tracks: list["EditorTrack"]
    revision: str | None
    saved_at: str | None

class EditorTrack:
    track_id: str
    track_type: str  # video, audio, text, other — map actual ChatCut values
    order: int
    items: list["EditorItem"]

class EditorItem:
    item_id: str
    asset_id: str | None
    item_type: str
    timeline_start_frame: int
    timeline_end_frame: int
    source_in_frame: int | None
    source_out_frame: int | None
    properties: dict
```

Adapt field names to the actual ChatCut MCP responses. Preserve raw tool response snapshots for debugging, but normalize them into stable internal contracts.

## 4. Required editor operations

First inspect the real MCP tool catalogue and schemas. Do not invent tool names or argument shapes.

The adapter should expose normalized methods for capabilities that actually exist:

- list/get projects;
- create/open project;
- get active project/timeline;
- inspect timeline and tracks;
- list/import/register assets;
- search stock media;
- preview timeline;
- add/place item;
- move/trim/split/remove item;
- update supported properties;
- save project;
- duplicate/snapshot/restore or safe rollback if supported;
- export/render;
- inspect export status and metadata.

If an operation is unsupported, mark it `UNSUPPORTED` and route to a human or documented alternative. Do not silently emulate it with a destructive sequence.

## 5. Editor-state synchronization

Before every write batch:

1. Read the current ChatCut project and timeline.
2. Confirm the expected project and timeline IDs.
3. Compare current editor revision/snapshot with the workflow's last observed revision.
4. Detect unexpected user edits or another process editing the same timeline.
5. If there is a conflict, stop and ask the owner; do not overwrite.
6. Validate that every referenced asset exists and is online.
7. Validate frame ranges and track references.
8. Create a checkpoint/snapshot or duplicate project if the verified recovery strategy requires it.
9. Apply a small, bounded batch of operations.
10. Read the timeline again and verify the intended changes.
11. Persist the new editor snapshot/revision in workflow state.

Do not edit while the owner is manually editing the same timeline. Use a lock/lease or explicit owner handoff. The lock must expire safely after a crash, but expiration must not cause an unsafe concurrent write.

## 6. Frame/time rules

- Use integer frames as the canonical timeline unit.
- Store frame rate as a rational number, not only a float.
- Convert seconds to frames in one deterministic utility.
- Use half-open intervals `[start_frame, end_frame)` internally.
- Validate `end_frame > start_frame`.
- Prevent negative frame positions and out-of-range source in/out points.
- Handle source FPS differing from timeline FPS explicitly.
- Do not infer exact frame rate from duration alone.
- Record rounding behavior in tests.

For the Short #13 test, the log states 30 FPS and 900 frames = 30 seconds. Treat this as the intended test configuration, not proof that the final rendered MP4 matches it.

## 7. Edit plan and operation model

Do not send vague prose such as “make it more engaging” directly to editor tools.

Create a typed `EditOperation` / `EditPlan` with:
- operation ID and idempotency key;
- target project/timeline/track;
- source asset ID;
- action and supported parameters;
- timeline start/end frames;
- source in/out frames;
- reason tied to script/shot/critique item;
- approval status;
- precondition and expected postcondition;
- verification method.

Example action types should be limited to actual supported MCP operations. A proposed operation must be validated against the tool catalogue before execution.

## 8. Timeline verification

After each batch, compare observed editor state with expected state:
- expected track exists;
- expected item exists once;
- item points to the expected asset;
- start/end frame values match within defined tolerance;
- source trim is correct;
- no unintended gaps/overlaps where prohibited;
- audio link/track is present when expected;
- timeline duration is expected;
- no missing/offline assets;
- no unexpected generated graphics/video items;
- no unapproved items or properties were introduced.

Use deterministic code for this verification wherever possible.

## 9. Generated asset guardrail

The asset pipeline must reject or quarantine any generated video, image, SVG, illustration, or synthetic motion graphic unless the owner explicitly authorizes a specific exception in a recorded approval.

For this build pack, the default and current approved policy is **NO GENERATED VISUAL ASSETS**.

SVG files created by the mistaken 12 November run must not be treated as approved reusable brand assets. Do not automatically place them in new timelines. Keep them out of the active production asset pool unless the owner explicitly re-approves them.

## 10. Export verification

Export is not complete merely because an export tool returns success. Verify the resulting file:
- exists at the expected path;
- opens and decodes;
- has expected width/height;
- has expected frame rate and duration;
- has expected audio stream;
- has no black/blank or missing sections;
- has acceptable audio levels and speech intelligibility;
- has no unexpected generated visual assets;
- matches the approved timeline version.

Store file size, checksum, media probe output, export settings, and timeline revision in `ExportRecord`.
