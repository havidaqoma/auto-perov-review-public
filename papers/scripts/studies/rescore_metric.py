"""Re-score R2/R3/R4 with the corrected number metric. No model calls.

The first version of study_common.numbers_in read every comma as a decimal
point, so "1,080 h" parsed as 1.08 and a correct extraction of 1080 counted
as ungrounded. Every stored row of the three fabrication studies keeps the
model's value, so the correction is a pure re-score: the abstracts are read
back from the run directories and each value is re-checked.

For each ungrounded value the deterministic classifier
(study_common.explain_ungrounded) states which arithmetic relation, if any,
links it to a number in the source: unit_conversion, rounding, decimal_shift
or absent. It says nothing about whether a converted quantity is the right
quantity; the paper reports that limit.

The title-only arm (R4) also gets a second grounding source, the TITLE. The
model saw only the title, so a value present in the abstract but absent from
the title cannot have come from the prompt: it came from the model's training
data or from a tool call. R4 cannot tell those apart (the raw event stream
was not kept), and probe_title_tools.py measures whether tools are reachable.

    python -u papers/scripts/studies/rescore_metric.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from studies.study_common import (ROOT, active_run, explain_ungrounded,  # noqa: E402
                                  norm_text, number_present,
                                  number_present_legacy, wilson)
from studies.ablation_gate import fisher_exact, P_FLOOR  # noqa: E402

MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04",
          "2026-05", "2026-06", "2026-07", "2026-08"]
STUDIES = ROOT / "papers" / "studies"


def texts():
    abst, title = {}, {}
    for m in MONTHS:
        rd = active_run(m)
        for line in (rd / "private" / "02_abstracts.jsonl").read_text(
                encoding="utf-8").splitlines():
            if line.strip():
                o = json.loads(line)
                abst[o["work_key"].lower()] = o.get("abstract") or ""
        for line in (rd / "05_corpus.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                o = json.loads(line)
                title[o["work_key"].lower()] = o.get("title") or ""
    return abst, title


def arm_summary(rows, key):
    n = len(rows)
    u = sum(1 for r in rows if not r[key])
    return {"n_values": n, "n_ungrounded": u,
            "ungrounded_rate": round(u / n, 4) if n else 0.0,
            "ungrounded_ci95": list(wilson(u, n))}


def p_repr(p):
    return f"< {P_FLOOR:.0e}" if p <= P_FLOOR else f"{p:.3e}"


def rescore(name: str, abst: dict, title: dict) -> dict:
    d = json.loads((STUDIES / f"{name}.json").read_text(encoding="utf-8"))
    rows = d["rows"]
    arms = sorted({r["arm"] for r in rows}, key=lambda a: a != [x["arm"] for x in d["meta"]["arms"]][0])
    ung_arm, gd_arm = [x["arm"] for x in d["meta"]["arms"]]
    out_rows, classes = [], {}
    for r in rows:
        src = norm_text(abst.get(r["work_key"].lower(), ""))
        v = r["value"]
        fixed = number_present(v, src)
        legacy = number_present_legacy(v, src)
        rec = dict(r)
        rec["grounded_legacy"] = legacy
        rec["grounded_stored"] = r["grounded"]
        rec["grounded"] = fixed
        rec["ungrounded_class"] = "" if fixed else explain_ungrounded(v, r["field"], src)
        if name == "baseline_title_only":
            rec["in_title"] = number_present(v, norm_text(title.get(r["work_key"].lower(), "")))
        if not fixed:
            k = (r["arm"], rec["ungrounded_class"])
            classes[k] = classes.get(k, 0) + 1
        out_rows.append(rec)

    res = {"study": name, "arms": {}, "tests": {}}
    for a in (ung_arm, gd_arm):
        ar = [r for r in out_rows if r["arm"] == a]
        res["arms"][a] = {"stored": arm_summary(ar, "grounded_stored"),
                          "fixed_metric": arm_summary(ar, "grounded")}
    stored_consistent = all(r["grounded_stored"] == r["grounded_legacy"] for r in out_rows)
    res["stored_matches_legacy_metric"] = stored_consistent
    ua, ga = res["arms"][ung_arm]["fixed_metric"], res["arms"][gd_arm]["fixed_metric"]
    p = fisher_exact(ua["n_ungrounded"], ua["n_values"] - ua["n_ungrounded"],
                     ga["n_ungrounded"], ga["n_values"] - ga["n_ungrounded"])
    res["tests"]["fixed_metric"] = {"fisher_exact_p": p, "repr": p_repr(p)}
    # strict reading: only values with no arithmetic link to the source count
    ab = sum(1 for r in out_rows if r["arm"] == ung_arm and not r["grounded"]
             and r["ungrounded_class"] in ("absent", "decimal_shift"))
    abg = sum(1 for r in out_rows if r["arm"] == gd_arm and not r["grounded"]
              and r["ungrounded_class"] in ("absent", "decimal_shift"))
    p2 = fisher_exact(ab, ua["n_values"] - ab, abg, ga["n_values"] - abg)
    res["tests"]["no_arithmetic_link_only"] = {
        "n_ungated": ab, "n_guarded": abg,
        "rate_ungated": round(ab / ua["n_values"], 4) if ua["n_values"] else 0.0,
        "ci95_ungated": list(wilson(ab, ua["n_values"])),
        "fisher_exact_p": p2, "repr": p_repr(p2)}
    res["ungrounded_by_class"] = {f"{a}:{c}": n for (a, c), n in sorted(classes.items())}
    res["ungrounded_rows"] = [
        {k: r.get(k) for k in ("arm", "month", "work_key", "field", "value",
                               "ungrounded_class", "grounded_legacy")}
        for r in out_rows if not r["grounded"]]
    res["recovered_by_fix"] = [
        {k: r.get(k) for k in ("arm", "work_key", "field", "value")}
        for r in out_rows if r["grounded"] and not r["grounded_stored"]]
    if name == "baseline_title_only":
        ur = [r for r in out_rows if r["arm"] == ung_arm]
        res["title_only_provenance"] = {
            "n_values": len(ur),
            "in_title": sum(1 for r in ur if r["in_title"]),
            "in_abstract_not_title": sum(1 for r in ur if r["grounded"] and not r["in_title"]),
            "in_neither": sum(1 for r in ur if not r["grounded"] and not r["in_title"]),
            "n_papers_with_any_value": len({r["work_key"] for r in ur}),
            "n_papers_pool": d["meta"].get("n_papers"),
            "n_papers_lost_to_partial_batches": d["meta"].get("n_papers_lost_to_partial_batches"),
        }
    if name == "baseline_scaled":
        res["review"] = apply_review(res["ungrounded_rows"], abst, ua["n_values"],
                                     ga["n_values"])
    return res, out_rows


REVIEW = STUDIES / "r3_ungrounded_review.json"


def apply_review(ung_rows, abst, n_ung, n_gd):
    """Join the hand-read verdicts onto the rows still ungrounded.

    Fail-closed: every ungrounded row needs exactly one verdict, every verdict
    must match an ungrounded row, and every quote must occur verbatim in that
    paper's abstract. A verdict without its evidence is not accepted.
    """
    rv = json.loads(REVIEW.read_text(encoding="utf-8"))
    by = {(x["work_key"].lower(), x["field"], float(x["value"])): x for x in rv["rows"]}
    got = {(r["work_key"].lower(), r["field"], float(r["value"])) for r in ung_rows}
    if set(by) != got:
        raise SystemExit(f"FAIL-CLOSED: review rows != ungrounded rows "
                         f"(missing {sorted(got - set(by))[:3]}, extra {sorted(set(by) - got)[:3]})")
    counts = {}
    for k, x in by.items():
        if x["verdict"] not in rv["classes"]:
            raise SystemExit(f"FAIL-CLOSED: unknown verdict {x['verdict']!r}")
        if x["quote"] not in abst.get(k[0], ""):
            raise SystemExit(f"FAIL-CLOSED: quote not verbatim in the abstract of {k[0]}")
        counts[x["verdict"]] = counts.get(x["verdict"], 0) + 1
    # Which verdicts count as an error is an operator ruling, recorded in the
    # review file and in verdict_rulings.json; never assumed here.
    err = rv.get("counts_as_error")
    if not err or any(c not in rv["classes"] for c in err):
        raise SystemExit("FAIL-CLOSED: review file lacks a valid counts_as_error ruling")
    n_wrong = sum(counts.get(c, 0) for c in err)
    p = fisher_exact(n_wrong, n_ung - n_wrong, 0, n_gd)
    # Sensitivity only: the stricter reading that also counts a module
    # footprint in the active-area field as an error (overruled by the operator).
    n_nc = n_wrong + (0 if "footprint_as_area" in err else counts.get("footprint_as_area", 0))
    p_nc = fisher_exact(n_nc, n_ung - n_nc, 0, n_gd)
    return {"reviewer": rv["reviewer"], "by_verdict": counts,
            "counts_as_error": err, "ruling": rv.get("counts_as_error_source"),
            "n_wrong": n_wrong, "wrong_rate": round(n_wrong / n_ung, 4),
            "wrong_ci95": list(wilson(n_wrong, n_ung)),
            "fisher_wrong_vs_guarded_p": p, "repr": p_repr(p),
            "n_not_correct": n_nc, "not_correct_rate": round(n_nc / n_ung, 4),
            "not_correct_ci95": list(wilson(n_nc, n_ung)),
            "not_correct_is": "sensitivity: errors plus footprints (stricter reading, overruled)",
            "fisher_not_correct_vs_guarded_p": p_nc, "not_correct_repr": p_repr(p_nc),
            "quotes_verified_verbatim": True}


def main():
    abst, title = texts()
    report = {"what": "R2/R3/R4 re-scored with the corrected number metric "
                      "(digit grouping read as grouping). No model calls; rows unchanged.",
              "studies": {}}
    for name in ("baseline_fabrication", "baseline_scaled", "baseline_title_only"):
        res, rows = rescore(name, abst, title)
        report["studies"][name] = res
        import csv
        cols = list(rows[0].keys())
        with (STUDIES / f"{name}_rescored.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
    (STUDIES / "metric_rescore.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    for n, r in report["studies"].items():
        print("==", n, "stored==legacy:", r["stored_matches_legacy_metric"])
        for a, v in r["arms"].items():
            print("  ", a, "stored", v["stored"]["n_ungrounded"], "/", v["stored"]["n_values"],
                  "-> fixed", v["fixed_metric"]["n_ungrounded"], v["fixed_metric"]["ungrounded_ci95"])
        print("   tests", {k: v.get("repr") for k, v in r["tests"].items()},
              r["tests"]["no_arithmetic_link_only"]["n_ungated"])
        print("   classes", r["ungrounded_by_class"])
        if "title_only_provenance" in r:
            print("   provenance", r["title_only_provenance"])


if __name__ == "__main__":
    main()
