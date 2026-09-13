#!/usr/bin/env python3
"""Four prose lints over the repository's committed text.

`python3 dev/prose_lint.py` prints one line per offender,

    <path>:<line>: <lint>: <message>

and exits 1 when there is at least one. `--json` prints the same offenders as
a JSON array. `specs/instructions/purlin_prose.md` RULE-12 through RULE-15 own
the four lints and name the file set each one covers today; widening a set is
an edit to the row in this module and to the rule that states it, never a new
rule and never a new module.

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
    return _prose_files() + _tracked('.claude-plugin') + ['CLAUDE.md']


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
#: manifests whose `description` values carried U+2014 as a JSON escape. Widening this
#: to skills/, agents/, references/ and specs/ is an edit to these two scope
#: tuples. `RELEASE_NOTES.md` and `dev/` (including `dev/plans/`) are exempt by
#: name: the notes are a historical record of what was once true, and this
#: module and its proofs carry the banned literals themselves.
DASH_SCOPE = ('docs/**.md', 'README.md',
              'references/remote_verification.md',
              'references/spec_quality_guide.md',
              'references/hard_gates.md',
              'references/audit_criteria.md',
              '.claude-plugin/plugin.json',
              '.claude-plugin/marketplace.json')

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
    ('skills/init/SKILL.md', 'Step 5d - Update'),
    ('skills/verify/SKILL.md', 'Pre-check: pending migrations'),
)

PROSE_SCOPE = ('docs/**', 'references/**', 'skills/**', 'tools/**',
               'agents/**', 'README.md')

REGULATED = 'docs/regulated-environments.md'

#: Every row: (name, unit, pattern, scope, min_files, allowlist, note).
#: `unit` is `line` or `paragraph`. `min_files` is the least number of files
#: the scope must resolve to, so a row cannot pass by scanning nothing. Each
#: `(path, section)` in `allowlist` exempts a hit there AND must still be hit,
#: so an exemption that outlives the text it covers is reported as stale.
BANNED = (
    ('em-dash', 'line', DASH_RE, DASH_SCOPE, 12, (),
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

#: The four references `purlin_docs` RULE-11 named plus the guides and the
#: README: the set held to resolving paths today.
PATH_SCOPE = DASH_SCOPE[:6]

#: A backticked token carrying any of these is not a repository path: an
#: angle bracket or a `$` marks a placeholder, a `*` a glob, a space a command
#: line, a pipe a table cell boundary, `::` a language-scoped name, a leading
#: `/` an absolute path, and a brace an attribute or a template.
PATH_SKIP_CHARS = ('<', '>', '*', '$', ' ', '|', '{', '}')

#: Runtime and user-local state. A checkout is not expected to carry it and a
#: fresh clone never does, so the tokens naming it are not breakages.
RUNTIME_PREFIXES = ('.purlin/cache/', '.purlin/runtime/', '.claude/')

#: Illustrative paths the guides use to show a shape rather than to point at a
#: file. Each must still appear in the scanned set or the lint reports it as a
#: stale exemption.
PATH_ALLOWLIST = (
    'specs/hooks/gate-hook.md',
    'specs/schema/schema_spec_format.md',
    'specs/integration/',
    '.purlin/config.local.json',
    # The workflow purlin:init --ci writes into a consumer project; this
    # repository carries its own verify-gate.yml under a different name.
    '.github/workflows/purlin-verify-gate.yml',
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
                if token.startswith(RUNTIME_PREFIXES):
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
        # A later commit drops the `model:` pin from every agent. The row
        # asserting its absence lands with that commit, not before:
        #   if _frontmatter_field(block, 'model'): offender
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
    ('platform, environment and prerequisite paragraph', 'paragraph',
     re.compile(r'(?=.*\bplatforms?\b)(?=.*\benvironments?\b)'
                r'(?=.*\bprerequisites?\b)', re.IGNORECASE),
     TAXONOMY_HOME, HOME_SCOPE, 1, TAXONOMY_HOME,
     'a paragraph naming all three categories either is the definition or '
     'points at it; a doc that names the three words without the link leaves '
     'a reader with three words and nowhere to resolve them'),
)


def single_home(root=PROJECT_ROOT, files=None, rows=HOMES, strict=True):
    """RULE-15: each row's pattern lives in its home file and nowhere else."""
    files = repo_files() if files is None else files
    offenders = []
    for (name, unit, pattern, home, scope, min_hits, pointer,
         note) in rows:
        scanned = _scope_files(scope, files)
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
# Entry point
# ---------------------------------------------------------------------------

LINTS = (banned_strings, paths_exist, structure, single_home)


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
