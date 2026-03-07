---
name: eval-task-batch-builder
description: eval-bench 批量测例构造与质检。基于 batch-orchestrator 框架 + eval-task-builder 领域逻辑，完成从候选清单到质检通过的完整流水线。支持可重入恢复。
---

# eval-task-batch-builder — 批量测例构造与质检

> 基于 `batch-orchestrator` 框架，特化 eval 测例的批量构造和质检任务。
> 整个流水线（构造 → 复盘 → 质检 → 修复）作为一个完整大环节，支持可重入恢复。

---

## 1. 概述

### 定位

将 `batch-orchestrator` 的通用编排能力与 `eval-task-builder` 的测例构造/质检逻辑结合，
实现从 scan 候选清单到质检通过的完整批量生产流水线。

### 依赖

| Skill | 用途 |
|-------|------|
| `batch-orchestrator` | 四层编排框架（准备→主控→调度→Worker） |
| `eval-task-builder` | 单个测例的构造流程、质检维度和策略 |
| `web-subsession` | Worker session 的创建和通信 |

### 整体流水线

```
Phase 1: 准备（人工 + 准备 session）
  ├── 对齐候选清单
  ├── 分配测例编号
  └── 生成执行计划

Phase 2: 批量构造（主控 → 调度 → Worker）
  ├── 调度 session 管理 Worker 生命周期
  └── Worker 使用 eval-task-builder 构造模式

Phase 3: 构造复盘（主控 session）
  ├── 汇总构造结果
  ├── 生成复盘报告
  └── 与人工交互获取反馈

Phase 4: 批量质检（主控 → 调度 → Worker）
  ├── 基于人工反馈制定质检计划
  ├── Worker 使用 eval-task-builder 质检模式
  └── 汇总质检结果

Phase 5: 质检复盘 + 人工修复（主控 session）
  ├── 汇总质检发现
  ├── 自动修复的确认
  ├── needs_fix 的人工处理
  └── 决定是否需要额外质检轮次

(可选) Phase 6+: 迭代质检修复
  └── 重复 Phase 4-5 直到质量达标
```

---

## 2. 可重入恢复机制

### 2.1 核心思路

整个流水线可能跨越多个 session（上下文耗尽、LLM 断连、人工介入等），
需要能在新 session 中从中断点恢复。

### 2.2 状态文件

所有状态集中在一个工作目录下（如 `eval-bench-data/batch_build_v2/`）：

```
{work_dir}/
├── PIPELINE_STATE.md      # 🔑 流水线全局状态（当前 Phase、进度、待办）
├── DESIGN.md              # 执行计划和设计决策
├── MASTER_PROMPT.md       # 主控 session 的可重入启动提示词
├── DISPATCHER_PROMPT.md   # 调度 session 模板
├── WORKER_PROMPT_TEMPLATE.md  # Worker 模板（构造模式）
├── QA_WORKER_PROMPT_TEMPLATE.md  # Worker 模板（质检模式）
├── state.json             # 机器可读的任务状态
├── RETROSPECTIVE.md       # 复盘报告
├── reports/               # 各 Worker 的 result 文件
│   ├── task-003.json
│   └── ...
├── qa_reports/            # 质检 Worker 的 result 文件
│   ├── task-003_qa.json
│   └── ...
└── human_feedback/        # 人工反馈记录
    ├── build_feedback.md  # 构造阶段反馈
    └── qa_feedback.md     # 质检阶段反馈
```

### 2.3 PIPELINE_STATE.md 格式

```markdown
# 流水线状态

> 最后更新: {timestamp}
> 当前 Phase: {1-6}
> 当前步骤: {具体描述}

## Phase 进度

| Phase | 状态 | 说明 |
|-------|------|------|
| Phase 1 准备 | ✅ 完成 | 36 个测例，编号 task-003 ~ task-038 |
| Phase 2 构造 | ✅ 完成 | 34/36 success, 2 needs_review |
| Phase 3 构造复盘 | ✅ 完成 | 人工反馈已收集 |
| Phase 4 质检 | 🔄 进行中 | 20/36 完成 |
| Phase 5 质检复盘 | ⏳ 待开始 | |

## 当前待办

1. 继续 Phase 4 质检：task-023 ~ task-038 尚未质检
2. task-015 构造阶段标记 needs_review，等待人工确认

## 恢复指引

如果在新 session 中继续：
1. 读取本文件了解当前进度
2. 读取 state.json 获取每个 task 的详细状态
3. 读取 DESIGN.md 了解执行计划
4. 从"当前待办"继续执行
```

### 2.4 恢复流程

当在新 session 中继续工作时：

```
1. 读取 PIPELINE_STATE.md → 了解当前 Phase 和进度
2. 读取 state.json → 获取每个 task 的状态
3. 根据当前 Phase:
   - Phase 2 中断 → 读取 DISPATCHER_PROMPT.md，启动新调度 session 继续未完成的 task
   - Phase 3 中断 → 读取已有的 reports/，继续汇总
   - Phase 4 中断 → 读取 QA_WORKER_PROMPT_TEMPLATE.md，启动新调度 session 继续质检
   - Phase 5 中断 → 读取 qa_reports/，继续汇总
4. 更新 PIPELINE_STATE.md
```

---

## 3. Phase 1: 准备

### 3.1 对齐候选清单

与用户确认要构造的测例范围：

```
操作:
1. 读取 CASE_REGISTRY.md，筛选状态为 📋 候选 的条目
2. 列出清单，让用户确认:
   - 哪些要构造，哪些跳过
   - 难度定级是否合理
   - 是否有需要合并的候选
3. 基本检查:
   - 每个候选的来源 session 文件是否存在
   - session 文件是否可读、内容非空
   - 如果 session 不存在，标记并与用户讨论
```

### 3.2 分配测例编号

```
规则:
- 编号格式: task-{NNN}（三位数字，从已有最大编号 +1 开始）
- 编号连续，不跳号
- 记录编号映射到 state.json
```

### 3.3 生成执行计划

产出 DESIGN.md，包含：
- 任务总量和难度分布
- 并行策略（Worker 并发数、每代调度处理量）
- 预估时间和资源
- 风险点

产出 PIPELINE_STATE.md（初始版本）。

### 3.4 生成 Prompt 模板

基于 eval-task-builder 的规范，生成：
- DISPATCHER_PROMPT.md（调度 session 指令）
- WORKER_PROMPT_TEMPLATE.md（构造模式 Worker 模板）
- QA_WORKER_PROMPT_TEMPLATE.md（质检模式 Worker 模板）

---

## 4. Phase 2: 批量构造

### 4.1 编排模式

遵循 `batch-orchestrator` 的四层编排：

```
主控 session
  │  读取 MASTER_PROMPT.md（可重入）
  │  管理全局进度，处理异常
  │
  ├── 调度 session (gen1)
  │     │  读取 DISPATCHER_PROMPT.md
  │     │  串行处理任务队列
  │     │
  │     ├── Worker session (task-003)  ← 构造模式
  │     ├── Worker session (task-004)
  │     └── ...
  │
  ├── 调度 session (gen2)  ← 如果 gen1 迭代耗尽
  │     └── ...
  └── ...
```

### 4.2 调度 session 职责

**调度 session 只做调度，不做构造**（来自 batch_build 复盘 A1）。

```
职责:
1. 读取 state.json，找到 status=pending 的任务
2. 逐个启动 Worker session（通过 curl web-subsession API）
3. 轮询 Worker 的 result 文件（检查 reports/task-{NNN}.json）
4. 收集结果，更新 state.json
5. 处理 Worker 卡住的情况（发送恢复消息）
6. 达到 budget 后停止，汇报进度

不做:
- 不自己构造测例（即使是 easy 任务）
- 不修改 CASE_REGISTRY.md
- 不做质检
```

### 4.3 Worker session 执行

每个 Worker session 收到的消息包含：
- 候选信息（ID、名称、session 路径、难度、描述）
- 分配的 task 编号
- 工作目录
- 指令：读取 eval-task-builder SKILL.md，按构造模式执行

Worker 完成后写入 `reports/task-{NNN}.json`。

### 4.4 异常处理

| 情况 | 处理方式 |
|------|---------|
| Worker 卡住（长时间无 result） | 调度 session 发送恢复消息 |
| Worker 报错退出 | 记录错误，标记 task 为 failed，继续下一个 |
| 调度 session 迭代耗尽 | 主控启动新一代调度 session |
| LLM 断连 | 等待恢复，向同一 session_key 发送继续消息 |
| Worker 标记 needs_review | 记录到 state.json，Phase 3 汇总处理 |

---

## 5. Phase 3: 构造复盘

### 5.1 汇总构造结果

```
操作:
1. 读取所有 reports/task-{NNN}.json
2. 统计: success / needs_review / failed
3. 汇总所有 Worker 记录的 decisions（决策点）
4. 汇总所有 issues
5. 生成 RETROSPECTIVE.md
```

### 5.2 与人工交互

将以下内容呈现给用户：

```
1. 总体统计（成功率、耗时、问题数）
2. 需要 review 的 task 列表及问题描述
3. 所有 Worker 的决策点汇总（需要人工确认）
4. 发现的共性问题（如多个 Worker 都遇到的困难）
5. 建议的质检重点
```

等待用户反馈，将反馈记录到 `human_feedback/build_feedback.md`。

### 5.3 更新状态

根据人工反馈：
- 确认的 needs_review → 安排修复（加入 Phase 4 质检计划）
- 确认的决策点 → 记录到 DESIGN.md
- 更新 PIPELINE_STATE.md

---

## 6. Phase 4: 批量质检

### 6.1 制定质检计划

基于构造复盘和人工反馈，制定质检计划：

```
输入:
- 构造阶段的 RETROSPECTIVE.md
- 人工反馈 human_feedback/build_feedback.md
- eval-task-builder 的质检维度（D1~D9）

输出:
- QA 任务清单（哪些 task 需要质检、质检类别、重点关注维度）
- QA_WORKER_PROMPT_TEMPLATE.md（质检 Worker 模板）
```

**质检分类**（来自 QA R3 实践）：

| 类别 | 说明 | 适用范围 |
|------|------|---------|
| A 类（标准质检） | 全维度检查 + verify dry-run | medium/hard/expert |
| E 类（easy 实施） | 全维度检查 + 实际执行 + verify | easy 任务 |
| B 类（无 verify） | 全维度检查，跳过 verify | 纯 LLM 评分的 task |
| C/D 类（特殊） | session 定位/修正等特殊处理 | 有已知问题的 task |

### 6.2 质检编排

与 Phase 2 相同的编排模式，但 Worker 使用质检模式：

```
主控 session
  ├── 调度 session (qa_gen1)
  │     ├── QA Worker (task-003)  ← 质检模式
  │     ├── QA Worker (task-004)
  │     └── ...
  └── ...
```

每个 QA Worker 收到的消息包含：
- 待质检的 task 信息
- 来源 session 路径
- 人工反馈（如有）
- 质检类别和重点维度
- 指令：读取 eval-task-builder SKILL.md，按质检模式执行

QA Worker 完成后写入 `qa_reports/task-{NNN}_qa.json`。

### 6.3 质检 Worker 的修复权限

- **小问题直接修复**：typo、缺失字段、路径不一致、verify 脚本语法错误
- **大问题记录不修复**：initial_state 缺失关键文件、query 偏离原始意图、需要重新构造
- 所有修复都记录在 qa_report 的 `fixes_applied` 字段中

---

## 7. Phase 5: 质检复盘

### 7.1 汇总质检结果

```
操作:
1. 读取所有 qa_reports/task-{NNN}_qa.json
2. 统计: pass / fixed / needs_fix
3. 按维度汇总发现（哪些维度问题最多）
4. 生成质检报告
```

### 7.2 与人工交互

```
呈现:
1. 总体质检结果（通过率、修复数、遗留问题数）
2. needs_fix 的 task 列表及问题描述
3. Worker 自动修复的汇总（需要人工确认修复是否合理）
4. 共性问题分析
5. 是否需要额外质检轮次的建议
```

### 7.3 决定后续

- 如果遗留问题少且可手动修复 → 人工修复后结束
- 如果遗留问题多 → 进入 Phase 6（迭代质检修复）
- 更新 PIPELINE_STATE.md

---

## 8. 实践经验

> 以下经验来自 2026-03 的完整实践（1 轮构造 + 3 轮 QA）。

### 8.1 调度策略

**⚠️ 调度 session 只调度，不构造**（复盘 A1）

Gen3~Gen5 中调度 session 混合了"自己构造 easy 任务"和"启动 worker"两种模式，
导致迭代次数不够。改为纯调度后，100 次迭代可管理 15-20 个 Worker。

**⚠️ 串行启动，不要并行启动太多 Worker**

一次启动 5+ 个 Worker 会导致：
- 调度 session 轮询压力大
- 系统资源竞争
- 推荐：串行启动，每个 Worker 启动后等待一小段时间再启动下一个

### 8.2 Worker 健壮性

**⚠️ Worker 卡住是常态，需要恢复机制**

实践中 Worker 卡住的原因：
- LLM 断连（最常见）
- 迭代次数耗尽
- 文件操作错误

恢复方式：向同一 session_key 发送继续消息
```bash
curl --max-time 5 -X POST http://localhost:8082/api/execute-stream \
  -H 'Content-Type: application/json' \
  -d '{"session_key":"<原key>","message":"请继续之前的工作，检查 result 文件是否已写入"}'
```

### 8.3 state.json 设计

```json
{
  "tasks": {
    "task-003": {
      "case_id": "N3",
      "status": "success | pending | in_progress | needs_review | failed",
      "worker_session": "webchat:worker_xxx",
      "build_result": "reports/task-003.json",
      "qa_status": "pass | fixed | needs_fix | pending",
      "qa_result": "qa_reports/task-003_qa.json",
      "notes": ""
    }
  },
  "pipeline_phase": 4,
  "last_updated": "2026-03-07T15:00:00"
}
```

### 8.4 迭代次数管理

| 角色 | 推荐 max_iterations | 说明 |
|------|---------------------|------|
| 调度 session | 100（默认） | 纯调度，主要是 curl + 文件读写 |
| 构造 Worker | 100 | 需要读 session、构造文件、git 操作 |
| 质检 Worker | 80 | 读 session + 检查 + 小修复 |

**⚠️ 100 次迭代是硬上限**，调度 session 如果管理的 Worker 多，可能不够。
解决方案：分代执行（gen1 处理前 N 个，gen2 继续）。

### 8.5 常见质量问题（从三轮 QA 总结）

| 问题 | 频率 | 根因 | 预防措施 |
|------|------|------|---------|
| 代码被简化/摘录 | 高 | LLM 倾向"理解后重写" | Worker Prompt 中强调"必须用 git 快照" |
| .git 体积过大 | 中 | 未做 orphan 精简 | Worker Prompt 中包含精简步骤 |
| 路径映射不一致 | 中 | task.yaml 和 verify 脚本路径不匹配 | 自检清单中包含路径一致性检查 |
| 敏感信息泄露 | 低 | 复制了真实配置文件 | Worker Prompt 中强调脱敏 |
| verify 脚本语法错误 | 低 | 未做 py_compile 检查 | 自检步骤包含编译检查 |
| query 不自包含 | 中 | 直接复制了原始对话 | 强调 query 需要改写为自包含 |

### 8.6 并行度建议

| 任务总量 | 推荐并行 Worker 数 | 说明 |
|---------|-------------------|------|
| ≤10 | 3-5 | 单代调度可完成 |
| 11-20 | 5-8 | 可能需要 2 代调度 |
| 21-40 | 8-12 | 需要 2-3 代调度 |
| >40 | 分批次执行 | 每批 20 个 |

---

## 9. Prompt 模板参考

### 9.1 MASTER_PROMPT.md 模板

```markdown
# 主控 Session — eval-bench 批量构造与质检

## 你的角色
你是 eval-bench 批量测例构造与质检的主控。管理整个流水线的执行。

## 当前状态
读取以下文件了解当前进度：
- `{work_dir}/PIPELINE_STATE.md` — 流水线全局状态
- `{work_dir}/state.json` — 任务详细状态
- `{work_dir}/DESIGN.md` — 执行计划

## 你的职责
1. 根据当前 Phase 执行对应操作
2. 启动/管理调度 session
3. 汇总结果，生成复盘报告
4. 与用户交互获取反馈
5. 更新 PIPELINE_STATE.md

## 关键约束
- 不要自己构造或质检测例（那是 Worker 的工作）
- 每次操作后更新 PIPELINE_STATE.md
- 遇到不确定的决策，与用户讨论
```

### 9.2 DISPATCHER_PROMPT.md 模板

```markdown
# 调度 Session — eval-bench 批量 {构造/质检}

## 你的角色
你是 eval-bench 批量 {构造/质检} 的调度者。只做调度，不做 {构造/质检}。

## 状态文件
- `{work_dir}/state.json` — 任务状态

## 执行流程
1. 读取 state.json，找到 status=pending 的任务
2. 逐个启动 Worker session:
   - 用 WORKER_PROMPT_TEMPLATE 生成消息
   - 通过 curl 启动 web-subsession
3. 轮询 Worker 的 result 文件
4. 更新 state.json
5. 达到 budget 后停止

## Worker 启动方式
```bash
curl --max-time 5 -X POST http://localhost:8082/api/execute-stream \
  -H 'Content-Type: application/json' \
  -d '{"session_key":"webchat:{role}_{dispatch_ts}_{task_id}","message":"..."}'
```

## Budget
每代最多处理 {N} 个任务。处理完后汇报进度并停止。
```

### 9.3 构造 Worker Prompt 模板

```markdown
你是 eval-bench 测例构造工作者。

## 任务信息
- **候选 ID**: {{CASE_ID}}
- **任务名**: {{CASE_NAME}}
- **来源 Session**: {{SESSION_PATH}}
- **难度**: {{DIFFICULTY}}
- **分配编号**: task-{{TASK_NUMBER}}
- **描述**: {{DESCRIPTION}}
- **工作目录**: {{WORK_DIR}}

## 执行步骤
1. 读取 `~/.nanobot/workspace/skills/eval-task-builder/SKILL.md`
2. 读取 `~/.nanobot/workspace/eval-bench/docs/TASK_SPEC.md`
3. 按 SKILL.md Section 3（构造流程）执行
4. 将 result 写入 `{{WORK_DIR}}/reports/task-{{TASK_NUMBER}}.json`

## ⚠️ 关键提醒
- initial_state 中的代码**必须使用 git 快照**，严禁简化/摘录
- 所有敏感信息必须脱敏
- .git 目录必须用 orphan branch 精简
- 遇到高不确定性决策，标记 needs_review 并停下
- 所有决策点都要记录，不能静默忽略
```

### 9.4 质检 Worker Prompt 模板

```markdown
你是 eval-bench 测例质检工作者。

## 任务信息
- **Task ID**: {{TASK_ID}}
- **Task 目录**: {{TASK_DIR}}
- **质检类别**: {{QA_CLASS}}（A=标准 / E=easy实施 / B=无verify / C/D=特殊）
- **难度**: {{DIFFICULTY}}
- **来源 Session**: {{SESSION_PATH}}
- **人工反馈**: {{HUMAN_FEEDBACK}}（如无则为"无"）
- **工作目录**: {{WORK_DIR}}

## 执行步骤
1. 读取 `~/.nanobot/workspace/skills/eval-task-builder/SKILL.md`
2. 按 SKILL.md Section 4（质检流程）执行
3. 将 result 写入 `{{WORK_DIR}}/qa_reports/{{TASK_ID}}_qa.json`

## ⚠️ 关键提醒
- **必须完整阅读来源 session**，对照验证 query 和 initial_state
- 小问题直接修复，大问题记录为 needs_fix
- 所有修复和发现都要记录在 result 中
```

---

## 10. 检查清单

### 10.1 Phase 1 完成检查

```
□ 候选清单已与用户确认
□ 所有候选的来源 session 文件存在且可读
□ 测例编号已分配，无冲突
□ DESIGN.md 已生成
□ PIPELINE_STATE.md 已生成
□ 所有 Prompt 模板已生成
□ state.json 已初始化
```

### 10.2 Phase 2 完成检查

```
□ 所有 task 的 state.json status 为 success 或 needs_review
□ 每个 success 的 task 目录结构完整（task.yaml + query.md + initial_state + verify/eval_prompt）
□ reports/ 下有每个 task 的 result 文件
□ PIPELINE_STATE.md 已更新
```

### 10.3 Phase 3 完成检查

```
□ RETROSPECTIVE.md 已生成
□ 所有 needs_review 已与用户讨论
□ 所有决策点已与用户确认
□ 人工反馈已记录到 human_feedback/build_feedback.md
□ 质检计划已制定
□ PIPELINE_STATE.md 已更新
```

### 10.4 Phase 4 完成检查

```
□ 所有 task 的质检完成（qa_status 为 pass / fixed / needs_fix）
□ qa_reports/ 下有每个 task 的质检 result 文件
□ PIPELINE_STATE.md 已更新
```

### 10.5 Phase 5 完成检查

```
□ 质检汇总报告已生成
□ needs_fix 的 task 已处理（修复或确认跳过）
□ 自动修复已与用户确认
□ PIPELINE_STATE.md 已更新为最终状态
□ CASE_REGISTRY.md 已更新（标记为 ✅ 已构造）
```
