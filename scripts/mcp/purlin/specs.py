"""Read `specs/` into feature dictionaries.

One walk of `specs/` per call answers every question a report asks. A spec is
a markdown file with two sections, `## Rules` and `## Proof`, and a block of
`> Field:` metadata above them. The grammar this module parses is the one
`references/formats/spec_format.md` documents; the anchor fields are the ones
`references/formats/anchor_format.md` documents.

Rule lines carry their tags at the end:

    - RULE-3: Expired tokens are rejected with 401 [risk: high] [origin: pm] [criterion: US-12]

The tags are read off the end and stripped, so `rule_text_hash` sees the claim
alone and re-tagging a rule never stales a signature.

Proof lines carry a tier and at most one operating system:

    - PROOF-3 (RULE-3): POST /login with a token issued 25h ago; verify 401 @integration @env(linux)

`@env` takes `windows`, `macos` or `linux` and nothing else. A proof with no
`@env` is satisfied by a run on any operating system.

Tags this release does not know (`@on(...)`, a bare `@windows`, a stamped  # retired
`@manual(...)`) are ignored, and the file that carried one is named once in
the run's warnings.
"""

import hashlib
import os
import re
import subprocess
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

# Rule tags, read off the end one at a time so the order they are written in
# does not matter and the text that remains is the claim alone.
_RULE_TAG_RE = re.compile(r'\s*\[(risk|origin|criterion):\s*([^\]]+)\]\s*$')

RISK_LEVELS = ('low', 'medium', 'high')
ORIGINS = ('pm', 'design', 'qa', 'eng')
DEFAULT_RISK = 'low'
DEFAULT_ORIGIN = 'eng'

# A trailing tag is metadata appended after the description: ` @e2e`,
# ` @env(linux)`. It must not match a description whose prose merely ends in
# an @word, e.g. "verify the doc lists @integration, @e2e and @unit", so the
# tag may not follow a list connector (`,`, `and`, `or`).
_TIER_TAG_RE = re.compile(r'(?<!\band)(?<!\bor)(?<!,)\s+@(\w+)(?:\(([^)]*)\))?\s*$')

ENVIRONMENTS = ('windows', 'macos', 'linux')

_REQUIRES_RE = re.compile(r'^>\s*Requires:\s*(.+)', re.MULTILINE)
_SCOPE_RE = re.compile(r'^>\s*Scope:\s*(.+)', re.MULTILINE)
_GLOBAL_RE = re.compile(r'^>\s*Global:\s*true\s*$', re.MULTILINE | re.IGNORECASE)
_SOURCE_RE = re.compile(r'^>\s*Source:\s*(.+)', re.MULTILINE)
_PINNED_RE = re.compile(r'^>\s*Pinned:\s*(.+)', re.MULTILINE)
_PATH_RE = re.compile(r'^>\s*Path:\s*(.+)', re.MULTILINE)
_DESCRIPTION_RE = re.compile(r'^>\s*Description:\s*(.+)', re.MULTILINE)
_STACK_RE = re.compile(r'^>\s*Stack:\s*(.+)', re.MULTILINE)
_META_FIELD_RE = re.compile(r'^>\s*[A-Z][A-Za-z-]+:')

# Fields this release no longer reads. A spec that still carries one parses;
# the field is ignored and the file is named once in the run's warnings.
_RETIRED_FIELDS = ('Visual-Reference', 'Visual-Hash')
_RETIRED_FIELD_RE = re.compile(
    r'^>\s*(' + '|'.join(_RETIRED_FIELDS) + r'):', re.MULTILINE)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def split_rule_tags(text):
    """`(clean_text, meta)` for one rule line's description.

    `meta` always carries `risk` and `origin` (defaults `low` and `eng`) and
    carries `criterion` only when the line named one. An unrecognised value
    for risk or origin is kept as written: the reader is better served by
    seeing what the spec says than by a silent correction.
    """
    meta = {}
    text = text.rstrip()
    while True:
        m = _RULE_TAG_RE.search(text)
        if not m:
            break
        name, value = m.group(1), m.group(2).strip()
        meta.setdefault(name, value)
        text = text[:m.start()].rstrip()
    meta.setdefault('risk', DEFAULT_RISK)
    meta.setdefault('origin', DEFAULT_ORIGIN)
    return text, meta


def split_proof_tags(desc):
    """`(clean_desc, tier, env, unknown)` for one proof line's description.

    Tags are read right to left. `@env(<os>)` names the operating system the
    proof must be proved on, at most once, one of `windows`, `macos`,
    `linux`; any other `@<name>` is the tier. `unknown` lists the tags this
    release does not read, so the caller can name the file once rather than
    warning per line.
    """
    desc = desc.rstrip()
    tier = None
    env = None
    unknown = []
    while True:
        m = _TIER_TAG_RE.search(desc)
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
        elif name == 'on':
            # Retired in 0.10.0: `@env(<os>)` replaced it.
            unknown.append('@on(%s)' % (args or ''))  # retired
        elif name == 'windows':
            unknown.append('@windows')
        elif args:
            # A tag with arguments that is not @env is a stamp, and stamps
            # are no longer part of the format. The tier survives it.
            unknown.append('@%s(...)' % name)
            if tier is None:
                tier = name
        elif tier is not None:
            unknown.append('@%s' % name)
        else:
            tier = name
        desc = desc[:m.start()].rstrip()
    return desc, tier or 'unit', env, unknown


# ---------------------------------------------------------------------------
# Hashes
# ---------------------------------------------------------------------------

def _normalise(text):
    return ' '.join((text or '').split())


def rule_text_hash(text):
    """The R of the rule/proof/test triple a signature binds.

    The tags are already off the text by the time a caller holds it, and
    whitespace is normalised here, so reflowing a long rule line does not
    stale the approvals that bind it.
    """
    return hashlib.sha256(_normalise(text).encode('utf-8')).hexdigest()


def proof_text_hash(text):
    """The P of the triple. Same normalisation as `rule_text_hash`."""
    return hashlib.sha256(_normalise(text).encode('utf-8')).hexdigest()


def scope_tree(project_root, scope):
    """A sha256 over the blob ids of the files a spec's `> Scope:` names.

    `git hash-object` gives each file's blob id, the ids are sorted with their
    paths and hashed together, so the answer changes when any scoped file's
    content changes and does not change when the files are merely re-listed.
    A path git cannot hash (it does not exist, or git is unavailable)
    contributes its path and an empty id, so a deleted scope file is a
    different tree rather than an error.

    The record writer reuses this: a record carries the scope tree of each
    spec it covers, and a record whose scope tree differs from the working
    tree's is what makes a rule's passed cell read `code changed`.
    """
    entries = []
    paths = []
    for entry in scope or ():
        entry = entry.strip()
        if not entry:
            continue
        full = os.path.join(project_root, entry)
        if os.path.isdir(full):
            for dirpath, dirnames, filenames in os.walk(full):
                dirnames[:] = sorted(d for d in dirnames if not d.startswith('.'))
                for name in sorted(filenames):
                    paths.append(os.path.relpath(
                        os.path.join(dirpath, name), project_root))
        else:
            paths.append(entry.rstrip('/'))
    for path in sorted(set(paths)):
        entries.append('%s %s' % (path, _blob_id(project_root, path)))
    digest = hashlib.sha256()
    digest.update('\n'.join(entries).encode('utf-8'))
    return digest.hexdigest()


def _blob_id(project_root, rel_path):
    full = os.path.join(project_root, rel_path)
    if not os.path.isfile(full):
        return ''
    try:
        result = subprocess.run(
            ['git', 'hash-object', '--', rel_path],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return ''
    if result.returncode != 0:
        return ''
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Sections and metadata
# ---------------------------------------------------------------------------

def extract_section(content, heading):
    """The body under a markdown heading, up to the next `## ` or the end."""
    pattern = re.compile(
        r'^' + re.escape(heading) + r'\s*\n(.*?)(?=^## |\Z)',
        re.MULTILINE | re.DOTALL)
    m = pattern.search(content)
    return m.group(1) if m else None


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


_GLOB_CHARS = re.compile(r'[*?\[]')


def parse_source(value):
    """`(source, path, globs)` for a `> Source:` value.

    Two shapes. A repository followed by a path in it,
    `https://github.com/acme/policies.git specs/no_eval.md`, gives the first
    two. A list of local file globs, `designs/checkout/*.png,
    designs/checkout/*.pdf`, gives the third. A comma or a glob character is
    what tells them apart, so a source that is neither a URL nor a glob (a
    bare path, or a string a caller should refuse) still comes back as the
    source rather than vanishing into an empty glob list.

    A `> Path:` line still names the path for a source written as a bare URL.
    """
    value = (value or '').strip()
    if not value:
        return None, None, []
    if ',' in value or _GLOB_CHARS.search(value):
        return None, None, _split_list(value)
    parts = value.split(None, 1)
    if len(parts) > 1 and _looks_like_git_url(parts[0]):
        return parts[0], parts[1].strip(), []
    # Not a URL and not a glob list: the whole line is the source, so a value
    # that has to be refused is refused whole rather than by its first word.
    return value, None, []


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
    `specs/`), `name`, `is_anchor`, `is_global`, `description`, `stack`,
    `requires`, `scope`, `rules` (`{RULE-N: text}` with tags stripped),
    `rule_meta` (`{RULE-N: {risk, origin, criterion}}`), `rule_order`,
    `proofs` (`{PROOF-N: {rules, text, tier, env}}`), `proof_env`,
    `proofs_by_rule`, `source`, `source_path`, `source_globs`, `pinned`,
    `has_rules_section`, `unnumbered_lines` and `unknown_tags`.
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
    rule_meta = {}
    rule_order = []
    unnumbered = []
    rules_section = extract_section(content, '## Rules')
    if rules_section is not None:
        for m in _RULE_RE.finditer(rules_section):
            rule_id = m.group(1)
            text, meta = split_rule_tags(m.group(2).strip())
            rules[rule_id] = text
            rule_meta[rule_id] = meta
            rule_order.append(rule_id)
        for line in rules_section.strip().splitlines():
            line = line.strip()
            if line.startswith('- ') and not _RULE_RE.match(line):
                unnumbered.append(line)

    proofs = {}
    proof_env = {}
    proofs_by_rule = {}
    proof_section = extract_section(content, '## Proof')
    if proof_section:
        for line in proof_section.strip().splitlines():
            m = _PROOF_LINE_RE.match(line.strip())
            if not m:
                continue
            proof_id = m.group(1)
            rule_ids = _split_list(m.group(2))
            text, tier, env, unknown = split_proof_tags(m.group(3).strip())
            unknown_tags.extend(unknown)
            proofs[proof_id] = {'rules': rule_ids, 'text': text,
                                'tier': tier, 'env': env}
            proof_env[proof_id] = env
            for rule_id in rule_ids:
                proofs_by_rule.setdefault(rule_id, []).append(proof_id)

    if _RETIRED_FIELD_RE.search(content):
        for field in _RETIRED_FIELDS:
            if re.search(r'^>\s*%s:' % field, content, re.MULTILINE):
                unknown_tags.append('> %s:' % field)

    source_match = _SOURCE_RE.search(content)
    source, source_path, source_globs = parse_source(
        source_match.group(1) if source_match else '')
    path_match = _PATH_RE.search(content)
    if path_match and not source_path:
        source_path = path_match.group(1).strip()
    pinned_match = _PINNED_RE.search(content)

    requires_match = _REQUIRES_RE.search(content)
    scope_match = _SCOPE_RE.search(content)
    stack_match = _STACK_RE.search(content)

    parts = rel_path.split('/')
    category = parts[1] if len(parts) >= 3 else ''

    return {
        'name': name,
        'spec_path': rel_path,
        'category': category,
        'is_anchor': is_anchor,
        'is_global': is_anchor and bool(_GLOBAL_RE.search(content)),
        'description': parse_description(content),
        'stack': stack_match.group(1).strip() if stack_match else None,
        'requires': _split_list(requires_match.group(1)) if requires_match else [],
        'scope': _split_list(scope_match.group(1)) if scope_match else [],
        'rules': rules,
        'rule_meta': rule_meta,
        'rule_order': rule_order,
        'proofs': proofs,
        'proof_env': proof_env,
        'proofs_by_rule': proofs_by_rule,
        'source': source,
        'source_path': source_path,
        'source_globs': source_globs,
        'pinned': pinned_match.group(1).strip() if pinned_match else None,
        'has_rules_section': rules_section is not None,
        'unnumbered_lines': unnumbered,
        'unknown_tags': sorted(set(unknown_tags)),
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
    return ('%d spec files carry tags this release does not read (%s); they are '
            'ignored: %s%s' % (len(carriers), ', '.join(tags),
                               ', '.join(shown), more))


def global_anchors(features):
    """The anchors whose rules apply to every feature without `> Requires:`."""
    return {name: info for name, info in features.items()
            if info.get('is_anchor') and info.get('is_global')}


def rule_refs(feature_name, features):
    """Every `(feature, rule_id, label)` a feature must prove.

    `label` is `own`, `required` (named in `> Requires:`, transitively) or
    `global` (an anchor with `> Global: true`). An anchor proves its own
    rules and nothing else.
    """
    info = features.get(feature_name)
    if not info:
        return []
    refs = [(feature_name, rule_id, 'own') for rule_id in info['rule_order']]
    if info.get('is_anchor'):
        return refs
    seen = {feature_name}
    pending = list(info.get('requires', []))
    while pending:
        required = pending.pop(0)
        if required in seen or required not in features:
            seen.add(required)
            continue
        seen.add(required)
        other = features[required]
        for rule_id in other['rule_order']:
            refs.append((required, rule_id, 'required'))
        pending.extend(other.get('requires', []))
    for anchor_name, anchor in sorted(global_anchors(features).items()):
        if anchor_name in seen:
            continue
        for rule_id in anchor['rule_order']:
            refs.append((anchor_name, rule_id, 'global'))
    return refs
