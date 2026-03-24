# claw-do

**Natural language → shell commands. Offline. Safe by default.**

```
$ claw-do "find all files larger than 1GB in my home directory"

  Generating command...

  ◆  Command
  ─────────────────────────────────────────────────────
  find ~/ -type f -size +1G 2>/dev/null
  ─────────────────────────────────────────────────────

  Run it? [Y/n]
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
- ✅ Memory in ClawOS mode — knows your project, git state, PINNED.md facts
- ✅ policyd integration — `rm -rf`, `dd`, `chmod 777`, `mkfs` auto-flagged
- ✅ Merkle-chained audit trail — every command logged with tamper-evident hash
- ✅ Standalone OR embedded — works without ClawOS, works better with it

---

## Installation

### Standalone (pip)

```bash
pip install claw-do
```

### As part of ClawOS

Already included. Access via:

```bash
claw do "compress all logs older than 7 days"
```

---

## Usage

```bash
# Basic
claw-do "find all files larger than 1GB"
claw-do "show what's using port 8080"
claw-do "set up a python venv and install requirements"
claw-do "compress logs older than 7 days and archive them"

# Flags
claw-do --dry "delete all .pyc files"       # show only, never run
claw-do --yes "list all running processes"  # skip confirm if safe
claw-do --model qwen2.5-coder:7b "..."      # override model
claw-do --no-context "list files"           # ignore workspace context
```

---

## How it works

```
Request: "archive logs older than 7 days"
         │
         ▼
Context collector (cwd, git, recent files, PINNED.md)
         │
         ▼
Ollama (qwen2.5:7b, temperature=0.1)
         │
         ▼
Safety classifier (pattern match — no LLM needed)
         │
         ▼ safe → [Y/n]   dangerous → [y/N]   critical → type "yes"
         │
         ▼
subprocess.run()  +  Merkle audit log
```

### Safety tiers

**Tier 1 — Pattern match** (instant, no LLM):
- Hardcoded patterns for `rm -rf`, `dd`, `mkfs`, `chmod 777`, `kill -9`, etc.
- Safe commands: `[Y/n]` (default YES)
- Dangerous commands: `[y/N]` (default NO)
- Critical commands (`rm -rf /`, `dd ... /dev/sda`): must type `yes` in full

**The `--yes` flag never bypasses dangerous command protection. Ever.**

---

## ClawOS integration

When running inside ClawOS:
- Reads `PINNED.md` for workspace facts → more contextually accurate commands
- Checks `policyd` before showing the command — blocks before asking the user
- All commands logged to `~/clawos/logs/claw-do-audit.jsonl` with Merkle chain

```
$ claw do "backup my project"

  Generating command...

  ◆  Context  jarvis_default · git:main · ~/clawos
  ◆  Command
  ─────────────────────────────────────────────────────
  tar -czf ~/backups/clawos-2026-03-24.tar.gz ~/clawos --exclude=.git
  ─────────────────────────────────────────────────────

  Run it? [Y/n]
```

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai) running locally
- A model pulled: `ollama pull qwen2.5:7b`

Default model: `qwen2.5:7b`. Falls back to any available Ollama model.

---

## License

MIT — part of the [ClawOS](https://github.com/xbrxr03/clawos) ecosystem.
