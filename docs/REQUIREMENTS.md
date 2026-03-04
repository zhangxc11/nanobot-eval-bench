# eval-bench 需求文档

## 项目目标

构建 nanobot Agent 评测基准平台，从真实历史 session 中提炼评测任务，用于衡量不同 Agent 策略的效果。

## 核心需求

### R1: Docker 隔离执行

- 每个评测任务在独立 Docker 容器中运行
- 容器内包含完整的 nanobot 运行环境
- Mock 外部服务（如 LLM API），确保可复现
- 支持资源限制（tool call 次数、超时时间）

### R2: 两类任务支持

- **Type A — 普通任务**：创建 Skill、写脚本等，agent 在 workspace 中操作
- **Type B — 代码修改任务**：修改 nanobot/webchat 源码，需要独立的项目代码目录

### R3: 多轮对话

- 支持单轮和多轮 query 注入
- 每轮 query 可以设置条件触发（基于上一轮结果）
- 模拟真实用户交互模式

### R4: 自动化验证

- **硬性验证**：文件存在性、内容包含、pytest 脚本
- **verify_criterion**：声明式规则（file_exists / file_contains / contains）
- **verify_script**：自定义 pytest 测试脚本

### R5: 评价机制（可选）

- 评价环节**不在平台内自动执行**
- 由执行任务的智能体统一读取 results 目录 + eval_prompt.md 进行评分
- 不配置 eval_prompt.md 则跳过评价
- eval_prompt.md 定义评价维度和评分标准（如功能完整性、代码质量、兼容性等）

### R6: 结果收集

- 执行轨迹（trajectory.jsonl）
- 最终文件系统快照（final_state/）
- 自动化验证结果（run_summary.json）
- 执行指标（tool calls、LLM calls、token 用量、耗时）
- 多轮对话摘要（turns.json）

### R7: Mock 服务

- Mock LLM API（如 volcengine）用于 Skill 开发类任务
- Mock provider 使用专用名称（如 `mock-volcengine`），与 agent 真实 provider 不冲突
- 支持 health check，确保 mock 就绪后再启动 agent

### R8: 策略对比

- 可对比的维度：LLM 模型、系统提示词、工具策略、记忆策略、Skill 加载、温度参数等
- 同一任务可用不同策略多次运行
- 结果可横向对比

## 任务来源

从 71 个历史 session（2026-02-25 ~ 2026-03-02）中提炼，分为四类：
- 🟢 A类：高度适合（16 个）— 自包含、可复现、标准明确
- 🟡 B类：可简化后提炼（21 个）— 涉及外部服务/跨通道
- 🔵 C类：轻量冒烟测试（10 个）
- 🔴 D类：不适合直接提炼

详见 [README.md](../README.md) 任务列表。

## 已实现任务

| Task ID | 名称 | 类型 | 来源 |
|---------|------|------|------|
| task-001 | doubao-search-skill | Type A (Skill 开发) | A1 |
| task-002 | token-usage-analytics | Type B (代码修改) | B9 |

## 演进路线

### Phase 1: MVP（当前）
- 手动提炼 3-5 个评测任务
- 单容器执行 + 自动化验证
- JSON 报告

### Phase 2: 自动化
- 自动从 session 历史提炼任务
- 并行多容器执行
- Web Dashboard 展示结果

### Phase 3: CI 集成
- 每次代码提交自动跑评测
- 回归检测
- 评分趋势图
