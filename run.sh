#!/bin/bash
# nanobot Eval Bench — 一键运行评测
#
# 打包策略:
#   - 基础镜像 (eval-bench-base): 预装所有系统依赖 + Python 第三方库，构建一次复用
#   - Agent 镜像 (eval-bench-agent): 基于 base，COPY nanobot 源码 + runner.py
#   - nanobot 源码以源代码形式放入，不 pip install，方便测试不同版本
#
# 用法:
#   ./run.sh                                    # 使用默认 nanobot 源码
#   ./run.sh --nanobot-src /path/to/nanobot     # 指定 nanobot 源码路径
#   ./run.sh --model gpt-4o --provider openai   # 指定模型
#   ./run.sh --rebuild-base                     # 强制重建基础镜像
#
# 环境变量:
#   AGENT_API_KEY     (必须) 驱动 agent 的 LLM API Key
#   AGENT_PROVIDER    (可选) LLM Provider，默认 anthropic
#   AGENT_MODEL       (可选) 模型名，默认 claude-sonnet-4-20250514
#   AGENT_API_BASE    (可选) 自定义 API Base URL
#   TASK_ID           (可选) 任务 ID，默认 task-001-doubao-search-skill
#   RUN_ID            (可选) 运行 ID，默认时间戳

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ─── 加载 .env 文件（如果存在）─────────────────────────
if [ -f ".env" ]; then
    echo "📄 Loading .env file..."
    set -a
    source .env
    set +a
fi

# ─── 默认值 ────────────────────────────────────────────
NANOBOT_SRC=""
REBUILD_BASE=false

# ─── 解析命令行参数 ────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --provider)      export AGENT_PROVIDER="$2"; shift 2 ;;
        --model)         export AGENT_MODEL="$2"; shift 2 ;;
        --key)           export AGENT_API_KEY="$2"; shift 2 ;;
        --base-url)      export AGENT_API_BASE="$2"; shift 2 ;;
        --task)          export TASK_ID="$2"; shift 2 ;;
        --run-id)        export RUN_ID="$2"; shift 2 ;;
        --nanobot-src)   NANOBOT_SRC="$2"; shift 2 ;;
        --rebuild-base)  REBUILD_BASE=true; shift ;;
        --help|-h)
            echo "Usage: ./run.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --provider NAME       LLM provider (default: anthropic)"
            echo "  --model NAME          Model name (default: claude-sonnet-4-20250514)"
            echo "  --key KEY             API key (or set AGENT_API_KEY env var)"
            echo "  --base-url URL        Custom API base URL"
            echo "  --task ID             Task ID (default: task-001-doubao-search-skill)"
            echo "  --run-id ID           Run ID for results directory (default: timestamp)"
            echo "  --nanobot-src PATH    Path to nanobot source repo (default: bundled)"
            echo "  --rebuild-base        Force rebuild base image (deps changed)"
            echo ""
            echo "Examples:"
            echo "  # 测试不同 LLM"
            echo "  ./run.sh --key sk-xxx --provider openai --model gpt-4o"
            echo ""
            echo "  # 测试不同版本的 nanobot 代码"
            echo "  ./run.sh --key sk-xxx --nanobot-src ~/code/nanobot-experimental"
            echo ""
            echo "  # 测试特定分支"
            echo "  git -C nanobot-src checkout feat/new-tool-strategy"
            echo "  ./run.sh --key sk-xxx"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ─── 检查必要条件 ──────────────────────────────────────
if [ -z "$AGENT_API_KEY" ]; then
    echo "❌ 请设置 AGENT_API_KEY 环境变量"
    echo ""
    echo "  export AGENT_API_KEY=sk-your-api-key"
    echo "  ./run.sh"
    echo ""
    echo "  或: ./run.sh --key sk-your-api-key"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker Desktop"
    exit 1
fi

# ─── 设置默认值 ────────────────────────────────────────
export TASK_ID="${TASK_ID:-task-001-doubao-search-skill}"
export RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
export AGENT_PROVIDER="${AGENT_PROVIDER:-anthropic}"
export AGENT_MODEL="${AGENT_MODEL:-claude-sonnet-4-20250514}"

# ─── 准备 nanobot 源码 ────────────────────────────────
# nanobot-src/ 目录是 agent 镜像构建时 COPY 的源码
# 每次运行都同步最新源码，确保测试的是指定版本
NANOBOT_SRC_DIR="$SCRIPT_DIR/nanobot-src"

if [ -n "$NANOBOT_SRC" ]; then
    # 用户指定了源码路径
    if [ ! -d "$NANOBOT_SRC/nanobot" ]; then
        echo "❌ 指定的路径不是有效的 nanobot 源码目录: $NANOBOT_SRC"
        echo "   应包含 nanobot/ 子目录（Python 包）"
        exit 1
    fi
    echo "📦 使用指定 nanobot 源码: $NANOBOT_SRC"
    # 同步源码（只保留核心 Python 包 + pyproject.toml）
    python3 -c "
import shutil, os
src = '$NANOBOT_SRC'
dst = '$NANOBOT_SRC_DIR'
if os.path.exists(dst):
    shutil.rmtree(dst)
ignore = shutil.ignore_patterns(
    '.git', '__pycache__', '*.pyc', '.ruff_cache', '*.egg-info',
    '.pytest_cache', 'venv*', 'tests', 'docs', '*.png', 'bridge',
    'case', 'docker-compose.yml', 'Dockerfile'
)
shutil.copytree(src, dst, ignore=ignore)
total = sum(os.path.getsize(os.path.join(dp, fn)) for dp, dn, fns in os.walk(dst) for fn in fns)
print(f'  Synced {total/1024:.0f} KB')
"
elif [ -d "$NANOBOT_SRC_DIR/nanobot" ]; then
    echo "📦 使用已有 nanobot 源码: $NANOBOT_SRC_DIR"
else
    echo "❌ 未找到 nanobot 源码"
    echo "   请使用 --nanobot-src 指定路径，或将源码放在 $NANOBOT_SRC_DIR/"
    echo ""
    echo "   示例: ./run.sh --nanobot-src ~/Documents/code/workspace/nanobot"
    exit 1
fi

# 显示 nanobot 版本信息
NANOBOT_VERSION=$(python3 -c "
import sys; sys.path.insert(0, '$NANOBOT_SRC_DIR')
try:
    import nanobot; print(nanobot.__version__)
except: print('unknown')
" 2>/dev/null || echo "unknown")

NANOBOT_GIT_INFO=""
if [ -d "$NANOBOT_SRC/.git" ] && [ -n "$NANOBOT_SRC" ]; then
    NANOBOT_GIT_INFO=" ($(git -C "$NANOBOT_SRC" rev-parse --short HEAD 2>/dev/null || echo '?') @ $(git -C "$NANOBOT_SRC" branch --show-current 2>/dev/null || echo '?'))"
fi

# ─── 创建结果目录 ──────────────────────────────────────
RESULTS_PATH="results/${RUN_ID}"
mkdir -p "$RESULTS_PATH"

echo "╔══════════════════════════════════════════════════════╗"
echo "║          nanobot Eval Bench — Task Runner            ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Task:       ${TASK_ID}"
echo "║  Run ID:     ${RUN_ID}"
echo "║  Provider:   ${AGENT_PROVIDER}"
echo "║  Model:      ${AGENT_MODEL}"
echo "║  nanobot:    v${NANOBOT_VERSION}${NANOBOT_GIT_INFO}"
echo "║  Results:    ${RESULTS_PATH}/"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# 保存运行配置到结果目录
cat > "${RESULTS_PATH}/run_config.json" << EOF
{
  "task_id": "${TASK_ID}",
  "run_id": "${RUN_ID}",
  "agent_provider": "${AGENT_PROVIDER}",
  "agent_model": "${AGENT_MODEL}",
  "nanobot_version": "${NANOBOT_VERSION}",
  "nanobot_git": "${NANOBOT_GIT_INFO}",
  "nanobot_src": "${NANOBOT_SRC:-bundled}",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

# ─── Step 1: 构建基础镜像（仅首次或 --rebuild-base）──
BASE_IMAGE="eval-bench-base:latest"
BASE_EXISTS=$(docker images -q "$BASE_IMAGE" 2>/dev/null)

if [ -z "$BASE_EXISTS" ] || [ "$REBUILD_BASE" = true ]; then
    echo "📦 Building base image (installs all dependencies, may take a few minutes)..."
    docker build -t "$BASE_IMAGE" \
        -f platform/Dockerfile.base \
        --build-arg REGISTRY_MIRROR="${DOCKER_MIRROR:-}" \
        --build-arg PIP_INDEX_URL="${PIP_INDEX_URL:-}" \
        . \
        2>&1 | tail -20
    echo "✅ Base image built: $BASE_IMAGE"
else
    echo "✅ Base image exists: $BASE_IMAGE (use --rebuild-base to force rebuild)"
fi
echo ""

# ─── Step 2: 构建 agent 镜像（每次都重建，因为源码可能变了）
echo "📦 Building agent image (copying nanobot source)..."
docker build -t eval-bench-agent:latest \
    -f platform/Dockerfile.agent \
    --build-arg REGISTRY_MIRROR="${DOCKER_MIRROR:-}" \
    . \
    2>&1 | tail -10
echo "✅ Agent image built"
echo ""

# ─── Step 3: 构建 mock 镜像 ───────────────────────────
echo "📦 Building mock image..."
docker build -t eval-bench-mock:latest \
    -f platform/Dockerfile.mock \
    --build-arg REGISTRY_MIRROR="${DOCKER_MIRROR:-}" \
    . \
    2>&1 | tail -5
echo "✅ Mock image built"
echo ""

# ─── Step 4: 运行评测 ─────────────────────────────────
echo "🚀 Starting evaluation..."
echo ""

docker compose -f platform/docker-compose.yaml up \
    --no-build \
    --abort-on-container-exit \
    --exit-code-from agent-runner \
    2>&1 | tee "${RESULTS_PATH}/docker_output.log"

EXIT_CODE=${PIPESTATUS[0]}

echo ""

# 清理容器
docker compose -f platform/docker-compose.yaml down --volumes 2>/dev/null

# ─── 显示结果 ──────────────────────────────────────────
if [ -f "${RESULTS_PATH}/run_summary.json" ]; then
    echo "📊 Results:"
    echo ""
    python3 -c "
import json
with open('${RESULTS_PATH}/run_summary.json') as f:
    r = json.load(f)
print(f\"  Task:       {r['task_id']} — {r['task_name']}\")
print(f\"  Result:     {'✅ PASS' if r['success'] else '❌ FAIL'}\")
print(f\"  Verified:   {r['verification']['passed']}/{r['verification']['total']}\")
m = r['metrics']
print(f\"  Tool calls: {m['tool_calls']}\")
print(f\"  LLM calls:  {m['llm_calls']}\")
print(f\"  Wall time:  {m['wall_time_seconds']}s\")
print()
print('  Verification details:')
for k, v in r['test_results'].items():
    s = '✅' if v['passed'] else '❌'
    print(f'    {s} {k[:70]}')
" 2>/dev/null || cat "${RESULTS_PATH}/run_summary.json"
fi

echo ""
echo "📁 Full results in: ${RESULTS_PATH}/"
echo "   - run_config.json    (运行配置)"
echo "   - run_summary.json   (评测结果)"
echo "   - trajectory.jsonl   (完整对话轨迹)"
echo "   - final_state/       (最终文件快照)"
echo "   - turns.json         (多轮对话摘要)"
echo "   - docker_output.log  (完整日志)"

exit $EXIT_CODE
