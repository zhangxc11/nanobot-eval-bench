# 构造流程详细指引

> 本文件是 eval-task-builder SKILL.md §3 的详细展开。

---

## 前置：读取规范

```
必读文件:
- ~/.nanobot/workspace/eval-bench/docs/TASK_SPEC.md  — 完整测例规范
- ~/.nanobot/workspace/skills/eval-task-builder/SKILL.md — 主文件
```

---

## Step 1: 理解 scan 记录

从输入的 scan 记录中提取：
- 候选 ID、任务名、来源 session 路径（**可能有多个**）、难度、类别
- scan 记录中的简要描述
- 如果涉及多个 session，明确**主 session**（发起原始 query 的那条）和**关联 session**（如 subagent、后续跟进等）

---

## Step 2: 深度阅读来源 session

**这是最关键的一步，不可跳过或简化。**

```
操作:
1. 阅读来源 session 的 JSONL 文件
   - 如果 session 文件较短（< 500 行），可完整读取
   - 如果 session 文件很长（混杂了很多任务），应先浏览所有 user 角色的消息，
     从中定位与目标任务相关的范围，再精读该范围内的完整记录
   - 不需要读完所有内容，只需覆盖任务相关的对话

2. 如果涉及多个 session，基于 timestamp 实现跨 session 内容关联
   - 先确定主 session 中任务的时间范围
   - 再在关联 session 中查找同一时间段的记录
   - 按时间线还原完整的任务执行过程

3. 补充数据源：~/.nanobot/workspace/llm-logs/ 目录有全量 LLM API 数据 dump
   - 按日期分文件，可按需搜索其中的内容
   - 当 session 记录不够详细时（如工具调用细节），可从 llm-logs 中补充

4. 重点关注:
   a) 用户的原始问题是什么
   b) agent 实际做了哪些操作（工具调用序列）
   c) 任务涉及了哪些文件、代码库、外部服务
   d) 最终结果是什么，是否成功
   e) 过程中遇到了什么困难/错误
```

---

## Step 3: 确定三要素

基于 session 阅读，确定测例的三个核心要素：

### a) Query（测例问题）

- **基于原始问题，但可以合理调整**：
  - 如果原始问题过于简单（如"帮我改个 typo"），可以适当增加难度（如"重构这个模块并修复 bug"）
  - 如果原始问题依赖过多上下文（如"继续上次的工作"），需要改写为自包含的问题
  - 保持任务本质不变，只调整表述和难度
- **Query 应该是自包含的**：读者不需要额外背景就能理解任务
- **难度调整原则**：
  - easy: 单步或少量步骤，明确指令
  - medium: 需要理解上下文，多步骤协调
  - hard: 需要设计决策，涉及多文件/多系统
  - expert: 复杂架构设计，需要深度领域知识

### b) Initial State（初始环境）

**核心原则：还原真实环境，不简化不摘录。**

根据 session 记录，确定任务执行所依赖的完整环境：

1. **代码库**：
   - 找到所有涉及的代码仓库
   - 通过 git log 定位 query 对应时间点的 commit
   - 使用 `git archive` 或 `git checkout` 恢复到该 commit 的状态
   - **必须保留完整代码**，不能摘录片段或简化
   - 如果仓库过大，使用 `git archive` 导出必要子目录，或用 orphan branch 精简 .git

2. **配置文件和数据**：
   - 环境配置（但需脱敏：API key → placeholder，真实 ID → 占位符）
   - 数据库文件、测试数据
   - session 历史文件（如任务涉及读取历史）

3. **预置 Skills 和 Memory**：
   - 如果任务依赖特定 skill，放入 initial_state/skills/
   - 如果任务依赖记忆内容，放入 initial_state/memory/

4. **外部 API Mock**（按需）：
   - 如果任务涉及外部 API（GitHub 等），评估是否需要 mock
   - 简单情况：在 query 中说明"假设 API 返回以下数据"
   - 复杂情况：提供 mock server 脚本
   - **飞书 API 特殊处理**：飞书部分 API 逻辑特别复杂，不方便 mock。
     scan 阶段会标记为"飞书专项"，这些场景**直接使用线上 API**，
     需要在执行测例之前手动配置飞书应用 key（在 .env 或 config 中）。
     task.yaml 中应添加 `tags: ["feishu-live-api"]` 标记。

5. **Git 状态还原**：
   - **不涉及 git 操作的任务**：initial_state 需包含 .git 目录以保留基本 git 信息，
     使用 orphan branch 技术精简 .git 体积：
     ```bash
     cd repo && git checkout --orphan slim && git add -A && git commit -m "snapshot at {commit_hash}"
     # 清理旧 refs，重新 gc
     ```
   - **涉及 git 操作的任务**（如 git log、git branch、git diff 等）：
     **不能使用 orphan branch 精简**，需要保留原始的 git 提交链条。
     根据任务需求，可能需要构造更复杂的 git 历史：
     - `git log` 类任务：保留足够多的 commit 记录（至少覆盖任务需要查看的范围）
     - `git branch` 类任务：保留相关的分支结构
     - `git diff` 类任务：保留对比所需的两个 commit
     - 如果原始仓库 .git 过大，可选择性保留相关 refs，删除无关分支和 tag

### c) Verification（验证方式）

构造两层验证：

1. **规则检查（verify/test_task.py）**：
   - 文件存在性检查
   - 关键内容/模式匹配
   - 功能正确性（如能 import、能运行）
   - 无回归检查（原有功能不被破坏）

2. **LLM 评分（eval_prompt.md）**：
   - 描述评分维度和权重
   - 提供评分标准（1-10 分）
   - 说明任务背景，让 LLM 理解预期结果

---

## Step 4: 构造测例目录

按照目录结构规范，逐一创建文件：

```
执行顺序:
1. 创建 task-{NNN}/ 目录
2. 写 task.yaml（元数据 + verify_script 字段）
3. 写 query.md（Turn 格式）
4. 构造 initial_state/（最耗时的步骤）
5. 写 verify/test_task.py（使用环境变量获取路径）
6. 创建 mocks/start.sh + mock 脚本（即使不需要 mock 也要提供最小版）
7. 写 eval_prompt.md
8. 写 README.md（可选）
```

---

## Step 5: 自检

构造完成后，执行以下自检：

```
□ task.yaml 格式正确，所有必填字段都有值
□ task.yaml 使用 verify_script 字段（非 deprecated 的 success_criteria）
□ query.md 自包含，不依赖外部上下文
□ query.md 使用 "## Turn N:" 格式（内容在代码块内）
□ initial_state/ 包含任务所需的所有文件
□ initial_state/ 中的代码是完整的（不是摘录/简化版）
□ verify/test_task.py 语法正确（python -m py_compile）
□ verify 脚本使用环境变量获取路径（WORKSPACE/PROJECT_DIR/RESULTS_DIR 等）
□ mocks/start.sh 存在且可执行（即使不需要 mock 也要提供最小版）
□ eval_prompt.md 评分维度覆盖任务核心目标
□ 敏感信息已脱敏（API key、真实 ID、密码等）
□ .git 目录体积合理：不涉及 git 操作的用 orphan branch 精简；涉及 git 操作的保留必要历史链条
□ **initial_state_mapping 路径映射正确**（见 docs/TASK_FORMAT_DETAIL.md 路径映射一致性）：
  - key 不含 `initial_state/` 前缀
  - value 以 `.nanobot/workspace/` 开头（放到 agent workspace 下）
  - verify 脚本中 PROJECT_DIR 默认值与 mapping value 对应
□ **PROJECT_DIR 约束**（Type B 必填）：
  - task.yaml 必须有 `project_dir` 字段（唯一设置 PROJECT_DIR 的方式）
  - 值必须以 `.nanobot/workspace/` 开头
  - 值必须与 initial_state_mapping 中某个 value 一致或是其子路径
  - verify 脚本中 PROJECT_DIR fallback 值必须与 task.yaml project_dir 一致
□ 需要 git 仓库的测例：预构建完整仓库（含 .git + 所有分支），通过 initial_state_mapping 直接复制
□ verify 脚本中的数据库查询按 session_key 过滤，避免全表统计
```

---

## Step 6: 记录决策点

**整个构造过程中，如果遇到不确定的设计决策，按以下策略处理：**

- **高不确定性**（如：不确定原始任务的真实意图、不确定该 mock 哪些 API、不确定难度定级）：
  - **停下来**，在 result 文件中记录问题，标记 `status: needs_review`
  - 等待人工反馈后再继续

- **低不确定性**（如：query 措辞的微调、verify 检查项的取舍、目录命名）：
  - **做出最佳判断继续推进**
  - 但必须在 result 文件的 `decisions` 字段中记录每个决策点和理由

**无论哪种情况，决策点都不能静默忽略——最终需要人工确认。**
