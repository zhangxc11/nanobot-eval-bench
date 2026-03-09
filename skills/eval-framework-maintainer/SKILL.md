---
name: eval-framework-maintainer
description: eval-bench 评测框架维护。根据测例构造过程中产生的框架改进需求，修改评测框架代码，并确保已有测例兼容。
---

# eval-framework-maintainer — 评测框架维护

根据测例构造过程中产生的框架改进需求，修改评测框架代码，并确保已有测例兼容。

---

## 职责

```
输入: eval-task-builder 产生的框架改进建议
输出: 框架代码修改 + 已有测例兼容性验证 + 文档更新
```

## 工作流程

```
1. 读取改进建议 → 分析影响范围
2. 修改框架代码（runner.py, docker-compose, Dockerfile 等）
3. 对已有测例运行兼容性检查
   - task.yaml 解析正常
   - verify_criterion 不报错
   - query.md 解析正常
4. 如有兼容性问题 → 修复已有测例
5. 更新文档（DESIGN.md, TASK_SPEC.md, DEVLOG.md）
6. Git 提交
```

## 使用方式

> 请使用 eval-framework-maintainer skill，处理以下框架改进需求：
> [粘贴 eval-task-builder 产生的改进建议]

## 兼容性检查脚本

```bash
# 检查所有已有测例的兼容性
python3 scripts/check_compatibility.py --tasks-dir eval-bench/tasks/
```

检查项：
1. task.yaml 能否被 runner.py 正确解析
2. task.yaml 使用 `verify_script` 字段（`success_criteria` 已废弃，runner.py 不再执行）
3. query.md 能否被 load_queries 正确解析（`## Turn N:` 格式）
4. initial_state_mapping 路径是否有效
5. verify_script 路径是否存在
6. mocks/start.sh 是否存在（框架统一入口）

## 关键文件

| 文件 | 说明 |
|------|------|
| `eval-bench/platform/runner.py` | 核心执行器 |
| `eval-bench/platform/docker-compose.yaml` | Docker 编排 |
| `eval-bench/run.sh` | 单测例入口脚本 |
| `eval-bench/batch_run.sh` | 批量运行脚本 |
| `eval-bench/docs/TASK_SPEC.md` | 测例规范 |
| `eval-bench/docs/DEVLOG.md` | 开发日志 |
| `eval-bench/platform/DESIGN.md` | 技术方案 |
