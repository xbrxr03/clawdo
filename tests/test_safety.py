"""
test_safety.py — Tests for the danger classification system.
These are the most important tests in the project.
Run: pytest tests/test_safety.py -v
"""
import pytest
from claw_do.safety import classify, is_safe_for_auto_yes


# ── Safe commands ──────────────────────────────────────────────────────────────

SAFE_COMMANDS = [
    ["ls -la"],
    ["df -h"],
    ["find ~/ -type f -size +1G 2>/dev/null"],
    ["git status"],
    ["cat README.md"],
    ["echo hello"],
    ["pwd"],
    ["ps aux"],
    ["top -bn1"],
    ["curl -s https://example.com"],
    ["tar -czf backup.tar.gz ~/projects"],
    ["pip install requests"],
    ["python3 -m pytest"],
    ["grep -r 'TODO' ."],
    ["find . -name '*.pyc' -delete"],
    ["chmod 644 myfile.txt"],
    ["chmod 755 myscript.sh"],
    ["cp file.txt file.bak"],
    ["mv old.txt new.txt"],
    ["mkdir -p /tmp/test"],
    ["systemctl status nginx"],
    ["journalctl -n 50"],
    ["htop"],
    ["du -sh *"],
]


@pytest.mark.parametrize("commands", SAFE_COMMANDS)
def test_safe_commands_pass(commands):
    dangerous, reason, level = classify(commands)
    assert not dangerous, f"False positive: {commands!r} flagged as dangerous: {reason}"
    assert level == "safe"
    assert is_safe_for_auto_yes(commands)


# ── Warn-level dangerous commands ─────────────────────────────────────────────

WARN_DANGEROUS = [
    (["rm -rf /tmp/test"], "rm -rf"),
    (["rm -fr ~/Downloads/old"], "rm -fr"),
    (["sudo rm /etc/config"], "sudo rm"),
    (["mkfs.ext4 /dev/sdb1"], "mkfs"),
    (["chmod 777 /var/www"], "chmod 777"),
    (["chmod -R 777 ."], "chmod -R 777"),
    (["shred -u secrets.txt"], "shred"),
    (["kill -9 1234"], "kill -9"),
    (["pkill -9 python"], "pkill -9"),
    (["killall -9 nginx"], "killall -9"),
    (["crontab -r"], "crontab -r"),
    (["iptables -F"], "iptables -F"),
    (["sudo su -"], "sudo su"),
    (["sudo -s"], "sudo -s"),
    (["truncate -s 0 important.log"], "truncate"),
    (["systemctl disable ssh"], "systemctl disable"),
    (["systemctl mask cron"], "systemctl mask"),
    (["dd if=/dev/urandom of=/dev/sda bs=1M count=10"], "dd to device"),
    (["find . -name 'node_modules' -type d -prune -exec rm -rf '{}' +"], "rm -rf"),
    (["echo '' > /etc/hosts"], "/etc/hosts"),
    (["chmod a+w /usr/bin"], "chmod a+w"),
]


@pytest.mark.parametrize("commands, description", WARN_DANGEROUS)
def test_dangerous_commands_detected(commands, description):
    dangerous, reason, level = classify(commands)
    assert dangerous, f"Missed dangerous command ({description}): {commands!r}"
    assert level in ("warn", "critical")
    assert not is_safe_for_auto_yes(commands), f"--yes should not bypass: {commands!r}"


# ── Critical-level commands ────────────────────────────────────────────────────

CRITICAL_COMMANDS = [
    (["rm -rf /"], "rm -rf /"),
    (["rm -rf /*"], "rm -rf /*"),
    (["dd if=/dev/zero of=/dev/sda"], "dd zero to disk"),
    (["dd if=/dev/random of=/dev/sda bs=1M"], "dd random to disk"),
    (["mkfs.ext4 /dev/sda"], "mkfs whole disk"),
    (["shred -n 3 /dev/sdb"], "shred with passes"),
]


@pytest.mark.parametrize("commands, description", CRITICAL_COMMANDS)
def test_critical_commands_detected(commands, description):
    dangerous, reason, level = classify(commands)
    assert dangerous, f"Missed critical command ({description}): {commands!r}"
    assert level == "critical", f"Expected critical, got {level}: {commands!r}"


# ── Multi-step plan safety ─────────────────────────────────────────────────────

def test_dangerous_in_multi_step_plan():
    """A dangerous command anywhere in a plan flags the whole plan."""
    commands = [
        "find /var/log -name '*.log' -mtime +7",
        "rm -rf /var/log/old/",  # dangerous step
        "echo done",
    ]
    dangerous, reason, level = classify(commands)
    assert dangerous
    assert level in ("warn", "critical")


def test_safe_multi_step_plan():
    commands = [
        "find /var/log -name '*.log' -mtime +7 -exec gzip {} \\;",
        "find /var/log -name '*.log.gz' -mtime +7 -exec mv {} /var/archive/ \\;",
    ]
    dangerous, reason, level = classify(commands)
    assert not dangerous
    assert level == "safe"


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_rm_without_rf_is_safe():
    """Plain 'rm file.txt' should not be flagged."""
    dangerous, _, _ = classify(["rm myfile.txt"])
    assert not dangerous


def test_chmod_safe_permissions():
    """chmod 644 or 755 should not be flagged."""
    assert not classify(["chmod 644 file.txt"])[0]
    assert not classify(["chmod 755 script.sh"])[0]
    assert not classify(["chmod +x script.sh"])[0]


def test_yes_never_bypasses_dangerous():
    """is_safe_for_auto_yes must return False for any dangerous command."""
    assert not is_safe_for_auto_yes(["rm -rf /"])
    assert not is_safe_for_auto_yes(["chmod 777 /etc"])
    assert not is_safe_for_auto_yes(["dd if=/dev/zero of=/dev/sda"])


def test_empty_commands():
    """Empty list should be safe."""
    dangerous, _, level = classify([])
    assert not dangerous
    assert level == "safe"
