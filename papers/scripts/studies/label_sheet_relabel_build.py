"""R1b: build the 20-paper re-label sheet for intra-rater reliability (kappa).

THE INSTRUMENT MUST BE IDENTICAL. This does not copy the builder -- it IMPORTS
it and rewrites three strings. A copy-paste clone drifts (the narration filter
lived in three divergent copies and the narrowest one shipped a leak into a
PDF), and a drifted form would make kappa measure the instrument instead of the
labeller.

THE SILENT-PERFECT-SCORE DEFECT. The primary sheet saves answers under
localStorage["r1_labels_v1"]. Chrome treats every file:// page as ONE origin,
so a re-label sheet reusing that key silently restores all 100 previous
answers, renders with buttons already selected, and a labeller clicking through
produces kappa = 1.00 that is pure artifact. It looks like a perfect result,
not an error -- the silent-zero class exactly. Two independent defences are
applied: a distinct storage key AND a distinct export filename, then the built
file is asserted to contain neither of the primary's strings.

FRESH NUMBERING. Cards are renumbered 1..20 in a newly shuffled order. Showing
"paper 42 of 100" would cue positional memory and inflate agreement.

Run: python -u scripts/studies/label_sheet_relabel_build.py
"""
from __future__ import annotations

import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from studies import label_sheet_build as B  # noqa: E402

OUT = B.OUT
PRIMARY_KEY = "r1_labels_v1"
PRIMARY_FILE = "r1_labels_filled.csv"
RELABEL_KEY = "r1_relabel_v1"
RELABEL_FILE = "r1_relabel_filled.csv"
SHUFFLE_SEED = 20260913
CARD_MARK = 'class="card"'


def main() -> int:
    frame_p = OUT / "relabel_frame.json"
    if not frame_p.exists():
        raise SystemExit("FAIL-CLOSED: relabel_frame.json missing. The draw is "
                         "pre-registered and committed BEFORE the sheet is built.")
    fr = json.loads(frame_p.read_text(encoding="utf-8"))
    want = set(fr["work_keys"])
    print(f"[r1b] pre-registered draw: {len(want)} keys, seed {fr['seed']}")

    pop = {r["work_key"]: r for r in B.load_population()}
    missing = want - set(pop)
    if missing:
        raise SystemExit(f"FAIL-CLOSED: {len(missing)} pre-registered keys are "
                         f"not in the population: {sorted(missing)[:3]}")

    rows = [dict(pop[k]) for k in sorted(want)]
    random.Random(SHUFFLE_SEED).shuffle(rows)
    for i, r in enumerate(rows, 1):
        r["order"] = i                      # fresh 1..20, not the 1..100 index

    html = B.build_html(rows)
    # The ONLY deliberate differences from the primary instrument.
    html = html.replace(f'const KEY="{PRIMARY_KEY}"', f'const KEY="{RELABEL_KEY}"')
    html = html.replace(f'x.download="{PRIMARY_FILE}"', f'x.download="{RELABEL_FILE}"')
    html = html.replace("<title>R1 label sheet</title>",
                        "<title>R1 re-label (reliability check)</title>")
    html = html.replace("<b>R1 label sheet</b>",
                        "<b>R1 re-label &mdash; reliability check</b>")

    # Assert the isolation actually landed. A .replace() that silently matched
    # nothing would ship the primary key and fake a perfect score.
    n_cards = html.count(CARD_MARK)
    checks = [
        (PRIMARY_KEY not in html, "primary localStorage key still present"),
        (PRIMARY_FILE not in html, "primary export filename still present"),
        (f'const KEY="{RELABEL_KEY}"' in html, "re-label key did not land"),
        (RELABEL_FILE in html, "re-label export filename did not land"),
        (n_cards == len(rows), f"expected {len(rows)} cards, found {n_cards}"),
        # No answer may be baked into the markup: 'sel' must appear ONLY inside
        # the JS that toggles it at runtime, never as a static class attribute.
        ('b sel"' not in html and 'sel "' not in html,
         "a button is pre-selected in the markup"),
    ]
    for ok, msg in checks:
        if not ok:
            raise SystemExit(f"FAIL-CLOSED: {msg}")

    out = OUT / "relabel_sheet.html"
    out.write_text(html, encoding="utf-8")
    print(f"[r1b] {n_cards} cards -> {out}")
    print(f"[r1b] storage key {RELABEL_KEY!r}, export {RELABEL_FILE!r}")
    print("[r1b] isolation asserted: primary key and filename both absent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
