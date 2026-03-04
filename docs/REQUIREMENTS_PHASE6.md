# eval-bench Phase 6: 架构解耦 + Skill 化需求文档

## 1. 背景与场景

### 1.1 当前状态

eval-bench 目前是一个紧耦合的评测项目：
- 评测框架（platform/）和测例（tasks/）在同一个仓库中
- 测例的创建过程是手动的（人工分析 session → 手工构造 task.yaml + query.md + initial_state）
- 无法规模化：每个新测例需要深入了解框架内部结构

### 1.2 目标场景

**组织级部署**：
```
┌─────────────────────────────────────────────────────────────────┐
│  组织内所有 Agent 用户                                           │
│                                                                 │
│  用户 A ──→ 定期整理 session → 提炼测例清单 → 构造测例实例         │
│  用户 B ──→ 定期整理 session → 提炼测例清单 → 构造测例实例         │
│  用户 C ──→ ...                                                 │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  测例仓库（集中汇总）                                      │    │
│  │  ├── task-001-xxx/                                       │    │
│  │  ├── task-002-xxx/                                       │    │
│  │  ├── task-003-xxx/ (来自用户 A)                           │    │
│  │  ├── task-004-xxx/ (来自用户 B)                           │    │
│  │  └── ...                                                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  框架团队                                                 │    │
│  │  ├── 运行测例集 → 评测报告                                │    │
│  │  ├── 分析薄弱环节 → 改进框架                              │    │
│  │  └── 回归验证 → 确保改进不退化                            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 核心诉求

1. **评测架构与测例解耦**：框架是基础设施，测例是数据，两者独立演进
2. **测例提炼自动化**：通过 Skill 辅助用户从 session 中发现、构造测例
3. **渐进式构造**：先生成清单，再逐个构造，过程中可能反馈框架需要改进
4. **批量构造**：利用子智能体并行构造多个测例

## 2. 解耦设计

### 2.1 分离原则

| 组件 | 归属 | 说明 |
|------|------|------|
| `platform/` | 框架仓库 (eval-bench) | runner.py, Dockerfile, docker-compose, DESIGN.md |
| `tasks/` | 测例仓库 (eval-tasks) 或框架仓库的 tasks/ 子目录 | task.yaml, query.md, initial_state, verify/, mocks/ |
| `run.sh` | 框架仓库 | 入口脚本，接受 `--task-dir` 参数指定外部测例路径 |
| `results/` | 运行时产物 | 不提交，每次运行生成 |

### 2.2 解耦方式

**方案：tasks 目录外部化**

```bash
# 当前（耦合）
./run.sh --task task-001-doubao-search-skill

# 解耦后
./run.sh --task-dir /path/to/eval-tasks/task-001-doubao-search-skill

# 或者保持 tasks/ 子目录作为内置示例，同时支持外部路径
./run.sh --task task-001  # 从内置 tasks/ 找
./run.sh --task-dir ~/my-tasks/task-042  # 从外部路径找
```

**关键改动**：
- `run.sh` 和 `docker-compose.yaml`：支持 `TASK_DIR` 环境变量指向外部路径
- `runner.py`：已经通过 `TASK_DIR` 环境变量定位任务，无需改动
- 内置的 `tasks/` 保留作为示例和框架自测

### 2.3 测例规范（Task Specification）

定义一个清晰的测例规范，使任何人都能按规范构造测例：

```
task-{id}-{slug}/
├── task.yaml          # 必须：任务元数据、验证规则
├── query.md           # 必须：用户 query（单轮或多轮）
├── initial_state/     # 可选：初始文件状态
│   ├── skills/        # 预置 skill
│   ├── memory/        # 预置记忆
│   └── project_code/  # 预置项目代码（Type B）
├── verify/            # 可选：pytest 验证脚本
│   └── test_xxx.py
├── mocks/             # 可选：Mock 服务脚本
│   └── xxx_mock.py
├── eval_prompt.md     # 可选：评价 prompt
└── reference/         # 可选：参考答案
```

## 3. Skill 设计

### 3.1 Skill 1: eval-session-scanner — 测例清单提炼

**职责**：扫描指定时间范围内的 session，识别可提炼为测例的独立任务。

**输入**：
- 时间范围（起止时间或 "从上次整理开始"）
- 已有测例清单（避免重复）
- 排除规则（隐私敏感、无意义的任务类型）

**输出**：
- 候选测例清单（Markdown 表格），每条包含：
  - 来源 session
  - 任务摘要
  - 分类（A/B/C/D）
  - 难度估计
  - 可行性评估（自包含性、可复现性、是否需要 mock）
  - 建议的 task-id 和 slug

**工作方式**：
- 读取 session JSONL，提取 user 消息和 assistant 工具调用
- 按时间和主题分割为独立任务
- 排除：ping/hello、纯重启操作、跨 session 继续的片段、含敏感信息的任务
- 对比已有测例清单去重

### 3.2 Skill 2: eval-task-builder — 测例构造

**职责**：根据清单中的一条描述，构造符合框架规范的完整测例实例。

**输入**：
- 候选测例描述（来自 Skill 1 的输出）
- 来源 session 路径
- 目标输出目录
- 评测框架的测例规范文档

**输出**：
- 完整的 `task-{id}-{slug}/` 目录，包含所有必要文件

**工作方式**：
1. 读取来源 session，提取相关对话片段
2. 分析任务类型（Type A / Type B），确定 initial_state 需求
3. 构造 task.yaml（元数据、验证规则、资源限制）
4. 构造 query.md（从原始对话中提炼，去除敏感信息，保留关键交互模式）
5. 构造 initial_state/（从 workspace 快照或 git 历史提取）
6. 构造 verify/（声明式规则或 pytest 脚本）
7. 构造 mocks/（如需要外部 API mock）
8. 构造 eval_prompt.md（评价维度）
9. **反馈机制**：如果发现框架不支持某种测例模式，生成改进建议

### 3.3 Skill 3: eval-framework-maintainer — 框架维护

**职责**：根据测例构造过程中产生的框架改进需求，修改评测框架，并确保已有测例兼容。

**输入**：
- 改进需求描述（来自 Skill 2 的反馈）
- 当前框架代码
- 已有测例列表

**工作方式**：
1. 分析改进需求，评估影响范围
2. 修改框架代码（runner.py, docker-compose, Dockerfile 等）
3. 对已有测例运行兼容性检查（至少验证 task.yaml 解析 + verify_criterion 不报错）
4. 更新 DESIGN.md / DEVLOG.md
5. Git 提交

### 3.4 Skill 4: eval-task-batch-builder — 批量构造

**职责**：利用子智能体，根据清单批量构造多个测例。

**输入**：
- 候选测例清单（Skill 1 的完整输出）
- 过滤条件（只构造 A 类、或指定 ID 范围）

**工作方式**：
1. 解析清单，筛选目标测例
2. 对每个目标测例，spawn 子智能体调用 Skill 2 构造
3. 收集构造结果和框架改进反馈
4. 汇总报告

## 4. 新增测例清单（3月2日 15:55 之后）

基于 session 分析，3月2日 15:55 之后的新任务候选：

| # | 任务名 | 来源 Session | 类型 | 分类 | 难度 | 说明 |
|---|--------|-------------|------|------|------|------|
| **N1** | 多仓库公开推送 + 敏感信息清理 | `webchat_1772441000` | 运维/安全 | 🟡B | ⭐⭐ | 将多个仓库推送到 GitHub，清理敏感信息（飞书 ID），修复 SETUP.md |
| **N2** | Upstream merge (nanobot) | `webchat_1772445453` | 代码合并 | 🟡B | ⭐⭐⭐⭐ | 合并 188 个 upstream commits，解决 9 个文件冲突，修复测试 |
| **N3** | 记忆压缩与整理 | `webchat_1772446986` | 记忆管理 | 🔵C | ⭐ | 压缩 MEMORY.md，将仓库特定内容移到各自文档 |
| **N4** | 跨通道查看任务进展 | `feishu.lab.1772448393` | 信息查询 | 🔵C | ⭐ | 从飞书通道查看 webchat session 的任务进展 |
| **N5** | 飞书转发消息解析测试 | `feishu.lab.1772451394` | 功能测试 | 🟡B | ⭐⭐ | 测试合并转发消息解析：发送人、@关系、文件下载 |
| **N6** | Message tool 输出处理 | `webchat_1772528059` | Bug 修复 | 🟢A | ⭐⭐ | agent 通过 message tool 发送的内容不显示在前端，需处理为 session 条目 |
| **N7** | 科研项目指南书整合 | `feishu.lab.1772529076` | 文档协作 | 🟡B | ⭐⭐ | 从飞书转发消息中整合科研项目指南内容 |
| **N8** | 算力国产化策略提纲 | `feishu.ST.1772584826` | 文档生成 | 🟡B | ⭐⭐⭐ | 从多份素材（PPT/PDF/DOCX）整理讨论提纲，创建飞书文档 |
| **N9** | Web Chat 前端卡死诊断 | `cli_direct` (17:28~19:15) | Bug 诊断 | 🟡B | ⭐⭐ | 多页面打开后关闭一个导致前端卡死，需诊断 SSE/连接数问题 |
| **N10** | Gemini Provider 接入诊断 | `cli_direct` (13:28~13:50) | Bug 诊断 | 🟢A | ⭐⭐ | 诊断 Gemini API 接入失败（apiBase 路径问题），修复 provider 配置 |
| **N11** | 飞书文档表格格式修复 | `webchat_1772619019` | Bug 修复 | 🟢A | ⭐⭐⭐ | 飞书文档内嵌表格格式异常，需理解 skill 工具逻辑并修复 |
| **N12** | Provider 配置热加载 | `webchat_1772603489` | 功能改进 | 🟢A | ⭐⭐ | config 保存后自动 reload worker ProviderPool + 新增 preferred_model |
| **N13** | Error response 修复 | `webchat_1772445453` (12:34) | Bug 修复 | 🟢A | ⭐⭐ | merge 后 error response 不写入 JSONL，前端无法显示错误 |
| **N14** | CLI 重启服务失败诊断 | `cli.1772603563` + `cli.1772605154` | 运维诊断 | 🔴D | ⭐ | CLI 下执行 restart 命令多次失败，需参考 skill 文档 |
| **N15** | 评测框架构建与迭代 | `webchat_1772437300` + `webchat_1772639822` | 工具开发 | 🔴D | ⭐⭐⭐⭐⭐ | eval-bench 自身的开发过程（元任务，不适合自评测） |

### 新增统计

| 分类 | 数量 | 说明 |
|------|------|------|
| 🟢 A类 | 5 | N6, N10, N11, N12, N13 — 自包含、可复现 |
| 🟡 B类 | 5 | N1, N2, N5, N7, N8 — 需简化/mock |
| 🔵 C类 | 2 | N3, N4 — 轻量任务 |
| 🔴 D类 | 3 | N9, N14, N15 — 不适合/元任务 |

## 5. 实施计划

### Phase 6.1: 需求与架构设计 ← **当前**
- [x] 需求文档（本文件）
- [ ] 架构设计文档更新

### Phase 6.2: 框架解耦
- [ ] run.sh 支持 `--task-dir` 外部路径
- [ ] docker-compose.yaml 支持外部 TASK_DIR
- [ ] 测例规范文档 (TASK_SPEC.md)
- [ ] 验证：已有 task-001, task-002 在解耦后仍正常工作

### Phase 6.3: Skill 1 — eval-session-scanner
- [ ] SKILL.md + scripts/scan_sessions.py
- [ ] 对 3月2日 15:55 之后的 session 运行，验证输出

### Phase 6.4: Skill 2 — eval-task-builder
- [ ] SKILL.md + scripts/
- [ ] 构造 1 个 A 类测例验证流程

### Phase 6.5: Skill 3 — eval-framework-maintainer
- [ ] SKILL.md + 兼容性检查脚本
- [ ] 处理 Skill 2 构造过程中的框架改进需求

### Phase 6.6: Skill 4 — eval-task-batch-builder
- [ ] SKILL.md + 子智能体编排逻辑
- [ ] 批量构造 A 类测例

### Phase 6.7: 集成验证
- [ ] 端到端：scan → build → run → verify
- [ ] Git 提交 + 推送
