# Eval Bench 部署指南

## 打包策略

```
┌─────────────────────────────────────────────────────────────┐
│  eval-bench-base (Docker image)                              │
│  ├── python:3.11-slim (支持 REGISTRY_MIRROR 镜像加速)        │
│  ├── 系统依赖: git, curl, jq, libxml2, libjpeg ...          │
│  └── Python 依赖: requirements-deps.txt                      │
│      构建一次，长期复用 ✅                                    │
├─────────────────────────────────────────────────────────────┤
│  eval-bench-agent (Docker image, 基于 base)                  │
│  ├── COPY .nanobot-src-staging/ → /opt/nanobot-src/          │
│  ├── PYTHONPATH=/opt/nanobot-src                             │
│  └── COPY runner.py → /opt/eval/runner.py                    │
│      每次运行自动同步最新 nanobot 源码，构建秒级 ✅           │
├─────────────────────────────────────────────────────────────┤
│  eval-bench-mock (Docker image)                              │
│  └── Mock 脚本通过 volume 挂载                                │
└─────────────────────────────────────────────────────────────┘
```

## 目录布局

```
~/.nanobot/workspace/
├── eval-bench/              # 框架（Git 仓库，可分发）
│   ├── skills/              # 4 个配套 Skill
│   ├── platform/            # Docker 运行时
│   ├── docs/                # 文档
│   └── run.sh               # 入口
│
├── eval-bench-data/         # 本地数据（不分发）
│   ├── CASE_REGISTRY.md     # 测例清单
│   ├── tasks/               # 测例目录
│   └── results/             # 运行结果
│
└── skills/                  # Skill symlinks
    ├── eval-session-scanner -> ../eval-bench/skills/...
    └── ...
```

## nanobot 源码机制

**不日常存放在 eval-bench 中**。`run.sh` 运行时自动从本地仓库同步：

1. 检测 `--nanobot-src` 参数 / `NANOBOT_SRC_PATH` 环境变量 / 默认路径
2. 过滤 `.git`、`__pycache__`、`tests` 等非必要文件
3. 拷贝到 `.nanobot-src-staging/`（临时目录，`.gitignore` 排除）
4. Docker build 时 COPY 进镜像

这样可以方便地测试不同版本/分支。

## 操作步骤

### 1. 配置环境变量

```bash
cd eval-bench
cp .env.example .env
# 编辑 .env，填入 API Key 等配置
```

### 2. 运行评测

```bash
# 自动检测 nanobot 源码 + 从 eval-bench-data/tasks/ 查找测例
./run.sh --task task-001-doubao-search-skill

# 显式指定 nanobot 源码
./run.sh --nanobot-src ~/code/nanobot --task task-001

# 外部测例目录
./run.sh --task-dir /path/to/my-task
```

### 3. 查看结果

```bash
ls ../eval-bench-data/results/<run_id>/

# 关键文件:
#   run_config.json    — 运行配置
#   run_summary.json   — 评测结果
#   trajectory.jsonl   — 完整对话轨迹
#   final_state/       — 最终文件快照
```

## 分发

```bash
# 打包框架（不含本地数据）
./pack.sh /tmp/eval-bench.tar.gz

# 接收方:
tar xzf eval-bench.tar.gz
cd eval-bench
cp .env.example .env && vim .env
mkdir -p ../eval-bench-data/tasks
# 将测例放到 ../eval-bench-data/tasks/ 中
./run.sh --nanobot-src /path/to/nanobot --task task-001
```

## 对比不同策略

```bash
# 对比不同 LLM
./run.sh --provider anthropic --model claude-sonnet-4-20250514 --run-id claude-sonnet
./run.sh --provider volcengine --model ep-xxx --run-id volcengine

# 对比不同 nanobot 版本
git -C ~/code/nanobot checkout main
./run.sh --run-id nanobot-main
git -C ~/code/nanobot checkout feat/new-strategy
./run.sh --run-id nanobot-new-strategy

# 对比结果
diff ../eval-bench-data/results/nanobot-main/run_summary.json \
     ../eval-bench-data/results/nanobot-new-strategy/run_summary.json
```
