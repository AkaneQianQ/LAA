# Quick Task 6: MAA Refactor Phase 1 - 目录结构重组

**Mode:** quick-full
**Description:** 遵循 MAA_REFACTOR_GUIDE.md 执行 Phase 1 目录结构重组
**Date:** 2026-03-09

---

## must_haves

### Truths
- 所有代码逻辑保持不变，仅移动文件位置
- 原有导入路径通过 __init__.py 转发保持兼容
- 创建 MaaEnd 风格的 agent/py-service/ 目录结构

### Artifacts
- `agent/py-service/pkg/` 目录及子目录
- `agent/py-service/modules/` 目录及子目录
- `assets/resource/` 目录
- 兼容层 `core/__init__.py` 和 `modules/__init__.py`

### Key Links
- MAA_REFACTOR_GUIDE.md Phase 1 章节
- QUICK_REFERENCE.md 目录映射表
- REFACTOR_EXAMPLES.md 代码示例

---

## Task 1: 创建新目录结构

**Files:** N/A (directory creation)

**Action:**
```bash
# 创建 pkg 子目录
mkdir -p agent/py-service/pkg/ferrum
mkdir -p agent/py-service/pkg/vision
mkdir -p agent/py-service/pkg/workflow
mkdir -p agent/py-service/pkg/recovery
mkdir -p agent/py-service/pkg/common

# 创建 modules 子目录
mkdir -p agent/py-service/modules/character
mkdir -p agent/py-service/modules/login
mkdir -p agent/py-service/modules/donation

# 创建资源目录
mkdir -p assets/resource/pipeline
mkdir -p assets/resource/image
mkdir -p assets/tasks

# 创建工具目录
mkdir -p tools
```

**Verify:**
```bash
ls -la agent/py-service/pkg/
ls -la agent/py-service/modules/
ls -la assets/resource/
```

**Done:** 所有目录结构创建完成

---

## Task 2: 移动核心文件到 pkg/

**Files:**
- `core/ferrum_controller.py` → `agent/py-service/pkg/ferrum/controller.py`
- `core/vision_engine.py` → `agent/py-service/pkg/vision/engine.py`
- `core/workflow_bootstrap.py` → `agent/py-service/pkg/workflow/bootstrap.py`
- `core/workflow_compiler.py` → `agent/py-service/pkg/workflow/compiler.py`
- `core/workflow_executor.py` → `agent/py-service/pkg/workflow/executor.py`
- `core/workflow_runtime.py` → `agent/py-service/pkg/workflow/runtime.py`
- `core/workflow_schema.py` → `agent/py-service/pkg/workflow/schema.py`
- `core/error_recovery.py` → `agent/py-service/pkg/recovery/orchestrator.py`
- `core/database.py` → `agent/py-service/pkg/common/database.py`
- `core/parallel_matcher.py` → `agent/py-service/pkg/vision/parallel_matcher.py`
- `core/perceptual_hash.py` → `agent/py-service/pkg/vision/perceptual_hash.py`

**Action:**
使用 `git mv` 移动文件保持版本历史

**Verify:**
```bash
git status  # 确认是 rename 操作
ls -la agent/py-service/pkg/ferrum/
ls -la agent/py-service/pkg/vision/
ls -la agent/py-service/pkg/workflow/
```

**Done:** 所有核心文件移动到 pkg/ 目录

---

## Task 3: 移动业务模块到 modules/

**Files:**
- `modules/character_detector.py` → `agent/py-service/modules/character/detector.py`
- `modules/auto_login.py` → `agent/py-service/modules/login/workflow.py`
- `modules/guild_donation.py` → `agent/py-service/modules/donation/workflow.py`

**Action:**
使用 `git mv` 移动文件

**Verify:**
```bash
git status
ls -la agent/py-service/modules/character/
ls -la agent/py-service/modules/login/
ls -la agent/py-service/modules/donation/
```

**Done:** 所有业务模块移动到 modules/ 目录

---

## Task 4: 移动资源文件

**Files:**
- `assets/*.bmp` → `assets/resource/image/`
- `config/workflows/*.yaml` → `assets/tasks/`

**Action:**
```bash
# 移动图片资源
mv assets/*.bmp assets/resource/image/

# 移动工作流配置
mv config/workflows/*.yaml assets/tasks/
```

**Verify:**
```bash
ls -la assets/resource/image/
ls -la assets/tasks/
```

**Done:** 所有资源文件移动完成

---

## Task 5: 创建 __init__.py 文件

**Files:**
- `agent/py-service/__init__.py`
- `agent/py-service/pkg/__init__.py`
- `agent/py-service/pkg/ferrum/__init__.py`
- `agent/py-service/pkg/vision/__init__.py`
- `agent/py-service/pkg/workflow/__init__.py`
- `agent/py-service/pkg/recovery/__init__.py`
- `agent/py-service/pkg/common/__init__.py`
- `agent/py-service/modules/__init__.py`
- `agent/py-service/modules/character/__init__.py`
- `agent/py-service/modules/login/__init__.py`
- `agent/py-service/modules/donation/__init__.py`
- `core/__init__.py` (兼容层)
- `modules/__init__.py` (兼容层)

**Action:**
创建所有 __init__.py 文件，使目录成为 Python 包

**Verify:**
```bash
python -c "import agent.py_service.pkg.ferrum.controller"
python -c "import agent.py_service.modules.character.detector"
```

**Done:** 所有 __init__.py 文件创建完成

---

## Task 6: 创建兼容层转发

**Files:**
- `core/__init__.py`
- `modules/__init__.py`

**Action:**
创建兼容层，使旧导入路径仍然有效:

```python
# core/__init__.py
"""兼容层 - 转发到新位置"""
from agent.py_service.pkg.ferrum.controller import FerrumController
from agent.py_service.pkg.vision.engine import VisionEngine
from agent.py_service.pkg.workflow.bootstrap import WorkflowBootstrap
from agent.py_service.pkg.workflow.executor import WorkflowExecutor
from agent.py_service.pkg.workflow.compiler import WorkflowCompiler
from agent.py_service.pkg.workflow.runtime import ActionDispatcher
from agent.py_service.pkg.recovery.orchestrator import RecoveryOrchestrator
from agent.py_service.pkg.common.database import Database
```

```python
# modules/__init__.py
"""兼容层 - 转发到新位置"""
from agent.py_service.modules.character.detector import CharacterDetector
from agent.py_service.modules.login.workflow import AutoLoginWorkflow
from agent.py_service.modules.donation.workflow import GuildDonationWorkflow
```

**Verify:**
```bash
python -c "from core import FerrumController; print('OK')"
python -c "from modules import CharacterDetector; print('OK')"
```

**Done:** 兼容层创建完成，旧导入路径仍然有效

---

## Task 7: 更新主入口文件位置

**Files:**
- `main.py` → `agent/py-service/main.py`
- `gui_launcher.py` (保持原地，但更新导入)

**Action:**
1. 复制 main.py 到新位置
2. 更新新位置的导入语句
3. 保持原 gui_launcher.py 更新导入

**Verify:**
```bash
python -c "import agent.py_service.main"
python -c "import gui_launcher"
```

**Done:** 主入口文件处理完成

---

## Task 8: 创建 register.py 注册表

**Files:**
- `agent/py-service/register.py`

**Action:**
创建 MaaEnd 风格的组件注册表:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组件注册表 - 类似 MaaEnd 的 agent/go-service/register.go
所有自定义识别和动作在此注册
"""

from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass

# 全局注册表
_custom_recognitions: Dict[str, Callable] = {}
_custom_actions: Dict[str, Callable] = {}

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
        """注册自定义识别器"""
        _custom_recognitions[name] = func
        print(f"[注册] 识别器: {name}")
        return func

    @staticmethod
    def register_action(name: str, func: Callable) -> Callable:
        """注册自定义动作"""
        _custom_actions[name] = func
        print(f"[注册] 动作: {name}")
        return func

    @staticmethod
    def get_recognition(name: str) -> Optional[Callable]:
        return _custom_recognitions.get(name)

    @staticmethod
    def get_action(name: str) -> Optional[Callable]:
        return _custom_actions.get(name)

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
```

**Verify:**
```bash
python -c "from agent.py_service.register import Registry, recognition, action; print('OK')"
```

**Done:** 注册表创建完成

---

## Task 9: 验证导入完整性

**Action:**
运行验证脚本检查所有导入:

```bash
python -c "
# 测试新路径导入
from agent.py_service.pkg.ferrum.controller import FerrumController
from agent.py_service.pkg.vision.engine import VisionEngine
from agent.py_service.pkg.workflow.executor import WorkflowExecutor
from agent.py_service.modules.character.detector import CharacterDetector
from agent.py_service.register import Registry

# 测试旧路径兼容层
from core import FerrumController as FC1
from modules import CharacterDetector as CD1

print('All imports OK!')
"
```

**Verify:** 无导入错误

**Done:** 所有导入验证通过

---

## Task 10: 提交 Phase 1 完成

**Action:**
```bash
git add -A
git commit -m "refactor(maa-phase1): 目录结构重组为 MaaEnd 风格

- 创建 agent/py-service/pkg/ 和 modules/ 目录结构
- 移动核心文件到 pkg/{ferrum,vision,workflow,recovery,common}/
- 移动业务模块到 modules/{character,login,donation}/
- 移动资源到 assets/resource/
- 创建兼容层保持旧导入路径有效
- 创建 register.py 组件注册表"
```

**Verify:**
```bash
git log -1 --oneline
git status
```

**Done:** Phase 1 完成并提交

---

## Summary

Phase 1 完成目标:
1. ✅ 创建完整的 MaaEnd 风格目录结构
2. ✅ 移动所有文件到新位置（保持 git 历史）
3. ✅ 创建兼容层保持向后兼容
4. ✅ 创建组件注册表框架
5. ✅ 验证所有导入正常

Next: Phase 2 - 配置外置 (interface.json)
