#!/usr/bin/env python3
"""eval-session-scanner — Session 扫描脚本

扫描指定时间范围内的 nanobot session JSONL 文件，
提取每个 session 的摘要信息，供后续分析和测例提炼使用。

输出格式：结构化 JSON（每个 session 一条记录），包含：
- session 文件名、时间范围、消息统计
- 用户消息摘要（前 N 条）
- 工具调用统计
- 任务主题推断

使用方式：
  python3 scan_sessions.py --sessions-dir ~/.nanobot/workspace/sessions --since "2026-03-02T15:55:00"
  python3 scan_sessions.py --sessions-dir ~/.nanobot/workspace/sessions --since-last-batch --registry CASE_REGISTRY.md
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse ISO timestamp string to datetime (timezone-naive)."""
    if not ts_str:
        return None
    try:
        # Strip timezone info for comparison
        clean = ts_str.split("+")[0].split("Z")[0].split(".")[0]
        return datetime.fromisoformat(clean)
    except (ValueError, TypeError):
        return None


def extract_text_content(content) -> str:
    """Extract text from message content (string or list of content blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "image_url":
                    parts.append("[image]")
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(parts)
    return str(content) if content else ""


def scan_session(filepath: Path, since: datetime, until: datetime) -> Optional[dict]:
    """Scan a single session JSONL file and extract summary.

    Returns None if the session has no messages in the time range.
    """
    messages = []
    with open(filepath, errors="replace") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                messages.append(msg)
            except json.JSONDecodeError:
                continue

    if not messages:
        return None

    # Collect user messages and their timestamps
    user_messages = []
    assistant_messages = []
    tool_calls_total = 0
    tool_names = {}
    first_ts = None
    last_ts = None
    has_messages_in_range = False

    for msg in messages:
        ts = parse_timestamp(msg.get("timestamp", ""))
        if ts:
            if first_ts is None or ts < first_ts:
                first_ts = ts
            if last_ts is None or ts > last_ts:
                last_ts = ts

        role = msg.get("role", "")

        if role == "user":
            text = extract_text_content(msg.get("content", ""))
            if ts and ts >= since and ts <= until:
                has_messages_in_range = True
            user_messages.append({
                "timestamp": ts.isoformat() if ts else None,
                "text": text[:300],  # Truncate for summary
                "in_range": ts is not None and ts >= since and ts <= until,
            })

        elif role == "assistant":
            assistant_messages.append(msg)
            tcs = msg.get("tool_calls", [])
            tool_calls_total += len(tcs)
            for tc in tcs:
                fn = tc.get("function", {}).get("name", "unknown")
                tool_names[fn] = tool_names.get(fn, 0) + 1

    # Filter: must have user messages in range
    if not has_messages_in_range:
        return None

    # Filter: must have at least some substance
    user_in_range = [m for m in user_messages if m["in_range"]]
    if not user_in_range:
        return None

    # Determine session channel/type from filename
    filename = filepath.stem
    channel = "unknown"
    if filename.startswith("webchat_"):
        channel = "webchat"
    elif filename.startswith("feishu.lab"):
        channel = "feishu.lab"
    elif filename.startswith("feishu.ST"):
        channel = "feishu.ST"
    elif filename.startswith("feishu_"):
        channel = "feishu.personal"
    elif filename.startswith("cli"):
        channel = "cli"

    # Build summary
    return {
        "session_file": filepath.name,
        "channel": channel,
        "time_range": {
            "first": first_ts.isoformat() if first_ts else None,
            "last": last_ts.isoformat() if last_ts else None,
        },
        "stats": {
            "total_user_messages": len(user_messages),
            "user_messages_in_range": len(user_in_range),
            "total_assistant_messages": len(assistant_messages),
            "total_tool_calls": tool_calls_total,
            "tool_usage": dict(sorted(tool_names.items(), key=lambda x: -x[1])[:10]),
        },
        "user_messages_in_range": [
            {"timestamp": m["timestamp"], "text": m["text"][:200]}
            for m in user_in_range[:15]  # At most 15 messages
        ],
    }


def parse_last_batch_time(registry_path: Path) -> Optional[datetime]:
    """Parse the end time of the last Batch from CASE_REGISTRY.md."""
    if not registry_path.exists():
        return None

    content = registry_path.read_text()

    # Look for "## Batch N: YYYY-MM-DD HH:MM ~ YYYY-MM-DD HH:MM"
    pattern = r"## Batch \d+:.*?~\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})"
    matches = re.findall(pattern, content)
    if not matches:
        return None

    # Take the last match (most recent batch)
    last_time_str = matches[-1].strip()
    try:
        return datetime.strptime(last_time_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser(description="Scan nanobot sessions for eval case candidates")
    parser.add_argument("--sessions-dir", required=True, help="Path to sessions directory")
    parser.add_argument("--since", help="Start time (ISO format)")
    parser.add_argument("--until", help="End time (ISO format, default: now)")
    parser.add_argument("--since-last-batch", action="store_true",
                        help="Start from last batch end time in registry")
    parser.add_argument("--registry", help="Path to CASE_REGISTRY.md")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument("--min-user-messages", type=int, default=1,
                        help="Minimum user messages to include (default: 1)")
    parser.add_argument("--format", choices=["json", "markdown"], default="json",
                        help="Output format (default: json)")

    args = parser.parse_args()

    sessions_dir = Path(args.sessions_dir)
    if not sessions_dir.exists():
        print(f"Error: sessions directory not found: {sessions_dir}", file=sys.stderr)
        sys.exit(1)

    # Determine time range
    if args.since_last_batch:
        if not args.registry:
            print("Error: --since-last-batch requires --registry", file=sys.stderr)
            sys.exit(1)
        since = parse_last_batch_time(Path(args.registry))
        if since is None:
            print("Error: could not parse last batch time from registry", file=sys.stderr)
            sys.exit(1)
        print(f"Scanning from last batch end time: {since.isoformat()}", file=sys.stderr)
    elif args.since:
        since = parse_timestamp(args.since)
        if since is None:
            print(f"Error: invalid --since format: {args.since}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: must specify --since or --since-last-batch", file=sys.stderr)
        sys.exit(1)

    until = parse_timestamp(args.until) if args.until else datetime.now()

    # Scan all session files
    results = []
    session_files = sorted(sessions_dir.glob("*.jsonl"))
    print(f"Scanning {len(session_files)} session files...", file=sys.stderr)

    for f in session_files:
        summary = scan_session(f, since, until)
        if summary and summary["stats"]["user_messages_in_range"] >= args.min_user_messages:
            results.append(summary)

    results.sort(key=lambda x: x["time_range"]["first"] or "")

    print(f"Found {len(results)} sessions with activity in range", file=sys.stderr)

    # Output
    if args.format == "json":
        output = json.dumps(results, indent=2, ensure_ascii=False)
    else:
        output = format_markdown(results, since, until)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Output written to: {args.output}", file=sys.stderr)
    else:
        print(output)


def format_markdown(results: list, since: datetime, until: datetime) -> str:
    """Format scan results as Markdown for review."""
    lines = [
        f"# Session 扫描结果",
        f"",
        f"扫描范围: {since.strftime('%Y-%m-%d %H:%M')} ~ {until.strftime('%Y-%m-%d %H:%M')}",
        f"命中 session 数: {len(results)}",
        f"",
        f"---",
        f"",
    ]

    for i, r in enumerate(results, 1):
        lines.append(f"## {i}. {r['session_file']}")
        lines.append(f"")
        lines.append(f"- **通道**: {r['channel']}")
        lines.append(f"- **时间**: {r['time_range']['first']} ~ {r['time_range']['last']}")
        lines.append(f"- **用户消息**: {r['stats']['user_messages_in_range']} 条"
                      f"（总 {r['stats']['total_user_messages']}）")
        lines.append(f"- **工具调用**: {r['stats']['total_tool_calls']} 次")

        if r["stats"]["tool_usage"]:
            top_tools = ", ".join(f"{k}({v})" for k, v in list(r["stats"]["tool_usage"].items())[:5])
            lines.append(f"- **常用工具**: {top_tools}")

        lines.append(f"")
        lines.append(f"### 用户消息摘要")
        lines.append(f"")
        for msg in r["user_messages_in_range"]:
            ts = msg["timestamp"][:16] if msg["timestamp"] else "?"
            text = msg["text"][:120].replace("\n", " ").strip()
            lines.append(f"- `[{ts}]` {text}")
        lines.append(f"")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
