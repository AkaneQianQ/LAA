# Quick Task 9: 为 guild_donation 生成 test.py

**Goal:** 创建一个完整的测试脚本，使用现有 API 测试 guild_donation 流程，不重复造轮子。

**Date:** 2026-03-09

---

## Task 1: 创建 tests/test_guild_donation.py 测试文件

**Files:**
- `tests/test_guild_donation.py` (new)

**Action:**
创建一个 pytest 测试文件，使用现有 API 测试 guild_donation 模块：

1. **导入现有 API:**
   - `from agent.py_service.main import initialize, load_pipeline, get_task_config, load_interface_config`
   - `from agent.py_service.pkg.vision.engine import VisionEngine`
   - `from agent.py_service.modules.donation.register import GuildMenuOpen, OpenGuildMenu, CloseGuildMenu, ExecuteDonation`

2. **测试函数:**
   - `test_pipeline_json_valid()` - 验证 guild_donation.json 格式正确
   - `test_task_config_exists()` - 验证 GuildDonation 任务配置存在
   - `test_donation_actions_registered()` - 验证捐赠动作已注册
   - `test_donation_recognitions_registered()` - 验证捐赠识别器已注册
   - `test_initialization_test_mode()` - 测试测试模式初始化（不连接硬件）

3. **遵循 CLAUDE.md 规范:**
   - 使用标准文件头（含 UTF-8 编码声明）
   - 使用 ASCII 括号日志格式 `[OK]`, `[ERROR]`
   - 使用 snake_case 命名
   - 不重复造轮子，调用现有 API

**Verify:**
- 文件存在于 `tests/test_guild_donation.py`
- 所有测试函数使用 pytest 框架
- 导入使用现有 API 而非重写逻辑

**Done:**
- `tests/test_guild_donation.py` 创建完成，包含 5+ 测试用例
- 使用现有 API：main.initialize, main.load_pipeline, donation.register 组件

---

## Task 2: 更新 STATE.md 记录

**Files:**
- `.planning/STATE.md`

**Action:**
更新 Quick Tasks Completed 表格，添加任务 9 的记录。

**Verify:**
- STATE.md 包含新的 quick task 记录

**Done:**
- STATE.md 已更新
