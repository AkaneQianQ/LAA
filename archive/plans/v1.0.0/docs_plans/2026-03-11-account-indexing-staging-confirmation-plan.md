# Account Indexing Staging Confirmation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a staging-and-confirmation flow for `AccountIndexing` so the Qt launcher shows only total role count `N+1`, an open-folder button, and save/discard actions before any persistent database write occurs.

**Architecture:** Split account indexing into two phases: pipeline collection writes only to a staging session directory, then launcher-triggered save/discard helpers either import staged data into persistent storage or remove it. The Qt config panel renders a small task-specific card driven by bridge signals for staged results.

**Tech Stack:** Python 3.13, PySide6, existing launcher service/bridge layer, workflow YAML/JSON, sqlite-backed account storage

---

### Task 1: Add a failing service-level test for staged indexing summary

**Files:**
- Modify: `tests/test_account_indexing.py`
- Modify: `agent/py_service/modules/account_indexing/register.py`

**Step 1: Write the failing test**

```python
def test_finalize_account_index_writes_staging_summary_only(tmp_path):
    ...
    finalize_account_index({... staging params ...})
    assert summary_path.exists()
    assert not list_all_accounts(str(db_path))
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_account_indexing.py::test_finalize_account_index_writes_staging_summary_only -v`
Expected: FAIL because finalize logic still assumes persistent output or does not write staging summary

**Step 3: Write minimal implementation**

Implement staging-aware finalize behavior in `agent/py_service/modules/account_indexing/register.py`:

- generate `session_id`
- write staged summary JSON
- avoid persistent DB writes during staging mode

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_account_indexing.py::test_finalize_account_index_writes_staging_summary_only -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_account_indexing.py agent/py_service/modules/account_indexing/register.py
git commit -m "feat: stage account indexing output before save"
```

### Task 2: Add failing tests for save/discard staging helpers

**Files:**
- Modify: `tests/test_account_indexing.py`
- Modify: `launcher/service.py`

**Step 1: Write the failing tests**

```python
def test_save_account_indexing_staging_imports_into_persistent_storage(tmp_path):
    ...

def test_discard_account_indexing_staging_removes_staging_without_db_write(tmp_path):
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_account_indexing.py -k "save_account_indexing_staging or discard_account_indexing_staging" -v`
Expected: FAIL because helpers do not exist

**Step 3: Write minimal implementation**

In `launcher/service.py` add helpers that:

- load staged summary
- on save: create/resolve account, copy files, upsert character rows, write final account info, delete staging
- on discard: delete staging directory only

Reuse existing database APIs from `API_REFERENCE.md` instead of creating parallel persistence utilities.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_account_indexing.py -k "save_account_indexing_staging or discard_account_indexing_staging" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_account_indexing.py launcher/service.py
git commit -m "feat: add save and discard helpers for staged account indexing"
```

### Task 3: Add a failing Qt test for pending staged result UI

**Files:**
- Modify: `tests/test_gui_launcher.py`
- Modify: `gui_qt/window.py`
- Modify: `gui_qt/adapters/launcher_bridge.py`

**Step 1: Write the failing test**

```python
def test_qt_launcher_shows_account_indexing_pending_result_controls(qtbot):
    ...
    assert "本次角色总数：8" == window.account_indexing_count_label.text()
    assert window.account_indexing_open_button.isVisible()
    assert window.account_indexing_save_button.isVisible()
    assert window.account_indexing_discard_button.isVisible()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gui_launcher.py::test_qt_launcher_shows_account_indexing_pending_result_controls -v`
Expected: FAIL because the config panel still shows only the placeholder

**Step 3: Write minimal implementation**

Add:

- a staged-result signal in `gui_qt/adapters/launcher_bridge.py`
- pending result card widgets in `gui_qt/window.py`
- render logic that swaps placeholder vs account indexing result card

Only show total `N+1`, open-folder, save, discard.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gui_launcher.py::test_qt_launcher_shows_account_indexing_pending_result_controls -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_gui_launcher.py gui_qt/window.py gui_qt/adapters/launcher_bridge.py
git commit -m "feat: show staged account indexing confirmation controls in qt launcher"
```

### Task 4: Add failing Qt interaction tests for save and discard actions

**Files:**
- Modify: `tests/test_gui_launcher.py`
- Modify: `gui_qt/window.py`
- Modify: `gui_qt/adapters/launcher_bridge.py`

**Step 1: Write the failing tests**

```python
def test_qt_launcher_save_account_indexing_staging_clears_pending_panel(qtbot):
    ...

def test_qt_launcher_discard_account_indexing_staging_clears_pending_panel(qtbot):
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_gui_launcher.py -k "save_account_indexing_staging_clears_pending_panel or discard_account_indexing_staging_clears_pending_panel" -v`
Expected: FAIL because button actions are not wired

**Step 3: Write minimal implementation**

Wire button handlers so they:

- call the new bridge save/discard methods
- clear the pending UI on success
- keep UI visible on failure
- append error logs when failures occur

Also add open-folder wiring using the staged `characters_dir`.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_gui_launcher.py -k "save_account_indexing_staging_clears_pending_panel or discard_account_indexing_staging_clears_pending_panel" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_gui_launcher.py gui_qt/window.py gui_qt/adapters/launcher_bridge.py
git commit -m "feat: wire staged account indexing save and discard actions"
```

### Task 5: Thread staged result through launcher task completion

**Files:**
- Modify: `launcher/service.py`
- Modify: `gui_qt/adapters/launcher_bridge.py`
- Modify: `tests/test_gui_launcher.py`

**Step 1: Write the failing test**

```python
def test_qt_bridge_emits_staged_result_after_account_indexing_success(...):
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_gui_launcher.py::test_qt_bridge_emits_staged_result_after_account_indexing_success -v`
Expected: FAIL because bridge completion still emits only boolean success

**Step 3: Write minimal implementation**

Update task execution path so account indexing success can surface staged summary data to the bridge:

- extend launcher service task result contract
- keep non-account-indexing tasks on current success/failure path
- emit staged result only for successful account indexing runs

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_gui_launcher.py::test_qt_bridge_emits_staged_result_after_account_indexing_success -v`
Expected: PASS

**Step 5: Commit**

```bash
git add launcher/service.py gui_qt/adapters/launcher_bridge.py tests/test_gui_launcher.py
git commit -m "feat: emit staged account indexing result through launcher bridge"
```

### Task 6: Verify the full targeted test set

**Files:**
- Test: `tests/test_account_indexing.py`
- Test: `tests/test_gui_launcher.py`

**Step 1: Run account indexing tests**

Run: `pytest tests/test_account_indexing.py -v`
Expected: PASS

**Step 2: Run launcher tests covering the new UI flow**

Run: `pytest tests/test_gui_launcher.py -k "account_indexing or staged" -v`
Expected: PASS

**Step 3: Run any required pipeline regeneration step**

Run: `python tools/convert_yaml_to_pipeline.py assets/tasks/account_indexing.yaml`
Expected: regenerated `assets/resource/pipeline/account_indexing.json`

**Step 4: Re-run the narrow regression checks**

Run: `pytest tests/test_account_indexing.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add assets/tasks/account_indexing.yaml assets/resource/pipeline/account_indexing.json
git commit -m "test: verify staged account indexing confirmation flow"
```
