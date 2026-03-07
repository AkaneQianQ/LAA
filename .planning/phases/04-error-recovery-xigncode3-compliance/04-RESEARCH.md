# Phase 4 Research: Error Recovery & XIGNCODE3 Compliance

## 结论先行（给 Phase 4 规划者）
本阶段的关键不是“多做重试”，而是建立**可证明安全**的执行边界：
1. 错误恢复必须从“步骤失败”升级为“场景状态机恢复”（局部回退 -> 会话降级 -> 角色跳过）。
2. ACE/XIGNCODE3 合规必须从“约定”升级为“启动即校验 + 运行时审计 + 违规即拒绝”。
3. 所有恢复决策都要结构化落盘（JSONL），否则 ERR-04 无法闭环，也无法解释误恢复。

## 当前代码基线（与 Phase 4 直接相关）
- 已有：`wait_image` 超时、step 级 retry、workflow 默认重试间隔、稳定 2-hit 判定。
- 缺口：
  - 无错误分类（网络/UI/断线）与恢复策略路由。
  - 无“锚点回退”schema 与编译期校验。
  - 无结构化错误日志与截图策略。
  - 无 ACE fail-fast 合规检查、无输入审计层。
  - `ActionDispatcher` 仍包含本地截图 fallback（DXCam/PIL），但输入层是 mock controller；尚未接入硬件输入门面。

## Standard Stack
- 运行时与配置：现有 `pydantic v2 + YAML workflow + compile-time validation`（继续沿用，不新增 DSL）。
- 恢复编排：在现有 `WorkflowExecutor` 上增加 `RecoveryOrchestrator`（纯 Python，状态机驱动）。
- 错误日志：JSONL（`logs/errors/YYYY-MM-DD.jsonl`）+ 失败截图文件路径索引。
- ACE 合规门面：新增 `HardwareInputGateway`（唯一输入出口），下挂 Ferrum/KMBox provider。
- 合规校验：启动阶段 `ComplianceGuard`（环境能力探测 + 策略校验，失败即拒绝运行）。

## Architecture Patterns
- Pattern 1: Error Taxonomy + Strategy Map
  - 定义 `ErrorKind = NETWORK_LAG | UI_TIMEOUT | DISCONNECT | INPUT_POLICY_VIOLATION | UNKNOWN`。
  - `ExecutionError` 统一封装上下文（step_id, action_type, attempt, elapsed_ms, roi/template）。
  - `RecoveryStrategyMap[ErrorKind] -> RecoveryPlan`，禁止在 executor 中散落 if/else。

- Pattern 2: 分层恢复状态机（满足 ERR-01/02/03）
  - L1：步骤级重试（已存在，保留）。
  - L2：局部回退（跳回显式锚点 step）。
  - L3：会话级降级（终止当前 workflow run，标记角色失败原因并进入下一个角色）。
  - L4：熔断（同类错误连续 N 次，短路本角色，防止死循环）。

- Pattern 3: 显式锚点配置（配置驱动）
  - 在 schema 增加类似字段：`recovery.anchor: bool`、`recovery.on_timeout: <step_id>`、`recovery.max_escalations`。
  - compiler 校验：锚点必须可达；恢复跳转目标存在；禁止形成仅恢复分支的闭环。

- Pattern 4: ACE “唯一输入出口”
  - 任何 click/press/scroll 必须经过 `HardwareInputGateway`。
  - 禁止直接调用 OS 软件注入 API（pyautogui/win32 SendInput 等）。
  - policy 拒绝时直接抛 `INPUT_POLICY_VIOLATION` 并审计。

- Pattern 5: Timing Jitter Policy（满足 ACE-02）
  - 对 click/press/scroll 注入截断正态抖动（±20%，会话级 seed）。
  - `wait_image` 轮询周期不注入人类化抖动（避免破坏检测稳定性）。
  - 记录实际延时值到审计日志，支持复盘。

## Ferrum 文档约束（规划时必须显式纳入）
来源：Ferrum developer documentation（skill references）。
- API 选择：Windows 优先 Software API；Legacy API 已弃用，仅在受限场景使用。
- 串口协议：命令需正确 line terminator（建议 `\n` 或 `\r\n`）；Software API 有命令 echo + prompt 行为。
- 安全语义：存在 Hardware Override，按键/按下状态可能被用户硬件行为覆盖。
- 锁/回调：lock/callback 是有状态的，使用后必须有清理路径（防 stuck input）。
- KMBox Net 风格 API：文档中“强烈不建议”作为未来项目首选；Phase 4 规划应优先统一 KM API 路径。

## Don’t Hand-Roll
- 不手写新的工作流语言或复杂规则引擎；复用现有 schema/compiler 扩展字段。
- 不手写“花哨自适应恢复 AI”；Phase 4 只做可验证状态机策略。
- 不自定义二进制日志格式；坚持 JSONL + 固定核心字段。
- 不实现任何进程注入、内存读写、DLL 相关探测或控制逻辑（直接违背 ACE-03/04）。

## Common Pitfalls
- 误把 `wait_image` 超时都当网络问题：应先分型（UI_TIMEOUT vs NETWORK_LAG）。
- 恢复后不重新建立“已知稳定 UI 状态”：导致后续步骤在错误前提上执行。
- 抖动注入到轮询逻辑：会引入额外随机超时，降低可重复性。
- 只打控制台日志不落结构化文件：排障时无法做聚合分析。
- 合规只做文档承诺，不做代码层封禁：后续很容易被“临时快捷实现”破坏。
- 忘记 lock/callback 清理：会造成输入卡死、误触发或状态漂移。

## 需求到实现映射（规划模板）
- ERR-01（网络卡顿恢复）
  - 检测信号：关键步骤连续超时 + 网络敏感锚点缺失。
  - 动作：局部回退到最近锚点；超阈值后角色熔断并跳过。
- ERR-02（UI 加载超时）
  - 检测信号：`wait_image(appear/disappear)` timeout。
  - 动作：step retry -> anchor rollback -> session downgrade。
- ERR-03（客户端断线恢复）
  - 检测信号：断线标志图出现或关键 UI 全部缺失。
  - 动作：记录 + 结束当前角色，不强制重启客户端（遵循已定决策）。
- ERR-04（错误日志）
  - 字段最小集：`ts, phase, step_id, error_kind, message, attempt, account_id/hash, screenshot_path, context`。
- ACE-01
  - 所有输入调用路径统一收口到 `HardwareInputGateway`；启动时握手失败即拒绝执行。
- ACE-02
  - 随机化策略固定在输入动作层，分布与参数可配置且默认 ±20%。
- ACE-03/04
  - 增加静态扫描或运行时守卫：禁止内存读写/注入类依赖与调用。

## Planning Unknowns（先补齐再拆 Plan）
- 网络卡顿的可观测信号最终定义是什么（仅视觉症状 vs 额外心跳）？
- “最近稳定锚点”选择规则是手工配置优先，还是允许 fallback 到全局锚点？
- 截图留存策略（分辨率、压缩、留存天数）与磁盘上限怎么定？
- 会话级 seed 是否需要写入日志以支持可复现实验？
- 合规守卫要做“import 黑名单”还是“运行时调用封禁”，或两者都做？

## 建议的计划拆分（供 gsd-plan-phase 直接使用）
1. Schema & Compiler 扩展
- 新增 recovery/anchor/audit 字段与语义校验。

2. Error Taxonomy 与 RecoveryOrchestrator
- 实现错误分型、升级策略、熔断计数与角色级跳过。

3. Structured Logging & Evidence
- JSONL logger、失败截图管理、上下文字段标准化。

4. ACE Compliance Guard
- 启动 fail-fast（硬件握手/能力探测/策略检查）与运行时输入审计。

5. Timing Jitter Engine
- 截断正态抖动实现（会话 seed），仅作用于输入动作。

6. 集成测试与回归
- 覆盖 ERR-01..04、ACE-01..04 的正反用例，验证不破坏 Phase 3 wait 语义。

## Code Examples
```python
# Error classification contract (example)
from enum import Enum
from dataclasses import dataclass

class ErrorKind(str, Enum):
    NETWORK_LAG = "network_lag"
    UI_TIMEOUT = "ui_timeout"
    DISCONNECT = "disconnect"
    INPUT_POLICY_VIOLATION = "input_policy_violation"
    UNKNOWN = "unknown"

@dataclass
class ErrorContext:
    phase: str
    step_id: str
    action_type: str
    attempt: int
    account_id: str | None
    screenshot_path: str | None
    detail: dict
```

```python
# Single input egress guard (example)
class HardwareInputGateway:
    def __init__(self, provider, policy, audit_logger):
        self.provider = provider
        self.policy = policy
        self.audit = audit_logger

    def click(self, x: int, y: int) -> None:
        if not self.policy.allow("click", {"x": x, "y": y}):
            self.audit.log_violation("click", {"x": x, "y": y})
            raise RuntimeError("INPUT_POLICY_VIOLATION")
        self.provider.click(x, y)
```

```python
# JSONL error log shape (example)
{
  "ts": "2026-03-07T21:30:15.123Z",
  "phase": "04",
  "step_id": "wait_guild_ui",
  "error_kind": "ui_timeout",
  "attempt": 2,
  "account": "a1b2...",
  "screenshot_path": "logs/screenshots/2026-03-07/err_00012.webp",
  "context": {"image": "guild_flag_mark.png", "roi": [100, 200, 500, 700]}
}
```

## 验收与验证建议（计划阶段就锁定）
- 单测：
  - 错误分型准确性（timeout/disconnect/policy_violation）。
  - 恢复升级链路（L1->L2->L3）与熔断阈值。
  - 抖动分布边界（不越 ±20%，可复现实验 seed）。
- 集成：
  - 模拟连续 timeout，验证锚点回退与角色跳过行为。
  - 模拟硬件握手失败，验证 fail-fast 拒绝启动。
  - 验证日志落盘字段完整性与截图仅失败时保存。
- 合规回归：
  - 扫描代码路径，确保动作仅通过 `HardwareInputGateway`。
  - 确认不存在内存访问/注入类依赖与调用。

## 规划质量门槛（Definition of Ready for Plan）
- 已确定错误分型规则与每类恢复上限。
- 已确定锚点 schema 字段与 compiler 校验规则。
- 已确定合规守卫的“启动检查项 + 运行时审计项”。
- 已确定日志字段契约和截图留存策略。
- 已确定测试矩阵覆盖 ERR-01..04 / ACE-01..04。
