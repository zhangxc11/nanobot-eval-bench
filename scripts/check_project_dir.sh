#!/bin/bash
# check_project_dir.sh — 质检脚本：检查所有 code_modification 测例的 project_dir 字段
#
# 规则：
# 1. 所有 type: code_modification 的测例必须有 project_dir 字段
# 2. project_dir 值必须以 .nanobot/workspace/ 开头
# 3. project_dir 值必须与 initial_state_mapping 中某个 value 一致或是其子路径
#
# 用法: bash scripts/check_project_dir.sh [tasks_dir]
# 默认: tasks_dir = ../eval-bench-data/tasks

set -euo pipefail

TASKS_DIR="${1:-$(dirname "$0")/../../eval-bench-data/tasks}"

if [ ! -d "$TASKS_DIR" ]; then
    echo "ERROR: Tasks directory not found: $TASKS_DIR"
    exit 1
fi

PASS=0
FAIL=0
WARN=0

for d in "$TASKS_DIR"/task-*/; do
    yaml="$d/task.yaml"
    [ -f "$yaml" ] || continue

    task_name=$(basename "$d")
    type=$(grep "^type:" "$yaml" 2>/dev/null | head -1 | awk '{print $2}' | tr -d '"' || true)

    # 只检查 code_modification 类型
    [ "$type" = "code_modification" ] || continue

    # 检查 1: project_dir 字段是否存在
    pd=$(grep "^project_dir:" "$yaml" 2>/dev/null | head -1 | sed 's/project_dir: *//; s/"//g; s/ *$//' || true)
    if [ -z "$pd" ]; then
        echo "❌ MISSING project_dir: $task_name"
        FAIL=$((FAIL + 1))
        continue
    fi

    # 检查 2: 是否以 .nanobot/workspace/ 开头
    if ! echo "$pd" | grep -q "^\.nanobot/workspace/"; then
        echo "❌ BAD PREFIX: $task_name → project_dir='$pd' (must start with .nanobot/workspace/)"
        FAIL=$((FAIL + 1))
        continue
    fi

    # 检查 3: 是否与 mapping value 一致
    # 提取所有 mapping values
    mapping_values=$(grep -A50 "^initial_state_mapping:" "$yaml" 2>/dev/null | \
        grep "^\s\+\"\?\w" | \
        sed 's/.*: *//; s/"//g; s/ *$//' | \
        grep "^\.nanobot/workspace/" || true)

    if [ -n "$mapping_values" ]; then
        found_match=false
        while IFS= read -r mv; do
            # 去掉尾部斜杠比较
            mv_clean=$(echo "$mv" | sed 's|/$||')
            pd_clean=$(echo "$pd" | sed 's|/$||')
            if [ "$pd_clean" = "$mv_clean" ] || echo "$pd_clean" | grep -q "^$mv_clean/"; then
                found_match=true
                break
            fi
        done <<< "$mapping_values"

        if ! $found_match; then
            echo "⚠️  MISMATCH: $task_name → project_dir='$pd' not in mapping values"
            WARN=$((WARN + 1))
            PASS=$((PASS + 1))  # 不算硬失败，只是 warning
            continue
        fi
    fi

    echo "✅ $task_name → $pd"
    PASS=$((PASS + 1))
done

echo ""
echo "=== Summary ==="
echo "PASS: $PASS"
echo "FAIL: $FAIL"
echo "WARN: $WARN"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
