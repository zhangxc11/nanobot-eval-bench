#!/bin/bash
# 打包 eval-bench 为 tar.gz
#
# 注意：
# - 排除 eval-bench 自身的 .git 记录
# - 保留 task-002 project_code 中的 .git（agent 需要 git 历史）
# - 排除 nanobot-src/（运行时通过 --nanobot-src 指定或 git clone）
# - 排除 results/（运行产出）
#
# 用法:
#   ./pack.sh                    # 打包到 /tmp/eval-bench.tar.gz
#   ./pack.sh /path/to/output    # 指定输出路径

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="${1:-/tmp/eval-bench.tar.gz}"

echo "📦 Packing eval-bench..."
echo "   Source: $SCRIPT_DIR"
echo "   Output: $OUTPUT"

cd "$(dirname "$SCRIPT_DIR")"

tar czf "$OUTPUT" \
    --exclude='eval-bench/.git' \
    --exclude='eval-bench/nanobot-src' \
    --exclude='eval-bench/results' \
    --exclude='eval-bench/.env' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    eval-bench/

echo ""
echo "✅ Packed successfully!"
echo "   Size: $(du -h "$OUTPUT" | cut -f1)"
echo ""
echo "📋 Contents:"
tar tzf "$OUTPUT" | head -30
echo "   ... ($(tar tzf "$OUTPUT" | wc -l | tr -d ' ') entries total)"
echo ""
echo "🔍 Verify task-002 git history is included:"
tar tzf "$OUTPUT" | grep "project_code/.git/" | head -5
echo ""
echo "📖 Next steps:"
echo "   1. Copy to target machine"
echo "   2. tar xzf $(basename "$OUTPUT")"
echo "   3. cd eval-bench"
echo "   4. cp .env.example .env && vim .env"
echo "   5. ./run.sh --nanobot-src /path/to/nanobot"
