---
phase: quick-ferrum
plan: 1
type: quick-task
subsystem: test-framework
tags: [ferrum, hardware, testing, pre-check]
dependency_graph:
  requires: [core/ferrum_controller.py]
  provides: [tests/interactive/hardware_check.py]
  affects: [tests/interactive/test_runner.py, tests/interactive/scenarios.py]
tech_stack:
  added: []
  patterns: [hardware-abstraction, pre-flight-check, graceful-degradation]
key_files:
  created:
    - tests/interactive/hardware_check.py
  modified:
    - tests/interactive/scenarios.py
    - tests/interactive/test_runner.py
decisions:
  - "Hardware check runs automatically in TestRunner.initialize() before scenario selection"
  - "R key hotkey allows retry without restarting the test program"
  - "Chinese error messages follow project [Ferrum]/[错误] prefix conventions"
  - "Mock-based unit tests patch at core.ferrum_controller level"
metrics:
  duration_minutes: 3
  completed_date: "2026-03-08T02:37:00+08:00"
  tasks_completed: 3
  files_created: 1
  files_modified: 2
  tests_added: 11
---

# Quick Task 1-Ferrum: Hardware Connection Pre-Check

## Summary

添加了Ferrum硬件连接预检测试，确保所有测试场景运行前硬件设备已正确连接并可用。

## One-Liner

Ferrum hardware pre-check module with automatic detection, retry capability, and graceful degradation when device unavailable.

## What Was Built

### 1. Hardware Check Module (`tests/interactive/hardware_check.py`)

- **`check_ferrum_connection()`**: 检测Ferrum设备连接状态
  - 尝试创建FerrumController实例
  - 成功返回True，失败返回False
  - 自动关闭连接避免占用串口
  - 中文状态输出（[Ferrum]/[错误]前缀）

- **`FerrumHardwareCheck` class**: 多端口详细检测
  - 支持检测多个端口（默认COM2, COM3）
  - 返回详细的错误信息
  - `is_any_connected()`: 检查是否有任何端口可用
  - `get_first_connected_port()`: 获取第一个可用端口

- **11个pytest单元测试**: 全覆盖测试场景
  - 成功/失败连接检测
  - 异常处理
  - 多端口检测逻辑

### 2. Hardware Check Scenario (`tests/interactive/scenarios.py`)

- **`HARDWARE_CHECK_SCENARIO`**: 硬件检测元场景
  - 作为ALL_SCENARIOS的第一个场景
  - 2步验证流程：检查连接 + 验证响应
  - 中文指令和预期结果

### 3. Test Runner Integration (`tests/interactive/test_runner.py`)

- **自动硬件预检测**: `initialize()`中自动执行
- **硬件状态属性**: `hardware_available`, `hardware_check_result`
- **错误显示**: 硬件未连接时显示中文错误信息
- **R键重试**: 用户可按R键重新检测，无需重启程序
- **场景选择保护**: 硬件不可用时阻止进入场景选择

## Commits

| Commit | Message | Files |
|--------|---------|-------|
| d1b7613 | feat(quick-ferrum-1): add hardware connection check module | tests/interactive/hardware_check.py |
| 1bf57a2 | feat(quick-ferrum-1): add hardware check scenario to scenarios.py | tests/interactive/scenarios.py |
| b4cde23 | feat(quick-ferrum-1): integrate hardware check into test runner | tests/interactive/test_runner.py, tests/interactive/hardware_check.py |

## Deviations from Plan

**None** - 计划按预期执行。

测试补丁路径从 `tests.interactive.hardware_check.FerrumController` 修正为 `core.ferrum_controller.FerrumController`，因为FerrumController是在函数内部导入的（避免循环依赖），需要在源位置进行mock。

## Verification Results

```bash
# 导入测试
$ python -c "from tests.interactive.hardware_check import check_ferrum_connection; from tests.interactive.scenarios import ALL_SCENARIOS; from tests.interactive.test_runner import TestRunner; print('All imports OK')"
All imports OK

# 场景顺序验证
$ python -c "from tests.interactive.scenarios import ALL_SCENARIOS; print([s.name for s in ALL_SCENARIOS])"
['hardware_check', 'guild_donation', 'character_detection']

# 单元测试
$ python -m pytest tests/interactive/hardware_check.py -v
============================= 11 passed in 0.08s =============================
```

## Usage

```python
# 快速检测
from tests.interactive.hardware_check import check_ferrum_connection
if check_ferrum_connection():
    print("硬件已就绪")
else:
    print("硬件未连接")

# 详细检测
from tests.interactive.hardware_check import FerrumHardwareCheck
checker = FerrumHardwareCheck(ports=["COM2", "COM3"])
if checker.is_any_connected():
    port = checker.get_first_connected_port()
    print(f"设备在 {port} 上可用")
```

## Self-Check: PASSED

- [x] tests/interactive/hardware_check.py 存在
- [x] tests/interactive/scenarios.py 包含 hardware_check 场景
- [x] tests/interactive/test_runner.py 集成硬件检测
- [x] 所有11个单元测试通过
- [x] 导入测试通过
- [x] 场景顺序正确
