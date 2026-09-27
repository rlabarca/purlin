"""Fail when a retired term appears in a tracked file.

The retired spellings and what replaced each one are listed in
`references/glossary.md`; that table is the one place in the repository where
they may still be written.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Whole words, case-insensitive. `Untested` and `test_` never match `tested`
# because the match is bounded on both sides.
# `platform` is not here. It was retired with the platform registry and came
# back in 0.10.0 meaning one thing: an operating system a counting run
# covered, which the passed cell lists under `platforms`. The registry's own
# spellings stay retired, in LITERALS below.
WORDS = ("gauge", "HOLLOW", "PROVABLE", "receipt", "mutation score",
         "caught score", "records branch", "forge", "queue", "CODEOWNERS", "approver rule",
         # the 0.10.0 three-level model
         "tested", "recorded", "approved", "approve", "approval", "approver", "approvers",
         "verified", "verdict", "reviewed", "re-verify",
         # the bar replaced it; the two levels that asked for a person became
         # `[bar: strong]` and the one that did not became `[bar: passed]`
         "risk", "risks",
         # decision 33: nothing scans a proof or a test before the AI audit
         "free scan", "free scans", "hint", "hints")
LITERALS = ("@on(",                     # not a word: the retired scope tag
            "platform registry", "--platform",
            "Proof ready", "lowest state", "seven states", "auto-approval", "review queue",
            "purlin:verify", "purlin:review", "purlin:approve", "verify_gate", "verify-gate:",
            "validated/",
            "needs a person", "needs_person", "needs-a-person",
            # the source a person's own record had, and the two flags that
            # went with it. `developer` as a plain English word stays legal,
            # so only the machine spellings are retired.
            "`developer`", "'developer'", '"developer"',
            "--commit", "purlin:audit --remote",
            # the bar retired these three in one move
            "manual audit", "not required", "ai_review_at",
            # signing is logged, not policed: no list says who may sign,
            # no branch has to carry the signature, and nothing compares the
            # signer with the test's author. The plain word `signers` stays
            # legal; only the config key's spellings are retired.
            "signer list", "Signer list", "`signers`", "'signers'", '"signers"',
            "protected branch", "Protected branch", "is_ancestor",
            "self-signing", "Self-signing",
            # decision 34: the arm `purlin:test` runs is named for what it
            # does, and the old spelling is an unknown flag
            "--quick",
            # decision 41: the periphery is removed. One settings file,
            # committed.
            "config.local.json",
            "anchor propose", "upstream-check",
            "tools/PM", "tools/QA", "pack_tools", "scan.py",
            "purlin:find", "purlin:rename", "--resolve",
            # decision 38: a proof says less. No kind of test on a proof
            # line, and no flag or variable that filtered by one
            "@integration", "@e2e", "@unit", "--tier", "PURLIN_PROOF_TIER",
            # and no design is tied to a spec
            "designs/", "design_hash", "CHANGED_DESIGNS")

# The review list is the one place a person is needed, and its header is the
# one sentence that may still say so. A line is stepped over only when every
# hit on it falls inside one of these phrases.
ALLOWED_PHRASES = ("rules need a person", "rule needs a person")
CASED = (re.compile(r"\bPages\b"),)     # capitalised only; "pages" of a document is fine
MD_ONLY = (re.compile(r"\bmode\b", re.I),)  # "mode" is only retired in prose

PATTERNS = [re.compile(r"\b" + re.escape(w) + r"\b", re.I) for w in WORDS]

EXCLUDED = (
    "references/glossary.md",   # the retired table itself
    "design/tokens/",           # an external design system's tokens, copied in verbatim
    "dev/fixtures/upgrade-0.9.5/",  # an old project layout, kept wrong on purpose
    "dev/plans/",               # the plan names what it retires
    "dev/test_vocabulary.py",   # this file lists the terms
    "RELEASE_NOTES.md",         # historical entries record what shipped, under
                                # the names it shipped under; the 0.10.0 section
                                # is held to this vocabulary by review
    ".purlin/",                 # records and briefs are machine output
)

# Paths a later phase of dev/plans/three-levels.md still rewrites, grouped by
# the lane that owns them. A lane deletes its entries in the commit that
# rewrites the files; the tuple is empty at closeout.
PENDING_REWRITE = ()

# Phase 7 deletes every signature directory of the old layout; until then the
# files inside carry the old words.
PENDING_DELETE = (".approvals/",)

SKIP = EXCLUDED + PENDING_REWRITE

# A migration or a parser has to name what it detects, and a test has to write
# the spelling it feeds the parser. Those lines end with the marker for their
# file type, and this proof steps over exactly those lines in exactly these
# files. Everything else in the file is held to the vocabulary.
MARKED = {
    "scripts/init/update.py": "# retired",
    "scripts/mcp/purlin/gate.py": "# retired",
    "scripts/mcp/purlin/specs.py": "# retired",
    "references/formats/spec_format.md": "<!-- retired -->",
    "dev/test_mcp_server.py": "# retired",
    "dev/test_schema_spec_format.py": "# retired",
    "dev/test_schema_proof_format.py": "# retired",
    "dev/test_run_script.py": "# retired",
}


def _tracked():
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines()
            if p and not p.startswith(SKIP)
            and not any(d in p for d in PENDING_DELETE)]


def _allowed_spans(probe):
    """Where the phrases the review list's header may use sit in one line."""
    spans = []
    for phrase in ALLOWED_PHRASES:
        start = probe.find(phrase)
        while start >= 0:
            spans.append((start, start + len(phrase)))
            start = probe.find(phrase, start + 1)
    return spans


def _spans_of(check, probe):
    """Where one check matches in one stretch of text, as `(start, end)` pairs."""
    if not isinstance(check, str):
        return [match.span() for match in check.finditer(probe)]
    found = []
    start = probe.find(check)
    while start >= 0:
        found.append((start, start + len(check)))
        start = probe.find(check, start + 1)
    return found


def _collapsed(text):
    """The text with every run of whitespace as one space, and the original
    offset of each character of the result.

    A retired phrase a line break splits is invisible to the pass over lines,
    so the collapsed text is searched as well. The offsets carry each hit back
    to the line it starts on. The list holds one more entry than the text, the
    end of the text, so a match's end always has an offset to read.
    """
    probe = []
    offsets = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            run = index
            while run < len(text) and text[run].isspace():
                run += 1
            probe.append(" ")
            offsets.append(index)
            index = run
        else:
            probe.append(text[index])
            offsets.append(index)
            index += 1
    offsets.append(len(text))
    return "".join(probe), offsets


def _collapsed_findings(rel, text, checks):
    """The hits only the collapsed text shows, as `<path>:<line>: <term>`.

    A hit whose text the collapsing did not change sits on one line, and the
    pass over lines already holds it with its `MARKED` and `ALLOWED_PHRASES`
    logic, so it is not reported twice. The line reported is the line the
    hit's first character is on.
    """
    findings = []
    probe, offsets = _collapsed(text)
    spans = _allowed_spans(probe)
    for check in checks:
        for start, end in _spans_of(check, probe):
            if any(s <= start and end <= e for s, e in spans):
                continue
            if text[offsets[start]:offsets[end]] == probe[start:end]:
                continue
            term = check if isinstance(check, str) else check.pattern
            findings.append("%s:%d: %s" % (
                rel, text.count("\n", 0, offsets[start]) + 1, term))
            break
    return findings


def test_no_retired_terms():
    findings = []
    for rel in _tracked():
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # a binary file carries no prose
        checks = PATTERNS + list(LITERALS) + list(CASED)
        if rel.endswith(".md"):
            checks = checks + list(MD_ONLY)
        marker = MARKED.get(rel)
        for lineno, line in enumerate(text.splitlines(), 1):
            if marker and line.rstrip().endswith(marker):
                continue
            probe = line
            spans = _allowed_spans(probe)
            for check in checks:
                for start, end in _spans_of(check, probe):
                    if any(s <= start and end <= e for s, e in spans):
                        continue
                    term = check if isinstance(check, str) else check.pattern
                    findings.append("%s:%d: %s" % (rel, lineno, term))
                    break
        findings.extend(_collapsed_findings(rel, text, checks))
    assert not findings, "retired terms found:\n" + "\n".join(findings)


def test_a_retired_phrase_split_by_a_line_break_is_caught():
    """The pass over lines cannot see `needs a person` wrapped onto two lines."""
    fixture = "The board says this one needs a\nperson before it merges.\n"
    findings = _collapsed_findings("fixture.md", fixture, list(LITERALS))
    assert findings == ["fixture.md:1: needs a person"], findings


def test_the_review_list_header_may_wrap():
    """The one sentence that may say so is allowed across a line break too."""
    fixture = "The header reads `4 rules need a\nperson` and nothing else does.\n"
    assert _collapsed_findings("fixture.md", fixture, list(LITERALS)) == []


def test_one_line_hits_are_left_to_the_pass_over_lines():
    """A hit the collapsing did not change is not reported twice."""
    fixture = "This one needs a person.\n"
    assert _collapsed_findings("fixture.md", fixture, list(LITERALS)) == []
