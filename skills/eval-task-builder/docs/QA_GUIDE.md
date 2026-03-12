# 质检详细指引 + 实践经验

> 本文件是 eval-task-builder SKILL.md §4 质检流程详细说明 + §5 实践经验全部内容。

---

## 质检执行步骤（详细）

### Step 1: 读取测例文件
- 读取 task.yaml, query.md, eval_prompt.md
- ls initial_state/，了解目录结构
- 读取 verify/test_task.py

### Step 2: 读取原始 session（必须）
- 阅读来源 session 文件（长 session 先定位范围再精读）
- 如果涉及多个 session，基于 timestamp 跨 session 关联
- 对照 query.md，逐项验证 D1（原始匹配度）

### Step 3: 逐维度检查
- D1~D9 逐一检查，记录发现

### Step 4: Verify Dry-run
- 在 initial_state 目录下运行 verify 脚本（预期应 fail，因为任务还没做）
- 检查脚本能否正常执行（不是因为语法错误而 fail）
- 注意路径映射：根据 task.yaml 的 initial_state_mapping 正确设置环境变量

### Step 4b: 低难度任务实施评测（仅 easy/medium 难度）
- 直接试执行任务（作为 agent 完成 query 中的要求）
- 执行完成后运行 verify 脚本，检查规则验证是否通过
- 运行 LLM 评分，检查 eval_prompt.md 的评分维度是否合理
- 如果验证/评分发现问题，反过来修正 verify 脚本或 eval_prompt.md

### Step 5: 修复或记录
- 小问题（typo、缺失字段、路径不一致）：直接修复
- 大问题（initial_state 缺失关键文件、query 偏离原始意图）：记录为 needs_fix
- 记录所有修复和发现到 result 文件

### Step 6: 输出质检报告
- 状态: pass | fixed | needs_fix
- 各维度评分（pass/warn/fail）
- 修复列表（如有）
- 遗留问题（如有）

---

## 质检 Result 文件格式

```json
{
  "task_id": "task-{NNN}",
  "status": "pass | fixed | needs_fix",
  "dimensions": {
    "D1_MATCH": "pass | warn | fail",
    "D2_STATE": "pass | warn | fail",
    "D3_REAL": "pass | warn | fail",
    "D4_VERIFY": "pass | warn | fail",
    "D5_EVAL": "pass | warn | fail",
    "D6_YAML": "pass | warn | fail",
    "D7_SECURITY": "pass | warn | fail",
    "D8_GIT_SIZE": "pass | warn | fail",
    "D9_DIFFICULTY": "pass | warn | fail"
  },
  "fixes_applied": ["描述修复1", "描述修复2"],
  "remaining_issues": ["描述遗留问题"],
  "decisions": ["决策点1: 选择了X因为Y"],
  "notes": "补充说明"
}
```

---

## 实践经验与注意事项

> 以下经验来自 2026-03 批量构造 36 个测例 + 三轮 QA 的实践总结。

### §5.1 Initial State 构造（最易出错的环节）

**⚠️ P0 — 代码必须用真实 git 快照，严禁简化/摘录**

这是第一轮批量构造中最严重的问题（R2 修复了 26 个测例）。LLM 在构造 initial_state 时，
倾向于"理解代码后写一个简化版"，而非直接使用原始代码。这会导致：
- 丧失真实场景复杂度
- verify 脚本基于简化代码编写，无法检测真实问题
- 评测结果不能反映 agent 处理真实代码的能力

**正确做法**：
```bash
# 1. 找到任务对应的 commit
cd /path/to/repo
git log --oneline --before="2026-03-05" | head -5

# 2. 导出该 commit 的完整代码
git archive {commit_hash} -o /tmp/snapshot.tar
# 或
git checkout {commit_hash} -- .

# 3. 如果需要保留 .git（任务涉及 git 操作），用 orphan branch 精简
git checkout --orphan slim
git add -A
git commit -m "snapshot at {commit_hash}"
# 删除旧 refs + gc
```

### §5.2 .git 体积控制

**⚠️ 不精简的 .git 可能占 30~60MB，精简后通常 1~3MB**

**场景一：任务不涉及 git 操作 → orphan branch 精简**

```bash
# orphan branch 精简流程
cd initial_state/{project_dir}
git checkout --orphan slim
git add -A
git commit -m "snapshot"
git branch -D main 2>/dev/null  # 删除旧分支
rm -rf .git/refs/original .git/logs
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

**场景二：任务涉及 git log / branch / diff 等操作 → 保留必要的 git 历史**

```bash
# 不能用 orphan branch！需要保留 commit 链条
# 策略：只保留相关分支，删除无关 refs
cd initial_state/{project_dir}

# 删除无关的远程分支
git remote remove origin 2>/dev/null

# 只保留需要的本地分支（如 main + feature-xxx）
git branch | grep -v 'main\|feature-xxx' | xargs git branch -D 2>/dev/null

# 删除 tags（如不需要）
git tag -l | xargs git tag -d 2>/dev/null

# 清理
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

实践中发现的问题（quality_fix R3）：
- task-016/019/030/035 的 .git 包含完整历史，总计 ~190MB
- 精简后降到 ~6MB，节省 97%

### §5.3 脱敏合规

**⚠️ 所有推送到公开仓库的内容严禁包含真实敏感信息**

需要脱敏的内容：
- API Key / Secret → `YOUR_API_KEY_HERE`
- 飞书 open_id → `ou_xxx`
- 飞书 chat_id → `oc_xxx`
- 真实用户名/邮箱 → 占位符
- config.json 中的敏感字段 → placeholder

### §5.4 路径映射一致性

> 详见 docs/TASK_FORMAT_DETAIL.md 中的"路径映射一致性详解"部分。

### §5.5 Query 设计

- **自包含**：不依赖"上次对话"、"之前的工作"等外部上下文
- **明确目标**：agent 读完 query 应该知道要做什么
- **合理难度**：如果原始问题太简单，可以加入额外要求（如"同时写单元测试"、"处理边界情况"）
- **多轮 query**：如果原始交互是多轮的，可以合并为单轮（更常见），或保留多轮结构

### §5.6 Verify 脚本设计

- **检查结果而非过程**：验证最终产出，不验证 agent 的具体操作步骤
- **容错性**：允许合理的实现差异（如函数名不同但功能正确）
- **Dry-run 友好**：在 initial_state 上运行应该 fail（因为任务没做），但不应因语法错误而 crash
- **路径使用环境变量**：`WORKSPACE`、`PROJECT_DIR`、`NANOBOT_DIR`
- **数据库查询按 session_key 过滤**：如果 verify 脚本查询 analytics.db 等数据库，
  **避免全表 COUNT/SUM**（如 `SELECT COUNT(*) FROM token_usage`），
  因为 agent 自身的 eval session 也会写入同一数据库。
  应按 session_key 过滤：`WHERE session_key LIKE 'webchat:test_session_%'`

### §5.7 决策点处理策略

| 不确定程度 | 行为 | 示例 |
|-----------|------|------|
| 高 | 停下来，标记 needs_review | 不确定原始任务意图；不确定是否需要 mock 某 API |
| 中 | 做出判断并继续，详细记录 | query 措辞的选择；verify 检查项的取舍 |
| 低 | 做出判断并继续，简要记录 | 目录命名；README 内容 |

**关键原则：任何决策点都不能静默忽略，最终需要人工确认。**

### §5.8 PROJECT_DIR 环境变量与 `project_dir` 字段

> 已移至独立文档 docs/PROJECT_DIR.md，详见该文件。

---

## Batch 4 经验教训

> 2026-03-12 Batch 4 构造 15 测例 + 质检复盘

**高频问题：initial_state_mapping 路径映射错误（5/15 = 33%）**

- **根因**：Worker 不理解 runner.py 的映射逻辑（`dest_path = EVAL_HOME / dest_rel`），把 value 写成裸目录名（如 `nanobot_core/`），导致文件被放到 `/eval/nanobot_core/` 而非 `/eval/.nanobot/workspace/nanobot_core/`
- **修复**：在 §2.2 task.yaml 示例、§3.5 checklist、§5.4 路径映射 三处加入了详细说明和常见错误表
- **预防**：Worker Prompt 模板中应明确提及路径映射规则，或在 checklist 中加粗提醒

**其他发现**：
- 所有 15 个测例的 D1（原始匹配度）、D3（真实性）、D7（脱敏）均通过 — 说明构造质量基本面良好
- E 类 easy 实施质检（task-047~052）全部 pass — 说明 easy 难度测例的 verify 脚本设计合理
- 合成仓库的测例（task-041/042）质检也通过 — 说明合成场景的还原度可接受
