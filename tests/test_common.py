import pathlib

import pytest
import yaml

from common import cleaners, csvio, dates, doi, ledger, net, titles

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"

# --- titles --------------------------------------------------------------
T_REC = ("Cs0.05FA0.85MA0.10Pb(I0.6Br0.4)3 perovskite solar cells with "
         "<sub>2D</sub> capping for certified efficiency")


def test_clean_title_subscript_content_kept():
    c = titles.clean_title(T_REC)
    assert "<sub>" not in c and "</sub>" not in c
    assert "Cs0.05FA0.85MA0.10Pb(I0.6Br0.4)3" in c
    assert "  " not in c


def test_clean_title_latex_and_entities():
    c = titles.clean_title("Efficiency &amp; stability of $\\alpha$-FAPbI$_3$ films")
    assert "&" in c and "\\alpha" not in c and "\\_" not in c


def test_title_hash_stable():
    assert titles.title_hash("Same Title Here") == titles.title_hash("same title here")


def test_containment_rules():
    base = "passivation of perovskite solar cells toward record certified efficiency"
    assert len(base) > 30
    assert titles.containment(base + " by 2D capping", base)
    assert not titles.containment("short", base)


# --- doi -----------------------------------------------------------------
def test_doi_norm_url_case_trailing():
    assert doi.norm_doi("HTTPS://dx.doi.org/10.1002/PIP.3919.") == "10.1002/pip.3919"


# --- dates ---------------------------------------------------------------
def test_month_window():
    assert dates.month_window("2024-02") == ("2024-02-01", "2024-02-29")
    assert dates.month_window("2026-08") == ("2026-08-01", "2026-08-31")


def test_band():
    assert dates.in_band(535) and not dates.in_band(0) and not dates.in_band(5000)


# --- cleaners ------------------------------------------------------------
def test_bibtex_escape():
    out = cleaners.bibtex_escape("A & B #1: 100% Cs0.05FA0.85MA0.10Pb(I0.6Br0.4)3")
    assert "\\&" in out and "\\%" in out and "\\#" in out
    assert "Cs0.05FA0.85MA0.10Pb(I0.6Br0.4)3" in out
    assert cleaners.bibtex_escape(out) == out  # idempotent


# --- csv -----------------------------------------------------------------
def test_csv_utf8sig_roundtrip(tmp_path):
    p = tmp_path / "x.csv"
    csvio.write_rows(p, ["No", "Full Title", "Lang"], [["1", "日本語タイトル", "ja"]])
    raw = p.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM for Excel
    rows = csvio.read_rows(p)
    assert rows[0]["Lang"] == "ja" and rows[0]["Full Title"] == "日本語タイトル"


# --- config loadability --------------------------------------------------
def test_config_files_load():
    # csv_columns.yaml / prose_rules.yaml were archived at T-01b (Q42):
    # the 22-column CSV is superseded by the 23-column spec in v5 3.2, and
    # prose_rules.yaml is superseded by hygiene.yaml at T-04. Asserting they
    # are GONE is the regression that stops them being quietly resurrected.
    assert not (CONFIG / "csv_columns.yaml").exists()
    assert not (CONFIG / "prose_rules.yaml").exists()

    axes = yaml.safe_load((CONFIG / "axes.yaml").read_text(encoding="utf-8"))["axes"]
    assert len(axes) == 6 and all(axes[k]["keywords"] for k in axes)
    wl = yaml.safe_load((CONFIG / "venue_whitelist.yaml").read_text(encoding="utf-8"))["venues"]
    assert len(wl) >= 25
    m = yaml.safe_load((CONFIG / "models.yaml").read_text(encoding="utf-8"))
    assert m["allocation"] in ("option_a", "option_b")


def test_axes_names_match_plan_5_6():
    """Q51: axes.yaml on disk used devices_tandems/scaleup; the plan 5.6 names
    are canonical. Without this the Q50 title slot_axis check rejects every
    title, since slot_axis must be one of these six or `audit`."""
    axes = yaml.safe_load((CONFIG / "axes.yaml").read_text(encoding="utf-8"))["axes"]
    assert set(axes) == {
        "composition", "defects", "interfaces",
        "architecture", "stability", "scale_up",
    }, f"axes.yaml keys drifted from plan 5.6: {sorted(axes)}"


# --- net (R20 regression: key never leaves api.openalex.org) -------------
def test_net_oa_rejects_foreign_host():
    with pytest.raises(AssertionError):
        net.oa("https://www.scimagojr.com/journalrank.php")


def test_net_plain_never_carries_key(monkeypatch):
    captured = {}

    class FakeResp:
        status_code = 200
        headers = {}

        @staticmethod
        def raise_for_status():
            pass

        @staticmethod
        def json():
            return {"ok": True}

    def fake_get(url, **kwargs):
        captured["url"] = url
        return FakeResp()

    monkeypatch.setattr(net.requests, "get", fake_get)
    net.plain("https://api.openalex.org/sources/S4310319961")
    assert "api_key" not in captured["url"]


# --- ledger (two-phase, idempotent, overlap guarantee) -------------------
def _rec(title, doi_norm="", oa_id="", arx_id=""):
    return {"title": title, "doi_norm": doi_norm, "openalex_id": oa_id,
            "arxiv_id": arx_id, "first_seen": "2026-09-05", "payload_hash": "p"}


T1 = "Double-side passivation of perovskite solar cells toward certified efficiency and stability"


def test_ledger_two_phase_and_idempotent(tmp_path):
    db = tmp_path / "ledger.sqlite3"
    r1 = tmp_path / "runs" / "h1"
    recs = [
        _rec(T1, doi_norm="10.1002/pip.3919", oa_id="W1"),          # new
        _rec("Different title same DOI", doi_norm="10.1002/pip.3919"),  # dup by doi
        _rec(T1 + " by 2D capping", doi_norm="10.1021/other.1"),    # dup by containment
        _rec("Wide-bandgap perovskite solar cells with rubidium cation engineering for tandems",
             doi_norm="10.1021/jacs.2x", oa_id="W9"),               # new
    ]
    ledger.append_pending(r1, recs, "h1", "2026-07")
    res = ledger.finalize_run(db, r1, "h1", "2026-07", {"n": 4})
    assert res == {"finalized": True, "added": 2, "dup": 2, "total": 2}
    # idempotency: same run never merges twice
    res2 = ledger.finalize_run(db, r1, "h1", "2026-07", {"n": 4})
    assert res2["finalized"] is False
    # cross-run overlap via openalex id
    r2 = tmp_path / "runs" / "h2"
    ledger.append_pending(r2, [_rec("Entirely different title but same work",
                                    doi_norm="10.1063/revised", oa_id="W1")], "h2", "2026-07")
    res3 = ledger.finalize_run(db, r2, "h2", "2026-07", {"n": 1})
    assert res3 == {"finalized": True, "added": 0, "dup": 1, "total": 2}


# --- R34: redaction is mechanical, never left to the writer ---------------
def test_redact_masks_key_and_email():
    from common.net import redact
    assert "SECRET123" not in redact("https://api.openalex.org/works?api_key=SECRET123")
    # Unpaywall carries the contact address in the query string; a probe note
    # pasted into docs/PROBES_v5.md would otherwise publish it into a history
    # that T-47 scans before public release.
    assert "aqoma.havid" not in redact("https://api.unpaywall.org/v2/10.1/x?email=aqoma.havid@gmail.com")
    assert "abc" not in redact("x&token=abc")
    assert redact("") == ""
