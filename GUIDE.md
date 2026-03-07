# nanobot Eval Bench — 使用指南

> 从真实 Agent 对话中提炼评测任务，在 Docker 隔离环境中回放，量化不同策略的效果差异。

---

## 一、这是什么？

### 核心思路

当你日常使用 nanobot（创建 Skill、修改代码、写文档……），每一次成功的对话都是一份「黄金数据」——它记录了 Agent 面对真实需求时的完整行为轨迹。

**Eval Bench 做的事情就是：**

```
真实对话历史  →  提炼为可重放的测例  →  在 Docker 中隔离执行  →  自动化验证 + 指标收集
```

这样你就可以回答一个关键问题：**换一个模型 / 换一种提示词策略 / 升级框架代码后，Agent 还能完成同样的任务吗？完成得更好还是更差？**

### 它不是什么

- 不是 LLM benchmark（不测基础能力，测的是 Agent 端到端完成复杂任务的能力）
- 不是单元测试（不测函数，测的是多轮对话 + 工具调用 + 文件操作的完整流程）
- 不是一次性的——它是一个持续积累的评测资产，随着你的使用不断丰富

---

## 二、本地部署

### 前置依赖

- Docker Desktop（用于隔离执行环境）
- Python 3.11+（宿主机脚本依赖）
- nanobot 源码仓库（本地 clone，参考 https://github.com/zhangxc11/nanobot/blob/main/SETUP.md ）

### 安装步骤

```bash
# 1. 克隆框架仓库
cd ~/.nanobot/workspace
git clone git@github.com:zhangxc11/nanobot-eval-bench.git eval-bench

# 2. 创建本地数据目录（不随框架分发）
mkdir -p eval-bench-data/tasks eval-bench-data/results

# 3. 配置环境变量
cd eval-bench
cp .env.example .env
vim .env   # 填入 AGENT_API_KEY 等配置

# 4. 安装配套 Skill（创建 symlink）
cd ~/.nanobot/workspace/skills
for s in eval-session-scanner eval-task-builder eval-framework-maintainer eval-task-batch-builder; do
    ln -sf ../eval-bench/skills/$s $s
done

# 5. 首次运行（会构建 Docker 基础镜像，约 2-5 分钟）
cd ~/.nanobot/workspace/eval-bench
./run.sh --task task-001-doubao-search-skill
```

### 目录布局

```
~/.nanobot/workspace/
├── eval-bench/                 # 框架仓库（Git 管理，可分发）
│   ├── run.sh                  # 一键运行入口
│   ├── pack.sh                 # 打包分发
│   ├── platform/               # Docker 运行时（runner.py, Dockerfile, compose）
│   ├── skills/                 # 4 个配套 Skill
│   └── docs/                   # 规范文档
│
├── eval-bench-data/            # 本地数据（不分发，不入 Git）
│   ├── CASE_REGISTRY.md        # 测例候选清单
│   ├── tasks/                  # 测例目录
│   └── results/                # 运行结果
│
└── skills/                     # Skill symlink
    ├── eval-session-scanner -> ../eval-bench/skills/...
    └── ...
```

**为什么分离？** `eval-bench/` 是通用框架，任何人拿到都能用；`eval-bench-data/` 是你自己的数据——从你的对话中提炼的测例，可能包含业务上下文，不适合公开分发。

---

## 三、日常使用：最佳实践

Eval Bench 的价值来源于你日常与 nanobot 的交互质量。以下最佳实践能让你的对话历史更容易被提炼为高质量测例：

### 🎯 1. 每个任务新启一个 Session

```
✅ 好：Session A = 创建 calendar-reader Skill
       Session B = 修复 SSE 超时 Bug
       Session C = 重构 gateway 并发

❌ 差：一个 Session 里混着创建 Skill + 修 Bug + 问天气
```

**为什么？** 一个 session 对应一个独立任务，提炼测例时可以直接复用，无需人工拆分。混杂的 session 很难提炼——上下文纠缠，难以确定 initial_state。

### 🔧 2. 开发类任务遵循 dev-workflow

要求 Agent 遵循 dev-workflow Skill 的规范（文档先行 → 任务拆解 → 逐步开发 → 测试验证 → Git 提交），这样产出的对话：

- **结构清晰**：有明确的阶段划分，容易提炼为多轮 query
- **可验证**：有 REQUIREMENTS.md、测试代码，可以转化为 success_criteria
- **可复现**：有 DEVLOG.md 记录决策过程，帮助理解任务意图

### 📁 3. 任务完成后保留工作文件

在你确认要提炼测例**之前**，不要大幅改动相关文件：

```
✅ 保留：
- 创建的 Skill 目录（作为 reference 参考答案）
- Session JSONL 文件（作为 query 提炼来源）
- 项目代码的 Git 历史（用 extract_git_snapshot.py 截取 initial_state）

❌ 避免：
- 提炼前就删除或大幅重构了 Agent 产出的文件
- 清理了 session 历史
- 覆盖了 Git 提交历史（rebase/force push）
```

### 📝 4. 给 Agent 的指令尽量完整

好的指令 = 好的测例 query：

```
✅ "创建一个 doubao-search skill，支持 search/summarize/fetch-url 三个子命令，
    从 config.json 读取 API 配置，按 dev-workflow 规范开发"

❌ "帮我搞个搜索功能"
```

完整的指令让测例的 query.md 可以直接从对话中提取，减少人工补充。

### 🔄 5. 定期扫描 + 提炼

建议的节奏：

```
每 1-2 周：
  1. 运行 eval-session-scanner → 扫描新 session → 更新 CASE_REGISTRY.md
  2. 审核候选清单 → 确认要构造的测例
  3. 使用 eval-task-builder skill 构造测例
  4. ./run.sh 验证测例可运行
```

---

## 四、构建测例

### 全生命周期

```
┌────────────────────────────────────────────────────────────┐
│  ① eval-session-scanner                                    │
│     扫描 session → 识别候选 → 更新 CASE_REGISTRY.md         │
│                       ↓                                    │
│  ② 用户审核                                                │
│     去除敏感/无意义的 → 确认构造目标                          │
│                       ↓                                    │
│  ③ eval-task-builder                                       │
│     候选描述 + 来源 session → 完整测例目录                    │
│     （或 eval-task-batch-builder 批量构造）                   │
│                       ↓                                    │
│  ④ ./run.sh --task <id>                                    │
│     Docker 隔离执行 → 自动化验证 → 评测报告                   │
└────────────────────────────────────────────────────────────┘
```

### Step 1：扫描 Session

```bash
# 方式 A：让 Agent 执行
> 请使用 eval-session-scanner skill，扫描从上次整理到现在的 session，
> 整理候选测例清单，并更新 CASE_REGISTRY.md。

# 方式 B：直接运行脚本
python3 eval-bench/skills/eval-session-scanner/scripts/scan_sessions.py \
  --sessions-dir ~/.nanobot/workspace/sessions \
  --since-last-batch \
  --registry eval-bench-data/CASE_REGISTRY.md \
  --output /tmp/scan_result.md
```

扫描会自动排除：纯重启操作、Ping/Hello、过短 session、eval-bench 自身开发过程。

### Step 2：审核候选清单

打开 `eval-bench-data/CASE_REGISTRY.md`，审核扫描结果：

| 分类 | 含义 | 行动 |
|------|------|------|
| 🟢 A类 | 自包含、可复现、验证明确 | 优先构造 |
| 🟡 B类 | 有价值但需简化（复杂 mock、跨通道） | 酌情构造 |
| 🔵 C类 | 轻量任务（小修复、信息查询） | 适合冒烟测试 |
| 🔴 D类 | 不适合（纯运维、含敏感信息） | 跳过 |

重点检查：
- 是否包含 API Key、密码等敏感信息
- 任务是否可在 Docker 中独立运行（无需真实外部服务，或可 mock）
- 成功标准是否明确可验证

### Step 3：构造测例

```bash
# 方式 A：让 Agent 逐个构造
> 请使用 eval-task-builder skill，构造候选测例 A2（创建 calendar-reader Skill）。

# 方式 B：批量构造
> 请使用 eval-task-batch-builder skill，批量构造所有 A 类候选测例。
```

构造产出的测例目录结构：

```
task-{id}-{slug}/
├── task.yaml          # 元数据 + 验证规则
├── query.md           # 多轮 query（从原始对话提炼）
├── initial_state/     # 初始文件状态
│   ├── skills/        #   预置 Skill
│   └── memory/        #   预置记忆
├── mocks/             # Mock 服务脚本
├── verify/            # pytest 验证脚本（可选）
├── eval_prompt.md     # 评价维度（供 Agent 评分用）
└── reference/         # 参考答案（可选）
```

### Step 4：验证测例

```bash
cd eval-bench
./run.sh --task task-003-calendar-reader
```

查看结果：

```bash
ls eval-bench-data/results/<run_id>/
# run_summary.json   — 验证结果 + 执行指标
# trajectory.jsonl   — 完整对话轨迹
# final_state/       — 最终文件快照
# turns.json         — 多轮对话摘要
```

---

## 五、运行评测

### 基本用法

```bash
# 运行内置测例（从 eval-bench-data/tasks/ 查找）
./run.sh --task task-001-doubao-search-skill

# 运行外部测例
./run.sh --task-dir /path/to/my-task

# 指定不同模型
./run.sh --provider volcengine --model ep-xxx --base-url https://ark.cn-beijing.volces.com/api/v3

# 指定 nanobot 源码版本
./run.sh --nanobot-src ~/code/nanobot-experimental
```

### 策略对比

Eval Bench 的核心价值在于**控制变量对比**：

```bash
# 对比不同 LLM
./run.sh --provider anthropic --model claude-sonnet-4-20250514 --run-id claude-sonnet
./run.sh --provider volcengine --model ep-xxx --run-id volcengine-deepseek

# 对比不同 nanobot 版本
git -C ~/code/nanobot checkout main
./run.sh --run-id nanobot-main

git -C ~/code/nanobot checkout feat/new-tool-strategy
./run.sh --run-id nanobot-new-strategy

# 对比结果
diff eval-bench-data/results/nanobot-main/run_summary.json \
     eval-bench-data/results/nanobot-new-strategy/run_summary.json
```

### 结果解读

`run_summary.json` 包含：

```json
{
  "task_id": "task-001",
  "success": true,                    // 所有验证是否通过
  "verification": {"passed": 6, "total": 6},
  "metrics": {
    "tool_calls": 58,                 // 工具调用次数
    "llm_calls": 35,                  // LLM 调用次数
    "prompt_tokens": 850000,          // 输入 token
    "completion_tokens": 25000,       // 输出 token
    "total_tokens": 875000,           // 总 token
    "wall_time_seconds": 305.9        // 耗时
  }
}
```

**关注的指标维度**：

| 指标 | 含义 | 越低越好？ |
|------|------|-----------|
| `success` | 是否通过所有硬性验证 | 必须 true |
| `tool_calls` | Agent 调用工具的次数 | ✅ 越少说明越高效 |
| `total_tokens` | Token 总消耗 | ✅ 越少说明越省钱 |
| `wall_time_seconds` | 端到端耗时 | ✅ 越短越好 |

---

## 六、分发与协作

### 打包框架

```bash
./pack.sh /tmp/eval-bench.tar.gz
```

打包内容包含框架代码 + 配套 Skill，不含本地数据和 nanobot 源码。

### 接收方使用

```bash
tar xzf eval-bench.tar.gz
cd eval-bench
cp .env.example .env && vim .env
mkdir -p ../eval-bench-data/tasks
# 将测例放到 ../eval-bench-data/tasks/ 中
./run.sh --nanobot-src /path/to/nanobot --task task-001
```

### 组织级部署

```
每个 Agent 用户:
  → 安装框架 + Skill
  → 定期扫描自己的 session → 提炼测例
  → 推送测例到组织的测例仓库

框架团队:
  → 汇总所有用户的测例
  → 统一运行评测套件
  → 根据薄弱环节改进框架
  → 回归验证确保不退化
```

---

## 七、技术细节

### 7.1 Docker 隔离架构

每次评测启动两个容器：

```
┌─────────────────────────────────────────────────┐
│  docker-compose                                  │
│                                                  │
│  ┌──────────────┐     ┌───────────────────────┐ │
│  │  mock-api     │◄────│  agent-runner          │ │
│  │  :18080       │     │                       │ │
│  │  模拟外部 API  │     │  nanobot + runner.py  │ │
│  └──────────────┘     └───────────────────────┘ │
│         ▲                       │                │
│    healthcheck              volume mount         │
│    确认就绪后                    │                │
│    才启动 agent           ┌─────┴──────┐         │
│                          │ /eval/task  │ (只读)  │
│                          │ /eval/results│ (读写) │
│                          └────────────┘         │
└─────────────────────────────────────────────────┘
```

### 7.2 镜像分层策略

```
eval-bench-base (构建一次，长期复用，2-5 分钟)
├── python:3.11-slim
├── 系统依赖: git, curl, jq, libxml2 ...
└── Python 依赖: nanobot 的所有 dependencies

eval-bench-agent (每次运行重建，秒级)
├── COPY nanobot 源码 → /opt/nanobot-src/
├── ENV PYTHONPATH=/opt/nanobot-src
└── COPY runner.py

eval-bench-mock (构建一次，mock 脚本通过 volume 挂载)
└── python:3.11-slim
```

**设计理由**：nanobot 源码不 `pip install`，而是直接 COPY + PYTHONPATH。这样可以在不重装依赖的情况下，秒级切换不同版本/分支的 nanobot 源码进行测试。

### 7.3 两类任务

#### Type A：普通任务（创建 Skill、写脚本等）

```
Container (/eval = HOME)
├── /opt/nanobot-src/              ← 驱动 Agent 的框架代码（PYTHONPATH）
├── /eval/.nanobot/workspace/
│   ├── skills/                    ← Agent 在这里创建/修改
│   ├── memory/
│   └── sessions/
├── /eval/task/                    ← 任务定义（只读挂载）
└── /eval/results/                 ← 输出结果
```

`initial_state/skills/` 和 `initial_state/memory/` 自动映射到 workspace 对应目录。

#### Type B：代码修改任务（修改 nanobot 源码）

```
Container (/eval = HOME)
├── /opt/nanobot-src/              ← 驱动 Agent 的框架（不被修改）
├── /eval/.nanobot/workspace/
│   ├── project/nanobot/           ← Agent 要修改的项目代码（git 快照）
│   ├── skills/                    ← dev-workflow 等辅助 Skill
│   └── memory/                    ← 项目上下文
├── /eval/task/
└── /eval/results/
```

**关键区分**：`/opt/nanobot-src/` 是驱动 Agent 思考的框架；`workspace/project/nanobot/` 是 Agent 通过工具读写的"项目代码"——两者完全独立。

通过 `task.yaml` 的 `initial_state_mapping` 控制映射：

```yaml
initial_state_mapping:
  project_code: ".nanobot/workspace/project/nanobot"
  skills: ".nanobot/workspace/skills"
  memory: ".nanobot/workspace/memory"
```

构造 Type B 测例时，使用 `extract_git_snapshot.py` 从 git 历史截取特定版本的源码：

```bash
# 找到某文件首次提交之前的 commit
python3 platform/extract_git_snapshot.py find-before \
  --repo ~/code/nanobot --file nanobot/usage/recorder.py

# 提取那个版本的源码
python3 platform/extract_git_snapshot.py extract \
  --repo ~/code/nanobot --commit abc1234 \
  --output tasks/task-002/initial_state/project_code \
  --include nanobot/ pyproject.toml
```

### 7.4 runner.py 执行流程

runner.py 是容器内的核心执行器，采用函数式架构：

```
setup_nanobot_home(task)         # 初始化 workspace + 生成 config.json
    ↓
load_queries()                   # 解析 query.md 中的多轮 query
    ↓
for each turn:
    run_agent_turn(message, sid) # subprocess 调用 nanobot agent
    ↓
snapshot_final_state(task)       # 快照最终文件状态
    ↓
copy_session_as_trajectory()     # 复制 session JSONL 作为 trajectory
    ↓
run_verification(task)           # 声明式规则 + pytest 脚本
    ↓
collect_metrics(start_time, task)# 工具调用数 + LLM 调用数 + Token 用量
    ↓
输出 run_summary.json
```

Agent 通过 `subprocess.run(["python", "-m", "nanobot", "agent", ...])` 调用，每轮使用相同的 session_id 保持上下文连续。

### 7.5 Mock Provider 命名约定

Mock 服务使用专用 provider 名称，与真实 provider 永不冲突：

```yaml
# config.json (容器内自动生成)
providers:
  volcengine:      {apiKey: "real-key", ...}       # ← Agent LLM
  mock-volcengine: {apiBase: "http://mock-api:18080/api/v3"}  # ← Mock API
```

task.yaml 中通过 `mock_services[].provider_name` 声明 mock provider 名称。query.md 中引导 Agent 从 `providers.mock-volcengine` 读取配置，而 Agent 自身通过 `providers.volcengine` 调用真实 LLM。

### 7.6 验证机制

#### 声明式规则（success_criteria）

在 task.yaml 中声明，runner.py 自动解析执行：

```yaml
success_criteria:
  - "skills/doubao-search/SKILL.md 存在且包含 YAML frontmatter"
  - "skills/doubao-search/scripts/doubao_search.py 存在"
  - "doubao_search.py 从 config.json 读取凭证，不硬编码 API Key"
```

支持的规则语法：

| 语法 | 示例 |
|------|------|
| `path 存在` | `skills/my-skill/SKILL.md 存在` |
| `path 包含 keyword` | `main.py 包含 import` |
| `path 存在且包含 keyword` | `SKILL.md 存在且包含 description` |

路径解析：先在 `workspace/` 下查找，找不到则在 `$HOME/` 下查找。

#### pytest 脚本（verify_script）

适用于复杂验证（如代码修改类任务）：

```yaml
verify_script: "verify/test_analytics.py"
```

pytest 通过环境变量获取路径：`EVAL_HOME`、`WORKSPACE`、`TASK_DIR`、`PROJECT_DIR`。

### 7.7 Token 用量统计

nanobot 的 `UsageRecorder` 模块在每次 LLM 调用后自动写入 `analytics.db`。runner.py 评测完成后直接查询该数据库，按 session_key 汇总 token 消耗，写入 `run_summary.json` 的 `metrics` 字段。

### 7.8 评价机制

评价环节**不在平台内自动执行**，而是由执行任务的 Agent 统一读取 results 目录产出物，结合 `eval_prompt.md` 进行评分：

```
产出物:
  run_summary.json     → 自动化验证结果 + 执行指标
  trajectory.jsonl     → 完整对话轨迹
  final_state/         → 最终文件系统快照
  eval_prompt.md       → 评价维度和评分标准（随测例分发）
```

`eval_prompt.md` 定义软性评价维度（如功能完整性 35%、代码质量 25%、效率 15%……），由 Agent 综合评分。

### 7.9 可对比的策略维度

| 维度 | 示例 |
|------|------|
| **LLM 模型** | Claude Sonnet vs GPT-4o vs Deepseek |
| **系统提示词** | 不同的 AGENTS.md / SOUL.md |
| **工具策略** | 限制工具集、调整工具描述 |
| **记忆策略** | 有/无长期记忆、不同记忆格式 |
| **Skill 加载** | 不同 Skill 组合 |
| **温度参数** | temperature 0 vs 0.3 vs 0.7 |
| **上下文管理** | 不同 consolidation 策略 |
| **nanobot 版本** | 不同分支/commit 的框架代码 |

### 7.10 测例规范速查

完整规范见 [docs/TASK_SPEC.md](docs/TASK_SPEC.md)。最小可运行测例：

```
task-simple/
├── task.yaml
├── query.md
└── mocks/
    └── minimal_mock.py    # 最小 health-check server
```

```yaml
# task.yaml
id: "task-simple"
name: "创建 Hello World Skill"
category: "skill_development"
difficulty: "easy"
success_criteria:
  - "skills/hello-world/SKILL.md 存在"
```

```markdown
# query.md
## Turn 1: 创建 Skill

\```
帮我创建一个 hello-world skill，包含 SKILL.md 和一个简单的 hello.py 脚本。
\```
```

### 7.11 配套 Skill 一览

| Skill | 职责 | 使用场景 |
|-------|------|---------|
| **eval-session-scanner** | 扫描 session → 候选清单 | 定期运行，发现新的可提炼任务 |
| **eval-task-builder** | 候选 → 完整测例目录 | 根据一条描述构造可运行的测例 |
| **eval-task-batch-builder** | 批量构造 | spawn 子 Agent 并行构造多个测例 |
| **eval-framework-maintainer** | 框架改进 + 兼容检查 | 处理构造过程中的框架改进需求 |

---

## 附录：常用命令速查

```bash
# 运行评测
./run.sh --task task-001-doubao-search-skill
./run.sh --task-dir /path/to/my-task
./run.sh --provider openai --model gpt-4o --run-id gpt4o-test

# 强制重建基础镜像（依赖变更时）
./run.sh --rebuild-base --task task-001

# 打包分发
./pack.sh /tmp/eval-bench.tar.gz

# 扫描 session
python3 skills/eval-session-scanner/scripts/scan_sessions.py \
  --sessions-dir ~/.nanobot/workspace/sessions \
  --since "2026-03-01" --output /tmp/scan.md

# 提取 git 快照（Type B 测例用）
python3 platform/extract_git_snapshot.py find-before \
  --repo ~/code/nanobot --file nanobot/usage/recorder.py
python3 platform/extract_git_snapshot.py extract \
  --repo ~/code/nanobot --commit abc1234 \
  --output tasks/task-xxx/initial_state/project_code
```
