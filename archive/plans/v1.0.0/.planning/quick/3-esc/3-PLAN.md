---
phase: quick
plan: 3
type: execute
wave: 1
depends_on: []
files_modified:
  - config/workflows/guild_donation.yaml
autonomous: true
requirements:
  - QUICK-03
must_haves:
  truths:
    - Character donation status is recorded to cache after completion
    - Guild UI is closed by pressing ESC
    - Guild UI disappearance is verified with 100ms polling and 500ms timeout
    - If UI still detected after timeout, ESC is pressed again
    - Workflow completes when UI is confirmed closed
  artifacts:
    - path: config/workflows/guild_donation.yaml
      provides: Updated workflow with post-donation completion steps
      min_lines: 220
  key_links:
    - from: donation_complete step
      to: write_donation_cache step
      via: next link
    - from: wait_guild_ui_close step
      to: final_esc_press step
      via: on_true conditional branch
    - from: wait_guild_ui_close step
      to: workflow_complete step
      via: on_false conditional branch
---

<objective>
Add post-donation completion workflow to guild_donation.yaml that records donation status and ensures clean exit from guild UI.

Purpose: After completing the guild donation, we need to record which character completed the donation (using visual hash) and ensure the guild menu is properly closed before proceeding to the next character.

Output: Updated guild_donation.yaml with new steps for cache writing, ESC press, and UI disappearance verification.
</objective>

<execution_context>
@C:/Users/Akane/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Akane/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@config/workflows/guild_donation.yaml
@core/workflow_schema.py

## Current Workflow State

The guild_donation.yaml workflow ends at `donation_complete` step (line 175-179) with `next: null`. The workflow needs to be extended with post-completion steps.

## Available Action Types (from workflow_schema.py)

- `click`: Click at (x, y) coordinates
- `press`: Press key or key combination (e.g., 'esc', 'alt+u')
- `wait`: Fixed duration wait (duration_ms)
- `wait_image`: Intelligent wait for image appear/disappear with timeout
- `scroll`: Scroll up/down with ticks
- `click_detected`: Click at detected image position with safe-area randomization

## Conditional Branching Pattern

From existing workflow (check_sec_donation step, lines 109-119):
```yaml
- step_id: check_sec_donation
  action:
    type: wait
    duration_ms: 100
  on_true: click_sec_donation1
  on_false: no_support_today
  condition:
    type: image
    template: assets/guild_sec_donation1.bmp
    roi: [1551, 606, 1693, 635]
    threshold: 0.8
```

## wait_image Action Pattern

From wait_menu_appear step (lines 38-52):
```yaml
- step_id: wait_menu_appear
  action:
    type: wait_image
    state: appear
    image: guild_ui.bmp
    roi: [546, 803, 903, 835]
    timeout_ms: 5000
    poll_interval_ms: 100
```

## ROI Reference

Guild UI detection ROI: [546, 803, 903, 835] (from wait_menu_appear step)
Same ROI should be used for UI disappearance check.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update donation_complete step to link to new cache step</name>
  <files>config/workflows/guild_donation.yaml</files>
  <action>
Modify the `donation_complete` step (lines 175-179) to change `next: null` to `next: write_donation_cache`.

Current:
```yaml
  # Step 6: Donation complete
  - step_id: donation_complete
    action:
      type: wait
      duration_ms: 100
    next: null
```

Change to:
```yaml
  # Step 6: Donation complete
  - step_id: donation_complete
    action:
      type: wait
      duration_ms: 100
    next: write_donation_cache
```

This connects the existing donation completion to the new post-donation workflow.
  </action>
  <verify>
    <automated>grep -A 5 "step_id: donation_complete" config/workflows/guild_donation.yaml | grep "next: write_donation_cache"</automated>
  </verify>
  <done>donation_complete step now links to write_donation_cache instead of ending workflow</done>
</task>

<task type="auto">
  <name>Task 2: Add write_donation_cache placeholder step</name>
  <files>config/workflows/guild_donation.yaml</files>
  <action>
Add a new step after donation_complete to record the donation status. Since there's no existing action type for writing to cache, use a `wait` action as a placeholder that can be implemented later.

Insert after the donation_complete step:
```yaml
  # Step 6a: Write character donation status to cache
  # Placeholder: Records character ID (visual hash) and donation completion
  # TODO: Implement custom action type 'write_cache' in workflow_runtime.py
  - step_id: write_donation_cache
    action:
      type: wait
      duration_ms: 50
    next: press_esc_close
```

This step serves as a marker for future implementation of cache writing functionality. The visual hash would come from the character slot screenshot taken during account detection phase.
  </action>
  <verify>
    <automated>grep -A 7 "step_id: write_donation_cache" config/workflows/guild_donation.yaml | grep "next: press_esc_close"</automated>
  </verify>
  <done>write_donation_cache step added with placeholder action and link to ESC press step</done>
</task>

<task type="auto">
  <name>Task 3: Add press_esc_close step</name>
  <files>config/workflows/guild_donation.yaml</files>
  <action>
Add a step to press ESC to close the guild menu.

Insert after write_donation_cache step:
```yaml
  # Step 6b: Press ESC to close guild menu
  - step_id: press_esc_close
    action:
      type: press
      key_name: esc
    next: wait_guild_ui_close
```

This sends the ESC keypress to initiate closing of the guild UI.
  </action>
  <verify>
    <automated>grep -A 5 "step_id: press_esc_close" config/workflows/guild_donation.yaml | grep "key_name: esc"</automated>
  </verify>
  <done>press_esc_close step added with ESC keypress action</done>
</task>

<task type="auto">
  <name>Task 4: Add wait_guild_ui_close step with conditional branching</name>
  <files>config/workflows/guild_donation.yaml</files>
  <action>
Add a step that waits for guild_ui.bmp to disappear with 100ms polling and 500ms timeout. Use conditional branching to handle both cases (still detected vs not detected).

Insert after press_esc_close step:
```yaml
  # Step 6c: Wait for guild UI to close
  # Polls every 100ms with 500ms timeout
  # If still detected after timeout, press ESC again
  # If not detected, workflow completes successfully
  - step_id: wait_guild_ui_close
    action:
      type: wait_image
      state: disappear
      image: guild_ui.bmp
      roi: [546, 803, 903, 835]
      timeout_ms: 500
      poll_interval_ms: 100
    on_true: final_esc_press
    on_false: workflow_complete
```

Note: For wait_image with state: disappear, the condition logic is:
- If image disappears within timeout -> on_false (condition not met, image gone)
- If timeout reached and image still present -> on_true (condition met, still there)

Wait, this is confusing. Let me reconsider based on the pattern from check_sec_donation which uses a separate condition block.

Actually, looking at the workflow_schema.py, the condition field is separate from the action. For wait_image, we should use the action result for routing. But the schema shows on_true/on_false are for condition field.

Let me check the existing pattern more carefully. The check_sec_donation uses:
- action: wait (just a delay)
- condition: image detection
- on_true/on_false for branching

For wait_guild_ui_close, we need similar structure but with wait_image action. However, wait_image doesn't directly support on_true/on_false in the schema.

Looking at the schema again, the WorkflowStep has:
- action: ActionConfig
- next: Optional[str] for simple routing
- on_true/on_false: Optional[str] for conditional routing
- condition: Optional[dict] for condition config

So we need a condition block for branching. But wait_image already does detection internally.

Alternative approach: Use the existing pattern but add a condition that checks for guild_ui.bmp after the wait:

```yaml
  # Step 6c: Wait for guild UI to close
  - step_id: wait_guild_ui_close
    action:
      type: wait_image
      state: disappear
      image: guild_ui.bmp
      roi: [546, 803, 903, 835]
      timeout_ms: 500
      poll_interval_ms: 100
    next: check_ui_closed
```

Then add a check step:
```yaml
  # Step 6d: Check if guild UI is still visible
  - step_id: check_ui_closed
    action:
      type: wait
      duration_ms: 50
    on_true: final_esc_press
    on_false: workflow_complete
    condition:
      type: image
      template: guild_ui.bmp
      roi: [546, 803, 903, 835]
      threshold: 0.8
```

This is cleaner and follows the established pattern in the workflow.
  </action>
  <verify>
    <automated>grep -A 10 "step_id: wait_guild_ui_close" config/workflows/guild_donation.yaml | grep "state: disappear"</automated>
  </verify>
  <done>wait_guild_ui_close step added with disappear state and proper timeout/poll settings</done>
</task>

<task type="auto">
  <name>Task 5: Add check_ui_closed conditional step</name>
  <files>config/workflows/guild_donation.yaml</files>
  <action>
Add a conditional check step to determine if guild UI is still visible after the wait.

Insert after wait_guild_ui_close step:
```yaml
  # Step 6d: Check if guild UI is still visible after ESC
  # If still detected (true), press ESC again
  # If not detected (false), workflow completes
  - step_id: check_ui_closed
    action:
      type: wait
      duration_ms: 50
    on_true: final_esc_press
    on_false: workflow_complete
    condition:
      type: image
      template: guild_ui.bmp
      roi: [546, 803, 903, 835]
      threshold: 0.8
```

This follows the exact pattern used in check_sec_donation and check_first_confirm steps.
  </action>
  <verify>
    <automated>grep -A 10 "step_id: check_ui_closed" config/workflows/guild_donation.yaml | grep "on_true: final_esc_press"</automated>
  </verify>
  <done>check_ui_closed conditional step added with proper branching logic</done>
</task>

<task type="auto">
  <name>Task 6: Add final_esc_press step for retry</name>
  <files>config/workflows/guild_donation.yaml</files>
  <action>
Add a step to press ESC again if the UI is still detected after the first attempt.

Insert after check_ui_closed step:
```yaml
  # Step 6e: Final ESC press if UI still visible
  - step_id: final_esc_press
    action:
      type: press
      key_name: esc
    next: workflow_complete
```

This handles the case where the first ESC press didn't close the UI, giving it one more attempt before completing.
  </action>
  <verify>
    <automated>grep -A 5 "step_id: final_esc_press" config/workflows/guild_donation.yaml | grep "key_name: esc"</automated>
  </verify>
  <done>final_esc_press step added with ESC keypress and link to workflow_complete</done>
</task>

<task type="auto">
  <name>Task 7: Update workflow_complete step comment</name>
  <files>config/workflows/guild_donation.yaml</files>
  <action>
Update the comment for the workflow_complete step to reflect it's now the actual completion point.

Current (lines 181-186):
```yaml
  # Step 7: Workflow complete (fallback)
  - step_id: workflow_complete
    action:
      type: wait
      duration_ms: 100
    next: null
```

Change to:
```yaml
  # Step 7: Workflow complete
  # Final step after guild UI is confirmed closed
  - step_id: workflow_complete
    action:
      type: wait
      duration_ms: 100
    next: null
```

This clarifies that workflow_complete is now actively used as the final step, not just a fallback.
  </action>
  <verify>
    <automated>grep -B 1 "step_id: workflow_complete" config/workflows/guild_donation.yaml | grep "Final step after guild UI is confirmed closed"</automated>
  </verify>
  <done>workflow_complete step comment updated to reflect its role as the actual completion point</done>
</task>

<task type="auto">
  <name>Task 8: Validate workflow YAML structure</name>
  <files>config/workflows/guild_donation.yaml</files>
  <action>
Validate the updated workflow file to ensure:
1. All step_ids are unique
2. All next/on_true/on_false references point to existing steps
3. YAML syntax is valid
4. All required fields are present

Run the workflow compiler validation:
```python
python -c "
from core.workflow_compiler import WorkflowCompiler
from core.workflow_schema import WorkflowConfig
import yaml

with open('config/workflows/guild_donation.yaml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

# Validate with Pydantic
config = WorkflowConfig(**data)
print(f'Workflow validated: {config.name}')
print(f'Total steps: {len(config.steps)}')

# Check all step IDs are unique
step_ids = [s.step_id for s in config.steps]
print(f'Step IDs: {step_ids}')

# Verify routing
for step in config.steps:
    if step.next and step.next not in step_ids:
        print(f'ERROR: {step.step_id} references unknown next: {step.next}')
    if step.on_true and step.on_true not in step_ids:
        print(f'ERROR: {step.step_id} references unknown on_true: {step.on_true}')
    if step.on_false and step.on_false not in step_ids:
        print(f'ERROR: {step.step_id} references unknown on_false: {step.on_false}')

print('Validation complete!')
"
```

If validation fails, fix any issues before marking complete.
  </action>
  <verify>
    <automated>python -c "from core.workflow_schema import WorkflowConfig; import yaml; data = yaml.safe_load(open('config/workflows/guild_donation.yaml')); config = WorkflowConfig(**data); print(f'Valid: {len(config.steps)} steps')"</automated>
  </verify>
  <done>Workflow YAML passes schema validation with all steps properly linked</done>
</task>

</tasks>

<verification>
1. donation_complete step links to write_donation_cache
2. write_donation_cache step exists with placeholder action
3. press_esc_close step sends ESC keypress
4. wait_guild_ui_close step waits for guild_ui.bmp to disappear (100ms poll, 500ms timeout)
5. check_ui_closed step branches based on guild_ui.bmp detection
6. final_esc_press step sends second ESC if needed
7. workflow_complete step is the final destination
8. All step IDs are unique and references are valid
9. YAML passes WorkflowConfig schema validation
</verification>

<success_criteria>
- guild_donation.yaml contains 12+ steps (originally 7, plus 5 new)
- Post-donation workflow: donation_complete -> write_donation_cache -> press_esc_close -> wait_guild_ui_close -> check_ui_closed -> [final_esc_press | workflow_complete]
- All new steps have proper Chinese comments explaining purpose
- Workflow validates successfully with WorkflowConfig schema
- No orphaned step references (all next/on_true/on_false point to valid step_ids)
</success_criteria>

<output>
After completion, create `.planning/quick/3-esc/3-SUMMARY.md` documenting:
- Steps added to workflow
- Flow diagram of post-donation completion
- Notes about placeholder cache action for future implementation
</output>
