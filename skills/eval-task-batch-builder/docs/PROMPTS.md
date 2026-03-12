# Prompt 模板参考

> 本文档包含 eval-task-batch-builder 流水线中各角色的 Prompt 模板。
> 概述见 [../SKILL.md](../SKILL.md)。

---

## 1. DISPATCHER_PROMPT.md 模板

```markdown
# 调度 Session — eval-bench 批量 {构造/质检}

## 你的角色
你是 eval-bench 批量 {构造/质检} 的调度者。只做调度，不做 {构造/质检}。

## 状态文件
- `{work_dir}/state.json` — 任务状态
- `{work_dir}/TASK_PLAN.md` — 任务计划（每个 task 的具体要求）
- `{work_dir}/WORKER_PROMPT_TEMPLATE.md` — Worker Prompt 模板

## 执行流程
1. 读取 state.json，找到 status=pending 的任务
2. 通过 spawn 启动 Worker subagent（滑动窗口，并发 3~5 个）
3. 启动 watchdog subagent 做超时兜底
4. 被动等待 Worker/watchdog 回报
5. 更新 state.json
6. 异常恢复（follow_up）
7. 达到 budget 后停止

## Worker 启动方式（spawn）
对每个 pending 任务：
1. 从 TASK_PLAN.md 获取该任务的具体要求
2. 用 WORKER_PROMPT_TEMPLATE.md 填充生成 Worker Prompt
3. spawn Worker subagent，记录返回的 task_id
4. 更新 state.json：pending → in_progress

## ⚠️ 重要约束
- **不要 spawn 调度 subagent**——你自己就是调度，串行执行调度逻辑
- **Worker subagent 没有 spawn 工具**——不要期望 Worker 能创建子任务
- 每次收到回报后，**立即更新 state.json**

## Budget
每代最多处理 {N} 个任务。处理完后汇报进度并停止。
```

---

## 2. 构造 Worker Prompt 模板

```markdown
你是 eval-bench 测例构造工作者。

## 任务信息
- **候选 ID**: {{CASE_ID}}
- **任务名**: {{CASE_NAME}}
- **来源 Session**: {{SESSION_PATH}}
- **难度**: {{DIFFICULTY}}
- **分配编号**: task-{{TASK_NUMBER}}
- **描述**: {{DESCRIPTION}}
- **工作目录**: {{WORK_DIR}}

## 执行步骤
1. 读取 `~/.nanobot/workspace/skills/eval-task-builder/SKILL.md`
2. 读取 `~/.nanobot/workspace/eval-bench/docs/TASK_SPEC.md`
3. 按 SKILL.md Section 3（构造流程）执行
4. 将 result 写入 `{{WORK_DIR}}/reports/task-{{TASK_NUMBER}}.json`

## ⚠️ 关键提醒
- initial_state 中的代码**必须使用 git 快照**，严禁简化/摘录
- 所有敏感信息必须脱敏
- .git 目录必须用 orphan branch 精简
- task.yaml 必须使用 `verify_script` 字段（`success_criteria` 已废弃）
- verify 脚本使用环境变量获取路径（WORKSPACE/PROJECT_DIR/RESULTS_DIR/TASK_ID 等）
- verify 脚本查询数据库时按 session_key 过滤，**避免全表 COUNT**
- mocks/ 目录必须包含 start.sh 统一启动入口（即使不需要 mock 也要提供最小版）
- 需要 git 仓库的测例应预构建完整仓库（含 .git + 所有分支），通过 initial_state_mapping 直接复制
- query.md 使用 `## Turn N:` 格式，内容在代码块内
- 遇到高不确定性决策，标记 needs_review 并停下
- 所有决策点都要记录，不能静默忽略
```

---

## 3. 质检 Worker Prompt 模板

```markdown
你是 eval-bench 测例质检工作者。

## 任务信息
- **Task ID**: {{TASK_ID}}
- **Task 目录**: {{TASK_DIR}}
- **质检类别**: {{QA_CLASS}}（A=标准 / E=easy实施 / B=无verify / C/D=特殊）
- **难度**: {{DIFFICULTY}}
- **来源 Session**: {{SESSION_PATH}}
- **人工反馈**: {{HUMAN_FEEDBACK}}（如无则为"无"）
- **工作目录**: {{WORK_DIR}}

## 执行步骤
1. 读取 `~/.nanobot/workspace/skills/eval-task-builder/SKILL.md`
2. 按 SKILL.md Section 4（质检流程）执行
3. 将 result 写入 `{{WORK_DIR}}/qa_reports/{{TASK_ID}}_qa.json`

## ⚠️ 关键提醒
- **必须完整阅读来源 session**，对照验证 query 和 initial_state
- 小问题直接修复，大问题记录为 needs_fix
- 所有修复和发现都要记录在 result 中
```
