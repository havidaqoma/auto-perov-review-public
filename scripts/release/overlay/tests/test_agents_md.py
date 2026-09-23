"""AGENTS.md must not drift from the handbooks it summarises.

AGENTS.md is a second statement of a contract whose real home is the three
handbooks. Principle 0.2 of that very contract says a rule enforced only by a
reminder comes back the moment something changes, and principle 0.6 says a
guard that exists twice diverges. A summary file is exactly the thing those
principles warn about, so it only earns its place if a test pins it.

This test asserts that every principle heading quoted in AGENTS.md still
appears verbatim in the handbook it claims to quote, and that no handbook
principle has been added without reaching AGENTS.md. Edit a handbook heading
and this test names the mismatch.

It deliberately does NOT check the explanatory prose. Prose is allowed to be a
loose retelling; headings are the contract.
"""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"

MONTHLY = ROOT / "MASTER_HANDBOOK.md"
H1 = ROOT / "MASTER_HANDBOOK_H1.md"
YEARLY = ROOT / "yearly" / "MASTER_HANDBOOK_YEARLY_v2.md"

# AGENTS.md ships only in the public release tree. In the private repo the
# file is absent by design, so every test here skips rather than fails.
pytestmark = pytest.mark.skipif(
    not AGENTS.exists(),
    reason="AGENTS.md ships in the public release tree only")


def read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def handbook_principles(path: pathlib.Path) -> dict[str, str]:
    """Numbered principle headings from a handbook: {'0.1': 'Format is ...'}."""
    out: dict[str, str] = {}
    for m in re.finditer(r"^#{3}\s+(0\.\d+)\s+(.+?)\s*$", read(path), re.M):
        out[m.group(1)] = m.group(2)
    return out


def agents_principles() -> dict[str, str]:
    """Numbered principles as AGENTS.md states them, from its bullet list."""
    out: dict[str, str] = {}
    for m in re.finditer(r"^-\s+\*\*(0\.\d+)\s+(.+?)\*\*\s*$", read(AGENTS), re.M):
        out[m.group(1)] = m.group(2)
    return out


def test_agents_md_exists_in_release_tree():
    assert AGENTS.is_file()


@pytest.mark.parametrize("handbook", [MONTHLY, H1, YEARLY])
def test_handbooks_are_present(handbook):
    """AGENTS.md routes the reader to these three files by name."""
    assert handbook.is_file(), f"AGENTS.md cites {handbook.name}, which is missing"


def test_every_quoted_principle_matches_its_handbook():
    """A heading quoted in AGENTS.md must exist verbatim in a handbook."""
    real = {**handbook_principles(MONTHLY), **handbook_principles(H1)}
    quoted = agents_principles()
    assert quoted, "AGENTS.md has no numbered principle bullets; parser or file broke"

    wrong: list[str] = []
    for num, text in sorted(quoted.items()):
        if num not in real:
            wrong.append(f"{num}: AGENTS.md states it, no handbook defines it")
        elif real[num] != text:
            wrong.append(
                f"{num}: AGENTS.md says {text!r}, handbook says {real[num]!r}")
    assert not wrong, (
        "AGENTS.md has drifted from the handbooks:\n  " + "\n  ".join(wrong) +
        "\n\nThe handbook is the source of truth. Update AGENTS.md to match it.")


def test_no_handbook_principle_is_missing_from_agents_md():
    """A new principle must reach AGENTS.md, or agents will never see it."""
    real = {**handbook_principles(MONTHLY), **handbook_principles(H1)}
    missing = sorted(set(real) - set(agents_principles()))
    assert not missing, (
        "these handbook principles are absent from AGENTS.md: " +
        ", ".join(f"{n} ({real[n]!r})" for n in missing) +
        "\n\nAn agent reading AGENTS.md would never learn them. Add them.")


def test_yearly_extra_principles_are_carried():
    """Yearly numbers its extra principles 6-8 in a list, not as headings.

    They are real rules and an agent working the yearly cadence needs them, so
    AGENTS.md must carry their substance. Match on a distinctive phrase from
    each rather than the full sentence, because the yearly handbook states them
    in list form and AGENTS.md restates them as a short list.
    """
    a = read(AGENTS).lower()
    y = read(YEARLY).lower()
    for phrase in ("never widen a gate",
                   "stops noticing",
                   "is not an artifact that shipped"):
        assert phrase in y, f"{phrase!r} no longer in the yearly handbook"
        assert phrase in a, (
            f"yearly principle {phrase!r} is missing from AGENTS.md")


def test_agents_md_points_at_the_real_entry_points():
    """The routing table must name files that exist."""
    a = read(AGENTS)
    for rel in ("reproduce.py",
                "scripts/run_month.py",
                "scripts/stages/s18d_build_v4.py",
                "config/gates.yaml",
                "config/models.yaml",
                "yearly/scripts/run_yearly.py",
                "tools/ship_audit.py",
                ".env.example"):
        assert rel in a, f"AGENTS.md no longer mentions {rel}"
        assert (ROOT / rel).exists(), (
            f"AGENTS.md sends an agent to {rel}, which does not exist")


def test_agents_md_states_the_structural_model_contract():
    """Swapping models is fine; losing these three guarantees is not."""
    a = read(AGENTS)
    for token in ("writer_rule: strict", "fallback_policy: fail_closed"):
        assert token in a, f"AGENTS.md no longer states {token!r}"
        assert token in read(ROOT / "config" / "models.yaml"), (
            f"{token!r} is in AGENTS.md but no longer in config/models.yaml")
