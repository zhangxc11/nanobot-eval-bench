# eval-bench 架构设计

> 详细技术方案见 [platform/DESIGN.md](../platform/DESIGN.md)

## 架构概览

```
Host (run.sh)
├── 1. 构建镜像: base → agent, mock
├── 2. docker-compose up (mock-api + agent-runner)
│     ├── mock-api: 提供 Mock LLM API
│     └── agent-runner: 执行 nanobot + runner.py
├── 3. docker-compose down
├── 4. 评价（可选）：由执行任务的智能体统一评价
└── 5. 生成报告
```

## 镜像分层

```
eval-bench-base (构建一次，长期复用)
├── python:3.11-slim
├── 系统依赖: git, curl, jq, libxml2 ...
└── Python 依赖: requirements-deps.txt

eval-bench-agent (每次换版本重建，秒级)
├── COPY nanobot-src/ → /opt/nanobot-src/
├── ENV PYTHONPATH=/opt/nanobot-src
└── COPY runner.py → /opt/eval/runner.py

eval-bench-mock (每个 task 独立 mock)
└── COPY mocks/ → /opt/mock/
```

## 容器内目录布局

### Type A: 普通任务

```
/eval/                          ← HOME
├── .nanobot/workspace/
│   ├── skills/                 ← agent 创建/修改 skill
│   ├── memory/                 ← agent 记忆
│   └── sessions/               ← 对话记录
├── task/                       ← 任务定义（只读）
└── results/                    ← 输出结果
```

### Type B: 代码修改任务

```
/eval/
├── .nanobot/workspace/
│   ├── project/nanobot/        ← agent 要修改的源码
│   ├── skills/                 ← dev-workflow 等辅助 skill
│   ├── memory/                 ← 项目上下文 MEMORY.md
│   └── sessions/
├── task/
└── results/
```

- `/opt/nanobot-src/`：驱动 agent 的框架代码（PYTHONPATH）
- `workspace/project/nanobot/`：agent 通过工具读写的项目代码（任务目标）
- 两者完全独立，互不干扰

## 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| **run.sh** | `run.sh` | 入口脚本：构建镜像、启动容器、收集结果 |
| **runner.py** | `platform/runner.py` | 容器内执行器：初始化环境→注入 query→收集结果→验证 |
| **docker-compose** | `platform/docker-compose.yaml` | 编排 mock-api + agent-runner |
| **extract_git_snapshot** | `platform/extract_git_snapshot.py` | 从 git 历史提取特定版本源码（Type B 任务用） |
| **pack.sh** | `pack.sh` | 打包分发用 |

## Mock Provider 命名约定

Mock 服务使用专用 provider 名称，与真实 provider 永不冲突：

```
providers:
  volcengine:      {apiKey: "real-key", ...}       ← Agent LLM
  mock-volcengine: {apiBase: "mock:18080/api/v3"}  ← Mock API
```

task.yaml 中通过 `mock_services[].provider_name` 声明 mock provider 名称。

## 验证机制

### 声明式规则 (verify_criterion)

```yaml
verify_criterion:
  - type: file_exists
    path: ".nanobot/workspace/skills/doubao-search/SKILL.md"
  - type: file_contains
    path: ".nanobot/workspace/skills/doubao-search/scripts/search.py"
    contains: "def search"
```

### 自定义 pytest (verify_script)

```yaml
verify_script: "verify/test_analytics.py"
```

pytest 通过 `PROJECT_DIR` 环境变量定位 agent 修改后的代码。

## 评价机制

评价环节不在平台内自动执行，而是由执行任务的智能体统一读取 results 目录产出物，
结合 `eval_prompt.md` 进行评分。

**产出物**：
- `run_summary.json` — 验证结果 + 执行指标
- `trajectory.jsonl` — 完整对话轨迹
- `final_state/` — 文件系统快照
- `turns.json` — 多轮对话摘要

**eval_prompt.md 示例维度**：
- 功能完整性（35%）
- 代码质量（25%）
- 兼容性（20%）
- 效率（10%）
- 规范遵循（10%）

## 测试设计

### 平台级测试
- runner.py 各函数单元测试（TODO）
- docker-compose 集成测试：mock 启动→agent 执行→结果收集

### 任务级测试
- 每个 task 的 verify_criterion / verify_script 即为该任务的验证用例
- eval_prompt.md 定义软性评价标准

## 策略对比维度

| 维度 | 示例 |
|------|------|
| LLM 模型 | Claude Sonnet vs GPT-4o vs Deepseek |
| 系统提示词 | 不同的 AGENTS.md / SOUL.md |
| 工具策略 | 限制工具集、调整工具描述 |
| 记忆策略 | 有/无长期记忆、不同格式 |
| Skill 加载 | 不同 skill 组合 |
| 温度参数 | temperature 0 vs 0.3 vs 0.7 |
| 上下文管理 | 不同 consolidation 策略 |
