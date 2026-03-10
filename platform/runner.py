#!/usr/bin/env python3
"""nanobot Eval Bench — Task Runner (runner.py)

Runs inside Docker container. Responsibilities:
1. Initialize isolated nanobot workspace (no host contamination)
2. Load multi-turn queries, drive nanobot agent
3. Collect execution trajectory (session JSONL) and final file state
4. Run hard verification tests (built-in rules + pytest scripts)
5. Output run_summary.json

Two task types:
- Type A (general): Create skills, write scripts, etc.
  - initial_state files map to workspace/ by default
- Type B (code_modification): Modify nanobot/webchat source code
  - initial_state_mapping controls precise file placement
  - project_code contains git-snapshot of nanobot source at specific commit
  - verify_script runs pytest on modified code

Mock provider naming:
- Mock services use dedicated provider names (e.g. "mock-volcengine")
  that never collide with the real AGENT_PROVIDER.
- Each task declares mock provider names in task.yaml mock_services[].provider_name.
"""

import asyncio
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


# ─── Data Structures ──────────────────────────────────

@dataclass
class RunMetrics:
    total_tool_calls: int = 0
    total_llm_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    wall_time_seconds: float = 0.0
    files_created: int = 0
    files_modified: int = 0


@dataclass
class RunResult:
    task_id: str
    success: bool = False
    error: Optional[str] = None
    metrics: RunMetrics = field(default_factory=RunMetrics)
    test_results: dict = field(default_factory=dict)


# ─── Environment Config ──────────────────────────────

EVAL_HOME = Path(os.environ.get("HOME", "/eval"))
NANOBOT_HOME = EVAL_HOME / ".nanobot"
WORKSPACE = NANOBOT_HOME / "workspace"
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", "/eval/results"))
TASK_DIR = Path(os.environ.get("TASK_DIR", "/eval/task"))
SESSION_ID = "eval:task-001"  # Default; overridden in main() from task.yaml

# Agent LLM config
AGENT_PROVIDER = os.environ.get("AGENT_PROVIDER", "anthropic")
AGENT_MODEL = os.environ.get("AGENT_MODEL", "claude-sonnet-4-20250514")
AGENT_API_KEY = os.environ.get("AGENT_API_KEY", "")
AGENT_API_BASE = os.environ.get("AGENT_API_BASE", "")

# Mock API
MOCK_API_URL = os.environ.get("MOCK_API_URL", "http://mock-api:18080")

# Limits
MAX_TOOL_CALLS = int(os.environ.get("MAX_TOOL_CALLS", "150"))
TIMEOUT_MINUTES = int(os.environ.get("TIMEOUT_MINUTES", "30"))


def setup_nanobot_home(task: dict):
    """Initialize container's isolated nanobot environment.

    Supports two modes:
    1. Default mapping (backward-compatible): skills/ and memory/ from initial_state
    2. Custom mapping (code_modification tasks): initial_state_mapping dict
    """
    print("[runner] Setting up nanobot home...", file=sys.stderr)

    # Create base directory structure
    for d in ["workspace/skills", "workspace/sessions", "workspace/memory"]:
        (NANOBOT_HOME / d).mkdir(parents=True, exist_ok=True)

    initial_state = TASK_DIR / "initial_state"
    if not initial_state.exists():
        print("[runner] WARNING: No initial_state directory", file=sys.stderr)
        _write_config(task)
        return

    # Check for custom mapping
    mapping = task.get("initial_state_mapping")

    if mapping:
        # Custom mapping mode: precise control over each directory
        print("[runner] Using custom initial_state_mapping", file=sys.stderr)
        for src_name, dest_rel in mapping.items():
            src_path = initial_state / src_name
            if not src_path.exists():
                print(f"[runner] WARNING: mapped source '{src_name}' not found, skipping",
                      file=sys.stderr)
                continue

            # dest_rel is relative to EVAL_HOME (/eval)
            dest_path = EVAL_HOME / dest_rel
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            if src_path.is_dir():
                shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dest_path)

            print(f"[runner] Mapped: {src_name} -> {dest_rel}", file=sys.stderr)
    else:
        # Default mapping mode (backward-compatible with task-001)
        for subdir in ["skills", "memory"]:
            src = initial_state / subdir
            if src.exists():
                target = WORKSPACE / subdir
                shutil.copytree(src, target, dirs_exist_ok=True)
                print(f"[runner] Copied {subdir} from initial_state", file=sys.stderr)

        # Copy other top-level files (e.g. config_mock.json)
        for f in initial_state.iterdir():
            if f.is_file():
                shutil.copy2(f, WORKSPACE / f.name)
                print(f"[runner] Copied file: {f.name}", file=sys.stderr)

    _write_config(task)


def _write_config(task: dict):
    """Generate nanobot config.json for the container.

    Agent LLM uses AGENT_PROVIDER directly.
    Mock services use dedicated provider names (e.g. "mock-volcengine")
    declared in task.yaml mock_services[].provider_name, so there's
    never a collision with the real agent provider.
    """
    agent_provider_key = AGENT_PROVIDER
    model_str = AGENT_MODEL
    if "/" not in model_str:
        model_str = f"{AGENT_PROVIDER}/{AGENT_MODEL}"

    # Build agent provider config
    agent_provider_config = {"apiKey": AGENT_API_KEY}
    if AGENT_API_BASE:
        agent_provider_config["apiBase"] = AGENT_API_BASE

    # Base config
    config = {
        "agents": {
            "defaults": {
                "workspace": str(WORKSPACE),
                "model": model_str,
                "maxTokens": 16384,
                "temperature": 0.3,
                "maxToolIterations": MAX_TOOL_CALLS,
            }
        },
        "providers": {
            agent_provider_key: agent_provider_config,
        },
        "channels": {
            "sendProgress": False,
            "sendToolHints": False,
        },
        "tools": {
            "exec": {"timeout": 60},
            "restrictToWorkspace": False,
            "web": {"search": {"apiKey": "", "maxResults": 5}},
        },
    }

    # Add mock providers from task.yaml mock_services
    mock_services = task.get("environment", {}).get("mock_services", [])
    for svc in mock_services:
        provider_name = svc.get("provider_name")
        if provider_name:
            mock_port = svc.get("port", 18080)
            config["providers"][provider_name] = {
                "apiKey": f"{provider_name}-api-key",
                "apiBase": f"{MOCK_API_URL}/api/v3",
            }
            print(f"[runner] Mock provider: {provider_name} -> {MOCK_API_URL}",
                  file=sys.stderr)

    # Apply task-level config overrides
    config_overrides = task.get("config_overrides", {})
    if config_overrides:
        _deep_merge(config, config_overrides)
        print(f"[runner] Applied config overrides: {list(config_overrides.keys())}",
              file=sys.stderr)

    config_path = NANOBOT_HOME / "config.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))
    print(f"[runner] Config written to {config_path}", file=sys.stderr)
    print(f"[runner] Agent provider: {agent_provider_key}", file=sys.stderr)
    print(f"[runner] Agent model: {model_str}", file=sys.stderr)


def _deep_merge(base: dict, override: dict):
    """Recursively merge override dict into base dict."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def load_queries() -> list[dict]:
    """Parse multi-turn queries from query.md."""
    query_path = TASK_DIR / "query.md"
    if not query_path.exists():
        return []

    content = query_path.read_text()
    turns = []
    current = None
    in_code = False

    for line in content.split("\n"):
        if line.startswith("## Turn"):
            if current:
                turns.append(current)
            current = {"label": line.lstrip("# ").strip(), "content": ""}
        elif line.startswith("```") and current is not None:
            in_code = not in_code
        elif in_code and current is not None:
            current["content"] += line + "\n"

    if current:
        turns.append(current)

    for t in turns:
        t["content"] = t["content"].strip()

    return [t for t in turns if t["content"]]


async def run_agent_turn(message: str, session_id: str) -> str:
    """Execute one turn of agent conversation."""
    print(f"\n[runner] >>> User: {message[:200]}...", file=sys.stderr)

    env = {
        **os.environ,
        "NANOBOT_HOME": str(NANOBOT_HOME),
        "HOME": str(EVAL_HOME),
    }

    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "nanobot", "agent",
                "-m", message,
                "-s", session_id,
                "--no-markdown",
            ],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_MINUTES * 60,
            env=env,
            cwd=str(EVAL_HOME),
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            print(f"[runner] Agent returned code {result.returncode}", file=sys.stderr)
            if stderr:
                print(f"[runner] STDERR: {stderr[:500]}", file=sys.stderr)

        print(f"[runner] <<< Agent: {stdout[:300]}...", file=sys.stderr)
        return stdout

    except subprocess.TimeoutExpired:
        print(f"[runner] Agent timed out after {TIMEOUT_MINUTES} minutes", file=sys.stderr)
        return "[TIMEOUT]"
    except Exception as e:
        print(f"[runner] Agent error: {e}", file=sys.stderr)
        return f"[ERROR: {e}]"


def snapshot_final_state(task: dict):
    """Snapshot workspace final state to results.

    For code_modification tasks, also snapshot project_code directories.
    """
    output = RESULTS_DIR / "final_state"
    output.mkdir(parents=True, exist_ok=True)

    # Snapshot workspace skills and memory (universal)
    for subdir in ["skills", "memory"]:
        src = WORKSPACE / subdir
        if src.exists():
            shutil.copytree(
                src, output / subdir,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )

    # Snapshot custom directories (code_modification tasks)
    snapshot_dirs = task.get("snapshot_dirs", [])
    for rel_path in snapshot_dirs:
        src = EVAL_HOME / rel_path
        if src.exists():
            dest = output / rel_path.replace("/", "_")
            if src.is_dir():
                shutil.copytree(
                    src, dest,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"),
                )
            else:
                shutil.copy2(src, dest)
            print(f"[runner] Snapshot: {rel_path} -> {dest.name}", file=sys.stderr)

    # Generate file manifest
    manifest = []
    for p in sorted(output.rglob("*")):
        if p.is_file():
            manifest.append({"path": str(p.relative_to(output)), "size": p.stat().st_size})

    (output / "file_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False)
    )

    print(f"[runner] Final state snapshot: {len(manifest)} files", file=sys.stderr)


def copy_session_as_trajectory():
    """Copy nanobot session JSONL as trajectory.

    Matches the eval session file by SESSION_ID (e.g. "eval:task-001" -> "eval_task-001.jsonl").
    Falls back to the first .jsonl file if no exact match is found (backward compatibility).
    """
    sessions_dir = WORKSPACE / "sessions"
    if not sessions_dir.exists():
        return

    dest = RESULTS_DIR / "trajectory.jsonl"

    # Precise match: SESSION_ID with ":" replaced by "_"
    expected_name = SESSION_ID.replace(":", "_") + ".jsonl"
    expected_file = sessions_dir / expected_name
    if expected_file.exists():
        shutil.copy2(expected_file, dest)
        print(f"[runner] Trajectory saved (exact match): {expected_name} -> {dest}",
              file=sys.stderr)
        return

    # Fallback: first .jsonl file (backward compatibility)
    for f in sessions_dir.glob("*.jsonl"):
        shutil.copy2(f, dest)
        print(f"[runner] Trajectory saved (fallback, no match for '{expected_name}'): "
              f"{f.name} -> {dest}", file=sys.stderr)
        return

    print(f"[runner] WARNING: No session JSONL found in {sessions_dir}", file=sys.stderr)


def run_verification(task: dict) -> dict:
    """Run hard verification using pytest verify_script.

    verify_script is the only supported verification method.
    success_criteria (declarative rules) is deprecated and will be ignored.
    """
    results = {}

    # Warn if deprecated success_criteria is still present
    if task.get("success_criteria"):
        print("[runner] WARNING: success_criteria is deprecated, use verify_script instead",
              file=sys.stderr)

    # Run pytest verify_script
    verify_script = task.get("verify_script")
    if verify_script:
        script_path = TASK_DIR / verify_script
        if script_path.exists():
            print(f"[runner] Running verify script: {verify_script}", file=sys.stderr)
            pytest_results = _run_pytest(script_path, task)
            results.update(pytest_results)
        else:
            results[f"verify_script:{verify_script}"] = {
                "passed": False,
                "error": f"Script not found: {verify_script}"
            }
    else:
        print("[runner] WARNING: No verify_script defined, skipping verification",
              file=sys.stderr)

    return results


def _run_pytest(script_path: Path, task: dict) -> dict:
    """Run pytest verification script, return per-test results.

    Verification scripts access paths via environment variables:
    - EVAL_HOME: /eval
    - WORKSPACE: /eval/.nanobot/workspace
    - TASK_DIR: /eval/task
    - RESULTS_DIR: /eval/results
    - NANOBOT_HOME: /eval/.nanobot
    - TASK_ID: task id from task.yaml (e.g. "task-001")
    - TASK_NAME: task name from task.yaml
    - PROJECT_DIR: project code directory (if code_modification task)
    """
    results = {}

    env = {
        **os.environ,
        "EVAL_HOME": str(EVAL_HOME),
        "WORKSPACE": str(WORKSPACE),
        "TASK_DIR": str(TASK_DIR),
        "NANOBOT_HOME": str(NANOBOT_HOME),
        "RESULTS_DIR": str(RESULTS_DIR),
        "TASK_ID": task.get("id", ""),
        "TASK_NAME": task.get("name", ""),
    }

    # Set PROJECT_DIR if initial_state_mapping has project_code
    mapping = task.get("initial_state_mapping", {})
    if "project_code" in mapping:
        env["PROJECT_DIR"] = str(EVAL_HOME / mapping["project_code"])
    else:
        # Try common project directory paths
        for candidate in ["project", "project_code"]:
            candidate_path = WORKSPACE / candidate
            if candidate_path.exists() and candidate_path.is_dir():
                env["PROJECT_DIR"] = str(candidate_path)
                break

    # Run pytest with JSON report
    json_report = RESULTS_DIR / "pytest_report.json"
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                str(script_path),
                f"--json-report-file={json_report}",
                "--json-report",
                "-v",
                "--tb=short",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
            cwd=str(EVAL_HOME),
        )

        # Try JSON report first, fall back to stdout parsing
        if json_report.exists():
            report = json.loads(json_report.read_text())
            for test in report.get("tests", []):
                name = test.get("nodeid", "unknown")
                passed = test.get("outcome") == "passed"
                error = None
                if not passed:
                    error = test.get("call", {}).get("longrepr", "")
                results[f"pytest:{name}"] = {"passed": passed, "error": error}
        else:
            _parse_pytest_stdout(result, results)

        print(f"[runner] pytest exit code: {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(f"[runner] pytest stderr: {result.stderr[:500]}", file=sys.stderr)

    except subprocess.TimeoutExpired:
        results["pytest:timeout"] = {"passed": False, "error": "pytest timed out after 120s"}
    except Exception as e:
        results["pytest:error"] = {"passed": False, "error": str(e)}

    return results


def _parse_pytest_stdout(result: subprocess.CompletedProcess, results: dict):
    """Parse test results from pytest stdout (fallback when json-report unavailable)."""
    for line in result.stdout.split("\n"):
        line = line.strip()
        if " PASSED" in line:
            name = line.split(" PASSED")[0].strip()
            results[f"pytest:{name}"] = {"passed": True, "error": None}
        elif " FAILED" in line:
            name = line.split(" FAILED")[0].strip()
            results[f"pytest:{name}"] = {"passed": False, "error": "See pytest output"}

    if not results:
        passed = result.returncode == 0
        results["pytest:overall"] = {
            "passed": passed,
            "error": None if passed else (result.stdout[-500:] if result.stdout else result.stderr[-500:])
        }


def collect_metrics(start_time: float, task: dict) -> RunMetrics:
    """Collect execution metrics from session JSONL and analytics.db."""
    metrics = RunMetrics()
    metrics.wall_time_seconds = time.time() - start_time

    sessions_dir = WORKSPACE / "sessions"
    if sessions_dir.exists():
        for f in sessions_dir.glob("*.jsonl"):
            with open(f) as fh:
                for line in fh:
                    try:
                        msg = json.loads(line)
                        if msg.get("role") == "assistant":
                            tcs = msg.get("tool_calls", [])
                            metrics.total_tool_calls += len(tcs)
                            if tcs or msg.get("content"):
                                metrics.total_llm_calls += 1
                    except json.JSONDecodeError:
                        pass

    # ─── Token usage from analytics.db ──────────────
    analytics_db = WORKSPACE / "analytics.db"
    if analytics_db.exists():
        try:
            conn = sqlite3.connect(str(analytics_db))
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT COALESCE(SUM(prompt_tokens), 0)     AS prompt_tokens,
                       COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                       COALESCE(SUM(total_tokens), 0)      AS total_tokens
                FROM token_usage
                WHERE session_key = ?
                """,
                (SESSION_ID,),
            ).fetchone()
            if row:
                metrics.total_prompt_tokens = row["prompt_tokens"]
                metrics.total_completion_tokens = row["completion_tokens"]
            # If no records for this session, try summing all records
            # (in case session_key format differs)
            if row and row["total_tokens"] == 0:
                row_all = conn.execute(
                    """
                    SELECT COALESCE(SUM(prompt_tokens), 0)     AS prompt_tokens,
                           COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                           COALESCE(SUM(total_tokens), 0)      AS total_tokens
                    FROM token_usage
                    """
                ).fetchone()
                if row_all and row_all["total_tokens"] > 0:
                    metrics.total_prompt_tokens = row_all["prompt_tokens"]
                    metrics.total_completion_tokens = row_all["completion_tokens"]
                    print(f"[runner] Token usage: no records for session '{SESSION_ID}', "
                          f"using all records (total_tokens={row_all['total_tokens']})",
                          file=sys.stderr)
            conn.close()
            print(f"[runner] Token usage from analytics.db: "
                  f"prompt={metrics.total_prompt_tokens}, "
                  f"completion={metrics.total_completion_tokens}, "
                  f"total={metrics.total_prompt_tokens + metrics.total_completion_tokens}",
                  file=sys.stderr)
        except Exception as e:
            print(f"[runner] WARNING: Failed to read analytics.db: {e}", file=sys.stderr)

    # Count files in relevant directories
    count_dirs = []
    mapping = task.get("initial_state_mapping", {})
    if "project_code" in mapping:
        count_dirs.append(EVAL_HOME / mapping["project_code"])
    else:
        doubao_dir = WORKSPACE / "skills" / "doubao-search"
        if doubao_dir.exists():
            count_dirs.append(doubao_dir)

    for d in count_dirs:
        if d.exists():
            metrics.files_created += sum(1 for _ in d.rglob("*") if _.is_file())

    return metrics


def _parse_args() -> bool:
    """Parse command-line arguments. Returns True if dry-run mode is enabled.

    Supports both --dry-run flag and DRY_RUN=1 environment variable.
    """
    import argparse
    parser = argparse.ArgumentParser(description="nanobot Eval Bench Task Runner")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.environ.get("DRY_RUN", "").strip() in ("1", "true", "yes"),
        help="Skip agent turns, only verify task setup and run tests",
    )
    args = parser.parse_args()
    return args.dry_run


async def main():
    global SESSION_ID

    start_time = time.time()

    # Parse command-line arguments
    dry_run = _parse_args()

    print("=" * 60, file=sys.stderr)
    print("  nanobot Eval Bench - Task Runner", file=sys.stderr)
    if dry_run:
        print("  *** DRY-RUN MODE — agent turns will be skipped ***", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Validate required env vars (skip API key check in dry-run mode)
    if not dry_run and not AGENT_API_KEY:
        print("[runner] ERROR: AGENT_API_KEY not set!", file=sys.stderr)
        sys.exit(1)

    # Load task definition
    task_yaml = TASK_DIR / "task.yaml"
    if not task_yaml.exists():
        print(f"[runner] ERROR: {task_yaml} not found!", file=sys.stderr)
        sys.exit(1)

    task = yaml.safe_load(task_yaml.read_text())
    task_id = task["id"]
    task_type = task.get("type", "general")

    # P3-1: Dynamic SESSION_ID from task_id
    SESSION_ID = f"eval:{task_id}"

    print(f"[runner] Task: {task_id} - {task['name']}", file=sys.stderr)
    print(f"[runner] Type: {task_type}", file=sys.stderr)
    print(f"[runner] Session ID: {SESSION_ID}", file=sys.stderr)

    # 1. Initialize environment
    setup_nanobot_home(task)

    # 2. Load queries
    turns = load_queries()
    print(f"[runner] Loaded {len(turns)} query turns", file=sys.stderr)

    # 3. Execute multi-turn conversation (skipped in dry-run mode)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    responses = []

    if dry_run:
        print(f"\n[runner] DRY-RUN: Skipping {len(turns)} agent turn(s)", file=sys.stderr)
        for i, turn in enumerate(turns):
            responses.append({
                "turn": i + 1,
                "label": turn["label"],
                "user": turn["content"],
                "agent": "[DRY-RUN: agent execution skipped]",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })
    else:
        for i, turn in enumerate(turns):
            print(f"\n{'_'*40}", file=sys.stderr)
            print(f"[runner] Turn {i+1}/{len(turns)}: {turn['label']}", file=sys.stderr)
            print(f"{'_'*40}", file=sys.stderr)

            response = await run_agent_turn(turn["content"], SESSION_ID)
            responses.append({
                "turn": i + 1,
                "label": turn["label"],
                "user": turn["content"],
                "agent": response,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })

            await asyncio.sleep(1)

    # Save conversation summary
    (RESULTS_DIR / "turns.json").write_text(
        json.dumps(responses, indent=2, ensure_ascii=False)
    )

    # 4. Snapshot final state
    snapshot_final_state(task)

    # 5. Copy session trajectory
    copy_session_as_trajectory()

    # 6. Run verification
    print(f"\n{'_'*40}", file=sys.stderr)
    print("[runner] Running verification...", file=sys.stderr)
    test_results = run_verification(task)

    passed = sum(1 for v in test_results.values() if v["passed"])
    total = len(test_results)
    print(f"[runner] Verification: {passed}/{total} passed", file=sys.stderr)
    for criterion, result in test_results.items():
        status = "PASS" if result["passed"] else "FAIL"
        err = f" ({result['error'][:60]})" if result.get("error") else ""
        print(f"  [{status}] {criterion[:80]}{err}", file=sys.stderr)

    # 7. Collect metrics
    metrics = collect_metrics(start_time, task)

    # 8. Output results
    total_tokens = metrics.total_prompt_tokens + metrics.total_completion_tokens
    summary = {
        "task_id": task_id,
        "task_name": task["name"],
        "task_type": task_type,
        "dry_run": dry_run,
        "success": all(v["passed"] for v in test_results.values()) if test_results else False,
        "verification": {"passed": passed, "total": total},
        "test_results": test_results,
        "metrics": {
            "tool_calls": metrics.total_tool_calls,
            "llm_calls": metrics.total_llm_calls,
            "prompt_tokens": metrics.total_prompt_tokens,
            "completion_tokens": metrics.total_completion_tokens,
            "total_tokens": total_tokens,
            "wall_time_seconds": round(metrics.wall_time_seconds, 1),
            "files_created": metrics.files_created,
        },
        "agent_config": {
            "provider": AGENT_PROVIDER,
            "model": AGENT_MODEL,
        },
    }

    (RESULTS_DIR / "run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False)
    )

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"[runner] Done! Wall time: {metrics.wall_time_seconds:.1f}s", file=sys.stderr)
    print(f"[runner] Tool calls: {metrics.total_tool_calls}, LLM calls: {metrics.total_llm_calls}",
          file=sys.stderr)
    if total_tokens > 0:
        print(f"[runner] Tokens: {total_tokens:,} "
              f"(prompt: {metrics.total_prompt_tokens:,}, "
              f"completion: {metrics.total_completion_tokens:,})",
              file=sys.stderr)
    print(f"[runner] Result: {'PASS' if summary['success'] else 'FAIL'}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    print(json.dumps(summary, indent=2, ensure_ascii=False))

    sys.exit(0 if summary["success"] else 1)


if __name__ == "__main__":
    asyncio.run(main())
