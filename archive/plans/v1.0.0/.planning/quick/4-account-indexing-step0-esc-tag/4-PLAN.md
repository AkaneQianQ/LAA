---
phase: quick-4
plan: 4
type: execute
wave: 1
depends_on: []
files_modified:
  - core/perceptual_hash.py
  - core/workflow_schema.py
  - core/workflow_runtime.py
  - core/workflow_executor.py
  - config/workflows/account_indexing.yaml
autonomous: true
requirements:
  - IDX-01
  - IDX-02
must_haves:
  truths:
    - ESC menu opens and 200ms delay is applied
    - Account tag ROI (666,793,772,902) is captured
    - Perceptual hash comparison finds similar accounts (not strict match)
    - New accounts are saved to database
    - Matched accounts return account_id for next step
  artifacts:
    - path: core/perceptual_hash.py
      provides: Perceptual hashing for visual similarity
      exports: [compute_phash, compare_phash, find_similar_account]
    - path: core/workflow_schema.py
      provides: CaptureROI action type
      contains: CaptureROIAction class
    - path: core/workflow_runtime.py
      provides: ROI capture dispatch
      contains: _dispatch_capture_roi method
    - path: config/workflows/account_indexing.yaml
      provides: Step0 workflow definition
      contains: [open_esc_menu, capture_account_tag, match_or_create_account]
  key_links:
    - from: workflow_executor
      to: perceptual_hash
      via: find_similar_account() call
      pattern: "phash.find_similar_account"
    - from: capture_roi action
      to: dxcam screenshot
      via: VisionEngine.capture_roi
      pattern: "vision.capture"
---

<objective>
实现账号索引Step0：ESC菜单打开 + 账号标签视觉哈希对比

Purpose: 在角色选择界面打开ESC菜单，捕获账号标签区域，使用感知哈希(perceptual hashing)与数据库中的账号进行对比，实现零配置的账号识别
Output: 感知哈希模块、CaptureROI工作流动作、更新的账号索引工作流
</objective>

<execution_context>
@C:/Users/Akane/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Akane/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

## Key Code References

From modules/character_detector.py:
```python
# Account tag ROI for account identification (new ROI to prevent UI color change)
ACCOUNT_TAG_ROI: Tuple[int, int, int, int] = (666, 793, 772, 902)

def match_account_tag(self, screenshot: np.ndarray, account_hash: str) -> bool:
    # Currently uses strict SHA-256 - needs perceptual hash upgrade
    current_tag = self._capture_account_tag(screenshot)
    current_hash = self._compute_screenshot_hash(current_tag)
    # ... strict comparison
```

From core/database.py:
```python
def find_account_by_hash(db_path: str, account_hash: str) -> Optional[Dict[str, Any]]:
    # Returns account with tag_screenshot_path

def list_all_accounts(db_path: str) -> List[Dict[str, Any]]:
    # Returns all accounts for perceptual hash comparison
```

From core/workflow_schema.py (existing actions):
```python
ClickAction, WaitAction, PressAction, ScrollAction, WaitImageAction, ClickDetectedAction, MoveAction
# Need to add: CaptureROIAction
```
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create perceptual hash module</name>
  <files>core/perceptual_hash.py</files>
  <action>
Create a new perceptual hashing module for visual similarity comparison.

Implementation requirements:
1. Use imagehash library (pHash - perceptual hash) for robust similarity comparison
2. Implement compute_phash(image_path or numpy array) -> hash string
3. Implement compare_phash(hash1, hash2) -> hamming distance (0-64)
4. Implement find_similar_account(db_path, screenshot, threshold=10) -> (account_id, distance) or None
   - Load all accounts from database
   - Compare perceptual hash of input with stored tag screenshots
   - Return best match if hamming distance <= threshold
5. Add compute_phash_from_roi(screenshot, roi) helper for direct ROI capture

The module should handle:
- PIL Image conversion from numpy arrays (OpenCV BGR format)
- Error handling for missing files or invalid images
- Chinese comments per project convention

Dependencies: imagehash, PIL (Pillow)
  </action>
  <verify>
    <automated>python -c "from core.perceptual_hash import compute_phash, compare_phash, find_similar_account; print('[OK] Perceptual hash module loaded')"</automated>
  </verify>
  <done>
    - Module imports without errors
    - compute_phash returns 64-bit hash string
    - compare_phash returns integer hamming distance
    - find_similar_account signature correct
  </done>
</task>

<task type="auto">
  <name>Task 2: Add CaptureROI action to workflow system</name>
  <files>core/workflow_schema.py, core/workflow_runtime.py, core/workflow_executor.py</files>
  <action>
Add CaptureROI action type to the workflow system.

In core/workflow_schema.py:
1. Add CaptureROIAction class with fields:
   - roi: Tuple[int, int, int, int] (required)
   - output_key: str (required) - key to store captured image in context
   - save_path: Optional[str] - optional path to save screenshot

2. Add to ActionType union and Action discriminated union

In core/workflow_runtime.py:
1. Add _dispatch_capture_roi method to ActionDispatcher:
   - Extract ROI from screenshot using VisionEngine or dxcam
   - Store numpy array in workflow context under output_key
   - Optionally save to save_path if specified
   - Use dxcam for capture, fallback to PIL

2. Add import for CaptureROIAction in dispatch method

In core/workflow_executor.py:
1. Ensure workflow context can store numpy arrays
2. No changes needed if context is Dict[str, Any]
  </action>
  <verify>
    <automated>python -c "from core.workflow_schema import CaptureROIAction; from core.workflow_runtime import ActionDispatcher; print('[OK] CaptureROI action registered')"</automated>
  </verify>
  <done>
    - CaptureROIAction class defined with roi, output_key, save_path fields
    - _dispatch_capture_roi method implemented
    - Action dispatcher handles new action type
  </done>
</task>

<task type="auto">
  <name>Task 3: Update account indexing workflow and integration</name>
  <files>config/workflows/account_indexing.yaml, modules/character_detector.py</files>
  <action>
Update the account indexing workflow to implement Step0 with perceptual hashing.

In config/workflows/account_indexing.yaml:
1. Replace existing workflow with Step0 implementation:
   - step_id: open_esc_menu
     action: press esc
     next: wait_after_esc

   - step_id: wait_after_esc
     action: wait 200ms
     next: capture_account_tag

   - step_id: capture_account_tag
     action: capture_roi
     roi: [666, 793, 772, 902]
     output_key: account_tag_image
     next: match_or_create_account

   - step_id: match_or_create_account
     action: match_account
     image_key: account_tag_image
     threshold: 10  # hamming distance threshold
     on_new: create_new_account
     on_match: account_matched

   - step_id: create_new_account
     action: create_account
     image_key: account_tag_image
     output_key: account_id
     next: workflow_complete

   - step_id: account_matched
     action: set_variable
     account_id: from_match
     next: workflow_complete

2. Update start_step_id to open_esc_menu

In modules/character_detector.py:
1. Add import for perceptual_hash module
2. Add method find_account_by_perceptual_hash(screenshot) -> Optional[Tuple[int, str]]:
   - Capture account tag ROI
   - Call perceptual_hash.find_similar_account()
   - Return (account_id, account_hash) or None
3. Keep existing strict hash methods for backward compatibility
  </action>
  <verify>
    <automated>python -c "import yaml; wf = yaml.safe_load(open('config/workflows/account_indexing.yaml')); print(f"[OK] Workflow loaded: {len(wf.get('steps', []))} steps")"</automated>
  </verify>
  <done>
    - Workflow YAML has 6 steps for Step0 implementation
    - ROI [666, 793, 772, 902] used for capture
    - CharacterDetector has find_account_by_perceptual_hash method
    - Perceptual hash integration complete
  </done>
</task>

</tasks>

<verification>
1. Perceptual hash module can be imported and used
2. Workflow schema accepts CaptureROIAction
3. Action dispatcher handles capture_roi
4. Account indexing workflow has correct Step0 flow
5. CharacterDetector integrates perceptual hash lookup
</verification>

<success_criteria>
- core/perceptual_hash.py exists with pHash implementation
- CaptureROI action works in workflow system
- Account indexing workflow implements Step0 (ESC -> wait -> capture -> match/create)
- Perceptual hash comparison finds similar accounts with threshold <= 10
- New accounts are automatically created when no match found
- Matched accounts return existing account_id
</success_criteria>

<output>
After completion, create `.planning/quick/4-account-indexing-step0-esc-tag/4-SUMMARY.md`
</output>
