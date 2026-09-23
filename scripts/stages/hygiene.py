"""Canonical prose-hygiene filter. ONE definition, imported everywhere.

Why this module exists
----------------------
The narration guard used to be copied into three files: `s13d_draft_v4.py`
(strips per line while drafting), `s18d_build_v4.py` (gate G4), and
`s19_si.py` (`strip()` for SI notes). The copies drifted, and the build-side
copy was the NARROWEST of the three.

That produced the worst possible failure on the August v4 issue. The writer
opened section 8 with:

    I have launched the search command and will wait for it to finish.

It survived the draft filter, then also passed G4, so the sentence reached the
rendered PDF sitting directly under the "8. Research Gaps and Outlook"
heading. Havid found it by reading the page. G4 reported `pass` on leaked
text, which is worse than no gate at all: a gate that cannot fail teaches you
to trust output you should be checking.

Why both copies missed it, precisely:
  - `the command has been launched` was an EXACT phrase. The writer wrote
    "I have launched the search command" -- same meaning, different voice.
  - `\bI (?:will|'ll) wait\b` required "I" adjacent to "will wait". The writer
    wrote "and will wait for it to finish".
  - `waiting for ...` required the gerund. The writer wrote "wait for it".

So the taxonomy was written from remembered sentences instead of from the
GRAMMAR of the failure. Three near-misses on one line.

Design rules for this file
--------------------------
1. One definition. `s13d`, `s18d` and `s19` all import from here. A test
   asserts they are the same object, so divergence fails the suite.
2. Case-insensitivity via `flags=`, never inline `(?i)`. Python 3.11 raises
   "global flags not at the start of the expression" for any `(?i)` past
   position 0, and 26 of them once killed stage 13c at import.
3. Patterns are written as CLASSES OF SENTENCE, not as remembered strings.
   Every class below reached a shipped draft or PDF at least once.
4. First-person or tool-noun scoping on the aggressive patterns, so ordinary
   review prose is never touched. "research" must never match "search";
   every token is `\b`-bounded.
"""
from __future__ import annotations

import re

# Tool/process nouns that have no place in a scientific review. Used to scope
# the launch/wait patterns so they cannot fire on real prose.
_TOOL_NOUN = (r"(?:search|command|script|query|task|tool|output|file|timer|"
              r"build|test|run|job|process|directory|listing)")

AGENT_NARRATION = re.compile(
    # ---- class 1: progress / waiting narration -------------------------
    # "Waiting for the task to complete." -- 25 such lines shipped in a v3 PDF.
    r"^\s*waiting for\b"
    r"|\bwaiting for (?:the |a |an )?" + _TOOL_NOUN +
    r"|\bwaiting (?:for it|for them|on it) to\b"
    # ---- class 2: launch + future-wait ---------------------------------
    # "I have launched the search command and will wait for it to finish."
    # Reached the shipped August v4 PDF under the section 8 heading. The old
    # patterns wanted the exact phrase "the command has been launched" and
    # "I will wait" adjacent, so all three clauses here missed.
    r"|\bI(?:\s+have|'ve|\s+just|\s+already)?\s+"
    r"(?:launched|started|initiated|executed|issued|submitted|kicked off|ran|run)\b"
    r"|\b(?:launching|starting|initiating|executing|issuing|submitting|running)\s+"
    r"(?:the |a |an |another )?" + _TOOL_NOUN +
    r"|\bthe " + _TOOL_NOUN + r" (?:has been|is being|was) (?:launched|started|issued|run)\b"
    r"|\bwill wait\b|\bI'?ll wait\b|\bwe will wait\b"
    r"|\bwait for (?:it|them|this|that|these|those)\b"
    r"|\bonce (?:it|the " + _TOOL_NOUN + r") (?:finishes|completes|returns|is done)\b"
    # A CLOSED VERB LIST IS NOT A GRAMMAR. This clause used to require one of
    # (check|run|see|look|verify|search|query|fetch|retrieve|inspect)
    # immediately after the intent marker, so "Let me pull up the remaining
    # records before I carry on with this part." walked through untouched and
    # reached the rendered PDF (fault injection FI-08, 2026-09-11). The filter
    # was recognising REMEMBERED SENTENCES, not the shape of the failure.
    #
    # The shape is: FIRST-PERSON INTENT MARKER + ANY ACTION VERB. Matching the
    # marker plus an arbitrary following verb covers the whole class, including
    # paraphrases nobody has written yet.
    #
    # "let me" is first-person singular framing and is never legitimate in a
    # review, so any verb may follow it. "let us" / "let's" is DIFFERENT:
    # "let us consider the case of" is ordinary academic prose, so that form
    # keeps the tool-verb scoping and must not be generalised.
    r"|\blet me\b"
    r"|\b(?:let us|let's)\s+"
    r"(?:check|run|see|look|verify|search|query|fetch|retrieve|inspect|pull)\b"
    r"|\b(?:I will|I'll|I am going to|I'm going to|I need to|I have to|"
    r"I should|I can now|I shall)\s+\w+"
    # continuation narration: the second half of the FI-08 sentence, which is
    # its own class -- an agent announcing that it is resuming work.
    r"|\bI\s+(?:carry on|carry|proceed|continue|resume|move on|get back|pick up)\b"
    r"|\b(?:carry on|move on|proceed|continue)\s+with\s+(?:this|the|that)\s+"
    r"(?:part|section|task|step|one|work)\b"
    r"|\bbefore I\b|\bafter I\b"
    r"|\bnow (?:I|let me|we)\b|\bnext,? I (?:will|'ll)\b"
    # ---- class 3: tool / filesystem vocabulary -------------------------
    r"|\b(?:task[- ]\d+|stdout|stderr|exit code|directory listing|file write)\b"
    r"|\b(?:timer to (?:fire|expire)|cooldown to elapse)\b"
    r"|\b(?:running|executing|launching) the (?:script|command|test|build)\b"
    # ---- class 4: file-path / save reporting ----------------------------
    r"|(?:written|saved|output|wrote|writing)\s+(?:to|into)\s+[`'\"]?(?:runs/|draft/|sec\d)"
    # ---- class 5: self-reported gate or word-count results --------------
    r"|\bgate checks?\b|\bchecks? pass\b|\b\d{2,4}\s+words?\b"
    r"|\bover the\s+\d+[- ]?word\b|\bover the\s+\d+\s+limit\b"
    r"|\bword (?:count|limit|ceiling)\b|\bcondensing\b|\btrimming\b"
    r"|\bbanned[- ]vocabular|\bsentence[- ]rhythm\b"
    r"|\ball (?:four|three|five) mandated\b"
    # ---- class 6: conversational framing --------------------------------
    r"|\bI (?:have |'ve |will |'ll )?(?:written|drafted|produced|condensed|revised)\b"
    r"|\bas requested\b|\bhere is (?:the|your)\b|\bbelow is (?:the|your)\b"
    r"|^\s*(?:ok|okay|done|note|sure)\b\s*[:.\-]",
    re.I | re.M)

# Historical alias. s18d's gate and s19's strip() both used their own name for
# the same concept; both now point at the single compiled object above.
LEAK_RX = AGENT_NARRATION
SELF_REF = AGENT_NARRATION


def strip_narration(raw: str) -> tuple[str, list[str]]:
    """Remove narration LINE BY LINE and report what was removed.

    Per-line, never per-section: an early version discarded whole sections and
    threw away three usable drafts, while the identical prompt run by hand
    produced clean prose. The model intermittently wraps one status line around
    real content, so the content is worth keeping and the line is not.

    Returns (cleaned_text, removed_lines) so a caller can log or gate on what
    was taken out rather than silently dropping it.
    """
    keep, removed = [], []
    for ln in raw.splitlines():
        if ln.strip() and AGENT_NARRATION.search(ln):
            removed.append(ln.strip())
        else:
            keep.append(ln)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(keep)).strip(), removed


def find_narration(text: str) -> list[str]:
    """Every narration match in `text`, for gate reporting."""
    return AGENT_NARRATION.findall(text)


# Sentences that ACTUALLY reached a shipped draft or PDF. Any change to the
# pattern above must keep every one of these matching; tests assert it.
KNOWN_LEAKS = [
    "I have launched the search command and will wait for it to finish.",
    "Waiting for the task to complete.",
    "The command has been launched.",
    "Let me check the output.",
    "I will wait for the timer to fire.",
    "Saved to runs/2026-08/sec8.md",
    "This section is 1030 words, over the 900 limit.",
    "Gate checks pass.",
    "As requested, here is the section.",
    "OK: done.",
    "stdout was empty",
    "I have drafted the section.",
    "Now I will condense.",
    "Next, I will verify the counts.",
    # paraphrases of the August v4 leak, same grammar, different wording
    "I've started the search and will wait.",
    "Launching the search command now.",
    "I ran the query and will wait for it to return.",
    "I just executed the script.",
    "Once it finishes I will summarise.",
    "The search has been started.",
    # FI-08 (fault injection, 2026-09-11). This reached the rendered PDF while
    # the filter reported clean, because the intent-marker clause required a
    # verb from a CLOSED LIST and "pull up" was not on it. A closed verb list
    # is not a grammar. Kept here as the canonical regression case.
    "Let me pull up the remaining records before I carry on with this part.",
    # unseen paraphrases of the same grammar, to prove the class generalises
    # rather than memorising the sentence above
    "I need to gather the rest of the data.",
    "Let me summarise what I found so far.",
    "I should verify these counts first.",
    "Before I continue, I will fetch the rest.",
    "I am going to compile the list.",
]

# Legitimate review prose that must NEVER be stripped. "research" contains
# "search"; "we will wait" is narration but "carriers wait" is not a phrase a
# reviewer writes, so the tool-noun scoping is what keeps this list clean.
KNOWN_CLEAN = [
    "Buried-interface passivation improves open-circuit voltage.",
    "Certified efficiency reached 27.12% on a 1.0 cm2 aperture.",
    "Wide-bandgap absorbers remain limited by halide segregation.",
    "Operational stability was tracked for 2125 h under one sun.",
    "Ion migration accelerates under forward bias.",
    "Further research is required to separate these mechanisms.",
    "The search for defect-tolerant absorbers has narrowed.",
    "A systematic search of the indexed literature identified 531 works.",
    "Researchers report a certified 33.66% tandem efficiency.",
    "The command of interfacial chemistry has improved markedly.",
    "Run-to-run variation in coating thickness remains unquantified.",
    "Task-specific passivation strategies diverge between architectures.",
]
