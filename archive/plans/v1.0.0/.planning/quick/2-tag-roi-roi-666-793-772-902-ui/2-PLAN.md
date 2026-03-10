# Quick Task 2: 修改账号TAG ROI和截图逻辑

**Date:** 2026-03-08
**Description:** 修改账号TAG ROI为(666,793,772,902)，实现防UI变色逻辑，延迟首角色截图

---

## Task 1: 添加账号TAG ROI常量和鼠标移动支持

**Files:**
- `modules/character_detector.py`
- `core/ferrum_controller.py`
- `core/hardware_input_gateway.py`

**Action:**
1. 在 `character_detector.py` 添加新的常量：
   - `ACCOUNT_TAG_ROI = (666, 793, 772, 902)` - 账号标签识别区域
   - `MOUSE_SAFE_POSITION = (827, 516)` - 防止UI变色的鼠标位置

2. 在 `ferrum_controller.py` 添加绝对鼠标移动方法：
   - `move_absolute(x, y)` - 使用 `win32api.GetCursorPos()` 获取当前位置，计算相对位移，调用 `km.move()`

3. 在 `hardware_input_gateway.py` 暴露鼠标移动方法：
   - `move_mouse(x, y)` - 包装 `ferrum_controller.move_absolute()`

**Verify:**
- 常量定义正确
- 鼠标移动方法可以正确计算相对位移
- 代码通过语法检查

**Done:**
- [ ] ACCOUNT_TAG_ROI 常量已添加
- [ ] MOUSE_SAFE_POSITION 常量已添加
- [ ] move_absolute 方法已实现
- [ ] move_mouse 方法已暴露

---

## Task 2: 重构账号识别逻辑

**Files:**
- `modules/character_detector.py`
- `core/database.py`

**Action:**
1. 修改 `character_detector.py`:
   - 添加 `_move_mouse_to_safe_position()` 方法 - 移动鼠标到安全位置防止UI变色
   - 修改 `create_or_get_account_index()`:
     * 首先调用 `_move_mouse_to_safe_position()`
     * 使用 `ACCOUNT_TAG_ROI` 截取账号标签区域
     * 基于标签区域计算 `account_hash`
     * 对比数据库中已有账号，如果不存在则创建新账号
   - 添加 `_capture_account_tag()` 方法 - 截取账号标签区域
   - 添加 `match_account_tag()` 方法 - 对比截图与库中标签

2. 修改 `database.py`:
   - 在 `accounts` 表添加 `tag_screenshot_path` 字段存储账号标签截图
   - 添加 `update_account_tag()` 函数更新标签截图
   - 添加 `get_account_tag_path()` 函数获取标签路径
   - 修改 `CREATE_ACCOUNTS_TABLE` SQL

3. 账号数据结构：
   ```
   data/accounts/{account_hash}/
     ├── tag.png              # 账号标签ROI截图
     ├── characters/
     │   ├── 0.png           # 角色1截图（延迟获取）
     │   ├── 1.png           # 角色2截图
     │   └── ...
     └── account_info.json   # 包含总角色数量等信息
   ```

**Verify:**
- 账号标签ROI截图正确
- 账号匹配逻辑正确
- 数据库schema更新正确
- 鼠标移动到安全位置后再截图

**Done:**
- [ ] _move_mouse_to_safe_position 方法已实现
- [ ] _capture_account_tag 方法已实现
- [ ] match_account_tag 方法已实现
- [ ] create_or_get_account_index 逻辑已重构
- [ ] 数据库schema已更新

---

## Task 3: 实现延迟首角色截图逻辑

**Files:**
- `modules/character_detector.py`
- `core/account_manager.py`

**Action:**
1. 修改 `character_detector.py`:
   - 添加 `_pending_first_slot_capture` 状态标记
   - 修改 `create_or_get_account_index()`:
     * 首次进入时不截取1-1角色格（slot_index=0）
     * 设置 `_pending_first_slot_capture = True`
     * 记录需要捕获的首角色信息
   - 添加 `capture_first_slot_on_switch()` 方法:
     * 在切换到第二个角色前调用
     * 此时第一个角色已不是当前选中状态，UI不会变色
     * 截取1-1角色格并保存
   - 修改 `cache_character_screenshot()`:
     * 对于非首角色（slot_index > 0），正常截图
     * 首角色截图通过专门的 `capture_first_slot_on_switch()` 处理

2. 修改 `account_manager.py`:
   - 在角色切换流程中集成首角色截图捕获
   - 确保在切换到第二个角色前调用 `capture_first_slot_on_switch()`

**Verify:**
- 首次进入角色选择界面时，1-1角色格不被截图
- 切换到第二角色前，1-1角色格被正确截图
- 所有角色截图最终都被保存
- 鼠标在安全位置

**Done:**
- [ ] _pending_first_slot_capture 状态已添加
- [ ] capture_first_slot_on_switch 方法已实现
- [ ] create_or_get_account_index 已修改跳过首角色截图
- [ ] account_manager 已集成延迟截图逻辑

---

## Task 4: 更新账号库文件结构

**Files:**
- `modules/character_detector.py`

**Action:**
1. 修改 `_ensure_account_directory()`:
   - 创建新的目录结构
   - 保存账号标签截图到 `tag.png`
   - 创建 `account_info.json` 存储总角色数量

2. 添加保存/读取账号信息的方法：
   - `_save_account_info()` - 保存账号元数据
   - `_load_account_info()` - 读取账号元数据

3. 账号信息包含：
   - account_hash
   - total_character_count
   - created_at
   - updated_at

**Verify:**
- 目录结构正确创建
- tag.png 保存到正确位置
- account_info.json 内容正确

**Done:**
- [ ] 目录结构已更新
- [ ] tag.png 保存逻辑已实现
- [ ] account_info.json 读写已实现

---

## Summary

这个quick task实现了：
1. 新的账号TAG ROI (666,793,772,902) 用于账号识别
2. 鼠标移动到安全位置 (827,516) 防止UI变色
3. 首角色截图延迟到切换第二角色时捕获
4. 完整的账号库文件结构
