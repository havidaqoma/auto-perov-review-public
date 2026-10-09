"""R6: build the blind numeric sheet and its pre-registration.

Who is asked: every paper of the R1 sample that the HUMAN labeller marked as
stating a PCE (states_pce = Y in r1_labels_filled.csv). The inclusion rule
uses a human label only, so no machine output decides who is on the sheet.

What the sheet shows: title, venue and abstract. Nothing else: no extractor
output, no pre-filled answer, no flag, no card, no model name. `blind_check`
proves it mechanically before the file is written.

What the labeller types: the numbers as the abstract writes them, for the
paper's OWN work: champion PCE, certified PCE, device area, and (if stated)
the control/reference device PCE. Scoring is r6_analyze.py, whose hash is
frozen into the pre-registration here, before anyone opens the sheet.

Run once: python papers/scripts/studies/r6_build_sheet.py
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "papers" / "scripts"))
sys.path.insert(0, str(ROOT / "scripts"))
from studies.label_sheet_build import clean, load_population  # noqa: E402

R1 = ROOT / "papers" / "studies" / "label_sheet"
OUT = ROOT / "papers" / "studies" / "r6_numeric"
SEED = 20261009

FIELDS = [
    ("pce_champion", "Champion PCE (%)",
     "the highest efficiency the abstract gives for this paper's OWN device. "
     "If only a module or tandem value is given, that value."),
    ("pce_certified", "Certified PCE (%)",
     "only a value the abstract says was independently certified, for this paper's OWN device."),
    ("active_area_cm2", "Device area, with its unit",
     "the area of the paper's own device as written, e.g. 0.09 cm2 or 9 mm2."),
    ("pce_control", "Control / reference PCE (%)",
     "the efficiency of the untreated or reference device, if the abstract states one."),
]

# Strings that would reveal the machine side. None may occur on the sheet.
FORBIDDEN = ("claim_card", "extractor", "anchor", "qwen", "glm", "opencode", "gemini",
             "verified", "pce_value_machine", "data-m", "card_pce", "has_card")


def blind_check(page: str, rows: list) -> None:
    """Fail unless each card shows only title, venue, abstract and fixed text."""
    low = page
    for r in rows:   # source text may say "anchoring"; only the frame is checked
        for part in (clean(r["title"]), clean(r["venue"]), clean(r["abstract"])):
            low = low.replace(part, "")
    low = low.lower()
    hit = [f for f in FORBIDDEN if f in low]
    if hit:
        raise SystemExit(f"FAIL-CLOSED: sheet not blind, contains {hit}")
    for r in rows:
        m = re.search(rf'<section class="card" id="c{r["order"]}"[^>]*>(.*?)</section>',
                      page, re.S)
        if not m:
            raise SystemExit(f"FAIL-CLOSED: card {r['order']} missing")
        body = m.group(1)
        for part in (clean(r["title"]), clean(r["venue"]), clean(r["abstract"])):
            body = body.replace(part, "", 1)
        body = re.sub(r"<[^>]+>", " ", body)
        body = body.replace(f'{r["order"]}/{len(rows)}', "")
        for _, lab, hint in FIELDS:
            body = body.replace(html.escape(lab), "").replace(html.escape(hint), "")
        body = body.replace("e.g. 0.09 cm2", "")
        if re.search(r"\d", body):
            raise SystemExit(f"FAIL-CLOSED: card {r['order']} shows a digit outside "
                             f"title/venue/abstract: {body.strip()[:120]!r}")
        if 'value="' in m.group(1):
            raise SystemExit(f"FAIL-CLOSED: card {r['order']} has a pre-filled input")


def build_html(rows: list) -> str:
    cards = []
    for r in rows:
        inputs = "".join(
            f'<label class="f" data-k="{k}"><span class="lab">{html.escape(lab)}</span>'
            f'<input type="text" autocomplete="off"><span class="hint">{html.escape(hint)}</span></label>'
            for k, lab, hint in FIELDS)
        cards.append(
            f'<section class="card" id="c{r["order"]}" data-wk="{html.escape(r["work_key"])}">'
            f'<div class="hd"><span class="num">{r["order"]}/{len(rows)}</span></div>'
            f'<h2>{clean(r["title"])}</h2><div class="ven">{clean(r["venue"])}</div>'
            f'<div class="abs">{clean(r["abstract"])}</div>'
            f'<div class="fs">{inputs}</div>'
            f'<button class="done-b">Done with this paper</button></section>')
    tmpl = """<!doctype html><meta charset="utf-8"><title>R6 numeric sheet</title>
<style>
:root{--bg:#faf9f7;--fg:#1a1a1a;--mut:#6b6b6b;--acc:#2d6cdf;--bd:#e0ddd8}
*{box-sizing:border-box}body{background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,Segoe UI,sans-serif;margin:0;padding:0 0 120px}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--bd);padding:10px 20px;display:flex;gap:16px;align-items:center;z-index:9}
#bar{height:4px;background:var(--bd);flex:1}#barf{height:100%;width:0;background:var(--acc)}
.card{max-width:820px;margin:26px auto;background:#fff;border:1px solid var(--bd);border-radius:10px;padding:22px 26px}
.card.done{opacity:.55}h2{font-size:18px;margin:8px 0 4px}.ven,.hd{color:var(--mut);font-size:13px}
.abs{background:#fbfaf8;border-left:3px solid var(--bd);padding:12px 14px;font-size:15px;margin:12px 0 18px}
.f{display:grid;grid-template-columns:230px 140px 1fr;gap:10px;align-items:center;padding:6px 0;border-top:1px solid #f0eeea;font-size:14px}
.f input{font-size:15px;padding:4px 8px;border:1px solid var(--bd);border-radius:5px}.hint{color:var(--mut);font-size:12.5px}
.done-b{margin-top:12px;padding:6px 14px;border:1px solid var(--bd);border-radius:6px;background:#fff;cursor:pointer}
.card.done .done-b{background:var(--acc);color:#fff}
.rules{max-width:820px;margin:20px auto;font-size:14.5px}
</style>
<header><b>R6 numeric sheet</b><span id="prog"></span><div id="bar"><div id="barf"></div></div>
<button onclick="exp()">Export CSV</button></header>
<div class="rules"><p><b>Rules.</b> You, Havid, fill this alone. No model may label, pre-label or
assist any row. Type each number <b>as the abstract writes it</b>; leave a box empty when the
abstract does not state that number. Label only the paper's <b>own</b> work: a record quoted from
another paper is not theirs. Press <b>Done</b> on every paper, including ones where every box
stays empty, so an empty box means "not stated" and not "skipped". Answers save in this browser;
press Export CSV at the end and save the file as
<code>papers/studies/r6_numeric/r6_labels_filled.csv</code>.</p></div>
__CARDS__
<script>
const KEY="r6_labels_v1";let A=JSON.parse(localStorage.getItem(KEY)||"{}");
const cards=[...document.querySelectorAll(".card")];
function paint(){let d=0;cards.forEach(c=>{const a=A[c.dataset.wk]||{};
 c.querySelectorAll(".f").forEach(f=>{const i=f.querySelector("input");const v=a[f.dataset.k]||"";if(i.value!==v)i.value=v;});
 c.classList.toggle("done",a.done==="1");if(a.done==="1")d++;});
 prog.textContent=d+" of "+cards.length+" done";barf.style.width=(100*d/cards.length)+"%";}
function save(){localStorage.setItem(KEY,JSON.stringify(A));paint();}
document.addEventListener("input",e=>{const f=e.target.closest(".f");if(!f)return;
 const wk=e.target.closest(".card").dataset.wk;(A[wk]=A[wk]||{})[f.dataset.k]=e.target.value.trim();save();});
document.addEventListener("click",e=>{const b=e.target.closest(".done-b");if(!b)return;
 const wk=b.closest(".card").dataset.wk;const a=(A[wk]=A[wk]||{});a.done=a.done==="1"?"":"1";save();});
function q(s){return '"'+String(s||"").replace(/"/g,'""')+'"';}
function exp(){const ks=__KEYS__;const L=[["work_key"].concat(ks,["done"]).join(",")];
 for(const c of cards){const a=A[c.dataset.wk]||{};L.push([q(c.dataset.wk)].concat(ks.map(k=>q(a[k])),[q(a.done)]).join(","));}
 const b=new Blob([L.join("\\n")],{type:"text/csv"});const u=URL.createObjectURL(b),x=document.createElement("a");
 x.href=u;x.download="r6_labels_filled.csv";x.click();URL.revokeObjectURL(u);}
paint();
</script>"""
    return (tmpl.replace("__CARDS__", "\n".join(cards))
                .replace("__KEYS__", json.dumps([k for k, _, _ in FIELDS])))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "r6_labels_filled.csv").exists():
        raise SystemExit("FAIL-CLOSED: labels exist; the sheet and prereg are frozen")
    labels = list(csv.DictReader((R1 / "r1_labels_filled.csv").open(encoding="utf-8")))
    frame1 = {r["work_key"]: r for r in json.loads(
        (R1 / "sampling_frame.json").read_text(encoding="utf-8"))}
    keep = sorted(r["work_key"] for r in labels if r["states_pce"] == "Y")
    pop = {}
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        for p in load_population():
            pop[p["work_key"]] = p
    rows = [dict(pop[k], month=frame1[k]["month"]) for k in keep]
    random.Random(SEED).shuffle(rows)
    for i, r in enumerate(rows, 1):
        r["order"] = i
    page = build_html(rows)
    blind_check(page, rows)
    (OUT / "r6_sheet.html").write_bytes(page.encode("utf-8"))  # LF, hash-stable
    (OUT / "sampling_frame.json").write_text(json.dumps(
        [{k: r[k] for k in ("order", "month", "work_key", "doi")} for r in rows],
        indent=2), encoding="utf-8")
    ana = (ROOT / "papers" / "scripts" / "studies" / "r6_analyze.py").read_bytes()
    pre = {
        "study": "R6 -- numeric accuracy and condition binding of extracted values",
        "built": "2026-10-09",
        "seed": SEED,
        "population": "R1 sample rows the human labeller marked states_pce = Y",
        "n_rows": len(rows),
        "inclusion_rule_uses": "human labels only (r1_labels_filled.csv)",
        "fields": [k for k, _, _ in FIELDS],
        "field_definitions": {k: hint for k, _, hint in FIELDS},
        "primary_metrics": [
            "exact-match rate of pce_champion where both human and card give a value",
            "exact-match rate of pce_certified where both give a value",
            "exact-match rate of active_area_cm2 where both give a value",
        ],
        "secondary_metrics": [
            "binding errors: wrong champion value equal to the human control value",
            "human-only values (card missing or field null) and machine-only values",
        ],
        "match_rule": "equal after unit normalisation (% ; cm2, mm2/100, m2*1e4), "
                      "|m-h| <= 1e-6*max(1,|h|)",
        "intervals": "Wilson 95%",
        "p_values": "none; there is no comparison to test",
        "weighting": "unweighted; rates describe this sample, not the corpus",
        "machine_side": "shipped claim cards after anchor verification, joined by work_key "
                        "inside r6_analyze.py, never shown on the sheet",
        "blinding": "the sheet shows title, venue and abstract only; no extractor output, "
                    "no pre-filled answer, no flag",
        "blind_check": "r6_build_sheet.blind_check passed before the sheet was written",
        "labeller": "Havid Aqoma (human). No model may label, pre-label or assist any row.",
        "prior_exposure": "the labeller read these abstracts for R1 (yes/no flags) on "
                          "2026-09-12; R1 recorded no numbers (pce_value blank in every row)",
        "analysis_script": "papers/scripts/studies/r6_analyze.py",
        "analysis_script_sha256": hashlib.sha256(ana.replace(b"\r\n", b"\n")).hexdigest(),
        # LF-normalised, so a CRLF checkout still verifies.
        "sheet_sha256": hashlib.sha256(page.encode("utf-8").replace(b"\r\n", b"\n")).hexdigest(),
        "analysis_frozen_before_labelling": True,
    }
    body = json.dumps(pre, indent=2)
    (OUT / "preregistration.json").write_text(body, encoding="utf-8")
    (OUT / "preregistration.sha256").write_text(
        hashlib.sha256(body.encode("utf-8")).hexdigest() + "  preregistration.json\n",
        encoding="utf-8")
    print(f"[r6] {len(rows)} rows; blind check passed; prereg {pre['analysis_script_sha256'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
