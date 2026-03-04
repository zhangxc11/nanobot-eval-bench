# nanobot Eval Platform — Docker 评测方案

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    Eval Runner (Host)                        │
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ Task Loader  │───→│ Docker Runner │───→│  Results +    │  │
│  │ (task.yaml)  │    │ (container)  │    │  Verification │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
│         │                   │                    │           │
│         ▼                   ▼                    ▼           │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ initial_state│    │  trajectory  │    │ run_summary   │  │
│  │ query.md     │    │  final_state │    │ eval_prompt   │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 执行流程

```
1. 加载任务定义 (task.yaml)
2. 构建 Docker 镜像 (run.sh 统一构建: base → agent → mock)
3. docker-compose up (mock-api + agent-runner):
   a. mock-api 启动并通过 healthcheck 确认就绪
   b. agent-runner 启动，runner.py 初始化容器内 workspace:
      - 从 /eval/task/initial_state 复制文件到 /eval/.nanobot/workspace/
      - 动态生成 config.json（含 agent provider + mock provider）
   c. runner.py 按 query.md 多轮注入 user message
   d. 每轮通过 `nanobot agent -m <message> -s <session_id>` 驱动 agent
4. 收集结果:
   a. 执行轨迹 (trajectory.jsonl — 从 session JSONL 复制)
   b. 最终文件系统快照 (final_state/)
   c. 自动化验证 (built-in rules + pytest scripts)
   d. Token 用量统计 (从 analytics.db 查询)
5. 输出 run_summary.json
6. docker-compose down
7. 评价（可选）：由执行任务的智能体统一读取 results + eval_prompt 进行评分
```

## 两类任务架构

### Type A: 普通任务（创建 skill、写脚本等）

```
Container (/eval = HOME)
┌──────────────────────────────────────────────────┐
│  /opt/nanobot-src/           ← 驱动 agent 的 nanobot（PYTHONPATH）
│  /eval/.nanobot/workspace/
│    ├── skills/               ← agent 在这里创建/修改 skill
│    ├── memory/               ← agent 的记忆
│    ├── sessions/             ← 对话记录
│    └── analytics.db          ← token 用量记录（自动创建）
│  /eval/task/                 ← 任务定义（只读挂载）
│  /eval/results/              ← 输出结果
└──────────────────────────────────────────────────┘
```

- `initial_state/skills/` → `workspace/skills/`（默认映射）
- `initial_state/memory/` → `workspace/memory/`（默认映射）
- agent 操作的文件都在 workspace 内
- 验证：检查 workspace 中的文件

### Type B: 代码修改任务（修改 nanobot/webchat 源码）

```
Container (/eval = HOME)
┌──────────────────────────────────────────────────┐
│  /opt/nanobot-src/           ← 驱动 agent 的 nanobot（PYTHONPATH）
│                                 这是"待测试的 agent 框架版本"
│  /eval/.nanobot/workspace/
│    ├── project/
│    │   └── nanobot/          ← 特定 git 版本的 nanobot 源码
│    │       └── nanobot/      │  （agent 要修改的对象）
│    │           ├── agent/
│    │           │   └── loop.py  ← agent 会修改这个文件
│    │           ├── usage/       ← agent 会创建这个模块
│    │           └── ...
│    ├── skills/               ← dev-workflow 等辅助 skill
│    ├── memory/               ← 包含项目上下文的 MEMORY.md
│    ├── sessions/             ← 对话记录
│    └── analytics.db          ← token 用量记录（自动创建）
│  /eval/task/                 ← 任务定义（只读挂载）
│  /eval/results/              ← 输出结果
└──────────────────────────────────────────────────┘
```

**关键区分**：
- `/opt/nanobot-src/`：驱动 agent 的框架代码（通过 PYTHONPATH 生效）
- `workspace/project/nanobot/`：agent 通过工具读写的"项目代码"（任务目标）
- 两者是**完全独立的**，互不干扰

**initial_state_mapping 机制**：
```yaml
# task.yaml 中声明映射关系
initial_state_mapping:
  project_code: ".nanobot/workspace/project/nanobot"
  skills: ".nanobot/workspace/skills"
  memory: ".nanobot/workspace/memory"
```

**构造 initial_state 的工具**：
```bash
# 1. 找到某文件首次提交之前的 commit
python3 platform/extract_git_snapshot.py find-before \
  --repo ~/Documents/code/workspace/nanobot \
  --file nanobot/usage/recorder.py

# 2. 提取那个版本的源码
python3 platform/extract_git_snapshot.py extract \
  --repo ~/Documents/code/workspace/nanobot \
  --commit abc1234 \
  --output tasks/task-002-xxx/initial_state/project_code \
  --include nanobot/ pyproject.toml
```

**验证方式**：
- `verify_script: "verify/test_analytics.py"` — pytest 脚本
- pytest 通过 `PROJECT_DIR` 环境变量找到 agent 修改后的代码
- 可以导入模块、检查文件内容、运行单元测试

## Docker 环境设计

### Mock Provider 命名约定

Mock 服务使用专用的 provider 名称（如 `mock-volcengine`），与真实的 `AGENT_PROVIDER`
永远不会冲突。每个 task 在 `task.yaml` 的 `mock_services[].provider_name` 中声明
mock provider 名称。

```
┌──────────────────────────────────────────────────┐
│  agents.defaults.provider: "volcengine"           │
│  providers:                                       │
│    volcengine:      {apiKey: "real-key", ...}     ← Agent LLM
│    mock-volcengine: {apiKey: "mock", apiBase: "mock:18080/api/v3"}  ← Mock API
│  → 永远不冲突 ✅
└──────────────────────────────────────────────────┘
```

task query 中引导 agent 从 `providers.mock-volcengine` 读取配置，
而 agent 自身通过 `providers.volcengine` 调用真实 LLM。

### Mock API apiBase 约定

mock API 的 `apiBase` 设为 `http://mock-api:18080/api/v3`（含路径前缀），
这样 skill 脚本拼接 `apiBase + "/responses"` 就能正确匹配
mock server 的 `/api/v3/responses` 端点。

mock server 同时支持 `/api/v3/responses`、`/v3/responses`、`/responses` 三种路径，
兼容不同的 apiBase 配置方式。

### 镜像分层策略

```
┌─────────────────────────────────────────────────────────────┐
│  eval-bench-base (构建一次，长期复用)                         │
│  ├── python:3.11-slim (支持 REGISTRY_MIRROR 镜像加速)        │
│  ├── 系统依赖: git, curl, jq, libxml2, libjpeg ...          │
│  └── Python 依赖: requirements-deps.txt (支持 PIP_INDEX_URL) │
│      (nanobot 的所有 dependencies，但不装 nanobot 本身)       │
├─────────────────────────────────────────────────────────────┤
│  eval-bench-agent (每次换版本重建，秒级)                      │
│  ├── COPY nanobot-src/ → /opt/nanobot-src/                   │
│  ├── ENV PYTHONPATH=/opt/nanobot-src                         │
│  └── COPY runner.py → /opt/eval/runner.py                    │
├─────────────────────────────────────────────────────────────┤
│  eval-bench-mock (构建一次，mock 脚本通过 volume 挂载)        │
│  ├── python:3.11-slim                                        │
│  └── 启动命令: python3 /mocks/volcengine_mock.py             │
└─────────────────────────────────────────────────────────────┘
```

**设计理由**:
- 依赖安装耗时 2-5 分钟，提前打包到 base 镜像
- nanobot 源码不 pip install，直接 COPY + PYTHONPATH，方便测试任意版本
- 评测可能涉及 nanobot core 代码改动（tool 策略、context 管理等），不只是换 API

### docker-compose.yaml

```yaml
services:
  # Mock API 服务 — 给 agent 创建的 skill 脚本调用
  mock-api:
    image: eval-bench-mock:latest
    volumes:
      - ../tasks/${TASK_ID}/mocks:/mocks:ro
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:18080/health')"]
      interval: 3s
      timeout: 2s
      retries: 5

  # Agent 执行环境
  agent-runner:
    image: eval-bench-agent:latest
    depends_on:
      mock-api:
        condition: service_healthy
    volumes:
      - ../tasks/${TASK_ID}:/eval/task:ro       # 任务定义（只读）
      - ../results/${RUN_ID}:/eval/results      # 结果输出
    environment:
      - AGENT_API_KEY=${AGENT_API_KEY}
      - AGENT_PROVIDER=${AGENT_PROVIDER:-anthropic}
      - AGENT_MODEL=${AGENT_MODEL:-claude-sonnet-4-20250514}
      - AGENT_API_BASE=${AGENT_API_BASE:-}
      - MOCK_API_URL=http://mock-api:18080
      - MAX_TOOL_CALLS=${MAX_TOOL_CALLS:-150}
      - TIMEOUT_MINUTES=${TIMEOUT_MINUTES:-30}
      - TASK_DIR=/eval/task
      - RESULTS_DIR=/eval/results
      - HOME=/eval
```

## 核心组件

### 1. runner.py — 容器内执行器

runner.py 是容器内的核心组件，负责完整的评测生命周期。采用函数式架构：

```python
# 主要函数
setup_nanobot_home(task)       # 初始化 workspace（支持默认映射 + custom mapping）
_write_config(task)            # 动态生成 config.json（agent provider + mock providers）
load_queries()                 # 解析 query.md 中的多轮 query
run_agent_turn(message, sid)   # 通过 subprocess 调用 nanobot agent 执行单轮对话
snapshot_final_state(task)     # 快照最终文件状态（支持 snapshot_dirs）
copy_session_as_trajectory()   # 复制 session JSONL 作为 trajectory
run_verification(task)         # 运行验证（built-in rules + pytest）
collect_metrics(start_time, task)  # 收集指标（tool calls, LLM calls, token usage）
main()                         # async 主函数，编排上述流程
```

**关键设计**：
- Agent 通过 `subprocess.run(["python", "-m", "nanobot", "agent", ...])` 调用
- 每轮对话使用相同的 session_id，保持上下文连续
- Token 用量从 nanobot 自动创建的 `analytics.db` 中查询（`token_usage` 表）
- 验证支持两种模式：声明式规则（success_criteria）和 pytest 脚本（verify_script）

### 2. 评价机制

评价环节**不在平台内自动执行**，而是由执行任务的智能体统一读取 results 目录中的产出物，
结合 `eval_prompt.md` 进行评分。

**产出物**（供评价使用）：
- `results/{run_id}/run_summary.json` — 自动化验证结果 + 执行指标（含 token 用量）
- `results/{run_id}/trajectory.jsonl` — 完整对话轨迹
- `results/{run_id}/final_state/` — 最终文件系统快照
- `results/{run_id}/turns.json` — 多轮对话摘要
- `results/{run_id}/pytest_report.json` — pytest 详细报告（代码修改类任务）
- `tasks/{task_id}/eval_prompt.md` — 评价维度和评分标准

**评价流程**：
1. 平台运行完毕后，results 目录包含所有产出物
2. 智能体读取 eval_prompt.md 获取评价维度和标准
3. 智能体读取 run_summary.json、trajectory、final_state 等
4. 智能体综合评分并输出 eval_result.md

### 3. Token 用量统计

nanobot 的 `UsageRecorder` 模块（`nanobot/usage/recorder.py`）在每次 LLM 调用后
自动将 token 用量写入 `~/.nanobot/workspace/analytics.db` 的 `token_usage` 表。

runner.py 在评测完成后，通过 SQLite 直接查询该数据库，按 session_key 汇总 token 消耗：

```python
# analytics.db schema
CREATE TABLE token_usage (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    session_key       TEXT NOT NULL,
    model             TEXT NOT NULL,
    prompt_tokens     INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens      INTEGER DEFAULT 0,
    llm_calls         INTEGER DEFAULT 0,
    started_at        TEXT NOT NULL,
    finished_at       TEXT NOT NULL
);
```

Token 用量包含在 `run_summary.json` 的 `metrics` 中：
```json
{
  "metrics": {
    "tool_calls": 31,
    "llm_calls": 35,
    "prompt_tokens": 850000,
    "completion_tokens": 25000,
    "total_tokens": 875000,
    "wall_time_seconds": 305.9,
    "files_created": 12
  }
}
```

## 使用方式

### 单任务评测

```bash
# 评测单个任务（默认 task-001）
./run.sh

# 指定任务
./run.sh --task task-002-token-usage-analytics

# 指定 nanobot 源码版本
./run.sh --task task-001-doubao-search-skill --nanobot-src ~/code/nanobot-experimental
```

### 多策略对比

```bash
# 对比不同 LLM
./run.sh --provider anthropic --model claude-sonnet-4-20250514 --run-id claude-sonnet
./run.sh --provider volcengine --model ep-xxx --base-url https://ark.cn-beijing.volces.com/api/v3 --run-id volcengine

# 对比不同 nanobot 版本
./run.sh --nanobot-src ~/code/nanobot-baseline --run-id baseline
./run.sh --nanobot-src ~/code/nanobot-improved --run-id improved
```

### 全套评测（TODO）

```bash
# 运行所有任务
python3 eval.py run-all --agent ./nanobot-v1 --output ./results/run-001
```

## 目录结构

```
eval-bench/
├── README.md                      # 项目说明 + 任务列表
├── DEPLOY.md                      # 部署指南
├── run.sh                         # 一键运行脚本（构建镜像 + 启动容器）
├── pack.sh                        # 打包分发
├── .env.example                   # 环境变量模板
├── docs/
│   ├── REQUIREMENTS.md            # 需求文档
│   ├── ARCHITECTURE.md            # 架构设计（引用本文件）
│   └── DEVLOG.md                  # 开发日志
├── platform/
│   ├── DESIGN.md                  # 本文件 — 详细技术方案
│   ├── Dockerfile.base            # 基础镜像（依赖安装）
│   ├── Dockerfile.agent           # Agent 镜像（nanobot 源码 + runner）
│   ├── Dockerfile.mock            # Mock 服务镜像
│   ├── docker-compose.yaml        # 编排
│   ├── runner.py                  # 容器内运行器（执行 + 验证 + 指标收集）
│   ├── extract_git_snapshot.py    # Git 快照提取工具（Type B 任务用）
│   └── requirements-deps.txt      # Python 依赖列表
├── nanobot-src/                   # nanobot 源码（运行时同步，不提交）
├── tasks/
│   ├── task-001-doubao-search-skill/
│   │   ├── task.yaml              # 任务定义
│   │   ├── query.md               # 多轮 query
│   │   ├── eval_prompt.md         # 评价 prompt
│   │   ├── initial_state/         # 初始文件状态
│   │   ├── reference/             # 参考答案（可选）
│   │   └── mocks/                 # Mock 服务脚本
│   └── task-002-token-usage-analytics/
│       ├── task.yaml
│       ├── query.md
│       ├── eval_prompt.md
│       ├── initial_state/         # 含 project_code/ (git 快照)
│       ├── verify/                # pytest 验证脚本
│       └── mocks/
└── results/                       # 评测结果（不提交）
    └── {run_id}/
        ├── run_config.json        # 运行配置
        ├── run_summary.json       # 验证结果 + 执行指标（含 token 用量）
        ├── trajectory.jsonl       # 完整对话轨迹
        ├── final_state/           # 最终文件快照
        ├── turns.json             # 多轮对话摘要
        ├── docker_output.log      # Docker 完整日志
        ├── pytest_report.json     # pytest 报告（Type B 任务）
        └── eval_result.md         # 评价结果（由智能体生成）
```

## 验证机制

### 声明式规则 (success_criteria)

在 task.yaml 中声明，runner.py 的 `verify_criterion()` 解析执行：

```yaml
success_criteria:
  - "skills/doubao-search/SKILL.md 存在且包含 YAML frontmatter"
  - "skills/doubao-search/scripts/doubao_search.py 存在且可执行"
  - ".nanobot/workspace/project/nanobot/nanobot/usage/recorder.py 存在"
  - ".nanobot/workspace/project/nanobot/nanobot/agent/loop.py 包含 usage"
```

支持的规则类型：
- `"path 存在"` / `"path exists"` — 文件/目录存在性
- `"path 包含 keyword"` / `"path contains keyword"` — 文件内容包含
- `"path 存在且包含 keyword"` — 组合规则
- Task-specific 特殊规则（如检查子命令、mock API 调用）

### pytest 脚本 (verify_script)

```yaml
verify_script: "verify/test_analytics.py"
```

pytest 通过环境变量定位文件：
- `EVAL_HOME`: `/eval`
- `WORKSPACE`: `/eval/.nanobot/workspace`
- `PROJECT_DIR`: agent 修改的项目代码目录（code_modification 任务）
- `TASK_DIR`: `/eval/task`

## 策略维度

评测平台可以对比的策略维度包括：

| 维度 | 示例 |
|------|------|
| **LLM 模型** | Claude Sonnet vs GPT-4o vs Deepseek |
| **系统提示词** | 不同的 AGENTS.md / SOUL.md |
| **工具策略** | 限制工具集、调整工具描述 |
| **记忆策略** | 有/无长期记忆、不同记忆格式 |
| **Skill 加载** | 加载不同 skill 组合 |
| **循环策略** | max_iterations、tool_call_limit |
| **温度参数** | temperature 0 vs 0.3 vs 0.7 |
| **上下文管理** | 不同的 consolidation 策略 |

## 扩展计划

### Phase 1: MVP（当前）
- 手动提炼 3-5 个评测任务
- 单容器执行 + 自动化验证
- JSON 报告

### Phase 2: 自动化
- 自动从 session 历史提炼任务
- 并行多容器执行
- Web Dashboard 展示结果

### Phase 3: CI 集成
- 每次代码提交自动跑评测
- 回归检测（新策略不能比旧策略差）
- 评分趋势图
