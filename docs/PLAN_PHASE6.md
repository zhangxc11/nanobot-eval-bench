# Phase 6 执行计划

## 总体目标
将评测框架与测例解耦，创建 4 个 Skill 支撑测例的发现→构造→维护→批量生产流程。

## 执行步骤

### Step 1: 框架解耦 [本次]
- 1.1 run.sh 增加 `--task-dir` 参数支持外部测例路径
- 1.2 docker-compose.yaml 支持 TASK_DIR_HOST 环境变量
- 1.3 创建 TASK_SPEC.md（测例规范文档）
- 1.4 创建统一测例清单 `CASE_REGISTRY.md`（整合 A1~A16 + B1~B16 + N1~N15）
- 1.5 验证已有 task-001, task-002 兼容性

### Step 2: Skill 1 — eval-session-scanner [本次]
- 2.1 SKILL.md（含体系运转逻辑说明）
- 2.2 scripts/scan_sessions.py（session 扫描脚本）
- 2.3 对 3月2日 15:55 之后的 session 实际运行验证
- 2.4 输出整合到 CASE_REGISTRY.md

### Step 3: Skill 2 — eval-task-builder [后续]
### Step 4: Skill 3 — eval-framework-maintainer [后续]
### Step 5: Skill 4 — eval-task-batch-builder [后续]
### Step 6: Git 提交
