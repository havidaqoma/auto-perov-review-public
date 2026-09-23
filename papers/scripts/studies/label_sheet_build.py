"""R1: build the human label sheet -- sampler, blind form, pre-registration.

WHAT THIS MEASURES. Every audit percentage the pipeline ships
(`audit.corpus.certified.pct` and friends) is a REGEX hit-rate over corpus
abstracts. `precision` and `recall` are literally `None` in stats.json and the
number ships as "detected in at least X%". This sheet produces the answer key
that turns that floor into a measured rate with a confidence interval.

THE POPULATION IS NOT THE CARDS. Measured on 2026-07:

    corpus.n                 648   works passing the scope gate
    audit.corpus.denominator 456   <- what the percentages actually divide by
    selection.n_depth        181   works read closely
    claim_cards              169   works the extractor produced records for

`audit_over()` pools `[abst.get(k) for k in labels if abst.get(k)]`, so the
denominator is CORPUS WORKS THAT HAVE AN ABSTRACT. Sampling the 169 cards
would measure a different population and no one would notice afterwards.

FOUR RULES THIS BUILDER ENFORCES.

1. BLIND. The sheet never shows what the pipeline extracted -- no pre-filled
   answers, no flags, no confidence ordering. Labels join to machine output by
   DOI inside the analysis script, after the fact. A labeller who can see the
   machine's answer is no longer an independent check.
2. NO MODEL TOUCHES A LABEL. Not to pre-fill, not to assist, not to break a
   tie. A machine grading the machine is the circularity this study exists to
   break.
3. STRATIFIED WITH RECORDED PROBABILITIES. Certified fires on ~8.3% of
   abstracts and ISOS on ~1.7%, so a flat random 100 yields ~8 and ~2 -- too
   few to support a precision claim. Rare cells are oversampled and every row
   carries its inclusion probability, so the analysis can invert the weights.
   A stratified sample reported as a population rate without weights is a
   false statement about the corpus.
4. INTERLEAVED. The final order is shuffled across strata, so stopping early
   still yields a valid subsample and fatigue spreads evenly instead of
   landing entirely on the rare cells.

Run: python -u scripts/studies/label_sheet_build.py [N] [--months 2026-07 ...]
"""
from __future__ import annotations

import hashlib
import html
import json
import pathlib
import random
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from studies.study_common import active_run  # noqa: E402
from stages.s04_10 import AUDIT_RX, audit_hit  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "papers" / "studies" / "label_sheet"

SEED = 20260912
N_TARGET = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 100
MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04",
          "2026-05", "2026-06", "2026-07", "2026-08"]
if "--months" in sys.argv:
    MONTHS = [a for a in sys.argv[sys.argv.index("--months") + 1:]
              if not a.startswith("--")]

# The five questions, deliberately mirroring the extractor's own flag names so
# precision/recall compare like with like.
QUESTIONS = [
    ("states_pce", "Does the abstract report a PCE (efficiency) number for a device?"),
    ("states_certified", "Does it say a value was independently CERTIFIED?"),
    ("states_area", "Does it give a device AREA with a unit?"),
    ("states_t80", "Does it give an operational lifetime (T80 or equivalent)?"),
    ("isos_protocol", "Does it name an ISOS protocol?"),
]

# Oversampling weights per stratum. Rare cells are lifted so the precision
# estimate on them is not built from three papers.
CELL_WEIGHT = {"certified": 4.0, "isos": 6.0, "pce_only": 1.0, "none": 0.7}


def cell_of(text: str) -> str:
    """Stratum from the REGEX flags -- the machine's view, used ONLY to sample.

    This never reaches the sheet. It decides who gets asked, not what the
    answer is, and the analysis re-derives everything from the human labels.
    """
    if audit_hit("isos_label", AUDIT_RX["isos_label"], text):
        return "isos"
    if audit_hit("certified", AUDIT_RX["certified"], text):
        return "certified"
    if audit_hit("efficiency_stated", AUDIT_RX["efficiency_stated"], text):
        return "pce_only"
    return "none"


def load_population():
    """Exactly the pool `audit_over()` builds: labelled works WITH an abstract."""
    pop = []
    for m in MONTHS:
        try:
            rd = active_run(m)
        except Exception as e:
            print(f"[r1] skip {m}: {e}")
            continue
        ab = {}
        p_ab = rd / "private" / "02_abstracts.jsonl"
        for line in p_ab.read_text(encoding="utf-8").splitlines():
            if line.strip():
                o = json.loads(line)
                ab[o["work_key"].lower()] = o.get("abstract") or ""
        lab = rd / "06_labels.jsonl"
        meta = {}
        p_corp = rd / "05_corpus.jsonl"
        if p_corp.exists():
            for line in p_corp.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    o = json.loads(line)
                    meta[(o.get("work_key") or "").lower()] = o
        n_m = 0
        for line in lab.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            o = json.loads(line)
            wk = (o.get("work_key") or "").lower()
            text = ab.get(wk, "")
            if not text:
                continue                       # audit_over drops these too
            md = meta.get(wk, {})
            pop.append(dict(month=m, work_key=o.get("work_key"),
                            doi=md.get("doi") or o.get("work_key"),
                            title=md.get("title") or "(title unavailable)",
                            venue=md.get("venue") or "",
                            abstract=text, cell=cell_of(text)))
            n_m += 1
        print(f"[r1] {m}: {n_m} works with abstracts")
    return pop


def sample(pop):
    rng = random.Random(SEED)
    by_cell: dict[str, list] = {}
    for r in pop:
        by_cell.setdefault(r["cell"], []).append(r)
    for v in by_cell.values():
        v.sort(key=lambda r: r["work_key"])     # deterministic before shuffle

    # allocate N across cells by weighted share
    tot = sum(len(v) * CELL_WEIGHT.get(k, 1.0) for k, v in by_cell.items())
    alloc, chosen = {}, []
    for k, v in sorted(by_cell.items()):
        want = round(N_TARGET * len(v) * CELL_WEIGHT.get(k, 1.0) / tot)
        alloc[k] = min(want, len(v))
    # fix rounding drift against the target
    while sum(alloc.values()) < N_TARGET:
        k = max(alloc, key=lambda k: len(by_cell[k]) - alloc[k])
        if alloc[k] >= len(by_cell[k]):
            break
        alloc[k] += 1
    while sum(alloc.values()) > N_TARGET:
        k = max(alloc, key=lambda k: alloc[k])
        alloc[k] -= 1

    for k, n in sorted(alloc.items()):
        pick = rng.sample(by_cell[k], n)
        p_incl = n / len(by_cell[k])            # inclusion probability
        for r in pick:
            r = dict(r)
            r["p_include"] = round(p_incl, 6)
            r["weight"] = round(1.0 / p_incl, 4)   # inverse-probability weight
            r["stratum_n_population"] = len(by_cell[k])
            r["stratum_n_sampled"] = n
            chosen.append(r)
        print(f"[r1] stratum {k:10s} {n:3d} of {len(by_cell[k]):4d} "
              f"(p={p_incl:.3f}, w={1/p_incl:.2f})")

    rng.shuffle(chosen)                          # interleave strata
    for i, r in enumerate(chosen, 1):
        r["order"] = i
    return chosen


_TAG = re.compile(r"<[^>]+>")


def clean(t: str) -> str:
    return html.escape(_TAG.sub(" ", t or "")).strip()


def build_html(rows) -> str:
    cards = []
    for r in rows:
        qs = "".join(
            f'<div class="q" data-k="{k}"><span class="qt">{html.escape(q)}</span>'
            f'<span class="btns">'
            f'<button class="b y" data-v="Y">Y</button>'
            f'<button class="b n" data-v="N">N</button>'
            f'<button class="b u" data-v="U">U</button></span></div>'
            for k, q in QUESTIONS)
        cards.append(
            f'<section class="card" id="c{r["order"]}" data-wk="{html.escape(r["work_key"])}">'
            f'<div class="hd"><span class="num">{r["order"]}/{len(rows)}</span>'
            f'<span class="mo">{r["month"]}</span></div>'
            f'<h2>{clean(r["title"])}</h2>'
            f'<div class="ven">{clean(r["venue"])}</div>'
            f'<div class="abs">{clean(r["abstract"])}</div>'
            f'<div class="qs">{qs}</div>'
            f'<div class="pce" data-k="pce_value">Declared headline PCE '
            f'(<em>only if you answered Y above</em>): '
            f'<input type="text" inputmode="decimal" placeholder="e.g. 26.1" size="8"></div>'
            f'</section>')

    # NOTE: no f-string here -- the JS/CSS is full of braces.
    tmpl = """<!doctype html><meta charset="utf-8">
<title>R1 label sheet</title>
<style>
:root{--bg:#faf9f7;--fg:#1a1a1a;--mut:#6b6b6b;--acc:#2d6cdf;--bd:#e0ddd8}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,Segoe UI,system-ui,sans-serif;margin:0;padding:0 0 120px}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--bd);padding:10px 20px;display:flex;gap:16px;align-items:center;z-index:9}
header b{font-size:15px}
#prog{color:var(--mut);font-size:14px}
#bar{height:4px;background:var(--bd);border-radius:2px;flex:1;overflow:hidden}
#barf{height:100%;width:0;background:var(--acc);transition:width .2s}
button.act{border:1px solid var(--bd);background:#fff;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:14px}
.card{max-width:820px;margin:26px auto;background:#fff;border:1px solid var(--bd);border-radius:10px;padding:22px 26px;scroll-margin-top:70px}
.card.done{opacity:.5}
.card.cur{border-color:var(--acc);box-shadow:0 0 0 3px rgba(45,108,223,.12)}
.hd{display:flex;justify-content:space-between;color:var(--mut);font-size:13px}
h2{font-size:18px;margin:8px 0 4px;line-height:1.35}
.ven{color:var(--mut);font-size:13px;margin-bottom:12px}
.abs{background:#fbfaf8;border-left:3px solid var(--bd);padding:12px 14px;font-size:15px;white-space:pre-wrap;margin-bottom:18px}
.q{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:7px 0;border-top:1px solid #f0eeea}
.qt{font-size:14.5px}
.btns{display:flex;gap:6px;flex:none}
.b{width:38px;height:32px;border:1px solid var(--bd);background:#fff;border-radius:6px;cursor:pointer;font-weight:600;font-size:13px}
.b.sel{background:var(--acc);color:#fff;border-color:var(--acc)}
.pce{margin-top:12px;font-size:14px;color:var(--mut)}
.pce input{font-size:15px;padding:5px 8px;border:1px solid var(--bd);border-radius:5px}
#help{position:fixed;inset:0;background:rgba(0,0,0,.55);display:none;overflow:auto;z-index:20}
#help.on{display:block}
#helpbox{max-width:720px;margin:40px auto;background:#fff;padding:28px 32px;border-radius:10px;font-size:15px}
#helpbox h3{margin:18px 0 6px}
#helpbox code{background:#f3f1ee;padding:1px 5px;border-radius:3px}
footer{position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid var(--bd);padding:10px 20px;display:flex;gap:12px;align-items:center;font-size:13px;color:var(--mut)}
</style>
<header>
  <b>R1 label sheet</b>
  <div id="bar"><div id="barf"></div></div>
  <span id="prog">0/0</span>
  <button class="act" onclick="help()">? codebook</button>
  <button class="act" onclick="exp()">Export CSV</button>
</header>
__CARDS__
<footer>
  <span><b>Y</b> yes &nbsp; <b>N</b> no &nbsp; <b>U</b> unclear &nbsp; &nbsp;
  <b>&uarr;&darr;</b> move &nbsp; <b>?</b> codebook</span>
  <span id="save" style="margin-left:auto"></span>
</footer>
<div id="help" onclick="help()"><div id="helpbox" onclick="event.stopPropagation()">
<h2>How to label</h2>
<p>Judge <b>only what the abstract says</b>. Not the title, not what the paper
probably did, not what you know about the group. If the abstract does not say
it, the answer is <b>N</b>.</p>
<p>Use <b>U</b> when the text genuinely could be read either way. U is data, not
failure &mdash; it measures how often the abstract itself is ambiguous.</p>

<h3>1. states_pce</h3>
Y if the abstract gives a PCE/efficiency <b>number</b> for a device.
"efficiency improved substantially" is <b>N</b> (no number).

<h3>2. states_certified</h3>
Y only for <b>independent certification</b>: the word certified, or a named lab
(NREL, AIST, Fraunhofer ISE, JET, Newport).
"we measured 25.1%" is <b>N</b>. "uncertified" is <b>N</b>.

<h3>3. states_area</h3>
Y for a device/aperture area with a unit, e.g. <code>0.09 cm2</code>,
<code>1 cm&sup2;</code>, <code>65 cm2 module</code>.
<b>Careful:</b> <code>24.1 mA cm-2</code> is a current density, <b>not</b> an
area &rarr; <b>N</b>.

<h3>4. states_t80</h3>
Y for an operational lifetime figure: T80, T90, "retained 92% after 1000 h".
A storage/shelf number with no operation is still Y if it gives hours.
"stable operation" with no number is <b>N</b>.

<h3>5. isos_protocol</h3>
Y only if an <b>ISOS</b> protocol is named (<code>ISOS-L-1</code>,
<code>ISOS&#8208;D&#8208;3</code>, <code>ISOS-L-2I</code>). Note the hyphen may
be a Unicode dash that looks identical. "ISOS protocols were followed" without a
code is <b>U</b>.

<h3>THE HARD CASE &mdash; read this one twice</h3>
<p>An abstract may report <b>its own device</b> and also <b>quote a record from
another paper</b>. Example: <em>"our p-i-n cell reached 25.8%, approaching the
certified 33.9% of perovskite/Si tandems"</em>.</p>
<p><b>Rule: label only the paper's OWN device.</b> Here states_pce = Y (25.8 is
theirs) and states_certified = <b>N</b> &mdash; the certified 33.9% belongs to
someone else. This exact confusion shipped a wrong number once, so it is the
single most valuable distinction on this sheet.</p>

<h3>Headline PCE box</h3>
Only when states_pce = Y. Type the paper's <b>own best</b> PCE as a bare number
(<code>26.1</code>). Leave blank if unsure. This upgrades the study from
"did it detect a number" to "did it detect the RIGHT number".

<p style="margin-top:22px;color:#6b6b6b">Your answers save automatically in this
browser on every keystroke. Closing the tab is safe. When finished (or when you
want to stop), press <b>Export CSV</b> and send me the file.</p>
</div></div>
<script>
const KEY="r1_labels_v1";
let A=JSON.parse(localStorage.getItem(KEY)||"{}");
const cards=[...document.querySelectorAll(".card")];
let cur=0;

function paint(){
  let done=0;
  cards.forEach((c,i)=>{
    const wk=c.dataset.wk, a=A[wk]||{};
    c.querySelectorAll(".q").forEach(q=>{
      const v=a[q.dataset.k];
      q.querySelectorAll(".b").forEach(b=>b.classList.toggle("sel",b.dataset.v===v));
    });
    const inp=c.querySelector(".pce input");
    if(inp&&a.pce_value!==undefined&&inp.value!==a.pce_value)inp.value=a.pce_value;
    const full=[...c.querySelectorAll(".q")].every(q=>(A[wk]||{})[q.dataset.k]);
    c.classList.toggle("done",full);
    c.classList.toggle("cur",i===cur);
    if(full)done++;
  });
  prog.textContent=done+"/"+cards.length;
  barf.style.width=(100*done/cards.length)+"%";
}
function save(){
  localStorage.setItem(KEY,JSON.stringify(A));
  document.getElementById("save").textContent="saved "+new Date().toLocaleTimeString();
  paint();
}
function set(wk,k,v){ (A[wk]=A[wk]||{})[k]=v; save(); }

document.addEventListener("click",e=>{
  const b=e.target.closest(".b"); if(!b)return;
  const c=b.closest(".card"), q=b.closest(".q");
  set(c.dataset.wk,q.dataset.k,b.dataset.v);
  cur=cards.indexOf(c);
  const qs=[...c.querySelectorAll(".q")];
  const i=qs.indexOf(q);
  if(i===qs.length-1&&qs.every(x=>(A[c.dataset.wk]||{})[x.dataset.k]))go(cur+1);
});
document.addEventListener("input",e=>{
  if(!e.target.closest(".pce"))return;
  set(e.target.closest(".card").dataset.wk,"pce_value",e.target.value.trim());
});
function go(i){
  if(i<0||i>=cards.length)return;
  cur=i; cards[i].scrollIntoView({behavior:"smooth",block:"start"}); paint();
}
document.addEventListener("keydown",e=>{
  if(e.target.tagName==="INPUT"){ if(e.key==="Enter")go(cur+1); return; }
  const k=e.key.toLowerCase();
  if(k==="?"||k==="/"){help();return;}
  if(e.key==="ArrowDown"||k==="j"){go(cur+1);e.preventDefault();return;}
  if(e.key==="ArrowUp"||k==="k"){go(cur-1);e.preventDefault();return;}
  if(!"ynu".includes(k))return;
  const c=cards[cur], wk=c.dataset.wk, a=A[wk]||{};
  const qs=[...c.querySelectorAll(".q")];
  const nx=qs.find(q=>!a[q.dataset.k]);
  if(nx){ set(wk,nx.dataset.k,k.toUpperCase());
    if(qs.every(q=>(A[wk]||{})[q.dataset.k]))setTimeout(()=>go(cur+1),140); }
  e.preventDefault();
});
function help(){ document.getElementById("help").classList.toggle("on"); }
function exp(){
  const hdr=["work_key","__QK__","pce_value"].join(",");
  const lines=[hdr];
  for(const c of cards){
    const wk=c.dataset.wk,a=A[wk]||{};
    lines.push([wk,__QJ__,'"'+(a.pce_value||"")+'"'].join(","));
  }
  const b=new Blob([lines.join("\\n")],{type:"text/csv"});
  const u=URL.createObjectURL(b),x=document.createElement("a");
  x.href=u;x.download="r1_labels_filled.csv";x.click();URL.revokeObjectURL(u);
}
paint(); go(0);
</script>"""
    qkeys = ",".join(k for k, _ in QUESTIONS)
    qjs = ",".join(f'(a.{k}||"")' for k, _ in QUESTIONS)
    return (tmpl.replace("__CARDS__", "\n".join(cards))
                .replace("__QK__", qkeys)
                .replace("__QJ__", qjs))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pop = load_population()
    if not pop:
        raise SystemExit("FAIL-CLOSED: empty population")
    print(f"[r1] population {len(pop)} works with abstracts "
          f"across {len(MONTHS)} months")
    rows = sample(pop)

    # blind CSV fallback -- same schema as the HTML export, answers empty
    cols = ["order", "month", "work_key", "doi", "title", "venue"] + \
           [k for k, _ in QUESTIONS] + ["pce_value"]
    import csv
    with (OUT / "label_sheet.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({**{c: "" for c in cols},
                        "order": r["order"], "month": r["month"],
                        "work_key": r["work_key"], "doi": r["doi"],
                        "title": r["title"], "venue": r["venue"]})

    (OUT / "label_sheet.html").write_text(build_html(rows), encoding="utf-8")

    # The sampling frame is kept SEPARATELY from the sheet: it carries the
    # weights and strata the analysis needs, and none of it may be visible
    # while labelling.
    frame = [{k: r[k] for k in ("order", "month", "work_key", "doi", "cell",
                                "p_include", "weight", "stratum_n_population",
                                "stratum_n_sampled")} for r in rows]
    (OUT / "sampling_frame.json").write_text(
        json.dumps(frame, indent=2), encoding="utf-8")

    prereg = {
        "study": "R1 -- extraction precision and recall against human labels",
        "built": "2026-09-12",
        "seed": SEED,
        "n_target": N_TARGET,
        "months": MONTHS,
        "population": "corpus works carrying an abstract (the pool audit_over() builds)",
        "population_size": len(pop),
        "denominator_check": {
            "audit.corpus.denominator": 456,
            "corpus.n": 648,
            "selection.n_depth": 181,
            "claim_cards": 169,
            "resolved": "audit rates divide by corpus works WITH abstracts, "
                        "so the label population is that pool, NOT the cards",
        },
        "questions": [k for k, _ in QUESTIONS],
        "stratification": "regex flag cell (isos > certified > pce_only > none)",
        "cell_weights": CELL_WEIGHT,
        "primary_metrics": [
            "precision and recall of each extractor flag vs human label",
            "Wilson 95% intervals",
            "inverse-probability weighted population rates",
        ],
        "secondary_metrics": [
            "numeric accuracy of the declared headline PCE",
            "intra-rater agreement (kappa) on a 20-paper re-label",
            "per-extractor-model breakdown (qwen3.8-flash vs glm-5.3-flash)",
        ],
        "blinding": "the sheet shows title, venue and abstract only; no "
                    "extractor output, no pre-filled answer, no flag",
        "labeller": "Havid Aqoma (human). No model may label, pre-label or "
                    "assist any row.",
        "analysis_frozen_before_labelling": True,
    }
    (OUT / "preregistration.json").write_text(
        json.dumps(prereg, indent=2), encoding="utf-8")
    h = hashlib.sha256(
        (OUT / "preregistration.json").read_bytes()).hexdigest()
    (OUT / "preregistration.sha256").write_text(h + "\n", encoding="utf-8")

    print(f"\n[r1] {len(rows)} papers -> {OUT}")
    print(f"[r1] prereg sha256 {h[:16]}")
    print(f"[r1] OPEN: {OUT / 'label_sheet.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
