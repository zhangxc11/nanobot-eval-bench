---
name: eval-task-builder
description: eval-bench 测例构造与质检。基于 scan 记录构造符合框架规范的完整测例目录，并提供质检维度和策略。Worker 执行时明确区分"构造模式"和"质检模式"。
---

# eval-task-builder — 测例构造与质检

基于 eval-session-scanner 的 scan 记录，构造符合 eval-bench 框架规范的完整测例目录；
同时定义质检维度和策略，供批量质检阶段使用。

---

## 1. 职责总览

```
构造模式:
  输入: scan 记录的一条候选描述 + 来源 session 文件（可能多个，需注明主 session 和关联 session）
  输出: task-{NNN}/ 完整目录（符合 TASK_SPEC.md 规范）

质检模式:
  输入: 已构造的 task 目录 + 来源 session 文件（可能多个） + 人工反馈（如有）
  输出: 质检报告（pass / fixed / needs_fix）+ 已修复的文件（如适用）
```

---

## 2. 测例格式规范

> 📄 详细内容见 [docs/TASK_FORMAT_DETAIL.md](docs/TASK_FORMAT_DETAIL.md)

### 目录结构

```
task-{NNN}/
├── task.yaml              # 必须 — 任务元数据 + 验证规则
├── query.md               # 必须 — 用户 query（## Turn N: 标题 + 代码块）
├── initial_state/         # 可选 — 初始文件/环境状态
│   ├── skills/            #   预置 skill
│   ├── memory/            #   预置记忆
│   └── {project_dir}/     #   项目代码（需配合 initial_state_mapping）
├── verify/                # 必须 — pytest 验证脚本
│   └── test_task.py       #   使用环境变量获取路径，检查结果而非过程
├── mocks/                 # 必须 — Mock 服务（即使不需要也提供最小版 start.sh）
│   ├── start.sh
│   └── minimal_mock.py
├── eval_prompt.md         # 推荐 — LLM 评分说明（维度 + 权重 + 1-10 标准）
└── README.md              # 可选
```

### task.yaml 核心字段

```yaml
id: "task-{NNN}"
name: "简短描述"
description: "详细描述"
difficulty: easy | medium | hard | expert
category: "coding | tool-use | planning | ..."
tags: ["tag1"]
time_limit: 300
max_iterations: 30
verify_script: "verify/test_task.py"   # 必须（success_criteria 已废弃）

# ⚠️ 路径映射规则：dest_path = /eval/{value}
# value 必须以 ".nanobot/workspace/" 开头才能放到 agent workspace 下！
# 错误示例："nanobot_core/" → /eval/nanobot_core/ ❌
# 正确示例：".nanobot/workspace/nanobot_core/" → /eval/.nanobot/workspace/nanobot_core/ ✅
initial_state_mapping:
  "project_code/": ".nanobot/workspace/project/{name}/"
  "skills/": ".nanobot/workspace/skills/"

# ⚠️ PROJECT_DIR：verify 脚本依赖此变量时，推荐显式声明（详见 docs/PROJECT_DIR.md）
# 优先级：1) project_dir 字段 → 2) mapping 中 project_code key → 3) fallback 探测
project_dir: ".nanobot/workspace/project/{name}"
```

### verify 脚本环境变量

| 变量 | 值 | 说明 |
|------|-----|------|
| `WORKSPACE` | `/eval/.nanobot/workspace` | agent workspace |
| `PROJECT_DIR` | 由 task.yaml 决定 | 项目代码目录 |
| `RESULTS_DIR` | `/eval/results` | 结果输出 |
| `TASK_DIR` | `/eval/task` | 任务定义目录 |
| `TASK_ID` / `TASK_NAME` | task.yaml 中的值 | 任务标识 |
| `EVAL_HOME` / `NANOBOT_HOME` | `/eval` / `/eval/.nanobot` | 容器根目录 |

---

## 3. 构造流程（构造模式）

> 📄 详细内容见 [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md)

前置：必读 `~/.nanobot/workspace/eval-bench/docs/TASK_SPEC.md`

1. **理解 scan 记录** — 提取候选 ID、session 路径（区分主/关联 session）、难度、描述
2. **深度阅读来源 session**（最关键）— 长 session 先定位范围再精读；多 session 按 timestamp 关联；关注原始问题、操作序列、涉及文件、最终结果
3. **确定三要素** — Query（自包含、可调整难度）、Initial State（真实 git 快照、完整代码、脱敏）、Verification（pytest 规则检查 + LLM 评分）
4. **构造测例目录** — 按目录结构逐一创建：task.yaml → query.md → initial_state → verify → mocks → eval_prompt
5. **自检** — mapping 路径正确、verify 语法正确且用环境变量、代码完整非摘录、敏感信息已脱敏、PROJECT_DIR 有显式声明
6. **记录决策点** — 高不确定性→停下标记 needs_review；低不确定性→继续但记录理由；决策不可静默忽略

---

## 4. 质检流程（质检模式）

> 📄 详细内容见 [docs/QA_GUIDE.md](docs/QA_GUIDE.md)（含实践经验 §5.1~§5.8）
> 📄 PROJECT_DIR 详解见 [docs/PROJECT_DIR.md](docs/PROJECT_DIR.md)

### 质检维度

| 维度 | 代号 | 权重 | 说明 |
|------|------|------|------|
| 原始匹配度 | D1 MATCH | 高 | query 是否准确还原真实任务意图 |
| Initial State 完整性 | D2 STATE | 高 | 是否包含全部所需文件和环境 |
| Initial State 真实性 | D3 REAL | 高 | 代码是否使用真实 git 快照（非简化版） |
| Verify 脚本正确性 | D4 VERIFY | 高 | 语法正确、路径匹配、检查项合理 |
| Eval Prompt 质量 | D5 EVAL | 中 | 评分维度覆盖核心目标 |
| task.yaml 规范性 | D6 YAML | 中→高 | 字段完整、mapping 路径正确、PROJECT_DIR 声明 |
| 脱敏合规 | D7 SECURITY | 高 | 无 API key、真实 ID 等 |
| .git 体积合理 | D8 GIT_SIZE | 低 | orphan branch 精简 |
| 难度匹配 | D9 DIFFICULTY | 中 | 标注与实际复杂度匹配 |

### 质检步骤摘要

1. **读取测例文件** — task.yaml, query.md, verify, eval_prompt, initial_state 目录
2. **读取原始 session** — 对照 query.md 验证 D1
3. **逐维度检查** — D1~D9
4. **Verify Dry-run** — 在 initial_state 上运行 verify（预期 fail 但不应 crash）
5. **低难度实施评测**（仅 easy/medium）— 实际执行任务 + verify 验证
6. **修复或记录** — 小问题直接修复；大问题标记 needs_fix
7. **输出质检报告** — status: pass | fixed | needs_fix + 各维度评分

---

## 5. Worker 执行指引

### 构造模式 Worker

- 读取本 SKILL.md + TASK_SPEC.md → 按 §3 构造流程执行
- 输入：scan 候选信息 + task 编号 + 工作目录
- 输出 Result：`{"task_id", "status": "success|needs_review|failed", "task_dir", "decisions", "issues", "notes"}`

### 质检模式 Worker

- 读取本 SKILL.md → 按 §4 质检流程执行
- 输入：task 目录 + session 路径 + 人工反馈 + 质检类别
- 质检类别：**A 类**（标准全维度）| **E 类**（easy 实施评测）| **B 类**（无 verify）| **C/D 类**（特殊处理）
- 输出 Result：`{"task_id", "status": "pass|fixed|needs_fix", "dimensions": {D1~D9}, "fixes_applied", "remaining_issues"}`

---

## 6. 附录

### eval-bench 体系 Skill 协同

```
① eval-session-scanner    → 扫描 session → 候选清单
② eval-task-builder (本)  → 构造 + 质检单个测例
③ eval-task-batch-builder → 批量构造 + 批量质检
④ eval-framework-maintainer → 框架代码维护
```

### 关键文件路径

| 类别 | 路径 |
|------|------|
| 测例规范 | `~/.nanobot/workspace/eval-bench/docs/TASK_SPEC.md` |
| 测例数据 | `~/.nanobot/workspace/eval-bench-data/tasks/` |
| 候选清单 | `~/.nanobot/workspace/eval-bench-data/CASE_REGISTRY.md` |
| nanobot 代码 | `~/Documents/code/workspace/nanobot/` |
| web-chat 代码 | `~/.nanobot/workspace/web-chat/` |
| Session 文件 | `~/.nanobot/sessions/` |
| LLM 日志 | `~/.nanobot/workspace/llm-logs/` |

### 详细文档索引

| 文档 | 内容 |
|------|------|
| [docs/TASK_FORMAT_DETAIL.md](docs/TASK_FORMAT_DETAIL.md) | query/task.yaml/verify/eval_prompt 完整格式 + 路径映射详解 |
| [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md) | 构造 Step 1-6 详细操作 + 自检清单 |
| [docs/QA_GUIDE.md](docs/QA_GUIDE.md) | 质检步骤详细说明 + 实践经验 §5.1~§5.8 + Batch 4 教训 |
| [docs/PROJECT_DIR.md](docs/PROJECT_DIR.md) | PROJECT_DIR 三级优先级 + 推荐用法 + 常见错误 |
