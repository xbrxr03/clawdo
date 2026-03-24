"""
cli.py — claw-do CLI entrypoint.

Usage:
  claw-do "find large files"
  claw-do --dry "delete temp files"
  claw-do --yes "list disk usage"
  claw-do --model qwen2.5-coder:7b "set up venv"
  claw-do --no-context "list files"

ClawOS integration: also callable as `claw do "..."` via do.py wrapper.
"""
from __future__ import annotations

import sys

import click

from claw_do import __version__
from claw_do.context import collect_context, workspace_name
from claw_do.generator import generate_command
from claw_do.renderer import (
    confirm_run,
    console,
    show_commands,
    show_error,
    show_running,
    show_success,
    show_audit_note,
    show_spinner_start,
)
from claw_do.runner import log_command, run_commands
from claw_do.safety import classify


@click.command(name="claw-do")
@click.argument("request", nargs=-1, required=True)
@click.option(
    "--dry", is_flag=True, default=False,
    help="Show the command but never run it.",
)
@click.option(
    "--yes", "-y", is_flag=True, default=False,
    help="Skip confirmation for safe commands. Never bypasses dangerous command protection.",
)
@click.option(
    "--model", "-m", default=None,
    help="Ollama model to use (e.g. qwen2.5:7b). Auto-detected if not set.",
)
@click.option(
    "--no-context", "no_context", is_flag=True, default=False,
    help="Don't inject workspace context into the prompt.",
)
@click.option(
    "--clawos", is_flag=True, default=False,
    help="Enable ClawOS mode: PINNED.md facts + policyd integration.",
)
@click.option(
    "--ollama-host", default="http://localhost:11434", show_default=True,
    help="Ollama server URL.",
)
@click.option(
    "--no-audit", is_flag=True, default=False,
    help="Skip writing to the audit log.",
)
@click.version_option(version=__version__, prog_name="claw-do")
def main(
    request: tuple[str, ...],
    dry: bool,
    yes: bool,
    model: str | None,
    no_context: bool,
    clawos: bool,
    ollama_host: str,
    no_audit: bool,
) -> None:
    """
    Natural language → shell commands. Offline. Safe by default.

    \b
    Examples:
      claw-do "find all files larger than 1GB"
      claw-do "compress logs older than 7 days and archive them"
      claw-do --dry "delete all .pyc files"
      claw-do --yes "show disk usage by directory"
    """
    request_str = " ".join(request)

    # ── Detect ClawOS mode automatically ──────────────────────────────────────
    if not clawos:
        from pathlib import Path
        clawos_root = Path.home() / "clawos"
        if clawos_root.exists():
            clawos = True

    # ── Build context label for display ───────────────────────────────────────
    context_label: str | None = None
    if not no_context and clawos:
        ws = workspace_name()
        from claw_do.context import git_branch
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

    # ── Generate command ───────────────────────────────────────────────────────
    show_spinner_start("Generating command...")

    try:
        commands = generate_command(
            request=request_str,
            model=model,
            clawos_mode=clawos and not no_context,
            ollama_host=ollama_host,
        )
    except RuntimeError as e:
        show_error(str(e))
        sys.exit(1)

    if not commands:
        show_error("No command generated.")
        sys.exit(1)

    # ── Classify safety ───────────────────────────────────────────────────────
    is_dangerous, danger_reason, danger_level = classify(commands)

    # ── Display ───────────────────────────────────────────────────────────────
    show_commands(
        commands=commands,
        is_dangerous=is_dangerous,
        danger_reason=danger_reason,
        danger_level=danger_level,
        context_label=context_label if not no_context else None,
    )

    # ── Confirm ───────────────────────────────────────────────────────────────
    should_run = confirm_run(
        commands=commands,
        is_dangerous=is_dangerous,
        danger_level=danger_level,
        dry=dry,
        yes=yes,
    )

    # ── Execute ───────────────────────────────────────────────────────────────
    exit_code = 0
    if should_run:
        show_running(commands)
        exit_code = run_commands(commands)
        show_success(exit_code)

    # ── Audit log ─────────────────────────────────────────────────────────────
    if not no_audit:
        log_path = log_command(
            request=request_str,
            commands=commands,
            exit_code=exit_code if should_run else -1,
            is_dangerous=is_dangerous,
            approved=should_run,
            dry=dry,
        )
        if clawos and should_run:
            show_audit_note(log_path)

    sys.exit(exit_code if should_run else 0)

if __name__ == '__main__':
    main()

