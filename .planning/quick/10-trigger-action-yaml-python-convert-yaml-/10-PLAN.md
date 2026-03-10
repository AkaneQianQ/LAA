# Quick Task 10: 重构 trigger_action 功能

**Goal:** 基于现有 YAML + Python 架构重构 trigger_action 功能，不改变现有代码

## must_haves

- **truths:**
  - trigger_action.py 包含两个任务：Task A（图像检测+按键）和 Task B（图像检测+偏移点击+按键）
  - 现有架构使用 YAML 定义流程，convert_yaml_to_pipeline.py 转换为 JSON Pipeline
  - Python 模块通过 register.py 注册自定义 action/recognition
  - 现有 trigger_action.py 代码保持不变

- **artifacts:**
  - assets/tasks/trigger_action.yaml - 新的 YAML 工作流定义
  - agent/py_service/modules/trigger/register.py - 触发模块注册
  - assets/resource/pipeline/trigger_action.json - 转换后的 Pipeline JSON
  - 可选：interface.json 中注册新任务（如需要）

- **key_links:**
  - trigger_action.py: 原实现参考
  - convert_yaml_to_pipeline.py: YAML 转换逻辑
  - agent/py_service/modules/donation/register.py: 模块注册示例
  - assets/tasks/guild_donation.yaml: YAML 格式示例

---

## Task 1: 创建 trigger_action.yaml 工作流定义

**files:**
- assets/tasks/trigger_action.yaml (新建)

**action:**
创建 YAML 工作流，将 Task A 和 Task B 的硬编码逻辑转换为声明式步骤：

1. **Task A** - 循环检测目标A图像：
   - 使用 `wait_image` 或自定义 recognition 检测 target_a.png
   - 检测到后执行 `press` 动作序列: up, up, down
   - 添加冷却等待

2. **Task B** - 循环检测目标B图像：
   - 检测 target_b_1.png 或 target_b_2.png
   - 检测到后执行偏移点击动作（需要自定义 action）
   - 执行 Enter 按键
   - 添加冷却等待

3. **主循环** - 通过 Pipeline 的 next 链路实现循环

**verify:**
- YAML 语法正确，可被 convert_yaml_to_pipeline.py 解析
- 包含 start_step_id 和完整的 steps 定义
- 保留原有 ROI、COOLDOWN、OFFSETS 等配置参数

**done:**
assets/tasks/trigger_action.yaml 文件创建完成

---

## Task 2: 创建 trigger 模块注册文件

**files:**
- agent/py_service/modules/trigger/__init__.py (新建)
- agent/py_service/modules/trigger/register.py (新建)

**action:**
创建 trigger 模块，注册以下自定义组件：

1. **Custom Recognition: `TriggerTargetADetection`**
   - 检测 target_a.png 在指定 ROI
   - 返回匹配结果供 Pipeline 使用

2. **Custom Recognition: `TriggerTargetBDetection`**
   - 检测 target_b_1.png 和 target_b_2.png
   - 返回匹配位置和最佳匹配结果

3. **Custom Action: `ExecuteOffsetClicks`**
   - 接收检测到的坐标
   - 执行两次偏移点击（OFFSETS: [(7,0), (127,0)]）
   - 每次点击后等待 0.3s
   - 最后按 Enter (HID 40)

4. **Custom Action: `PressUpUpDown`**
   - 执行 Task A 的按键序列：up, up, down
   - 每按键间隔 50ms

**verify:**
- register.py 符合模块注册规范（包含 register() 函数）
- 使用正确的 import 路径（相对导入）
- 代码风格与 donation/register.py 一致

**done:**
agent/py_service/modules/trigger/ 目录及注册文件创建完成

---

## Task 3: 转换 YAML 为 Pipeline JSON 并验证

**files:**
- assets/resource/pipeline/trigger_action.json (新建)

**action:**
1. 运行 convert_yaml_to_pipeline.py 转换 YAML 为 JSON
2. 验证生成的 JSON 格式正确
3. 检查 Pipeline 节点链路是否形成循环（用于持续检测）

**verify:**
- JSON 文件成功生成
- 包含入口节点（trigger_actionMain）
- 节点 next 链路正确，可实现循环检测逻辑

**done:**
assets/resource/pipeline/trigger_action.json 成功生成

---

## Task 4: 更新主注册表（如需要）

**files:**
- agent/py_service/register.py (检查/可选修改)
- assets/interface.json (可选：添加任务定义)

**action:**
1. 检查主 register.py 是否自动加载 modules/*/register.py
2. 如需手动注册，添加 trigger 模块
3. 可选：在 interface.json 中添加 TriggerTask 定义

**verify:**
- trigger 模块会被正确加载
- 自定义 action/recognition 可被 Pipeline 调用

**done:**
模块注册逻辑验证完成
