# Phase 3: Intelligent Wait System - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

在现有自动化流程中，用图像状态驱动的智能等待替换硬编码/固定时长等待，覆盖出现等待与消失等待、超时控制、以及超时后的自动重试。  
本阶段聚焦“等待机制的行为升级”，不新增与等待无关的新功能能力。

</domain>

<decisions>
## Implementation Decisions

### 等待条件模型
- 智能等待优先采用统一的 `image` 条件语义。
- 等待目标状态明确支持两类：`appear` 与 `disappear`。
- 判定稳定性采用“连续 2 次命中/满足”才通过，避免单帧抖动误判。
- 轮询策略采用“默认固定间隔 + 步骤可配置覆盖”。
- 等待超时按步骤失败处理，交由现有 `step.retry` 机制执行重试。

### Timeout 与重试策略
- 默认超时采用“按动作/场景分级默认”，而不是单一全局固定值。
- 重试归属沿用 `step.retry`，不引入并行的新重试体系。
- 重试间隔采用“固定短间隔 + 可覆盖”策略。
- 达到最大重试后，流程按失败终止（保持 stop-on-failure 基线）。

### YAML 配置形状
- 新增专用智能等待动作（如 `wait_image`），与现有 `wait(duration_ms)` 分离建模。
- 等待方向使用显式字段表达（如 `state: appear|disappear`）。
- 超时/轮询采用“全局默认 + 步骤可覆盖”的优先级模型。
- 对既有 `wait(duration_ms)` 采用渐进迁移：新旧并存，逐步替换。

### Claude's Discretion
- 分级默认超时的具体档位与命名（如 short/medium/long 或按场景命名）。
- 智能等待动作的精确字段命名与 schema 细节（在不违背已锁定语义前提下）。
- 轮询与重试默认值的具体数值。

</decisions>

<specifics>
## Specific Ideas

- 目标是让等待行为“由 UI 实际状态驱动”，而不是依赖猜测性睡眠时间。
- 优先保证语义清晰与迁移平滑，避免一次性大改导致回归风险。
- 配置层要求可读、可维护，并与现有工作流定义风格保持一致。

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/workflow_executor.py`: 已有 `step.retry` 与 stop-on-failure 语义，可直接承接超时失败后的重试/终止流程。
- `core/workflow_runtime.py` 的 `ConditionEvaluator`: 已有图像条件评估入口，可复用于智能等待的图像状态判定。
- `core/vision_engine.py`: 现有模板匹配与 ROI 能力可作为等待判定底层。
- `config/workflows/guild_donation.yaml`: 现有工作流样例可作为新旧 wait 语义共存与迁移样板。

### Established Patterns
- 工作流执行采用显式步骤与路由（`next` / `on_true` / `on_false`）的确定性模型。
- 配置 schema 使用严格校验（Pydantic），适合为新等待动作增加明确约束。
- 现有项目对“失败即停”行为已有基线认知，应保持一致性。

### Integration Points
- 智能等待动作与字段扩展需落在 `core/workflow_schema.py`（配置契约）与 `core/workflow_runtime.py`（运行时派发/判定）。
- 超时触发失败并复用 `step.retry` 的行为需与 `core/workflow_executor.py` 对齐。
- 工作流示例与测试需在 `config/workflows/`、`tests/config_system/` 中同步体现迁移路径。

</code_context>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 03-intelligent-wait-system*
*Context gathered: 2026-03-07*
