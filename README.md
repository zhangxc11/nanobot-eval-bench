# nanobot Eval Bench — Agent 评测基准

从历史 session 中提炼评测任务，用于衡量不同 Agent 策略的效果。

---

## 一、适合提炼成评测的历史任务

通过逐个分析 71 个 session 记录（2026-02-25 ~ 2026-03-02），识别出以下独立任务。
注意：一个 session 可能包含多个任务，一个任务也可能跨多个 session/通道完成。

### 分类说明
- 🟢 **A类**：高度适合提炼（自包含、可复现、成功标准明确）
- 🟡 **B类**：可提炼但需简化（涉及外部服务/跨通道/上下文复杂）
- 🔵 **C类**：轻量任务（可作为简单评测或冒烟测试）
- 🔴 **D类**：不适合直接提炼（纯运维/过于碎片化/高度依赖上下文）

---

### 🟢 A类：高度适合提炼

| # | 任务名 | 来源 Session | 类型 | 难度 | 说明 |
|---|--------|-------------|------|------|------|
| **A1** | 创建 doubao-search Skill | `webchat_1772349033` | Skill 开发 | ⭐⭐ | 从零创建搜索 skill（search/summarize/fetch-url），含需求→架构→脚本→测试→SKILL.md 全流程。多轮交互（用户分阶段提供 API 配置）。 |
| **A2** | 创建 calendar-reader Skill | `cli_direct` [2-6,10-13] | Skill 开发 | ⭐⭐ | 通过 AppleScript 查询 macOS 日历，封装为 skill。含多日历源适配、只读安全约束。 |
| **A3** | 创建 dev-workflow Skill | `feishu.lab_...1772307725` [9] | Skill 开发 | ⭐ | 将开发规范（文档先行、任务拆解、git 管理）整理为流程说明 skill。 |
| **A4** | 创建 doc-reader Skill | `feishu.lab_...1772356375` [23] | Skill 开发 | ⭐⭐ | PPT/DOCX 分析 skill，从飞书实际使用中提炼。 |
| **A5** | 创建 restart-gateway Skill | `feishu.ST_...` [17-22] | Skill 开发 | ⭐ | 将 gateway 重启操作封装为 skill（含 exec `&` 限制绕过方案）。 |
| **A6** | 创建 insight-dashboard Skill | `webchat_1772377467` | Skill 开发 | ⭐⭐⭐ | 基于自然语言自动生成社交媒体/用户反馈的数据呈现和可视化页面。 |
| **A7** | Session 按来源分组 | `webchat_1772209967` | 前端功能 | ⭐⭐ | 给 web-chat 左侧 session 列表按来源（webchat/feishu.lab/feishu.ST/cli）分组。 |
| **A8** | 图片输入支持 | `webchat_1772181905` + `cli_direct` [63-65] | 前端功能 | ⭐⭐ | Web UI 支持图片输入（📎按钮+拖拽+粘贴），base64 压缩，nanobot core media 参数。 |
| **A9** | 图片 base64 大小限制反算 | `webchat_1772209687` | 小修复 | ⭐ | 5MB base64 限制需反算实际文件大小上限，更新压缩触发边界。 |
| **A10** | SSE 流 330s 超时修复 | `cli_direct` [74-79] + `webchat_1772353199` | Bug 修复 | ⭐⭐⭐ | 诊断 web-chat SSE 流在长任务时 330s 超时断开，需分析 done event race condition。 |
| **A11** | Session 标题恢复 Bug 修复 | `cli_direct` [29] | Bug 修复 | ⭐ | 每次发消息后 session 标题被恢复成原始标题。 |
| **A12** | 工具调用折叠优化 | `cli_direct` [23,27-28] + `cli_webchat` [18-20] | 前端功能 | ⭐⭐ | 工具调用过程折叠显示，只显示最终回复；折叠内 Markdown 渲染；换行保留。 |
| **A13** | 工具调用展示精细化 | `webchat_1772113625` | 前端功能 | ⭐⭐ | 运行中/历史记录的工具调用展示统一（输入参数显示、折叠标记优化）。 |
| **A14** | Session 删除 + 标题优化 | `webchat_1772125037` | 前端功能 | ⭐ | 支持删除 session、显示文件名小字、改进标题生成方法。 |
| **A15** | 飞书图片保存 + session 瘦身 | `webchat_1772207666` | 功能改进 | ⭐⭐ | 飞书上传图片保存到下载目录 + 从 session jsonl 中移除 base64 减小文件体积。 |
| **A16** | 超大图片压缩 | `feishu.lab_...1772307725` [3-5] | 功能改进 | ⭐ | IM/Web 端传入 >5M 图片自动压缩后再传 LLM。 |

### 🟡 B类：可提炼但需简化

| # | 任务名 | 来源 | 类型 | 难度 | 说明 |
|---|--------|------|------|------|------|
| **B1** | 飞书通道卡住诊断 | `webchat_1772344758` | 问题诊断 | ⭐⭐ | 分析 gateway 日志定位串行阻塞。需构造日志快照。 |
| **B2** | ProviderPool 运行时切换 | `webchat_1772291560` (13轮) | 核心功能 | ⭐⭐⭐⭐ | 多 Provider 动态切换 + 前端 UI + /provider 命令。8 次用户需求修正。 |
| **B3** | 飞书合并转发消息解析 | `webchat_1772346998` + `feishu.lab.1772376517` | 功能开发 | ⭐⭐⭐ | 解析 merge_forward 消息，获取子消息详情，下载附件。需飞书 API mock。 |
| **B4** | 飞书 SDK Skill 化 | `webchat_1772379210` | 重构 | ⭐⭐ | 将 gateway 中的飞书 SDK 操作拆分为 feishu-parser + feishu-messenger skill。 |
| **B5** | Gateway 并发执行重构 | `feishu.lab_...1772366290` → `webchat_1772364082` | 架构重构 | ⭐⭐⭐⭐ | 串行→并发 + per-session provider + user injection。跨通道（飞书讨论→webchat 执行）。 |
| **B6** | 斜杠命令体系 | `webchat_1772193190` + `1772195178` + `1772195916` | 架构设计 | ⭐⭐⭐ | 统一 /help /stop /new /flush /provider /session 在 CLI/Web/Gateway 的行为。 |
| **B7** | /new 策略反转 | `feishu.lab_...` [9-10轮] | 功能改进 | ⭐⭐ | 旧 session 文件不动保持原 key，新 session 用短 key。含 session 命名策略调整。 |
| **B8** | Analytics DB session_key 修复 | `webchat_1772370857` + `feishu.lab.1772376517` | 数据修复 | ⭐⭐ | 诊断 usage 统计与 session 条目不匹配，修复因 /new 导致的 session_key 错乱。 |
| **B9** | Token 用量统计系统 | `cli_webchat` [29-38] + `webchat_1772111064` | 全栈功能 | ⭐⭐⭐ | 引入 SQLite 后端记录 LLM 调用 token 用量 + 前端 Usage 页面 + 趋势曲线看板。 |
| **B10** | /session 命令 + Token 用量 | `feishu.lab_...` [Phase 20] | 功能开发 | ⭐⭐ | 查询当前 session 名称/状态/消息数 + 累计 token 统计。 |
| **B11** | 多飞书租户接入 | `webchat_1772172079` | 架构扩展 | ⭐⭐⭐ | gateway 同时连接多个飞书租户，各自独立 session。含配置格式调整和前端适配。 |
| **B12** | 飞书文档 CRUD Skill | `webchat_1772250674` | Skill 开发 | ⭐⭐⭐ | 创建飞书文档操作 skill（创建/读取/写入）。需飞书 API mock。 |
| **B13** | 飞书文档批注管理 | `feishu.ST_...` [34-36] | Skill 扩展 | ⭐⭐ | 给 feishu-docs skill 添加批注读取/回复/解决/创建能力。 |
| **B14** | 飞书文档权限管理 | `feishu.ST_...` [26-27] | Skill 扩展 | ⭐⭐ | 文档权限设置（添加协作者 vs 组织内可编辑）。 |
| **B15** | 文件访问审计功能 | `feishu_...` [3-5] | 安全功能 | ⭐⭐ | 对所有文件读写工具操作进行审计日志记录。 |
| **B16** | 飞书文件附件发送修复 | `webchat_1772353199` [2] + `feishu.lab_...1772356375` [20-28] | Bug 修复 | ⭐⭐ | 诊断并修复 gateway 通过飞书发送文件失败的问题（MessageTool + ChannelManager 路由）。 |
| **B17** | 损坏 Session 修复 | `webchat_1772168096` [3] | 数据修复 | ⭐⭐ | 飞书 session 因 gateway 自重启导致工具调用不匹配而损坏，需诊断并修复 jsonl。 |
| **B18** | 超大图片导致 Session 损坏修复 | `feishu.ST_...` [5-10] | 数据修复 | ⭐⭐ | >5M 图片 base64 导致 LLM API 报错，需从 session 中定位并删除超大图片消息。 |
| **B19** | Web Chat 从零搭建 | `cli_webchat` + `cli_direct` (早期) | 全栈项目 | ⭐⭐⭐⭐⭐ | 从简易 HTTP 到 React+Vite+Zustand 全栈 web chat UI。超大任务需拆分。 |
| **B20** | Web Chat 自修改架构设计 | `cli_webchat` [20,26] + `cli_direct` [25-26] | 架构设计 | ⭐⭐⭐ | 分析代码自修改导致服务重启时任务中断的问题，设计 webserver/worker 分离架构。 |
| **B21** | 科学算力材料整合 | `feishu.lab_...1772341100` + `feishu.lab_...1772356375` | 文档协作 | ⭐⭐⭐ | 从飞书群聊记录中提取信息，整合多方材料（PPT/Word），生成合并后的 docx 文档。 |

### 🔵 C类：轻量任务（冒烟测试 / 简单评测）

| # | 任务名 | 来源 | 类型 | 说明 |
|---|--------|------|------|------|
| **C1** | 日程查询 | `webchat_1772030778` | 信息查询 | 查询明天/未来三天日程 + 找空闲时间段。 |
| **C2** | 空闲时间判断 | `feishu.ST_...` [37] | 信息查询 | "下周二上午11-12有空吗？" 需结合日历判断。 |
| **C3** | 图片内容识别 | `webchat_1772200160` [1] + `webchat_1772187037` | 多模态 | 识别图片内容 / 颜色。 |
| **C4** | 飞书配置指引 | `webchat_1772155524` | 配置指导 | 指引用户配置飞书长连接。 |
| **C5** | 邮箱能力探测 | `webchat_1772175244` | 能力边界 | "能查看我的邮箱邮件吗？" — 测试 agent 对能力边界的认知。 |
| **C6** | 记忆整理 | `webchat_1772199307` + `webchat_1772290340` + `webchat_1772354186` + `webchat_1772383112` | 记忆管理 | 精简/重组记忆文件，拆分到独立文档。 |
| **C7** | 需求文档排序修复 | `webchat_1772352882` | 文档修复 | 需求文档中正式需求写到了手动 backlog 里，修复顺序。 |
| **C8** | Git 分支确认 + 记忆同步 | `webchat_1772354898` | 状态确认 | 确认 feat/provider-pool 是否合并到 local，同步记忆。 |
| **C9** | Gateway 卡住诊断 | `webchat_1772206434` | 快速诊断 | 简单的 gateway 卡住诊断（轻量版 B1）。 |
| **C10** | Usage 调用次数异常诊断 | `webchat_1772123170` | 数据诊断 | 两个 session 的工具调用次数/usage 比例差距过大，定位原因。 |
| **C11** | 历史消息异常过滤 | `webchat_1772200160` [2-6] | Bug 修复 | 历史记录中出现不明消息，需定位来源并过滤。 |
| **C12** | Webchat interjection 功能失效 | `webchat_1772351797` | Bug 修复 | 工作过程中用户插入消息功能失效的诊断。 |
| **C13** | 终端闪退诊断 | `feishu.lab_...1772341100` [1] | 问题诊断 | nanobot CLI 输入过程中终端闪退，可能与退格键有关。 |
| **C14** | Debug 日志默认关闭 | `webchat_1772291560` [13] | 小修复 | 启动时 OAuth provider skipped 的 DEBUG 日志默认不输出。 |
| **C15** | 飞书聊天记录总结 | `feishu.lab.1772376517` [最后] | 信息提取 | 从转发的群聊记录中提取发言人、@关系、总结内容。 |
| **C16** | 思考/想法整理成文 | `feishu.ST_...` [28-33] | 文档生成 | 将用户零散输入的想法整理成结构化飞书文档。 |

### 🔴 D类：不适合直接提炼

| 类别 | 数量 | 说明 |
|------|------|------|
| **Gateway 重启操作** | ~15 个 session | 纯模板化脚本执行（`webchat_1772341511` ~ `webchat_1772381274` 等），无智能决策 |
| **简单 ping/hello** | ~5 个 | `webchat_1772306091`、`feishu.lab_...1772196120` 等，仅测试连通性 |
| **跨 session 继续任务** | ~8 次 | `cli_direct` [19,31,36,49] 等 "超时了请继续"，依赖前序状态 |
| **Backlog 批量执行** | ~5 次 | `cli_direct` [39,45,59] 等 "完成 backlog 中的 X-Y"，依赖具体 backlog 内容 |

---

### 统计汇总

| 类别 | 任务数 | 说明 |
|------|--------|------|
| 🟢 A类 | 16 | 高度适合，可直接提炼 |
| 🟡 B类 | 21 | 需简化/mock，但价值高 |
| 🔵 C类 | 16 | 轻量任务，适合冒烟测试 |
| 🔴 D类 | ~33 次 | 不适合（重启/ping/继续等） |
| **合计** | **53 个独立任务** + D类碎片 | |

### 任务类型分布

| 类型 | 数量 | 代表任务 |
|------|------|---------|
| **Skill 开发** | 8 | A1-A6, B12, B13 |
| **前端功能开发** | 7 | A7, A8, A12-A14, B9, B19 |
| **Bug 修复/诊断** | 11 | A10-A11, B1, B16-B18, C9-C13 |
| **架构设计/重构** | 5 | B2, B5, B6, B20, B4 |
| **数据修复** | 3 | B7, B8, B17 |
| **功能改进** | 5 | A9, A15-A16, B7, B15 |
| **信息查询/提取** | 5 | C1-C2, C5, C15-C16 |
| **文档/记忆管理** | 5 | C6-C8, A3, B21 |
| **多模态** | 1 | C3 |
| **配置/运维** | 3 | C4, B11, C14 |

### 跨通道/跨 session 任务

以下任务涉及多个通道或 session 协作：

| 任务 | 涉及通道 | 说明 |
|------|---------|------|
| B5 Gateway 并发重构 | 飞书 lab → webchat | 飞书讨论需求设计 → webchat 执行代码开发 |
| B4 飞书 SDK Skill 化 | 飞书 lab → webchat | 飞书发现问题 → webchat 重构 |
| B8 Analytics 修复 | webchat → 飞书 lab | webchat 诊断 → 飞书 lab 执行修复 |
| B16 文件发送修复 | webchat → 飞书 lab | webchat 修复代码 → 飞书 lab 测试验证 |
| B21 材料整合 | 飞书 lab (多 session) | 跨多个 session 持续处理 |
| A8 图片输入 | webchat + cli_direct | webchat 提需求 → cli 执行（因涉及重启 worker） |
| A10 SSE 超时 | cli_direct + webchat | cli 诊断 → webchat 修复 |

---

## 二、示例：Task-001 详细整理

**选择 A1 (doubao-search Skill 创建)** 作为第一个完整整理的评测任务，原因：
- ✅ 自包含性最好（不依赖复杂的已有代码库）
- ✅ 可复现性高（外部 API 可 mock）
- ✅ 成功标准明确（文件存在 + 脚本可执行 + 测试通过）
- ✅ 涵盖完整开发流程（需求→架构→编码→测试→文档）
- ✅ 有多轮用户交互（考验 agent 的交互能力）

### 文件结构

```
tasks/task-001-doubao-search-skill/
├── task.yaml                          # 任务元数据、评测维度、成功标准
├── query.md                           # 4 轮用户 query（含条件触发说明）
├── eval_prompt.md                     # LLM 评价 prompt（5 维度打分，供智能体评价时参考）
├── initial_state/                     # 初始文件状态
│   ├── config_mock.json               # 脱敏配置（含 mock API URL）
│   └── skills/                        # 已有 skill
│       ├── dev-workflow/SKILL.md      # 开发规范
│       └── skill-creator/SKILL.md     # Skill 创建指南
├── mocks/
│   └── volcengine_mock.py             # 火山方舟 API Mock Server
└── reference/                         # 参考答案（可选）
    └── expected_files/                # 预期产出的文件
```

### 评测维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 功能完整性 | 30% | 三个命令可用、配置读取正确、JSON 输出 |
| 代码质量 | 20% | 结构清晰、错误处理、无敏感信息泄露 |
| 开发规范 | 20% | 遵循 dev-workflow（文档先行、任务拆解） |
| 效率 | 15% | 工具调用次数合理（参考 ~60 次） |
| 鲁棒性 | 15% | 有测试、处理异常情况 |

### 参考执行轨迹（从历史 session 提取）

原始 session `webchat_1772349033` 的执行摘要：
1. Agent 读取已有 skill 目录了解结构 → 检查 volcengine 配置
2. 发现 apiKey 为空 → 询问用户
3. 用户确认 key 已配好 → Agent 创建文档（REQUIREMENTS → ARCHITECTURE → DEVLOG）
4. 创建脚本 `doubao_search.py` + `SKILL.md`
5. 测试发现需要 endpoint ID → 用户提供
6. 测试发现联网搜索未生效 → 用户提供参考代码（需要 `tools=[{"type": "web_search"}]`）
7. 修复脚本 → 测试通过 → 完成

**总计**: ~63 次工具调用，9 轮用户消息（含 4 轮关键信息提供）

---

## 三、Docker 评测平台方案

详见 [`platform/DESIGN.md`](platform/DESIGN.md)

### 核心架构

```
Host (eval.py)
  │
  ├── 1. 加载 task.yaml
  ├── 2. docker-compose up (mock-api + agent-runner)
  │       ├── mock-api:   模拟外部 API（volcengine 等）
  │       └── agent-runner: 
  │             ├── 初始化 workspace (initial_state → /workspace)
  │             ├── 多轮驱动 agent 执行
  │             ├── 收集 trajectory + final_state
  │             └── 运行验证测试
  ├── 3. docker-compose down
  ├── 4. 评价：由执行任务的智能体统一读取 results 并评分
  └── 5. 生成报告
```

### 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| **隔离方式** | Docker 容器 | 避免评测任务污染宿主环境，可复现 |
| **外部 API** | Mock Server | 消除网络依赖，确定性结果 |
| **多轮交互** | 条件触发 + 预设注入 | 模拟真实用户行为，但保持可复现 |
| **评价方式** | 自动验证 + 智能体评价 | 硬性标准自动检查；软性质量由执行任务的智能体统一评价（不配置则跳过） |
| **Agent 注入** | Volume 挂载 | 方便对比不同版本的 agent 框架 |

### 使用方式

```bash
# 单任务评测
python3 eval.py run --task task-001 --agent ./nanobot-v1

# 多策略对比
python3 eval.py compare \
  --task task-001 \
  --agents "baseline=./nanobot-v1,improved=./nanobot-v2" \
  --runs 3

# 全套评测
python3 eval.py run-all --agent ./nanobot-v1 --output ./results/run-001
```

### 可对比的策略维度

| 维度 | 示例变量 |
|------|---------|
| LLM 模型 | Claude Sonnet / GPT-4o / Deepseek |
| 系统提示词 | 不同的 AGENTS.md 内容 |
| 工具策略 | 工具集限制、工具描述详细度 |
| 记忆策略 | 有/无长期记忆 |
| Skill 加载 | 不同 skill 组合 |
| 循环参数 | max_iterations, tool_call_limit |
| 温度参数 | temperature 0 / 0.3 / 0.7 |
| 上下文管理 | 不同 consolidation 策略 |

### 演进路线

| Phase | 内容 | 状态 |
|-------|------|------|
| **Phase 1: MVP** | 手动提炼 3-5 个任务 + 单容器执行 + LLM 评价 | 🔜 |
| **Phase 2: 自动化** | 自动从 session 提炼任务 + 并行执行 + Web Dashboard | 📋 |
| **Phase 3: CI** | 代码提交自动跑评测 + 回归检测 + 趋势图 | 📋 |
