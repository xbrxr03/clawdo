<div align="center">

# 🐾 Clawdo

### Natural language → shell commands. Offline. Safe by default.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_AI-000000?logo=ollama&logoColor=white)](https://ollama.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

---

## Demo

![Demo: typing "list all python files" and getting back find . -name "*.py"](./docs/demo.png)

```
$ clawdo "find all files larger than 1GB in my home directory"

  Generating command...

  ◆  Command
  ───────────────────────────────────────────────────────
  find ~/ -type f -size +1G 2>/dev/null
  ───────────────────────────────────────────────────────

  Run it? [y/n] (y):
```

No API keys. No cloud. Runs entirely on your machine via [Ollama](https://ollama.ai).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| AI Backend | [Ollama](https://ollama.ai) (local LLM inference) |
| Default Model | `qwen2.5:7b` (auto-detects installed models) |
| CLI Framework | [Click](https://click.palletsprojects.com/) |
| Terminal Rendering | [Rich](https://rich.readthedocs.io/) |
| Shell Execution | `subprocess.run` |
| Git Integration | [GitPython](https://gitpython.readthedocs.io/) |
| JSON Repair | [json-repair](https://github.com/1rgs/json-repair) (graceful LLM output parsing) |

**Dependencies:** `click`, `ollama`, `rich`, `gitpython`, `json-repair`

---

## Safety Features

Clawdo is built around a core principle: **dangerous commands default to NO**. The safety system uses deterministic pattern matching — no LLM calls needed for classification, so it's fast, auditable, and never hallucinates.

### Three-Tier Danger Classification

Every generated command is classified before execution:

| Tier | Behavior | Examples |
|------|----------|---------|
| **Safe** | Default **Yes** — press Enter to run | `ls`, `cat`, `find`, `git status`, `du` |
| **Warn** | Default **No** — must type `y` to confirm | `rm -rf`, `chmod 777`, `kill -9`, `sudo rm` |
| **Critical** | Must type `yes` in full — no shortcuts | `rm -rf /`, `dd if=/dev/zero of=/dev/sda`, `mkfs` |

**`--yes` never bypasses dangerous command protection. Ever.** Safe commands auto-run; dangerous ones always require explicit confirmation.

### Restricted Command Blocklist

The pattern-based blocklist catches 40+ dangerous patterns across these categories:

- **Recursive/forced deletion** — `rm -rf`, `sudo rm`
- **Disk destruction** — `dd`, `mkfs`, `fdisk`, `parted`, `wipefs`
- **Block device writes** — redirecting to `/dev/sd*`, `/dev/nvme*`
- **Dangerous permissions** — `chmod 777`, `chmod a+w`
- **Irreversible destruction** — `shred`, `wipe`, `secure-delete`
- **Force kills** — `kill -9`, `pkill -9`, `killall -9`
- **System management** — `crontab -r`, `iptables -F`, `sudo su`
- **Critical file overwrites** — writing to `/etc/passwd`, `/etc/shadow`, `/etc/hosts`
- **Service disruption** — `systemctl disable`, `systemctl mask`

Multi-step plans are classified as dangerous if **any** step matches. See [`claw_do/safety.py`](claw_do/safety.py) for the full pattern list.

### Dry-Run Mode (`--dry`)

Shows exactly which files would be affected — **never runs the command**. Supports:
- `find ... -exec` commands (runs `find` without `-exec` to preview matches)
- `rm`/`mv`/`cp` with globs (expands the glob to show target files)

```
$ clawdo --dry "delete all .pyc files"

  ◆  Would affect 3 file(s)
  ───────────────────────────────────────────────────────
  ./src/__pycache__/main.cpython-312.pyc
  ./tests/__pycache__/test_main.cpython-312.pyc
  ./build/__pycache__/app.cpython-312.pyc
  ───────────────────────────────────────────────────────

  --dry: not running
```

### Confirmation Prompts

- **Safe commands:** `Run it? [Y/n]` — Enter to run
- **Dangerous commands:** `Are you sure? [y/N]` — must type `y`
- **Critical commands:** `Type yes to confirm` — must type `yes` in full
- **Multi-step plans (`--step`):** Confirm each step individually

### Merkle-Chained Audit Trail

Every command — approved or rejected, run or dry-run — is logged to a tamper-evident JSONL audit trail:

```jsonl
{"timestamp":"2026-05-19T00:10:00Z","request":"delete old logs","commands":["find /var/log -name '*.log' -mtime +7 -exec rm {} \\;"],"exit_code":0,"is_dangerous":true,"approved":true,"dry_run":false,"prev_hash":"0a1b2c...","entry_hash":"3d4e5f..."}
```

Each entry chains to the previous via `prev_hash` → `entry_hash` (SHA-256 of previous hash + entry data). Any tampering with the log breaks the chain. Log location:
- **ClawOS mode:** `~/clawos/logs/claw-do-audit.jsonl`
- **Standalone:** `~/.claw-do/audit.jsonl`

View history with `clawdo --history`.

---

## How to Run

### Prerequisites

1. **Python 3.10+**
2. **Ollama** running locally — [install guide](https://ollama.ai)
3. **A model** pulled in Ollama:
   ```bash
   ollama pull qwen2.5:7b
   ```

### Install

```bash
pip install click ollama rich gitpython json-repair
git clone https://github.com/xbrxr03/clawdo.git
cd clawdo
```

### Set Up the CLI

```bash
mkdir -p ~/bin
cat > ~/bin/claw-do << 'BINEOF'
#!/bin/bash
export PYTHONPATH=$HOME/clawdo
python3 $HOME/clawdo/claw_do/cli.py "$@"
BINEOF
chmod +x ~/bin/claw-do
```

Make sure `~/bin` is in your `$PATH`.

### Run

```bash
# Basic usage
clawdo "find all files larger than 1GB"
clawdo "show what's using port 8080"
clawdo "compress logs older than 7 days and archive them"

# Safety first
clawdo "delete all node_modules recursively"   # defaults to N
clawdo --dry "delete all .pyc files"           # preview only, never runs
clawdo --yes "list all running processes"      # auto-confirm safe commands only

# Understand before running
clawdo --explain "find . -name '*.log' -mtime +7 -exec gzip {} \;"
clawdo --step "compress logs and move to archive"

# History & undo
clawdo --history
clawdo --undo

# Advanced
clawdo --model qwen2.5-coder:7b "set up a python venv"
clawdo --no-context "list files"
```

### ClawOS Integration

Already included. Access via `/do` inside the ClawOS REPL:
```
clawos
you › /do backup my project
  ◆  Context  jarvis_default · git:main · ~/clawos
  ◆  Command
  ───────────────────────────────────────────────────────
  tar -czf ~/backups/clawos-2026-03-25.tar.gz ~/clawos --exclude=.git
  ───────────────────────────────────────────────────────
  Run it? [y/n] (y):
```

---

## All Flags

| Flag | What it does |
|------|-------------|
| `--dry` | Show command + affected files, never run |
| `--yes` / `-y` | Skip confirmation for **safe** commands only |
| `--history` | Show last 10 commands with timestamp and approval status |
| `--undo` | Infer and offer to run the inverse of the last command |
| `--explain` | Plain English explanation of the generated command |
| `--step` | Confirm each step of a multi-step plan individually |
| `--model` / `-m` | Override the Ollama model |
| `--no-context` | Don't inject workspace/git/history context |
| `--no-audit` | Skip writing to the audit log |
| `--ollama-host` | Override Ollama server URL (default: localhost:11434) |

---

## How It Works

```
Request: "archive logs older than 7 days"
         │
         ▼
Context collector
  · current directory
  · git branch + status
  · recent files
  · last 5 shell commands (bash history)
  · PINNED.md workspace facts (ClawOS mode)
         │
         ▼
Ollama (qwen2.5:7b, temperature=0.1)
         │
         ▼
Safety classifier (pattern match — no LLM needed)
  · Tier 1: safe       → [y/n] default YES
  · Tier 2: dangerous  → [y/N] default NO
  · Tier 3: critical   → must type "yes"
         │
         ▼
subprocess.run() + Merkle-chained audit log
```

---

## What This Demonstrates

- **Natural language → shell commands** — translate intent into correct, contextual CLI commands using local LLMs
- **CLI design** — a polished terminal UX with Rich rendering, progressive disclosure, and sensible defaults
- **Safety engineering** — three-tier classification, restricted command blocklist, confirmation gates that can't be bypassed with `--yes`
- **Audit integrity** — Merkle-chained append-only log with SHA-256 hash linking, tamper-evident by design
- **Local AI** — zero cloud dependency. Ollama runs on your hardware, your data never leaves your machine
- **Context-aware generation** — injects cwd, git state, recent files, and shell history so commands are specific, not generic

---

## Part of ClawOS

Clawdo is a standalone tool and part of [ClawOS](https://github.com/xbrxr03/clawos) — an agent-native Linux OS that runs offline with no API keys.

---

## License

MIT