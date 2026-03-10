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

### 2.1 目录结构（TASK_SPEC.md 摘要）

```
task-{NNN}/
├── task.yaml              # 必须 — 任务元数据 + 验证规则
├── query.md               # 必须 — 用户 query（单轮或多轮）
├── initial_state/         # 可选 — 初始文件/环境状态
│   ├── skills/            #   预置 skill
│   ├── memory/            #   预置记忆
│   └── {project_dir}/     #   项目代码（需配合 initial_state_mapping）
├── verify/                # 必须 — pytest 验证脚本
│   └── test_task.py       #   规则检查代码
├── mocks/                 # 必须 — Mock 服务（即使不需要 mock 也要提供最小版）
│   ├── start.sh           #   统一启动入口（框架执行 bash /mocks/start.sh）
│   └── minimal_mock.py    #   Mock 服务实现
├── eval_prompt.md         # 推荐 — LLM 评分说明（大多数测例都需要）
└── README.md              # 可选 — 测例说明
```

### 2.2 task.yaml 核心字段

```yaml
id: "task-{NNN}"
name: "简短描述"
description: "详细描述任务背景和目标"
difficulty: easy | medium | hard | expert
category: "coding | tool-use | planning | ..."
tags: ["tag1", "tag2"]

# 评测配置
time_limit: 300           # 秒，默认 300
max_iterations: 30        # agent 最大迭代次数

# 环境初始化脚本（可选）
# 在 initial_state 复制完成后、config 写入前执行
# 典型用途：初始化 git 仓库、创建分支、构造复杂初始状态
setup_script: "initial_state/setup_repo.sh"   # 相对于 TASK_DIR
setup_args: ["project/repo"]                   # 相对路径会基于 EVAL_HOME 解析

# 初始状态映射（将 initial_state/ 下的目录映射到 agent 的工作环境）
initial_state_mapping:
  "skills/": "workspace/skills/"
  "memory/": "workspace/memory/"
  "{project_dir}/": "project/{project_dir}/"

# 验证配置 — 必须使用 verify_script
verify_script: "verify/test_task.py"

# ⚠️ DEPRECATED: success_criteria 已废弃，runner.py 不再执行
# 所有测例必须使用 verify_script 提供 pytest 验证脚本
```

### 2.3 query.md 格式

```markdown
## Turn 1: 主要指令

\```
用户的问题/任务描述
\```
```

多轮对话：

```markdown
## Turn 1: 初始需求

\```
第一轮 query
\```

## Turn 2: 补充信息

\```
第二轮 query（可以引用第一轮的结果）
\```
```

**注意**：
- 每个 Turn 的内容必须在 ``` 代码块内
- Turn 标题格式: `## Turn N: 描述`

### 2.4 verify/test_task.py 结构

```python
"""eval-bench 验证脚本模板"""
import os
import pytest

# 框架通过环境变量传递所有路径，verify 脚本不应硬编码路径
WORKSPACE = os.environ.get("WORKSPACE", ".")
PROJECT_DIR = os.environ.get("PROJECT_DIR", WORKSPACE)
RESULTS_DIR = os.environ.get("RESULTS_DIR", "/eval/results")
TASK_ID = os.environ.get("TASK_ID", "")
TASK_NAME = os.environ.get("TASK_NAME", "")
NANOBOT_HOME = os.environ.get("NANOBOT_HOME", "/eval/.nanobot")
TASK_DIR = os.environ.get("TASK_DIR", "/eval/task")

class TestTaskVerification:
    """规则检查"""

    def test_file_exists(self):
        """检查关键产出文件是否存在"""
        assert os.path.exists(f"{PROJECT_DIR}/expected_file.py")

    def test_content_correctness(self):
        """检查文件内容是否符合预期"""
        content = open(f"{PROJECT_DIR}/expected_file.py").read()
        assert "expected_pattern" in content

    def test_no_regression(self):
        """检查没有引入回归问题"""
        # ...
```

**环境变量完整列表**（由 runner.py `_run_pytest()` 传递）：

| 变量 | 值 | 说明 |
|------|-----|------|
| `EVAL_HOME` | `/eval` | 容器 HOME |
| `WORKSPACE` | `/eval/.nanobot/workspace` | nanobot workspace |
| `NANOBOT_HOME` | `/eval/.nanobot` | nanobot 配置目录 |
| `TASK_DIR` | `/eval/task` | 任务定义目录 |
| `RESULTS_DIR` | `/eval/results` | 结果输出目录 |
| `TASK_ID` | task.yaml 中的 id | 任务 ID（如 `task-001`） |
| `TASK_NAME` | task.yaml 中的 name | 任务名称 |
| `PROJECT_DIR` | 由 initial_state_mapping 决定 | 项目代码目录（Type B） |

### 2.5 eval_prompt.md 结构

```markdown
# 评分说明

## 任务背景
{简述任务目标}

## 评分维度

### 功能完整性 (40%)
- 是否完成了核心功能
- 边界情况是否处理

### 代码质量 (30%)
- 代码结构是否合理
- 是否有明显 bug

### 方案合理性 (30%)
- 技术选型是否恰当
- 是否过度工程化

## 评分标准
- 9-10: 完美完成，超出预期
- 7-8: 基本完成，有小瑕疵
- 5-6: 部分完成，有明显不足
- 3-4: 完成度低
- 1-2: 基本未完成
```

---

## 3. 构造流程（构造模式）

### 3.0 前置：读取规范

```
必读文件:
- ~/.nanobot/workspace/eval-bench/docs/TASK_SPEC.md  — 完整测例规范
- ~/.nanobot/workspace/skills/eval-task-builder/SKILL.md — 本文件（当前正在读）
```

### 3.1 Step 1: 理解 scan 记录

从输入的 scan 记录中提取：
- 候选 ID、任务名、来源 session 路径（**可能有多个**）、难度、类别
- scan 记录中的简要描述
- 如果涉及多个 session，明确**主 session**（发起原始 query 的那条）和**关联 session**（如 subagent、后续跟进等）

### 3.2 Step 2: 深度阅读来源 session

**这是最关键的一步，不可跳过或简化。**

```
操作:
1. 阅读来源 session 的 JSONL 文件
   - 如果 session 文件较短（< 500 行），可完整读取
   - 如果 session 文件很长（混杂了很多任务），应先浏览所有 user 角色的消息，
     从中定位与目标任务相关的范围，再精读该范围内的完整记录
   - 不需要读完所有内容，只需覆盖任务相关的对话

2. 如果涉及多个 session，基于 timestamp 实现跨 session 内容关联
   - 先确定主 session 中任务的时间范围
   - 再在关联 session 中查找同一时间段的记录
   - 按时间线还原完整的任务执行过程

3. 补充数据源：~/.nanobot/workspace/llm-logs/ 目录有全量 LLM API 数据 dump
   - 按日期分文件，可按需搜索其中的内容
   - 当 session 记录不够详细时（如工具调用细节），可从 llm-logs 中补充

4. 重点关注:
   a) 用户的原始问题是什么
   b) agent 实际做了哪些操作（工具调用序列）
   c) 任务涉及了哪些文件、代码库、外部服务
   d) 最终结果是什么，是否成功
   e) 过程中遇到了什么困难/错误
```

### 3.3 Step 3: 确定三要素

基于 session 阅读，确定测例的三个核心要素：

#### a) Query（测例问题）

- **基于原始问题，但可以合理调整**：
  - 如果原始问题过于简单（如"帮我改个 typo"），可以适当增加难度（如"重构这个模块并修复 bug"）
  - 如果原始问题依赖过多上下文（如"继续上次的工作"），需要改写为自包含的问题
  - 保持任务本质不变，只调整表述和难度
- **Query 应该是自包含的**：读者不需要额外背景就能理解任务
- **难度调整原则**：
  - easy: 单步或少量步骤，明确指令
  - medium: 需要理解上下文，多步骤协调
  - hard: 需要设计决策，涉及多文件/多系统
  - expert: 复杂架构设计，需要深度领域知识

#### b) Initial State（初始环境）

**核心原则：还原真实环境，不简化不摘录。**

根据 session 记录，确定任务执行所依赖的完整环境：

1. **代码库**：
   - 找到所有涉及的代码仓库
   - 通过 git log 定位 query 对应时间点的 commit
   - 使用 `git archive` 或 `git checkout` 恢复到该 commit 的状态
   - **必须保留完整代码**，不能摘录片段或简化
   - 如果仓库过大，使用 `git archive` 导出必要子目录，或用 orphan branch 精简 .git

2. **配置文件和数据**：
   - 环境配置（但需脱敏：API key → placeholder，真实 ID → 占位符）
   - 数据库文件、测试数据
   - session 历史文件（如任务涉及读取历史）

3. **预置 Skills 和 Memory**：
   - 如果任务依赖特定 skill，放入 initial_state/skills/
   - 如果任务依赖记忆内容，放入 initial_state/memory/

4. **外部 API Mock**（按需）：
   - 如果任务涉及外部 API（GitHub 等），评估是否需要 mock
   - 简单情况：在 query 中说明"假设 API 返回以下数据"
   - 复杂情况：提供 mock server 脚本
   - **飞书 API 特殊处理**：飞书部分 API 逻辑特别复杂，不方便 mock。
     scan 阶段会标记为"飞书专项"，这些场景**直接使用线上 API**，
     需要在执行测例之前手动配置飞书应用 key（在 .env 或 config 中）。
     task.yaml 中应添加 `tags: ["feishu-live-api"]` 标记。

5. **Git 状态还原**：
   - **不涉及 git 操作的任务**：initial_state 需包含 .git 目录以保留基本 git 信息，
     使用 orphan branch 技术精简 .git 体积：
     ```bash
     cd repo && git checkout --orphan slim && git add -A && git commit -m "snapshot at {commit_hash}"
     # 清理旧 refs，重新 gc
     ```
   - **涉及 git 操作的任务**（如 git log、git branch、git diff 等）：
     **不能使用 orphan branch 精简**，需要保留原始的 git 提交链条。
     根据任务需求，可能需要构造更复杂的 git 历史：
     - `git log` 类任务：保留足够多的 commit 记录（至少覆盖任务需要查看的范围）
     - `git branch` 类任务：保留相关的分支结构
     - `git diff` 类任务：保留对比所需的两个 commit
     - 如果原始仓库 .git 过大，可选择性保留相关 refs，删除无关分支和 tag

#### c) Verification（验证方式）

构造两层验证：

1. **规则检查（verify/test_task.py）**：
   - 文件存在性检查
   - 关键内容/模式匹配
   - 功能正确性（如能 import、能运行）
   - 无回归检查（原有功能不被破坏）

2. **LLM 评分（eval_prompt.md）**：
   - 描述评分维度和权重
   - 提供评分标准（1-10 分）
   - 说明任务背景，让 LLM 理解预期结果

### 3.4 Step 4: 构造测例目录

按照 2.1 的目录结构，逐一创建文件：

```
执行顺序:
1. 创建 task-{NNN}/ 目录
2. 写 task.yaml（元数据 + verify_script 字段）
3. 写 query.md（Turn 格式）
4. 构造 initial_state/（最耗时的步骤）
5. 写 verify/test_task.py（使用环境变量获取路径）
6. 创建 mocks/start.sh + mock 脚本（即使不需要 mock 也要提供最小版）
7. 写 eval_prompt.md
8. 写 README.md（可选）
```

### 3.5 Step 5: 自检

构造完成后，执行以下自检：

```
□ task.yaml 格式正确，所有必填字段都有值
□ task.yaml 使用 verify_script 字段（非 deprecated 的 success_criteria）
□ query.md 自包含，不依赖外部上下文
□ query.md 使用 "## Turn N:" 格式（内容在代码块内）
□ initial_state/ 包含任务所需的所有文件
□ initial_state/ 中的代码是完整的（不是摘录/简化版）
□ verify/test_task.py 语法正确（python -m py_compile）
□ verify 脚本使用环境变量获取路径（WORKSPACE/PROJECT_DIR/RESULTS_DIR 等）
□ mocks/start.sh 存在且可执行（即使不需要 mock 也要提供最小版）
□ eval_prompt.md 评分维度覆盖任务核心目标
□ 敏感信息已脱敏（API key、真实 ID、密码等）
□ .git 目录体积合理：不涉及 git 操作的用 orphan branch 精简；涉及 git 操作的保留必要历史链条
□ initial_state_mapping 路径与 verify 脚本中的路径一致
□ 如有 setup_script，脚本存在且可执行；setup_args 路径正确
□ verify 脚本中的数据库查询按 session_key 过滤，避免全表统计
```

### 3.6 Step 6: 记录决策点

**整个构造过程中，如果遇到不确定的设计决策，按以下策略处理：**

- **高不确定性**（如：不确定原始任务的真实意图、不确定该 mock 哪些 API、不确定难度定级）：
  - **停下来**，在 result 文件中记录问题，标记 `status: needs_review`
  - 等待人工反馈后再继续

- **低不确定性**（如：query 措辞的微调、verify 检查项的取舍、目录命名）：
  - **做出最佳判断继续推进**
  - 但必须在 result 文件的 `decisions` 字段中记录每个决策点和理由

**无论哪种情况，决策点都不能静默忽略——最终需要人工确认。**

---

## 4. 质检流程（质检模式）

### 4.1 质检维度

| 维度 | 代号 | 说明 | 权重 |
|------|------|------|------|
| **D1 原始匹配度** | MATCH | 对照原始 session，query.md 是否准确还原真实任务意图 | 高 |
| **D2 Initial State 完整性** | STATE | initial_state 是否包含任务所需的全部文件和环境 | 高 |
| **D3 Initial State 真实性** | REAL | 代码是否使用真实 git 快照，而非简化/摘录版 | 高 |
| **D4 Verify 脚本正确性** | VERIFY | test_task.py 语法正确、路径匹配、检查项合理 | 高 |
| **D5 Eval Prompt 质量** | EVAL | 评分维度覆盖核心目标，标准清晰 | 中 |
| **D6 task.yaml 规范性** | YAML | 字段完整、格式正确、mapping 路径一致 | 中 |
| **D7 脱敏合规** | SECURITY | 无 API key、真实 ID、密码等敏感信息 | 高 |
| **D8 .git 体积合理** | GIT_SIZE | .git 目录已精简（orphan branch），无冗余历史 | 低 |
| **D9 难度匹配** | DIFFICULTY | 标注难度与实际任务复杂度匹配 | 中 |

### 4.2 质检执行步骤

```
Step 1: 读取测例文件
  - 读取 task.yaml, query.md, eval_prompt.md
  - ls initial_state/，了解目录结构
  - 读取 verify/test_task.py

Step 2: 读取原始 session（必须）
  - 阅读来源 session 文件（按 3.2 的策略：长 session 先定位范围再精读）
  - 如果涉及多个 session，基于 timestamp 跨 session 关联
  - 对照 query.md，逐项验证 D1（原始匹配度）

Step 3: 逐维度检查
  - D1~D9 逐一检查，记录发现

Step 4: Verify Dry-run
  - 在 initial_state 目录下运行 verify 脚本（预期应 fail，因为任务还没做）
  - 检查脚本能否正常执行（不是因为语法错误而 fail）
  - 注意路径映射：根据 task.yaml 的 initial_state_mapping 正确设置环境变量

Step 4b: 低难度任务实施评测（仅 easy/medium 难度）
  - 直接试执行任务（作为 agent 完成 query 中的要求）
  - 执行完成后运行 verify 脚本，检查规则验证是否通过
  - 运行 LLM 评分，检查 eval_prompt.md 的评分维度是否合理
  - 如果验证/评分发现问题，反过来修正 verify 脚本或 eval_prompt.md

Step 5: 修复或记录
  - 小问题（typo、缺失字段、路径不一致）：直接修复
  - 大问题（initial_state 缺失关键文件、query 偏离原始意图）：记录为 needs_fix
  - 记录所有修复和发现到 result 文件

Step 6: 输出质检报告
  - 状态: pass | fixed | needs_fix
  - 各维度评分（pass/warn/fail）
  - 修复列表（如有）
  - 遗留问题（如有）
```

### 4.3 质检 Result 文件格式

```json
{
  "task_id": "task-{NNN}",
  "status": "pass | fixed | needs_fix",
  "dimensions": {
    "D1_MATCH": "pass | warn | fail",
    "D2_STATE": "pass | warn | fail",
    "D3_REAL": "pass | warn | fail",
    "D4_VERIFY": "pass | warn | fail",
    "D5_EVAL": "pass | warn | fail",
    "D6_YAML": "pass | warn | fail",
    "D7_SECURITY": "pass | warn | fail",
    "D8_GIT_SIZE": "pass | warn | fail",
    "D9_DIFFICULTY": "pass | warn | fail"
  },
  "fixes_applied": ["描述修复1", "描述修复2"],
  "remaining_issues": ["描述遗留问题"],
  "decisions": ["决策点1: 选择了X因为Y"],
  "notes": "补充说明"
}
```

---

## 5. 实践经验与注意事项

> 以下经验来自 2026-03 批量构造 36 个测例 + 三轮 QA 的实践总结。

### 5.1 Initial State 构造（最易出错的环节）

**⚠️ P0 — 代码必须用真实 git 快照，严禁简化/摘录**

这是第一轮批量构造中最严重的问题（R2 修复了 26 个测例）。LLM 在构造 initial_state 时，
倾向于"理解代码后写一个简化版"，而非直接使用原始代码。这会导致：
- 丧失真实场景复杂度
- verify 脚本基于简化代码编写，无法检测真实问题
- 评测结果不能反映 agent 处理真实代码的能力

**正确做法**：
```bash
# 1. 找到任务对应的 commit
cd /path/to/repo
git log --oneline --before="2026-03-05" | head -5

# 2. 导出该 commit 的完整代码
git archive {commit_hash} -o /tmp/snapshot.tar
# 或
git checkout {commit_hash} -- .

# 3. 如果需要保留 .git（任务涉及 git 操作），用 orphan branch 精简
git checkout --orphan slim
git add -A
git commit -m "snapshot at {commit_hash}"
# 删除旧 refs + gc
```

### 5.2 .git 体积控制

**⚠️ 不精简的 .git 可能占 30~60MB，精简后通常 1~3MB**

**场景一：任务不涉及 git 操作 → orphan branch 精简**

```bash
# orphan branch 精简流程
cd initial_state/{project_dir}
git checkout --orphan slim
git add -A
git commit -m "snapshot"
git branch -D main 2>/dev/null  # 删除旧分支
rm -rf .git/refs/original .git/logs
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

**场景二：任务涉及 git log / branch / diff 等操作 → 保留必要的 git 历史**

```bash
# 不能用 orphan branch！需要保留 commit 链条
# 策略：只保留相关分支，删除无关 refs
cd initial_state/{project_dir}

# 删除无关的远程分支
git remote remove origin 2>/dev/null

# 只保留需要的本地分支（如 main + feature-xxx）
git branch | grep -v 'main\|feature-xxx' | xargs git branch -D 2>/dev/null

# 删除 tags（如不需要）
git tag -l | xargs git tag -d 2>/dev/null

# 清理
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

实践中发现的问题（quality_fix R3）：
- task-016/019/030/035 的 .git 包含完整历史，总计 ~190MB
- 精简后降到 ~6MB，节省 97%

### 5.3 脱敏合规

**⚠️ 所有推送到公开仓库的内容严禁包含真实敏感信息**

需要脱敏的内容：
- API Key / Secret → `YOUR_API_KEY_HERE`
- 飞书 open_id → `ou_xxx`
- 飞书 chat_id → `oc_xxx`
- 真实用户名/邮箱 → 占位符
- config.json 中的敏感字段 → placeholder

### 5.4 路径映射一致性

**⚠️ task.yaml 的 initial_state_mapping 必须与 verify 脚本中的路径一致**

常见错误：
- task.yaml 映射 `project_code/ → project/`，但 verify 脚本中写死了 `initial_state/project_code/`
- 实际 eval 运行时，框架会按 mapping 重新组织目录，verify 脚本应使用 `WORKSPACE`/`PROJECT_DIR` 环境变量

```python
# verify 脚本中的正确写法 — 使用环境变量，不硬编码路径
WORKSPACE = os.environ.get("WORKSPACE", ".")
PROJECT_DIR = os.environ.get("PROJECT_DIR", os.path.join(WORKSPACE, "project"))
RESULTS_DIR = os.environ.get("RESULTS_DIR", "/eval/results")
TASK_ID = os.environ.get("TASK_ID", "")
```

### 5.5 Query 设计

- **自包含**：不依赖"上次对话"、"之前的工作"等外部上下文
- **明确目标**：agent 读完 query 应该知道要做什么
- **合理难度**：如果原始问题太简单，可以加入额外要求（如"同时写单元测试"、"处理边界情况"）
- **多轮 query**：如果原始交互是多轮的，可以合并为单轮（更常见），或保留多轮结构

### 5.6 Verify 脚本设计

- **检查结果而非过程**：验证最终产出，不验证 agent 的具体操作步骤
- **容错性**：允许合理的实现差异（如函数名不同但功能正确）
- **Dry-run 友好**：在 initial_state 上运行应该 fail（因为任务没做），但不应因语法错误而 crash
- **路径使用环境变量**：`WORKSPACE`、`PROJECT_DIR`、`NANOBOT_DIR`
- **数据库查询按 session_key 过滤**：如果 verify 脚本查询 analytics.db 等数据库，
  **避免全表 COUNT/SUM**（如 `SELECT COUNT(*) FROM token_usage`），
  因为 agent 自身的 eval session 也会写入同一数据库。
  应按 session_key 过滤：`WHERE session_key LIKE 'webchat:test_session_%'`

### 5.7 决策点处理策略

| 不确定程度 | 行为 | 示例 |
|-----------|------|------|
| 高 | 停下来，标记 needs_review | 不确定原始任务意图；不确定是否需要 mock 某 API |
| 中 | 做出判断并继续，详细记录 | query 措辞的选择；verify 检查项的取舍 |
| 低 | 做出判断并继续，简要记录 | 目录命名；README 内容 |

**关键原则：任何决策点都不能静默忽略，最终需要人工确认。**

---

## 6. Worker 执行指引

### 6.1 构造模式 Worker

Worker 收到的输入包含：
- scan 记录的候选信息（ID、名称、session 路径、难度、描述）
- 分配的 task 编号
- 工作目录路径

**执行流程**：
1. 读取本 SKILL.md（规范和流程）
2. 读取 TASK_SPEC.md（完整格式规范）
3. 按 Section 3 的构造流程执行
4. 将 result 写入指定路径

**Result 文件格式**（构造模式）：
```json
{
  "task_id": "task-{NNN}",
  "status": "success | needs_review | failed",
  "task_dir": "tasks/task-{NNN}/",
  "decisions": ["决策点1", "决策点2"],
  "issues": ["遇到的问题"],
  "notes": "补充说明"
}
```

### 6.2 质检模式 Worker

Worker 收到的输入包含：
- 待质检的 task 信息（ID、目录路径）
- 来源 session 路径
- 人工反馈（如有，来自上一轮构造/质检的问题）
- 质检类别（标准质检 / easy 实施评测 / 特殊处理）

**执行流程**：
1. 读取本 SKILL.md（质检维度和流程）
2. 按 Section 4 的质检流程执行
3. 将 result 写入指定路径

**质检类别说明**：
- **A 类（标准质检）**：全维度检查 + verify dry-run
- **E 类（easy 实施）**：全维度检查 + 实际执行任务 + verify 验证（仅 easy 难度）
- **B 类（无 verify）**：全维度检查，跳过 verify dry-run
- **C/D 类（特殊）**：需要定位/修正 session 引用等特殊处理

---

## 7. 附录

### 7.1 eval-bench 体系 Skill 协同

```
┌──────────────────────────────────────────────────────────────────┐
│                    eval-bench 测例生命周期                         │
│                                                                  │
│  ① eval-session-scanner         ② eval-task-builder (本 Skill)  │
│     扫描 session → 候选清单         构造 + 质检单个测例            │
│                                                                  │
│  ③ eval-task-batch-builder      ④ eval-framework-maintainer     │
│     批量构造 + 批量质检             框架代码维护                   │
└──────────────────────────────────────────────────────────────────┘
```

### 7.2 关键文件路径

```
规范文档:
  ~/.nanobot/workspace/eval-bench/docs/TASK_SPEC.md

测例数据:
  ~/.nanobot/workspace/eval-bench-data/tasks/          — 所有测例目录
  ~/.nanobot/workspace/eval-bench-data/CASE_REGISTRY.md — 候选清单

代码仓库（用于 git 快照）:
  ~/Documents/code/workspace/nanobot/                  — nanobot 核心
  ~/.nanobot/workspace/web-chat/                       — web-chat UI

Session 文件:
  ~/.nanobot/sessions/                                 — session JSONL 文件

LLM 日志（补充数据源）:
  ~/.nanobot/workspace/llm-logs/                       — 全量 LLM API 数据 dump（按日期分文件）
```
