# PROJECT_DIR 环境变量详解

> 本文件详细说明 PROJECT_DIR 环境变量的 runner.py 逻辑和使用规范。
> 更新于 Phase 11（2026-03-13）：简化为唯一方式 + 容错兜底。

---

## 背景

Phase 10 引入 `project_dir` 字段时保留了三级优先级（project_dir > project_code key > fallback），
导致构造者仍容易写错（把 mapping key 误写为 project_dir 值）。
**Phase 11 简化**：`project_dir` 字段为唯一设置 PROJECT_DIR 的方式，废弃其他路径。

---

## runner.py 当前逻辑（Phase 11）

```python
# 唯一方式: task.yaml 的 project_dir 字段
project_dir_value = task.get("project_dir")
if project_dir_value:
    candidate = EVAL_HOME / project_dir_value
    if candidate.exists():
        env["PROJECT_DIR"] = str(candidate)
    elif project_dir_value in mapping:
        # 容错: 误写了 mapping key，自动修正 + WARNING
        resolved = EVAL_HOME / mapping[project_dir_value]
        env["PROJECT_DIR"] = str(resolved)
        print(f"WARNING: project_dir is a mapping key, auto-resolved")
    else:
        env["PROJECT_DIR"] = str(candidate)
        print(f"WARNING: project_dir does not exist")
# 不再支持 project_code key 推导和 fallback 探测
```

---

## 规范要求

### task.yaml 必须

```yaml
# ✅ 正确：project_dir = mapping 的 value（完整路径）
project_dir: ".nanobot/workspace/nanobot_core"

initial_state_mapping:
  "nanobot_core": ".nanobot/workspace/nanobot_core"
```

### 约束条件

1. 所有 `type: code_modification` 测例 **必须** 有 `project_dir` 字段
2. 值 **必须** 以 `.nanobot/workspace/` 开头
3. 值 **必须** 与 `initial_state_mapping` 中某个 value 一致或是其子路径
4. verify 脚本的 PROJECT_DIR fallback 值 **必须** 与 task.yaml project_dir 一致

### 常见错误

```yaml
# ❌ 错误：写了 mapping 的 key 而非 value
project_dir: "nanobot_core"   # 应为 ".nanobot/workspace/nanobot_core"

# ❌ 错误：缺少 .nanobot/workspace/ 前缀
project_dir: "project/nanobot"  # 应为 ".nanobot/workspace/project/nanobot"

# ❌ 错误：没有 project_dir 字段（Phase 11 后不再自动推导）
initial_state_mapping:
  project_code: ".nanobot/workspace/project"
```

---

## 容器目录结构参考

```
/eval                          ← EVAL_HOME (= $HOME)
/eval/.nanobot                 ← NANOBOT_HOME
/eval/.nanobot/workspace       ← WORKSPACE（agent 的工作目录）
```

`project_dir` 字段的值是相对于 EVAL_HOME 的路径，因此：
- `project_dir: ".nanobot/workspace/nanobot_core"` → `PROJECT_DIR=/eval/.nanobot/workspace/nanobot_core`

verify 脚本中应设 fallback 默认值：
```python
PROJECT_DIR = os.environ.get("PROJECT_DIR", os.path.join(WORKSPACE, "nanobot_core"))
```

---

## 质检脚本

使用 `scripts/check_project_dir.sh` 自动校验所有测例：
```bash
bash scripts/check_project_dir.sh [tasks_dir]
```
