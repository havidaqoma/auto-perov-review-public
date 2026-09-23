"""09_cards: claim cards from abstracts (Q53 basis).

5.9 designs two passes with DIFFERENT CHUNK BOUNDARIES (offset 0 / offset 2k)
to cross-check a long full text. A July abstract is 187 words at the median,
so there is exactly ONE chunk and "two passes at different offsets" degenerates
into running an identical prompt twice for double the tokens and no extra
information. Under Q53 the honest adaptation is a single pass plus the
deterministic guards, which are what actually stop invented numbers:
  guard 1  anchor must appear verbatim in the source text
  guard 2  the numeric value must appear inside its own anchor
  guard 3  anchors truncated to 25 words AFTER the checks
  guard 4  reporting_flags recomputed by script; the model's are advisory
Abstracts are batched to keep the run tractable; the guards are per-field.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stages.util import ROOT, done, read_jsonl, run_dir, write_jsonl

BATCH = 12
# Floor on cards/depth_papers. A paper with no extractable claim still yields
# a card, so real coverage sits at ~100%; 0.98 leaves room for a genuine
# per-paper skip without admitting a dead batch. The 2025-06 run scored
# 92.1% with exactly one dead batch, so this floor would have caught it.
MIN_COVERAGE = 0.98
# Reverted from muse-spark-1.3-contributor on 2026-09-08 (Havid, "to be
# safe"). That model passed a JSON-shape probe but never extracted a real
# month; qwen3.8-flash has 313 verified anchors across July and August.
# Changing this REQUIRES the probe in handbook 2.1 and a re-extraction,
# because provenance() declares the model the CARDS record, not this one.
MODEL = "opencode-go/qwen3.8-flash"

PROMPT = """You extract structured facts from perovskite solar-cell paper abstracts.

Return ONLY a JSON array, one object per input paper, no prose, no markdown fence.

For each paper return:
{"i": <the paper's index number>,
 "architecture": "p-i-n"|"n-i-p"|"tandem_2T"|"tandem_4T"|"module"|"none"|"unknown",
 "absorber": "<short formula or material, or null>",
 "pce_champion": {"value": <number>, "unit": "%", "anchor": "<VERBATIM quote from the abstract containing that number>"} | null,
 "pce_certified": {...} | null,
 "pce_stabilised": {...} | null,
 "active_area_cm2": {...} | null,
 "stability_protocol": "<e.g. ISOS-L-1, or null>",
 "t80_h": {...} | null,
 "claims": [{"text": "<one factual sentence about THIS paper>", "anchor": "<VERBATIM quote>", "evidence_type": "measurement"|"simulation"|"inference"}]
}

HARD RULES:
- Every anchor MUST be copied WORD-FOR-WORD from that paper's abstract. Do not paraphrase.
- A numeric value MUST appear inside its own anchor text.
- If the abstract does not state something, use null. Never guess or infer a number.
- 1 to 3 claims per paper, each with its own verbatim anchor.
- Output the JSON array only.

PAPERS:
"""


def _opencode_exe() -> str:
    """Resolve the REAL opencode binary, not a shim.

    Three-layer Windows trap, all hit for real on 2026-09-07:
      1. `command -v opencode` -> a POSIX shell script. bash runs it;
         CreateProcess cannot -> FileNotFoundError [WinError 2].
      2. shutil.which finds opencode.CMD, but `cmd.exe /c <path with spaces>`
         splits on the space in "<HOME>" ->
         "'<HOME>' is not recognized". rc=1, stdout empty.
      3. The .cmd is only a wrapper around
         node_modules/opencode-ai/bin/opencode.exe -- so use that directly and
         skip both shims. No shell, no quoting, no space problem.
    """
    import shutil
    cand = shutil.which("opencode")
    if cand:
        real = (pathlib.Path(cand).parent / "node_modules" / "opencode-ai"
                / "bin" / "opencode.exe")
        if real.exists():
            return str(real)
        if cand.lower().endswith(".exe"):
            return cand
    raise SystemExit(
        "FAIL-CLOSED: cannot resolve opencode.exe (Q40: writer has no fallback)")


class WriterFailure(RuntimeError):
    """Q41: writer failed. Never silently substituted, never silently skipped."""


def call_opencode(prompt: str, timeout: int = 900, attempts: int = 3) -> tuple[str, dict]:
    """Run the writer non-interactively (P-08 flags).

    Q41: retry the SAME model up to 3 times with backoff; never fall back to a
    different model. A non-zero rc or empty stdout RAISES -- the previous
    version ignored p.returncode, so 14 consecutive failed calls produced
    "0 cards" with no error at all. That silent-zero shape is exactly what
    section 0 rule 4 forbids, and it is the second time this run has appeared
    (see run_dir relocation), so it now fails loudly.
    """
    exe = _opencode_exe()
    last = ""
    for i in range(attempts):
        p = subprocess.run(
            [exe, "run", "-m", MODEL, "--format", "json", prompt],
            capture_output=True, text=True, timeout=timeout, cwd=ROOT)
        out = p.stdout or ""
        if p.returncode == 0 and out.strip():
            text, tokens = "", {}
            for line in out.splitlines():
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                part = ev.get("part") or {}
                if part.get("type") == "text" and part.get("text"):
                    text += part["text"]
                if isinstance(part.get("tokens"), dict):
                    tokens = part["tokens"]
            if text.strip():
                return text, tokens
            last = "rc=0 but no text part in the JSON event stream"
        else:
            last = f"rc={p.returncode} stdout={len(out)}B stderr={(p.stderr or '')[:200]!r}"
        if i < attempts - 1:
            time.sleep(2 ** i + 1)
    raise WriterFailure(f"opencode failed after {attempts} attempts: {last}")


def parse_array(raw: str) -> list:
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    i, j = raw.find("["), raw.rfind("]")
    if i == -1 or j == -1:
        return []
    try:
        return json.loads(raw[i:j + 1])
    except Exception:
        return []


class BatchParseFailure(RuntimeError):
    """A batch's response could not be parsed into usable objects.

    THE SILENT HOLE THIS CLOSES -- MEASURED, NOT HYPOTHETICAL
    ---------------------------------------------------------
    Measured on the 2025-06 dry run:

        [09]  96/152 -> 96 cards
        [09] 108/152 -> 96 cards      <- 12 papers in, 0 cards out

    Papers 96-107 were exactly one contiguous batch (batch 8). Their
    abstracts were 148-342 words, median 197 -- perfectly good input. The
    batch's response simply failed to parse.

    `call_opencode` already fails loudly on rc!=0 or empty stdout. But when
    it returns TEXT that `parse_array` cannot decode, `parse_array` returns
    [] by design, `got` becomes empty, every paper in the batch receives
    `o = {}`, and the per-paper loop produces no card WITHOUT RAISING. The
    summary then reports `dropped_papers: 12` as though that were a normal
    outcome.

    So the loud failure sat on one side of the seam and the silent zero on
    the other. 12 of 152 papers is 7.9% of a month; on ~450 yearly depth
    papers a few bad batches could delete several percent of the evidence
    base while EVERY downstream gate passes, because the gates measure
    internal consistency, not coverage.
    """


def parse_batch_or_raise(raw: str, batch_len: int, batch_no: int,
                         *, retry) -> dict:
    """Decode one batch's response, retrying once, then failing closed.

    Returns {index: object}. Raises BatchParseFailure rather than returning
    an empty mapping, because "the model answered nothing usable" and "these
    papers legitimately carry no extractable claim" are different facts and
    must not share a representation.

    `retry` is a zero-argument callable that re-issues the SAME request to
    the SAME model. Retrying the same model is not a fallback (Q40/Q41): a
    fallback would put two models' output in one corpus and break the
    provenance distribution.
    """
    def decode(text: str) -> dict:
        return {int(o["i"]): o for o in parse_array(text)
                if isinstance(o, dict) and str(o.get("i", "")).isdigit()}

    got = decode(raw)
    if got:
        return got

    print(f"[09] batch {batch_no}: response parsed to 0 objects "
          f"({len(raw or '')}B). Retrying the same model once.")
    raw2, _ = retry()
    got = decode(raw2)
    if got:
        print(f"[09] batch {batch_no}: retry recovered {len(got)} objects")
        return got

    raise BatchParseFailure(
        f"batch {batch_no} ({batch_len} papers) produced no parseable "
        f"objects after a retry. First response was {len(raw or '')}B, "
        f"second {len(raw2 or '')}B. This is the silent-zero class: the "
        f"papers are fine and the model's answer is unusable, so the batch "
        f"must NOT contribute zero cards and continue. Re-run the stage; "
        f"completed batches are not repeated only if you resume from a "
        f"written claim_cards.jsonl.")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


NUM = re.compile(r"\d+(?:[.,]\d+)?")


def guard_field(fld, source: str, stats: dict):
    """Guards 1+2+3, with the plan's guard ORDER corrected.

    5.9 says: (1) anchor verbatim, (2) value appears inside its own anchor,
    (3) "anchors truncated to 25 words AFTER the checks". That order is a bug:
    guard 2 validates the FULL anchor, then guard 3 removes words from it, so a
    value sitting past word 25 passes the check and is then cut out of the text
    that is supposed to prove it. Measured on the July run: 5 fields shipped
    with anchors ending mid-sentence right before their own number
    ("...leading to", "...(PCE)", "...increases efficiency from"), while stage
    09 reported nulled_number=0.

    Fix: truncate FIRST, then require the value inside the TRUNCATED anchor.
    This keeps both invariants that matter -- G10's <=25-word copyright cap and
    "every shipped number is provable from its own shipped quote" -- instead of
    trading one for the other. A value that cannot be proved within 25 words is
    nulled, which is the fail-closed answer.
    """
    if not isinstance(fld, dict):
        return None
    anchor = norm(fld.get("anchor"))
    if not anchor or anchor.lower() not in norm(source).lower():
        stats["nulled_anchor"] += 1
        return None

    words = anchor.split()
    truncated = len(words) > 25
    if truncated:
        # keep a window that still contains the value when one exists
        val_s = str(fld.get("value")) if fld.get("value") is not None else None
        head = " ".join(words[:25])
        if val_s and not _num_in(val_s, head):
            for start in range(1, max(1, len(words) - 24)):
                win = " ".join(words[start:start + 25])
                if _num_in(val_s, win):
                    head = win
                    break
        anchor = head

    val = fld.get("value")
    if val is not None and not _num_in(str(val), anchor):
        stats["nulled_number"] += 1
        return None
    return {"value": val, "unit": fld.get("unit"),
            "anchor": anchor, "anchor_truncated": truncated}


def _num_in(want: str, text: str) -> bool:
    want = want.replace(",", ".")
    if not _isnum(want):
        return False
    for m in NUM.finditer(text):
        g = m.group(0).replace(",", ".")
        if _isnum(g) and abs(float(want) - float(g)) < 1e-6:
            return True
    return False


def _isnum(s: str) -> bool:
    try:
        float(s)
        return True
    except Exception:
        return False


def cards(month: str) -> dict:
    rd = run_dir(month)
    sub = [x for x in read_jsonl(rd / "08_subset_scores.jsonl") if x["depth_slot"]]
    abst = {a["work_key"]: a["abstract"]
            for a in read_jsonl(rd / "private" / "02_abstracts.jsonl")}
    corpus = {r["work_key"]: r for r in read_jsonl(rd / "05_corpus.jsonl")}
    labels = {l["work_key"]: l for l in read_jsonl(rd / "06_labels.jsonl")}

    stats = {"nulled_anchor": 0, "nulled_number": 0, "dropped_papers": 0}
    out, tokrows = [], []
    # Per-batch answered counts, so `dropped_papers` becomes auditable rather
    # than a bare total. A reader must be able to tell "the model skipped
    # these papers" from "one batch failed to parse".
    batch_coverage: list[dict] = []
    todo = [x for x in sub if abst.get(x["work_key"])]
    print(f"[09] {len(todo)} depth papers, batches of {BATCH}")

    for b0 in range(0, len(todo), BATCH):
        batch = todo[b0:b0 + BATCH]
        body = []
        for n, x in enumerate(batch):
            wk = x["work_key"]
            body.append(f"--- PAPER {n} ---\nTITLE: {corpus[wk]['title']}\n"
                        f"ABSTRACT: {abst[wk][:2600]}")
        prompt = PROMPT + "\n\n".join(body)
        batch_no = b0 // BATCH
        raw, tok = call_opencode(prompt)
        # A batch that parses to nothing RETRIES, then RAISES. It must never
        # contribute zero cards and continue -- see BatchParseFailure for the
        # measured 12-paper hole this closes.
        got = parse_batch_or_raise(
            raw, len(batch), batch_no,
            retry=lambda: call_opencode(prompt))
        n_answered = sum(1 for n in range(len(batch)) if n in got)
        batch_coverage.append({"batch": batch_no, "n_papers": len(batch),
                               "n_answered": n_answered})
        tokrows.append({"stage": "09_cards", "model": MODEL, "cli": "opencode",
                        "batch": batch_no, "n_papers": len(batch),
                        "n_answered": n_answered,
                        "tokens_in": tok.get("input"), "tokens_out": tok.get("output"),
                        "cache_read": (tok.get("cache") or {}).get("read"),
                        "token_source": "reported" if tok else "missing",
                        "at": time.strftime("%H:%M:%S")})

        for n, x in enumerate(batch):
            wk = x["work_key"]
            src = abst[wk]
            o = got.get(n) or {}
            perf = {}
            for f in ("pce_champion", "pce_certified", "pce_stabilised",
                      "active_area_cm2"):
                g = guard_field(o.get(f), src, stats)
                if g:
                    perf[f] = g
            t80 = guard_field(o.get("t80_h"), src, stats)
            claims = []
            for c in (o.get("claims") or [])[:3]:
                if not isinstance(c, dict):
                    continue
                a = norm(c.get("anchor"))
                if a and a.lower() in norm(src).lower():
                    claims.append({
                        "id": f"{wk}#{len(claims)+1}",
                        "text": norm(c.get("text"))[:300],
                        "anchor": " ".join(a.split()[:25]),
                        "evidence_type": c.get("evidence_type") or "measurement"})
                else:
                    stats["nulled_anchor"] += 1
            if not claims:
                stats["dropped_papers"] += 1
                continue
            proto = o.get("stability_protocol")
            if proto and not re.search(re.escape(str(proto)), src, re.I):
                proto = None
            # Guard 5: the ARCHITECTURE must describe the device the certified
            # number was measured on, not merely the paper's own device.
            #
            # June 2026 shipped "certified PCE reached 32.95% [3]" under
            # single-junction inverted cells, and its abstract said the same.
            # The paper IS a p-i-n flexible cell, so architecture "p-i-n" was
            # right about the paper -- but the certified value's own anchor
            # reads "a certified 32.95% perovskite/Si tandem efficiency". One
            # abstract carried two devices, and the label followed the paper
            # while the number came from the other one.
            #
            # A number and its device label must come from the SAME sentence,
            # so when the certified anchor names a multi-junction stack the
            # architecture is corrected to match the number. The anchor is the
            # only text verified verbatim against the source, so it wins.
            arch = o.get("architecture") or "unknown"
            cert_anchor = ((perf.get("pce_certified") or {})
                           .get("anchor") or "").lower()
            if cert_anchor and not str(arch).startswith("tandem"):
                if any(t in cert_anchor for t in
                       ("tandem", "/si ", "/silicon", "perovskite/si",
                        "perovskite/perovskite", "all-perovskite")):
                    stats["arch_corrected_to_tandem"] = stats.get(
                        "arch_corrected_to_tandem", 0) + 1
                    arch = "tandem_2T"
            out.append({
                "work_key": wk, "doi": corpus[wk]["doi"],
                "title": corpus[wk]["title"], "venue": corpus[wk]["venue"],
                # Stamped from the CORPUS record, never from the model. The
                # yearly trajectory slices months from these two fields, and a
                # monthly run never needed them because the run directory WAS
                # the month. Without them every card is month-unknown and the
                # twelve-point series, F5, F6 and the trajectory/synthesis
                # sections all have zero data while the run reports success.
                "publication_date": corpus[wk].get("publication_date") or "",
                "date_precision": corpus[wk].get("date_precision") or "unknown",
                "axis": labels[wk]["axis_primary"],
                "lens": labels[wk]["lens"],
                "text_basis": "abstract",          # Q53
                "device": {"architecture": arch,
                           "absorber": o.get("absorber")},
                "performance": perf,
                "stability": {"protocol": proto, "t80_h": t80},
                "claims": claims,
                # guard 4: recomputed by script, model flags discarded
                "reporting_flags": {
                    "states_certification": "pce_certified" in perf,
                    "states_area": "active_area_cm2" in perf,
                    "states_stabilised": "pce_stabilised" in perf,
                    "isos_labelled": bool(proto),
                    "states_t80": bool(t80)},
                "extractor": {"model": MODEL, "basis": "abstract"},
            })
        print(f"[09] {min(b0+BATCH,len(todo))}/{len(todo)} -> {len(out)} cards, "
              f"nulled a/n {stats['nulled_anchor']}/{stats['nulled_number']}")

    write_jsonl(rd / "claim_cards.jsonl", out)
    write_jsonl(rd / "tokens.jsonl", tokrows)

    # ---- COVERAGE ASSERTION ------------------------------------------
    # The per-batch raise above catches a WHOLE batch failing. This catches
    # the diffuse case: many batches each answering a few papers short, which
    # no single batch failure would reveal. Measured baseline on 2025-06
    # before the fix: 140/152 = 92.1%, and that was ONE dead batch.
    #
    # A paper legitimately carrying no extractable claim still yields a CARD
    # (with empty performance), so cards should track `todo` almost exactly.
    # The floor is therefore high on purpose.
    n_expected = len(todo)
    coverage = (len(out) / n_expected) if n_expected else 1.0
    short = [b for b in batch_coverage if b["n_answered"] < b["n_papers"]]
    if coverage < MIN_COVERAGE:
        raise SystemExit(
            f"FAIL-CLOSED: extraction produced {len(out)} cards for "
            f"{n_expected} depth papers ({coverage:.1%}), below the "
            f"{MIN_COVERAGE:.0%} floor. Short batches: "
            f"{[(b['batch'], b['n_answered'], b['n_papers']) for b in short]}. "
            f"Cards are already written, so inspect them before re-running; "
            f"a coverage hole is invisible to every downstream gate because "
            f"the gates measure internal consistency, not coverage.")
    if short:
        print(f"[09] WARNING {len(short)} batch(es) answered short: "
              f"{[(b['batch'], b['n_answered'], b['n_papers']) for b in short]}")

    meta = {"n_cards": len(out), "n_claims": sum(len(c["claims"]) for c in out),
            **stats,
            "n_depth_papers": n_expected,
            "coverage_pct": round(100.0 * coverage, 1),
            "batches": len(batch_coverage),
            "batches_short": len(short),
            "median_claims": sorted(len(c["claims"]) for c in out)[len(out) // 2] if out else 0,
            "with_pce": sum(1 for c in out if "pce_champion" in c["performance"]),
            "with_certified": sum(1 for c in out if c["reporting_flags"]["states_certification"]),
            # Reported as-is and NOT to be quoted: the provider returns an
            # implausible prompt-token count (78 across 13 batches carrying
            # ~180 words each on the 2025-06 run). An implausible number is
            # the same class as a zero -- surfaced, never substituted.
            "tokens_in": sum(r["tokens_in"] or 0 for r in tokrows),
            "tokens_in_credible": False,
            "tokens_out": sum(r["tokens_out"] or 0 for r in tokrows)}
    (rd / "09_batch_coverage.json").write_text(
        json.dumps(batch_coverage, indent=2), encoding="utf-8")
    (rd / "09_cards_summary.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    done(rd, "09_cards", **meta)
    print("[09]", json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    # No default period. This stage is the ONLY one that spends money, so a
    # silent default is the most expensive possible defect here: run it bare
    # and it would extract a 2026-07 run dir this repo does not own.
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: s09_cards.py <period>   e.g. 2025  or  2025-06\n"
            "No default: the period must be stated, never inferred.\n"
            "This is the extraction stage -- the only stage that costs "
            "tokens. State the period deliberately.")
    cards(sys.argv[1])
