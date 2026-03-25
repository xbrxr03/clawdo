"""
renderer.py — Terminal UI for claw-do.
Uses rich for all output. Never calls print() directly.
"""
from __future__ import annotations

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.text import Text

console = Console(force_terminal=True)


def _rule() -> str:
    return "  " + "─" * 53


def show_spinner_start(message: str = "Thinking...") -> None:
    """Print a simple waiting indicator (no live spinner to keep it simple)."""
    console.print(f"\n  [dim]{message}[/dim]")


def show_commands(
    commands: list[str],
    is_dangerous: bool,
    danger_reason: str,
    danger_level: str,  # "safe" | "warn" | "critical"
    context_label: str | None = None,
) -> None:
    """Render the command box with optional danger warning."""
    console.print()

    # Context pill (ClawOS mode)
    if context_label:
        console.print(f"  [bold blue]◆[/bold blue]  [dim]Context[/dim]  {context_label}")

    # Header
    if len(commands) > 1:
        title = f"Plan ({len(commands)} steps)"
    else:
        title = "Command"
    console.print(f"  [bold blue]◆[/bold blue]  [bold]{title}[/bold]")

    # Command box
    console.print(_rule())
    for i, cmd in enumerate(commands, 1):
        if len(commands) > 1:
            console.print(f"  [dim]{i}.[/dim] [cyan]{cmd}[/cyan]")
        else:
            console.print(f"  [cyan]{cmd}[/cyan]")
    console.print(_rule())

    # Danger warning
    if is_dangerous:
        if danger_level == "critical":
            console.print(
                f"  [bold red]✗  CRITICAL[/bold red] [red]— {danger_reason}[/red]"
            )
        else:
            console.print(
                f"  [bold yellow]⚠  Destructive[/bold yellow] [yellow]— {danger_reason}[/yellow]"
            )


def confirm_run(
    commands: list[str],
    is_dangerous: bool,
    danger_level: str,
    dry: bool,
    yes: bool,
) -> bool:
    """
    Ask for confirmation. Returns True if the command should run.

    Confirmation logic:
      - safe + --yes        → auto-run (True)
      - safe + no flags     → "Run it? [Y/n]"  (default Y)
      - dangerous           → "Are you sure? [y/N]" (default N)
      - critical            → must type "yes" in full
      - --dry               → never runs (False)
    """
    if dry:
        console.print("\n  [dim]--dry: not running[/dim]\n")
        return False

    # --yes: only bypass for safe commands
    if yes and not is_dangerous:
        console.print()
        return True

    console.print()

    if danger_level == "critical":
        console.print(
            "  [bold red]This action may be irreversible.[/bold red] "
            "Type [bold]yes[/bold] to confirm, or anything else to cancel.\n"
        )
        answer = Prompt.ask("  Confirm", default="no")
        console.print()
        return answer.lower() == "yes"

    if is_dangerous:
        console.print("  [bold yellow]Type y to confirm, anything else cancels[/bold yellow]")
        answer = input("  Are you sure? [y/N] ").strip().lower()
        result = answer == "y"
    else:
        result = Confirm.ask("  Run it?", default=True)

    console.print()
    return result


def show_blocked(reason: str) -> None:
    """Display a policyd block message."""
    console.print(f"\n  [bold red]✗[/bold red]  [red]Blocked by policy — {reason}[/red]")
    console.print("  [dim]Run: claw policy grant shell.exec[/dim]\n")


def show_running(commands: list[str]) -> None:
    """Show 'Running...' indicator before execution."""
    if len(commands) == 1:
        console.print("  [dim]Running...[/dim]\n")
    else:
        console.print("  [dim]Running plan...[/dim]\n")


def show_success(return_code: int) -> None:
    """Show success or failure indicator after execution."""
    if return_code == 0:
        console.print("  [bold green]✓[/bold green]  [dim]Done[/dim]\n")
    else:
        console.print(
            f"  [bold red]✗[/bold red]  [dim]Command exited with code {return_code}[/dim]\n"
        )


def show_error(message: str) -> None:
    """Show an error message."""
    console.print(f"\n  [bold red]Error[/bold red]  {message}\n")


def show_audit_note(log_path: str) -> None:
    """Show a small audit log note (ClawOS mode)."""
    console.print(f"  [dim]Logged → {log_path}[/dim]\n")


def show_dry_preview(affected_files: list[str]) -> None:
    """Show files that would be affected in dry-run mode."""
    if not affected_files:
        return
    console.print(f"  [bold blue]◆[/bold blue]  [bold]Would affect {len(affected_files)} file(s)[/bold]")
    console.print("  " + "─" * 53)
    for f in affected_files:
        console.print(f"  [dim]{f}[/dim]")
    if len(affected_files) == 10:
        console.print("  [dim]... and possibly more[/dim]")
    console.print("  " + "─" * 53)


def show_dry_preview(affected_files: list[str]) -> None:
    """Show files that would be affected in dry-run mode."""
    if not affected_files:
        return
    console.print(f"  [bold blue]◆[/bold blue]  [bold]Would affect {len(affected_files)} file(s)[/bold]")
    console.print("  " + "─" * 53)
    for f in affected_files[:10]:
        console.print(f"  [dim]{f}[/dim]")
    if len(affected_files) == 10:
        console.print("  [dim]... and possibly more[/dim]")
    console.print("  " + "─" * 53)
