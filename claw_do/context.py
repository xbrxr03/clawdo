"""
context.py — Environment context collector for claw-do.
Collects cwd, git state, recent files, OS/shell info.
ClawOS mode: also reads PINNED.md, WORKFLOW.md, workspace name.
"""
from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path


def _run(cmd: list[str], cwd: str | None = None) -> str | None:
    """Run a shell command silently, return stdout or None on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3,
            cwd=cwd,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except Exception:
        pass
    return None


def git_branch(cwd: str | None = None) -> str | None:
    return _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)


def git_status_short(cwd: str | None = None) -> str | None:
    raw = _run(["git", "status", "--short"], cwd=cwd)
    if raw:
        # Summarise: "3M 1? 0D" style
        lines = raw.splitlines()
        modified = sum(1 for l in lines if l.startswith(" M") or l.startswith("M "))
        untracked = sum(1 for l in lines if l.startswith("??"))
        deleted = sum(1 for l in lines if l.startswith(" D") or l.startswith("D "))
        parts = []
        if modified:
            parts.append(f"{modified} modified")
        if untracked:
            parts.append(f"{untracked} untracked")
        if deleted:
            parts.append(f"{deleted} deleted")
        return ", ".join(parts) if parts else "clean"
    return None


def recent_files(n: int = 5, cwd: str | None = None) -> list[str]:
    """Return the n most recently modified files in cwd (non-hidden, non-git)."""
    target = Path(cwd) if cwd else Path.cwd()
    try:
        files = [
            f for f in target.iterdir()
            if f.is_file()
            and not f.name.startswith(".")
            and f.suffix not in {".pyc", ".pyo"}
        ]
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return [f.name for f in files[:n]]
    except Exception:
        return []


def read_pinned_md() -> str | None:
    """Read PINNED.md from the ClawOS workspace (if present)."""
    clawos_root = Path.home() / "clawos"
    pinned = clawos_root / "workspace" / "jarvis_default" / "PINNED.md"
    if pinned.exists():
        try:
            content = pinned.read_text().strip()
            return content if content else None
        except Exception:
            pass
    return None


def workspace_name() -> str | None:
    """Detect current ClawOS workspace name from directory or config."""
    cwd = Path.cwd()
    clawos_root = Path.home() / "clawos" / "workspace"
    try:
        cwd.relative_to(clawos_root)
        # We're inside a workspace directory
        parts = cwd.relative_to(clawos_root).parts
        if parts:
            return parts[0]
    except ValueError:
        pass
    # Check if there's a .clawos-workspace marker
    marker = cwd / ".clawos-workspace"
    if marker.exists():
        try:
            return marker.read_text().strip()
        except Exception:
            pass
    return None


def collect_context(clawos_mode: bool = False) -> dict:
    """
    Collect environment context for LLM injection.
    Returns a dict of key → value (None values are filtered by the caller).
    """
    cwd = os.getcwd()
    ctx: dict = {
        "cwd": cwd,
        "os": platform.system(),
        "shell": os.environ.get("SHELL", "bash").split("/")[-1],
        "user": os.environ.get("USER") or os.environ.get("USERNAME"),
        "git_branch": git_branch(cwd),
        "git_status": git_status_short(cwd),
        "recent_files": ", ".join(recent_files(5, cwd)) or None,
    }

    if clawos_mode:
        ctx["workspace"] = workspace_name()
        ctx["pinned_facts"] = read_pinned_md()

    # Filter None values
    return {k: v for k, v in ctx.items() if v is not None}


def format_context(ctx: dict) -> str:
    """Format context dict as a readable string for the system prompt."""
    lines = []
    label_map = {
        "cwd": "Current directory",
        "os": "OS",
        "shell": "Shell",
        "user": "User",
        "git_branch": "Git branch",
        "git_status": "Git status",
        "recent_files": "Recent files",
        "workspace": "ClawOS workspace",
        "pinned_facts": "Workspace facts (PINNED.md)",
    }
    for key, label in label_map.items():
        if key in ctx:
            val = ctx[key]
            if key == "pinned_facts":
                lines.append(f"{label}:\n{val}")
            else:
                lines.append(f"{label}: {val}")
    return "\n".join(lines)
