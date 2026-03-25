# claw-do

**Natural language → shell commands. Offline. Safe by default.**
```
$ claw-do "find all files larger than 1GB in my home directory"

  Generating command...

  ◆  Command
  ───────────────────────────────────────────────────────
  find ~/ -type f -size +1G 2>/dev/null
  ───────────────────────────────────────────────────────

  Run it? [y/n] (y):
```

No API keys. No cloud. Runs entirely on your machine via [Ollama](https://ollama.ai).

---

## Why claw-do beats everything else

| Tool | Fatal flaw |
|------|-----------|
| `pls` | Requires OpenAI/Anthropic API key |
| `spren` | Rust binary, no memory, no safety layer |
| `whai` | Needs API key, no memory |
| `cmdh` | Bare-bones, no safety |
| `shell-ai` | Runs commands directly, no policy gate |
| `ShellGPT` | Not optimized for local models |

**What claw-do has that none of them do:**
- ✅ 100% offline — Ollama only, no API key ever
- ✅ **Dangerous commands default to NO** — the key UX difference
- ✅ Shell history context — knows what you've been doing
- ✅ `--history` — see every command you've run with approval status
- ✅ `--undo` — automatically infers and runs the inverse command
- ✅ `--explain` — plain English description before you run anything
- ✅ `--dry` — shows exactly which files would be affected, never runs
- ✅ `--step` — confirm each step of a multi-step plan individually
- ✅ Merkle-chained audit trail — every command logged with tamper-evident hash
- ✅ ClawOS integration — `/do` command inside the clawos REPL

---

## Installation

### Standalone
```bash
pip install click ollama rich gitpython json-repair
git clone https://github.com/xbrxr03/clawdo
cd clawdo
mkdir -p ~/bin
cat > ~/bin/claw-do << 'BINEOF'
#!/bin/bash
export PYTHONPATH=$HOME/clawdo
python3 $HOME/clawdo/claw_do/cli.py "$@"
BINEOF
chmod +x ~/bin/claw-do
```

### As part of ClawOS

Already included. Access via `/do` inside the clawos REPL:
```
clawos
you › /do compress all logs older than 7 days
```

---

## Usage
```bash
# Basic
claw-do "find all files larger than 1GB"
claw-do "show what's using port 8080"
claw-do "compress logs older than 7 days and archive them"
claw-do "rename testfile.txt to oldfile.txt"

# Safety
claw-do "delete all node_modules recursively"   # defaults to N
claw-do --dry "delete all .pyc files"           # shows affected files, never runs
claw-do --yes "list all running processes"      # skip confirm for safe commands only

# Understanding
claw-do --explain "find . -name '*.log' -mtime +7 -exec gzip {} \;"
claw-do --step "compress logs and move to archive"

# History & undo
claw-do --history
claw-do --undo

# Advanced
claw-do --model qwen2.5-coder:7b "set up a python venv"
claw-do --no-context "list files"
```

---

## How it works
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

**`--yes` never bypasses dangerous command protection. Ever.**

---

## All flags

| Flag | What it does |
|------|-------------|
| `--dry` | Show command + affected files, never run |
| `--yes` / `-y` | Skip confirmation for safe commands only |
| `--history` | Show last 10 commands with timestamp and approval status |
| `--undo` | Infer and offer to run the inverse of the last command |
| `--explain` | Plain English explanation of the command |
| `--step` | Confirm each step of a multi-step plan individually |
| `--model` / `-m` | Override the Ollama model |
| `--no-context` | Don't inject workspace/git/history context |
| `--no-audit` | Skip writing to the audit log |
| `--ollama-host` | Override Ollama server URL (default: localhost:11434) |

---

## ClawOS integration

When running inside ClawOS, access via `/do` in the REPL:
```
clawos
you › /do backup my project
  ◆  Context  jarvis_default · git:main · ~/clawos
  ◆  Command
  ─────────────────────────────────────────────────────
  tar -czf ~/backups/clawos-2026-03-25.tar.gz ~/clawos --exclude=.git
  ─────────────────────────────────────────────────────
  Run it? [y/n] (y):
```

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai) running locally
- `ollama pull qwen2.5:7b`

---

## Part of ClawOS

claw-do is a standalone tool and part of [ClawOS](https://github.com/xbrxr03/clawos) — an agent-native Linux OS that runs offline with no API keys.

---

## License

MIT
