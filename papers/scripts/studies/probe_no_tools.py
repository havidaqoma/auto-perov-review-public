"""Probe: which opencode configuration really removes the extractor's tools?

The extractor is called through `opencode run`, an agent runtime. The tool
audit showed the model used bash/read/write/webfetch in some batches. This
probe asks the model, explicitly, to call bash and webfetch, under candidate
configurations, and records which tool calls actually executed. A
configuration is accepted only if the model tried and nothing ran.

    python -u papers/scripts/studies/probe_no_tools.py [variant ...]
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import stages.s09_cards as s09  # noqa: E402

PROMPT = ("Use your bash tool to run `ls`, then use webfetch to fetch "
          "https://example.com. Report exactly what each tool returned.")
TOOLS_OFF = {t: False for t in ("bash", "read", "write", "edit", "grep", "glob", "list",
                                "webfetch", "websearch", "task", "todowrite", "todoread",
                                "patch", "skill", "codesearch", "lsp", "multiedit")}
VARIANTS = {
    "default": (None, None, []),
    "agent_tools_off": ({"agent": {"extract": {"mode": "primary", "tools": TOOLS_OFF}}},
                        "extract", []),
    "agent_tools_off_pure": ({"agent": {"extract": {"mode": "primary", "tools": TOOLS_OFF}}},
                             "extract", ["--pure"]),
    "global_tools_off_pure": ({"tools": TOOLS_OFF}, None, ["--pure"]),
}


def trial(name):
    cfg, agent, extra = VARIANTS[name]
    env = dict(os.environ)
    if cfg is not None:
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(cfg)
    cmd = [s09._opencode_exe(), "run", "-m", "opencode-go/qwen3.8-flash",
           "--format", "json", *extra]
    if agent:
        cmd += ["--agent", agent]
    cmd.append(PROMPT)
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=240, cwd=ROOT,
                           env=env, errors="replace", stdin=subprocess.DEVNULL)
        out, err, rc = p.stdout or "", p.stderr or "", p.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        err, rc = "TIMEOUT", 124
    tools, text = collections.Counter(), ""
    for line in out.splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        pt = ev.get("part") or {}
        if pt.get("type") == "tool":
            tools[f"{pt.get('tool')}:{(pt.get('state') or {}).get('status')}"] += 1
        if pt.get("type") == "text":
            text += pt.get("text") or ""
    return {"variant": name, "rc": rc, "sec": round(time.time() - t0, 1),
            "tool_parts": dict(tools), "text": text[:300], "stderr_tail": err[-300:]}


if __name__ == "__main__":
    names = sys.argv[1:] or list(VARIANTS)
    res = [trial(n) for n in names]
    for r in res:
        print(json.dumps(r, ensure_ascii=False))
    outp = ROOT / "papers" / "studies" / "probe_no_tools.json"
    old = json.loads(outp.read_text(encoding="utf-8")) if outp.exists() else {}
    old.update({r["variant"]: r for r in res})
    outp.write_text(json.dumps(old, indent=1, ensure_ascii=False), encoding="utf-8")
