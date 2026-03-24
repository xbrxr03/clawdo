"""
test_context.py — Tests for the context collector.
Run: pytest tests/test_context.py -v
"""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from claw_do.context import (
    collect_context,
    format_context,
    git_branch,
    git_status_short,
    recent_files,
)


def test_collect_context_has_required_keys():
    ctx = collect_context()
    # cwd and os should always be present
    assert "cwd" in ctx
    assert "os" in ctx
    assert ctx["cwd"] == os.getcwd()


def test_collect_context_no_none_values():
    ctx = collect_context()
    for k, v in ctx.items():
        assert v is not None, f"Key {k!r} has None value"


def test_format_context_is_string():
    ctx = collect_context()
    result = format_context(ctx)
    assert isinstance(result, str)
    assert len(result) > 0


def test_format_context_contains_cwd():
    ctx = {"cwd": "/home/user/project"}
    result = format_context(ctx)
    assert "/home/user/project" in result


def test_recent_files_returns_list(tmp_path):
    # Create some test files
    for name in ["a.txt", "b.py", "c.md"]:
        (tmp_path / name).write_text("test")

    files = recent_files(5, cwd=str(tmp_path))
    assert isinstance(files, list)
    assert len(files) <= 5
    assert all(isinstance(f, str) for f in files)


def test_recent_files_empty_dir(tmp_path):
    files = recent_files(5, cwd=str(tmp_path))
    assert files == []


def test_recent_files_respects_limit(tmp_path):
    for i in range(10):
        (tmp_path / f"file{i}.txt").write_text("x")
    files = recent_files(3, cwd=str(tmp_path))
    assert len(files) <= 3


def test_git_branch_returns_string_or_none():
    result = git_branch()
    assert result is None or isinstance(result, str)


def test_git_status_returns_string_or_none():
    result = git_status_short()
    assert result is None or isinstance(result, str)


def test_clawos_mode_adds_extra_keys():
    ctx = collect_context(clawos_mode=True)
    # These keys should be attempted even if values are None (filtered out)
    # We just check the function runs without error in ClawOS mode
    assert "cwd" in ctx
