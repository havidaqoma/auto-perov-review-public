"""The final-edition table must be declared once, in agreement, in two places.

scripts/release/release_layout.py decides which edition the public tree ships;
scripts/stages/editions.py tells the tests where that edition lives. If they
disagreed, the release would ship one edition while its tests read another.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stages import editions  # noqa: E402


def test_final_edition_tables_agree():
    rl = ROOT / "scripts" / "release" / "release_layout.py"
    if not rl.exists():
        return          # the builder does not ship in the public tree
    sys.path.insert(0, str(rl.parent))
    import release_layout
    assert {p: v for p, (_, _, v) in release_layout.FINAL.items()} == editions.FINAL


def test_every_final_edition_is_on_disk():
    for period in editions.FINAL:
        for stem, ext in (("manuscript", ".pdf"), ("supplementary", ".md"),
                          ("supplementary", ".pdf")):
            f = editions.edition_file(ROOT, period, stem, ext)
            assert f.exists(), f
        assert editions.manuscript_md(ROOT, period).exists(), period
