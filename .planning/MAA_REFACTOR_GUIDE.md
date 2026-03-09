# MaaEnd 结构迁移指南

**目标**: 将 MaaEnd 的项目结构和逻辑规范应用到 LostarkGuildDonationBot，保持现有功能不变，仅进行结构规范化和模块化改进。

**分析日期**: 2026-03-09

---

## 1. 当前架构对比

### LostarkGuildDonationBot (当前)

```
[project-root]/
├── core/                    # 核心硬件和视觉抽象
│   ├── ferrum_controller.py      # KMBox 硬件控制
│   ├── vision_engine.py          # OpenCV 视觉引擎
│   ├── workflow_bootstrap.py     # 工作流启动器
│   ├── workflow_compiler.py      # YAML 工作流编译
│   ├── workflow_executor.py      # 工作流执行器
│   ├── workflow_runtime.py       # 工作流运行时
│   ├── error_recovery.py         # 错误恢复
│   ├── database.py               # SQLite 数据库
│   └── parallel_matcher.py       # 并行匹配
├── modules/                 # 自动化工作流实现
│   ├── character_detector.py     # 角色检测
│   ├── auto_login.py             # 自动登录
│   └── guild_donation.py         # 公会捐赠
├── assets/                  # 模板图片 (Buttom.bmp, CharacterISorNo.bmp)
├── config/                  # 配置
│   └── workflows/
│       └── guild_donation.yaml   # 主工作流定义
├── tests/                   # 测试用例
├── docs/                    # 文档
├── gui_launcher.py          # GUI 入口
└── main.py                  # 主自动化脚本
```

### MaaEnd (参考结构)

```
[project-root]/
├── agent/                   # 自定义算法代理
│   ├── cpp-algo/            # C++ 视觉算法 (OpenCV + ONNX)
│   └── go-service/          # Go 业务逻辑服务
├── assets/                  # 静态资源配置
│   ├── interface.json       # 主界面配置
│   ├── resource/            # 核心资源包
│   │   ├── pipeline/        # 119 个 JSON 流水线定义
│   │   └── image/           # 41 个目录的模板图片
│   └── tasks/               # 32 个任务定义
├── tests/                   # 测试用例
├── tools/                   # 开发工具 (Python)
└── docs/                    # 文档
```

---

## 2. 迁移策略

### 2.1 目录结构调整 (Phase 1)

将现有结构映射到 MaaEnd 模式:

```
LostarkGuildDonationBot/
├── agent/                          # [NEW] 自定义算法代理 (Python-based)
│   └── py-service/                 # [MOVED] 原 core/ + modules/ 合并
│       ├── main.py                 # [MOVED] 服务入口 (原 main.py)
│       ├── register.py             # [NEW] 组件注册表
│       ├── pkg/                    # [NEW] 共享包
│       │   ├── ferrum/             # [MOVED] 原 core/ferrum_controller.py
│       │   ├── vision/             # [MOVED] 原 core/vision_engine.py
│       │   ├── workflow/           # [MOVED] 原 workflow_*.py
│       │   └── recovery/           # [MOVED] 原 error_recovery.py
│       └── modules/                # [MOVED] 业务模块
│           ├── character/          # [MOVED] 原 character_detector.py
│           ├── login/              # [MOVED] 原 auto_login.py
│           └── donation/           # [MOVED] 原 guild_donation.py
├── assets/                         # [EXISTING] 增强组织
│   ├── interface.json              # [NEW] 主配置 (类似 MaaEnd)
│   ├── resource/                   # [REORG] 原 assets/ 重组织
│   │   ├── pipeline/               # [NEW] YAML -> JSON 流水线 (可选)
│   │   └── image/                  # [MOVED] 原 assets/*.bmp
│   └── tasks/                      # [MOVED] 原 config/workflows/
├── tests/                          # [EXISTING] 保持不变
├── tools/                          # [NEW] 开发工具目录
│   └── setup_workspace.py          # [MOVED] 环境初始化脚本
├── docs/                           # [EXISTING] 保持不变
└── gui_launcher.py                 # [MOVED] 根目录保留入口
```

### 2.2 核心改进点

#### A. 配置文件标准化 (MaaEnd Pattern)

**当前**: `config/workflows/guild_donation.yaml`

**改进后**: `assets/interface.json` (类似 MaaEnd)

```json
{
    "interface_version": 1,
    "name": "FerrumBot",
    "description": "Lost Ark 公会捐赠自动化",
    "version": "v1.0.0",
    "controller": [
        {
            "name": "KMBox-Default",
            "type": "Serial",
            "serial": {
                "port": "COM2",
                "baudrate": 115200
            }
        }
    ],
    "resource": [
        {
            "name": "LostArk-KR",
            "path": ["./assets/resource"],
            "resolution": "2560x1440"
        }
    ],
    "task": [
        {
            "name": "GuildDonation",
            "entry": "DonationMain",
            "pipeline": "tasks/guild_donation.json"
        },
        {
            "name": "CharacterSwitch",
            "entry": "CharacterSwitchMain",
            "pipeline": "tasks/character_switch.json"
        }
    ]
}
```

#### B. Pipeline 结构规范化

**当前**: YAML 工作流定义

```yaml
steps:
  - name: "打开ESC菜单"
    action:
      type: press
      key: esc
  - name: "点击公会捐赠"
    action:
      type: click_detected
      image: assets/guild_button.bmp
      roi: [100, 200, 300, 400]
```

**改进后**: JSON Pipeline (MaaEnd 风格)

```json
{
    "DonationMain": {
        "desc": "公会捐赠主入口",
        "next": ["_OpenEscMenu", "_CheckNetworkError"]
    },
    "_OpenEscMenu": {
        "desc": "打开ESC菜单",
        "action": {
            "type": "KeyPress",
            "param": { "key": "esc" }
        },
        "next": ["_ClickGuildButton"]
    },
    "_ClickGuildButton": {
        "desc": "点击公会捐赠按钮",
        "recognition": {
            "type": "TemplateMatch",
            "param": {
                "roi": [100, 200, 300, 400],
                "template": "image/guild_button.png",
                "threshold": 0.8
            }
        },
        "action": "Click",
        "next": ["_WaitDonationUI"]
    },
    "_WaitDonationUI": {
        "desc": "等待捐赠界面加载",
        "recognition": {
            "type": "TemplateMatch",
            "param": {
                "template": "image/donation_ui_title.png",
                "threshold": 0.8
            }
        },
        "timeout": 5000,
        "on_error": ["_HandleNetworkError"]
    }
}
```

#### C. 组件注册模式 (Go Service Pattern)

**新建**: `agent/py-service/register.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组件注册表 - 类似 MaaEnd 的 agent/go-service/register.go
所有自定义识别和动作在此注册
"""

from typing import Dict, Callable, Any

# 注册表
_custom_recognitions: Dict[str, Callable] = {}
_custom_actions: Dict[str, Callable] = {}

def register_recognition(name: str, func: Callable):
    """注册自定义识别器"""
    _custom_recognitions[name] = func

def register_action(name: str, func: Callable):
    """注册自定义动作"""
    _custom_actions[name] = func

def get_recognition(name: str) -> Callable:
    return _custom_recognitions.get(name)

def get_action(name: str) -> Callable:
    return _custom_actions.get(name)

def register_all():
    """注册所有组件 - 主入口调用"""
    # 导入并注册各个模块
    from .modules.character import detector
    from .modules.donation import workflow
    from .pkg.vision import custom_matcher

    # 注册角色检测识别器
    register_recognition("CharacterSlotDetection", detector.detect_slots)
    register_recognition("AccountIdentification", detector.identify_account)

    # 注册捐赠工作流动作
    register_action("ExecuteDonation", workflow.execute_donation)
    register_action("SwitchCharacter", workflow.switch_character)

    # 注册自定义视觉识别
    register_recognition("ROIMatcher", custom_matcher.match_in_roi)

    print(f"[注册] 已加载 {_custom_recognitions} 个识别器, {_custom_actions} 个动作")
```

#### D. 错误处理规范化

**当前**: 分散的 try-except 块

**改进后**: 统一错误节点 (MaaEnd Pattern)

```python
# agent/py-service/pkg/recovery/error_nodes.py

ERROR_NODES = {
    "_NetworkError": {
        "desc": "网络错误处理",
        "recognition": {
            "type": "TemplateMatch",
            "param": {
                "template": "image/network_error.png",
                "threshold": 0.8
            }
        },
        "action": "Click",  # 点击确认
        "next": ["_WaitReconnect"]
    },
    "_DisconnectError": {
        "desc": "断开连接处理",
        "recognition": {
            "type": "TemplateMatch",
            "param": {
                "template": "image/disconnect.png"
            }
        },
        "action": "Click",
        "next": ["_WaitLoginScreen"]
    },
    "_GeneralErrorHandler": {
        "desc": "通用错误处理",
        "focus": {
            "Node.Action.Failed": "[错误] 发生异常，准备恢复"
        },
        "next": ["_CleanupState", "_JumpBack"]
    }
}
```

---

## 3. 具体迁移步骤

### Phase 1: 目录重组 (保持代码不变)

```bash
# 1. 创建新目录结构
mkdir -p agent/py-service/pkg/{ferrum,vision,workflow,recovery}
mkdir -p agent/py-service/modules/{character,login,donation}
mkdir -p assets/resource/{pipeline,image}
mkdir -p assets/tasks
mkdir -p tools

# 2. 移动核心文件 (保持 import 不变，使用 __init__.py 转发)
mv core/ferrum_controller.py agent/py-service/pkg/ferrum/controller.py
mv core/vision_engine.py agent/py-service/pkg/vision/engine.py
mv core/workflow_*.py agent/py-service/pkg/workflow/
mv core/error_recovery.py agent/py-service/pkg/recovery/
mv modules/character_detector.py agent/py-service/modules/character/detector.py
mv modules/auto_login.py agent/py-service/modules/login/
mv modules/guild_donation.py agent/py-service/modules/donation/

# 3. 资源重组织
mv assets/*.bmp assets/resource/image/
mv config/workflows/* assets/tasks/
```

### Phase 2: 创建转发文件

在旧位置创建转发文件保持兼容性:

```python
# core/__init__.py
"""兼容层 - 转发到新位置"""
from agent.py_service.pkg.ferrum.controller import FerrumController
from agent.py_service.pkg.vision.engine import VisionEngine
from agent.py_service.pkg.workflow.bootstrap import WorkflowBootstrap
# ... etc
```

### Phase 3: 实现 MaaEnd 模式

#### 3.1 接口配置标准化

创建 `assets/interface.json`:

```json
{
    "interface_version": 1,
    "name": "FerrumBot",
    "description": "Lost Ark 公会捐赠自动化助手",
    "version": "v1.0.0",
    "contact": "docs/CONTACT.md",
    "license": "LICENSE",
    "controller": [
        {
            "name": "KMBox-Default",
            "label": "KMBox 默认",
            "description": "通过串口连接的 KMBox 硬件设备",
            "type": "Serial",
            "serial": {
                "port": "COM2",
                "baudrate": 115200,
                "timeout": 1.0
            }
        }
    ],
    "resource": [
        {
            "name": "LostArk-KR-2560x1440",
            "label": "失落的方舟 (韩服)",
            "description": "2560x1440 分辨率资源包",
            "path": ["./assets/resource"],
            "resolution": "2560x1440"
        }
    ],
    "agent": [
        {
            "type": "python",
            "entry": "agent/py-service/main.py"
        }
    ],
    "task": [
        {
            "name": "GuildDonation",
            "label": "公会捐赠",
            "description": "自动执行公会捐赠任务",
            "entry": "DonationMain",
            "pipeline": "assets/tasks/guild_donation.json"
        },
        {
            "name": "CharacterDiscovery",
            "label": "角色发现",
            "description": "自动发现并索引角色",
            "entry": "CharacterDiscoveryMain",
            "pipeline": "assets/tasks/character_discovery.json"
        }
    ]
}
```

#### 3.2 Pipeline JSON 转换

将现有 YAML 工作流转换为 MaaEnd 风格的 JSON:

```python
# tools/convert_yaml_to_pipeline.py
"""
YAML 工作流到 JSON Pipeline 转换工具
保持逻辑不变，仅格式转换
"""

import yaml
import json
from pathlib import Path

def convert_step_to_node(step: dict, index: int) -> tuple:
    """将 YAML step 转换为 Pipeline node"""
    name = step.get('name', f'Step{index}')
    action = step.get('action', {})

    node = {
        "desc": name,
    }

    # 转换 action 类型
    action_type = action.get('type')
    if action_type == 'press':
        node['action'] = {
            'type': 'KeyPress',
            'param': {'key': action.get('key')}
        }
    elif action_type == 'click':
        node['action'] = {
            'type': 'Click',
            'param': {'target': action.get('coordinates', [])}
        }
    elif action_type == 'click_detected':
        node['recognition'] = {
            'type': 'TemplateMatch',
            'param': {
                'template': action.get('image', ''),
                'roi': action.get('roi', []),
                'threshold': action.get('threshold', 0.8)
            }
        }
        node['action'] = 'Click'
    elif action_type == 'wait_image':
        node['recognition'] = {
            'type': 'TemplateMatch',
            'param': {
                'template': action.get('image', ''),
                'roi': action.get('roi', [])
            }
        }
        node['timeout'] = action.get('timeout', 5000)

    return f'_{name}', node

def convert_workflow(yaml_path: Path) -> dict:
    """转换整个工作流文件"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        workflow = yaml.safe_load(f)

    pipeline = {}
    prev_node = None

    for i, step in enumerate(workflow.get('steps', [])):
        node_name, node = convert_step_to_node(step, i)
        pipeline[node_name] = node

        # 链接节点
        if prev_node:
            pipeline[prev_node]['next'] = [node_name]
        prev_node = node_name

    # 添加入口节点
    if workflow.get('steps'):
        entry_name = f"{yaml_path.stem}Main"
        pipeline[entry_name] = {
            "desc": f"{workflow.get('name', '任务')} 主入口",
            "next": [list(pipeline.keys())[0]]
        }

    return pipeline

if __name__ == '__main__':
    import sys
    yaml_file = Path(sys.argv[1])
    pipeline = convert_workflow(yaml_file)

    output = yaml_file.parent / f"{yaml_file.stem}.json"
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(pipeline, f, indent=4, ensure_ascii=False)

    print(f"转换完成: {output}")
```

#### 3.3 自定义识别器注册

```python
# agent/py-service/modules/character/register.py
"""
角色检测模块注册 - 类似 MaaEnd 的模块化注册
"""

from ...register import register_recognition, register_action
from .detector import CharacterDetector

# 创建检测器实例
detector = CharacterDetector()

def detect_slots(context: dict) -> dict:
    """自定义识别: 检测角色槽位"""
    screenshot = context.get('screenshot')
    slots = detector.detect_character_slots(screenshot)
    return {
        'slots': slots,
        'count': len(slots)
    }

def identify_account(context: dict) -> dict:
    """自定义识别: 识别账号"""
    screenshot = context.get('screenshot')
    account_id = detector.identify_by_screenshot(screenshot)
    return {
        'account_id': account_id
    }

# 注册到全局注册表
def register():
    register_recognition("CharacterSlotDetection", detect_slots)
    register_recognition("AccountIdentification", identify_account)
    print("[注册] 角色检测模块已加载")
```

---

## 4. 命名规范对照表

| 当前命名 | MaaEnd 规范 | 说明 |
|---------|------------|------|
| `guild_donation.py` | `donation/` | 模块目录化 |
| `ferrum_controller.py` | `ferrum/controller.py` | pkg/子目录 |
| `vision_engine.py` | `vision/engine.py` | pkg/子目录 |
| `CONFIG` dict | `interface.json` | 配置外置 |
| `ROI_CONFIG` | Pipeline JSON | ROI 嵌入 pipeline |
| `run_guild_donation()` | `DonationMain` node | 入口节点化 |
| `yaml workflow` | `pipeline/*.json` | JSON Pipeline |
| hardcoded coords | `interface.json` controller | 配置化 |

---

## 5. 关键设计模式迁移

### 5.1 MaaEnd 的 "秦始皇节点" 模式

MaaEnd 中复用性高的节点被封装为可复用组件:

```python
# agent/py-service/pkg/common/nodes.py
"""
通用节点库 - 类似 MaaEnd 的 Interface 目录
"""

COMMON_NODES = {
    "CommonPressEsc": {
        "desc": "通用: 按ESC键",
        "action": {
            "type": "KeyPress",
            "param": {"key": "esc"}
        }
    },
    "CommonWaitLoading": {
        "desc": "通用: 等待加载完成",
        "recognition": {
            "type": "TemplateMatch",
            "param": {
                "template": "image/common/loading_complete.png"
            }
        },
        "timeout": 10000,
        "on_error": ["CommonHandleTimeout"]
    },
    "CommonHandleTimeout": {
        "desc": "通用: 处理超时",
        "focus": {
            "Node.Action.Failed": "[超时] 等待加载超时"
        },
        "next": ["CommonPressEsc"]
    }
}
```

### 5.2 场景管理器模式

```python
# agent/py-service/pkg/scene/manager.py
"""
场景管理器 - 类似 MaaEnd 的 SceneManager
管理游戏界面之间的跳转
"""

class SceneManager:
    """万能跳转和场景导航"""

    SCENES = {
        "character_selection": {
            "recognition": {
                "type": "TemplateMatch",
                "template": "image/scene/character_select_title.png"
            }
        },
        "guild_ui": {
            "recognition": {
                "type": "TemplateMatch",
                "template": "image/scene/guild_ui_title.png"
            }
        },
        "main_game": {
            "recognition": {
                "type": "TemplateMatch",
                "template": "image/scene/main_ui.png"
            }
        }
    }

    def navigate_to(self, target_scene: str):
        """导航到目标场景"""
        # 实现跳转逻辑
        pass
```

### 5.3 工作流执行器模式

```python
# agent/py-service/pkg/workflow/executor.py
"""
工作流执行器 - MaaEnd 风格 Pipeline 执行
替代现有的 workflow_executor.py
"""

import json
from typing import Dict, Any

class PipelineExecutor:
    """
    Pipeline JSON 执行器
    类似于 MaaFramework 的节点执行引擎
    """

    def __init__(self, vision_engine, hardware_gateway):
        self.vision = vision_engine
        self.hardware = hardware_gateway
        self.nodes: Dict[str, dict] = {}
        self.current_node = None

    def load_pipeline(self, pipeline_path: str):
        """加载 Pipeline JSON"""
        with open(pipeline_path, 'r', encoding='utf-8') as f:
            self.nodes = json.load(f)

    def execute(self, entry_node: str):
        """从入口节点开始执行"""
        self.current_node = entry_node

        while self.current_node:
            node = self.nodes.get(self.current_node)
            if not node:
                print(f"[错误] 节点不存在: {self.current_node}")
                break

            print(f"[执行] {node.get('desc', self.current_node)}")

            try:
                # 执行识别
                if 'recognition' in node:
                    result = self._execute_recognition(node['recognition'])
                    if not result and 'on_error' in node:
                        self.current_node = node['on_error'][0]
                        continue

                # 执行动作
                if 'action' in node:
                    self._execute_action(node['action'])

                # 确定下一个节点
                next_nodes = node.get('next', [])
                if next_nodes:
                    self.current_node = next_nodes[0]
                else:
                    self.current_node = None

            except Exception as e:
                print(f"[错误] 节点执行失败: {e}")
                if 'on_error' in node:
                    self.current_node = node['on_error'][0]
                else:
                    raise

    def _execute_recognition(self, recognition: dict) -> bool:
        """执行识别逻辑"""
        rec_type = recognition.get('type')
        param = recognition.get('param', {})

        if rec_type == 'TemplateMatch':
            return self.vision.find_template(
                template_path=param.get('template'),
                roi=param.get('roi'),
                threshold=param.get('threshold', 0.8)
            )

        return False

    def _execute_action(self, action: Any):
        """执行动作逻辑"""
        if isinstance(action, str):
            action = {'type': action}

        action_type = action.get('type')
        param = action.get('param', {})

        if action_type == 'Click':
            target = param.get('target')
            if target:
                self.hardware.click(target[0], target[1])
        elif action_type == 'KeyPress':
            key = param.get('key')
            self.hardware.press_key(key)
```

---

## 6. 测试框架迁移

### 6.1 MaaEnd 风格测试结构

```
tests/
├── Common/                    # 通用测试
│   └── Button/
│       ├── test_esc_button.json
│       └── test_confirm_button.json
├── Character/                 # 角色检测测试
│   ├── test_slot_detection.json
│   └── test_account_id.json
├── Donation/                  # 捐赠流程测试
│   ├── test_open_guild_ui.json
│   └── test_donation_flow.json
└── MaaEndTesting/             # 测试截图资源
    ├── Win32/
    │   └── Official_KR/
    │       ├── 角色选择/
    │       └── 公会界面/
    └── ADB/
```

### 6.2 测试用例格式

```json
{
    "configs": {
        "name": "公会捐赠按钮测试 (韩服-Win32)",
        "resource": "LostArk-KR-2560x1440",
        "controller": "KMBox-Default"
    },
    "cases": [
        {
            "name": "ESC菜单中的公会按钮",
            "image": "tests/MaaEndTesting/Win32/Official_KR/esc_menu_guild_button.png",
            "hits": ["GuildButton"]
        },
        {
            "name": "公会界面已打开",
            "image": "tests/MaaEndTesting/Win32/Official_KR/guild_ui_open.png",
            "hits": ["GuildDonationTab"]
        }
    ]
}
```

---

## 7. 迁移检查清单

### Phase 1: 结构重组 (低风险)
- [ ] 创建新目录结构
- [ ] 移动文件到新位置
- [ ] 创建兼容层 __init__.py
- [ ] 验证现有脚本仍可运行

### Phase 2: 配置外置 (中风险)
- [ ] 创建 `assets/interface.json`
- [ ] 将硬编码配置迁移到 JSON
- [ ] 实现配置加载器
- [ ] 测试配置读取

### Phase 3: Pipeline JSON 化 (中风险)
- [ ] 开发 YAML->JSON 转换工具
- [ ] 转换现有工作流
- [ ] 实现 Pipeline 执行器
- [ ] 验证执行结果一致

### Phase 4: 组件注册 (低风险)
- [ ] 实现注册表模式
- [ ] 将现有函数注册为自定义识别/动作
- [ ] 更新入口点使用注册表

### Phase 5: 测试迁移 (低风险)
- [ ] 重组测试目录
- [ ] 转换测试用例格式
- [ ] 验证测试通过

---

## 8. 保留的现有逻辑 (不要改动)

以下内容保持原样:

1. **KMBox 通信协议** (`ferrum_controller.py` 核心逻辑)
2. **OpenCV 模板匹配算法** (`vision_engine.py` 核心逻辑)
3. **角色检测网格算法** (`character_detector.py` 核心逻辑)
4. **公会捐赠流程** (`guild_donation.py` 步骤顺序)
5. **错误恢复策略** (三层恢复逻辑)
6. **ROI 坐标值** (2560x1440 固定坐标)

---

## 9. 新增能力 (通过结构改进获得)

1. **任务配置化**: 通过 `interface.json` 定义新任务
2. **Pipeline 复用**: 通用节点可在多个任务间共享
3. **自定义识别**: 通过注册表扩展识别能力
4. **测试标准化**: MaaEnd 风格的测试用例
5. **多分辨率准备**: 结构支持未来多分辨率扩展
6. **插件化**: 新模块可通过 `register.py` 自动加载

---

## 10. 参考资料

- MaaEnd 源码: `c:\Users\Akane\Desktop\IDE\Project\MaaEnd-1.20.0`
- MaaFramework 文档: https://maafw.com/
- 当前项目: `c:\Users\Akane\FerrumProject\LostarkGuildDonationBot`

---

*此文档为重构指导，不改变任何现有业务逻辑，仅进行结构规范化。*
