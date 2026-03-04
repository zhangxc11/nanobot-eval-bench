#!/usr/bin/env python3
"""从 git 历史中提取特定版本的 nanobot 源码，用于构造 initial_state。

用法:
  python3 extract_git_snapshot.py \\
    --repo ~/Documents/code/workspace/nanobot \\
    --commit abc1234 \\
    --output tasks/task-002-xxx/initial_state/project_code \\
    --include nanobot/ pyproject.toml \\
    --exclude __pycache__ .git venv tests

说明:
  对于代码修改类评测任务（如 B8/B9），需要从 git 历史中截取
  "功能实现之前"的代码版本作为 initial_state，让 agent 在此基础上
  重新实现该功能。

  例如 B9 (Token 用量统计)：
  - 找到 analytics.py 首次提交之前的 commit
  - 提取那个版本的 nanobot 源码
  - 作为 initial_state/project_code
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def extract_snapshot(
    repo_path: str,
    commit: str,
    output_dir: str,
    include_paths: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
):
    """从 git 历史中提取特定 commit 的文件快照"""
    repo = Path(repo_path).resolve()
    output = Path(output_dir).resolve()

    if not (repo / ".git").exists():
        print(f"❌ Not a git repo: {repo}", file=sys.stderr)
        sys.exit(1)

    # 验证 commit 存在
    result = subprocess.run(
        ["git", "rev-parse", "--verify", commit],
        capture_output=True, text=True, cwd=str(repo)
    )
    if result.returncode != 0:
        print(f"❌ Invalid commit: {commit}", file=sys.stderr)
        sys.exit(1)

    full_commit = result.stdout.strip()
    print(f"📦 Extracting snapshot from {full_commit[:8]}...")

    # 使用 git archive 提取文件
    with tempfile.TemporaryDirectory() as tmpdir:
        # git archive 提取到临时目录
        archive_cmd = ["git", "archive", "--format=tar", commit]
        if include_paths:
            archive_cmd.extend(include_paths)

        tar_cmd = ["tar", "-x", "-C", tmpdir]

        p1 = subprocess.Popen(
            archive_cmd,
            stdout=subprocess.PIPE,
            cwd=str(repo)
        )
        p2 = subprocess.Popen(
            tar_cmd,
            stdin=p1.stdout,
        )
        p1.stdout.close()
        p2.communicate()

        if p2.returncode != 0:
            print(f"❌ Failed to extract archive", file=sys.stderr)
            sys.exit(1)

        # 复制到输出目录（排除不需要的文件）
        exclude = set(exclude_patterns or [])
        exclude.update({"__pycache__", ".pyc", ".git", ".ruff_cache"})

        if output.exists():
            shutil.rmtree(output)
        output.mkdir(parents=True)

        def should_exclude(path: str) -> bool:
            parts = Path(path).parts
            return any(p in exclude or p.endswith(".pyc") for p in parts)

        count = 0
        for root, dirs, files in os.walk(tmpdir):
            # 过滤目录
            dirs[:] = [d for d in dirs if d not in exclude]

            for f in files:
                src = Path(root) / f
                rel = src.relative_to(tmpdir)
                if should_exclude(str(rel)):
                    continue
                dest = output / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                count += 1

    # 获取 commit 信息
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-1", commit],
        capture_output=True, text=True, cwd=str(repo)
    )
    commit_msg = log_result.stdout.strip()

    # 写入版本信息
    (output / ".git_snapshot_info").write_text(
        f"commit: {full_commit}\n"
        f"message: {commit_msg}\n"
        f"extracted_by: eval-bench extract_git_snapshot.py\n"
    )

    print(f"✅ Extracted {count} files to {output}")
    print(f"   Commit: {commit_msg}")

    # 显示目录结构概览
    top_dirs = sorted(set(p.parts[0] for p in output.rglob("*") if p.is_file() and p.parts[0] != ".git_snapshot_info"))
    print(f"   Top-level: {', '.join(top_dirs[:10])}")


def find_commit_before_feature(repo_path: str, feature_file: str) -> str:
    """找到某个文件首次出现之前的 commit

    用于确定代码修改类任务的"起始版本"。
    例如：找到 analytics.py 首次提交之前的 commit。
    """
    repo = Path(repo_path).resolve()

    # 找到文件首次出现的 commit
    result = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", feature_file],
        capture_output=True, text=True, cwd=str(repo)
    )
    if not result.stdout.strip():
        print(f"❌ File never existed in history: {feature_file}", file=sys.stderr)
        sys.exit(1)

    first_commit = result.stdout.strip().split("\n")[-1]  # 最早的 commit

    # 取前一个 commit
    result = subprocess.run(
        ["git", "rev-parse", f"{first_commit}~1"],
        capture_output=True, text=True, cwd=str(repo)
    )
    if result.returncode != 0:
        print(f"❌ Cannot find parent of {first_commit[:8]}", file=sys.stderr)
        sys.exit(1)

    before_commit = result.stdout.strip()

    # 显示信息
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-1", before_commit],
        capture_output=True, text=True, cwd=str(repo)
    )
    print(f"📍 Feature file: {feature_file}")
    print(f"   First added in: {first_commit[:8]}")
    print(f"   Commit before:  {before_commit[:8]} — {log_result.stdout.strip()}")

    return before_commit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract git snapshot for eval-bench initial_state"
    )
    subparsers = parser.add_subparsers(dest="command")

    # extract 命令
    extract_parser = subparsers.add_parser("extract", help="Extract snapshot at commit")
    extract_parser.add_argument("--repo", required=True, help="Git repo path")
    extract_parser.add_argument("--commit", required=True, help="Git commit hash")
    extract_parser.add_argument("--output", required=True, help="Output directory")
    extract_parser.add_argument("--include", nargs="*", help="Paths to include")
    extract_parser.add_argument("--exclude", nargs="*", default=[], help="Patterns to exclude")

    # find-before 命令
    find_parser = subparsers.add_parser("find-before",
                                         help="Find commit before a feature file was added")
    find_parser.add_argument("--repo", required=True, help="Git repo path")
    find_parser.add_argument("--file", required=True, help="Feature file path (relative to repo)")

    args = parser.parse_args()

    if args.command == "extract":
        extract_snapshot(
            args.repo, args.commit, args.output,
            include_paths=args.include,
            exclude_patterns=args.exclude,
        )
    elif args.command == "find-before":
        commit = find_commit_before_feature(args.repo, args.file)
        print(f"\n💡 Use this to extract snapshot:")
        print(f"   python3 {sys.argv[0]} extract \\")
        print(f"     --repo {args.repo} \\")
        print(f"     --commit {commit[:8]} \\")
        print(f"     --output tasks/task-xxx/initial_state/project_code")
    else:
        parser.print_help()
