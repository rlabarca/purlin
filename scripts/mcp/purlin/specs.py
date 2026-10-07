"""Read `specs/` into feature dictionaries.

One walk of `specs/` per call answers every question a report asks. A spec is
a markdown file with two sections, `## Rules` and `## Proof`, and a block of
`> Field:` metadata above them. The grammar this module parses is the one
`references/formats/spec_format.md` documents; the anchor fields are the ones
`references/formats/anchor_format.md` documents.

A rule line is its id and its text, and the text is everything after the id:

    - RULE-3: Expired tokens are rejected with 401

Proof lines carry at most one operating system, `@manual` where no test
can settle the rule, and `@slow` where the proof's test takes a long time:

    - PROOF-3 (RULE-3): POST /login with a token issued 25h ago; verify 401 @env(linux)

`@env` takes `windows`, `macos` or `linux` and nothing else. A proof with no
`@env` is satisfied by a run on any operating system.

The tags 0.9.5 wrote, a bare `@windows` and a stamped `@manual(...)`, are
ignored, and the file that carried one is named once in the run's warnings.
"""

import hashlib
import os
import re
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import notices                                     # noqa: E402

# ---------------------------------------------------------------------------
# A spec's name
# ---------------------------------------------------------------------------

# What a spec's name holds: a letter, a digit or `_`, then those and `-`. The
# marker reader, the anchor's `--name` and the upgrade read the same pattern.
NAME = r'\w[\w-]*'
_NAME_RE = re.compile(NAME)
_NOT_IN_A_NAME_RE = re.compile(r'[^\w-]')


def name_ok(name):
    """True where the whole name matches NAME."""
    return bool(_NAME_RE.fullmatch(name or ''))


def _renamed(name):
    """The name with each character a name cannot hold, and a leading `-`,
    written `_`."""
    new = _NOT_IN_A_NAME_RE.sub('_', name)
    return '_' + new[1:] if new.startswith('-') else new


# ---------------------------------------------------------------------------
# Line grammar
# ---------------------------------------------------------------------------

_RULE_RE = re.compile(r'^-\s+(RULE-\d+):\s*(.+)', re.MULTILINE)
_PROOF_LINE_RE = re.compile(
    r'^-\s+(PROOF-\d+)\s*\((RULE-\d+(?:,\s*RULE-\d+)*)\):\s*(.+)')

# A trailing tag is metadata appended after the description: ` @manual`,
# ` @slow`, ` @env(linux)`. It must not match a description whose prose merely ends in
# an @word, e.g. "verify the doc lists @manual, @env and @word", so the
# tag may not follow a list connector (`,`, `and`, `or`).
_PROOF_TAG_RE = re.compile(r'(?<!\band)(?<!\bor)(?<!,)\s+@(\w+)(?:\(([^)]*)\))?\s*$')

ENVIRONMENTS = ('windows', 'macos', 'linux')

# A tag standing between a proof's id and its rule ids, where no tag is read.
_TAG_BEFORE_RULES_RE = re.compile(
    r'^-\s+PROOF-\d+\s*(?:@manual\b|@slow\b|@env\()')

# A line git leaves in a file whose merge stopped on a conflict: seven of one
# marker character at the start of the line, then a space or the line's end.
CONFLICT_RE = re.compile(r'^(?:<{7}|={7}|>{7}|\|{7})(?:[ \t].*)?$')

_HIGHEST_RULE_RE = re.compile(r'^>[ \t]*Highest-Rule:[ \t]*(\d+)', re.MULTILINE)
_HIGHEST_PROOF_RE = re.compile(r'^>[ \t]*Highest-Proof:[ \t]*(\d+)', re.MULTILINE)

_SCOPE_RE = re.compile(r'^>\s*Scope:\s*(.+)', re.MULTILINE)
_SOURCE_RE = re.compile(r'^>\s*Source:\s*(.+)', re.MULTILINE)
_PINNED_RE = re.compile(r'^>\s*Pinned:\s*(.+)', re.MULTILINE)
_PATH_RE = re.compile(r'^>\s*Path:\s*(.+)', re.MULTILINE)
_DESCRIPTION_RE = re.compile(r'^>\s*Description:\s*(.+)', re.MULTILINE)
_STACK_RE = re.compile(r'^>\s*Stack:\s*(.+)', re.MULTILINE)
_META_FIELD_RE = re.compile(r'^>\s*[A-Z][A-Za-z-]+:')
_HEADING_RE = re.compile(r'^#\s+(?:Feature|Anchor):\s*(.*?)\s*$')

# The fields 0.9.5 wrote that the format does not carry. A spec that still
# carries one parses; the field is ignored and the file is named once in the
# run's warnings.
_RETIRED_FIELDS = ('Visual-Reference', 'Visual-Hash')
_RETIRED_FIELD_RE = re.compile(
    r'^>\s*(' + '|'.join(_RETIRED_FIELDS) + r'):', re.MULTILINE)

# The fields a spec may carry that Purlin does not read, because every anchor
# covers the whole project: a line opening `> Requires:` or `> Global:` on any
# spec, whatever its value, and `> Scope:` on an anchor. Each is warned of.
_REQUIRES_RE = re.compile(r'^>[ \t]*Requires:', re.MULTILINE)
_GLOBAL_RE = re.compile(r'^>[ \t]*Global:', re.MULTILINE)
_SCOPE_LINE_RE = re.compile(r'^>[ \t]*Scope:', re.MULTILINE)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def split_proof_tags(desc):
    """`(clean_desc, manual, env, unknown, slow)` for one proof line's description.

    Tags are read right to left. `@env(<os>)` names the operating system the
    proof must be proved on, at most once, one of `windows`, `macos`,
    `linux`; `@manual` says no test settles the rule; `@slow` says the
    proof's test takes a long time. Any other trailing
    `@<name>` is not a tag: reading stops there and it stays in the text.
    `unknown` lists the tags this release does not read, so the caller can
    name the file once rather than warning per line.
    """
    desc = desc.rstrip()
    manual = False
    slow = False
    env = None
    unknown = []
    while True:
        m = _PROOF_TAG_RE.search(desc)
        if not m:
            break
        name, args = m.group(1), m.group(2)
        if name == 'env':
            value = (args or '').strip()
            if env is not None:
                unknown.append('@env(%s)' % value)
            elif value in ENVIRONMENTS:
                env = value
            else:
                unknown.append('@env(%s)' % value)
        elif name == 'windows':
            unknown.append('@windows')
        elif args:
            # A tag with arguments that is not @env is a stamp, which the
            # format does not carry; a stamped `@manual` still reads manual.
            unknown.append('@%s(...)' % name)
            manual = manual or name == 'manual'
        elif name == 'manual':
            manual = True
        elif name == 'slow':
            slow = True
        else:
            break
        desc = desc[:m.start()].rstrip()
    return desc, manual, env, unknown, slow


# ---------------------------------------------------------------------------
# Hashes
# ---------------------------------------------------------------------------

def _normalise(text):
    return ' '.join((text or '').split())


def rule_text_hash(text):
    """The rule hash a signature binds.

    It is taken over the rule's whole text with whitespace normalised, so
    reflowing a long rule line does not end the signatures that bind it.
    """
    return hashlib.sha256(_normalise(text).encode('utf-8')).hexdigest()


def proof_text_hash(text):
    """The proof hash a signature binds. Same normalisation as `rule_text_hash`."""
    return hashlib.sha256(_normalise(text).encode('utf-8')).hexdigest()


# ---------------------------------------------------------------------------
# Sections and metadata
# ---------------------------------------------------------------------------

def extract_section(content, heading):
    """The body under a markdown heading, up to the next `## ` or the end.

    The heading is matched without regard to case, as the format says.
    """
    pattern = re.compile(
        r'^' + re.escape(heading) + r'\s*\n(.*?)(?=^## |\Z)',
        re.MULTILINE | re.DOTALL | re.IGNORECASE)
    m = pattern.search(content)
    return m.group(1) if m else None


def _section_first_line(content, heading):
    """The 1-based line of the file on which `extract_section`'s body
    starts, or None where the heading is absent."""
    pattern = re.compile(
        r'^' + re.escape(heading) + r'\s*\n(.*?)(?=^## |\Z)',
        re.MULTILINE | re.DOTALL | re.IGNORECASE)
    m = pattern.search(content)
    return content.count('\n', 0, m.start(1)) + 1 if m else None


def _highest(regex, content):
    m = regex.search(content)
    return int(m.group(1)) if m else None


def parse_description(content):
    """The `> Description:` field, joined across its continuation lines.

    A continuation line starts with `>` and is not itself a `> Field:` line.
    """
    m = _DESCRIPTION_RE.search(content)
    if not m:
        return None
    lines = [m.group(1).strip()]
    for line in content[m.end():].splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('>') and not _META_FIELD_RE.match(stripped):
            text = stripped[1:].strip()
            if text:
                lines.append(text)
        else:
            break
    joined = ' '.join(lines)
    return joined or None


def _split_list(value):
    return [part.strip() for part in value.split(',') if part.strip()]


def parse_source(value):
    """`(source, path)` for a `> Source:` value.

    A repository followed by a path in it,
    `https://github.com/acme/policies.git specs/no_eval.md`, gives the two
    separately. Anything else (a bare URL, a local path, or a string a caller
    should refuse) comes back whole as the source.

    A `> Path:` line still names the path for a source written as a bare URL.
    """
    value = (value or '').strip()
    if not value:
        return None, None
    parts = value.split(None, 1)
    if len(parts) > 1 and _looks_like_git_url(parts[0]):
        return parts[0], parts[1].strip()
    # Not a URL followed by a path: the whole line is the source, so a value
    # that has to be refused is refused whole rather than by its first word.
    return value, None


def _looks_like_git_url(value):
    return (value.startswith('git@') or value.endswith('.git')
            or value.startswith('https://') or value.startswith('http://')
            or value.startswith('ssh://'))


# ---------------------------------------------------------------------------
# The scan
# ---------------------------------------------------------------------------

def spec_files(project_root):
    """Every `specs/**/*.md` path, from one walk, in directory order."""
    spec_dir = os.path.join(project_root, 'specs')
    found = []
    if not os.path.isdir(spec_dir):
        return found
    for root, dirnames, filenames in os.walk(spec_dir, followlinks=True):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith('.'))
        for name in sorted(filenames):
            if name.startswith('.') or not name.endswith('.md'):
                continue
            found.append(os.path.join(root, name))
    return found


def scan_specs(project_root):
    """`{feature_name: info}` for every spec under `specs/`.

    Each `info` carries:

    `spec_path` (relative, `/` separated), `category` (the directory under
    `specs/`), `name`, `is_anchor`, `description`, `stack`, `scope` (always
    `[]` for an anchor, which covers the whole project), `unread_fields`
    (`'Requires'`, `'Global'` and `'Scope'`, in that order, for each field
    the spec carries and Purlin does not read), `rules` (`{RULE-N: text}`),
    `rule_order`,
    `proofs` (`{PROOF-N: {rules, text, manual, env}}`), `proof_env`,
    `proofs_by_rule`, `source`, `source_path`, `pinned`,
    `has_rules_section`, `unnumbered_lines`, `unknown_tags`, `highest_rule`
    and `highest_proof` (the number on `> Highest-Rule:` and
    `> Highest-Proof:`, or None), and the ones that `spec_mistakes` and
    `broken_reasons` read: `doubled_rules` and `doubled_proofs` (each rule
    or proof id written more than once, in the order first written),
    `doubled_lines` (`{id: [{'line', 'text'}]}` for each of those ids, one
    entry per line, the line 1-based), `conflict_lines` (`[line, text]` for
    each line left from a merge conflict), `unread_proof_lines` (each list
    item under `## Proof` that is not a proof line) and `heading_name` (the
    name the first line gives, or None).

    Where two specs share a file name the one reached last in the walk is
    read. A rule or proof id written twice is read once, in the place first
    written, with the text of the last line that carries it. A spec holding
    conflict lines is read as any other, both sides' lines included.
    """
    features = {}
    for spec_path in spec_files(project_root):
        rel_path = os.path.relpath(spec_path, project_root).replace(os.sep, '/')
        name = os.path.splitext(os.path.basename(spec_path))[0]
        try:
            with open(spec_path, 'r', encoding='utf-8') as handle:
                content = handle.read()
        except (IOError, OSError, UnicodeDecodeError):
            continue
        features[name] = _parse_spec(name, rel_path, content)
    return features


def _parse_spec(name, rel_path, content):
    is_anchor = ('/_anchors/' in rel_path
                 or content.lstrip().startswith('# Anchor:'))
    unknown_tags = []

    rules = {}
    rule_order = []
    doubled = []
    unnumbered = []
    # Every line of each id, `{id: [{'line', 'text'}]}`; the ids written
    # more than once are kept as `doubled_lines`.
    rule_lines = {}
    proof_lines = {}
    rules_section = extract_section(content, '## Rules')
    if rules_section is not None:
        first = _section_first_line(content, '## Rules')
        for m in _RULE_RE.finditer(rules_section):
            rule_id = m.group(1)
            if rule_id in rules:
                if rule_id not in doubled:
                    doubled.append(rule_id)
            else:
                rule_order.append(rule_id)
            rules[rule_id] = m.group(2).strip()
            rule_lines.setdefault(rule_id, []).append({
                'line': first + rules_section.count('\n', 0, m.start()),
                'text': rules[rule_id]})
        for line in rules_section.strip().splitlines():
            line = line.strip()
            if line.startswith('- ') and not _RULE_RE.match(line):
                unnumbered.append(line)

    proofs = {}
    proof_env = {}
    proofs_by_rule = {}
    unread_proof_lines = []
    doubled_proofs = []
    slow_and_manual = []
    proof_section = extract_section(content, '## Proof')
    if proof_section:
        first = _section_first_line(content, '## Proof')
        for offset, line in enumerate(proof_section.splitlines()):
            m = _PROOF_LINE_RE.match(line.strip())
            if not m:
                if line.strip().startswith('- '):
                    unread_proof_lines.append(line.strip())
                continue
            proof_id = m.group(1)
            rule_ids = _split_list(m.group(2))
            text, manual, env, unknown, slow = split_proof_tags(
                m.group(3).strip())
            unknown_tags.extend(unknown)
            if slow and manual:
                # A hand check has no test to leave out of a run.
                slow = False
                if proof_id not in slow_and_manual:
                    slow_and_manual.append(proof_id)
            if proof_id in proofs and proof_id not in doubled_proofs:
                doubled_proofs.append(proof_id)
            proof_lines.setdefault(proof_id, []).append(
                {'line': first + offset, 'text': text})
            proofs[proof_id] = {'rules': rule_ids, 'text': text,
                                'manual': manual, 'env': env, 'slow': slow}
            proof_env[proof_id] = env
            for rule_id in rule_ids:
                proofs_by_rule.setdefault(rule_id, []).append(proof_id)

    if _RETIRED_FIELD_RE.search(content):
        for field in _RETIRED_FIELDS:
            if re.search(r'^>\s*%s:' % field, content, re.MULTILINE):
                unknown_tags.append('> %s:' % field)

    source_match = _SOURCE_RE.search(content)
    source, source_path = parse_source(
        source_match.group(1) if source_match else '')
    path_match = _PATH_RE.search(content)
    if path_match and not source_path:
        source_path = path_match.group(1).strip()
    pinned_match = _PINNED_RE.search(content)

    scope_match = _SCOPE_RE.search(content)
    unread_fields = []
    if _REQUIRES_RE.search(content):
        unread_fields.append('Requires')
    if _GLOBAL_RE.search(content):
        unread_fields.append('Global')
    if is_anchor and _SCOPE_LINE_RE.search(content):
        unread_fields.append('Scope')
    stack_match = _STACK_RE.search(content)

    parts = rel_path.split('/')
    category = parts[1] if len(parts) >= 3 else ''

    first_line = next((line for line in content.splitlines() if line.strip()),
                      '')
    heading_match = _HEADING_RE.match(first_line.strip())

    return {
        'name': name,
        'spec_path': rel_path,
        'category': category,
        'is_anchor': is_anchor,
        'description': parse_description(content),
        'stack': stack_match.group(1).strip() if stack_match else None,
        'scope': (_split_list(scope_match.group(1))
                  if scope_match and not is_anchor else []),
        'unread_fields': unread_fields,
        'rules': rules,
        'rule_order': rule_order,
        'proofs': proofs,
        'proof_env': proof_env,
        'proofs_by_rule': proofs_by_rule,
        'source': source,
        'source_path': source_path,
        'pinned': pinned_match.group(1).strip() if pinned_match else None,
        'has_rules_section': rules_section is not None,
        'unnumbered_lines': unnumbered,
        'unknown_tags': sorted(set(unknown_tags)),
        'doubled_rules': doubled,
        'doubled_proofs': doubled_proofs,
        'doubled_lines': dict(
            [(rule_id, rule_lines[rule_id]) for rule_id in doubled]
            + [(proof_id, proof_lines[proof_id])
               for proof_id in doubled_proofs]),
        'conflict_lines': [
            [number, line.strip()]
            for number, line in enumerate(content.splitlines(), 1)
            if CONFLICT_RE.match(line)],
        'highest_rule': _highest(_HIGHEST_RULE_RE, content),
        'highest_proof': _highest(_HIGHEST_PROOF_RE, content),
        'unread_proof_lines': unread_proof_lines,
        'slow_and_manual': slow_and_manual,
        'heading_name': heading_match.group(1) if heading_match else None,
    }


def unknown_tag_warning(features):
    """One line for the tags this release ignores, about the tags.

    A warning per line would print hundreds on a project mid-migration. One
    line names the tags, how many specs carry one and the first of those
    files, which is what a reader acts on.
    """
    carriers = sorted(info['spec_path'] for info in features.values()
                      if info.get('unknown_tags'))
    if not carriers:
        return None
    tags = sorted({tag for info in features.values()
                   for tag in info.get('unknown_tags', ())})
    wrong = (UNKNOWN_TAGS_ONE % carriers[0] if len(carriers) == 1
             else UNKNOWN_TAGS_MANY % (len(carriers), carriers[0]))
    return notices.line('tag_unread', ', '.join(tags), wrong,
                        notices.run('purlin:init --update'))


def unnumbered_warnings(features):
    """One line per spec holding a line under `## Rules` with no number."""
    lines = []
    for name in sorted(features):
        count = len(features[name].get('unnumbered_lines') or ())
        if count:
            lines.append(_mistake(
                'unnumbered', name,
                UNNUMBERED_ONE if count == 1 else UNNUMBERED_MANY % count))
    return lines


def _mistake(kind, name, wrong, do=None, about=None, rule=None, proof=None):
    """One spec mistake's line, ending on `Run purlin:spec <name>.` unless
    `do` says otherwise."""
    return notices.line(kind, about or name, wrong,
                        do or notices.run('purlin:spec %s' % name),
                        feature=name, rule=rule, proof=proof)


# What each spec mistake's line says is wrong, after `<name>: <kind>.`
# (`notices.line`), and what to do where it is not `Run purlin:spec <name>.`
SAME_NAME = 'Only %s is read.'
SAME_NAME_DO = 'Run git mv %s %s/<new name>.md.'
WRITTEN_TWICE = 'It is written twice, and the second is read.'
CONFLICT_ONE = '1 line is left from a merge conflict, at line %d.'
CONFLICT_MANY = '%d lines are left from a merge conflict, the first at line %d.'
NAME_REFUSED = 'A name holds letters, digits, _ and -.'
NAME_REFUSED_DO = 'Run git mv %s %s.'
PROOF_LINE_UNREAD = '%s: "%s".'
TAG_AT_END = 'A tag goes last'
NOT_A_PROOF_LINE = 'It is not `- PROOF-N (RULE-N): <text>`'
HEADING_NAMES_OTHER = 'It names %s.'
SLOW_AND_MANUAL = 'It is read as @manual, not @slow.'
UNREAD_FIELD = 'Every anchor covers the whole project, so %s is not read.'
REMOTE_UNREAD = 'Its source carries %s.'
REMOTE_UNREAD_DO = 'Ask its owners to take %s out, then run purlin:anchor sync %s.'
UNNUMBERED_ONE = '1 line under ## Rules is not numbered.'
UNNUMBERED_MANY = '%d lines under ## Rules are not numbered.'
# The specs that carry a tag this release ignores: the one, or how many and
# the first.
UNKNOWN_TAGS_ONE = 'Found in %s.'
UNKNOWN_TAGS_MANY = 'Found in %d specs, the first %s.'

# Why every rule of a spec reads `failed`: `broken_reasons` gives them.
DOUBLED_REASON = '%s is written twice in the spec'
CONFLICT_REASON = 'the spec holds a line left from a merge conflict'

# How many words of a line under `## Proof` that is not read its warning
# quotes: enough to find the line, its id and what stands after it.
PROOF_LINE_WORDS = 4


def spec_mistakes(project_root, features):
    """One line per mistake Purlin can see in a spec, each naming its fix.

    `features` is `scan_specs`' answer. The lines are warned of; a number
    written twice and a line left from a merge conflict also make every rule
    of the spec read `failed` (`broken_reasons`). They come in the order of
    the mistakes, each sorted by feature: two specs with one name, a name
    holding a character a name cannot (with the `git mv` that renames the
    file), a rule id written twice, a proof id written twice, the lines
    left from a merge conflict (one line per spec), a line under `## Proof`
    that is not a proof line (its first 4 words quoted, with the reason), a first line
    naming another feature, a proof tagged both `@slow` and `@manual`, then
    the fields Purlin does not read: every `> Requires:`, then every `> Global:`, then every
    anchor's `> Scope:`. A remote anchor carrying any of the three has one
    line naming them all and its source, sorted with the `> Scope:` lines.
    A `> Scope:` entry naming a file git does not have is no mistake: the
    status names it as information (`status.not_written_lines`).
    """
    lines = []
    by_name = {}
    for spec_path in spec_files(project_root):
        rel_path = os.path.relpath(spec_path, project_root).replace(os.sep, '/')
        stem = os.path.splitext(os.path.basename(spec_path))[0]
        by_name.setdefault(stem, []).append(rel_path)
    for name in sorted(by_name):
        if len(by_name[name]) < 2 or name not in features:
            continue
        kept = features[name]['spec_path']
        for dropped in by_name[name]:
            if dropped == kept:
                continue
            lines.append(_mistake(
                'same_name', name, SAME_NAME % kept,
                SAME_NAME_DO % (dropped, dropped.rsplit('/', 1)[0])))

    for name in sorted(features):
        if name_ok(name):
            continue
        path = features[name]['spec_path']
        folder = path.rsplit('/', 1)[0]
        lines.append(_mistake(
            'name_refused', name, NAME_REFUSED,
            NAME_REFUSED_DO % (path, '%s/%s.md' % (folder, _renamed(name)))))

    for name in sorted(features):
        for rule_id in features[name].get('doubled_rules') or ():
            lines.append(_mistake('to_repair', name, WRITTEN_TWICE,
                                  about='%s %s' % (name, rule_id),
                                  rule=rule_id))
    for name in sorted(features):
        for proof_id in features[name].get('doubled_proofs') or ():
            # Its two lines may name two rules, so the proof stands alone.
            lines.append(_mistake('to_repair', name, WRITTEN_TWICE,
                                  about='%s %s' % (name, proof_id),
                                  proof=proof_id))
    for name in sorted(features):
        conflicts = features[name].get('conflict_lines') or ()
        if not conflicts:
            continue
        number = conflicts[0][0]
        if len(conflicts) == 1:
            lines.append(_mistake('to_repair', name, CONFLICT_ONE % number))
        else:
            lines.append(_mistake('to_repair', name, CONFLICT_MANY % (
                len(conflicts), number)))
    for name in sorted(features):
        for line in features[name].get('unread_proof_lines') or ():
            why = (TAG_AT_END if _TAG_BEFORE_RULES_RE.match(line)
                   else NOT_A_PROOF_LINE)
            lines.append(_mistake('proof_unread', name, PROOF_LINE_UNREAD % (
                why, notices.shown(line, PROOF_LINE_WORDS))))
    for name in sorted(features):
        other = features[name].get('heading_name')
        if other and other != name:
            lines.append(_mistake('heading', name,
                                  HEADING_NAMES_OTHER % other))
    for name in sorted(features):
        for proof_id in features[name].get('slow_and_manual') or ():
            lines.append(_proof_mistake('tags_conflict', features[name],
                                        name, proof_id, SLOW_AND_MANUAL))
    for field in ('Requires', 'Global'):
        for name in sorted(features):
            info = features[name]
            if field in (info.get('unread_fields') or ()) and not _remote(info):
                lines.append(_mistake('line_unread', name,
                                      UNREAD_FIELD % ('> %s:' % field)))
    for name in sorted(features):
        info = features[name]
        fields = info.get('unread_fields') or ()
        if not fields:
            continue
        if _remote(info):
            lines.append(_mistake(
                'line_unread', name,
                REMOTE_UNREAD % _join_fields(fields),
                REMOTE_UNREAD_DO % ('it' if len(fields) == 1 else 'them',
                                    name)))
        elif 'Scope' in fields:
            lines.append(_mistake('line_unread', name,
                                  UNREAD_FIELD % '> Scope:'))
    return lines


def _proof_mistake(kind, info, name, proof_id, wrong):
    """A mistake in one proof: named `<spec> PROOF-N (RULE-N)`."""
    about, rule = notices.about_proof(info, name, proof_id)
    return _mistake(kind, name, wrong, about=about, rule=rule, proof=proof_id)


def broken_reasons(info):
    """Why every rule of this spec reads `failed`, or [] when nothing does.

    One `DOUBLED_REASON` per id of `doubled_rules`, then one per id of
    `doubled_proofs`, each in the order first written, then `CONFLICT_REASON`
    once where `conflict_lines` is not empty."""
    reasons = [DOUBLED_REASON % rule_id
               for rule_id in info.get('doubled_rules') or ()]
    reasons += [DOUBLED_REASON % proof_id
                for proof_id in info.get('doubled_proofs') or ()]
    if info.get('conflict_lines'):
        reasons.append(CONFLICT_REASON)
    return reasons


def _remote(info):
    """True for a remote anchor, one pulled from another repository: it carries
    `> Source:`."""
    return bool(info.get('is_anchor') and info.get('source'))


def _join_fields(fields):
    """`> Global: and > Scope:`: each field as its line opens, joined `, `
    with ` and ` before the last."""
    shown = ['> %s:' % field for field in fields]
    if len(shown) == 1:
        return shown[0]
    return ', '.join(shown[:-1]) + ' and ' + shown[-1]
