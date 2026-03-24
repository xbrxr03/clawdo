"""
runner.py — Command execution and audit logging.
Runs commands via subprocess. Optionally logs to ClawOS audit trail.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path


def run_commands(commands: list[str], cwd: str | None = None) -> int:
    """
    Run a list of commands sequentially in the current shell.
    Stops at first non-zero exit code.

    Returns:
        Final exit code (0 = all succeeded).
    """
    for cmd in commands:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd or os.getcwd(),
        )
        if result.returncode != 0:
            return result.returncode
    return 0


# ── Audit logging ──────────────────────────────────────────────────────────────

def _audit_log_path() -> Path:
    """Return the claw-do audit log path."""
    # ClawOS mode: use the standard log dir
    clawos_logs = Path.home() / "clawos" / "logs"
    if clawos_logs.exists():
        return clawos_logs / "claw-do-audit.jsonl"
    # Standalone mode: ~/.claw-do/audit.jsonl
    standalone = Path.home() / ".claw-do"
    standalone.mkdir(exist_ok=True)
    return standalone / "audit.jsonl"


def _read_last_hash(log_path: Path) -> str:
    """Read the last entry_hash from the audit log for Merkle chaining."""
    if not log_path.exists():
        return "0" * 64
    try:
        lines = log_path.read_text().strip().splitlines()
        if lines:
            last = json.loads(lines[-1])
            return last.get("entry_hash", "0" * 64)
    except Exception:
        pass
    return "0" * 64


def _make_entry_hash(prev_hash: str, entry_data: dict) -> str:
    """Compute SHA-256 of prev_hash + sorted entry payload."""
    payload = prev_hash + json.dumps(entry_data, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def log_command(
    request: str,
    commands: list[str],
    exit_code: int,
    is_dangerous: bool,
    approved: bool,
    dry: bool,
) -> str:
    """
    Append a Merkle-chained entry to the audit log.

    Returns:
        Path to the log file as a string.
    """
    log_path = _audit_log_path()
    prev_hash = _read_last_hash(log_path)

    entry_data = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "request": request,
        "commands": commands,
        "exit_code": exit_code,
        "is_dangerous": is_dangerous,
        "approved": approved,
        "dry_run": dry,
        "cwd": os.getcwd(),
        "user": os.environ.get("USER") or os.environ.get("USERNAME", "unknown"),
    }

    entry_hash = _make_entry_hash(prev_hash, entry_data)
    log_entry = {**entry_data, "prev_hash": prev_hash, "entry_hash": entry_hash}

    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass  # Audit failure should never crash the tool

    return str(log_path)
