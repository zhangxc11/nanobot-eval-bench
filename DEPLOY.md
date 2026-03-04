# Eval Bench 部署指南

## 打包策略

```
┌─────────────────────────────────────────────────────────────┐
│  eval-bench-base (Docker image)                              │
│  ├── python:3.11-slim (支持 REGISTRY_MIRROR 镜像加速)        │
│  ├── 系统依赖: git, curl, jq, libxml2, libjpeg ...          │
│  └── Python 依赖: requirements-deps.txt (支持 PIP_INDEX_URL) │
│      (nanobot 的所有 dependencies，但不装 nanobot 本身)       │
│      构建一次，长期复用 ✅                                    │
├─────────────────────────────────────────────────────────────┤
│  eval-bench-agent (Docker image, 基于 base)                  │
│  ├── COPY nanobot-src/ → /opt/nanobot-src/                   │
│  ├── PYTHONPATH=/opt/nanobot-src                             │
│  └── COPY runner.py → /opt/eval/runner.py                    │
│      每次换 nanobot 版本都重新构建（秒级，只 COPY 文件）      │
├─────────────────────────────────────────────────────────────┤
│  eval-bench-mock (Docker image)                              │
│  ├── python:3.11-slim                                        │
│  └── Mock 脚本通过 volume 挂载                                │
└─────────────────────────────────────────────────────────────┘
```

**为什么这样设计？**

- 评测不只是换 API，还可能测试 nanobot 代码改动（新 tool 策略、context 管理等）
- 依赖安装耗时（2-5分钟），提前打包到 base 镜像，只需构建一次
- nanobot 源码 COPY 进去，构建秒级完成
- 支持 `--nanobot-src` 指定任意版本的源码目录

## 前提条件

- ✅ Docker Desktop 已安装
- ✅ 有可用的 LLM API Key（Anthropic Claude / 火山方舟 等）
- ✅ nanobot 源码（本机或远程获取）

## 隔离保证

评测在 Docker 容器内运行，使用独立的 `~/.nanobot` 目录（容器内 `/eval/.nanobot`），**不会读写宿主机的 `~/.nanobot`**。

---

## 操作步骤

### 1. 获取 eval-bench

```bash
# 从 tar.gz 解压
tar xzf eval-bench.tar.gz
cd eval-bench
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 API Key 等配置
```

**Anthropic Claude 用户**:
```bash
AGENT_API_KEY=sk-ant-xxx
AGENT_PROVIDER=anthropic
AGENT_MODEL=claude-sonnet-4-20250514
```

**火山方舟 (volcengine) 用户**:
```bash
AGENT_API_KEY=你的API-Key
AGENT_PROVIDER=volcengine
AGENT_MODEL=ep-你的endpoint-id
AGENT_API_BASE=https://ark.cn-beijing.volces.com/api/v3
```

> ⚠️ volcengine 用户必须设置 `AGENT_API_BASE`，否则 LLM 调用会失败。

**国内用户网络配置**:
```bash
DOCKER_MIRROR=docker.1ms.run/
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 准备 nanobot 源码

```bash
# 方式一：使用 --nanobot-src 指定已有源码
./run.sh --nanobot-src ~/Documents/code/workspace/nanobot

# 方式二：clone 源码到 nanobot-src/ 目录
git clone https://github.com/zhangxc11/nanobot.git nanobot-src
```

### 4. 运行评测

```bash
# 基本用法（自动从 .env 读取配置）
./run.sh

# 指定任务
./run.sh --task task-001-doubao-search-skill
./run.sh --task task-002-token-usage-analytics

# 指定模型（命令行优先于 .env）
./run.sh --provider openai --model gpt-4o --key sk-xxx

# 强制重建基础镜像（依赖变化时）
./run.sh --rebuild-base
```

### 5. 查看结果

```bash
ls results/<run_id>/

# 关键文件:
#   run_config.json    — 运行配置（模型、nanobot版本等）
#   run_summary.json   — 评测结果（通过/失败、指标）
#   trajectory.jsonl   — 完整对话轨迹
#   final_state/       — 最终文件快照
#   turns.json         — 多轮对话摘要
#   docker_output.log  — 完整 Docker 日志
#   pytest_report.json — pytest 详细报告（代码修改类任务）
```

## 任务类型

### Type A: 普通任务（如 task-001）
- 创建 skill、写脚本等
- initial_state 包含 skills/ 和 memory/
- 验证：内置规则检查文件和功能

### Type B: 代码修改任务（如 task-002）
- 修改 nanobot/webchat 源码
- initial_state 包含 project_code/（特定 git 版本的源码，含 .git 历史）
- 验证：pytest 脚本检查代码修改结果
- task.yaml 使用 `initial_state_mapping` 控制文件放置

## 对比不同策略

```bash
# 对比不同 LLM
./run.sh --provider anthropic --model claude-sonnet-4-20250514 --run-id claude-sonnet
./run.sh --provider volcengine --model ep-xxx --base-url https://ark.cn-beijing.volces.com/api/v3 --run-id volcengine

# 对比不同 nanobot 版本
./run.sh --nanobot-src ~/code/nanobot-baseline --run-id baseline
./run.sh --nanobot-src ~/code/nanobot-improved --run-id improved

# 对比结果
diff results/baseline/run_summary.json results/improved/run_summary.json
```

## 故障排查

### 基础镜像构建失败
```bash
# 查看详细日志
docker build -t eval-bench-base:latest -f platform/Dockerfile.base . 2>&1

# 国内网络问题：设置 DOCKER_MIRROR 和 PIP_INDEX_URL
```

### Agent LLM 返回 404
```bash
# 常见原因：API Base URL 未设置
# 解决：确保 .env 中设置了 AGENT_API_BASE（volcengine 必填）
```

### Mock API 调用 404
```bash
# 常见原因：apiBase 路径不匹配
# runner.py 设置 mock apiBase 为 http://mock-api:18080/api/v3
# mock server 支持 /api/v3/responses, /v3/responses, /responses 三种路径
```
