# FerrumBot API Reference

**强制阅读**: 开发新功能前必须阅读此文档，避免重复造轮子。

此文档汇总了代码库中所有可用的API，包括硬件控制、视觉引擎、工作流系统、模块注册等。

---

## 1. 组件注册系统 (Registry)

**文件**: `agent/py_service/register.py`

### 核心类

#### `Registry`
组件注册表，管理所有自定义识别器和动作。

| 方法 | 签名 | 说明 |
|------|------|------|
| `register_recognition` | `(name: str, func: Callable) -> Callable` | 注册自定义识别器 |
| `register_action` | `(name: str, func: Callable) -> Callable` | 注册自定义动作 |
| `get_recognition` | `(name: str) -> Optional[Callable]` | 获取识别器 |
| `get_action` | `(name: str) -> Optional[Callable]` | 获取动作 |
| `list_recognitions` | `() -> Dict[str, Callable]` | 列出所有识别器 |
| `list_actions` | `() -> Dict[str, Callable]` | 列出所有动作 |

#### `RecognitionResult`
识别结果数据类。

```python
@dataclass
class RecognitionResult:
    matched: bool
    box: Optional[tuple] = None  # [x, y, w, h]
    score: float = 0.0
    payload: Optional[dict] = None
```

### 装饰器

| 装饰器 | 用途 | 示例 |
|--------|------|------|
| `@recognition(name)` | 注册识别器 | `@recognition("MyDetector")` |
| `@action(name)` | 注册动作 | `@action("MyAction")` |

### 自动注册

```python
from agent.py_service.register import register_all_modules

# 自动发现并注册所有 modules/*/register.py
register_all_modules()
```

---

## 2. 硬件控制 (FerrumController)

**文件**: `agent/py_service/pkg/ferrum/controller.py`

### FerrumController 类

通过串口与KMBox硬件设备通信，实现鼠标和键盘控制。

#### 初始化

```python
controller = FerrumController(
    port: str = "COM2",
    baudrate: int = 115200,
    timeout: float = 1.0
)
```

#### 鼠标控制

| 方法 | 签名 | 说明 |
|------|------|------|
| `move_absolute` | `(x: int, y: int) -> None` | 绝对坐标移动（需win32api） |
| `click` | `(x: int, y: int) -> None` | 相对移动并左键点击 |
| `move_and_click` | `(x: int, y: int) -> None` | 快速序列：绝对移动+点击 |
| `click_right` | `(x: int, y: int) -> None` | 右键点击 |
| `scroll` | `(direction: str, ticks: int) -> None` | 滚轮滚动（"up"/"down"） |

#### 键盘控制

| 方法 | 签名 | 说明 |
|------|------|------|
| `press` | `(key_name: str) -> None` | 按键或组合键 |
| `key_down` | `(key_name: str) -> None` | 按住不释放 |
| `key_up` | `(key_name: str) -> None` | 释放按键 |

#### 支持的键名

```python
# 字母/数字: a-z, 0-9
# 方向键: up, down, left, right
# 功能键: f1-f12
# 修饰键: alt, lalt, ralt, ctrl, lctrl, rctrl, shift, lshift, rshift
# 其他: enter, esc, backspace, tab, space

# 组合键示例
controller.press("alt+u")      # 公会菜单
controller.press("esc")        # 取消/关闭
controller.press("enter")      # 确认
```

#### 其他方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `wait` | `(seconds: float) -> None` | 等待指定时间 |
| `is_connected` | `() -> bool` | 检查连接状态 |
| `handshake` | `() -> bool` | 硬件握手验证 |
| `close` | `() -> None` | 关闭连接 |

#### 上下文管理器支持

```python
with FerrumController() as controller:
    controller.click(100, 100)
# 自动关闭
```

---

## 3. 视觉引擎 (VisionEngine)

**文件**: `agent/py_service/pkg/vision/engine.py`

### VisionEngine 类

计算机视觉引擎，提供模板匹配和屏幕捕获。

#### 初始化

```python
from agent.py_service.pkg.vision.frame_cache import FrameCache

frame_cache = FrameCache(ttl_ms=150.0)
vision = VisionEngine(frame_cache=frame_cache)
```

#### 核心方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `find_element` | `(screenshot, template_path, roi, threshold=0.8) -> Tuple[bool, float, Tuple[int, int]]` | 模板匹配查找元素 |
| `get_screenshot` | `(force_fresh=False) -> np.ndarray` | 获取屏幕截图 |
| `clear_cache` | `() -> None` | 清空模板缓存 |
| `invalidate_cache` | `() -> None` | 使帧缓存失效 |

#### ROI约束

**所有模板匹配必须指定ROI**，ROI格式为 `(x1, y1, x2, y2)`。

```python
# 示例ROI (2560x1440)
roi = (904, 557, 1152, 624)  # Slot 1-1
```

### 独立函数

| 函数 | 签名 | 说明 |
|------|------|------|
| `match_template_roi` | `(screenshot, template, roi, method=cv2.TM_CCOEFF_NORMED)` | ROI内模板匹配 |
| `find_element` | `(screenshot, template, roi, threshold=0.8)` | 查找元素（函数版） |
| `apply_ff00ff_mask` | `(image) -> np.ndarray` | 应用FF00FF透明遮罩 |
| `load_template_with_mask` | `(path) -> Optional[np.ndarray]` | 加载带遮罩的模板 |

---

## 4. 帧缓存 (FrameCache)

**文件**: `agent/py_service/pkg/vision/frame_cache.py`

### FrameCache 类

TTL-based帧缓存，减少屏幕捕获开销。

#### 初始化

```python
cache = FrameCache(ttl_ms=150.0)  # 默认150ms
```

#### 方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `get` | `() -> Optional[np.ndarray]` | 获取缓存帧（如未过期） |
| `set` | `(frame: np.ndarray) -> None` | 存储帧到缓存 |
| `invalidate` | `() -> None` | 强制清除缓存 |
| `cache_stats` | `-> Dict[str, Any]` | 获取缓存统计 |

---

## 5. 并行匹配 (ParallelMatcher)

**文件**: `agent/py_service/pkg/vision/parallel_matcher.py`

### ParallelMatcher 类

多线程并行ROI模板匹配。

#### 初始化

```python
matcher = ParallelMatcher(max_workers=4)
```

#### 方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `scan_rois` | `(screenshot, template, rois, threshold=0.8) -> Dict[int, Tuple[bool, float]]` | 并行扫描多个ROI |
| `scan_slots` | `(screenshot, template, rois, threshold=0.8) -> Dict[int, Tuple[bool, float]]` | scan_rois别名 |

### 独立函数

| 函数 | 签名 | 说明 |
|------|------|------|
| `match_single_roi` | `(screenshot, template, roi, slot_index, threshold=0.8)` | 单ROI匹配 |
| `benchmark_parallel_vs_sequential` | `(screenshot, template, rois, threshold=0.8, iterations=3)` | 性能对比测试 |

---

## 6. 工作流系统 (Workflow)

### 6.1 Schema 定义

**文件**: `agent/py_service/pkg/workflow/schema.py`

#### 动作类型 (ActionConfig)

```python
ClickAction           # 点击: type="click", x, y, roi, random_y
ClickDetectedAction   # 检测点击: type="click_detected", image, roi, threshold, shrink_percent
CaptureROIAction      # ROI截图: type="capture_roi", roi, output_key, save_path
MoveAction            # 移动: type="move", x, y
PressAction           # 按键: type="press", key_name
ScrollAction          # 滚动: type="scroll", direction, ticks
WaitAction            # 等待: type="wait", duration_ms
WaitImageAction       # 等待图像: type="wait_image", state, image, roi, timeout_ms
```

#### WorkflowStep

```python
WorkflowStep(
    step_id: str,           # 唯一标识
    action: ActionConfig,    # 动作配置
    next: Optional[str],     # 下一步ID
    on_true: Optional[str],  # 条件为真时
    on_false: Optional[str], # 条件为假时
    retry: int = 0,          # 重试次数
    recovery: RecoveryConfig # 恢复配置
)
```

#### RecoveryConfig

```python
RecoveryConfig(
    anchor: bool = False,              # 是否为恢复锚点
    on_timeout: Optional[str],         # 超时回退目标
    max_escalations: int = 3,          # 最大升级次数
    audit_context: Optional[Dict]      # 审计上下文
)
```

### 6.2 编译器

**文件**: `agent/py_service/pkg/workflow/compiler.py`

#### compile_workflow

```python
from agent.py_service.pkg.workflow.compiler import compile_workflow

compiled = compile_workflow(config: WorkflowConfig) -> CompiledWorkflow
```

### 6.3 执行器

**文件**: `agent/py_service/pkg/workflow/executor.py`

#### WorkflowExecutor 类

```python
executor = WorkflowExecutor(
    workflow: CompiledWorkflow,
    action_dispatcher: Any,
    condition_evaluator: Any,
    error_logger: Optional[ErrorLogger] = None,
    account_id: Optional[str] = None
)

result = executor.execute()  # -> ExecutionResult
```

#### ExecutionResult

```python
ExecutionResult(
    success: bool,
    steps_executed: int,
    final_step_id: Optional[str],
    error: Optional[Exception],
    duration_ms: Optional[float],
    skipped_role: bool
)
```

### 6.4 引导器

**文件**: `agent/py_service/pkg/workflow/bootstrap.py`

```python
from agent.py_service.pkg.workflow.bootstrap import (
    create_workflow_executor,
    create_workflow_executor_with_account
)

# 创建执行器
executor = create_workflow_executor(
    workflow_path: Union[str, Path],
    controller: Any,
    vision_engine: Any,
    enable_compliance_guard: bool = True,
    compliance_config: Optional[Dict] = None,
    account_context: Optional[AccountContext] = None
)
```

---

## 7. 错误恢复系统

### 7.1 恢复编排器

**文件**: `agent/py_service/pkg/recovery/orchestrator.py`

#### ErrorKind (枚举)

```python
NETWORK_LAG = "network_lag"
UI_TIMEOUT = "ui_timeout"
DISCONNECT = "disconnect"
INPUT_POLICY_VIOLATION = "input_policy_violation"
UNKNOWN = "unknown"
```

#### RecoveryAction (枚举)

```python
L1_RETRY = "l1_retry"       # 步骤级重试
L2_ROLLBACK = "l2_rollback" # 回退到锚点
L3_SKIP = "l3_skip"         # 跳过当前角色
```

#### RecoveryOrchestrator 类

```python
orchestrator = RecoveryOrchestrator(
    l1_retry_threshold: int = 3,
    l2_rollback_threshold: int = 3,
    l3_skip_threshold: int = 3
)

action = orchestrator.determine_action(error_kind, step_id, attempt)
is_open = orchestrator.is_circuit_open(error_kind)
orchestrator.record_success(step_id)
orchestrator.reset()
```

#### ErrorContext

```python
ErrorContext(
    phase: str,
    step_id: str,
    action_type: str,
    attempt: int,
    account_id: Optional[str] = None,
    screenshot_path: Optional[str] = None,
    detail: Dict[str, Any] = field(default_factory=dict)
)
```

### 7.2 错误日志

**文件**: `agent/py_service/pkg/recovery/error_logger.py`

```python
logger = ErrorLogger(log_dir: str = "logs/errors")
log_file = logger.log_error(error_kind, message, context)
```

### 7.3 合规检查

**文件**: `agent/py_service/pkg/recovery/compliance.py`

```python
guard = ComplianceGuard()
report = guard.validate_all()

if report.all_ok:
    # 启动自动化
```

---

## 8. 数据库模块

**文件**: `agent/py_service/pkg/common/database.py`

### 初始化

```python
from agent.py_service.pkg.common.database import init_database

init_database(db_path: str)
```

### 账户管理

| 函数 | 签名 | 说明 |
|------|------|------|
| `create_account` | `(db_path, account_hash) -> int` | 创建账户 |
| `find_account_by_hash` | `(db_path, account_hash) -> Optional[Dict]` | 查找账户 |
| `get_or_create_account` | `(db_path, account_hash) -> int` | 获取或创建 |
| `update_account_tag` | `(db_path, account_id, tag_screenshot_path) -> bool` | 更新标签 |
| `list_all_accounts` | `(db_path) -> List[Dict]` | 列出所有账户 |

### 角色管理

| 函数 | 签名 | 说明 |
|------|------|------|
| `upsert_character` | `(db_path, account_id, slot_index, screenshot_path) -> int` | 插入/更新角色 |
| `find_character_by_slot` | `(db_path, account_id, slot_index) -> Optional[Dict]` | 查找角色 |
| `list_characters_by_account` | `(db_path, account_id) -> List[Dict]` | 列出账户角色 |
| `delete_character` | `(db_path, character_id) -> bool` | 删除角色 |

### 进度跟踪

| 函数 | 签名 | 说明 |
|------|------|------|
| `mark_character_done` | `(db_path, slot_index, character_name=None) -> bool` | 标记完成 |
| `is_character_done_today` | `(db_path, slot_index) -> bool` | 今日是否完成 |
| `get_character_progress` | `(db_path, slot_index) -> Optional[Dict]` | 获取进度 |
| `get_account_progress_summary` | `(db_path) -> Dict` | 获取汇总统计 |

---

## 9. 已注册模块

### 9.1 Character 模块

**文件**: `agent/py_service/modules/character/register.py`

| 名称 | 类型 | 说明 |
|------|------|------|
| `CharacterSlotDetection` | recognition | 检测角色选择界面的槽位 |
| `AccountIdentification` | recognition | 通过截图识别账户 |
| `ScrollbarBottomDetection` | recognition | 检测滚动条是否到底部 |
| `ScrollToNextRow` | action | 滚动到下一行 |
| `MoveToSafePosition` | action | 移动鼠标到安全位置 |

### 9.2 Login 模块

**文件**: `agent/py_service/modules/login/register.py`

| 名称 | 类型 | 说明 |
|------|------|------|
| `SwitchCharacter` | action | 切换角色 |
| `EnterCharacterSelection` | action | 进入角色选择界面 |
| `ClickCharacterSlot` | action | 点击指定槽位 |
| `ConfirmCharacterLogin` | action | 确认角色登录 |
| `OnCharacterSelectionScreen` | recognition | 检测是否在角色选择界面 |
| `LoginConfirmationDialog` | recognition | 检测登录确认对话框 |

### 9.3 Donation 模块

**文件**: `agent/py_service/modules/donation/register.py`

| 名称 | 类型 | 说明 |
|------|------|------|
| `ExecuteDonation` | action | 执行公会捐赠 |
| `OpenGuildMenu` | action | 打开公会菜单 (Alt+U) |
| `CloseGuildMenu` | action | 关闭公会菜单 (ESC) |
| `GuildMenuOpen` | recognition | 检测公会菜单是否打开 |

---

## 10. CharacterDetector 详细API

**文件**: `agent/py_service/modules/character/detector.py`

### 常量定义

#### ROI常量 (2560x1440)

```python
# 角色槽位ROI (3x3网格)
SLOT_1_1_ROI = (904, 557, 1152, 624)
SLOT_1_2_ROI = (1164, 557, 1412, 624)
SLOT_1_3_ROI = (1425, 557, 1673, 624)
SLOT_2_1_ROI = (904, 674, 1152, 741)
SLOT_2_2_ROI = (1164, 674, 1412, 741)
SLOT_2_3_ROI = (1425, 674, 1673, 741)
SLOT_3_1_ROI = (904, 791, 1152, 858)
SLOT_3_2_ROI = (1164, 791, 1412, 858)
SLOT_3_3_ROI = (1425, 791, 1673, 858)

ALL_SLOT_ROIS = [SLOT_1_1_ROI, ...]  # 所有9个槽位

# 其他ROI
ACCOUNT_TAG_ROI = (657, 854, 831, 876)
SCROLLBAR_BOTTOM_ROI = (1674, 790, 1694, 860)
MOUSE_SAFE_POSITION = (1700, 900)

# 模板路径
ONLINE_STATUS_TEMPLATE = 'resource/image/status_online_tag.png'
SCROLLBAR_BOTTOM_TEMPLATE = 'resource/image/scrollbar_bottom.png'
```

### CharacterDetector 类

```python
detector = CharacterDetector(vision_engine: VisionEngine)

# 检测角色槽位
slots = detector.detect_character_slots(screenshot)  # -> List[int]

# 获取当前在线槽位
online_slot = detector.get_current_online_slot(screenshot)  # -> Optional[int]

# 识别账户
account_id = detector.identify_by_screenshot(screenshot)  # -> Optional[str]

# 滚动相关
scroll_row = detector.calculate_scroll_row(slot_index, total_characters)
detector.scroll_to_slot(slot_index, total_characters, hardware_controller)
```

---

## 11. 服务入口 (main.py)

**文件**: `agent/py_service/main.py`

### 核心函数

| 函数 | 签名 | 说明 |
|------|------|------|
| `load_interface_config` | `(config_path=None) -> Dict` | 加载interface.json |
| `get_controller_config` | `(config, controller_name=None) -> Dict` | 获取控制器配置 |
| `get_resource_config` | `(config, resource_name=None) -> Dict` | 获取资源配置 |
| `get_task_config` | `(config, task_name) -> Dict` | 获取任务配置 |
| `list_available_tasks` | `(config) -> List[Dict]` | 列出可用任务 |
| `initialize` | `(...) -> InitializedComponents` | 初始化所有组件 |
| `run_task` | `(task_name, context=None, ...) -> bool` | 执行任务 |

### 命令行接口

```bash
python -m agent.py_service.main --task GuildDonation
python -m agent.py_service.main --list-tasks
python -m agent.py_service.main --test-init
```

---

## 12. 快速参考

### 12.1 创建自定义识别器

```python
from agent.py_service.register import recognition, RecognitionResult

@recognition("MyCustomDetection")
def my_detector(context: dict) -> RecognitionResult:
    screenshot = context.get('screenshot')
    vision = context.get('vision_engine')
    param = context.get('param', {})

    # 检测逻辑
    found = detect_something(screenshot, vision)

    return RecognitionResult(
        matched=found,
        box=(x, y, w, h) if found else None,
        score=confidence,
        payload={'extra': data}
    )
```

### 12.2 创建自定义动作

```python
from agent.py_service.register import action

@action("MyCustomAction")
def my_action(context: dict):
    hardware = context.get('hardware_controller')
    vision = context.get('vision_engine')
    param = context.get('param', {})

    # 执行动作
    hardware.click(x, y)
```

### 12.3 在Pipeline JSON中使用

```json
{
    "MyStep": {
        "recognition": "Custom",
        "custom_recognition": "MyCustomDetection",
        "action": {
            "type": "Custom",
            "custom_action": "MyCustomAction",
            "param": {"key": "value"}
        },
        "next": ["NextStep"]
    }
}
```

---

*最后更新: 2026-03-09*
