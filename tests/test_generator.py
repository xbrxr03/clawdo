"""
test_generator.py — Tests for command generation and response parsing.
Mocks Ollama so no live model needed.
Run: pytest tests/test_generator.py -v
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from claw_do.generator import _clean_raw_output, _parse_response


# ── _clean_raw_output ──────────────────────────────────────────────────────────

class TestCleanRawOutput:
    def test_plain_command(self):
        assert _clean_raw_output("ls -la") == "ls -la"

    def test_strips_backtick_fences(self):
        raw = "```\nls -la\n```"
        assert _clean_raw_output(raw) == "ls -la"

    def test_strips_bash_fence(self):
        raw = "```bash\nls -la\n```"
        assert _clean_raw_output(raw) == "ls -la"

    def test_strips_sh_fence(self):
        raw = "```sh\nfind . -name '*.py'\n```"
        assert _clean_raw_output(raw) == "find . -name '*.py'"

    def test_strips_inline_backticks(self):
        raw = "`ls -la`"
        assert _clean_raw_output(raw) == "ls -la"

    def test_strips_bash_prefix(self):
        raw = "bash\nls -la"
        assert _clean_raw_output(raw) == "ls -la"

    def test_strips_sh_prefix(self):
        raw = "sh\nls -la"
        assert _clean_raw_output(raw) == "ls -la"

    def test_handles_whitespace(self):
        assert _clean_raw_output("  ls -la  ") == "ls -la"


# ── _parse_response ────────────────────────────────────────────────────────────

class TestParseResponse:
    def test_single_command(self):
        result = _parse_response("ls -la")
        assert result == ["ls -la"]

    def test_json_array(self):
        raw = '["find . -name logs", "gzip /var/log/app.log"]'
        result = _parse_response(raw)
        assert result == ["find . -name logs", "gzip /var/log/app.log"]

    def test_single_item_array(self):
        raw = '["ls -la"]'
        result = _parse_response(raw)
        assert result == ["ls -la"]

    def test_strips_markdown_before_parse(self):
        raw = "```bash\nls -la\n```"
        result = _parse_response(raw)
        assert result == ["ls -la"]

    def test_array_with_markdown(self):
        raw = '```\n["cmd1", "cmd2"]\n```'
        result = _parse_response(raw)
        assert result == ["cmd1", "cmd2"]

    def test_empty_string(self):
        result = _parse_response("")
        assert result == []

    def test_empty_after_clean(self):
        result = _parse_response("```\n\n```")
        assert result == []

    def test_multi_word_command(self):
        result = _parse_response("find ~/ -type f -size +1G 2>/dev/null")
        assert result == ["find ~/ -type f -size +1G 2>/dev/null"]

    def test_filters_empty_strings_in_array(self):
        raw = '["cmd1", "", "cmd2"]'
        result = _parse_response(raw)
        assert "" not in result
        assert "cmd1" in result
        assert "cmd2" in result


# ── generate_command (parsing pipeline only — no live Ollama needed) ──────────

class TestGenerateCommand:
    def test_parsing_pipeline_single(self):
        """_parse_response returns a list for a plain command."""
        result = _parse_response("ls -la")
        assert isinstance(result, list)
        assert result == ["ls -la"]

    def test_parsing_pipeline_multi(self):
        """_parse_response handles multi-step JSON arrays."""
        raw = '["step1", "step2", "step3"]'
        result = _parse_response(raw)
        assert len(result) == 3
        assert result[0] == "step1"

    def test_import_error_raises_runtime_error(self):
        """If ollama not installed, generate_command raises RuntimeError."""
        import sys
        original = sys.modules.get("ollama")
        sys.modules["ollama"] = None  # type: ignore
        try:
            import importlib
            import claw_do.generator as gen_mod
            importlib.reload(gen_mod)
            with pytest.raises((RuntimeError, ImportError, TypeError)):
                gen_mod.generate_command("test")
        finally:
            if original is not None:
                sys.modules["ollama"] = original
            elif "ollama" in sys.modules:
                del sys.modules["ollama"]
            # Reload back to working state
            import importlib
            import claw_do.generator
            importlib.reload(claw_do.generator)
