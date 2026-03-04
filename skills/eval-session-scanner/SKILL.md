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
5. **元任务**：eval-bench 自身的开发过程

## 分类标准

| 分类 | 标准 |
|------|------|
| 🟢 A类 | 自包含、可复现、成功标准明确、不需要外部服务 mock（或 mock 简单） |
| 🟡 B类 | 有价值但需简化：涉及外部服务、跨通道、上下文复杂、需要大量 mock |
| 🔵 C类 | 轻量任务：简单问答、小修复、信息查询，适合冒烟测试 |
| 🔴 D类 | 不适合：纯运维、过于碎片化、高度依赖实时环境、含敏感信息 |
