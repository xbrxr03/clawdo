from __future__ import annotations
import json
try:
    from json_repair import repair_json
    HAS_JSON_REPAIR = True
except ImportError:
    HAS_JSON_REPAIR = False

from claw_do.context import collect_context, format_context

SYSTEM_PROMPT = """You are a shell command generator. Output ONLY a single shell command as plain text.

Rules:
- Output the command as plain text. Example: du -sh *
- NO explanation, NO markdown, NO backticks, NO JSON for single commands
- Only use a JSON array ["cmd1","cmd2"] if the task requires multiple SEPARATE commands
- NEVER put a single command's flags or arguments as separate array items
- Use context to make commands specific (correct paths, filenames, etc.)
- Never invent paths not in context"""


def _detect_ollama_model() -> str:
    try:
        import ollama
        models = ollama.list()
        names = [m.model for m in models.models] if hasattr(models, "models") else []
        preferred = ["qwen2.5:7b","qwen2.5-coder:7b","qwen2.5:3b","llama3.1:8b","mistral:7b"]
        for p in preferred:
            if p in names:
                return p
        if names:
            return names[0]
    except Exception:
        pass
    return "qwen2.5:7b"


def _clean_raw_output(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        raw = "\n".join(inner).strip()
    if raw.startswith("`") and raw.endswith("`"):
        raw = raw[1:-1].strip()
    if raw.startswith("bash\n"):
        raw = raw[5:].strip()
    if raw.startswith("sh\n"):
        raw = raw[3:].strip()
    return raw


def _parse_response(raw: str) -> list[str]:
    clean = _clean_raw_output(raw)
    if clean.startswith("["):
        try:
            parsed = json.loads(clean)
            if isinstance(parsed, list) and all(isinstance(c, str) for c in parsed):
                # Safety check: if it looks like a split command, rejoin it
                if len(parsed) <= 3 and all(" " not in c and not c.startswith("/") for c in parsed):
                    return [" ".join(parsed)]
                return [c.strip() for c in parsed if c.strip()]
        except json.JSONDecodeError:
            if HAS_JSON_REPAIR:
                try:
                    parsed = json.loads(repair_json(clean))
                    if isinstance(parsed, list):
                        return [c.strip() for c in parsed if c.strip()]
                except Exception:
                    pass
    return [clean] if clean else []


def generate_command(
    request: str,
    model: str | None = None,
    extra_context: dict | None = None,
    clawos_mode: bool = False,
    ollama_host: str = "http://localhost:11434",
) -> list[str]:
    try:
        import ollama as _ollama
    except ImportError:
        raise RuntimeError("ollama Python package not installed. Run: pip install ollama")

    ctx = collect_context(clawos_mode=clawos_mode)
    if extra_context:
        ctx.update(extra_context)
    ctx_str = format_context(ctx)
    resolved_model = model or _detect_ollama_model()

    user_message = f"Context:\n{ctx_str}\n\nRequest: {request}"

    try:
        client = _ollama.Client(host=ollama_host)
        response = client.chat(
            model=resolved_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            options={"temperature": 0.1, "num_predict": 256},
        )
        raw = response["message"]["content"].strip()
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}") from e

    commands = _parse_response(raw)
    if not commands:
        raise RuntimeError(f"Model returned empty response. Raw: {raw!r}")
    return commands
