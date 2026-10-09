"""Probe: can the title-only arm (R4) reach tools?

R4 gave the extractor the TITLE only, yet 49 of its 84 values match the
abstract and not the title. Either the model had seen those papers in
training, or `opencode run` let it call a tool (web fetch, web search) and
read the abstract itself. R4 kept only the concatenated text parts of the
reply, so its artifacts cannot tell these apart.

This probe re-sends the R4 title-only prompt for the papers whose values
came from the abstract, through the same opencode binary, model and flags,
and keeps the FULL JSON event stream. Every event type and every tool part
is counted. It changes nothing in R4; it reports a mechanism.

    python -u papers/scripts/studies/probe_title_tools.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
from studies.study_common import ROOT, norm_text, number_present  # noqa: E402
from studies.rescore_metric import texts  # noqa: E402
import stages.s09_cards as s09  # noqa: E402

STUDIES = ROOT / "papers" / "studies"
OUT = STUDIES / "probe_title_tools.json"
RAW = ROOT / "runs" / "studies" / "probe_title_tools_events.jsonl"
MODEL = "opencode-go/qwen3.8-flash"      # the model R4 recorded


def harsh_prompt() -> str:
    src = (ROOT / "papers" / "scripts" / "studies" / "baseline_scaled.py").read_text(encoding="utf-8")
    ns: dict = {}
    start = src.index("_COMMON_SCHEMA = ")
    end = src.index("OPEN_PROMPT = ")
    exec(src[start:end], ns)             # the exact R4 prompt text, not a copy
    return ns["HARSH_PROMPT"]


def main() -> int:
    abst, title = texts()
    rs = json.loads((STUDIES / "metric_rescore.json").read_text(encoding="utf-8"))
    d = json.loads((STUDIES / "baseline_title_only.json").read_text(encoding="utf-8"))
    leaked = []
    for r in d["rows"]:
        if r["arm"] != "ungated_title_only":
            continue
        wk = r["work_key"].lower()
        if number_present(r["value"], norm_text(abst.get(wk, ""))) and not \
                number_present(r["value"], norm_text(title.get(wk, ""))):
            if r["work_key"] not in leaked:
                leaked.append(r["work_key"])
    batch = leaked[:12]
    body = [f"[{i}] TITLE: {title[wk.lower()]}" for i, wk in enumerate(batch)]
    prompt = harsh_prompt() + "\n\n".join(body)

    exe = s09._opencode_exe()
    t0 = time.time()
    p = subprocess.run([exe, "run", "-m", MODEL, "--format", "json", prompt],
                       capture_output=True, text=True, timeout=900, cwd=ROOT,
                       errors="replace")
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(p.stdout or "", encoding="utf-8")
    ev_types, part_types, tools = collections.Counter(), collections.Counter(), collections.Counter()
    text = ""
    for line in (p.stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        ev_types[ev.get("type")] += 1
        part = ev.get("part") or {}
        part_types[part.get("type")] += 1
        if part.get("type") == "tool" or part.get("tool"):
            tools[str(part.get("tool"))] += 1
        if part.get("type") == "text" and part.get("text"):
            text += part["text"]
    arr = s09.parse_array(text)
    in_abs = 0
    n_vals = 0
    for o in arr:
        try:
            wk = batch[int(o.get("i"))]
        except Exception:
            continue
        for f in ("pce_champion", "pce_certified", "active_area_cm2", "t80_h"):
            v = o.get(f)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                n_vals += 1
                a = number_present(v, norm_text(abst.get(wk.lower(), "")))
                t = number_present(v, norm_text(title.get(wk.lower(), "")))
                in_abs += int(a and not t)
    res = {"model": MODEL, "rc": p.returncode, "sec": round(time.time() - t0, 1),
           "n_papers": len(batch), "work_keys": batch,
           "event_types": dict(ev_types), "part_types": dict(part_types),
           "tool_calls": dict(tools), "n_tool_calls": sum(tools.values()),
           "n_values": n_vals, "n_values_in_abstract_not_title": in_abs,
           "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "raw_events": str(RAW.relative_to(ROOT))}
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
