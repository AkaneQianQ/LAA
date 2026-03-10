---
phase: quick-ferrum
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/interactive/hardware_check.py
  - tests/interactive/scenarios.py
  - tests/interactive/test_runner.py
autonomous: true
requirements:
  - FERRUM-01
must_haves:
  truths:
    - "Hardware connection check runs before test scenarios"
    - "Clear error message shown if Ferrum device not connected"
    - "Test runner proceeds only when hardware is available"
  artifacts:
    - path: "tests/interactive/hardware_check.py"
      provides: "Hardware connection verification module"
      exports: ["check_ferrum_connection", "FerrumHardwareCheck"]
    - path: "tests/interactive/scenarios.py"
      provides: "Hardware check scenario added to ALL_SCENARIOS"
    - path: "tests/interactive/test_runner.py"
      provides: "Automatic hardware check on initialization"
  key_links:
    - from: "test_runner.py"
      to: "hardware_check.py"
      via: "import and call check_ferrum_connection()"
    - from: "scenarios.py"
      to: "hardware_check.py"
      via: "hardware_check scenario definition"
---

<objective>
添加Ferrum硬件连接预检测试，确保所有测试前硬件连接正常

Purpose: 在运行任何测试场景之前，自动检测Ferrum硬件设备是否已连接并可用，避免因硬件未连接导致的测试失败
Output: 硬件检测模块、硬件检测测试场景、测试运行器集成
</objective>

<execution_context>
@C:/Users/Akane/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Akane/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@C:/Users/Akane/FerrumProject/LostarkGuildDonationBot/core/ferrum_controller.py
@C:/Users/Akane/FerrumProject/LostarkGuildDonationBot/tests/interactive/scenarios.py
@C:/Users/Akane/FerrumProject/LostarkGuildDonationBot/tests/interactive/test_runner.py

## Hardware Interface Context

From ferrum_controller.py:
- FerrumController connects via serial port (default COM2, 115200 baud)
- Connection error raises FerrumConnectionError
- `is_connected()` method returns connection status
- `__init__` attempts connection immediately, raises on failure

## Test Framework Context

From test_flow_launcher.py:
- Uses TestRunner class to orchestrate tests
- Scenarios defined in scenarios.py with TestScenario/TestStep
- Hotkey 1-9 for scenario selection
- F1 to continue/start

From scenarios.py:
- ALL_SCENARIOS list contains available test scenarios
- TestScenario has name, description, steps fields
- TestStep has step_id, instruction, expected_result, can_skip fields
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create hardware connection check module</name>
  <files>tests/interactive/hardware_check.py</files>
  <action>
创建硬件连接检测模块 tests/interactive/hardware_check.py，包含：

1. `check_ferrum_connection(port="COM2", baudrate=115200, timeout=1.0)` 函数：
   - 尝试创建 FerrumController 实例
   - 使用 try/except 捕获 FerrumConnectionError
   - 成功时返回 True，失败时返回 False
   - 打印中文状态信息（[Ferrum] 前缀表示信息，[错误] 前缀表示错误）
   - 确保在成功检测后关闭连接（避免占用串口）

2. `FerrumHardwareCheck` 类（可选，用于更详细的检测）：
   - 支持检测多个端口（COM2, COM3）
   - 返回详细的错误信息

3. 模块级单元测试（使用 pytest）：
   - 测试成功连接场景（使用 mock）
   - 测试连接失败场景（使用 mock）

遵循项目约定：
- 使用中文注释和用户消息
- 使用 [Ferrum] 和 [错误] 前缀
- 导入 FerrumController 和 FerrumConnectionError 从 core.ferrum_controller
  </action>
  <verify>
    <automated>python -c "from tests.interactive.hardware_check import check_ferrum_connection; print('Import OK')"</automated>
  </verify>
  <done>
    - 文件 tests/interactive/hardware_check.py 存在
    - 可以成功导入 check_ferrum_connection 函数
    - 包含基本的中文状态输出
  </done>
</task>

<task type="auto">
  <name>Task 2: Add hardware check scenario to scenarios.py</name>
  <files>tests/interactive/scenarios.py</files>
  <action>
在 tests/interactive/scenarios.py 中添加硬件检测测试场景：

1. 创建 HARDWARE_CHECK_SCENARIO 常量：
   - name: "hardware_check"
   - description: "检测Ferrum硬件连接状态"
   - steps: 包含2个步骤
     - 步骤1: instruction="检查Ferrum设备是否已连接", expected_result="设备连接成功，串口COM2可用", can_skip=False
     - 步骤2: instruction="验证设备响应", expected_result="设备响应正常，可以执行测试", can_skip=False

2. 将 HARDWARE_CHECK_SCENARIO 添加到 ALL_SCENARIOS 列表的第一位（作为默认/第一个选项）

3. 确保导入所需的 TestStep 和 TestScenario（已存在）

注意：这个场景是一个"元场景"，用于验证测试基础设施本身。实际硬件检测逻辑在 test_runner.py 中自动执行。
  </action>
  <verify>
    <automated>python -c "from tests.interactive.scenarios import ALL_SCENARIOS; print('First scenario:', ALL_SCENARIOS[0].name)"</automated>
  </verify>
  <done>
    - HARDWARE_CHECK_SCENARIO 已定义
    - ALL_SCENARIOS 列表以 hardware_check 开头
    - 可以成功导入并访问场景
  </done>
</task>

<task type="auto">
  <name>Task 3: Integrate hardware check into test runner</name>
  <files>tests/interactive/test_runner.py</files>
  <action>
在 tests/interactive/test_runner.py 中集成硬件预检测：

1. 在文件顶部导入：
   - `from tests.interactive.hardware_check import check_ferrum_connection`

2. 在 TestRunner.__init__ 中添加：
   - `self.hardware_available = False`
   - `self.hardware_check_result = None`

3. 在 TestRunner.initialize 方法开头添加硬件检测逻辑：
   - 调用 check_ferrum_connection() 进行预检测
   - 如果检测失败，在 overlay 显示错误信息：
     - instruction = "[错误] Ferrum硬件未连接，请检查: 1.设备电源 2.USB连接 3.COM端口"
     - 禁用场景选择（不调用 show_scenario_selection）
     - 只显示重试提示
   - 如果检测成功，设置 self.hardware_available = True，继续正常流程

4. 添加 `_retry_hardware_check` 方法：
   - 允许用户按 R 键重试硬件检测
   - 成功后自动继续到场景选择

5. 更新 show_scenario_selection 方法：
   - 如果 hardware_available 为 False，显示错误而不是场景列表

确保：
- 使用中文消息，[Ferrum] 和 [错误] 前缀
- 硬件检测失败时测试流程优雅降级
- 用户可以通过重试恢复（无需重启程序）
  </action>
  <verify>
    <automated>python -c "from tests.interactive.test_runner import TestRunner; r = TestRunner(); print('TestRunner imports OK, hardware_available attr exists:', hasattr(r, 'hardware_available'))"</automated>
  </verify>
  <done>
    - TestRunner 导入 hardware_check 模块
    - initialize() 方法包含硬件预检测逻辑
    - 硬件检测失败时显示中文错误信息
    - 硬件检测成功后才显示场景选择
  </done>
</task>

</tasks>

<verification>
整体验证步骤：

1. 导入测试：
   ```bash
   python -c "from tests.interactive.hardware_check import check_ferrum_connection; from tests.interactive.scenarios import ALL_SCENARIOS; from tests.interactive.test_runner import TestRunner; print('All imports OK')"
   ```

2. 场景列表验证：
   ```bash
   python -c "from tests.interactive.scenarios import ALL_SCENARIOS; print('Scenarios:', [s.name for s in ALL_SCENARIOS])"
   ```
   期望输出：第一个场景是 "hardware_check"

3. 单元测试运行：
   ```bash
   python -m pytest tests/interactive/hardware_check.py -v
   ```

4. 集成测试（模拟无硬件情况）：
   ```bash
   python test_flow_launcher.py --list
   ```
</verification>

<success_criteria>
- tests/interactive/hardware_check.py 存在且可导入
- check_ferrum_connection() 函数可以检测硬件连接状态
- scenarios.py 中包含 hardware_check 场景作为第一个选项
- TestRunner.initialize() 自动执行硬件预检测
- 硬件未连接时显示中文错误信息并阻止测试继续
- 所有代码遵循项目中文注释和命名约定
</success_criteria>

<output>
After completion, create `.planning/quick/1-ferrum/1-SUMMARY.md`
</output>
