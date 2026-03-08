---
phase: quick
plan: 5
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/test1_account_indexing_step0.py
autonomous: true
requirements:
  - TEST-01
must_haves:
  truths:
    - "Test script can execute Step0 workflow (ESC -> wait -> capture -> hash)"
    - "All screenshots are saved to tests/output/test1/ directory"
    - "Cache is automatically cleaned on next run"
    - "Visual hash comparison works for account matching"
  artifacts:
    - path: "tests/test1_account_indexing_step0.py"
      provides: "Test script for Step0 logic tree"
      min_lines: 150
    - path: "tests/output/test1/"
      provides: "Screenshot output directory"
  key_links:
    - from: "test1_account_indexing_step0.py"
      to: "core/perceptual_hash.py"
      via: "import compute_phash, compare_phash"
    - from: "test1_account_indexing_step0.py"
      to: "core/workflow_runtime.py"
      via: "CaptureROI action simulation"
    - from: "test1_account_indexing_step0.py"
      to: "modules/character_detector.py"
      via: "find_account_by_perceptual_hash"
---

<objective>
创建account_indexing Step0的测试脚本test1，截屏输出图片并自动清理缓存

Purpose: 验证Step0逻辑树（ESC菜单 -> 等待 -> 账号tag捕获 -> 视觉哈希对比/创建账号）的正确性
Output: tests/test1_account_indexing_step0.py 测试脚本
</objective>

<execution_context>
@C:/Users/Akane/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Akane/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@C:/Users/Akane/FerrumProject/LostarkGuildDonationBot/core/perceptual_hash.py
@C:/Users/Akane/FerrumProject/LostarkGuildDonationBot/core/workflow_runtime.py
@C:/Users/Akane/FerrumProject/LostarkGuildDonationBot/modules/character_detector.py
@C:/Users/Akane/FerrumProject/LostarkGuildDonationBot/config/workflows/account_indexing.yaml
@C:/Users/Akane/FerrumProject/LostarkGuildDonationBot/tests/test_index.py

## Key Interfaces

From core/perceptual_hash.py:
- `compute_phash(image_source)` - Compute perceptual hash from image path or numpy array
- `compare_phash(hash1, hash2)` - Compare two hashes, return hamming distance
- `compute_phash_from_roi(screenshot, roi)` - Compute hash directly from screenshot ROI
- `find_similar_account(db_path, screenshot, roi, threshold)` - Find best matching account

From core/workflow_runtime.py:
- `CaptureROIAction` - Action type with roi, output_key, save_path fields
- `_dispatch_capture_roi()` - Extracts ROI and saves to file

From modules/character_detector.py:
- `ACCOUNT_TAG_ROI = (666, 793, 772, 902)` - Account tag region
- `find_account_by_perceptual_hash()` - Find account by pHash comparison

From config/workflows/account_indexing.yaml:
- Step0: open_esc_menu (press esc) -> wait_after_esc (200ms) -> capture_account_tag (capture_roi)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create test1_account_indexing_step0.py test script</name>
  <files>tests/test1_account_indexing_step0.py</files>
  <action>
Create a comprehensive test script at tests/test1_account_indexing_step0.py that:

1. **Output Directory Management**:
   - Define OUTPUT_DIR = "tests/output/test1/"
   - Create clean_output_dir() function that:
     - Checks if OUTPUT_DIR exists
     - If exists, deletes all .png files in the directory
     - If not exists, creates the directory recursively
   - Call clean_output_dir() at script startup

2. **Step0 Logic Tree Implementation**:
   Implement test_step0_logic_tree() function that simulates the workflow:
   - Step 0: Simulate ESC menu open (print message, optional: capture full screenshot)
   - Step 1: Wait 200ms (time.sleep(0.2))
   - Step 2: Capture account tag ROI (666, 793, 772, 902):
     - Use dxcam to capture screen
     - Extract ROI region
     - Save to tests/output/test1/step2_account_tag.png
     - Compute perceptual hash using compute_phash_from_roi()
   - Step 3: Match or create account:
     - Try to find similar account using find_similar_account() from core/perceptual_hash
     - If found: print match info (account_id, hamming_distance)
     - If not found: print "New account detected"

3. **Screenshot Saving**:
   - Save full screenshot at each step to tests/output/test1/step{N}_{description}.png
   - Steps to save:
     - step0_full_screen.png (after ESC press)
     - step2_account_tag.png (ROI extraction)
     - step3_comparison.png (if comparing with existing accounts)

4. **Test Functions**:
   - test_capture_roi(): Test ROI extraction and saving
   - test_perceptual_hash(): Test hash computation consistency
   - test_account_matching(): Test account matching with mock data
   - run_step0_workflow(): Full integration test

5. **Main Entry Point**:
   - if __name__ == '__main__':
     - Parse arguments: --auto (run automated tests), --manual (run with live screen)
     - Default to --auto mode with mock screenshots
     - In --manual mode: use dxcam for live screen capture

6. **Chinese Output**:
   - Use Chinese print messages with [测试] [信息] [错误] [完成] prefixes
   - Include Windows console encoding fix at top of file

Include proper imports, error handling, and follow the test structure from tests/test_index.py.
  </action>
  <verify>
    <automated>python -c "import sys; sys.path.insert(0, '.'); from tests.test1_account_indexing_step0 import test_capture_roi; test_capture_roi()"</automated>
  </verify>
  <done>
    - tests/test1_account_indexing_step0.py exists with 200+ lines
    - Script includes clean_output_dir() function
    - Script implements all 4 Step0 workflow steps
    - Screenshots are saved to tests/output/test1/ directory
    - All functions have proper Chinese output messages
  </done>
</task>

</tasks>

<verification>
1. Run `python tests/test1_account_indexing_step0.py --auto` - should pass all automated tests
2. Check that tests/output/test1/ directory is created and contains test images
3. Run script again - should clean previous images before creating new ones
4. Verify perceptual hash functions are called correctly
</verification>

<success_criteria>
- Test script exists at tests/test1_account_indexing_step0.py
- Script can run in both --auto (mock) and --manual (live screen) modes
- All screenshots saved to tests/output/test1/ with descriptive names
- Cache cleaning works (old images deleted on new run)
- Visual hash comparison functions are tested
- Chinese output messages are used throughout
</success_criteria>

<output>
After completion, create `.planning/quick/5-account-indexing-step0-test1/5-SUMMARY.md`
</output>
