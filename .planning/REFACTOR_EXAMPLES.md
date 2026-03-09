# 重构代码示例

**本文档提供具体的代码重构示例，展示如何将现有代码转换为 MaaEnd 风格。**

---

## 1. 目录结构迁移示例

### 1.1 当前文件结构

```
core/
├── ferrum_controller.py          # 267 lines
├── vision_engine.py              # 189 lines
├── workflow_bootstrap.py         # 85 lines
├── workflow_compiler.py          # 156 lines
├── workflow_executor.py          # 234 lines
├── workflow_runtime.py           # 312 lines
├── error_recovery.py             # 178 lines
├── database.py                   # 145 lines
└── parallel_matcher.py           # 98 lines

modules/
├── character_detector.py         # 245 lines
├── auto_login.py                 # 189 lines
└── guild_donation.py             # 267 lines
```

### 1.2 重构后结构

```
agent/
└── py-service/
    ├── main.py                   # [MOVED] 原 main.py
    ├── register.py               # [NEW] 组件注册入口
    ├── gui_bridge.py             # [NEW] GUI 桥接
    ├── pkg/                      # [NEW] 共享包目录
    │   ├── __init__.py
    │   ├── ferrum/               # [MOVED] 原 core/ferrum_controller.py
    │   │   ├── __init__.py
    │   │   ├── controller.py
    │   │   └── protocol.py       # [NEW] KMBox 协议定义
    │   ├── vision/               # [MOVED] 原 core/vision_engine.py
    │   │   ├── __init__.py
    │   │   ├── engine.py
    │   │   ├── template.py       # [NEW] 模板匹配封装
    │   │   └── roi.py            # [NEW] ROI 管理
    │   ├── workflow/             # [MOVED] 原 workflow_*.py
    │   │   ├── __init__.py
    │   │   ├── bootstrap.py
    │   │   ├── compiler.py
    │   │   ├── executor.py
    │   │   ├── runtime.py
    │   │   └── schema.py         # [NEW] Pipeline JSON Schema
    │   ├── recovery/             # [MOVED] 原 error_recovery.py
    │   │   ├── __init__.py
    │   │   ├── orchestrator.py
    │   │   └── errors.py         # [NEW] 错误类型定义
    │   └── common/               # [NEW] 通用节点
    │       ├── __init__.py
    │       └── nodes.py          # [NEW] 通用 Pipeline 节点
    └── modules/                  # [MOVED] 原 modules/
        ├── __init__.py
        ├── character/            # [MOVED] 原 character_detector.py
        │   ├── __init__.py
        │   ├── detector.py
        │   ├── register.py       # [NEW] 模块注册
        │   └── pipeline.json     # [NEW] 角色相关 Pipeline
        ├── login/                # [MOVED] 原 auto_login.py
        │   ├── __init__.py
        │   ├── workflow.py
        │   ├── register.py
        │   └── pipeline.json
        └── donation/             # [MOVED] 原 guild_donation.py
            ├── __init__.py
            ├── workflow.py
            ├── register.py
            └── pipeline.json
```

---

## 2. 代码重构示例

### 2.1 FerrumController → ferrum/controller.py

**原代码 (core/ferrum_controller.py):**
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import serial
import time
import random

class FerrumController:
    def __init__(self, port='COM2', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial = None

    def connect(self):
        self.serial = serial.Serial(self.port, self.baudrate, timeout=1)

    def move_to(self, x, y):
        # ... 原有代码保持不变 ...
        pass

    def click(self, x=None, y=None):
        # ... 原有代码保持不变 ...
        pass

    def press_key(self, key):
        # ... 原有代码保持不变 ...
        pass
```

**重构后 (agent/py-service/pkg/ferrum/controller.py):**
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KMBox 硬件控制器 - MaaEnd 风格封装
原有逻辑完全保留，仅添加 MaaEnd 风格的配置支持
"""

import serial
import time
import random
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class ControllerConfig:
    """控制器配置 - 对应 MaaEnd interface.json controller 配置"""
    name: str = "KMBox-Default"
    port: str = "COM2"
    baudrate: int = 115200
    timeout: float = 1.0

class FerrumController:
    """
    KMBox 硬件控制器

    原 FerrumController 的完全兼容封装，添加 MaaEnd 风格配置支持。
    所有原有方法保持不变。
    """

    def __init__(self, config: Optional[ControllerConfig] = None):
        """
        Args:
            config: 控制器配置，为 None 时使用默认配置
        """
        self.config = config or ControllerConfig()
        self.serial = None
        self._connected = False

    @classmethod
    def from_interface_config(cls, config_dict: dict) -> 'FerrumController':
        """
        从 interface.json 配置创建控制器

        Args:
            config_dict: interface.json 中的 controller 配置项

        Returns:
            FerrumController 实例
        """
        serial_config = config_dict.get('serial', {})
        config = ControllerConfig(
            name=config_dict.get('name', 'KMBox-Default'),
            port=serial_config.get('port', 'COM2'),
            baudrate=serial_config.get('baudrate', 115200),
            timeout=serial_config.get('timeout', 1.0)
        )
        return cls(config)

    def connect(self) -> bool:
        """连接硬件设备 - 原有逻辑"""
        try:
            self.serial = serial.Serial(
                self.config.port,
                self.config.baudrate,
                timeout=self.config.timeout
            )
            self._connected = True
            print(f"[硬件] 已连接 {self.config.port}")
            return True
        except Exception as e:
            print(f"[错误] 连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接 - 新增方法"""
        if self.serial:
            self.serial.close()
            self._connected = False
            print("[硬件] 已断开连接")

    # ===== 以下方法保持原样，完全不变 =====

    def move_to(self, x: int, y: int):
        """移动鼠标到坐标 - 原有逻辑"""
        # ... 原有代码完全复制 ...
        pass

    def click(self, x: Optional[int] = None, y: Optional[int] = None):
        """点击 - 原有逻辑"""
        # ... 原有代码完全复制 ...
        pass

    def press_key(self, key: str):
        """按键 - 原有逻辑"""
        # ... 原有代码完全复制 ...
        pass

    def send_command(self, cmd: str):
        """发送原始命令 - 原有逻辑"""
        # ... 原有代码完全复制 ...
        pass
```

### 2.2 注册表模式实现

**新建 (agent/py-service/register.py):**
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组件注册表 - 类似 MaaEnd agent/go-service/register.go

所有自定义识别器和动作在此集中注册，实现模块化加载。
"""

from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass
import importlib
import pkgutil

# 全局注册表
_custom_recognitions: Dict[str, Callable] = {}
_custom_actions: Dict[str, Callable] = {}
_registered_modules: set = set()

@dataclass
class RecognitionResult:
    """识别结果结构 - MaaEnd 风格"""
    matched: bool
    box: Optional[tuple] = None  # [x, y, w, h]
    score: float = 0.0
    payload: Optional[dict] = None

class Registry:
    """组件注册表"""

    @staticmethod
    def register_recognition(name: str, func: Callable) -> Callable:
        """
        注册自定义识别器

        Args:
            name: 识别器名称，Pipeline JSON 中通过此名称引用
            func: 识别函数，接收 context 字典，返回 RecognitionResult
        """
        _custom_recognitions[name] = func
        print(f"[注册] 识别器: {name}")
        return func

    @staticmethod
    def register_action(name: str, func: Callable) -> Callable:
        """
        注册自定义动作

        Args:
            name: 动作名称，Pipeline JSON 中通过此名称引用
            func: 动作函数，接收 context 字典
        """
        _custom_actions[name] = func
        print(f"[注册] 动作: {name}")
        return func

    @staticmethod
    def get_recognition(name: str) -> Optional[Callable]:
        return _custom_recognitions.get(name)

    @staticmethod
    def get_action(name: str) -> Optional[Callable]:
        return _custom_actions.get(name)

    @staticmethod
    def list_recognitions() -> Dict[str, Callable]:
        return _custom_recognitions.copy()

    @staticmethod
    def list_actions() -> Dict[str, Callable]:
        return _custom_actions.copy()

# 便捷装饰器
def recognition(name: str):
    """识别器装饰器"""
    def decorator(func: Callable) -> Callable:
        return Registry.register_recognition(name, func)
    return decorator

def action(name: str):
    """动作装饰器"""
    def decorator(func: Callable) -> Callable:
        return Registry.register_action(name, func)
    return decorator

def register_all_modules():
    """
    自动发现并注册所有模块

    扫描 modules/ 目录下的所有 register.py 并执行
    """
    from . import modules

    for importer, modname, ispkg in pkgutil.iter_modules(modules.__path__):
        if ispkg:
            try:
                register_module = importlib.import_module(f'.modules.{modname}.register', package=__package__)
                if hasattr(register_module, 'register'):
                    register_module.register()
                    _registered_modules.add(modname)
            except Exception as e:
                print(f"[警告] 模块 {modname} 注册失败: {e}")

    print(f"[注册] 已完成 {_registered_modules} 个模块加载")
```

### 2.3 CharacterDetector 模块化

**原代码 (modules/character_detector.py):**
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cv2
import numpy as np

# ROI 硬编码配置
SLOT_1_1_ROI = (904, 557, 1152, 624)
SLOT_1_2_ROI = (1164, 557, 1412, 624)
# ... 更多 ROI

class CharacterDetector:
    def __init__(self, vision_engine):
        self.vision = vision_engine
        self.slots = [SLOT_1_1_ROI, SLOT_1_2_ROI, ...]

    def detect_character_slots(self, screenshot):
        """检测角色槽位"""
        # ... 原有逻辑 ...
        pass

    def identify_by_screenshot(self, screenshot):
        """通过截图识别账号"""
        # ... 原有逻辑 ...
        pass
```

**重构后 (agent/py-service/modules/character/detector.py):**
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色检测器 - MaaEnd 风格模块化

原有逻辑完全保留，添加 Pipeline JSON 支持。
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from ...register import recognition, action, RecognitionResult

@dataclass
class SlotConfig:
    """槽位配置"""
    index: int
    roi: Tuple[int, int, int, int]  # x1, y1, x2, y2

# 原有 ROI 配置保持不变
SLOT_CONFIGS = [
    SlotConfig(0, (904, 557, 1152, 624)),   # 1-1
    SlotConfig(1, (1164, 557, 1412, 624)),  # 1-2
    SlotConfig(2, (1425, 557, 1673, 624)),  # 1-3
    SlotConfig(3, (904, 691, 1152, 758)),   # 2-1
    SlotConfig(4, (1164, 691, 1412, 758)),  # 2-2
    SlotConfig(5, (1425, 691, 1673, 758)),  # 2-3
    SlotConfig(6, (904, 826, 1152, 893)),   # 3-1
    SlotConfig(7, (1164, 826, 1412, 893)),  # 3-2
    SlotConfig(8, (1425, 826, 1673, 893)),  # 3-3
]

class CharacterDetector:
    """
    角色检测器

    原 CharacterDetector 的完全兼容封装。
    """

    def __init__(self, vision_engine=None):
        self.vision = vision_engine
        self.slots = [c.roi for c in SLOT_CONFIGS]

    def detect_character_slots(self, screenshot: np.ndarray) -> List[int]:
        """
        检测有角色的槽位索引

        原有逻辑完全保留
        """
        # ... 原有代码完全复制 ...
        pass

    def identify_by_screenshot(self, screenshot: np.ndarray) -> str:
        """
        通过截图生成账号标识

        原有逻辑完全保留
        """
        # ... 原有代码完全复制 ...
        pass

    def get_slot_roi(self, slot_index: int) -> Optional[Tuple]:
        """获取槽位 ROI"""
        if 0 <= slot_index < len(SLOT_CONFIGS):
            return SLOT_CONFIGS[slot_index].roi
        return None

# ===== MaaEnd 风格 Pipeline 集成 =====

@recognition("CharacterSlotDetection")
def detect_slots_recognition(context: dict) -> RecognitionResult:
    """
    Pipeline JSON 可调用的识别器

    在 Pipeline JSON 中使用:
    {
        "recognition": "Custom",
        "custom_recognition": "CharacterSlotDetection",
        "next": ["_HasCharacters", "_NoCharacters"]
    }
    """
    screenshot = context.get('screenshot')
    vision = context.get('vision_engine')

    if screenshot is None:
        return RecognitionResult(matched=False)

    detector = CharacterDetector(vision)
    slots = detector.detect_character_slots(screenshot)

    return RecognitionResult(
        matched=len(slots) > 0,
        payload={'slots': slots, 'count': len(slots)}
    )

@recognition("AccountIdentification")
def identify_account_recognition(context: dict) -> RecognitionResult:
    """
    Pipeline JSON 可调用的账号识别器
    """
    screenshot = context.get('screenshot')
    vision = context.get('vision_engine')

    if screenshot is None:
        return RecognitionResult(matched=False)

    detector = CharacterDetector(vision)
    account_id = detector.identify_by_screenshot(screenshot)

    return RecognitionResult(
        matched=bool(account_id),
        payload={'account_id': account_id}
    )

@action("ScrollToNextRow")
def scroll_next_row_action(context: dict):
    """
    Pipeline JSON 可调用的滚动动作
    """
    hardware = context.get('hardware_controller')
    if hardware:
        # 原有滚动逻辑
        hardware.move_to(1425, 826)
        hardware.scroll(-3)
```

**新建 (agent/py-service/modules/character/register.py):**
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色检测模块注册

自动注册本模块的所有识别器和动作。
"""

from ...register import register_all_modules
# 导入 detector.py 以触发装饰器注册
from .detector import detect_slots_recognition, identify_account_recognition, scroll_next_row_action

def register():
    """模块注册入口 - 由 register_all_modules() 调用"""
    # 装饰器已在导入时自动注册
    print("[模块] character 已注册")
```

### 2.4 Pipeline JSON 执行器

**原代码 (core/workflow_executor.py 核心逻辑):**
```python
class WorkflowExecutor:
    def __init__(self, compiled_workflow):
        self.workflow = compiled_workflow
        self.current_step = 0

    def execute(self):
        for step in self.workflow.steps:
            self.execute_step(step)
```

**重构后 (agent/py-service/pkg/workflow/executor.py):**
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline JSON 执行器 - MaaEnd 风格

兼容原有 YAML 工作流，同时支持 MaaEnd 风格的 JSON Pipeline。
"""

import json
import time
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field

from ...register import Registry, RecognitionResult

class NodeStatus(Enum):
    """节点执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class ExecutionContext:
    """执行上下文"""
    vision_engine: Any
    hardware_controller: Any
    screenshot: Optional[Any] = None
    variables: Dict[str, Any] = field(default_factory=dict)

class PipelineExecutor:
    """
    Pipeline 执行器

    支持:
    1. MaaEnd 风格的 JSON Pipeline
    2. 原有 YAML 工作流 (通过适配层)
    """

    def __init__(self, vision_engine, hardware_controller):
        self.vision = vision_engine
        self.hardware = hardware_controller
        self.nodes: Dict[str, dict] = {}
        self.current_node: Optional[str] = None
        self.node_history: List[str] = []
        self.max_history = 100

    def load_pipeline(self, pipeline_path: str):
        """加载 Pipeline JSON"""
        with open(pipeline_path, 'r', encoding='utf-8') as f:
            self.nodes = json.load(f)
        print(f"[Pipeline] 已加载 {len(self.nodes)} 个节点")

    def load_pipeline_from_dict(self, nodes: dict):
        """从字典加载 Pipeline"""
        self.nodes = nodes

    def execute(self, entry_node: str, context: Optional[ExecutionContext] = None) -> bool:
        """
        从入口节点开始执行 Pipeline

        Args:
            entry_node: 入口节点名称 (如 "DonationMain")
            context: 执行上下文，为 None 时自动创建

        Returns:
            是否成功完成
        """
        if context is None:
            context = ExecutionContext(self.vision, self.hardware)

        self.current_node = entry_node
        start_time = time.time()

        try:
            while self.current_node:
                if len(self.node_history) > self.max_history:
                    raise RuntimeError("节点执行循环 detected")

                success = self._execute_node(self.current_node, context)

                if not success:
                    print(f"[Pipeline] 节点执行失败: {self.current_node}")
                    return False

                self.node_history.append(self.current_node)

            print(f"[Pipeline] 执行完成，耗时 {time.time() - start_time:.2f}s")
            return True

        except Exception as e:
            print(f"[Pipeline] 执行异常: {e}")
            return False

    def _execute_node(self, node_name: str, context: ExecutionContext) -> bool:
        """执行单个节点"""
        node = self.nodes.get(node_name)
        if not node:
            print(f"[错误] 节点不存在: {node_name}")
            return False

        desc = node.get('desc', node_name)
        print(f"[节点] {desc}")

        try:
            # 1. 执行识别 (如果有)
            if 'recognition' in node:
                matched = self._execute_recognition(node['recognition'], context)

                if not matched:
                    # 识别失败，处理错误或跳转
                    if 'on_error' in node:
                        self.current_node = node['on_error'][0]
                        return True
                    elif 'timeout' in node:
                        # 等待重试逻辑
                        timeout = node.get('timeout', 5000)
                        print(f"[等待] 识别超时 {timeout}ms")
                        time.sleep(timeout / 1000)
                        return True
                    else:
                        return False

            # 2. 执行动作 (如果有)
            if 'action' in node:
                self._execute_action(node['action'], context)

            # 3. 更新当前节点为下一个
            next_nodes = node.get('next', [])
            if next_nodes:
                self.current_node = next_nodes[0]
            else:
                self.current_node = None  # 执行结束

            return True

        except Exception as e:
            print(f"[错误] 节点执行异常: {e}")
            if 'on_error' in node:
                self.current_node = node['on_error'][0]
                return True
            raise

    def _execute_recognition(self, recognition: Any, context: ExecutionContext) -> bool:
        """执行识别逻辑"""
        # 更新截图
        context.screenshot = self.vision.get_screen()

        if isinstance(recognition, str):
            # 简单识别类型
            recognition = {'type': recognition}

        rec_type = recognition.get('type')
        param = recognition.get('param', {})

        # 内置识别类型
        if rec_type == 'TemplateMatch':
            return self._recognize_template(param, context)

        # 自定义识别器
        elif rec_type == 'Custom':
            custom_name = recognition.get('custom_recognition')
            func = Registry.get_recognition(custom_name)
            if func:
                result = func({
                    'screenshot': context.screenshot,
                    'vision_engine': self.vision,
                    'hardware_controller': self.hardware,
                    'param': param
                })
                if isinstance(result, RecognitionResult):
                    return result.matched
                return bool(result)
            else:
                print(f"[警告] 未找到自定义识别器: {custom_name}")
                return False

        return False

    def _recognize_template(self, param: dict, context: ExecutionContext) -> bool:
        """模板匹配识别"""
        template = param.get('template')
        roi = param.get('roi')
        threshold = param.get('threshold', 0.8)

        if not template:
            return False

        result = self.vision.find_element(
            template_path=template,
            roi=roi,
            threshold=threshold
        )
        return result is not None

    def _execute_action(self, action: Any, context: ExecutionContext):
        """执行动作逻辑"""
        if isinstance(action, str):
            action = {'type': action}

        action_type = action.get('type')
        param = action.get('param', {})

        # 内置动作类型
        if action_type == 'Click':
            target = param.get('target')
            if target:
                self.hardware.click(target[0], target[1])

        elif action_type == 'KeyPress':
            key = param.get('key')
            if key:
                self.hardware.press_key(key)

        elif action_type == 'Custom':
            custom_name = action.get('custom_action')
            func = Registry.get_action(custom_name)
            if func:
                func({
                    'screenshot': context.screenshot,
                    'vision_engine': self.vision,
                    'hardware_controller': self.hardware,
                    'param': param
                })

        # 执行后延迟
        post_delay = action.get('post_delay', 0)
        if post_delay > 0:
            time.sleep(post_delay / 1000)
```

---

## 3. interface.json 完整示例

```json
{
    "interface_version": 1,
    "name": "FerrumBot",
    "description": "Lost Ark 公会捐赠自动化助手 - MaaEnd 结构",
    "version": "v1.0.0",
    "contact": "docs/CONTACT.md",
    "license": "LICENSE",

    "controller": [
        {
            "name": "KMBox-Default",
            "label": "KMBox 默认 (COM2)",
            "description": "通过串口连接的 KMBox 硬件设备",
            "type": "Serial",
            "serial": {
                "port": "COM2",
                "baudrate": 115200,
                "timeout": 1.0
            }
        },
        {
            "name": "KMBox-Custom",
            "label": "KMBox 自定义端口",
            "description": "用户指定端口的 KMBox 设备",
            "type": "Serial",
            "serial": {
                "port": "${PORT}",
                "baudrate": 115200,
                "timeout": 1.0
            },
            "option": [
                {
                    "name": "PORT",
                    "label": "串口",
                    "type": "text",
                    "default": "COM3"
                }
            ]
        }
    ],

    "resource": [
        {
            "name": "LostArk-KR-2560x1440",
            "label": "失落的方舟 (韩服) - 2560x1440",
            "description": "韩国服务器 2560x1440 分辨率资源",
            "path": ["./assets/resource"],
            "resolution": "2560x1440"
        }
    ],

    "agent": [
        {
            "type": "python",
            "entry": "agent/py-service/main.py",
            "description": "Python 服务代理"
        }
    ],

    "task": [
        {
            "name": "GuildDonation",
            "label": "公会捐赠",
            "description": "自动执行公会捐赠任务",
            "entry": "DonationMain",
            "pipeline": "assets/tasks/guild_donation.json",
            "option": [
                {
                    "name": "max_characters",
                    "label": "最大角色数",
                    "type": "number",
                    "default": 21,
                    "description": "最多处理的角色数量"
                }
            ]
        },
        {
            "name": "CharacterDiscovery",
            "label": "角色发现",
            "description": "扫描并索引所有角色",
            "entry": "CharacterDiscoveryMain",
            "pipeline": "assets/tasks/character_discovery.json"
        },
        {
            "name": "QuickDonation",
            "label": "快速捐赠 (预设)",
            "description": "使用默认设置的快速捐赠",
            "entry": "DonationMain",
            "pipeline": "assets/tasks/preset/quick_donation.json",
            "option": []
        }
    ],

    "import": [
        "assets/tasks/guild_donation.json",
        "assets/tasks/character_discovery.json",
        "assets/tasks/preset/quick_donation.json"
    ]
}
```

---

## 4. 测试用例示例

```json
{
    "configs": {
        "name": "公会捐赠按钮测试 (韩服-2560x1440)",
        "resource": "LostArk-KR-2560x1440",
        "controller": "KMBox-Default"
    },
    "cases": [
        {
            "name": "ESC菜单中的公会按钮",
            "image": "tests/MaaEndTesting/2560x1440/esc_menu_guild.png",
            "hits": ["GuildButton"],
            "description": "ESC菜单打开时，公会捐赠按钮应被识别"
        },
        {
            "name": "公会界面已打开",
            "image": "tests/MaaEndTesting/2560x1440/guild_ui_open.png",
            "hits": [
                {
                    "node": "GuildDonationTab",
                    "box": [100, 200, 150, 40]
                }
            ]
        },
        {
            "name": "网络错误弹窗",
            "image": "tests/MaaEndTesting/2560x1440/network_error.png",
            "hits": ["NetworkErrorDialog"]
        }
    ]
}
```

---

## 5. 迁移验证清单

### 功能验证
- [ ] KMBox 连接和通信正常
- [ ] 屏幕截图和模板匹配正常
- [ ] 角色检测返回正确槽位
- [ ] 账号识别生成正确 ID
- [ ] 公会捐赠流程完整执行
- [ ] 错误恢复机制正常工作

### 结构验证
- [ ] interface.json 能被正确解析
- [ ] Pipeline JSON 能被正确加载
- [ ] 自定义识别器能被调用
- [ ] 自定义动作能被调用
- [ ] 模块自动注册正常工作

### 兼容性验证
- [ ] 原有 GUI 能正常启动
- [ ] 全局热键 (F10, F11, END) 正常工作
- [ ] 进度存档正常读写
- [ ] 账号配置正常加载

---

*代码示例为重构参考，保持原有业务逻辑不变。*
