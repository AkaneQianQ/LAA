# Phase 4: Error Recovery & XIGNCODE3 Compliance - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

实现网络/界面/断线场景的自动恢复能力，并建立 ACE 合规的输入与时序约束。范围仅限于当前流程的恢复与合规保障，不新增业务能力。

</domain>

<decisions>
## Implementation Decisions

### Recovery Strategy
- `wait_image` 超时且步骤重试耗尽后：采用“步骤级重试后局部回退”。
- 稳定锚点通过工作流显式标注（配置层可调），不采用纯动作类型自动推断。
- 同一错误场景连续恢复失败达到 3 次后，升级为会话级恢复策略。
- 断线/掉线场景：记录错误并跳过当前角色，不强制重启客户端。

### ACE Timing Policy
- 随机时序覆盖点击/按键/滚轮，不干扰 `wait_image` 轮询机制。
- 随机幅度采用固定 ±20%，与 Phase 4 验收标准一致。
- 抖动分布采用截断正态分布（多数值靠近基准，少量偏离）。
- 合规约束在启动阶段执行 fail-fast 校验，不通过则拒绝运行。

### Error Logging Shape
- 采用“结构化文件 + 控制台摘要”双通道日志。
- 错误文件格式使用 JSONL。
- 字段策略：核心字段固定（时间、phase、step、error、retry、account、screenshot_path）+ `context` 可扩展字段。
- 仅在失败时保存截图，并按天轮转管理。

### ACE Boundary & Audit
- 明确严格合规边界：仅允许 KMBox 硬件输入；禁止软件模拟输入、进程注入、内存读写类路径。
- 启动前执行硬件握手自检与能力探测，失败即阻止任务启动。
- 随机时序采用“会话级随机种子”。
- 检测到不合规输入请求时：拒绝执行并写入审计日志。

### Claude's Discretion
- 局部回退“稳定锚点”字段名与 schema 细节（在不改变“显式标注锚点”决策前提下）。
- JSONL 日志目录结构、文件轮转阈值、截图压缩格式。
- 截断正态分布的具体参数（均值/方差/截断上下界）实现细节。

</decisions>

<specifics>
## Specific Ideas

- 用户明确要求后续讨论使用中文。
- 用户提出“避免 python 软件鼠标交互被 ACE 判定”的关注点，已转化为“严格合规边界 + 审计”实现约束。

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/workflow_executor.py`：已有 `step.retry` 与 `retry_interval_ms` 语义，可作为恢复重试基础。
- `core/workflow_runtime.py`：已有 `wait_image` 智能轮询与超时机制，可作为恢复触发信号来源。
- `config/workflows/guild_donation.yaml`：已配置多处 `wait_image`，适合扩展锚点与恢复分支。

### Established Patterns
- 现有执行引擎为“编译后工作流 + 显式 step 路由”；新增恢复策略应优先走配置驱动。
- 项目已有 fail-fast 倾向（配置加载/编译出错即失败），适合 ACE 启动校验。
- 当前日志能力偏弱（以异常/打印为主），需要补结构化日志层满足 ERR-04。

### Integration Points
- `core/workflow_schema.py`：扩展锚点、恢复策略、审计相关字段。
- `core/workflow_compiler.py`：增加新增字段的语义校验。
- `core/workflow_executor.py` / `core/workflow_runtime.py`：实现恢复决策、错误分级、审计事件上报。
- `config/workflows/guild_donation.yaml`：标注锚点并接入恢复链路。

</code_context>

<deferred>
## Deferred Ideas

- None - discussion stayed within phase scope.

</deferred>

---

*Phase: 04-error-recovery-xigncode3-compliance*
*Context gathered: 2026-03-07*