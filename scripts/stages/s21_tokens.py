"""s21_tokens: per-run token and cost accounting as CSV.

Havid's requirement (2026-09-08): every full-stack review paper run must ship
a CSV detailing token use per model, per CLI, and per process.

Sources, in order of trust:
  1. runs/<m>/tokens.jsonl   -- written by each LLM stage as it runs. The
     extractor records CLI-reported usage (tokens_in/out/cache_read); the
     writer records only word counts, because `agy -p` prints prose to stdout
     and reports no usage.
  2. .done markers           -- authoritative per-stage totals for stage 09.
  3. draft/manuscript files  -- word counts for stages that report no tokens.

Where a CLI reports nothing, the row is marked `token_source=estimated` and
carries `est_tokens_out` derived from words (x1.33, the usual English
word-to-token ratio). ESTIMATED IS NEVER SILENTLY MIXED WITH REPORTED: the
column says which, and the summary totals them separately. A number whose
provenance is unclear is worse than a missing number.

Run: python scripts/stages/s21_tokens.py 2026-08 [v4]
"""
from __future__ import annotations

import csv
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stages.util import ROOT, done, run_dir  # noqa: E402

WORD_TO_TOKEN = 1.33          # English prose, rough but declared

# Stage -> (role, what it does). Roles match config/models.yaml.
STAGE_ROLE = {
    "01_harvest": ("none", "OpenAlex/S2/Crossref/arXiv harvest (no LLM)"),
    "02_normalize": ("none", "DOI/title normalisation, language detect"),
    "05_dedupe": ("none", "work_key merge across sources"),
    "06_mechanism": ("none", "mechanism axis + lens keyword scoring"),
    "04_venues": ("none", "journal citation percentile"),
    "08_subset": ("none", "depth-tier selection + sensitivity draws"),
    "09_cards": ("extractor", "structured claim extraction, anchor-bound"),
    "10_stats": ("none", "every citable number"),
    "11_figures": ("none", "figures plotted from stats/cards"),
    "13d_draft_v4": ("writer", "prose: body -> gaps -> abstract"),
    "18d_build_v4": ("none", "format assembly + gates + PDF"),
    "19_si": ("none", "supplementary information"),
    "20_chemrxiv": ("none", "ChemRxiv package + CSV data pack"),
}


def _load_jsonl(p: pathlib.Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()
            if x.strip()]


def collect(month: str, ver: str = "v4") -> dict:
    rd = run_dir(month)
    rows: list[dict] = []

    tok = _load_jsonl(rd / "tokens.jsonl")

    # Which call actually produced the shipped text? The ledger is append-only,
    # so a section redrafted three times leaves three rows. Total cost INCURRED
    # is all of them; cost OF THE SHIPPED MANUSCRIPT is the last per stage.
    # Reporting one number for both would overstate the artifact by 3x, so the
    # rows carry an explicit `attempt` and `shipped` flag and the summary
    # totals them separately.
    last_of: dict[str, int] = {}
    seen_count: dict[str, int] = {}
    for i, r in enumerate(tok):
        st = r.get("stage", "?")
        last_of[st] = i

    # ---- LLM calls, one row per recorded call -------------------------
    for _i, r in enumerate(tok):
        stage = r.get("stage", "?")
        base = re.sub(r"_s\d+$|_abstract$", "", stage)
        role, desc = STAGE_ROLE.get(base, ("llm", stage))
        words = r.get("words")
        t_in = r.get("tokens_in")
        t_out = r.get("tokens_out")
        reported = t_out is not None
        seen_count[stage] = seen_count.get(stage, 0) + 1
        rows.append({
            "month": month,
            "attempt": seen_count[stage],
            "shipped": "yes" if last_of.get(stage) == _i else "no",
            "stage": stage,
            "process": desc,
            "role": role,
            "cli": r.get("cli", ""),
            "model": r.get("model", ""),
            "batch": r.get("batch", ""),
            "n_papers": r.get("n_papers", ""),
            "words_out": words if words is not None else "",
            "tokens_in": t_in if t_in is not None else "",
            "tokens_out": t_out if t_out is not None else "",
            "cache_read": r.get("cache_read", ""),
            "est_tokens_out": ("" if reported else
                               int(round((words or 0) * WORD_TO_TOKEN))),
            "token_source": r.get("token_source",
                                  "reported" if reported else "estimated"),
            "at": r.get("at", ""),
        })

    # ---- deterministic stages: no LLM, but they ARE processes ---------
    for marker in sorted(rd.glob("*.done")):
        payload = {}
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
        except Exception:
            pass
        stage = payload.get("stage", marker.stem)
        base = re.sub(r"_s\d+$|_abstract$", "", stage)
        role, desc = STAGE_ROLE.get(base, ("none", stage))
        if role != "none":
            continue                       # LLM stages already covered above
        rows.append({
            "month": month, "attempt": 1, "shipped": "yes",
            "stage": stage, "process": desc, "role": "none",
            "cli": "python", "model": "", "batch": "", "n_papers": "",
            "words_out": "", "tokens_in": 0, "tokens_out": 0,
            "cache_read": "", "est_tokens_out": 0,
            "token_source": "deterministic", "at": payload.get("at", ""),
        })

    cols = ["month", "attempt", "shipped", "stage", "process", "role",
            "cli", "model", "batch",
            "n_papers", "words_out", "tokens_in", "tokens_out", "cache_read",
            "est_tokens_out", "token_source", "at"]

    outdir = ROOT / "manuscript" / f"{month}_{ver}" / "data"
    outdir.mkdir(parents=True, exist_ok=True)
    detail = outdir / "token_usage.csv"
    with detail.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # ---- per model+cli summary ---------------------------------------
    agg: dict[tuple, dict] = {}
    ship: dict[tuple, dict] = {}
    for r in rows:
        key = (r["role"], r["cli"], r["model"])
        if r.get("shipped") == "yes":
            b = ship.setdefault(key, {"calls": 0, "tokens_out": 0,
                                      "est_tokens_out": 0, "words_out": 0})
            b["calls"] += 1
            for k in ("tokens_out", "est_tokens_out", "words_out"):
                v = r.get(k)
                if isinstance(v, (int, float)):
                    b[k] += v
        a = agg.setdefault(key, {"calls": 0, "tokens_in": 0, "tokens_out": 0,
                                 "cache_read": 0, "est_tokens_out": 0,
                                 "words_out": 0, "reported": 0, "estimated": 0})
        a["calls"] += 1
        for k in ("tokens_in", "tokens_out", "cache_read", "est_tokens_out",
                  "words_out"):
            v = r.get(k)
            if isinstance(v, (int, float)):
                a[k] += v
        if r["token_source"] == "reported":
            a["reported"] += 1
        elif r["token_source"] == "estimated":
            a["estimated"] += 1

    summary = outdir / "token_summary.csv"
    scols = ["role", "cli", "model", "calls_total", "calls_shipped",
             "calls_reported", "calls_estimated", "tokens_in",
             "tokens_out_total", "tokens_out_shipped", "cache_read",
             "est_tokens_out_total", "est_tokens_out_shipped",
             "words_out_total", "words_out_shipped"]
    with summary.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(scols)
        for (role, cli, model), a in sorted(agg.items()):
            sh = ship.get((role, cli, model),
                          {"calls": 0, "tokens_out": 0, "est_tokens_out": 0,
                           "words_out": 0})
            w.writerow([role, cli, model, a["calls"], sh["calls"],
                        a["reported"], a["estimated"], a["tokens_in"],
                        a["tokens_out"], sh["tokens_out"], a["cache_read"],
                        a["est_tokens_out"], sh["est_tokens_out"],
                        a["words_out"], sh["words_out"]])

    tot_reported_out = sum(a["tokens_out"] for a in agg.values())
    tot_est_out = sum(a["est_tokens_out"] for a in agg.values())
    meta = {
        "detail_csv": str(detail),
        "summary_csv": str(summary),
        "rows": len(rows),
        "llm_calls": sum(1 for r in rows if r["role"] in ("extractor", "writer")),
        "models": sorted({r["model"] for r in rows if r["model"]}),
        "tokens_in_reported": sum(a["tokens_in"] for a in agg.values()),
        "tokens_out_reported": tot_reported_out,
        "tokens_out_estimated": tot_est_out,
        "cache_read": sum(a["cache_read"] for a in agg.values()),
        "calls_shipped": sum(b["calls"] for b in ship.values()),
        "note": ("agy reports no usage for -p calls, so writer rows are "
                 "estimated from word counts at x1.33; reported and estimated "
                 "are never summed into one figure. `shipped=yes` marks the "
                 "call whose output reached the manuscript: totals are cost "
                 "INCURRED, shipped columns are cost OF THE ARTIFACT."),
    }
    done(rd, "21_tokens", **meta)
    print("[21]", json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    collect(sys.argv[1] if len(sys.argv) > 1 else "2026-08",
            sys.argv[2] if len(sys.argv) > 2 else "v4")
