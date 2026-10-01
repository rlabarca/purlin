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
    """One line naming every spec that carries a tag this release ignores.

    A warning per line would print hundreds on a project mid-migration. One
    line names the files and says what was skipped, which is what a reader
    acts on.
    """
    carriers = sorted(info['spec_path'] for info in features.values()
                      if info.get('unknown_tags'))
    if not carriers:
        return None
    tags = sorted({tag for info in features.values()
                   for tag in info.get('unknown_tags', ())})
    shown = carriers[:5]
    more = '' if len(carriers) <= 5 else ', and %d more' % (len(carriers) - 5)
    count = ('1 spec file carries' if len(carriers) == 1
             else '%d spec files carry' % len(carriers))
    return ('%s tags this release does not read (%s); they are ignored: %s%s. '
            'Run purlin:init --update to remove them.'
            % (count, ', '.join(tags), ', '.join(shown), more))


SAME_NAME = ('%s and %s are both named %s; only %s is read. Rename one: '
             'git mv %s %s/<new name>.md')
RULE_WRITTEN_TWICE = ('%s: %s is written twice; the second is read. '
                      'Run purlin:spec %s.')
PROOF_WRITTEN_TWICE = ('%s: %s is written twice; the second is read. '
                       'Run purlin:spec %s.')
CONFLICT_ONE = ('%s: 1 line is left from a merge conflict, at line %d: %s. '
                'Run purlin:spec %s.')
CONFLICT_MANY = ('%s: %d lines are left from a merge conflict, the first at '
                 'line %d: %s. Run purlin:spec %s.')
PROOF_LINE_UNREAD = ('%s: a line under ## Proof cannot be read: %s. '
                     'Run purlin:spec %s.')

# Why every rule of a spec reads `failed`: `broken_reasons` gives them.
DOUBLED_REASON = '%s is written twice in the spec'
CONFLICT_REASON = 'the spec holds a line left from a merge conflict'
HEADING_NAMES_OTHER = ('%s: the first line names %s, but the file is %s.md, so '
                       'it is read as %s. Run purlin:spec %s.')
SLOW_AND_MANUAL = ('%s: %s is tagged @slow and @manual; a hand check has no '
                   'test to leave out, so it is read as @manual. '
                   'Run purlin:spec %s.')
UNREAD_REQUIRES = ('%s: > Requires: is not read, because every anchor covers '
                   'the whole project. Run purlin:spec %s.')
UNREAD_GLOBAL = ('%s: > Global: is not read, because every anchor covers the '
                 'whole project. Run purlin:spec %s.')
UNREAD_SCOPE = ('%s: > Scope: is not read on an anchor, because an anchor '
                'covers the whole project. Run purlin:spec %s.')
PINNED_UNREAD = ('%s: its source, %s, carries %s, which Purlin does not read '
                 'on an anchor, so %s read as nothing. Ask the owners of %s to '
                 'take %s out, then run purlin:anchor sync %s.')

# How much of a proof line that cannot be read its warning quotes.
PROOF_LINE_SHOWN = 60


def spec_mistakes(project_root, features):
    """One line per mistake Purlin can see in a spec, each naming its fix.

    `features` is `scan_specs`' answer. The lines are warned of; a number
    written twice and a line left from a merge conflict also make every rule
    of the spec read `failed` (`broken_reasons`). They come in the order of
    the mistakes, each sorted by feature: two specs with one name, a rule id
    written twice, a proof id written twice, the lines left from a merge
    conflict (one line per spec), a line under `## Proof` that is not a
    proof line, a first line naming another feature, a proof tagged both
    `@slow` and `@manual`, then the fields Purlin
    does not read: every `> Requires:`, then every `> Global:`, then every
    anchor's `> Scope:`. A pinned anchor carrying any of the three has one
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
            lines.append(SAME_NAME % (kept, dropped, name, kept, dropped,
                                      dropped.rsplit('/', 1)[0]))

    for name in sorted(features):
        for rule_id in features[name].get('doubled_rules') or ():
            lines.append(RULE_WRITTEN_TWICE % (name, rule_id, name))
    for name in sorted(features):
        for proof_id in features[name].get('doubled_proofs') or ():
            lines.append(PROOF_WRITTEN_TWICE % (name, proof_id, name))
    for name in sorted(features):
        conflicts = features[name].get('conflict_lines') or ()
        if not conflicts:
            continue
        number, shown = conflicts[0][0], conflicts[0][1][:PROOF_LINE_SHOWN]
        if len(conflicts) == 1:
            lines.append(CONFLICT_ONE % (name, number, shown, name))
        else:
            lines.append(CONFLICT_MANY % (name, len(conflicts), number, shown,
                                          name))
    for name in sorted(features):
        for line in features[name].get('unread_proof_lines') or ():
            lines.append(PROOF_LINE_UNREAD
                         % (name, line[:PROOF_LINE_SHOWN], name))
    for name in sorted(features):
        other = features[name].get('heading_name')
        if other and other != name:
            lines.append(HEADING_NAMES_OTHER % (name, other, name, name, name))
    for name in sorted(features):
        for proof_id in features[name].get('slow_and_manual') or ():
            lines.append(SLOW_AND_MANUAL % (name, proof_id, name))
    for field, line in (('Requires', UNREAD_REQUIRES), ('Global', UNREAD_GLOBAL)):
        for name in sorted(features):
            info = features[name]
            if field in (info.get('unread_fields') or ()) and not _pinned(info):
                lines.append(line % (name, name))
    for name in sorted(features):
        info = features[name]
        fields = info.get('unread_fields') or ()
        if not fields:
            continue
        if _pinned(info):
            lines.append(PINNED_UNREAD % (
                name, info['source'], _join_fields(fields),
                'the line is' if len(fields) == 1 else 'the lines are',
                info['source'], 'it' if len(fields) == 1 else 'them', name))
        elif 'Scope' in fields:
            lines.append(UNREAD_SCOPE % (name, name))
    return lines


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


def _pinned(info):
    """True for an anchor pulled from another repository: one carrying
    `> Source:`."""
    return bool(info.get('is_anchor') and info.get('source'))


def _join_fields(fields):
    """`> Global: and > Scope:`: each field as its line opens, joined `, `
    with ` and ` before the last."""
    shown = ['> %s:' % field for field in fields]
    if len(shown) == 1:
        return shown[0]
    return ', '.join(shown[:-1]) + ' and ' + shown[-1]
