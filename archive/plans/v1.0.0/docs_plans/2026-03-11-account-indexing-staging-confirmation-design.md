# Account Indexing Staging Confirmation Design

## Goal

Add a confirmation flow for `AccountIndexing` so the task writes only to a temporary staging area first, then lets the user decide whether to save or discard the result from the Qt launcher config panel.

## Scope

This design only covers the account indexing task and the Qt launcher UI.

User-visible requirements:

- After account indexing finishes, the config panel shows only:
  - total role count as `N+1`
  - a button to open the staged character screenshot directory
  - a `保存` button
  - a `丢弃` button
- No formal database interaction happens until the user presses `保存`
- If the user presses `丢弃`, all staged files for that indexing run are deleted

Out of scope:

- changing `CharacterSwitch`
- showing per-character details in the UI
- preserving staged runs across multiple pending sessions

## Current State

`AccountIndexing` currently writes account tag data, character screenshots, and final account metadata directly into persistent storage during pipeline execution. The Qt launcher starts the task and only receives success/failure status; the config panel has no task-specific widgets yet.

This means the current flow cannot support user confirmation before database persistence.

## Recommended Approach

Use a staging-based two-phase flow.

Phase 1: collect indexing output into a per-run staging directory and emit a compact summary.

Phase 2: if the user presses `保存`, import staged files into the persistent account database and persistent account directory. If the user presses `丢弃`, delete the staging directory and clear the pending summary.

This approach is preferred because it preserves the existing indexing logic shape while moving persistence behind an explicit confirmation step.

## Alternatives Considered

### 1. Direct in-memory result only

Keep all indexing output in memory and persist only after `保存`.

Pros:

- clean persistence boundary

Cons:

- poor fit for screenshot assets
- higher risk if the process exits before user action
- requires larger refactor of existing indexing actions

### 2. Write directly to real database and rollback on discard

Pros:

- smallest initial change

Cons:

- wrong semantics for "save to database only after confirmation"
- rollback is easy to get wrong
- leaves higher risk of partial persistence

## Architecture

### Staging output

Each `AccountIndexing` run creates a unique staging session directory under:

`data/staging/account_indexing/<session_id>/`

Expected contents:

- `summary.json`
- `account_tag.png`
- `characters/*.png`
- optional run metadata needed for import

`summary.json` must include:

- `session_id`
- `account_hash`
- `character_count_switchable`
- `character_count_total`
- `staging_dir`
- `characters_dir`

The UI only consumes `character_count_total` and `characters_dir`, but the bridge/service layer needs the rest for save/discard operations.

### Persistence split

Account indexing runtime must stop writing to:

- `data/accounts.db`
- `data/accounts/<account_hash>/...`

Instead it writes only to staging.

On `保存`, a new bridge/service helper imports the staged account into persistent storage by:

1. loading the staging summary
2. creating or resolving the persistent account row
3. copying staged assets into the persistent account directory
4. upserting all character screenshots into `data/accounts.db`
5. writing final `account_info.json`
6. removing the staging directory after successful commit

On `丢弃`, the bridge/service helper deletes the staging directory without touching persistent storage.

### Qt launcher UI

The config panel gets a task-specific result card for `AccountIndexing`.

States:

- idle: existing placeholder
- pending-confirmation: show staged result controls
- clearing: transient busy/disabled state during save or discard

Displayed fields:

- `本次角色总数：<N+1>`

Buttons:

- `打开角色截图目录`
- `保存`
- `丢弃`

No extra account metadata is shown.

### Bridge integration

`LauncherBridge` needs to surface task-specific completion payloads instead of only a boolean success result.

Recommended additions:

- signal for staged indexing result ready
- `save_account_indexing_staging(session_id)`
- `discard_account_indexing_staging(session_id)`

The main window subscribes to the staged result signal and updates the config panel only for `AccountIndexing`.

## Data Flow

1. User starts `AccountIndexing`
2. Task runs and writes only to staging
3. Task finishes successfully and exposes `summary.json`
4. Bridge loads summary and emits staged result to Qt
5. UI shows total role count `N+1` and action buttons
6. User chooses:
   - `保存`: staged import into persistent DB/storage, then clear UI
   - `丢弃`: delete staging and clear UI

## Error Handling

If staging summary is missing or malformed after a successful run:

- keep task result as failed from the UI perspective
- append a log message
- keep config panel in placeholder state

If `打开角色截图目录` target is missing:

- append a log message
- do not crash the UI

If `保存` fails during import:

- keep the staged result visible
- append a detailed error message
- do not delete staging automatically

If `丢弃` fails:

- keep the staged result visible
- append a detailed error message

Only a fully successful save removes staging and clears the panel.

## Testing Strategy

### Service/module tests

- indexing finalize step writes `summary.json` into staging instead of persistent storage
- save helper imports staged account into persistent DB and file tree
- discard helper removes staging without persistent writes

### Qt tests

- config panel shows placeholder by default
- after staged result signal, panel shows `N+1`, open-folder, save, discard
- save button clears panel on success
- discard button clears panel on success
- save/discard failure leaves panel visible and logs error

## File Areas Expected To Change

- `agent/py_service/modules/account_indexing/register.py`
- `assets/tasks/account_indexing.yaml`
- `assets/resource/pipeline/account_indexing.json`
- `launcher/service.py`
- `gui_qt/adapters/launcher_bridge.py`
- `gui_qt/window.py`
- `tests/test_account_indexing.py`
- `tests/test_gui_launcher.py`

## Acceptance Criteria

- Running `AccountIndexing` no longer writes directly into persistent account storage
- Successful indexing shows only total role count `N+1` and the three requested buttons in the config panel
- Pressing `保存` performs the first persistent DB/file interaction for that run
- Pressing `丢弃` deletes the staged output and leaves persistent storage unchanged
