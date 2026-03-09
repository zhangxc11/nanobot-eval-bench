#!/bin/bash
# 打包 eval-bench 框架为 tar.gz（不含本地数据）
#
# 分发包内容:
#   - 评测框架 (platform/, run.sh, docs/)
#   - 配套 Skill (skills/)
#   - 不含: nanobot-src, tasks, results, CASE_REGISTRY.md
#
# 用法:
#   ./pack.sh                    # 打包到 /tmp/eval-bench.tar.gz
#   ./pack.sh /path/to/output    # 指定输出路径

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="${1:-/tmp/eval-bench.tar.gz}"

echo "📦 Packing eval-bench framework..."
echo "   Source: $SCRIPT_DIR"
echo "   Output: $OUTPUT"

cd "$(dirname "$SCRIPT_DIR")"

tar czf "$OUTPUT" \
    --exclude='eval-bench/.git' \
    --exclude='eval-bench/.nanobot-src-staging' \
    --exclude='eval-bench/nanobot-src' \
    --exclude='eval-bench/results' \
    --exclude='eval-bench/tasks' \
    --exclude='eval-bench/CASE_REGISTRY.md' \
    --exclude='eval-bench/.env' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    eval-bench/

echo ""
echo "✅ Packed successfully!"
echo "   Size: $(du -h "$OUTPUT" | cut -f1)"
echo ""
echo "📋 Contents:"
tar tzf "$OUTPUT" | head -40
echo "   ... ($(tar tzf "$OUTPUT" | wc -l | tr -d ' ') entries total)"
echo ""
echo "📖 Next steps:"
echo "   1. Copy to target machine"
echo "   2. tar xzf $(basename "$OUTPUT")"
echo "   3. cd eval-bench"
echo "   4. cp .env.example .env && vim .env"
echo "   5. mkdir -p ../eval-bench-data/tasks"
echo "   6. # Copy or create tasks in ../eval-bench-data/tasks/"
echo "   7. ./run.sh --nanobot-src /path/to/nanobot --task task-001"
echo "   8. ./batch_run.sh --all  # or: ./batch_run.sh --all --dry-run"
