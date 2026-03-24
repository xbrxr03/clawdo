"""
safety.py — Danger classification for shell commands.
Tier 1: instant pattern match (no LLM needed).
Returns (is_dangerous, reason, tier).
"""
from __future__ import annotations

import re

# Each entry: (regex_pattern, human_readable_reason)
DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    # Recursive deletion
    (r'\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*)\b', "recursively and forcefully deletes files"),
    (r'\brm\s+-rf\b', "permanently deletes files recursively"),
    (r'\brm\s+-fr\b', "permanently deletes files recursively"),
    (r'\bsudo\s+rm\b', "deletes files as root"),
    # Disk / filesystem operations
    (r'\bdd\b.*\bof=', "writes directly to a device (can destroy disk)"),
    (r'\bmkfs\b', "formats a filesystem (data loss)"),
    (r'\bfdisk\b', "modifies partition table"),
    (r'\bparted\b', "modifies partition table"),
    (r'\bwipefs\b', "wipes filesystem signatures"),
    # Write to block devices
    (r'\b>\s*/dev/sd[a-z]', "writes to a block device"),
    (r'\b>\s*/dev/nvme', "writes to an NVMe device"),
    (r'\b>\s*/dev/disk', "writes to a disk device"),
    # Dangerous permissions
    (r'\bchmod\s+777\b', "makes files world-writable (security risk)"),
    (r'\bchmod\s+-R\s+777\b', "recursively makes all files world-writable"),
    (r'\bchmod\s+a\+w\b', "grants write access to all users"),
    # Shred / secure erase
    (r'\bshred\b', "irreversibly destroys file data"),
    (r'\bwipe\b', "irreversibly wipes files"),
    (r'\bsecure-delete\b', "irreversibly deletes files"),
    # Force kill processes
    (r'\bkill\s+-9\b', "force-kills a process without cleanup"),
    (r'\bpkill\s+-9\b', "force-kills processes by name"),
    (r'\bkillall\s+-9\b', "force-kills all matching processes"),
    # System management
    (r'\bcrontab\s+-r\b', "deletes ALL scheduled cron jobs"),
    (r'\biptables\s+-F\b', "flushes ALL firewall rules"),
    (r'\bufw\s+--force\s+reset\b', "resets firewall to defaults"),
    (r'\bsudo\s+su\b', "escalates to root shell"),
    (r'\bsudo\s+-s\b', "opens root shell"),
    # Overwrite important files
    (r'>\s*/etc/passwd\b', "overwrites the system user database"),
    (r'>\s*/etc/shadow\b', "overwrites encrypted passwords"),
    (r'>\s*/etc/hosts\b', "overwrites the hosts file"),
    # Nuke home or root
    (r'\brm\b.*\b~/', "deletes files in home directory"),
    (r'\brm\b.*\b/home/', "deletes files in /home"),
    # Truncate
    (r'\btruncate\b.*--size\s+0\b', "truncates file to zero length"),
    (r'\btruncate\b.*-s\s+0\b', "truncates file to zero length"),
    # Disable services without confirmation
    (r'\bsystemctl\s+disable\b', "disables a system service"),
    (r'\bsystemctl\s+mask\b', "permanently disables a system service"),
]

# Patterns that are SO dangerous they require typing "yes" explicitly
CRITICAL_PATTERNS: list[tuple[str, str]] = [
    (r'\brm\s+-rf\s+/', "deletes from filesystem root — catastrophic"),
    (r'\bdd\b.*\bif=/dev/zero\b.*\bof=', "overwrites disk with zeros — irreversible"),
    (r'\bdd\b.*\bif=/dev/random\b.*\bof=', "overwrites disk with random data — irreversible"),
    (r'\bmkfs[\.\w]*\s+/dev/sd[a-z]\b', "formats an entire disk — destroys all data"),
    (r'\bshred\b.*-n\b', "secure-wipes files with multiple passes — irreversible"),
]


def classify(commands: list[str]) -> tuple[bool, str, str]:
    """
    Classify a list of commands for danger.

    Returns:
        (is_dangerous, reason, level)
        level: "safe" | "warn" | "critical"
    """
    full = " && ".join(commands)

    # Check critical first
    for pattern, reason in CRITICAL_PATTERNS:
        if re.search(pattern, full, re.IGNORECASE):
            return True, reason, "critical"

    # Then warn-level
    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, full, re.IGNORECASE):
            return True, reason, "warn"

    return False, "", "safe"


def is_safe_for_auto_yes(commands: list[str]) -> bool:
    """Return True only if the command is completely safe for --yes flag."""
    dangerous, _, _ = classify(commands)
    return not dangerous
