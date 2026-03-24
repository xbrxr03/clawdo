"""
do.py — ClawOS integration wrapper for claw-do.

This is the thin wrapper that powers `claw do "..."` inside ClawOS.
It calls claw_do with ClawOS context (PINNED.md, workspace, policyd).

Location: ~/clawos/clients/cli/commands/do.py

Usage inside claw CLI:
    claw do "find all log files older than 7 days"
    claw do --dry "delete temp files"
    claw do --yes "show disk usage"
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure claw_do is importable whether installed or run from source
_CLAW_DO_SRC = Path(__file__).parent.parent.parent.parent / "claw-do"
if _CLAW_DO_SRC.exists() and str(_CLAW_DO_SRC) not in sys.path:
    sys.path.insert(0, str(_CLAW_DO_SRC))

import click

from claw_do.context import collect_context, workspace_name, git_branch
from claw_do.generator import generate_command
from claw_do.renderer import (
    confirm_run,
    show_commands,
    show_error,
    show_running,
    show_success,
    show_audit_note,
    show_spinner_start,
)
from claw_do.runner import log_command, run_commands
from claw_do.safety import classify


def _check_policyd(commands: list[str]) -> tuple[bool, str]:
    """
    Check with ClawOS policyd before showing the command to the user.
    Returns (allowed, reason).
    """
    try:
        import requests
        # policyd runs on port 7074
        response = requests.post(
            "http://localhost:7074/check",
            json={
                "tool": "shell.exec",
                "commands": commands,
                "workspace": workspace_name() or "jarvis_default",
            },
            timeout=2,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("allowed", True), data.get("reason", "")
        # If policyd unreachable, allow (degraded mode)
        return True, ""
    except Exception:
        # policyd not running — allow in degraded mode
        return True, ""


@click.command(name="do")
@click.argument("request", nargs=-1, required=True)
@click.option("--dry", is_flag=True, default=False, help="Show only, never run.")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirm if safe.")
@click.option("--model", "-m", default=None, help="Override Ollama model.")
@click.option("--no-context", "no_context", is_flag=True, default=False)
def do_command(
    request: tuple[str, ...],
    dry: bool,
    yes: bool,
    model: str | None,
    no_context: bool,
) -> None:
    """Natural language → shell command. Offline. Safe by default."""
    request_str = " ".join(request)

    # Context label for display
    context_label: str | None = None
    if not no_context:
        ws = workspace_name()
        branch = git_branch()
        import os
        cwd_short = os.path.basename(os.getcwd())
        parts = []
        if ws:
            parts.append(ws)
        if branch:
            parts.append(f"git:{branch}")
        parts.append(f"~/{cwd_short}" if cwd_short else "~")
        context_label = " · ".join(parts)

    # Generate
    show_spinner_start("Generating command...")
    try:
        commands = generate_command(
            request=request_str,
            model=model,
            clawos_mode=not no_context,
        )
    except RuntimeError as e:
        show_error(str(e))
        sys.exit(1)

    # policyd check — happens BEFORE showing to user
    allowed, block_reason = _check_policyd(commands)
    if not allowed:
        from claw_do.renderer import show_blocked
        show_blocked(block_reason or "shell.exec not permitted in this workspace")
        log_command(
            request=request_str,
            commands=commands,
            exit_code=-1,
            is_dangerous=True,
            approved=False,
            dry=False,
        )
        sys.exit(1)

    # Classify
    is_dangerous, danger_reason, danger_level = classify(commands)

    # Display
    show_commands(
        commands=commands,
        is_dangerous=is_dangerous,
        danger_reason=danger_reason,
        danger_level=danger_level,
        context_label=context_label if not no_context else None,
    )

    # Confirm
    should_run = confirm_run(
        commands=commands,
        is_dangerous=is_dangerous,
        danger_level=danger_level,
        dry=dry,
        yes=yes,
    )

    # Run
    exit_code = 0
    if should_run:
        show_running(commands)
        exit_code = run_commands(commands)
        show_success(exit_code)

    # Audit (always in ClawOS mode)
    log_path = log_command(
        request=request_str,
        commands=commands,
        exit_code=exit_code if should_run else -1,
        is_dangerous=is_dangerous,
        approved=should_run,
        dry=dry,
    )
    if should_run:
        show_audit_note(log_path)

    sys.exit(exit_code if should_run else 0)
