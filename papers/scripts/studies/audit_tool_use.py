"""Audit: did the extractor call tools during any study or shipped extraction?

`opencode run` gives the model its agent tools (bash, read, grep, glob,
webfetch, write, edit) unless they are denied. A study that says "the model
saw only the title" is false for any batch in which the model fetched the
paper from the web or grepped the repository's own run artifacts. R4 kept only
the text parts of each reply, so its artifacts could not show this; opencode's
own session store (~/.local/share/opencode/opencode.db) can, and this script
reads it READ-ONLY.

Every session whose first user prompt starts with one of the known extractor
prompts is classified, its paper titles are recovered from the prompt body,
and titles are mapped back to work_keys through the run corpora. Output:
papers/studies/tool_use_audit.json.

    python -u papers/scripts/studies/audit_tool_use.py
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import os
import pathlib
import re
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from studies.study_common import ROOT, active_run, norm_text  # noqa: E402

DB = pathlib.Path(os.path.expanduser("~/.local/share/opencode/opencode.db"))
OUT = ROOT / "papers" / "studies" / "tool_use_audit.json"
MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04",
          "2026-05", "2026-06", "2026-07", "2026-08"]
PROMPTS = {
    "s09_extractor": "You extract structured facts from perovskite solar-cell paper abstracts",
    "r3_open_ungated": "You are extracting performance data from perovskite solar cell paper abstracts",
    "r4_title_only": "You are reporting device performance data",
}
# tools that can bring outside information into the answer
INFO_TOOLS = {"webfetch", "websearch", "bash", "read", "grep", "glob", "list"}
TITLE_RE = re.compile(r"(?:\[\d+\] TITLE: |--- PAPER \d+ ---\s*TITLE: )(.+)")
# Boundary between regimes, read from the batch caches rather than typed: the
# start of the earliest call whose cache record says it was made tools-off.
# Sessions before it are "tools_on"; after it, any EXECUTED tool is a failure.
_OFF_CACHES = ["ablation_raw", "baseline_title_only_raw", "baseline_scaled_raw"]


def _tools_off_since() -> dt.datetime:
    starts = []
    for c in _OFF_CACHES:
        for f in (ROOT / "runs" / "studies" / c).glob("batch_[0-9][0-9][0-9].json"):
            r = json.loads(f.read_text(encoding="utf-8"))
            if str(r.get("tools", "")).startswith("off"):
                starts.append(dt.datetime.fromisoformat(r["at"]).timestamp() - float(r.get("sec") or 0))
    if not starts:
        return dt.datetime.max
    return dt.datetime.fromtimestamp(min(starts) - 5)


TOOLS_OFF_SINCE = _tools_off_since()


def title_index():
    idx = {}
    for m in MONTHS:
        rd = active_run(m)
        for line in (rd / "05_corpus.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                o = json.loads(line)
                idx[norm_text(o.get("title") or "").lower()] = o["work_key"]
    return idx


def main() -> int:
    if not DB.exists():
        raise SystemExit(f"FAIL-CLOSED: opencode session store not found at {DB}")
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    idx = title_index()
    report = {"db": "opencode.db (read-only)", "generated": dt.datetime.now().isoformat(timespec="seconds"),
              "tools_off_since": TOOLS_OFF_SINCE.isoformat(timespec="seconds"),
              "note": "A session is one `opencode run` call. Retries and smoke runs are "
                      "separate sessions, so session counts exceed batch counts.",
              "prompts": {}}
    for key, prefix in PROMPTS.items():
        sids = [r[0] for r in con.execute(
            "select distinct session_id from part where data like ?", (f"%{prefix}%",))]
        sessions = []
        for s in sids:
            parts = con.execute("select time_created, data from part where session_id=? "
                                "order by time_created", (s,)).fetchall()
            tools = collections.Counter()
            denied = collections.Counter()
            calls = []
            prompt = ""
            for _t, d in parts:
                o = json.loads(d)
                if o.get("type") == "text" and prefix in (o.get("text") or "") and not prompt:
                    prompt = o["text"]
                if o.get("type") == "tool":
                    st = (o.get("state") or {}).get("status")
                    inp = (o.get("state") or {}).get("input")
                    if st == "completed":          # the tool actually ran
                        tools[o.get("tool")] += 1
                    else:                           # asked for, never executed
                        denied[o.get("tool")] += 1
                    calls.append({"tool": o.get("tool"), "status": st,
                                  "path": (inp or {}).get("filePath") if isinstance(inp, dict) else None,
                                  "input": json.dumps(inp)[:300]})
            titles = [norm_text(t).lower() for t in TITLE_RE.findall(prompt)]
            wks = [idx.get(t) for t in titles]
            d0 = con.execute("select directory from session where id=?", (s,)).fetchone()
            sessions.append({
                "session": s,
                "started": dt.datetime.fromtimestamp(parts[0][0] / 1000).isoformat(timespec="seconds"),
                "directory": d0[0] if d0 else None,
                "n_titles": len(titles), "work_keys": [w for w in wks if w],
                "n_titles_unmapped": sum(1 for w in wks if not w),
                "tools": dict(tools),
                "tools_denied": dict(denied),
                "regime": "tools_off" if parts[0][0] / 1000 >= TOOLS_OFF_SINCE.timestamp()
                          else "tools_on",
                "info_tools_used": bool(set(tools) & INFO_TOOLS),
                "web_used": bool({"webfetch", "websearch"} & set(tools)),
                "calls": calls[:60]})
        sessions.sort(key=lambda x: x["started"])
        by_day = collections.defaultdict(lambda: {"sessions": 0, "with_tools": 0,
                                                   "with_web": 0, "tools": collections.Counter()})
        for x in sessions:
            b = by_day[x["started"][:10]]
            b["sessions"] += 1
            b["with_tools"] += int(bool(x["tools"]))
            b["with_web"] += int(x["web_used"])
            b["tools"].update(x["tools"])
        on = [x for x in sessions if x["regime"] == "tools_on"]
        off = [x for x in sessions if x["regime"] == "tools_off"]
        report["prompts"][key] = {
            "prefix": prefix, "n_sessions": len(sessions),
            "tools_on_regime": {
                "n_sessions": len(on),
                "n_with_executed_tool": sum(1 for x in on if x["tools"]),
                "n_with_web": sum(1 for x in on if x["web_used"]),
                "n_with_repo_read": sum(1 for x in on if set(x["tools"]) & {"read", "grep", "glob", "list"}
                                        or any(re.search(r"manuscript/|runs/|grep -ril|rg -il", c["input"])
                                               for c in x["calls"] if c["status"] == "completed")),
                "write_targets": sorted({c["path"] or "?"
                                         for x in on for c in x["calls"]
                                         if c["tool"] in ("write", "edit") and c["status"] == "completed"}),
                "n_titles_in_tool_sessions": sum(x["n_titles"] for x in on if x["tools"]),
                "n_titles": sum(x["n_titles"] for x in on)},
            "tools_off_regime": {
                "n_sessions": len(off),
                "n_with_executed_tool": sum(1 for x in off if x["tools"]),
                "n_with_denied_request": sum(1 for x in off if x["tools_denied"])},
            "n_sessions_with_any_tool": sum(1 for x in sessions if x["tools"]),
            "n_sessions_with_info_tool": sum(1 for x in sessions if x["info_tools_used"]),
            "n_sessions_with_web": sum(1 for x in sessions if x["web_used"]),
            "by_day": {k: {**v, "tools": dict(v["tools"])} for k, v in sorted(by_day.items())},
            "contaminated_work_keys": sorted({w for x in sessions if x["info_tools_used"]
                                              for w in x["work_keys"]}),
            "sessions": sessions}
    # Production = s09 extractions that shipped in a monthly issue. They all
    # precede the first evaluation-study session (the R2/R3 open prompt), so
    # that session's start is the boundary; it is read, not typed.
    study_start = min((x["started"] for x in report["prompts"]["r3_open_ungated"]["sessions"]),
                      default="9999")
    prod = [x for x in report["prompts"]["s09_extractor"]["sessions"] if x["started"] < study_start]
    report["s09_production"] = {
        "boundary_first_study_session": study_start,
        "n_sessions": len(prod),
        "n_with_executed_tool": sum(1 for x in prod if x["tools"]),
        "n_with_web": sum(1 for x in prod if x["web_used"]),
        "n_titles": sum(x["n_titles"] for x in prod),
        "n_titles_in_tool_sessions": sum(x["n_titles"] for x in prod if x["tools"]),
        "write_targets": sorted({c["path"] or "?" for x in prod for c in x["calls"]
                                 if c["tool"] in ("write", "edit") and c["status"] == "completed"})}
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    leaks = {k: v["tools_off_regime"]["n_with_executed_tool"]
             for k, v in report["prompts"].items() if v["tools_off_regime"]["n_with_executed_tool"]}
    for k, v in report["prompts"].items():
        print(f"{k:18s} sessions={v['n_sessions']:4d} any_tool={v['n_sessions_with_any_tool']:3d} "
              f"info_tool={v['n_sessions_with_info_tool']:3d} web={v['n_sessions_with_web']:3d} "
              f"papers_touched={len(v['contaminated_work_keys'])}")
        for day, b in v["by_day"].items():
            print(f"   {day} {b}")
    if leaks:
        raise SystemExit(f"FAIL: a tool EXECUTED after the tools-off fix: {leaks}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
