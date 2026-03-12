# Phase 详细执行步骤

> 本文档包含 eval-task-batch-builder 流水线各 Phase 的完整执行细节。
> 概述见 [../SKILL.md](../SKILL.md)。

---

## Phase 1: 准备（用户 session）

### 1.1 对齐候选清单

与用户确认要构造的测例范围：

1. 读取 CASE_REGISTRY.md，筛选状态为 📋 候选 的条目
2. 列出清单，让用户确认：
   - 哪些要构造，哪些跳过
   - 难度定级是否合理
   - 是否有需要合并的候选
3. 基本检查：
   - 每个候选的来源 session 文件是否存在
   - session 文件是否可读、内容非空
   - 如果 session 不存在，标记并与用户讨论

### 1.2 分配测例编号

- 编号格式: `task-{NNN}`（三位数字，从已有最大编号 +1 开始）
- 编号连续，不跳号
- 记录编号映射到 state.json

### 1.3 生成执行计划

产出 DESIGN.md：
- 任务总量和难度分布
- 并行策略（Worker 并发数）
- 预估时间和资源
- 风险点

产出 PIPELINE_STATE.md（初始版本）。

### 1.4 生成 Prompt 模板

基于 eval-task-builder 的规范，生成：
- DISPATCHER_PROMPT.md（调度 session 指令）
- WORKER_PROMPT_TEMPLATE.md（构造模式 Worker 模板）
- QA_WORKER_PROMPT_TEMPLATE.md（质检模式 Worker 模板）

---

## Phase 2: 批量构造（调度 session → Worker spawn）

### 2.1 编排模式

遵循 `batch-orchestrator` 的两层编排 + 用户 session watchdog：

```
用户 session
  │  与用户讨论，产出设计文档和 Prompt
  │
  ├── 调度 session（一个，串行执行调度逻辑）
  │     │  读取 DISPATCHER_PROMPT.md
  │     │  通过 spawn 启动 Worker subagent（滑动窗口并行）
  │     │
  │     ├── Worker subagent (task-003)  ← 构造模式
  │     ├── Worker subagent (task-004)
  │     └── Watchdog subagent（调度级，监控 Worker 超时）
  │
  └── User Watchdog subagent ← sleep N 分钟后回报，触发用户 session 检查
```

**⚠️ 关键约束**：
- **调度 session 串行，Worker 并行**——不要 spawn 多个调度 subagent 并行
- **Worker subagent 没有 spawn 工具**——Worker 不能创建子 session 或嵌套子任务
- **User Watchdog 自动接力**——调度 session 迭代耗尽时，user watchdog 回报触发用户 session 自动启动新调度

### 2.2 调度 session 职责

**调度 session 只做调度，不做构造**。

职责：
1. 读取 state.json，找到 status=pending 的任务
2. 通过 spawn 启动 Worker subagent（滑动窗口，并发 3~5 个）
3. 被动接收 Worker 回报（spawn 完成后自动回报）
4. 更新 state.json
5. 异常恢复（follow_up）
6. 启动 watchdog subagent 做超时兜底

不做：
- 不自己构造测例（即使是 easy 任务）
- 不修改 CASE_REGISTRY.md
- 不做质检
- 不 spawn 调度 subagent（调度本身串行执行）

### 2.3 Worker subagent 执行

每个 Worker subagent 收到的消息包含：
- 候选信息（ID、名称、session 路径、难度、描述）
- 分配的 task 编号
- 工作目录
- 指令：读取 eval-task-builder SKILL.md，按构造模式执行

Worker 完成后写入 `reports/task-{NNN}.json`。

### 2.4 异常处理

| 情况 | 处理方式 |
|------|---------|
| Worker 卡住（长时间无回报） | watchdog 检测 → 调度 session follow_up |
| Worker 报错退出 | 记录错误，标记 task 为 failed，继续下一个 |
| 调度 session 迭代耗尽 | User Watchdog 触发 → 用户 session 启动新调度 session |
| Worker 标记 needs_review | 记录到 state.json，Phase 3 汇总处理 |

---

## Phase 3: 构造复盘（用户 session）

### 3.1 汇总构造结果

1. 读取所有 reports/task-{NNN}.json
2. 统计: success / needs_review / failed
3. 汇总所有 Worker 记录的 decisions（决策点）
4. 汇总所有 issues
5. 生成 RETROSPECTIVE.md

### 3.2 与人工交互

将以下内容呈现给用户：
1. 总体统计（成功率、耗时、问题数）
2. 需要 review 的 task 列表及问题描述
3. 所有 Worker 的决策点汇总（需要人工确认）
4. 发现的共性问题
5. 建议的质检重点

等待用户反馈，记录到 `human_feedback/build_feedback.md`。

### 3.3 更新状态

根据人工反馈：
- 确认的 needs_review → 安排修复（加入 Phase 4 质检计划）
- 确认的决策点 → 记录到 DESIGN.md
- 更新 PIPELINE_STATE.md

---

## Phase 4: 批量质检（调度 session → QA Worker spawn）

### 4.1 制定质检计划

输入：
- 构造阶段的 RETROSPECTIVE.md
- 人工反馈 human_feedback/build_feedback.md
- eval-task-builder 的质检维度（D1~D9）

输出：
- QA 任务清单（哪些 task 需要质检、质检类别、重点关注维度）
- QA_WORKER_PROMPT_TEMPLATE.md（质检 Worker 模板）

**质检分类**：

| 类别 | 说明 | 适用范围 |
|------|------|---------|
| A 类（标准质检） | 全维度检查 + verify dry-run | medium/hard/expert |
| E 类（easy 实施） | 全维度检查 + 实际执行 + verify | easy 任务 |
| B 类（无 verify） | 全维度检查，跳过 verify | 纯 LLM 评分的 task |
| C/D 类（特殊） | session 定位/修正等特殊处理 | 有已知问题的 task |

### 4.2 质检编排

与 Phase 2 相同的编排模式，但 Worker 使用质检模式：

```
调度 session（一个，串行执行调度逻辑）
  ├── QA Worker subagent (task-003)  ← 质检模式
  ├── QA Worker subagent (task-004)
  └── Watchdog subagent
```

每个 QA Worker 收到的消息包含：
- 待质检的 task 信息
- 来源 session 路径
- 人工反馈（如有）
- 质检类别和重点维度
- 指令：读取 eval-task-builder SKILL.md，按质检模式执行

QA Worker 完成后写入 `qa_reports/task-{NNN}_qa.json`。

### 4.3 质检 Worker 的修复权限

- **小问题直接修复**：typo、缺失字段、路径不一致、verify 脚本语法错误
- **大问题记录不修复**：initial_state 缺失关键文件、query 偏离原始意图、需要重新构造
- 所有修复都记录在 qa_report 的 `fixes_applied` 字段中

---

## Phase 5: 质检复盘（用户 session）

### 5.1 汇总质检结果

1. 读取所有 qa_reports/task-{NNN}_qa.json
2. 统计: pass / fixed / needs_fix
3. 按维度汇总发现（哪些维度问题最多）
4. 生成质检报告

### 5.2 与人工交互

呈现：
1. 总体质检结果（通过率、修复数、遗留问题数）
2. needs_fix 的 task 列表及问题描述
3. Worker 自动修复的汇总（需要人工确认修复是否合理）
4. 共性问题分析
5. 是否需要额外质检轮次的建议

### 5.3 决定后续

- 遗留问题少且可手动修复 → 人工修复后结束
- 遗留问题多 → 进入 Phase 6（迭代质检修复，重复 Phase 4-5）
- 更新 PIPELINE_STATE.md
