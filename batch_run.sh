#!/bin/bash
# nanobot Eval Bench — 批量运行多个测例
#
# 用法:
#   ./batch_run.sh task-001 task-002 task-003        # 指定测例 ID 列表
#   ./batch_run.sh --glob "task-0*"                  # 使用 glob 模式匹配
#   ./batch_run.sh --all                             # 运行所有测例
#   ./batch_run.sh --dry-run task-001 task-002       # dry-run 模式（跳过 agent）
#   ./batch_run.sh --results-dir ./my-results task-001  # 指定结果输出目录
#
# 选项:
#   --dry-run           传递 --dry-run 给 runner.py（跳过 agent 执行）
#   --results-dir DIR   结果根目录（默认: eval-bench-data/results/batch_<timestamp>）
#   --glob PATTERN      匹配测例 ID 的 glob 模式（可多次使用）
#   --all               运行所有可找到的测例
#   --continue          跳过已有结果的测例（断点续跑）
#   --help              显示帮助
#
# 环境变量:
#   与 run.sh 相同（AGENT_API_KEY, AGENT_PROVIDER, AGENT_MODEL 等）
#   DRY_RUN=1           等效于 --dry-run

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ─── 加载 .env 文件 ───────────────────────────────────
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# ─── 默认值 ────────────────────────────────────────────
DRY_RUN="${DRY_RUN:-}"
RESULTS_ROOT=""
TASK_IDS=()
GLOB_PATTERNS=()
RUN_ALL=false
CONTINUE_MODE=false
BATCH_ID="batch_$(date +%Y%m%d_%H%M%S)"

# ─── 解析命令行参数 ────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --results-dir)
            RESULTS_ROOT="$2"
            shift 2
            ;;
        --glob)
            GLOB_PATTERNS+=("$2")
            shift 2
            ;;
        --all)
            RUN_ALL=true
            shift
            ;;
        --continue)
            CONTINUE_MODE=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./batch_run.sh [OPTIONS] [TASK_ID ...]"
            echo ""
            echo "Options:"
            echo "  --dry-run           Skip agent execution, only verify task setup"
            echo "  --results-dir DIR   Results root directory"
            echo "  --glob PATTERN      Glob pattern to match task IDs (repeatable)"
            echo "  --all               Run all available tasks"
            echo "  --continue          Skip tasks that already have results"
            echo ""
            echo "Examples:"
            echo "  ./batch_run.sh task-001 task-002"
            echo "  ./batch_run.sh --glob 'task-0*' --dry-run"
            echo "  ./batch_run.sh --all --results-dir ./results"
            echo "  ./batch_run.sh --continue --all"
            exit 0
            ;;
        -*)
            echo "❌ Unknown option: $1"
            echo "   Use --help for usage information"
            exit 1
            ;;
        *)
            TASK_IDS+=("$1")
            shift
            ;;
    esac
done

# ─── 检查必要条件 ──────────────────────────────────────
if [ -z "$DRY_RUN" ] && [ -z "$AGENT_API_KEY" ]; then
    echo "❌ AGENT_API_KEY not set (required unless --dry-run)"
    echo "   export AGENT_API_KEY=sk-your-key"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed"
    exit 1
fi

# ─── 发现测例目录 ──────────────────────────────────────
DATA_DIR="${EVAL_BENCH_DATA:-$(dirname "$SCRIPT_DIR")/eval-bench-data}"
TASKS_SEARCH_DIRS=("$DATA_DIR/tasks" "$SCRIPT_DIR/tasks")

find_task_dir() {
    local task_id="$1"
    for search_dir in "${TASKS_SEARCH_DIRS[@]}"; do
        if [ -d "$search_dir/$task_id" ] && [ -f "$search_dir/$task_id/task.yaml" ]; then
            echo "$search_dir/$task_id"
            return 0
        fi
    done
    return 1
}

list_all_tasks() {
    local tasks=()
    for search_dir in "${TASKS_SEARCH_DIRS[@]}"; do
        if [ -d "$search_dir" ]; then
            for d in "$search_dir"/*/; do
                if [ -f "${d}task.yaml" ]; then
                    tasks+=("$(basename "$d")")
                fi
            done
        fi
    done
    # Deduplicate and sort
    printf '%s\n' "${tasks[@]}" | sort -u
}

# ─── 解析测例列表 ──────────────────────────────────────
RESOLVED_TASKS=()

if [ "$RUN_ALL" = true ]; then
    while IFS= read -r t; do
        RESOLVED_TASKS+=("$t")
    done < <(list_all_tasks)
fi

# Add explicitly listed task IDs
for t in "${TASK_IDS[@]}"; do
    RESOLVED_TASKS+=("$t")
done

# Expand glob patterns
for pattern in "${GLOB_PATTERNS[@]}"; do
    while IFS= read -r t; do
        # Check if task matches glob
        if [[ "$t" == $pattern ]]; then
            RESOLVED_TASKS+=("$t")
        fi
    done < <(list_all_tasks)
done

# Deduplicate
RESOLVED_TASKS=($(printf '%s\n' "${RESOLVED_TASKS[@]}" | sort -u))

if [ ${#RESOLVED_TASKS[@]} -eq 0 ]; then
    echo "❌ No tasks specified"
    echo ""
    echo "Available tasks:"
    list_all_tasks | sed 's/^/  /'
    echo ""
    echo "Usage: ./batch_run.sh [--all | --glob PATTERN | TASK_ID ...]"
    exit 1
fi

# ─── 设置结果目录 ──────────────────────────────────────
if [ -z "$RESULTS_ROOT" ]; then
    RESULTS_ROOT="${DATA_DIR}/results/${BATCH_ID}"
fi
mkdir -p "$RESULTS_ROOT"

# ─── 显示运行计划 ──────────────────────────────────────
echo "╔══════════════════════════════════════════════════════╗"
echo "║        nanobot Eval Bench — Batch Runner             ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Batch ID:   ${BATCH_ID}"
echo "║  Tasks:      ${#RESOLVED_TASKS[@]}"
echo "║  Dry-run:    ${DRY_RUN:-no}"
echo "║  Continue:   ${CONTINUE_MODE}"
echo "║  Results:    ${RESULTS_ROOT}/"
echo "║  Provider:   ${AGENT_PROVIDER:-anthropic}"
echo "║  Model:      ${AGENT_MODEL:-claude-sonnet-4-20250514}"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Tasks to run:"
for t in "${RESOLVED_TASKS[@]}"; do
    echo "  - $t"
done
echo ""

# ─── 逐个运行测例 ─────────────────────────────────────
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
ERROR_COUNT=0
declare -a SUMMARY_LINES=()

TOTAL=${#RESOLVED_TASKS[@]}
CURRENT=0

for TASK_ID in "${RESOLVED_TASKS[@]}"; do
    CURRENT=$((CURRENT + 1))
    TASK_RESULTS_DIR="${RESULTS_ROOT}/${TASK_ID}"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  [${CURRENT}/${TOTAL}] ${TASK_ID}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Skip if continue mode and results exist
    if [ "$CONTINUE_MODE" = true ] && [ -f "${TASK_RESULTS_DIR}/run_summary.json" ]; then
        echo "  ⏭️  Skipping (results exist)"
        SKIP_COUNT=$((SKIP_COUNT + 1))

        # Read existing result for summary
        EXISTING_RESULT=$(python3 -c "
import json
with open('${TASK_RESULTS_DIR}/run_summary.json') as f:
    r = json.load(f)
status = 'PASS' if r['success'] else 'FAIL'
v = r['verification']
print(f\"{status}|{v['passed']}/{v['total']}\")
" 2>/dev/null || echo "SKIP|?/?")
        IFS='|' read -r STATUS VERIFY <<< "$EXISTING_RESULT"
        SUMMARY_LINES+=("${TASK_ID}|${STATUS} (cached)|${VERIFY}")
        if [ "$STATUS" = "PASS" ]; then
            PASS_COUNT=$((PASS_COUNT + 1))
        else
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
        echo ""
        continue
    fi

    # Find task directory
    TASK_DIR_HOST=$(find_task_dir "$TASK_ID")
    if [ -z "$TASK_DIR_HOST" ]; then
        echo "  ❌ Task directory not found: $TASK_ID"
        ERROR_COUNT=$((ERROR_COUNT + 1))
        SUMMARY_LINES+=("${TASK_ID}|ERROR|task not found")
        echo ""
        continue
    fi

    # Create results directory
    mkdir -p "$TASK_RESULTS_DIR"

    # Build run.sh arguments
    RUN_ARGS=(
        --task-dir "$TASK_DIR_HOST"
        --run-id "${BATCH_ID}/${TASK_ID}"
    )

    # Construct docker compose command directly (more control than run.sh)
    export TASK_DIR_HOST
    export RESULTS_PATH="$TASK_RESULTS_DIR"
    RUN_ID="${BATCH_ID}_${TASK_ID}"

    # Build DRY_RUN environment for docker compose
    DRY_RUN_ENV=""
    if [ -n "$DRY_RUN" ]; then
        DRY_RUN_ENV="-e DRY_RUN=1"
    fi

    # Ensure images are built (only on first task)
    if [ "$CURRENT" -eq 1 ]; then
        echo "  📦 Ensuring images are built..."

        # Sync nanobot source (same logic as run.sh)
        NANOBOT_SRC_DIR="$SCRIPT_DIR/.nanobot-src-staging"
        DEFAULT_NANOBOT_SRC="${NANOBOT_SRC_PATH:-$(dirname "$SCRIPT_DIR")/../Documents/code/workspace/nanobot}"

        if [ -d "$DEFAULT_NANOBOT_SRC/nanobot" ]; then
            RESOLVED_SRC="$DEFAULT_NANOBOT_SRC"
        elif [ -d "$NANOBOT_SRC_DIR/nanobot" ]; then
            RESOLVED_SRC=""  # Already staged
        else
            echo "  ❌ nanobot source not found. Set NANOBOT_SRC_PATH or run ./run.sh first"
            exit 1
        fi

        if [ -n "$RESOLVED_SRC" ]; then
            python3 -c "
import shutil, os
src = '$RESOLVED_SRC'
dst = '$NANOBOT_SRC_DIR'
if os.path.exists(dst):
    shutil.rmtree(dst)
ignore = shutil.ignore_patterns(
    '.git', '__pycache__', '*.pyc', '.ruff_cache', '*.egg-info',
    '.pytest_cache', 'venv*', 'tests', 'docs', '*.png', 'bridge',
    'case', 'docker-compose.yml', 'Dockerfile'
)
shutil.copytree(src, dst, ignore=ignore)
print(f'  Synced nanobot source')
"
        fi

        # Build images if needed
        BASE_IMAGE="eval-bench-base:latest"
        if [ -z "$(docker images -q "$BASE_IMAGE" 2>/dev/null)" ]; then
            echo "  📦 Building base image..."
            docker build -t "$BASE_IMAGE" \
                -f platform/Dockerfile.base \
                --build-arg REGISTRY_MIRROR="${DOCKER_MIRROR:-}" \
                --build-arg PIP_INDEX_URL="${PIP_INDEX_URL:-}" \
                --build-arg APT_MIRROR="${APT_MIRROR:-}" \
                . 2>&1 | tail -5
        fi

        echo "  📦 Building agent image..."
        docker build -t eval-bench-agent:latest \
            -f platform/Dockerfile.agent \
            --build-arg REGISTRY_MIRROR="${DOCKER_MIRROR:-}" \
            . 2>&1 | tail -5

        echo "  📦 Building mock image..."
        docker build -t eval-bench-mock:latest \
            -f platform/Dockerfile.mock \
            --build-arg REGISTRY_MIRROR="${DOCKER_MIRROR:-}" \
            . 2>&1 | tail -5
        echo ""
    fi

    # Run docker compose
    echo "  🚀 Running ${TASK_ID}..."
    COMPOSE_PROJECT="eval-batch-${RUN_ID//\//-}"

    TASK_START=$(date +%s)

    # Run with DRY_RUN passed as environment variable
    set +e
    if [ -n "$DRY_RUN" ]; then
        docker compose -p "$COMPOSE_PROJECT" -f platform/docker-compose.yaml run \
            --rm \
            -e DRY_RUN=1 \
            agent-runner \
            python3 /eval/runner.py --dry-run \
            > "${TASK_RESULTS_DIR}/docker_output.log" 2>&1
    else
        docker compose -p "$COMPOSE_PROJECT" -f platform/docker-compose.yaml up \
            --no-build \
            --abort-on-container-exit \
            --exit-code-from agent-runner \
            > "${TASK_RESULTS_DIR}/docker_output.log" 2>&1
    fi
    TASK_EXIT=$?
    set -e

    TASK_END=$(date +%s)
    TASK_DURATION=$((TASK_END - TASK_START))

    # Cleanup containers
    docker compose -p "$COMPOSE_PROJECT" -f platform/docker-compose.yaml down --volumes 2>/dev/null || true

    # Parse results
    if [ -f "${TASK_RESULTS_DIR}/run_summary.json" ]; then
        RESULT_INFO=$(python3 -c "
import json
with open('${TASK_RESULTS_DIR}/run_summary.json') as f:
    r = json.load(f)
status = 'PASS' if r['success'] else 'FAIL'
v = r['verification']
print(f\"{status}|{v['passed']}/{v['total']}\")
" 2>/dev/null || echo "ERROR|?/?")
        IFS='|' read -r STATUS VERIFY <<< "$RESULT_INFO"

        if [ "$STATUS" = "PASS" ]; then
            echo "  ✅ PASS (${VERIFY}) — ${TASK_DURATION}s"
            PASS_COUNT=$((PASS_COUNT + 1))
        else
            echo "  ❌ FAIL (${VERIFY}) — ${TASK_DURATION}s"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
        SUMMARY_LINES+=("${TASK_ID}|${STATUS}|${VERIFY}|${TASK_DURATION}s")
    else
        echo "  ❌ ERROR — no run_summary.json (exit code: ${TASK_EXIT}) — ${TASK_DURATION}s"
        ERROR_COUNT=$((ERROR_COUNT + 1))
        SUMMARY_LINES+=("${TASK_ID}|ERROR|no summary|${TASK_DURATION}s")
    fi

    echo ""
done

# ─── 输出汇总表格 ─────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                  Batch Summary                       ║"
echo "╠══════════════════════════════════════════════════════╣"

# Print table header
printf "║  %-40s %-8s %-10s %-8s ║\n" "Task ID" "Status" "Verify" "Time"
echo "║  ──────────────────────────────────────── ──────── ────────── ──────── ║"

for line in "${SUMMARY_LINES[@]}"; do
    IFS='|' read -r TASK_ID STATUS VERIFY TIME <<< "$line"
    # Color status
    if [ "$STATUS" = "PASS" ] || [ "$STATUS" = "PASS (cached)" ]; then
        STATUS_DISPLAY="✅ PASS"
    elif [ "$STATUS" = "FAIL" ] || [ "$STATUS" = "FAIL (cached)" ]; then
        STATUS_DISPLAY="❌ FAIL"
    else
        STATUS_DISPLAY="⚠️  ERR"
    fi
    printf "║  %-40s %-8s %-10s %-8s ║\n" "$TASK_ID" "$STATUS_DISPLAY" "$VERIFY" "$TIME"
done

echo "╠══════════════════════════════════════════════════════╣"
TOTAL_RUN=$((PASS_COUNT + FAIL_COUNT + ERROR_COUNT + SKIP_COUNT))
echo "║  Total: ${TOTAL_RUN}  ✅ Pass: ${PASS_COUNT}  ❌ Fail: ${FAIL_COUNT}  ⚠️  Error: ${ERROR_COUNT}  ⏭️  Skip: ${SKIP_COUNT}"
echo "║  Results: ${RESULTS_ROOT}/"
echo "╚══════════════════════════════════════════════════════╝"

# ─── 保存汇总 JSON ────────────────────────────────────
python3 -c "
import json, os, glob

results_root = '${RESULTS_ROOT}'
summaries = []
for task_dir in sorted(glob.glob(os.path.join(results_root, '*/run_summary.json'))):
    try:
        with open(task_dir) as f:
            summaries.append(json.load(f))
    except:
        pass

batch_summary = {
    'batch_id': '${BATCH_ID}',
    'total': ${TOTAL_RUN},
    'passed': ${PASS_COUNT},
    'failed': ${FAIL_COUNT},
    'errors': ${ERROR_COUNT},
    'skipped': ${SKIP_COUNT},
    'dry_run': bool('${DRY_RUN}'),
    'tasks': summaries,
}

with open(os.path.join(results_root, 'batch_summary.json'), 'w') as f:
    json.dump(batch_summary, f, indent=2, ensure_ascii=False)
print(f'Batch summary saved to {results_root}/batch_summary.json')
"

# Exit with failure if any task failed
if [ $FAIL_COUNT -gt 0 ] || [ $ERROR_COUNT -gt 0 ]; then
    exit 1
fi
exit 0
