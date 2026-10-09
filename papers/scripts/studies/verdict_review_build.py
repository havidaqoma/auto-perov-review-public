"""Build a one-page sheet for the operator to confirm the hand verdicts.

The R3 and R5 ungrounded values were classified by the Hermes conductor
(Claude), not by the extractor under test (qwen). The operator still has to
confirm them. This page shows, per value: the abstract with the quoted span
highlighted, the value the extractor returned, the verdict and why, and two
buttons (Agree / Disagree + note). Export CSV writes verdict_confirmations.csv;
confirm_verdicts.py then records the result.

Offline, no network, answers saved in the browser as you click.
"""
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "papers" / "scripts"))
from studies.rescore_metric import texts  # noqa: E402

ST = ROOT / "papers" / "studies"
OUT = ST / "verdict_review.html"
REVIEWS = [("R3", "r3_ungrounded_review.json",
            "Generic prompt, abstract in context"),
           ("R5", "r5_ungrounded_review.json",
            "Production prompt, gate off")]


def rows() -> list:
    out = []
    for study, fname, arm in REVIEWS:
        d = json.loads((ST / fname).read_text(encoding="utf-8"))
        for r in d["rows"]:
            out.append({**r, "study": study, "arm": arm,
                        "id": f"{study}|{r['work_key']}|{r['field']}|{r['value']}"})
    return out


def mark(abstract: str, quote: str) -> str:
    a, q = html.escape(abstract), html.escape(quote)
    i = a.find(q)
    if i < 0:
        raise SystemExit(f"FAIL-CLOSED: quote not found verbatim: {quote!r}")
    return a[:i] + "<mark>" + q + "</mark>" + a[i + len(q):]


CSS = """
body{font:16px/1.5 system-ui,Segoe UI,sans-serif;max-width:900px;margin:0 auto;padding:16px;color:#222}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #ccc;padding:8px 0;z-index:2}
.card{border:1px solid #ccc;border-radius:8px;padding:14px;margin:14px 0}
.card.done{border-color:#2a7;background:#f5fbf7}.card.no{border-color:#c33;background:#fdf5f5}
.meta{color:#666;font-size:13px}.abs{background:#fafafa;padding:10px;border-radius:6px}
mark{background:#ffe066;padding:0 2px}.v{font-size:18px;margin:8px 0}
.b{font-size:16px;padding:6px 18px;margin-right:8px;border-radius:6px;border:1px solid #888;background:#fff;cursor:pointer}
.b.sel.y{background:#2a7;color:#fff}.b.sel.n{background:#c33;color:#fff}
textarea{width:100%;margin-top:6px}.cls{color:#555;font-size:14px}
"""

JS = """
const KEY="verdict_review_v1";
let A=JSON.parse(localStorage.getItem(KEY)||"{}");
const cards=[...document.querySelectorAll(".card")];
function paint(){let d=0;cards.forEach(c=>{const a=A[c.dataset.id]||{};
 c.querySelectorAll(".b").forEach(b=>b.classList.toggle("sel",b.dataset.v===a.v));
 const t=c.querySelector("textarea");if(a.note!==undefined&&t.value!==a.note)t.value=a.note;
 c.classList.toggle("done",a.v==="agree");c.classList.toggle("no",a.v==="disagree");if(a.v)d++;});
 prog.textContent=d+" of "+cards.length+" answered";}
function save(){localStorage.setItem(KEY,JSON.stringify(A));paint();}
document.addEventListener("click",e=>{const b=e.target.closest(".b");if(!b)return;
 const id=b.closest(".card").dataset.id;(A[id]=A[id]||{}).v=b.dataset.v;save();});
document.addEventListener("input",e=>{if(e.target.tagName!=="TEXTAREA")return;
 const id=e.target.closest(".card").dataset.id;(A[id]=A[id]||{}).note=e.target.value;save();});
function exp(){const L=["id,answer,note"];for(const c of cards){const a=A[c.dataset.id]||{};
 L.push(['"'+c.dataset.id+'"',a.v||"",'"'+(a.note||"").replace(/"/g,"'")+'"'].join(","));}
 const b=new Blob([L.join("\\n")],{type:"text/csv"}),u=URL.createObjectURL(b),x=document.createElement("a");
 x.href=u;x.download="verdict_confirmations.csv";x.click();URL.revokeObjectURL(u);}
paint();
"""


def main() -> int:
    abst, title = texts()
    rs = rows()
    classes = json.loads((ST / "r5_ungrounded_review.json").read_text(
        encoding="utf-8"))["classes"]
    cards = []
    for n, r in enumerate(rs, 1):
        wk = r["work_key"].lower()
        if wk not in abst:
            raise SystemExit(f"FAIL-CLOSED: no abstract for {wk}")
        cards.append(
            f'<div class="card" data-id="{html.escape(r["id"])}">'
            f'<div class="meta">{n} of {len(rs)} &middot; {r["study"]} '
            f'({html.escape(r["arm"])}) &middot; {html.escape(r["work_key"])}</div>'
            f'<b>{html.escape(title.get(wk, ""))}</b>'
            f'<div class="abs">{mark(abst[wk], r["quote"])}</div>'
            f'<div class="v">Extractor wrote <b>{html.escape(r["field"])} = '
            f'{html.escape(str(r["value"]))}</b></div>'
            f'<div>My verdict: <b>{html.escape(r["verdict"])}</b> &mdash; '
            f'{html.escape(r["why"])}</div>'
            f'<div class="cls">({html.escape(classes[r["verdict"]])})</div><p>'
            f'<button class="b y" data-v="agree">Agree</button>'
            f'<button class="b n" data-v="disagree">Disagree</button></p>'
            f'<textarea rows="2" placeholder="Optional note (say why if you disagree)">'
            f'</textarea></div>')
    page = (
        "<!doctype html><meta charset='utf-8'><title>Confirm hand verdicts</title>"
        f"<style>{CSS}</style><header><b>Confirm the hand verdicts</b> &middot; "
        "<span id='prog'></span> &middot; <button onclick='exp()'>Export CSV</button>"
        "<div class='meta'>For each value: read the yellow quote, check the "
        "number and my verdict, press Agree or Disagree. Answers save in this "
        "browser as you click. When done press Export CSV.</div></header>"
        + "".join(cards) + f"<script>{JS}</script>")
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} with {len(rs)} values")
    return 0


if __name__ == "__main__":
    sys.exit(main())
