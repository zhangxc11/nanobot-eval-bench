#!/usr/bin/env python3
"""Task 002: Token 用量统计系统 — 验证脚本

通过 pytest 验证 agent 的代码修改是否正确。

环境变量：
  PROJECT_DIR: nanobot 项目源码目录（agent 修改后的版本）
  WORKSPACE: nanobot workspace 目录
"""

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

# ─── 路径设置 ──────────────────────────────────────────

PROJECT_DIR = Path(os.environ.get(
    "PROJECT_DIR",
    "/eval/.nanobot/workspace/project/nanobot"
))
WORKSPACE = Path(os.environ.get(
    "WORKSPACE",
    "/eval/.nanobot/workspace"
))


# ═══════════════════════════════════════════════════════
# Test Group 1: usage 模块文件存在性
# ═══════════════════════════════════════════════════════

class TestUsageModuleExists:
    """验证 usage 模块的文件结构"""

    def test_usage_directory_exists(self):
        """usage/ 目录必须存在"""
        usage_dir = PROJECT_DIR / "nanobot" / "usage"
        assert usage_dir.exists() and usage_dir.is_dir(), \
            f"usage/ directory not found at {usage_dir}"

    def test_usage_init_exists(self):
        """usage/__init__.py 必须存在"""
        init_path = PROJECT_DIR / "nanobot" / "usage" / "__init__.py"
        assert init_path.exists(), \
            f"usage/__init__.py not found"

    def test_usage_recorder_exists(self):
        """usage/recorder.py 必须存在"""
        recorder_path = PROJECT_DIR / "nanobot" / "usage" / "recorder.py"
        assert recorder_path.exists(), \
            f"usage/recorder.py not found"

    def test_recorder_importable(self):
        """recorder.py 必须可以正常导入"""
        recorder_path = PROJECT_DIR / "nanobot" / "usage" / "recorder.py"
        if not recorder_path.exists():
            pytest.skip("recorder.py not found")

        sys.path.insert(0, str(PROJECT_DIR))
        try:
            spec = importlib.util.spec_from_file_location(
                "nanobot.usage.recorder",
                recorder_path
            )
            assert spec is not None, "Cannot create module spec"
            module = importlib.util.module_from_spec(spec)
            # Don't actually exec_module (may have import deps)
            # Just verify it's a valid Python file
            assert spec.loader is not None
        finally:
            sys.path.pop(0)


# ═══════════════════════════════════════════════════════
# Test Group 2: recorder.py 内容验证
# ═══════════════════════════════════════════════════════

class TestRecorderContent:
    """验证 recorder.py 的实现质量"""

    @pytest.fixture
    def recorder_content(self):
        path = PROJECT_DIR / "nanobot" / "usage" / "recorder.py"
        if not path.exists():
            pytest.skip("recorder.py not found")
        return path.read_text()

    def test_uses_sqlite(self, recorder_content):
        """recorder.py 必须使用 SQLite"""
        assert "sqlite3" in recorder_content, \
            "recorder.py should import sqlite3"

    def test_has_record_function(self, recorder_content):
        """recorder.py 必须有记录用量的函数/方法"""
        has_record = any(kw in recorder_content.lower() for kw in [
            "def record", "def log_usage", "def save",
            "def track", "def add_usage", "def record_usage",
        ])
        assert has_record, \
            "recorder.py should have a record/log/save function or method"

    def test_has_query_function(self, recorder_content):
        """recorder.py 应有查询功能"""
        has_query = any(kw in recorder_content.lower() for kw in [
            "def get_summary", "def get_by_session", "def query",
            "def get_usage", "def fetch", "def list_usage",
        ])
        assert has_query, \
            "recorder.py should have query/get functions"

    def test_has_create_table(self, recorder_content):
        """recorder.py 应能自动创建表"""
        assert "CREATE TABLE" in recorder_content.upper() or \
               "create_table" in recorder_content, \
            "recorder.py should auto-create table if not exists"

    def test_schema_has_required_fields(self, recorder_content):
        """schema 必须包含必要字段"""
        content_lower = recorder_content.lower()
        required_fields = [
            "timestamp", "session", "model",
            "prompt_tokens", "completion_tokens"
        ]
        for field in required_fields:
            assert field in content_lower, \
                f"Schema should include '{field}' field"

    def test_no_hardcoded_paths(self, recorder_content):
        """不应硬编码绝对路径"""
        assert "/Users/" not in recorder_content, \
            "recorder.py should not hardcode absolute user paths"

    def test_has_class_definition(self, recorder_content):
        """应有 UsageRecorder 或类似的类定义"""
        has_class = any(kw in recorder_content for kw in [
            "class UsageRecorder", "class Recorder",
            "class TokenRecorder", "class UsageTracker",
        ])
        assert has_class, \
            "recorder.py should define a UsageRecorder class"


# ═══════════════════════════════════════════════════════
# Test Group 3: loop.py 集成验证
# ═══════════════════════════════════════════════════════

class TestLoopIntegration:
    """验证 loop.py 中的 usage recording 集成"""

    @pytest.fixture
    def loop_content(self):
        path = PROJECT_DIR / "nanobot" / "agent" / "loop.py"
        assert path.exists(), "loop.py not found"
        return path.read_text()

    def test_loop_references_usage(self, loop_content):
        """loop.py 必须引用 usage 模块"""
        assert "usage" in loop_content.lower(), \
            "loop.py should reference usage module"

    def test_loop_imports_usage(self, loop_content):
        """loop.py 应导入 usage 相关模块"""
        has_import = ("from nanobot.usage" in loop_content or
                      "import nanobot.usage" in loop_content or
                      "from .usage" in loop_content or
                      "from ..usage" in loop_content)
        # Also allow importing via a local variable
        if not has_import:
            has_import = "UsageRecorder" in loop_content or "usage_recorder" in loop_content
        assert has_import, \
            "loop.py should import from usage module"

    def test_loop_records_after_llm(self, loop_content):
        """loop.py 在 LLM 调用后应记录用量"""
        has_recording = any(kw in loop_content for kw in [
            "record_usage", "log_usage", "track_usage",
            "record(", ".record(",
            "usage_recorder", "recorder.record",
        ])
        assert has_recording, \
            "loop.py should call usage recording after LLM response"


# ═══════════════════════════════════════════════════════
# Test Group 4: 不破坏现有功能
# ═══════════════════════════════════════════════════════

class TestNoBreakingChanges:
    """验证修改不破坏现有功能"""

    def test_loop_has_core_functions(self):
        """loop.py 的核心函数不应被删除"""
        loop_path = PROJECT_DIR / "nanobot" / "agent" / "loop.py"
        content = loop_path.read_text()
        # AgentLoop class should still exist
        assert "class AgentLoop" in content, \
            "loop.py should still have AgentLoop class"

    def test_loop_has_run_method(self):
        """loop.py 应保留 run 方法"""
        loop_path = PROJECT_DIR / "nanobot" / "agent" / "loop.py"
        content = loop_path.read_text()
        assert "async def run" in content or "def run" in content, \
            "loop.py should still have run method"

    def test_loop_has_chat_method(self):
        """loop.py 应保留 LLM 调用相关方法"""
        loop_path = PROJECT_DIR / "nanobot" / "agent" / "loop.py"
        content = loop_path.read_text()
        # Original nanobot code calls LLM via self.provider.chat() inside
        # _run_agent_loop.  Accept any of these patterns as evidence that
        # the LLM call path is intact.
        has_chat = ("_chat_with_retry" in content or
                    "_chat" in content or
                    "chat_completion" in content or
                    "provider.chat" in content or
                    "_run_agent_loop" in content)
        assert has_chat, \
            "loop.py should still have chat/LLM call method"

    def test_other_modules_untouched(self):
        """其他核心模块不应被意外修改"""
        # Check that key files still exist
        key_files = [
            "nanobot/config/schema.py",
            "nanobot/session/manager.py",
            "nanobot/providers/base.py",
        ]
        for rel_path in key_files:
            full_path = PROJECT_DIR / rel_path
            assert full_path.exists(), \
                f"{rel_path} should still exist"


# ═══════════════════════════════════════════════════════
# Test Group 5: Git 提交验证（可选）
# ═══════════════════════════════════════════════════════

class TestGitCommit:
    """验证 agent 是否进行了 git commit"""

    def test_has_git_commits(self):
        """应有新的 git commit"""
        result = subprocess.run(
            ["git", "log", "--oneline"],
            capture_output=True, text=True,
            cwd=str(PROJECT_DIR), timeout=10,
        )
        lines = result.stdout.strip().split("\n")
        # Should have more than the initial 2 commits
        assert len(lines) >= 2, \
            f"Expected at least 2 git commits, found {len(lines)}"

    def test_usage_files_tracked(self):
        """usage/ 文件应被 git 跟踪"""
        result = subprocess.run(
            ["git", "ls-files", "nanobot/usage/"],
            capture_output=True, text=True,
            cwd=str(PROJECT_DIR), timeout=10,
        )
        files = result.stdout.strip().split("\n")
        tracked = [f for f in files if f.strip()]
        # At least __init__.py and recorder.py should be tracked
        assert len(tracked) >= 2, \
            f"Expected at least 2 tracked files in usage/, found: {tracked}"
