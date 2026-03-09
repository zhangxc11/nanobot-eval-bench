# nanobot Eval Bench — Agent 评测基准

从历史 session 中提炼评测任务，用于衡量不同 Agent 策略的效果。

---

## 快速开始

```bash
# 1. 设置 API Key
export AGENT_API_KEY=sk-your-api-key

# 2. 运行单个测例（从 eval-bench-data/tasks/ 查找）
./run.sh --task task-001-doubao-search-skill

# 3. 运行外部测例
./run.sh --task-dir /path/to/my-task

# 4. 指定 nanobot 源码路径
./run.sh --nanobot-src ~/code/nanobot

# 5. 指定不同模型
./run.sh --provider volcengine --model ep-xxx --base-url https://ark.cn-beijing.volces.com/api/v3

# 6. Dry-run 模式（跳过 agent 执行，仅验证测例配置和 verify_script）
./run.sh --task task-001 --dry-run

# 7. 批量运行多个测例
./batch_run.sh task-001 task-002 task-003
./batch_run.sh --all                          # 运行所有测例
./batch_run.sh --glob "task-01*" --dry-run    # glob 匹配 + dry-run
./batch_run.sh --all --continue               # 断点续跑（跳过已有结果的）
```

## 项目结构

```
eval-bench/                        # 框架仓库（Git 管理，可分发）
├── README.md                      # 本文件
├── run.sh                         # 单测例运行脚本
├── batch_run.sh                   # 批量运行脚本（支持 glob/--all/--continue）
├── pack.sh                        # 打包分发脚本
├── .env.example                   # 环境变量模板
├── skills/                        # 📋 配套 Skill（随框架分发）
│   ├── eval-session-scanner/      #   扫描 session → 候选清单
│   ├── eval-task-builder/         #   候选 → 完整测例
│   ├── eval-framework-maintainer/ #   框架改进 + 兼容检查
│   └── eval-task-batch-builder/   #   批量构造
├── platform/                      # Docker 运行时
│   ├── runner.py                  #   容器内执行器
│   ├── Dockerfile.*               #   镜像定义
│   └── docker-compose.yaml        #   编排
└── docs/                          # 文档
    ├── TASK_SPEC.md               #   测例规范
    ├── ARCHITECTURE.md            #   架构设计
    └── DEVLOG.md                  #   开发日志

eval-bench-data/                   # 本地数据（不随框架分发）
├── CASE_REGISTRY.md               # 📋 统一测例清单
├── tasks/                         # 测例目录
│   ├── task-001-doubao-search-skill/
│   └── task-002-token-usage-analytics/
└── results/                       # 运行结果
```

### 为什么分离？

- **eval-bench/** 是通用框架，可以分发给任何人使用
- **eval-bench-data/** 是本地数据，包含从你自己的 session 提炼的测例
- nanobot 源码不存放在仓库中，`run.sh` 运行时自动从本地仓库同步最新版本

## 配套 Skill

eval-bench 提供 4 个配套 Skill，支撑测例的全生命周期：

| Skill | 职责 | 说明 |
|-------|------|------|
| **eval-session-scanner** | 扫描 session → 候选清单 | 定期运行，发现新的可提炼任务 |
| **eval-task-builder** | 候选描述 → 完整测例 | 根据一条描述构造可运行的测例目录 |
| **eval-framework-maintainer** | 框架改进 + 兼容检查 | 处理构造过程中的框架改进需求 |
| **eval-task-batch-builder** | 批量构造测例 | spawn 子智能体并行构造多个测例 |

Skill 随框架分发（在 `skills/` 目录中），通过 symlink 链接到 nanobot workspace：

```bash
# 安装 Skill（创建 symlink）
cd ~/.nanobot/workspace/skills
for s in eval-session-scanner eval-task-builder eval-framework-maintainer eval-task-batch-builder; do
    ln -sf ../eval-bench/skills/$s $s
done
```

### 运转流程

```
1. eval-session-scanner  → 扫描 session → 更新 CASE_REGISTRY.md
2. 用户审核清单          → 去除敏感/无意义的 → 确认构造目标
3. eval-task-builder     → 逐个构造测例（或 batch-builder 批量构造）
4. eval-framework-maintainer → 处理框架改进需求
5. ./run.sh              → 运行测例 → 评测报告
6. 框架团队              → 分析报告 → 改进框架 → 回归验证
```

## nanobot 源码

框架不捆绑 nanobot 源码。运行时自动从本地仓库同步：

```bash
# 方式 1: 自动检测（默认路径: ~/Documents/code/workspace/nanobot）
./run.sh

# 方式 2: 显式指定
./run.sh --nanobot-src /path/to/nanobot

# 方式 3: 环境变量
export NANOBOT_SRC_PATH=/path/to/nanobot
./run.sh
```

这样可以方便地测试不同版本/分支的 nanobot：

```bash
# 测试 main 分支
git -C ~/code/nanobot checkout main
./run.sh --task task-001

# 测试实验分支
git -C ~/code/nanobot checkout feat/new-tool-strategy
./run.sh --task task-001
```

## Dry-Run 模式

跳过 agent 执行，仅验证测例配置（task.yaml、initial_state、verify_script）是否正确：

```bash
# 单测例 dry-run
./run.sh --task task-001 --dry-run

# 批量 dry-run（快速验证所有测例）
./batch_run.sh --all --dry-run
```

Dry-run 模式下：
- ✅ 正常加载 task.yaml 和 query.md
- ✅ 正常初始化 workspace（复制 initial_state）
- ⏭️ **跳过** agent turns（不调用 LLM，不需要 API Key）
- ✅ 正常执行 pytest verification
- ✅ 正常输出 run_summary.json（含 `"dry_run": true` 标记）

## 批量运行

`batch_run.sh` 支持一次运行多个测例，自动收集结果并输出汇总：

```bash
# 指定测例 ID 列表
./batch_run.sh task-001 task-002 task-003

# glob 模式匹配（可多次使用）
./batch_run.sh --glob "task-01*" --glob "task-02*"

# 运行所有测例
./batch_run.sh --all

# 指定结果输出目录
./batch_run.sh --all --results-dir ./my-results

# 断点续跑（跳过已有 run_summary.json 的测例）
./batch_run.sh --all --continue --results-dir ./my-results
```

运行完成后输出：
- 每个测例的结果存到 `{results_dir}/{task_id}/`
- 格式化汇总表格（task_id, pass/fail, verification 通过率）
- `batch_summary.json` 汇总文件

## 文档

- [测例规范 (TASK_SPEC.md)](docs/TASK_SPEC.md) — 如何构造测例
- [技术方案 (DESIGN.md)](platform/DESIGN.md) — Docker 评测架构详解
- [开发日志 (DEVLOG.md)](docs/DEVLOG.md) — 开发过程记录
