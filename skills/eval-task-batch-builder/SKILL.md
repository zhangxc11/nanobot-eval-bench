---
name: eval-task-batch-builder
description: eval-bench 批量测例构造与质检。基于 batch-orchestrator (spawn 两层模式) + eval-task-builder 领域逻辑，完成从候选清单到质检通过的完整流水线。支持可重入恢复。
---

# eval-task-batch-builder — 批量测例构造与质检

> 基于 `batch-orchestrator` 的两层编排（调度 session → Worker spawn），
> 特化 eval 测例的批量构造和质检。整个流水线支持可重入恢复。

## 1. 概述

### 依赖

| Skill | 用途 |
|-------|------|
| `batch-orchestrator` | 两层编排（调度 session + spawn Worker）、滑动窗口并发、watchdog 兜底 |
| `eval-task-builder` | 单个测例的构造流程、质检维度和策略 |

### 流水线总览

```
Phase 1: 准备（用户 session）
  ├── 对齐候选清单、分配编号、生成执行计划和 Prompt 模板

Phase 2: 批量构造（调度 session → Worker spawn）
  └── Worker 使用 eval-task-builder 构造模式

Phase 3: 构造复盘（用户 session）
  ├── 汇总结果 → 生成复盘报告 → 与用户交互获取反馈

Phase 4: 批量质检（调度 session → QA Worker spawn）
  └── Worker 使用 eval-task-builder 质检模式

Phase 5: 质检复盘 + 修复（用户 session）
  ├── 汇总质检发现 → 人工确认 → 决定是否迭代

(可选) Phase 6+: 重复 Phase 4-5 直到质量达标
```

### 编排架构

```
用户 session ─── 准备 / 复盘 / 人工交互
     │
     ├── 调度 session ─── spawn Worker、接收回报、状态更新
     │     ├── Worker subagent (task-003)  ← 构造或质检
     │     ├── Worker subagent (task-004)
     │     └── Watchdog subagent（超时兜底）
     │
     └── User Watchdog subagent ← 调度耗尽时自动接力
```

> 📄 各 Phase 详细步骤见 [docs/PHASE_DETAIL.md](docs/PHASE_DETAIL.md)
> 📄 Prompt 模板见 [docs/PROMPTS.md](docs/PROMPTS.md)
> 📄 实践经验见 [docs/EXPERIENCE.md](docs/EXPERIENCE.md)

---

## 2. 可重入恢复

### 核心思路

流水线可能跨越多个 session（上下文耗尽、LLM 断连、人工介入等），
通过 PIPELINE_STATE.md + state.json 在新 session 中从中断点恢复。

### 工作目录结构

```
{work_dir}/
├── PIPELINE_STATE.md          # 🔑 流水线全局状态
├── DESIGN.md                  # 执行计划和设计决策
├── DISPATCHER_PROMPT.md       # 调度 session 模板
├── WORKER_PROMPT_TEMPLATE.md  # 构造 Worker 模板
├── QA_WORKER_PROMPT_TEMPLATE.md  # 质检 Worker 模板
├── state.json                 # 机器可读的任务状态
├── RETROSPECTIVE.md           # 复盘报告
├── reports/                   # 构造 Worker result 文件
├── qa_reports/                # 质检 Worker result 文件
└── human_feedback/            # 人工反馈记录
```

### PIPELINE_STATE.md 核心字段

包含：最后更新时间、当前 Phase（1-6）、Phase 进度表（✅/🔄/⏳）、当前待办列表、恢复指引。

### 恢复流程

1. 读取 PIPELINE_STATE.md → 当前 Phase 和进度
2. 读取 state.json → 每个 task 的详细状态
3. Phase 2/4 中断 → 启动新调度 session 从断点继续；Phase 3/5 中断 → 读取 reports 继续汇总
4. 更新 PIPELINE_STATE.md

---

## 3. ⚠️ 关键约束

| 约束 | 说明 |
|------|------|
| **调度只调度不干活** | 调度 session 不自己构造/质检测例，一律 spawn Worker |
| **调度串行，Worker 并行** | 一个调度 session 通过滑动窗口 spawn 多个 Worker |
| **Worker 无 spawn 工具** | Worker 只有 7 个基础工具，不能创建子任务 |
| **follow_up 优先于重建** | Worker 卡住时用 follow_up 恢复，保留完整历史上下文 |
| **及时更新 state.json** | 每次收到 Worker 回报后立即更新，确保可重入 |

---

## 4. 质检分类

| 类别 | 说明 | 适用范围 |
|------|------|---------|
| A 类（标准质检） | 全维度检查 + verify dry-run | medium/hard/expert |
| E 类（easy 实施） | 全维度检查 + 实际执行 + verify | easy 任务 |
| B 类（无 verify） | 全维度检查，跳过 verify | 纯 LLM 评分的 task |
| C/D 类（特殊） | session 定位/修正等特殊处理 | 有已知问题的 task |

---

## 5. 检查清单

### Phase 1 完成

- [ ] 候选清单已与用户确认
- [ ] 来源 session 文件存在且可读
- [ ] 测例编号已分配，无冲突
- [ ] DESIGN.md / PIPELINE_STATE.md / state.json / Prompt 模板已生成

### Phase 2 完成

- [ ] 所有 task 的 status 为 success 或 needs_review
- [ ] 每个 success 的 task 目录结构完整
- [ ] reports/ 下有每个 task 的 result 文件

### Phase 3 完成

- [ ] RETROSPECTIVE.md 已生成
- [ ] needs_review 已与用户讨论
- [ ] 人工反馈已记录到 human_feedback/
- [ ] 质检计划已制定

### Phase 4 完成

- [ ] 所有 task 质检完成（qa_status 为 pass / fixed / needs_fix）
- [ ] qa_reports/ 下有每个 task 的质检 result 文件

### Phase 5 完成

- [ ] 质检汇总报告已生成
- [ ] needs_fix 已处理（修复或确认跳过）
- [ ] PIPELINE_STATE.md 已更新为最终状态
- [ ] CASE_REGISTRY.md 已更新（标记为 ✅ 已构造）
