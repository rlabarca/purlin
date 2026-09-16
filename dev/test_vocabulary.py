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
WORDS = ("gauge", "HOLLOW", "PROVABLE", "receipt", "platform", "mutation score",
         "caught score", "records branch", "forge", "queue", "CODEOWNERS", "approver rule",
         # the 0.10.0 three-level model
         "tested", "recorded", "approved", "approve", "approval", "approver", "approvers",
         "verified", "verdict", "reviewed", "re-verify")
LITERALS = ("@on(",                     # not a word: the retired scope tag
            "Proof ready", "lowest state", "seven states", "auto-approval", "review queue",
            "purlin:verify", "purlin:review", "purlin:approve", "verify_gate", "verify-gate:",
            "validated/")
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
PENDING_REWRITE = (
    # lane 3: init and update
    "scripts/init/update.py",
    "dev/test_init_update.py", "dev/test_init_e2e.sh",
    "dev/test_e2e_required_rules.sh", "dev/test_e2e_anchor_authority.sh",
    "dev/test_e2e_external_refs.sh", "dev/test_e2e_feature_scoped_overwrite.sh",
    "specs/init/update.md",
    # lane 6A: docs rewrites
    "docs/dashboard.md", "docs/regulated-workflow.md", "docs/review-and-approval.md",
    "docs/review-and-signing.md", "docs/running-and-records.md", "docs/team-workflow.md",
    "docs/getting-started.md", "docs/raising-the-gate-and-upgrading.md",
    "docs/working-together.md",
)

# Phase 7 deletes every signature directory of the old layout; until then the
# files inside carry the old words.
PENDING_DELETE = (".approvals/",)

SKIP = EXCLUDED + PENDING_REWRITE

# A migration or a parser has to name what it detects, and a test has to write
# the spelling it feeds the parser. Those lines end with the marker for their
# file type, and this proof steps over exactly those lines in exactly these
# files. Everything else in the file is held to the vocabulary.
MARKED = {
    "scripts/init/scaffold.py": "# retired",
    "scripts/init/update.py": "# retired",
    "scripts/mcp/purlin/gate.py": "# retired",
    "scripts/mcp/purlin/specs.py": "# retired",
    "references/formats/spec_format.md": "<!-- retired -->",
    "dev/test_mcp_server.py": "# retired",
    "dev/test_schema_spec_format.py": "# retired",
    "dev/test_schema_proof_format.py": "# retired",
}


def _tracked():
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines()
            if p and not p.startswith(SKIP)
            and not any(d in p for d in PENDING_DELETE)]


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
            probe = line.replace("sys.platform", "")  # the one allowed literal
            for check in checks:
                hit = check in probe if isinstance(check, str) else check.search(probe)
                if hit:
                    term = check if isinstance(check, str) else check.pattern
                    findings.append("%s:%d: %s" % (rel, lineno, term))
    assert not findings, "retired terms found:\n" + "\n".join(findings)
