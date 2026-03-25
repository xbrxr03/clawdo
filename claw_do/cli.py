"""
cli.py — claw-do CLI entrypoint.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

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
from claw_do.runner import log_command, run_commands, _audit_log_path
from claw_do.safety import classify


def _read_audit_log(n: int = 20) -> list[dict]:
    log_path = _audit_log_path()
    if not log_path.exists():
        return []
    try:
        lines = log_path.read_text().strip().splitlines()
        entries = []
        for line in lines:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
        return entries[-n:]
    except Exception:
        return []


def _read_bash_history(n: int = 10) -> list[str]:
    history_file = Path.home() / ".bash_history"
    if not history_file.exists():
        return []
    try:
        lines = history_file.read_text(errors="ignore").strip().splitlines()
        lines = [l for l in lines if not l.startswith("claw-do") and not l.startswith("~/bin/claw-do")]
        return lines[-n:]
    except Exception:
        return []


def _infer_undo(command: str) -> str | None:
    import re
    m = re.match(r'mv\s+(\S+)\s+(\S+)', command)
    if m:
        return f"mv {m.group(2)} {m.group(1)}"
    m = re.match(r'mkdir(?:\s+-p)?\s+(\S+)', command)
    if m:
        return f"rmdir {m.group(1)}"
    m = re.match(r'cp\s+(?:-\w+\s+)?(\S+)\s+(\S+)', command)
    if m:
        return f"rm {m.group(2)}"
    m = re.match(r'touch\s+(\S+)', command)
    if m:
        return f"rm {m.group(1)}"
    return None


@click.command(name="claw-do")
@click.argument("request", nargs=-1, required=False)
@click.option("--dry", is_flag=True, default=False)
@click.option("--yes", "-y", is_flag=True, default=False)
@click.option("--model", "-m", default=None)
@click.option("--no-context", "no_context", is_flag=True, default=False)
@click.option("--clawos", is_flag=True, default=False)
@click.option("--ollama-host", default="http://localhost:11434")
@click.option("--no-audit", is_flag=True, default=False)
@click.option("--history", is_flag=True, default=False, help="Show last 10 commands run.")
@click.option("--undo", is_flag=True, default=False, help="Reverse the last command.")
@click.option("--explain", is_flag=True, default=False, help="Explain the command instead of running it.")
@click.option("--step", is_flag=True, default=False, help="Confirm each step of a multi-step plan individually.")
@click.version_option(version=__version__, prog_name="claw-do")
def main(request, dry, yes, model, no_context, clawos, ollama_host, no_audit, history, undo, explain, step):
    """Natural language to shell commands. Offline. Safe by default."""

    if history:
        entries = _read_audit_log(10)
        if not entries:
            console.print("\n  [dim]No command history yet.[/dim]\n")
            return
        console.print()
        console.print("  [bold blue]◆[/bold blue]  [bold]Recent commands[/bold]")
        console.print("  " + "─" * 53)
        for e in reversed(entries):
            ts = e["timestamp"][:16].replace("T", " ")
            cmds = " && ".join(e["commands"])
            approved = "[green]✓[/green]" if e["approved"] else "[red]✗[/red]"
            dangerous = " [yellow]⚠[/yellow]" if e.get("is_dangerous") else ""
            console.print(f"  {approved}{dangerous}  [dim]{ts}[/dim]  [cyan]{cmds}[/cyan]")
        console.print("  " + "─" * 53)
        console.print()
        return

    if undo:
        entries = _read_audit_log(20)
        last = next((e for e in reversed(entries) if e["approved"] and not e.get("is_dangerous")), None)
        if not last:
            console.print("\n  [dim]No undoable command found in history.[/dim]\n")
            return
        cmd = " && ".join(last["commands"])
        inverse = _infer_undo(cmd)
        console.print()
        console.print("  [bold blue]◆[/bold blue]  [bold]Last command[/bold]")
        console.print("  " + "─" * 53)
        console.print(f"  [cyan]{cmd}[/cyan]")
        console.print("  " + "─" * 53)
        if inverse:
            console.print("  [bold blue]◆[/bold blue]  [bold]Suggested undo[/bold]")
            console.print("  " + "─" * 53)
            console.print(f"  [cyan]{inverse}[/cyan]")
            console.print("  " + "─" * 53)
            console.print()
            from rich.prompt import Confirm
            if Confirm.ask("  Run undo?", default=False):
                run_commands([inverse])
                console.print("  [green]✓[/green]  Done\n")
        else:
            console.print("  [dim]No automatic undo available for this command.[/dim]\n")
        return

    if not request:
        show_error('Please provide a request. Example: claw-do "show disk usage"')
        sys.exit(1)

    request_str = " ".join(request)

    if not clawos:
        if (Path.home() / "clawos").exists():
            clawos = True

    context_label = None
    if not no_context:
        from claw_do.context import git_branch
        ws = workspace_name()
        branch = git_branch()
        cwd_short = os.path.basename(os.getcwd())
        parts = []
        if ws:
            parts.append(ws)
        if branch:
            parts.append(f"git:{branch}")
        parts.append(f"~/{cwd_short}" if cwd_short else "~")
        context_label = " · ".join(parts)

    extra_ctx = {}
    if not no_context:
        recent_cmds = _read_bash_history(10)
        if recent_cmds:
            extra_ctx["recent_shell_history"] = "; ".join(recent_cmds[-5:])

    show_spinner_start("Generating command...")

    try:
        commands = generate_command(
            request=request_str,
            model=model,
            extra_context=extra_ctx if extra_ctx else None,
            clawos_mode=clawos and not no_context,
            ollama_host=ollama_host,
        )
    except RuntimeError as e:
        show_error(str(e))
        sys.exit(1)

    if not commands:
        show_error("No command generated.")
        sys.exit(1)

    if explain:
        try:
            import ollama as _ollama
            cmd_str = " && ".join(commands)
            client = _ollama.Client(host=ollama_host)
            response = client.chat(
                model=model or "qwen2.5:7b",
                messages=[{"role": "user", "content": f"Explain what this shell command does in plain English, 2-3 sentences max. Be specific.\n\nCommand: {cmd_str}"}],
                options={"temperature": 0.1, "num_predict": 200},
            )
            explanation = response["message"]["content"].strip()
        except Exception as e:
            explanation = f"Could not generate explanation: {e}"
        console.print()
        console.print("  [bold blue]◆[/bold blue]  [bold]Command[/bold]")
        console.print("  " + "─" * 53)
        for cmd in commands:
            console.print(f"  [cyan]{cmd}[/cyan]")
        console.print("  " + "─" * 53)
        console.print("  [bold blue]◆[/bold blue]  [bold]What it does[/bold]")
        console.print(f"  {explanation}\n")
        return

    is_dangerous, danger_reason, danger_level = classify(commands)

    if dry and not explain:
        from claw_do.runner import preview_affected_files
        from claw_do.renderer import show_dry_preview
        affected = preview_affected_files(commands)
        show_dry_preview(affected)
    show_commands(
        commands=commands,
        is_dangerous=is_dangerous,
        danger_reason=danger_reason,
        danger_level=danger_level,
        context_label=context_label if not no_context else None,
    )

    if step and len(commands) > 1:
        exit_code = 0
        console.print()
        for i, cmd in enumerate(commands, 1):
            console.print(f"  [bold blue]Step {i}/{len(commands)}:[/bold blue] [cyan]{cmd}[/cyan]")
            _, dr, dl = classify([cmd])
            should_run = confirm_run([cmd], is_dangerous=dr, danger_level=dl, dry=dry, yes=yes)
            if not should_run:
                console.print(f"  [dim]Stopped at step {i}.[/dim]\n")
                break
            show_running([cmd])
            exit_code = run_commands([cmd])
            show_success(exit_code)
            if exit_code != 0:
                console.print(f"  [red]Step {i} failed. Stopping.[/red]\n")
                break
        if not no_audit:
            log_command(request_str, commands, exit_code, is_dangerous, True, dry)
        sys.exit(exit_code)

    should_run = confirm_run(
        commands=commands,
        is_dangerous=is_dangerous,
        danger_level=danger_level,
        dry=dry,
        yes=yes,
    )

    exit_code = 0
    if should_run:
        show_running(commands)
        exit_code = run_commands(commands)
        show_success(exit_code)

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
