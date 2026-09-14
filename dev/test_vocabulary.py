"""Fail when a retired term appears in a tracked file.

The retired spellings and what replaced each one are listed in
`references/glossary.md`; that table is the one place in the repository where
they may still be written.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Whole words, case-insensitive.
WORDS = ("audit", "gauge", "HOLLOW", "PROVABLE", "receipt", "platform", "mutation score",
         "caught score", "records branch", "forge", "queue", "CODEOWNERS", "approver rule")
LITERALS = ("@on(",)                    # not a word: the retired scope tag
CASED = (re.compile(r"\bPages\b"),)     # capitalised only; "pages" of a document is fine
MD_ONLY = (re.compile(r"\bmode\b", re.I),)  # "mode" is only retired in prose

PATTERNS = [re.compile(r"\b" + re.escape(w) + r"\b", re.I) for w in WORDS]

EXCLUDED = (
    "references/glossary.md",   # the retired table itself
    "design/",                  # an external design system, copied in verbatim
    "dev/fixtures/upgrade-",    # old project layouts, kept wrong on purpose
    "dev/plans/",               # the plan names what it retires
    "dev/test_vocabulary.py",   # this file lists the terms
    "specs/",                   # frozen until phase 9
    ".purlin/",                 # frozen until phase 9
)

# Paths a later phase still rewrites. Delete an entry when its phase lands.
PENDING_REWRITE = (
    # phase 9: the migration, which must name the retired `@on(` tag in order
    # to ignore it, and the tests and the format file that pin that behaviour
    "scripts/mcp/purlin/specs.py", "references/formats/spec_format.md",
    "dev/test_mcp_server.py", "dev/test_schema_spec_format.py",
    "dev/test_schema_proof_format.py",
    # phase 4: the rule-writing examples, which follow the spec guide
    "references/rule_examples.md",
    # phase 5: the interpreter resolver, which names what sys.platform reads
    "scripts/purlin_python.sh",
    # phase 8: the docs
    "docs/", "README.md", "CLAUDE.md", "RELEASE_NOTES.md", "assets/purlin-logo.svg",
)

SKIP = EXCLUDED + PENDING_REWRITE

# The update has to name what it detects. Its migration table is the one place
# those spellings are written, and every line of it ends with this comment, so
# this proof steps over exactly those lines in exactly that file.
TABLE_FILE = "scripts/init/update.py"
TABLE_LINE = "# retired"


def _tracked():
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if p and not p.startswith(SKIP)]


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
        for lineno, line in enumerate(text.splitlines(), 1):
            if rel == TABLE_FILE and line.rstrip().endswith(TABLE_LINE):
                continue
            probe = line.replace("sys.platform", "")  # the one allowed literal
            for check in checks:
                hit = check in probe if isinstance(check, str) else check.search(probe)
                if hit:
                    term = check if isinstance(check, str) else check.pattern
                    findings.append("%s:%d: %s" % (rel, lineno, term))
    assert not findings, "retired terms found:\n" + "\n".join(findings)
