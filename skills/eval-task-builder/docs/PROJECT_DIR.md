# PROJECT_DIR 环境变量详解

> 本文件详细说明 PROJECT_DIR 环境变量的 runner.py 逻辑、推荐用法和常见错误。
> 来源：task-032 评测反馈（2026-03-12）。

---

## 背景

因 mapping 使用 `nanobot_repo` 而非 `project_code` 作为 key，
导致 runner.py 走入 fallback 逻辑，`PROJECT_DIR` 被错误设为父目录，27/30 测试误判 FAIL。
**已修复**：runner.py 新增 `project_dir` 字段支持（Phase 10, R10.6）。

---

## runner.py 当前逻辑（三级优先级）

```python
# 优先级 1: task.yaml 显式 project_dir 字段（推荐）
project_dir_value = task.get("project_dir")
if project_dir_value:
    env["PROJECT_DIR"] = str(EVAL_HOME / project_dir_value)

# 优先级 2: mapping 中的 project_code key（向后兼容）
elif "project_code" in mapping:
    env["PROJECT_DIR"] = str(EVAL_HOME / mapping["project_code"])

# 优先级 3: fallback 目录探测（不推荐依赖，可能指向错误目录）
else:
    for candidate in ["project", "project_code"]:
        ...
```

---

## 推荐做法

在 task.yaml 中使用 `project_dir` 字段显式声明项目目录：

```yaml
# ✅ 推荐：使用 project_dir 字段
project_dir: ".nanobot/workspace/project/nanobot"

initial_state_mapping:
  nanobot_repo: ".nanobot/workspace/project/nanobot"
  memory: ".nanobot/workspace/memory"
```

```yaml
# ✅ 也可以：mapping 中使用 project_code key（向后兼容）
initial_state_mapping:
  project_code: ".nanobot/workspace/project/nanobot"
  memory: ".nanobot/workspace/memory"
```

```yaml
# ❌ 错误：mapping 中没有 project_code key，也没有 project_dir 字段
initial_state_mapping:
  nanobot_repo: ".nanobot/workspace/project/nanobot"
  memory: ".nanobot/workspace/memory"
```

---

## 影响范围

所有 verify 脚本中使用 `os.environ.get("PROJECT_DIR")` 的测例。

---

## 容器目录结构参考

```
/eval                          ← EVAL_HOME (= $HOME)
/eval/.nanobot                 ← NANOBOT_HOME
/eval/.nanobot/workspace       ← WORKSPACE（agent 的工作目录）
```

`project_dir` 字段的值是相对于 EVAL_HOME 的路径，因此：
- `project_dir: ".nanobot/workspace/project/nanobot"` → `PROJECT_DIR=/eval/.nanobot/workspace/project/nanobot`

verify 脚本中应设 fallback 默认值：
```python
PROJECT_DIR = os.environ.get("PROJECT_DIR", os.path.join(WORKSPACE, "project/nanobot"))
```
