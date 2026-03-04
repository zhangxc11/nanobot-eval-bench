# nanobot Eval Bench — Agent 评测基准

从历史 session 中提炼评测任务，用于衡量不同 Agent 策略的效果。

---

## 快速开始

```bash
# 1. 设置 API Key
export AGENT_API_KEY=sk-your-api-key

# 2. 运行内置测例
./run.sh --task task-001-doubao-search-skill

# 3. 运行外部测例
./run.sh --task-dir /path/to/my-task

# 4. 指定不同模型
./run.sh --provider volcengine --model ep-xxx --base-url https://ark.cn-beijing.volces.com/api/v3
```

## 项目结构

```
eval-bench/
├── README.md                      # 本文件
├── CASE_REGISTRY.md               # 📋 统一测例清单（所有候选 + 已构造的测例）
├── run.sh                         # 一键运行脚本
├── .env.example                   # 环境变量模板
├── docs/
│   ├── REQUIREMENTS.md            # 需求文档
│   ├── REQUIREMENTS_PHASE6.md     # Phase 6 解耦需求
│   ├── ARCHITECTURE.md            # 架构设计
│   ├── TASK_SPEC.md               # 测例规范（如何构造测例）
│   └── DEVLOG.md                  # 开发日志
├── platform/
│   ├── DESIGN.md                  # 详细技术方案
│   ├── runner.py                  # 容器内执行器
│   ├── Dockerfile.*               # Docker 镜像定义
│   └── docker-compose.yaml        # 编排
├── tasks/                         # 内置测例
│   ├── task-001-doubao-search-skill/
│   └── task-002-token-usage-analytics/
└── results/                       # 评测结果（不提交）
```

## 测例清单

所有候选和已构造的测例统一管理在 [CASE_REGISTRY.md](CASE_REGISTRY.md)。

当前状态：
- **68 个候选任务**（A类 21 + B类 26 + C类 18 + D类排除 ~36）
- **2 个已构造测例**（task-001, task-002）

### 已构造测例

| 测例 | 类型 | 难度 | 说明 |
|------|------|------|------|
| `task-001-doubao-search-skill` | Type A (Skill 开发) | ⭐⭐ | 从零创建豆包联网搜索 Skill |
| `task-002-token-usage-analytics` | Type B (代码修改) | ⭐⭐⭐ | 为 nanobot 添加 Token 用量统计系统 |

## 配套 Skill

eval-bench 提供 4 个配套 Skill，支撑测例的全生命周期：

| Skill | 职责 | 说明 |
|-------|------|------|
| **eval-session-scanner** | 扫描 session → 候选清单 | 定期运行，发现新的可提炼任务 |
| **eval-task-builder** | 候选描述 → 完整测例 | 根据一条描述构造可运行的测例目录 |
| **eval-framework-maintainer** | 框架改进 + 兼容检查 | 处理构造过程中的框架改进需求 |
| **eval-task-batch-builder** | 批量构造测例 | spawn 子智能体并行构造多个测例 |

### 运转流程

```
1. eval-session-scanner  → 扫描 session → 更新 CASE_REGISTRY.md
2. 用户审核清单         → 去除敏感/无意义的 → 确认构造目标
3. eval-task-builder     → 逐个构造测例（或 batch-builder 批量构造）
4. eval-framework-maintainer → 处理框架改进需求
5. ./run.sh              → 运行测例 → 评测报告
6. 框架团队              → 分析报告 → 改进框架 → 回归验证
```

## 文档

- [测例规范 (TASK_SPEC.md)](docs/TASK_SPEC.md) — 如何构造测例
- [技术方案 (DESIGN.md)](platform/DESIGN.md) — Docker 评测架构详解
- [开发日志 (DEVLOG.md)](docs/DEVLOG.md) — 开发过程记录
- [Phase 6 需求 (REQUIREMENTS_PHASE6.md)](docs/REQUIREMENTS_PHASE6.md) — 架构解耦设计
