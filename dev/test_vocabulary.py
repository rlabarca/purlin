"""Fail when a machine spelling this release removed appears in a tracked file.

The list holds the spellings of commands, flags, keys, files, tags and states
that are gone, so none of them comes back into the code, the specs or the
docs. A plain English word is never on it: prose is held to the writing
style by review, and a word like `tested` or `hold` is honest English.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LITERALS = (
    # tags, flags and commands
    "@on(", "@integration", "@e2e", "@unit", "[origin:", "[criterion:",
    "[bar:", "--platform", "--quick", "--tier", "--hold", "--resolve",
    re.compile(r"--ai\b"),
    "purlin:verify", "purlin:review", "purlin:approve", "purlin:find",
    "purlin:rename", "purlin:audit --remote", "anchor propose",
    "upstream-check", "validated/",
    # keys, fields and variables
    "needs_person", "needs-a-person", "ai_review_at", "bar_from", "sign_at",
    "review_list", "sign_list", "signable", "design_hash", "CHANGED_DESIGNS",
    "PURLIN_PROOF_TIER", "is_ancestor", "build_brief",
    "`developer`", "'developer'", '"developer"',
    "`signers`", "'signers'", '"signers"',
    # files, folders and scripts
    "verify_gate", "verify-gate:", "config.local.json", "tools/PM",
    "tools/QA", "pack_tools", "scan.py", "designs/", "test_run.json",
    "last_sweep.json", ".purlin/plugin-root", ".purlin/hooks",
    "report-stamp.js",
    # the files a run once wrote beside the evidence, and their readers
    ".purlin/records", ".purlin/briefs", ".purlin/tests/",
    "purlin-record/", "purlin-tests/", "purlin-brief/",
    "record_format", "tests_format", "test_results.md",
    "brief.json", "brief.txt",
    "purlin: record for", "purlin: tests at",
    "Record committed", "Record unchanged",
    "Test results committed", "Test results unchanged",
    "write_record", "load_records", "record_label", "latest_record",
    "results_reader", "write_brief", "find_brief", "briefs_dir",
    "scripts/run/records.py", "scripts/run/results.py",
    "purlin/records.py", "purlin/results.py",
    # the markers the proof plugins read, their folder and their format
    "pytest.mark.proof", "purlin_proof", "[proof:", "PurlinProof",
    "-- @purlin", ".purlin/plugins", "proofs_format")

# Spellings that are only machine text in capitals: the two state badges and
# the file a git host reads owners from. `hollow` in a sentence is fine.
CASED = (re.compile(r"\bHOLLOW\b"), re.compile(r"\bPROVABLE\b"),
         re.compile(r"\bCODEOWNERS\b"), re.compile(r"\bPages\b"))

EXCLUDED = (
    "design/tokens/",           # an external design system's tokens, copied in verbatim
    "dev/fixtures/upgrade-0.9.5/",  # a 0.9.5 project, kept as 0.9.5 left it
    "dev/plans/",               # the plan names what it removes
    "dev/test_vocabulary.py",   # this file lists the spellings
    "RELEASE_NOTES.md",         # the one place history is kept
    ".purlin/",                 # the evidence is machine output
)

# The upgrade from 0.9.5 has to name what it rewrites, and its tests have to
# write the spellings they feed it. Those lines end with the marker for their
# file type, and the check steps over exactly those lines in exactly these
# files. Everything else in the file is held to the list.
MARKED = {
    "scripts/init/update.py": "# retired",
    "dev/test_init_update.py": "# retired",
}


def _tracked():
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines()
            if p and not p.startswith(EXCLUDED)]


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
    pass over lines already holds it with its `MARKED` logic, so it is not
    reported twice. The line reported is the line the
    hit's first character is on.
    """
    findings = []
    probe, offsets = _collapsed(text)
    for check in checks:
        for start, end in _spans_of(check, probe):
            if text[offsets[start]:offsets[end]] == probe[start:end]:
                continue
            term = check if isinstance(check, str) else check.pattern
            findings.append("%s:%d: %s" % (
                rel, text.count("\n", 0, offsets[start]) + 1, term))
            break
    return findings


def test_no_removed_spelling_comes_back():
    findings = []
    for rel in _tracked():
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # a binary file carries no prose
        checks = list(LITERALS) + list(CASED)
        marker = MARKED.get(rel)
        for lineno, line in enumerate(text.splitlines(), 1):
            if marker and line.rstrip().endswith(marker):
                continue
            for check in checks:
                for start, end in _spans_of(check, line):
                    term = check if isinstance(check, str) else check.pattern
                    findings.append("%s:%d: %s" % (rel, lineno, term))
                    break
        findings.extend(_collapsed_findings(rel, text, checks))
    assert not findings, "removed spellings found:\n" + "\n".join(findings)


def test_a_spelling_split_by_a_line_break_is_caught():
    """The pass over lines cannot see a spelling wrapped onto two lines."""
    fixture = "Run purlin:audit\n--remote to send it away.\n"
    findings = _collapsed_findings("fixture.md", fixture, list(LITERALS))
    assert findings == ["fixture.md:1: purlin:audit --remote"], findings


def test_one_line_hits_are_left_to_the_pass_over_lines():
    """A hit the collapsing did not change is not reported twice."""
    fixture = "Run purlin:audit --remote to send it away.\n"
    assert _collapsed_findings("fixture.md", fixture, list(LITERALS)) == []
