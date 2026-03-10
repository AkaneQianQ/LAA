# MaaEnd 重构速查表

**快速参考指南 - 用于另一个 Claude Code 进行重构**

---

## 📁 目录映射 (必须遵循)

| 当前路径 | 新路径 | 操作 |
|---------|-------|------|
| `core/ferrum_controller.py` | `agent/py-service/pkg/ferrum/controller.py` | 移动 + 包装 |
| `core/vision_engine.py` | `agent/py-service/pkg/vision/engine.py` | 移动 |
| `core/workflow_*.py` | `agent/py-service/pkg/workflow/` | 拆分移动 |
| `core/error_recovery.py` | `agent/py-service/pkg/recovery/orchestrator.py` | 移动 |
| `modules/character_detector.py` | `agent/py-service/modules/character/detector.py` | 移动 |
| `modules/auto_login.py` | `agent/py-service/modules/login/workflow.py` | 移动 |
| `modules/guild_donation.py` | `agent/py-service/modules/donation/workflow.py` | 移动 |
| `config/workflows/*.yaml` | `assets/tasks/*.json` | 转换格式 |
| `assets/*.bmp` | `assets/resource/image/*.bmp` | 移动 |
| `main.py` | `agent/py-service/main.py` | 移动 |

---

## 🔑 关键设计模式

### 1. 注册表模式 (必须实现)

```python
# agent/py-service/register.py
from typing import Dict, Callable

_custom_recognitions: Dict[str, Callable] = {}
_custom_actions: Dict[str, Callable] = {}

def register_recognition(name: str, func: Callable):
    _custom_recognitions[name] = func

def register_action(name: str, func: Callable):
    _custom_actions[name] = func
```

### 2. 装饰器注册 (推荐)

```python
from .register import register_recognition, register_action

@register_recognition("CharacterSlotDetection")
def detect_slots(context: dict) -> dict:
    # 原有逻辑
    pass

@register_action("SwitchCharacter")
def switch_char(context: dict):
    # 原有逻辑
    pass
```

### 3. Pipeline JSON 结构

```json
{
    "NodeName": {
        "desc": "节点描述",
        "recognition": {
            "type": "TemplateMatch",
            "param": {
                "template": "image/button.png",
                "roi": [x, y, w, h],
                "threshold": 0.8
            }
        },
        "action": "Click",
        "next": ["NextNode"],
        "on_error": ["ErrorNode"]
    }
}
```

---

## 🔄 YAML → JSON 转换规则

| YAML 类型 | JSON 结构 | 示例 |
|-----------|----------|------|
| `press: esc` | `"action": {"type": "KeyPress", "param": {"key": "esc"}}` | `{"type": "KeyPress", "param": {"key": "esc"}}` |
| `click: [x, y]` | `"action": {"type": "Click", "param": {"target": [x, y]}}` | `{"type": "Click", "param": {"target": [100, 200]}}` |
| `click_detected` | `recognition + action` | `{"recognition": {...}, "action": "Click"}` |
| `wait_image` | `recognition + timeout` | `{"recognition": {...}, "timeout": 5000}` |

---

## 🚫 保持不变的代码

**以下内容严禁修改，只能移动位置：**

1. **KMBox 通信协议** - `ferrum_controller.py` 核心逻辑
2. **OpenCV 模板匹配** - `vision_engine.py` 核心逻辑
3. **角色检测算法** - `character_detector.py` 检测逻辑
4. **捐赠流程步骤** - `guild_donation.py` 步骤顺序
5. **ROI 坐标值** - 所有 2560x1440 坐标
6. **错误恢复逻辑** - 三层恢复策略

---

## ✅ 新增文件清单

### 必须创建
- [ ] `agent/py-service/register.py` - 组件注册表
- [ ] `agent/py-service/main.py` - 服务入口
- [ ] `assets/interface.json` - 主配置
- [ ] `agent/py-service/pkg/__init__.py`
- [ ] `agent/py-service/modules/__init__.py`

### 每个模块必须创建
- [ ] `modules/{name}/__init__.py`
- [ ] `modules/{name}/register.py` - 模块注册入口

### 可选但推荐
- [ ] `agent/py-service/pkg/common/nodes.py` - 通用节点
- [ ] `tools/convert_yaml_to_pipeline.py` - 转换工具

---

## 🧪 验证命令

```bash
# 1. 验证目录结构
ls agent/py-service/pkg/
ls agent/py-service/modules/

# 2. 验证配置
python -c "import json; json.load(open('assets/interface.json'))"

# 3. 验证导入
python -c "from agent.py_service.register import Registry"

# 4. 验证 Pipeline
python -c "from agent.py_service.pkg.workflow.executor import PipelineExecutor"

# 5. 完整测试
python agent/py-service/main.py --test
```

---

## 📋 重构顺序

```
Phase 1: 创建目录结构 (低风险)
├── mkdir -p agent/py-service/pkg/{ferrum,vision,workflow,recovery,common}
├── mkdir -p agent/py-service/modules/{character,login,donation}
├── mkdir -p assets/resource/{pipeline,image}
└── mkdir -p assets/tasks

Phase 2: 移动核心文件 (中风险)
├── mv core/ferrum_controller.py → agent/py-service/pkg/ferrum/controller.py
├── mv core/vision_engine.py → agent/py-service/pkg/vision/engine.py
├── mv modules/character_detector.py → agent/py-service/modules/character/detector.py
└── ... (其他文件)

Phase 3: 创建包装层 (中风险)
├── 创建 register.py
├── 创建 __init__.py 转发
├── 创建 interface.json
└── 测试导入是否正常

Phase 4: 转换配置 (高风险)
├── YAML → JSON Pipeline 转换
├── 测试 Pipeline 执行
└── 验证功能一致

Phase 5: 完善 (低风险)
├── 添加通用节点
├── 完善测试
└── 文档更新
```

---

## 🔧 常见问题

### Q: 原有导入失效了？
**A:** 在旧位置创建转发文件 `__init__.py`:
```python
# core/__init__.py
from agent.py_service.pkg.ferrum.controller import FerrumController
from agent.py_service.pkg.vision.engine import VisionEngine
```

### Q: Pipeline JSON 不执行？
**A:** 检查:
1. JSON 格式有效
2. 入口节点名称正确
3. next 节点存在
4. 识别器已注册

### Q: 自定义识别器不工作？
**A:** 检查:
1. 装饰器 `@register_recognition()` 已应用
2. `register_all_modules()` 已调用
3. 名称与 Pipeline 中一致

---

## 📚 参考文件

| 文件 | 用途 |
|------|------|
| `MAA_REFACTOR_GUIDE.md` | 完整迁移指南 |
| `REFACTOR_EXAMPLES.md` | 详细代码示例 |
| `QUICK_REFERENCE.md` | 本速查表 |
| `../MaaEnd/.planning/codebase/*.md` | MaaEnd 结构参考 |

---

**记住：只改结构，不改逻辑！**
