"""The extractor must run as a plain completion call, never as an agent.

`opencode run` gives the model bash, read, grep, webfetch, write and edit by
default. The tool-use audit (papers/studies/tool_use_audit.json) found the
shipped extractor running its own scripts and the title-only study model
fetching papers from the web. An extractor with tools has more input than its
prompt says, so every grounding number it produces is measured against the
wrong source. These tests lock the fix: they fail if a later edit restores
tools or stops treating an executed tool as a failure.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import stages.s09_cards as s09  # noqa: E402

AGENT_TOOLS = ("bash", "read", "write", "edit", "grep", "glob", "list",
               "webfetch", "websearch", "task", "patch")


def test_every_agent_tool_is_denied():
    cfg = json.loads(s09._no_tools_env()["OPENCODE_CONFIG_CONTENT"])
    for t in AGENT_TOOLS:
        assert cfg["tools"].get(t) is False, f"tool {t!r} is not switched off"


class _Done:
    def __init__(self, parts):
        self.returncode = 0
        self.stdout = "\n".join(json.dumps(p) for p in parts)
        self.stderr = ""


def _patch_run(monkeypatch, parts, seen):
    def fake_run(cmd, **kw):
        seen.append((cmd, kw))
        return _Done(parts)
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(s09, "_opencode_exe", lambda: "opencode")


def test_call_is_pure_and_tool_free(monkeypatch):
    seen = []
    _patch_run(monkeypatch, [{"type": "text", "part": {"type": "text", "text": "[]"}}], seen)
    try:
        s09.call_opencode("p", attempts=1)
    except Exception:
        pass  # the reply shape is not under test here, only the invocation
    assert seen, "call_opencode never invoked the CLI"
    cmd, kw = seen[0]
    assert "--pure" in cmd
    assert kw.get("stdin") is subprocess.DEVNULL
    cfg = json.loads(kw["env"]["OPENCODE_CONFIG_CONTENT"])
    assert all(cfg["tools"][t] is False for t in AGENT_TOOLS)


def test_executed_tool_fails_the_call(monkeypatch):
    tool_part = {"type": "tool_use",
                 "part": {"type": "tool", "tool": "webfetch",
                          "state": {"status": "completed"}}}
    text_part = {"type": "text", "part": {"type": "text", "text": "[]"}}
    _patch_run(monkeypatch, [tool_part, text_part], [])
    with pytest.raises(Exception, match="tool"):
        s09.call_opencode("p", attempts=1)
