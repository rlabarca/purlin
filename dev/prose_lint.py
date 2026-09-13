#!/usr/bin/env python3
"""The prose lints over the repository's committed text.

`python3 dev/prose_lint.py` prints one line per offender,

    <path>:<line>: <lint>: <message>

and exits 1 when there is at least one. `--json` prints the same offenders as
a JSON array. `specs/instructions/purlin_prose.md` RULE-12 through RULE-15 own
the first four lints and name the file set each one covers today; widening a
set is an edit to the row in this module and to the rule that states it, never
a new rule and never a new module. The fifth, `banned_paths`, is owned from
outside: `specs/instructions/purlin_skills.md` RULE-19 states it over the
skills and the agents and `specs/instructions/purlin_references.md` RULE-35
over the references, because the claim it makes is about those surfaces and
not about this module.

The five helpers below (`_tracked`, `_read`, `_prose_files`,
`_sectioned_paragraphs`, `_yaml_blocks`, `_dash_hits`) were lifted from
`dev/test_purlin_docs.py`, which proved the hand-listed rules these lints
replace. `dev/test_purlin_prose.py` imports them from here so the proofs and
the lint read the tree exactly the same way.
"""

import argparse
import json
import os
import re
import subprocess
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


# ---------------------------------------------------------------------------
# Helpers lifted from dev/test_purlin_docs.py
# ---------------------------------------------------------------------------

PROSE_TREES = ('docs', 'references', 'skills', 'tools', 'agents')


def _tracked(*paths):
    out = subprocess.run(['git', 'ls-files', '--'] + list(paths),
                         cwd=PROJECT_ROOT, capture_output=True, text=True,
                         check=True).stdout
    return [p for p in out.splitlines() if p.strip()]


def _read(rel, root=PROJECT_ROOT):
    with open(os.path.join(root, rel), encoding='utf-8') as f:
        return f.read()


def _prose_files():
    files = _tracked(*PROSE_TREES) + ['README.md']
    return [f for f in files if not f.endswith('.skill')]


def _norm_heading(text):
    text = text.replace('\u2014', '-').replace('\u2013', '-')
    return re.sub(r'\s+', ' ', text).strip()


def _sectioned_paragraphs(text):
    """Yield (paragraph, nearest preceding heading) for one markdown file.

    Paragraphs are blank-line delimited. Lines inside a fenced block are never
    read as headings, so a `# comment` in a shell example cannot be mistaken
    for a section.
    """
    section = None
    fenced = False
    para = []
    para_section = None
    for line in text.splitlines():
        if re.match(r'^\s{0,3}(```|~~~)', line):
            fenced = not fenced
        elif not fenced:
            heading = re.match(r'^\s{0,3}#{1,6}\s+(.*\S)\s*$', line)
            if heading:
                section = _norm_heading(heading.group(1))
        if line.strip():
            if not para:
                para_section = section
            para.append(line)
        elif para:
            yield '\n'.join(para), para_section
            para = []
            para_section = None
    if para:
        yield '\n'.join(para), para_section


def _located_paragraphs(text):
    """(lineno, paragraph, section) for one markdown file.

    `_sectioned_paragraphs` yields paragraphs in document order and drops the
    line number; this walks the same lines alongside it so an offender can be
    reported at the line its paragraph starts on.
    """
    lines = text.splitlines()
    pos = 0
    for para, section in _sectioned_paragraphs(text):
        first = para.splitlines()[0]
        while pos < len(lines) and lines[pos] != first:
            pos += 1
        yield pos + 1, para, section
        pos += len(para.splitlines())


def _yaml_blocks(text):
    return re.findall(r'^```ya?ml\n(.*?)^```', text, re.MULTILINE | re.DOTALL)


DASHES = ('\u2014', '\u2013')
DASH_RE = re.compile('[' + ''.join(DASHES) + ']')


def _hits(text, pattern):
    """(lineno, line) per line matching `pattern` outside a fenced block."""
    out = []
    fenced = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if re.match(r'^\s{0,3}(```|~~~)', line):
            fenced = not fenced
            continue
        if fenced:
            continue
        if pattern.search(line):
            out.append((lineno, line))
    return out


def _dash_hits(text, rel):
    """`<rel>:<lineno>: <line>` per dash outside a fenced block.

    Lifted from the RULE-11 sweep this module replaced. The line walk it did
    inline is now `_hits`, so every banned row shares one fence tracker.
    """
    return [f"{rel}:{lineno}: {line.strip()}"
            for lineno, line in _hits(text, DASH_RE)]


# ---------------------------------------------------------------------------
# Scope resolution
# ---------------------------------------------------------------------------

def _glob_re(glob):
    """A glob where `**` crosses directories and `*` does not."""
    out = []
    i = 0
    while i < len(glob):
        if glob.startswith('**', i):
            out.append('.*')
            i += 2
        elif glob[i] == '*':
            out.append('[^/]*')
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile('^' + ''.join(out) + '$')


_GLOB_CACHE = {}


def _in_scope(rel, scope):
    for glob in scope:
        if glob not in _GLOB_CACHE:
            _GLOB_CACHE[glob] = _glob_re(glob)
        if _GLOB_CACHE[glob].match(rel):
            return True
    return False


def _scope_files(scope, files):
    return [rel for rel in files if _in_scope(rel, scope)]


def repo_files():
    """Every git-tracked file the lints may be pointed at."""
    specs = [rel for rel in _tracked('specs') if rel.endswith('.md')]
    return (_prose_files() + _tracked('.claude-plugin') + ['CLAUDE.md']
            + specs + list(SCRIPT_STRING_FILES))


class Offender:
    """One reported defect, printed as `<path>:<line>: <lint>: <message>`."""

    def __init__(self, path, line, lint, message):
        self.path = path
        self.line = line
        self.lint = lint
        self.message = message

    def __str__(self):
        return f"{self.path}:{self.line}: {self.lint}: {self.message}"

    __repr__ = __str__

    def as_dict(self):
        return {'path': self.path, 'line': self.line, 'lint': self.lint,
                'message': self.message}


# ---------------------------------------------------------------------------
# Lint 1: banned_strings (RULE-12)
# ---------------------------------------------------------------------------

#: The dash-free set as `purlin_docs` RULE-11 enforced it, plus the two plugin
#: manifests whose `description` values carried U+2014 as a JSON escape, plus
#: every skill and agent definition. Widening this to the rest of
#: `references/` and to `specs/` is an edit to this tuple. `RELEASE_NOTES.md` and `dev/` (including `dev/plans/`) are exempt by
#: name: the notes are a historical record of what was once true, and this
#: module and its proofs carry the banned literals themselves.
DASH_SCOPE = ('docs/**.md', 'README.md',
              'references/remote_verification.md',
              'references/spec_quality_guide.md',
              'references/hard_gates.md',
              'references/audit_criteria.md',
              '.claude-plugin/plugin.json',
              '.claude-plugin/marketplace.json',
              'skills/**.md', 'agents/**.md',
              'references/**.md', 'tools/**.md', 'CLAUDE.md')

#: `purlin_docs` RULE-1's closed list: the only (file, section) pairs where the
#: bare `@windows` token may appear. A section is the nearest preceding
#: markdown heading, normalised by `_norm_heading`.
WINDOWS_TOKEN_SECTIONS = (
    ('docs/installation-guide.md', 'Upgrading the plugin'),
    ('docs/testing-workflow-guide.md', 'What `purlin:test` does per platform'),
    ('references/audit_criteria.md', 'LOOSE'),
    ('references/formats/proofs_format.md', 'File Naming'),
    ('references/formats/spec_format.md', 'Platform tags'),
    ('references/spec_quality_guide.md', 'Tier Assignment'),
    ('skills/init/SKILL.md', 'Usage'),
    ('skills/init/SKILL.md', 'Step 5d: Update'),
    ('skills/verify/SKILL.md', 'Pre-check: pending migrations'),
)

#: The two trees the `em-dash`, `retired-format` and `anchor-home` rows
#: reached in the commit that removed their 391 dashes and their last
#: `3-section` and `## What it does` mentions.
SKILL_AND_AGENT = ('skills/**.md', 'agents/**.md')

PROSE_SCOPE = ('docs/**', 'references/**', 'skills/**', 'tools/**',
               'agents/**', 'README.md')

#: The `anchor-home` row's file set. `skills/` and `agents/` are named here
#: because the two skills that route a new spec to a category are where a wrong
#: anchor home is written into a project, and the agent definition is what
#: routes a request to those skills.
ANCHOR_HOME_SCOPE = ('docs/**', 'references/**', 'skills/**', 'agents/**')

#: `specs/schema/` in any form, and the bare category token the routing lists
#: used. `sync_status` reads anchors from `specs/_anchors/` only.
ANCHOR_HOME_RE = re.compile(r'specs/schema/|`schema/`')

#: The `slash-prefix` row's file set. `specs/**.md` is here because a spec
#: asserts the literal a hook prints, and the two scripts are named one by one
#: because the lints read markdown prose and have no scanner for the strings a
#: program prints; naming the two files that print skill names is narrower and
#: more honest than pretending `scripts/**` is prose.
SLASH_PREFIX_SCOPE = ('docs/**', 'references/**', 'skills/**', 'agents/**',
                      'specs/**.md',
                      'scripts/hooks/pre_push_gate.py',
                      'scripts/hooks/pre-push.sh')

#: The skill invocation as Claude Code prints it and as every other surface
#: writes it: `purlin:<skill>`, with no leading slash.
SLASH_PREFIX_RE = re.compile(r'/purlin:')

#: The one section that must still carry the banned spelling: the rule that
#: states it. Written as an allowlist pair rather than a scope exclusion so
#: the lint reports it the day the rule stops quoting the literal.
SLASH_PREFIX_ALLOWLIST = (('specs/instructions/purlin_prose.md', 'Rules'),)

#: Files outside the prose trees that the tables above point a row at.
SCRIPT_STRING_FILES = ('scripts/hooks/pre_push_gate.py',
                       'scripts/hooks/pre-push.sh')

#: The `last-gate` row's file set and its three phrasings. `purlin:verify` is
#: Layer 0 of the four in `references/hard_gates.md`, and the CI gate job is
#: Layer 3, so any of these words in a guide tells a reader the opposite of
#: what the reference says.
LAST_GATE_SCOPE = ('docs/**',)
LAST_GATE_RE = re.compile(r'last gate|final gate|the last check')

REGULATED = 'docs/regulated-environments.md'

#: The `retired-format` row's file set, now every prose tree.
RETIRED_FORMAT_SCOPE = PROSE_SCOPE

#: The retired phrases, as one alternation. The heading arm is anchored at both
#: ends so `#### What it does not bind`, a real heading of
#: `docs/regulated-environments.md`, is not read as the retired section.
RETIRED_FORMAT_RE = re.compile(
    r'^\s{0,3}#{1,6}\s+What it does\s*$|3-section format', re.MULTILINE)

#: Every row: (name, unit, pattern, scope, min_files, allowlist, note).
#: `unit` is `line` or `paragraph`. `min_files` is the least number of files
#: the scope must resolve to, so a row cannot pass by scanning nothing. Each
#: `(path, section)` in `allowlist` exempts a hit there AND must still be hit,
#: so an exemption that outlives the text it covers is reported as stale.
#: The one section that may still carry an em dash: the `(assumed - <context>)`
#: rule tag is a literal `scripts/mcp/purlin_server.py` matches with
#: `\\(assumed\\s*\u2014\\s*.+?\\)`, so the worked examples of the tag in the skill
#: and the row that documents it in the format contract are parser input
#: rather than prose. Retiring the separator is one edit to that
#: expression, to `references/formats/spec_format.md`, to `skill_spec` RULE-11
#: and to the two end-to-end fixtures, and it belongs in the commit that owns
#: `scripts/`; the exemption is written as an allowlist pair so it fails the
#: day that lands.
DASH_ALLOWLIST = (
    ('skills/spec/SKILL.md', 'Step 5: Rule Extraction Heuristics'),
    ('references/formats/spec_format.md', 'Rule Tags'),
)

BANNED = (
    ('em-dash', 'line', DASH_RE, DASH_SCOPE, 12, DASH_ALLOWLIST,
     'an em dash or en dash joins two ideas without stating the relation; '
     'use a colon, a comma or a full stop'),
    ('promise', 'line',
     re.compile('|'.join(re.escape(s) for s in (
         'signed verification', 'tamper-evident', 'The vhash proves',
         '(signed off)', 'signed off'))),
     PROSE_SCOPE, 40, ((REGULATED, 'What Purlin Is NOT'),),
     'nothing Purlin writes is signed and nothing it writes is '
     'tamper-evident; the only permitted occurrence is a negation in the '
     '"What Purlin Is NOT" list'),
    ('windows-tier', 'paragraph', re.compile(r'@windows(?![-\w.])'),
     PROSE_SCOPE, 40, WINDOWS_TOKEN_SECTIONS,
     '`windows` is a platform, never a tier; the bare token belongs only in '
     'the sections that state the one-release legacy alias and its '
     '`@unit @on(windows)` rewrite, and the word `legacy` nearby exempts '
     'nothing'),
    ('approval', 'line',
     re.compile('|'.join(re.escape(s) for s in (
         'compliance status', 'sign-off', 'signs off', 'certified'))),
     (REGULATED,), 1, (),
     'approval vocabulary for something Purlin never does; the page is cited '
     'in a validation record, so it names mechanisms rather than approvals'),
    ('retired-format', 'line', RETIRED_FORMAT_RE, RETIRED_FORMAT_SCOPE, 25, (),
     'a spec and an anchor carry two sections, `## Rules` and `## Proof`, so '
     'the name is the 2-section format; `## What it does` is retired and what '
     'a feature does belongs on the `> Description:` continuation lines'),
    ('last-gate', 'line', LAST_GATE_RE, LAST_GATE_SCOPE, 10, (),
     '`purlin:verify` is Layer 0, the first of the four enforcement layers '
     'of `references/hard_gates.md`, and the CI gate job is Layer 3; a guide '
     'that calls any of them the last gate tells the reader the opposite of '
     'what the reference says'),
    ('slash-prefix', 'line', SLASH_PREFIX_RE, SLASH_PREFIX_SCOPE, 80,
     SLASH_PREFIX_ALLOWLIST,
     'a skill is invoked as `purlin:<name>`; the leading slash is a Claude '
     'Code slash-command spelling that nothing else in this repository uses, '
     'and a reader who copies it from one page and not another cannot tell '
     'which one is right'),
    ('anchor-home', 'line', ANCHOR_HOME_RE, ANCHOR_HOME_SCOPE, 35, (),
     'an anchor spec lives at `specs/_anchors/<name>.md`; `sync_status` reads '
     'that directory and no other, so a `schema/` category routes an anchor '
     'to a file nothing loads'),
)


def _json_descriptions(text):
    """(lineno, value) per `description` string in a decoded JSON document.

    The manifests carry their dashes as `\\u2014` escapes, so the raw bytes
    hold no dash at all: only the decoded value does.
    """
    out = []
    lines = text.splitlines()
    pos = 0

    def walk(node):
        nonlocal pos
        if isinstance(node, dict):
            for key, value in node.items():
                if key == 'description' and isinstance(value, str):
                    while pos < len(lines) and '"description"' not in \
                            lines[pos]:
                        pos += 1
                    out.append((pos + 1, value))
                    pos += 1
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(json.loads(text))
    return out


def _sections_by_line(text):
    """{lineno: nearest preceding heading} for a markdown file."""
    out = {}
    section = None
    fenced = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if re.match(r'^\s{0,3}(```|~~~)', line):
            fenced = not fenced
        elif not fenced:
            heading = re.match(r'^\s{0,3}#{1,6}\s+(.*\S)\s*$', line)
            if heading:
                section = _norm_heading(heading.group(1))
        out[lineno] = section
    return out


def banned_strings(root=PROJECT_ROOT, files=None, rows=BANNED, strict=True):
    """RULE-12: no row's pattern appears outside the sections it is allowed.

    `strict` carries the vacuity guards (`min_files` and the stale-exemption
    check). A proof running the row against a temp root passes strict=False.
    """
    files = repo_files() if files is None else files
    offenders = []
    for name, unit, pattern, scope, min_files, allowlist, note in rows:
        scanned = _scope_files(scope, files)
        if strict and len(scanned) < min_files:
            offenders.append(Offender(
                'dev/prose_lint.py', 0, 'banned_strings',
                f"row {name!r} resolved to {len(scanned)} files, fewer than "
                f"the {min_files} it must read; the sweep would pass by "
                f"scanning nothing"))
            continue
        allowed = set(allowlist)
        covered = set()
        for rel in scanned:
            try:
                text = _read(rel, root)
            except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
                continue
            if rel.endswith('.json'):
                units = [(lineno, value, None)
                         for lineno, value in _json_descriptions(text)]
            elif unit == 'paragraph':
                units = list(_located_paragraphs(text))
            else:
                sections = _sections_by_line(text)
                units = [(lineno, line, sections.get(lineno))
                         for lineno, line in _hits(text, pattern)]
            for lineno, haystack, section in units:
                if not pattern.search(haystack):
                    continue
                if (rel, section) in allowed:
                    covered.add((rel, section))
                    continue
                offenders.append(Offender(
                    rel, lineno, 'banned_strings',
                    f"{name}: {note}: {haystack.strip()[:160]}"))
        if strict:
            for rel, section in allowlist:
                if (rel, section) not in covered:
                    offenders.append(Offender(
                        rel, 0, 'banned_strings',
                        f"{name}: this section is exempt but no longer "
                        f"carries an occurrence, so the exemption is stale: "
                        f"{section!r}"))
    return offenders


# ---------------------------------------------------------------------------
# Lint 2: paths_exist (RULE-13)
# ---------------------------------------------------------------------------

#: The four references `purlin_docs` RULE-11 named plus the guides, the README,
#: and every skill and agent definition: the set held to resolving paths. The
#: skills are here because they are where the 115 bare plugin-relative paths
#: live, and a bare path is only safe while something checks that it resolves
#: under the plugin root.
PATH_SCOPE = DASH_SCOPE[:6] + SKILL_AND_AGENT

#: A backticked token carrying any of these is not a repository path: an
#: angle bracket or a `$` marks a placeholder, a `*` a glob, a space a command
#: line, a pipe a table cell boundary, `::` a language-scoped name, a leading
#: `/` an absolute path, and a brace an attribute or a template.
PATH_SKIP_CHARS = ('<', '>', '*', '$', ' ', '|', '{', '}')

#: Generated at run time, gitignored, and named by the documentation on
#: purpose: `.purlin/report-stamp.js` is written beside the digest on every
#: build, the two `.purlin/` directories hold the caches and the run marker,
#: and `.claude/` is the host's own state. A fresh clone and a fresh worktree
#: carry none of it, so a token naming one is a live link for a reader with an
#: initialized project and a dangling one only for a lint that mistakes a
#: checkout for a running project. An entry ending in `/` covers everything
#: beneath it. Each entry must still be named somewhere in the scanned set,
#: the staleness bar `PATH_ALLOWLIST` carries, so a skip that outlives the
#: documentation naming it is reported rather than kept.
RUNTIME_PATHS = ('.purlin/report-stamp.js',
                 '.purlin/cache/',
                 '.purlin/runtime/',
                 '.claude/')


def _runtime_skip(token):
    """The `RUNTIME_PATHS` entry covering `token`, or None."""
    for entry in RUNTIME_PATHS:
        if token == entry or (entry.endswith('/')
                              and token.startswith(entry)):
            return entry
    return None

#: Illustrative paths the guides use to show a shape rather than to point at a
#: file. Each must still appear in the scanned set or the lint reports it as a
#: stale exemption.
PATH_ALLOWLIST = (
    'specs/hooks/gate-hook.md',
    'specs/integration/',
    '.purlin/config.local.json',
    # The workflow purlin:init --ci writes into a consumer project; this
    # repository carries its own verify-gate.yml under a different name.
    '.github/workflows/purlin-verify-gate.yml',
    # Two paths in the project a skill is run against, not in this one: the
    # directory purlin:anchor writes design screenshots to, and an anchor
    # purlin:spec-from-code offers to create. This repository has neither.
    'specs/_anchors/screenshots/',
    'specs/_anchors/project_environment.md',
    # The Example column of spec_quality_guide.md's Spec Categories table and
    # the e2e example under it. They show where a spec of that kind goes in
    # the reader's project; naming one of this repository's own specs there
    # sends a consumer looking for a file that did not ship.
    'specs/_anchors/design_tokens.md',
    'specs/instructions/agent_guides.md',
    'specs/checkout/checkout_flow.md',
)

_BACKTICK = re.compile(r'`([^`\n]+)`')

#: `purlin:<skill> --<flag>`; `--flag` and `--option` are placeholders and a
#: run of three or more dashes is a table rule, not a flag.
_SKILL_CALL = re.compile(r'`purlin:([a-z][a-z-]*)((?:\s+--[a-z][a-z0-9-]*)+)')
_FLAG = re.compile(r'--[a-z][a-z0-9-]*')
FLAG_PLACEHOLDERS = ('--flag', '--option')


def _heading_slugs(text):
    """GitHub-style slugs for every heading outside a fenced block."""
    slugs = set()
    fenced = False
    for line in text.splitlines():
        if re.match(r'^\s{0,3}(```|~~~)', line):
            fenced = not fenced
            continue
        if fenced:
            continue
        heading = re.match(r'^\s{0,3}#{1,6}\s+(.*\S)\s*$', line)
        if not heading:
            continue
        slug = heading.group(1).lower()
        slug = re.sub(r'[^\w\s-]', '', slug.replace('\u2014', ' ')
                      .replace('\u2013', ' '))
        slugs.add(re.sub(r'[\s]+', '-', slug.strip()))
    return slugs


def _root_names(root):
    try:
        return set(os.listdir(root))
    except OSError:
        return set()


def _usage_flags(skill, root=PROJECT_ROOT):
    """The `--flag` tokens in `skills/<skill>/SKILL.md`'s `## Usage` block."""
    path = os.path.join(root, 'skills', skill, 'SKILL.md')
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as f:
        text = f.read()
    block = re.search(r'^##\s+Usage\s*$(.*?)(?=^##\s|\Z)', text,
                      re.MULTILINE | re.DOTALL)
    if not block:
        return set()
    return set(_FLAG.findall(block.group(1)))


def paths_exist(root=PROJECT_ROOT, files=None, scope=PATH_SCOPE,
                allowlist=PATH_ALLOWLIST, strict=True):
    """RULE-13: every backticked path in the scanned set resolves on disk."""
    files = repo_files() if files is None else files
    scanned = _scope_files(scope, files)
    names = _root_names(root)
    offenders = []
    seen_allowed = set()
    seen_runtime = set()
    for rel in scanned:
        try:
            text = _read(rel, root)
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        for lineno, line in _hits(text, _BACKTICK):
            for token in _BACKTICK.findall(line):
                if '/' not in token or '::' in token or token.startswith('/'):
                    continue
                if any(c in token for c in PATH_SKIP_CHARS):
                    continue
                # A first segment that names nothing at the repository root is
                # a path in someone else's project, which these guides use as
                # an example.
                if token.split('/', 1)[0] not in names:
                    continue
                runtime = _runtime_skip(token)
                if runtime is not None:
                    seen_runtime.add(runtime)
                    continue
                if token in allowlist:
                    seen_allowed.add(token)
                    continue
                target, _, fragment = token.partition('#')
                if not os.path.exists(os.path.join(root, target)):
                    offenders.append(Offender(
                        rel, lineno, 'paths_exist',
                        f"`{token}` does not resolve; no {target} under the "
                        f"repository root"))
                    continue
                if fragment:
                    try:
                        body = _read(target, root)
                    except (UnicodeDecodeError, IsADirectoryError,
                            FileNotFoundError):
                        continue
                    if fragment not in _heading_slugs(body):
                        offenders.append(Offender(
                            rel, lineno, 'paths_exist',
                            f"`{token}`: {target} has no heading whose slug "
                            f"is {fragment!r}"))
        for lineno, line in _hits(text, _SKILL_CALL):
            for match in _SKILL_CALL.finditer(line):
                skill = match.group(1)
                declared = _usage_flags(skill, root)
                for flag in _FLAG.findall(match.group(2)):
                    if flag in FLAG_PLACEHOLDERS:
                        continue
                    if declared is None:
                        offenders.append(Offender(
                            rel, lineno, 'paths_exist',
                            f"`purlin:{skill}` names no skill; there is no "
                            f"skills/{skill}/SKILL.md"))
                        break
                    if flag not in declared:
                        offenders.append(Offender(
                            rel, lineno, 'paths_exist',
                            f"`purlin:{skill} {flag}`: the `## Usage` block "
                            f"of skills/{skill}/SKILL.md declares no {flag}"))
    if strict:
        for token in allowlist:
            if token not in seen_allowed:
                offenders.append(Offender(
                    'dev/prose_lint.py', 0, 'paths_exist',
                    f"`{token}` is allowlisted as an illustrative path but "
                    f"appears nowhere in the scanned set, so the exemption "
                    f"is stale"))
        for entry in RUNTIME_PATHS:
            if entry not in seen_runtime:
                offenders.append(Offender(
                    'dev/prose_lint.py', 0, 'paths_exist',
                    f"`{entry}` is skipped as generated runtime state but "
                    f"appears nowhere in the scanned set, so the skip is "
                    f"stale"))
    return offenders


def usage_flags_missing_from_commands(root=PROJECT_ROOT):
    """Usage flags `references/purlin_commands.md` does not mention.

    The reverse direction of the flag check. It is reported by `main()` and
    asserted by no proof yet: the count is over the threshold at which fixing
    it belongs in this commit, so it is a count to drive down rather than a
    gate. See `specs/instructions/purlin_prose.md` RULE-13.
    """
    try:
        commands = _read('references/purlin_commands.md', root)
    except OSError:
        return []
    missing = []
    skills_dir = os.path.join(root, 'skills')
    for skill in sorted(os.listdir(skills_dir)):
        declared = _usage_flags(skill, root) or set()
        for flag in sorted(declared):
            if flag in FLAG_PLACEHOLDERS:
                continue
            if flag not in commands:
                missing.append(f"purlin:{skill} {flag}")
    return missing


# ---------------------------------------------------------------------------
# Lint 3: structure (RULE-14)
# ---------------------------------------------------------------------------

SKILL_GLOB = 'skills/*/SKILL.md'
AGENT_GLOB = 'agents/*.md'


def _frontmatter(text):
    """The YAML frontmatter block of a markdown file, or None."""
    match = re.match(r'\A---\n(.*?)\n---\s*\n', text, re.DOTALL)
    return match.group(1) if match else None


def _frontmatter_field(block, field):
    match = re.search(rf'^{field}:\s*(.+?)\s*$', block, re.MULTILINE)
    return match.group(1) if match else None


def structure(root=PROJECT_ROOT, files=None, strict=True):
    """RULE-14: every skill and agent definition carries its required shape."""
    files = repo_files() if files is None else files
    offenders = []
    skills = _scope_files((SKILL_GLOB,), files)
    agents = _scope_files((AGENT_GLOB,), files)
    if strict and (len(skills) < 10 or len(agents) < 1):
        offenders.append(Offender(
            'dev/prose_lint.py', 0, 'structure',
            f"resolved {len(skills)} skills and {len(agents)} agents; the "
            f"lint would pass by reading nothing"))
        return offenders
    for rel in skills:
        try:
            text = _read(rel, root)
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        block = _frontmatter(text)
        if block is None:
            offenders.append(Offender(rel, 1, 'structure',
                                      'no YAML frontmatter block'))
            continue
        directory = rel.split('/')[1]
        name = _frontmatter_field(block, 'name')
        if name != directory:
            offenders.append(Offender(
                rel, 1, 'structure',
                f"frontmatter `name` is {name!r}; the loader resolves a skill "
                f"by its directory, so it must be {directory!r}"))
        if not _frontmatter_field(block, 'description'):
            offenders.append(Offender(
                rel, 1, 'structure',
                'frontmatter carries no `description`; the loader shows it '
                'wherever the skill is offered'))
        if not re.search(r'^##\s+Usage\s*$', text, re.MULTILINE):
            offenders.append(Offender(
                rel, 1, 'structure',
                'no `## Usage` section; it is where the skill declares the '
                'flags references/purlin_commands.md and the guides cite'))
    for rel in agents:
        try:
            text = _read(rel, root)
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        block = _frontmatter(text)
        if block is None:
            offenders.append(Offender(rel, 1, 'structure',
                                      'no YAML frontmatter block'))
            continue
        for field in ('name', 'description'):
            if not _frontmatter_field(block, field):
                offenders.append(Offender(
                    rel, 1, 'structure',
                    f"frontmatter carries no `{field}`; an agent the loader "
                    f"cannot name cannot be dispatched to"))
        if _frontmatter_field(block, 'model'):
            offenders.append(Offender(
                rel, 1, 'structure',
                'frontmatter pins a `model`; a shipped agent overrides the '
                'choice of every host that installs the plugin, and the pin '
                'goes stale the moment that model is superseded'))
    return offenders


# ---------------------------------------------------------------------------
# Lint 4: single_home (RULE-15)
# ---------------------------------------------------------------------------

def _flow(sentence):
    """A pattern matching `sentence` across any line wrapping."""
    return re.compile(r'\s+'.join(re.escape(w) for w in sentence.split()))


HOME_SCOPE = ('docs/**.md', 'references/**.md', 'skills/**.md',
              'agents/**.md', 'README.md')

TAXONOMY_HOME = 'references/remote_verification.md'
VHASH_HOME = 'references/formats/receipt_format.md'
SCORING_HOME = 'references/audit_criteria.md'

PROOF_COMMON_HOME = 'specs/_anchors/proof_common.md'


def _anchor_rule_lines(rel):
    """A pattern matching any full `- RULE-N:` line of an anchor spec.

    The alternation is built from the anchor's own rule bodies, so the row
    catches a verbatim copy of a rule and nothing that merely talks about one.
    A home outside the scanned trees is still read for its own count, which is
    what `single_home` does when the home is not in the file list.
    """
    bodies = re.findall(r'^- RULE-\d+: (.+)$', _read(rel), re.M)
    return re.compile('|'.join(re.escape(b.rstrip()) for b in bodies))

#: Every row: (name, unit, pattern, home, scope, min_hits, pointer, note).
#: `unit` is `line` (one line at a time, fenced blocks skipped), `text` (the
#: whole file, so a sentence wrapped across lines still matches) or
#: `paragraph` (one blank-line-delimited paragraph with its whitespace
#: collapsed). The pattern must occur in `home` at least `min_hits` times and
#: in no other scanned file. A hit elsewhere carrying `pointer` is a link back to the home
#: rather than a second copy, which is how a doc names a subject the home owns.
HOMES = (
    ('enforcement-layer table', 'line',
     re.compile(r'^\|\s*\*\*(Layer \d|Not a layer)'),
     'references/hard_gates.md', HOME_SCOPE, 5, None,
     'the enforcement model has one home; three copies is how the repository '
     'came to say the hook has two modes in one file and three in another'),
    ('platform membership question', 'text',
     _flow('Would the same test passing on a different OS be evidence for '
           'this claim?'),
     TAXONOMY_HOME, HOME_SCOPE, 1, None,
     'a second copy of a membership question is a second answer the day one '
     'of the two is edited'),
    ('environment membership question', 'text',
     _flow("Does the outcome depend on an external system's real answers, an "
           "account, a model, or money, so that installing a package cannot "
           "reproduce it?"),
     TAXONOMY_HOME, HOME_SCOPE, 1, None,
     'a second copy of a membership question is a second answer the day one '
     'of the two is edited'),
    ('prerequisite membership question', 'text',
     _flow('Would any host with the tool installed produce the same '
           'evidence?'),
     TAXONOMY_HOME, HOME_SCOPE, 1, None,
     'a second copy of a membership question is a second answer the day one '
     'of the two is edited'),
    ('proof_common rule text', 'line',
     _anchor_rule_lines(PROOF_COMMON_HOME),
     PROOF_COMMON_HOME, HOME_SCOPE, 25, None,
     'the proof-plugin contract cites the anchor and never restates it, so a '
     'verbatim rule line in a reference is a second source of truth that goes '
     'stale the first time the anchor is edited'),
    ('platform, environment and prerequisite paragraph', 'paragraph',
     re.compile(r'(?=.*\bplatforms?\b)(?=.*\benvironments?\b)'
                r'(?=.*\bprerequisites?\b)', re.IGNORECASE),
     TAXONOMY_HOME, HOME_SCOPE, 1, TAXONOMY_HOME,
     'a paragraph naming all three categories either is the definition or '
     'points at it; a doc that names the three words without the link leaves '
     'a reader with three words and nowhere to resolve them'),
    ('vhash segment list', 'text',
     re.compile(r'\["(?:R|P|M)",'),
     VHASH_HOME, HOME_SCOPE, 3, None,
     'the receipt format owns the hash recipe; a second copy of it is a '
     'second recipe from the day one of the two is edited, and a receipt '
     'issued under either one cannot be checked against the other'),
    ('design formula', 'line',
     re.compile(r'PROVABLE / \(PROVABLE \+ LOOSE \+ UNPROVABLE\)'),
     SCORING_HOME, HOME_SCOPE, 1, None,
     'the scoring reference owns both gauge formulas; a formula restated '
     'beside the text that uses it is what lets a denominator gain a grade '
     'in one file and not in the other'),
)


def single_home(root=PROJECT_ROOT, files=None, rows=HOMES, strict=True):
    """RULE-15: each row's pattern lives in its home file and nowhere else."""
    files = repo_files() if files is None else files
    offenders = []
    for (name, unit, pattern, home, scope, min_hits, pointer,
         note) in rows:
        scanned = _scope_files(scope, files)
        if home not in scanned:
            # A home may live outside the scanned trees; it is still read for
            # its own count, or `min_hits` would fail on the home's absence.
            scanned = scanned + [home]
        at_home = 0
        for rel in scanned:
            try:
                text = _read(rel, root)
            except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
                continue
            if unit == 'paragraph':
                units = [(lineno, ' '.join(para.split()))
                         for lineno, para, _section in
                         _located_paragraphs(text)]
                units = [(lineno, body) for lineno, body in units
                         if pattern.search(body)]
            elif unit == 'text':
                units = [(text.count('\n', 0, m.start()) + 1, m.group(0))
                         for m in pattern.finditer(text)]
            else:
                units = _hits(text, pattern)
            if rel == home:
                at_home += len(units)
                continue
            for lineno, body in units:
                if pointer and pointer in body:
                    continue
                offenders.append(Offender(
                    rel, lineno, 'single_home',
                    f"{name}: this belongs in {home} and nowhere else: "
                    f"{note}: {body.strip()[:160]}"))
        if strict and at_home < min_hits:
            offenders.append(Offender(
                home, 0, 'single_home',
                f"{name}: the home carries {at_home} occurrences, fewer than "
                f"the {min_hits} it must; the sweep would pass on a tree "
                f"where the subject is documented nowhere"))
    return offenders


# ---------------------------------------------------------------------------
# Lint 5: banned_paths (purlin_skills RULE-19, purlin_references RULE-35)
# ---------------------------------------------------------------------------

#: The two trees that ship with the plugin and mean nothing in a consumer
#: checkout: this repository develops itself with itself, so its own specs and
#: its own development scripts sit beside the shipped prose and are the
#: easiest thing in the tree to cite by accident.
OWN_TREES = ('specs/', 'dev/')

#: Every row: (name, scope, exempt, min_files, note). A backticked token in a
#: scanned file that resolves to a regular file under one of `OWN_TREES` is a
#: citation the reader it is written for cannot follow. A token naming a
#: directory is left alone: `specs/` and `specs/_anchors/` name the shape of
#: any project's tree, which is what a skill is teaching. So is a token that
#: resolves to nothing here, such as `specs/auth/login.md`: it is an example
#: of a path in the reader's own project.
BANNED_PATH_ROWS = (
    ('own-spec-in-skill', ('skills/**.md', 'agents/**.md'), (), 12,
     'a skill and an agent definition are read inside a consumer project, '
     'which carries neither this repository\'s specs nor its dev tree, so a '
     'citation of either is an instruction to open a file that is not there; '
     'cite the shipped reference that carries the content, or drop the '
     'citation'),
    ('own-spec-in-reference',
     ('references/**.md',), ('references/proof_plugin_contract.md',), 12,
     'a reference under references/ ships to the consumer for the same '
     'reason and cannot cite what did not ship with it; '
     '`references/proof_plugin_contract.md` is exempt by name because it is '
     'written for someone authoring a proof plugin in this repository'),
)


def banned_paths(root=PROJECT_ROOT, files=None, rows=BANNED_PATH_ROWS,
                 strict=True):
    """No shipped prose cites this repository's own `specs/` or `dev/` tree."""
    files = repo_files() if files is None else files
    offenders = []
    for name, scope, exempt, min_files, note in rows:
        scanned = [rel for rel in _scope_files(scope, files)
                   if rel not in exempt]
        if strict and len(scanned) < min_files:
            offenders.append(Offender(
                'dev/prose_lint.py', 0, 'banned_paths',
                f"row {name!r} resolved to {len(scanned)} files, fewer than "
                f"the {min_files} it must read; the sweep would pass by "
                f"scanning nothing"))
            continue
        for rel in scanned:
            try:
                text = _read(rel, root)
            except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
                continue
            for lineno, line in _hits(text, _BACKTICK):
                for token in _BACKTICK.findall(line):
                    if '<' in token or not token.startswith(OWN_TREES):
                        continue
                    target = token.partition('#')[0]
                    if not os.path.isfile(os.path.join(root, target)):
                        continue
                    offenders.append(Offender(
                        rel, lineno, 'banned_paths',
                        f"{name}: `{token}`: {note}: {line.strip()[:160]}"))
    return offenders


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

LINTS = (banned_strings, paths_exist, structure, single_home, banned_paths)


def run_all(root=PROJECT_ROOT, files=None):
    offenders = []
    for lint in LINTS:
        offenders.extend(lint(root=root, files=files))
    return offenders


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--json', action='store_true',
                        help='print the offenders as a JSON array')
    args = parser.parse_args(argv)

    offenders = sorted(run_all(), key=lambda o: (o.path, o.line))
    if args.json:
        print(json.dumps([o.as_dict() for o in offenders], indent=2))
    else:
        for offender in offenders:
            print(offender)
        missing = usage_flags_missing_from_commands()
        if missing:
            print(f"note: {len(missing)} `## Usage` flags are absent from "
                  f"references/purlin_commands.md: {', '.join(missing)}",
                  file=sys.stderr)
        if not offenders:
            print('prose_lint: no offenders')
    return 1 if offenders else 0


if __name__ == '__main__':
    sys.exit(main())
