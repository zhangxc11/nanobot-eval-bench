# 测例规范 (Task Specification)

本文档定义了 eval-bench 评测框架接受的测例格式。任何人按此规范构造的测例目录，
都可以通过 `./run.sh --task-dir <path>` 运行。

## 目录结构

```
task-{id}-{slug}/
├── task.yaml          # 必须 — 任务元数据 + 验证规则
├── query.md           # 必须 — 用户 query（单轮或多轮）
├── initial_state/     # 可选 — 初始文件状态
│   ├── skills/        #   预置 skill（默认映射到 workspace/skills/）
│   ├── memory/        #   预置记忆（默认映射到 workspace/memory/）
│   └── project_code/  #   项目代码（Type B，需配合 initial_state_mapping）
├── verify/            # 可选 — pytest 验证脚本
│   └── test_xxx.py
├── mocks/             # 可选 — Mock 服务脚本
│   ├── start.sh       #   必须 — 统一启动入口（框架执行 bash /mocks/start.sh）
│   └── xxx_mock.py    #   Mock 服务实现
├── eval_prompt.md     # 可选 — 评价 prompt（供智能体评分用）
└── reference/         # 可选 — 参考答案
```

## task.yaml 字段说明

### 必填字段

```yaml
id: "task-001"                    # 唯一标识符
name: "创建豆包联网搜索 Skill"      # 人类可读名称
```

### 推荐字段

```yaml
category: "skill_development"     # 分类（见下方分类列表）
difficulty: "medium"              # 难度: easy / medium / hard / expert
type: "general"                   # 任务类型: general / code_modification
tags: ["skill", "api", "testing"] # 标签
description: |                    # 详细描述
  从零创建一个联网搜索 skill...

source_sessions:                  # 来源 session（追溯用）
  - "webchat_1772349033"
```

### 验证字段

```yaml
# pytest 脚本（必须）
verify_script: "verify/test_analytics.py"
```

> **⚠️ Deprecated**: `success_criteria`（声明式规则列表）已废弃，不再被 runner.py 执行。
> 所有测例必须使用 `verify_script` 提供 pytest 验证脚本。

### 可选字段

```yaml
# 多轮对话配置
multi_turn: true
interaction_count: 4              # 预期用户交互次数

# 资源限制
resource_limits:
  max_tool_calls: 150
  timeout_minutes: 30

# Type B 专用: 文件映射
initial_state_mapping:
  project_code: ".nanobot/workspace/project/nanobot"
  skills: ".nanobot/workspace/skills"
  memory: ".nanobot/workspace/memory"

# Type B 专用: 快照目录（收集到 results/final_state/）
snapshot_dirs:
  - ".nanobot/workspace/project/nanobot/nanobot"

# Mock 服务配置
environment:
  mock_services:
    - name: "volcengine-mock"
      provider_name: "mock-volcengine"   # 容器内 config.json 中的 provider 名
      port: 18080

# 评价维度
eval_dimensions:
  - name: "功能完整性"
    weight: 40
    criteria: "所有功能是否实现"
  - name: "代码质量"
    weight: 30
    criteria: "代码结构、错误处理"

# config.json 覆盖（高级）
config_overrides:
  tools:
    exec:
      timeout: 120
```

## query.md 格式

### 单轮

```markdown
## Turn 1: 主要指令

\```
你的完整 query 内容
\```
```

### 多轮

```markdown
## Turn 1: 初始需求

\```
第一轮 query
\```

## Turn 2: 补充信息

\```
第二轮 query（可以引用第一轮的结果）
\```

## Turn 3: 修正与确认

\```
第三轮 query
\```
```

**注意**：
- 每个 Turn 的内容必须在 ``` 代码块内
- Turn 标题格式: `## Turn N: 描述`
- 多轮对话中，后续 Turn 可以模拟用户对 agent 输出的反馈

## 验证规则语法

### ~~声明式规则 (success_criteria)~~ — **DEPRECATED**

> **已废弃**：`success_criteria` 声明式规则已在 Phase 8 (P2) 中废弃。
> runner.py 不再执行 `success_criteria` 中的规则，仅打印 WARNING 日志。
> 所有测例必须使用 `verify_script` 提供 pytest 验证脚本。

### pytest 脚本 (verify_script) — **必须**

pytest 脚本通过环境变量获取路径：

| 变量 | 值 | 说明 |
|------|-----|------|
| `EVAL_HOME` | `/eval` | 容器 HOME |
| `WORKSPACE` | `/eval/.nanobot/workspace` | nanobot workspace |
| `NANOBOT_HOME` | `/eval/.nanobot` | nanobot 配置目录 |
| `TASK_DIR` | `/eval/task` | 任务定义目录 |
| `RESULTS_DIR` | `/eval/results` | 结果输出目录 |
| `TASK_ID` | task.yaml 中的 id | 任务 ID |
| `TASK_NAME` | task.yaml 中的 name | 任务名称 |
| `PROJECT_DIR` | 由 initial_state_mapping 决定 | 项目代码目录（Type B） |

## 分类列表

| 分类 | 说明 | 示例 |
|------|------|------|
| `skill_development` | 创建新 Skill | 联网搜索、文档操作 |
| `code_modification` | 修改框架源码 | Token 统计、Bug 修复 |
| `bug_diagnosis` | 诊断和修复 Bug | Provider 配置问题 |
| `document_generation` | 生成文档/报告 | 技术提纲、需求文档 |
| `configuration` | 配置管理 | Provider 热加载 |
| `data_processing` | 数据处理/分析 | 日志分析、格式转换 |
| `integration` | 集成/对接 | 飞书、GitHub |

## Mock 服务

### 启动入口约定

每个测例的 `mocks/` 目录**必须**提供 `start.sh` 作为统一启动入口。
框架通过 `bash /mocks/start.sh` 启动 mock 容器，不做任何自动检测。

**`start.sh` 示例**（最常见的单脚本场景）：
```bash
#!/bin/bash
# Mock 服务启动脚本
exec python3 /mocks/minimal_mock.py
```

**高级场景**（多进程、环境初始化等）：
```bash
#!/bin/bash
# 设置环境变量
export MOCK_PORT=18080
export DATA_DIR=/mocks/fixtures

# 启动 mock 服务
exec python3 /mocks/my_custom_mock.py
```

### mock 脚本规范

mock 脚本放在 `mocks/` 目录下，由 `start.sh` 负责启动。

**要求**：
- 监听 `0.0.0.0:18080`
- 提供 `/health` 端点（返回 200）
- 模拟目标 API 的核心端点

**命名约定**：
- Mock provider 名称使用 `mock-` 前缀（如 `mock-volcengine`）
- 永远不会与真实的 `AGENT_PROVIDER` 冲突

### 无 Mock 的任务

如果任务不需要 Mock API，仍需提供 `mocks/` 目录，包含最小 mock 脚本 + `start.sh`
（docker-compose 会挂载该目录，容器依赖 health check 通过才启动 agent）。

最小 mock 脚本（`minimal_mock.py`）：
```python
#!/usr/bin/env python3
"""Minimal mock server — no external API needed for this task."""
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')
    def log_message(self, *args): pass

HTTPServer(("0.0.0.0", 18080), Handler).serve_forever()
```

对应的 `start.sh`：
```bash
#!/bin/bash
exec python3 /mocks/minimal_mock.py
```

## 示例

### 最简测例（Type A，单轮，pytest 验证）

```
task-simple-example/
├── task.yaml
├── query.md
├── verify/
│   └── test_hello.py
└── mocks/
    ├── start.sh
    └── minimal_mock.py
```

```yaml
# task.yaml
id: "task-simple"
name: "创建 Hello World Skill"
category: "skill_development"
difficulty: "easy"
verify_script: "verify/test_hello.py"
```

```markdown
# query.md
## Turn 1: 创建 Skill

\```
帮我创建一个 hello-world skill，包含 SKILL.md 和一个简单的 hello.py 脚本。
\```
```

### 复杂测例（Type B，多轮，pytest 验证）

参考 `tasks/task-002-token-usage-analytics/` 的完整结构。
