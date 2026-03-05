---
name: eval-session-scanner
description: eval-bench 测例清单提炼。从 nanobot session 历史中扫描、识别、整理可提炼为评测测例的独立任务。
---

# eval-session-scanner — 测例清单提炼

从 nanobot session 历史中扫描、识别、整理可提炼为评测测例的独立任务。

---

## 体系运转逻辑

eval-bench 评测体系由 4 个 Skill 协同运转：

```
┌──────────────────────────────────────────────────────────────────┐
│                    eval-bench 测例生命周期                         │
│                                                                  │
│  ① eval-session-scanner (本 Skill)                               │
│     扫描 session → 识别候选任务 → 更新 CASE_REGISTRY.md            │
│                          ↓                                       │
│  ② eval-task-builder                                             │
│     根据候选描述 → 构造完整测例目录 (task.yaml + query.md + ...)    │
│     → 如发现框架不支持 → 生成改进建议                               │
│                          ↓                                       │
│  ③ eval-framework-maintainer                                     │
│     处理改进建议 → 修改框架 → 兼容性检查 → 已有测例按需修复          │
│                          ↓                                       │
│  ④ eval-task-batch-builder                                       │
│     批量调用 ② → spawn 子智能体并行构造多个测例                     │
│                          ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  测例仓库 (eval-bench/tasks/ 或外部 eval-tasks/)          │    │
│  │  所有 ✅ 已构造 的测例汇集于此                              │    │
│  └──────────────────────────────────────────────────────────┘    │
│                          ↓                                       │
│  框架团队: ./run.sh --task-dir <path> → 评测 → 改进框架           │
└──────────────────────────────────────────────────────────────────┘
```

### 定期运转流程

```
1. 用户定期运行本 Skill → 扫描新 session → 候选追加到 CASE_REGISTRY.md
2. 用户审核清单 → 去除敏感/无意义的 → 确认要构造的测例
3. 使用 eval-task-builder 逐个构造（或 eval-task-batch-builder 批量构造）
4. 构造完成后 → 回到 CASE_REGISTRY.md 更新状态为 "✅ 已构造" + 填写测例目录名
5. 如果构造过程中发现框架需改进 → 使用 eval-framework-maintainer 处理
6. 框架团队从测例仓库拉取所有 ✅ 测例 → 运行评测 → 改进框架 → 回归验证
```

### 组织级部署场景

```
每个 Agent 用户:
  - 安装本 Skill + eval-bench 框架
  - 定期运行 scanner → 提炼自己的测例
  - 构造后推送到组织的测例仓库

框架团队:
  - 汇总所有用户的测例
  - 统一运行评测套件
  - 根据薄弱环节改进框架
  - 回归验证确保不退化
```

---

## 核心文件

| 文件 | 位置 | 说明 |
|------|------|------|
| `CASE_REGISTRY.md` | `eval-bench-data/` | 统一测例清单（本地数据，不随框架分发） |
| `scripts/scan_sessions.py` | 本 Skill 目录 | Session 扫描脚本 |
| `TASK_SPEC.md` | `eval-bench/docs/` | 测例规范 |

### 目录结构说明

```
~/.nanobot/workspace/
├── eval-bench/                    # 框架仓库（Git 管理，可分发）
│   ├── skills/                    # 4 个配套 Skill（随框架分发）
│   │   ├── eval-session-scanner/  # ← 本 Skill
│   │   ├── eval-task-builder/
│   │   ├── eval-framework-maintainer/
│   │   └── eval-task-batch-builder/
│   ├── platform/                  # Docker 运行时
│   ├── docs/                      # 文档
│   └── run.sh                     # 入口脚本
│
├── eval-bench-data/               # 本地数据（不分发）
│   ├── CASE_REGISTRY.md           # 测例清单
│   ├── tasks/                     # 测例目录
│   └── results/                   # 运行结果
│
└── skills/                        # nanobot skill 目录
    ├── eval-session-scanner -> ../eval-bench/skills/eval-session-scanner
    ├── eval-task-builder -> ...   # symlink 到 eval-bench
    └── ...
```

## 使用方式

### 1. 扫描新 session 并输出候选清单

```bash
# 扫描指定时间范围内的 session
python3 ~/.nanobot/workspace/eval-bench/skills/eval-session-scanner/scripts/scan_sessions.py \
  --sessions-dir ~/.nanobot/workspace/sessions \
  --since "2026-03-02T15:55:00" \
  --output /tmp/scan_result.md

# 从上次扫描开始（读取 CASE_REGISTRY.md 中最后一个 Batch 的结束时间）
python3 ~/.nanobot/workspace/eval-bench/skills/eval-session-scanner/scripts/scan_sessions.py \
  --sessions-dir ~/.nanobot/workspace/sessions \
  --since-last-batch \
  --registry ~/.nanobot/workspace/eval-bench-data/CASE_REGISTRY.md \
  --output /tmp/scan_result.md
```

### 2. 让智能体执行完整流程

直接告诉智能体：

> 请使用 eval-session-scanner skill，扫描从上次整理到现在的 session，
> 整理候选测例清单，并更新 CASE_REGISTRY.md。

智能体会：
1. 读取 CASE_REGISTRY.md 确定上次扫描的截止时间
2. 运行 scan_sessions.py 扫描新 session
3. 对扫描结果进行人工级别的分析（分类、去重、评估可行性）
4. 将新候选追加到 CASE_REGISTRY.md 的新 Batch 中

### 3. 审核与整合

扫描完成后，用户应审核输出：
- 去除含敏感信息的任务（个人数据、密钥等）
- 去除无意义的任务（ping/hello、纯重启）
- 调整分类和难度评估
- 确认哪些候选值得构造

---

## CASE_REGISTRY.md 格式说明

### Batch 结构

每次扫描产生一个新 Batch：

```markdown
## Batch N: YYYY-MM-DD HH:MM ~ YYYY-MM-DD HH:MM

> 来源：X 个 session，描述

### 🟢 A类：高度适合提炼
| # | 任务名 | 来源 Session | 类型 | 难度 | 状态 | 构造记录 | 说明 |
...

### 🟡 B类：可提炼但需简化
...

### 🔵 C类：轻量任务
...

### 🔴 D类：不适合提炼
...
```

### 状态标记

| 标记 | 含义 |
|------|------|
| `📋 候选` | 已识别，尚未构造 |
| `🔨 构造中` | 正在通过 eval-task-builder 构造 |
| `✅ 已构造` | 测例目录已就绪，可运行 |
| `❌ 放弃` | 评估后决定不构造（注明原因） |
| `🔄 需更新` | 框架变更后需要重新适配 |

### 编号规则

- Batch 1: A1~A16, B1~B21, C1~C16（首次整理的历史任务）
- Batch 2: N1~N15（第二次扫描的新任务，N = New）
- Batch 3+: 后续扫描使用递增编号，前缀为 Batch 号（如 B3-01, B3-02...）

### 构造记录

测例构造完成后，更新对应行：

```
| A1 | 创建 doubao-search Skill | ... | ✅ 已构造 | task-001-doubao-search-skill (2026-03-02) | ... |
```

---

## 扫描脚本参数

```
scan_sessions.py [OPTIONS]

必选:
  --sessions-dir PATH     Session JSONL 文件目录

时间范围（二选一）:
  --since DATETIME        起始时间 (ISO 格式, 如 "2026-03-02T15:55:00")
  --since-last-batch      从 CASE_REGISTRY.md 最后 Batch 的结束时间开始
                          （需配合 --registry）

可选:
  --until DATETIME        截止时间（默认: 当前时间）
  --registry PATH         CASE_REGISTRY.md 路径（用于去重和读取上次时间）
  --output PATH           输出文件路径（默认: stdout）
  --min-user-messages N   最少用户消息数（过滤太短的 session，默认: 2）
  --exclude-patterns      排除的 session 名称模式（逗号分隔）
```

## 排除规则

以下类型的 session/任务自动排除或标记为 D 类：

1. **纯重启操作**：只包含 "重启 gateway/webchat" 类指令
2. **Ping/Hello**：只有 1 条用户消息且无实质内容
3. **跨 session 继续**：主要内容是 "继续上次的任务"
4. **敏感信息**：包含 API Key、密码、个人身份信息
5. **元任务（session 级别）**：session 的主题是 eval-bench 自身的开发

> ⚠️ **元任务的细粒度处理**：排除规则第 5 条针对的是 **session 整体主题**。
> 即使 session 主题是元任务，其中的**子环节**仍可能包含有独立评测价值的能力考察：
>
> | 子环节类型 | 示例 | 是否提炼 |
> |-----------|------|---------|
> | 长文档细粒度编辑（多处精准修改） | 批量更新 CASE_REGISTRY 状态标记 | ✅ 可提炼 |
> | 原则/规则的归纳整理 | 从 review 经验中提炼预标记原则 | ✅ 可提炼 |
> | 大文档分段上传 + 错误恢复 | 上传 GUIDE.md 到飞书遇到 429 限流 | ✅ 可提炼 |
> | 纯讨论/确认/对齐 | 跟用户对齐放弃原则 | ❌ 不提炼 |
> | 简单的 CRUD 操作 | 创建目录、移动文件 | ❌ 不提炼 |
>
> **原则**：扫描时不要因为 session 主题是元任务就跳过，应逐个子环节审视。
> 如果子环节具备「多步推理 + 工具调用 + 可客观评测」的特征，就值得提炼。

## 分类标准

| 分类 | 标准 |
|------|------|
| 🟢 A类 | 自包含、可复现、成功标准明确、不需要外部服务 mock（或 mock 简单） |
| 🟡 B类 | 有价值但需简化：涉及外部服务、跨通道、上下文复杂、需要大量 mock |
| 🔵 C类 | 轻量任务：简单问答、小修复、信息查询，适合冒烟测试 |
| 🔴 D类 | 不适合：纯运维、过于碎片化、高度依赖实时环境、含敏感信息 |

---

## 预标记原则

> 扫描产出的候选 case 在用户审核前，可根据以下原则预标记状态。
> 预标记不等于最终决定——用户审核时可覆盖。
> 原则来源于 2026-03-05 首次系统性 review 的经验总结。

### ❌ 预标记放弃的原则

符合以下**任一**条件的 case，扫描时预标记为 `❌ 放弃`：

| # | 原则 | 说明 | 典型案例 |
|---|------|------|---------|
| R1 | **平台原生 API 依赖** | 依赖 macOS AppleScript、Windows COM 等平台原生接口，Docker 沙箱无法运行 | A2(calendar-reader), C1/C2(日程查询) |
| R2 | **价值过低 / 重复覆盖** | 本质是简单计算/配置查找，无多步推理无区分度；或同等难度的测例已有足够覆盖 | A9(base64反算), B7(/new策略反转) |
| R3 | **输出不可客观评测** | 架构设计、方案讨论等，输出是主观文档，难以自动化评分 | B20(架构设计) |
| R4 | **纯知识问答** | 不涉及工具调用，纯靠模型知识回答，测不出 agent 工具使用能力 | C4(飞书配置指引) |
| R5 | **依赖实时运行环境** | 高度依赖实时进程状态（端口占用、进程存活），无法预设初始状态 | C12(interjection失效), C13(终端闪退) |
| R6 | **涉及人机交互** | 任务过程中需要用户实时反馈/操作，无法在自动化评测中模拟 | N5(飞书转发消息解析测试) |
| R7 | **不可回滚的外部操作** | 需要真实 GitHub 推送、真实邮件发送等不可回滚的外部操作 | N1(多仓库推送) |
| R8 | **非技术任务** | 素材整合/文档协作类且不涉及代码开发，需人工判断是否保留 | B21(科学算力材料), N7/N8(素材整合) |

### 🔶 预标记飞书专项的原则

符合以下条件的 case，扫描时预标记为 `🔶 飞书专项`：

| 条件 | 说明 |
|------|------|
| 涉及飞书 API 调用 | 包括飞书文档 CRUD、消息发送/解析、权限管理、租户接入等 |
| Mock 成本 > 测例价值 | 飞书 API 体系复杂，mock 成本极高 |
| 但任务本身有评测价值 | 考察 agent 对 SDK/API 的理解和使用能力 |

**飞书专项处理方式**：
- 正常 scan 出来，记录到 CASE_REGISTRY.md
- 标记为 `🔶 飞书专项`，不纳入常规沙箱评测集
- 评测时直接与线上飞书 API 交互，不 mock
- 可作为"飞书能力评测"子集单独运行
- 需要配置真实飞书应用凭证才能执行

### 🔀 预标记合并的原则

| 条件 | 说明 |
|------|------|
| 两个 case 考察同一能力的不同侧面 | 如 A12(折叠优化) 和 A13(展示精细化) |
| 一个 case 是另一个的特例/子集 | 如 B18(超大图片损坏) 是 B17(Session损坏) 的特例 |
| 一个 case 是另一个的子需求 | 如 B10(/session命令) 是 B6(斜杠命令体系) 的子需求 |

合并时保留更完整/更通用的 case 作为主 case，被合并的标记 `🔀 已合并` 并注明合并目标。

### 📌 日常标记机制（Inline Case Hint）

在日常工作中，用户或 Agent 可以在对话中随时标记值得提炼为测例的环节，
后续 scanner 扫描时会优先关注这些标记。

#### 标记格式

在 session 对话中（用户消息或 assistant 消息均可），使用以下格式：

```
[EVAL-HINT] <简短描述>
```

**示例**：
- 用户说：`[EVAL-HINT] 这个表格 bug 诊断过程很有价值`
- Agent 说：`[EVAL-HINT] 大文档分段上传 + 429 限流恢复`

#### 扫描时处理

scanner 扫描 session 时：
1. **优先检测** `[EVAL-HINT]` 标记，有标记的子环节直接进入候选清单
2. 标记中的描述作为候选 case 的初始说明
3. 标记所在位置帮助定位 session 中的具体环节
4. 无标记的 session 仍按常规逻辑分析

#### 使用场景

- 用户在完成一个有挑战性的任务后，随手标记
- Agent 在执行复杂操作后，主动建议标记（需用户确认）
- Review 他人 session 时，标记有价值的环节

> 💡 **鼓励在工作中养成标记习惯**——这比事后回顾 session 效率高得多。
> 不确定是否有价值时也可以标记，scanner 审核时会再次评估。

### ⚠️ 不自动放弃的特殊情况

以下情况即使看似符合放弃原则，仍应保留为候选，由用户决定：

| 情况 | 说明 | 典型案例 |
|------|------|---------|
| **范围大但考察复杂任务能力** | 架构级重构/全栈项目，虽然范围大但可用 general 评价方式考察 agent 做复杂任务的能力 | B5(并发重构), B19(Web Chat从零搭建) |
| **可从日志/数据中截取构造** | 虽然原始场景依赖实时环境，但可以从日志/DB 中截取对应部分作为测例输入 | C9(Gateway卡住诊断), B8(DB修复) |
| **可基于 Git 历史构造** | 依赖特定 git 状态，但可以从 git 历史中 checkout 对应快照构造 | C8(Git分支确认), N2(Upstream merge) |
| **高难度但有独特评测价值** | 特别难的任务可以作为 "挑战级" 测例保留 | N2(188 commits merge) |
