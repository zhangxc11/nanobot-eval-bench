# 测例格式详细说明

> 本文件是 eval-task-builder SKILL.md §2 的详细展开。

---

## query.md 多轮格式

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

---

## task.yaml 完整字段说明

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

# 初始状态映射（将 initial_state/ 下的目录映射到 agent 的工作环境）
# 注意：需要 git 仓库的测例应提前构建好完整仓库（含 .git），直接通过映射复制
#
# ⚠️ 路径映射规则（runner.py 逻辑）：
#   src_path = TASK_DIR/initial_state/{key}
#   dest_path = EVAL_HOME/{value}     ← 即 /eval/{value}
#
# 容器目录结构：
#   /eval                          ← EVAL_HOME
#   /eval/.nanobot                 ← NANOBOT_HOME
#   /eval/.nanobot/workspace       ← WORKSPACE（agent 的工作目录）
#
# 因此 value 必须以 ".nanobot/workspace/" 为前缀才能放到 agent workspace 下！
# 常见错误：写成 "nanobot_core/" 会放到 /eval/nanobot_core/（workspace 外面）
#
# ⚠️ PROJECT_DIR 约束（runner.py 三级优先级）：
# 如果 verify 脚本依赖 PROJECT_DIR 环境变量，推荐在 task.yaml 中使用
# 顶层 project_dir 字段显式声明路径。也可在 mapping 中使用 project_code key。
# 详见 docs/PROJECT_DIR.md。
initial_state_mapping:
  "project_code/": ".nanobot/workspace/project/{project_name}/"
  "skills/": ".nanobot/workspace/skills/"
  "memory/": ".nanobot/workspace/memory/"

# 验证配置 — 必须使用 verify_script
verify_script: "verify/test_task.py"

# ⚠️ DEPRECATED: success_criteria 已废弃，runner.py 不再执行
# 所有测例必须使用 verify_script 提供 pytest 验证脚本
```

---

## verify/test_task.py 结构

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
| `PROJECT_DIR` | 由 task.yaml 决定 | 项目代码目录。runner.py 三级优先级：1) `project_dir` 字段 → `EVAL_HOME/{value}`；2) mapping 中 `project_code` key；3) fallback 目录探测。详见 docs/PROJECT_DIR.md。verify 脚本应设 fallback 默认值 |

---

## eval_prompt.md 结构

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

## 路径映射一致性详解

### runner.py 映射逻辑

```
容器目录结构：
  /eval                          ← EVAL_HOME (= $HOME)
  /eval/.nanobot                 ← NANOBOT_HOME
  /eval/.nanobot/workspace       ← WORKSPACE（agent 的工作目录）

mapping 执行逻辑（runner.py setup_nanobot_home）：
  for src_name, dest_rel in initial_state_mapping.items():
      src_path = TASK_DIR / "initial_state" / src_name   # 源：测例目录下
      dest_path = EVAL_HOME / dest_rel                    # 目标：/eval/{dest_rel}
```

### ⚠️ 高频错误（Batch 4 质检中 5/15 测例犯此错误）

| 错误写法 | 实际效果 | 正确写法 | 实际效果 |
|---------|---------|---------|---------|
| `"nanobot_core/": "nanobot_core/"` | → `/eval/nanobot_core/` ❌ | `"nanobot_core/": ".nanobot/workspace/nanobot_core/"` | → `/eval/.nanobot/workspace/nanobot_core/` ✅ |
| `"web_chat/": "web_chat/"` | → `/eval/web_chat/` ❌ | `"web_chat/": ".nanobot/workspace/web_chat/"` | → `/eval/.nanobot/workspace/web_chat/` ✅ |
| `"initial_state/project/": "project/"` | key 含 initial_state/ 前缀 ❌ | `"project/": ".nanobot/workspace/project/"` | key 直接是 initial_state 下的目录名 ✅ |

**核心规则**：
1. **key** = initial_state/ 目录下的子目录名（**不含** `initial_state/` 前缀）
2. **value** = 相对于 `/eval` 的目标路径（要放到 workspace 下则**必须**以 `.nanobot/workspace/` 开头）

### verify 脚本中的路径

```python
# verify 脚本中的正确写法 — 使用环境变量，不硬编码路径
WORKSPACE = os.environ.get("WORKSPACE", ".")
PROJECT_DIR = os.environ.get("PROJECT_DIR", os.path.join(WORKSPACE, "project"))
RESULTS_DIR = os.environ.get("RESULTS_DIR", "/eval/results")
TASK_ID = os.environ.get("TASK_ID", "")
```

### 自检清单

构造完 task.yaml 后，逐项验证：
- [ ] mapping 的每个 key 在 `initial_state/` 目录下确实存在
- [ ] mapping 的每个 value 以 `.nanobot/workspace/` 开头（除非有特殊理由放到 workspace 外）
- [ ] verify 脚本中 `PROJECT_DIR` 的默认值与 mapping value 对应（如 `WORKSPACE + "/nanobot_core"`）
- [ ] **如果 verify 脚本使用 `PROJECT_DIR`，task.yaml 中需有 `project_dir` 字段或 mapping 中有 `project_code` key**（见 docs/PROJECT_DIR.md）
- [ ] dry-run：在 initial_state 上模拟 mapping 后的路径，verify 脚本能正常执行（fail 因检查不满足，而非路径找不到）
