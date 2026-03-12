---
name: eval-session-scanner
description: eval-bench 测例清单提炼。从 nanobot session 历史中扫描、识别、整理可提炼为评测测例的独立任务。
---

# eval-session-scanner — 测例清单提炼

从 nanobot session 历史中扫描、识别、整理可提炼为评测测例的独立任务。

---

## 体系运转逻辑

```
┌──────────────────────────────────────────────────────────────────┐
│                    eval-bench 测例生命周期                         │
│                                                                  │
│  ① eval-session-scanner (本 Skill)                               │
│     扫描 session → 识别候选任务 → 更新 CASE_REGISTRY.md            │
│                          ↓                                       │
│  ② eval-task-builder                                             │
│     根据候选描述 → 构造完整测例目录 (task.yaml + query.md + ...)    │
│                          ↓                                       │
│  ③ eval-framework-maintainer                                     │
│     处理改进建议 → 修改框架 → 兼容性检查                            │
│                          ↓                                       │
│  ④ eval-task-batch-builder                                       │
│     批量调用 ② → spawn 子智能体并行构造多个测例                     │
│                          ↓                                       │
│  测例仓库 → ./run.sh 评测 → 改进框架                              │
└──────────────────────────────────────────────────────────────────┘
```

## 核心文件

| 文件 | 位置 | 说明 |
|------|------|------|
| `CASE_REGISTRY.md` | `eval-bench-data/` | 统一测例清单（本地数据，不随框架分发） |
| `scripts/scan_sessions.py` | 本 Skill 目录 | Session 扫描脚本 |
| `TASK_SPEC.md` | `eval-bench/docs/` | 测例规范 |

### 目录结构

```
~/.nanobot/workspace/
├── eval-bench/                    # 框架仓库（Git 管理，可分发）
│   ├── skills/                    # 4 个配套 Skill（随框架分发）
│   │   ├── eval-session-scanner/  # ← 本 Skill
│   │   ├── eval-task-builder/
│   │   ├── eval-framework-maintainer/
│   │   └── eval-task-batch-builder/
│   ├── platform/                  # Docker 运行时
│   └── docs/                      # 文档
├── eval-bench-data/               # 本地数据（不分发）
│   ├── CASE_REGISTRY.md           # 测例清单
│   ├── tasks/                     # 测例目录
│   └── results/                   # 运行结果
└── skills/                        # nanobot skill 目录（symlink 到 eval-bench）
```

## 使用方式

### 1. 脚本扫描

```bash
# 扫描指定时间范围
python3 <skill-dir>/scripts/scan_sessions.py \
  --sessions-dir ~/.nanobot/workspace/sessions \
  --since "2026-03-02T15:55:00" --output /tmp/scan_result.md

# 从上次扫描结束时间开始（自动读取 CASE_REGISTRY.md）
python3 <skill-dir>/scripts/scan_sessions.py \
  --sessions-dir ~/.nanobot/workspace/sessions \
  --since-last-batch --registry <path>/CASE_REGISTRY.md --output /tmp/scan_result.md
```

### 2. 智能体执行完整流程

> 请使用 eval-session-scanner skill，扫描从上次整理到现在的 session，整理候选测例清单，并更新 CASE_REGISTRY.md。

智能体会：读取上次截止时间 → 运行扫描 → 分析分类 → 追加到新 Batch。

### 3. 审核与整合

扫描后用户审核：去除敏感/无意义任务，调整分类，确认构造目标。

---

## CASE_REGISTRY.md 格式

### Batch 结构示例

```markdown
## Batch N: YYYY-MM-DD HH:MM ~ YYYY-MM-DD HH:MM
> 来源：X 个 session，描述

### 🟢 A类：高度适合提炼
| # | 任务名 | 来源 Session | 类型 | 难度 | 状态 | 构造记录 | 说明 |

### 🟡 B类：可提炼但需简化
### 🔵 C类：轻量任务
### 🔴 D类：不适合提炼
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

- Batch 1: `A1~A16, B1~B21, C1~C16`（首次历史任务）
- Batch 2: `N1~N15`（N = New）
- Batch 3+: 前缀为 Batch 号（如 `B3-01, B3-02...`）

---

## 扫描脚本参数

```
scan_sessions.py [OPTIONS]

必选:  --sessions-dir PATH       Session JSONL 文件目录
时间范围（二选一）:
       --since DATETIME          起始时间 (ISO 格式)
       --since-last-batch        从 CASE_REGISTRY.md 最后 Batch 结束时间开始（需 --registry）
可选:  --until DATETIME          截止时间（默认: 当前时间）
       --registry PATH           CASE_REGISTRY.md 路径
       --output PATH             输出文件路径（默认: stdout）
       --min-user-messages N     最少用户消息数（默认: 2）
       --exclude-patterns        排除的 session 名称模式（逗号分隔）
```

## 排除规则

自动排除或标记为 D 类：
1. **纯重启操作** — 只含重启指令
2. **Ping/Hello** — 1 条消息无实质内容
3. **跨 session 继续** — 主要是 "继续上次任务"
4. **敏感信息** — 含 API Key、密码、个人身份信息
5. **元任务** — session 主题是 eval-bench 自身开发（但子环节若具备「多步推理 + 工具调用 + 可客观评测」仍可提炼）

## 分类标准

| 分类 | 标准 |
|------|------|
| 🟢 A类 | 自包含、可复现、成功标准明确、mock 简单或不需要 |
| 🟡 B类 | 有价值但需简化：涉及外部服务/跨通道/上下文复杂 |
| 🔵 C类 | 轻量任务：简单问答/小修复/信息查询，适合冒烟测试 |
| 🔴 D类 | 不适合：纯运维/碎片化/依赖实时环境/含敏感信息 |

> 📄 详细分类标准、预标记原则（❌放弃/🔶飞书专项/🔀合并/📌Inline Hint/⚠️特殊保留）见 [docs/CLASSIFICATION.md](docs/CLASSIFICATION.md)

## 日常标记（Inline Case Hint）

在 session 对话中使用 `[EVAL-HINT] <简短描述>` 标记有评测价值的环节。Scanner 扫描时优先检测此标记，有标记的子环节直接进入候选清单。

> 📄 详细标记格式与使用场景见 [docs/CLASSIFICATION.md](docs/CLASSIFICATION.md)
