# 实践经验

> 以下经验来自 2026-03 的完整实践（1 轮构造 + 3 轮 QA）。
> 概述见 [../SKILL.md](../SKILL.md)。

---

## 1. 调度策略

**⚠️ 调度 session 只调度，不构造**

早期调度 session 混合了"自己构造 easy 任务"和"启动 worker"两种模式，
导致迭代次数不够。改为纯调度后，100 次迭代可管理 15-20 个 Worker。

**⚠️ 调度串行，Worker 并行**

- 一个调度 session 管理所有 Worker，通过滑动窗口并行 spawn
- ❌ 不要 spawn 多个调度 subagent 并行（subagent 没有 spawn 工具，会导致降级和命名混乱）
- 如果调度 session 迭代耗尽，由用户 session 启动新调度 session 接力

**⚠️ Worker subagent 不创建子 session**

Worker subagent 只有 7 个基础工具（read_file/write_file/edit_file/list_dir/exec/web_search/web_fetch），
没有 spawn/message/cron。如果需要子任务，说明架构设计有问题，应由调度 session 拆分为多个独立 Worker。

---

## 2. Worker 健壮性

**⚠️ Worker 卡住是常态，需要恢复机制**

实践中 Worker 卡住的原因：
- LLM 断连（最常见）
- 迭代次数耗尽
- 文件操作错误

恢复方式：调度 session 使用 follow_up 向 Worker 发送继续消息。

---

## 3. state.json 设计

```json
{
  "tasks": {
    "task-003": {
      "case_id": "N3",
      "status": "success | pending | in_progress | needs_review | failed",
      "worker_task_id": "spawn_task_id",
      "build_result": "reports/task-003.json",
      "qa_status": "pass | fixed | needs_fix | pending",
      "qa_result": "qa_reports/task-003_qa.json",
      "notes": ""
    }
  },
  "pipeline_phase": 4,
  "last_updated": "2026-03-07T15:00:00"
}
```

---

## 4. 迭代次数管理

| 角色 | 推荐 max_iterations | 说明 |
|------|---------------------|------|
| 调度 session | 100（默认） | 纯调度，主要是 spawn + 文件读写 |
| 构造 Worker | 100 | 需要读 session、构造文件、git 操作 |
| 质检 Worker | 80 | 读 session + 检查 + 小修复 |

**⚠️ 100 次迭代是硬上限**，调度 session 如果管理的 Worker 多，可能不够。
解决方案：分代执行（gen1 处理前 N 个，gen2 继续），由 User Watchdog 自动接力。

---

## 5. 常见质量问题（从三轮 QA 总结）

| 问题 | 频率 | 根因 | 预防措施 |
|------|------|------|---------|
| 代码被简化/摘录 | 高 | LLM 倾向"理解后重写" | Worker Prompt 中强调"必须用 git 快照" |
| .git 体积过大 | 中 | 未做 orphan 精简 | Worker Prompt 中包含精简步骤 |
| 路径映射不一致 | 中 | task.yaml 和 verify 脚本路径不匹配 | 自检清单中包含路径一致性检查 |
| 敏感信息泄露 | 低 | 复制了真实配置文件 | Worker Prompt 中强调脱敏 |
| verify 脚本语法错误 | 低 | 未做 py_compile 检查 | 自检步骤包含编译检查 |
| query 不自包含 | 中 | 直接复制了原始对话 | 强调 query 需要改写为自包含 |

---

## 6. 并行度建议

| 任务总量 | 推荐并行 Worker 数 | 说明 |
|---------|-------------------|------|
| ≤10 | 3-5 | 单代调度可完成 |
| 11-20 | 5-8 | 可能需要 2 代调度 |
| 21-40 | 8-12 | 需要 2-3 代调度 |
| >40 | 分批次执行 | 每批 20 个 |
