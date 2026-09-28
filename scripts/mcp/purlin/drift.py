"""What changed since your last pull, by role.

Drift is for a person who has just brought someone else's changes into their
checkout. It reads git's own log of HEAD for the last action that brought
changes in, a pull, a merge, a rebase, a checkout, a clone or a reset, and
reports what changed between where HEAD stood before that action and HEAD.
It reports facts and judges nothing.

Three role views come out of the same range:

`pm`      rules added, rules changed, rules removed
`eng`     code changed and the rules behind it, changed files under no spec's
          scope, rules with no test, anchors behind their source, features
          whose evidence is out of date
`qa`      test files changed and the features they cover, signatures gone
          stale and why, the size of the queue

Each view is a list of lines, the first naming the range, beside the facts
each line was built from.
"""

import json
import os
import re
import subprocess
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import (fingerprint as fingerprint_module, payload as payload_module,
                    signatures as signatures_module, specs as specs_module)

ROLES = ('pm', 'eng', 'qa')

# How far back drift reads when git's log of HEAD names no action that
# brought changes in, or names only the clone.
DEFAULT_WINDOW = 20

# A `since` value reaches drift from a model-authored tool call, so it is
# untrusted input: a commit count or an ISO date, and nothing else reaches git.
_SINCE_DAYS_RE = re.compile(r'^[0-9]+$')
_SINCE_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

# The reflog actions that bring changes in, as the first word of an entry's
# subject, and how the first line of a view names each.
_ACTIONS = {
    'pull': 'your last pull',
    'merge': 'your last merge',
    'rebase': 'your last rebase',
    'checkout': 'your last checkout',
    'reset': 'your last reset',
    'clone': 'the clone',
}

_SPECS_DIR = 'specs/'


def _git(project_root, args, timeout=15, stdin=None):
    try:
        result = subprocess.run(
            ['git'] + args, capture_output=True, text=True,
            cwd=project_root, timeout=timeout, input=stdin)
    except (subprocess.SubprocessError, OSError):
        return ''
    return result.stdout.strip() if result.returncode == 0 else ''


def _lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Pins
# ---------------------------------------------------------------------------

def source_url_is_safe(url):
    """`(True, '')` or `(False, reason)` for an anchor's `> Source:` value.

    A Source line is repository-supplied text, so it never reaches git in
    option position and never names a transport that runs a command. The
    reason is the phrase the status line prints.
    """
    if not url:
        return True, ''
    if url.startswith('-'):
        return False, 'begins with "-"'
    if 'ext::' in url:
        return False, 'names an ext:: transport'
    if 'fd::' in url:
        return False, 'names an fd:: transport'
    if '\x00' in url:
        return False, 'contains a NUL byte'
    if '\n' in url or '\r' in url:
        return False, 'contains a newline'
    return True, ''


def check_pin(project_root, source_url, pinned, cache=None):
    """`{'status', 'remote_sha', ...}` for one pinned anchor, or None.

    `status` is `current`, `behind`, `unpinned` or `error`. One
    `git ls-remote` per source per run: the cache is keyed on the url, so an
    anchor repo serving six anchors is reached once.
    """
    if not source_url:
        return None
    safe, reason = source_url_is_safe(source_url)
    if not safe:
        return {'status': 'error', 'remote_sha': None,
                'error': 'rejected source url', 'reason': reason}
    if not _looks_like_git(source_url):
        return None
    if not pinned:
        return {'status': 'unpinned', 'remote_sha': None}

    cache = cache if cache is not None else {}
    if source_url in cache:
        remote = cache[source_url]
    else:
        remote = _ls_remote(project_root, source_url)
        cache[source_url] = remote
    if remote.get('error'):
        return {'status': 'error', 'remote_sha': None, 'error': remote['error']}
    remote_sha = remote.get('sha')
    if not remote_sha:
        return {'status': 'error', 'remote_sha': None,
                'error': 'no HEAD ref returned'}
    if remote_sha.startswith(pinned) or pinned.startswith(remote_sha):
        return {'status': 'current', 'remote_sha': remote_sha}
    return {'status': 'behind', 'remote_sha': remote_sha}


# An absolute path on Windows: a drive letter, or a UNC share. Neither begins
# with a slash, so the POSIX test below sees them as free text and an anchor
# sourced from a local clone is never checked on that operating system.
_ABSOLUTE_WINDOWS_PATH = re.compile(r'^(?:[A-Za-z]:[\\/]|\\\\[^\\/])')


def _looks_like_git(url):
    return (url.startswith('git@') or url.endswith('.git')
            or 'github.com' in url or 'gitlab.com' in url
            or url.startswith('/') or url.startswith('.')
            or bool(_ABSOLUTE_WINDOWS_PATH.match(url)))


def _ls_remote(project_root, url):
    try:
        result = subprocess.run(
            ['git', 'ls-remote', '--end-of-options', url, 'HEAD'],
            capture_output=True, text=True, timeout=10,
            cwd=project_root or '.')
    except subprocess.TimeoutExpired:
        return {'error': 'timeout reaching the remote'}
    except (subprocess.SubprocessError, OSError) as exc:
        return {'error': str(exc)[:200]}
    if result.returncode != 0:
        return {'error': ' '.join(result.stderr.split())[:200]}
    lines = result.stdout.strip().splitlines()
    if not lines:
        return {'error': 'no HEAD ref returned'}
    return {'sha': lines[0].split('\t')[0]}


def pin_report(project_root, features, network=True, cache=None):
    """One row per pinned anchor that is not current."""
    rows = []
    if not network:
        return rows
    cache = cache if cache is not None else {}
    for name in sorted(features):
        info = features[name]
        if not info.get('is_anchor') or not info.get('source'):
            continue
        result = check_pin(project_root, info['source'], info.get('pinned'),
                           cache)
        if result is None or result['status'] == 'current':
            continue
        row = {'anchor': name, 'source': info['source'],
               'pinned': info.get('pinned'), 'status': result['status']}
        if result.get('remote_sha'):
            row['remote_sha'] = result['remote_sha'][:7]
        if result.get('error'):
            row['error'] = result['error']
        if result.get('reason'):
            row['reason'] = result['reason']
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# The range
# ---------------------------------------------------------------------------

def _reflog(project_root):
    """`[(sha, when, subject), ...]` for HEAD's reflog, newest first."""
    out = _git(project_root, ['reflog', 'show', '--date=relative',
                              '--format=%H%x09%gd%x09%gs', 'HEAD', '--'])
    entries = []
    for line in out.splitlines():
        parts = line.split('\t', 2)
        if len(parts) != 3:
            continue
        sha, selector, subject = parts
        when = selector[selector.find('{') + 1:selector.rfind('}')] \
            if '{' in selector else ''
        entries.append((sha, when, subject))
    return entries


def _action_of(subject):
    """`(action, stage)` for one reflog subject, or `(None, None)`.

    The action is the first word before the colon; a pull or a rebase that
    ran as several entries carries its stage in parentheses, `start`,
    `pick` or `finish`.
    """
    head = subject.split(':', 1)[0]
    words = head.split()
    if not words or words[0] not in _ACTIONS:
        return None, None
    stage = None
    match = re.search(r'\((\w+)\)\s*$', head)
    if match:
        stage = match.group(1)
    return words[0], stage


def last_action(project_root):
    """The newest reflog entry that brought changes in, or None.

    `{'action', 'when', 'old', 'new'}`. `old` is where HEAD stood before the
    action: the entry below it in the log. A pull or a rebase that ran as
    several entries is measured from where HEAD stood before its first, its
    `start`. A clone has no old sha.
    """
    entries = _reflog(project_root)
    for index, (sha, when, subject) in enumerate(entries):
        action, stage = _action_of(subject)
        if action is None or (stage is not None and stage != 'finish'):
            continue
        start = index
        if stage == 'finish':
            for later in range(index + 1, len(entries)):
                later_action, later_stage = _action_of(entries[later][2])
                if later_action == action and later_stage == 'start':
                    start = later
                    break
        old = entries[start + 1][0] if start + 1 < len(entries) else None
        if action == 'clone':
            old = None
        return {'action': action, 'when': when, 'old': old, 'new': sha}
    return None


def _last_commits(project_root, count):
    """`(from_sha or None, commits)` for the last `count` commits to HEAD.

    With fewer commits than that the range reaches the first commit, and
    there is no sha before it.
    """
    shas = _lines(_git(project_root, ['rev-list', '--max-count=%d' % (count + 1),
                                      'HEAD', '--']))
    if len(shas) > count:
        return shas[count], count
    return None, len(shas)


def _count(project_root, from_sha):
    rev = 'HEAD' if from_sha is None else '%s..HEAD' % from_sha
    text = _git(project_root, ['rev-list', '--count', '--end-of-options', rev])
    return int(text) if text.isdigit() else 0


def resolve_range(project_root, since_arg=None):
    """The range a report measures, or `{'error', 'reason', ...}`.

    `{'from', 'to', 'commits', 'action', 'when', 'phrase', 'line'}`. `from`
    is None where the range reaches the first commit.
    """
    if since_arg is not None and str(since_arg).strip() != '':
        since_arg = str(since_arg).strip()
        if not (_SINCE_DAYS_RE.match(since_arg)
                or _SINCE_DATE_RE.match(since_arg)):
            return {
                'error': 'rejected since',
                'reason': ('since must be a number of commits (digits only) or '
                           'a YYYY-MM-DD date; refusing to pass %r to git'
                           % since_arg),
                'since': since_arg,
            }

    head = _git(project_root, ['rev-parse', '--verify', '-q', 'HEAD'])
    if not head:
        return {'error': 'no commits',
                'reason': 'drift reads git, and HEAD names no commit here'}

    if since_arg:
        if _SINCE_DAYS_RE.match(since_arg):
            from_sha, commits = _last_commits(project_root, int(since_arg))
            phrase = 'in the last %d commits' % commits
            opening = 'The last %d commits' % commits
            action = 'commits'
        else:
            first = _git(project_root, ['log', '--reverse',
                                        '--since=%s' % since_arg,
                                        '--format=%H', 'HEAD', '--'])
            first = first.splitlines()[0] if first else ''
            if first:
                from_sha = _git(project_root, ['rev-parse', '--verify', '-q',
                                               first + '^']) or None
            else:
                from_sha = head
            commits = _count(project_root, from_sha)
            phrase = 'since %s' % since_arg
            opening = 'Since %s' % since_arg
            action = 'date'
        return _range(from_sha, head, commits, action, None, phrase, opening)

    found = last_action(project_root)
    if found and found['old']:
        from_sha = found['old']
        phrase = 'since %s' % _ACTIONS[found['action']]
        opening = 'Since %s, %s' % (_ACTIONS[found['action']], found['when'])
        return _range(from_sha, head, _count(project_root, from_sha),
                      found['action'], found['when'], phrase, opening)

    from_sha, commits = _last_commits(project_root, DEFAULT_WINDOW)
    phrase = 'in the last %d commits' % commits
    if found:
        opening = 'Since the clone, %s, the last %d commits' % (
            found['when'], commits)
        return _range(from_sha, head, commits, 'clone', found['when'],
                      phrase, opening)
    return _range(from_sha, head, commits, None, None, phrase,
                  'The last %d commits' % commits,
                  ' Git\'s log of HEAD names no pull, merge, rebase, checkout, '
                  'clone or reset.')


def _range(from_sha, head, commits, action, when, phrase, opening, tail=''):
    span = ('%s..%s' % (from_sha[:7], head[:7]) if from_sha
            else 'up to %s' % head[:7])
    line = '%s (%s, %s).%s' % (opening, span, _plural(commits, 'commit'), tail)
    return {'from': from_sha, 'to': head, 'commits': commits,
            'action': action, 'when': when, 'phrase': phrase, 'line': line}


def _empty_tree(project_root):
    return _git(project_root, ['hash-object', '-t', 'tree', '--stdin'],
                stdin='')


def _changed_files(project_root, rng):
    """Every path the range added, modified or deleted, sorted."""
    base = rng['from'] or _empty_tree(project_root)
    return sorted(_lines(_git(project_root, [
        'diff', '--name-only', '--no-renames', '--end-of-options',
        base, rng['to'], '--'], timeout=30)))


# ---------------------------------------------------------------------------
# Words
# ---------------------------------------------------------------------------

def _plural(count, word, plural=None):
    return '%d %s' % (count, word if count == 1 else (plural or word + 's'))


def _by_feature(pairs):
    """`{feature: [RULE-N, ...]}` in feature order and rule-number order."""
    grouped = {}
    for feature, rule_id in pairs:
        grouped.setdefault(feature, []).append(rule_id)
    return {name: sorted(set(ids), key=_rule_number)
            for name, ids in sorted(grouped.items())}


def _rule_number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


def _rules_text(grouped):
    """`login RULE-7, RULE-8; export RULE-2`."""
    return '; '.join('%s %s' % (name, ', '.join(ids))
                     for name, ids in grouped.items())


def _rule_count(grouped):
    return sum(len(ids) for ids in grouped.values())


# ---------------------------------------------------------------------------
# The views
# ---------------------------------------------------------------------------

def _rule_map(project_root, ref, paths):
    """`{feature: {RULE-N: text}}` for the specs among `paths` at `ref`."""
    found = {}
    if not ref:
        return found
    for path in paths:
        content = _git(project_root, ['show', '--end-of-options',
                                      '%s:%s' % (ref, path)])
        if not content:
            continue
        name = os.path.splitext(os.path.basename(path))[0]
        found[name] = specs_module._parse_spec(name, path, content)['rules']
    return found


def _pm_view(project_root, rng, changed):
    spec_paths = [path for path in changed
                  if path.startswith(_SPECS_DIR) and path.endswith('.md')]
    before = _rule_map(project_root, rng['from'], spec_paths)
    after = _rule_map(project_root, rng['to'], spec_paths)
    added, changed_rules, removed = [], [], []
    for name in sorted(set(before) | set(after)):
        old = before.get(name, {})
        new = after.get(name, {})
        for rule_id in new:
            if rule_id not in old:
                added.append((name, rule_id))
            elif old[rule_id] != new[rule_id]:
                changed_rules.append((name, rule_id))
        for rule_id in old:
            if rule_id not in new:
                removed.append((name, rule_id))

    view = {'rules_added': _by_feature(added),
            'rules_changed': _by_feature(changed_rules),
            'rules_removed': _by_feature(removed)}
    lines = []
    for key, verb in (('rules_added', 'added'), ('rules_changed', 'changed'),
                      ('rules_removed', 'removed')):
        if view[key]:
            lines.append('%s %s: %s.' % (_plural(_rule_count(view[key]), 'rule'),
                                         verb, _rules_text(view[key])))
    if not lines:
        lines.append('No rule was added, changed or removed %s.'
                     % rng['phrase'])
    return view, lines


def _eng_view(project_root, rng, changed, data, raw_features, markers,
              network):
    present = set(_lines(_git(project_root, ['ls-files'])))
    changed_present = [path for path in changed if path in present]

    code_changed = []
    scoped = set()
    for feature in data.get('features', []):
        files, _unmatched = fingerprint_module.expand_scope(
            project_root, feature.get('scope') or [])
        in_scope = set(files)
        hits = [path for path in changed_present if path in in_scope]
        if not hits:
            continue
        scoped.update(hits)
        rules = [rule['id'] for rule in feature.get('rules', [])
                 if rule.get('label') == 'own']
        code_changed.append({'feature': feature['name'], 'files': hits,
                             'rules': sorted(rules, key=_rule_number)})

    marked = {path for paths in markers.values() for path in paths}
    unscoped = [path for path in changed_present
                if path not in scoped and path not in marked
                and not path.startswith(_SPECS_DIR)
                and not path.startswith('.purlin/')]

    no_test = _by_feature(
        (rule['feature'], rule['id'])
        for feature in data.get('features', [])
        for rule in feature.get('rules', [])
        if rule.get('label') == 'own'
        and ((rule.get('cells') or {}).get('passed') or {}).get('word')
        == 'no test')

    anchors = pin_report(project_root, raw_features, network=network)

    out_of_date = sorted(
        feature['name'] for feature in data.get('features', [])
        if not feature.get('current') and _has_evidence(feature))

    view = {'code_changed': code_changed, 'unscoped': unscoped,
            'rules_without_test': no_test, 'anchors_behind': anchors,
            'out_of_date': out_of_date}
    lines = []
    for entry in code_changed:
        count = len(entry['files'])
        rules = entry['rules']
        behind = ('%s %s behind %s' % (', '.join(rules),
                                        'is' if len(rules) == 1 else 'are',
                                        'it' if count == 1 else 'them')
                  if rules else 'no rule is behind %s'
                  % ('it' if count == 1 else 'them'))
        lines.append('%s changed under %s\'s scope: %s.'
                     % (_plural(count, 'file'), entry['feature'], behind))
    if unscoped:
        lines.append('%s under no spec\'s scope: %s.' % (
            '1 changed file is' if len(unscoped) == 1
            else '%d changed files are' % len(unscoped),
            ', '.join(unscoped)))
    if no_test:
        count = _rule_count(no_test)
        lines.append('%s %s no test: %s.' % (
            _plural(count, 'rule'), 'has' if count == 1 else 'have',
            _rules_text(no_test)))
    for row in anchors:
        lines.append(_anchor_line(row))
    if out_of_date:
        lines.append('%s: %s.' % (
            '1 feature is out of date' if len(out_of_date) == 1
            else '%d features are out of date' % len(out_of_date),
            ', '.join(out_of_date)))
    return view, lines


def _has_evidence(feature):
    evidence = feature.get('evidence') or {}
    return any(entry and entry.get('platforms')
               for entry in evidence.values())


def _anchor_line(row):
    name = row['anchor']
    if row['status'] == 'behind':
        return ('anchor %s is behind its source (now %s). Run: '
                'purlin:anchor sync %s.' % (name, row.get('remote_sha'), name))
    if row['status'] == 'unpinned':
        return ('anchor %s names a source and no pin. Run: '
                'purlin:anchor sync %s.' % (name, name))
    return 'anchor %s: its source could not be read (%s).' % (
        name, row.get('reason') or row.get('error'))


def _qa_view(project_root, rng, changed, data, raw_features, markers):
    covering = {}
    for feature, paths in markers.items():
        for path in paths:
            covering.setdefault(path, set()).add(feature)
    test_files = [path for path in changed if path in covering]
    covered = sorted({name for path in test_files for name in covering[path]})

    signatures = signatures_module.load_signatures(project_root, raw_features)
    stale = []
    for feature in data.get('features', []):
        for rule in feature.get('rules', []):
            if rule.get('label') != 'own' or not rule['flags'].get('stale'):
                continue
            found = signatures.get((rule['feature'], rule['id'])) or []
            stale.append({'feature': rule['feature'], 'rule': rule['id'],
                          'reason': _stale_reason(found[0] if found else {},
                                                  rule)})

    rows = data.get('queue', [])
    hand = sum(1 for row in rows if row.get('need') == 'hand check')
    queue = {'rules': len(rows), 'hand_checks': hand,
             'signatures': len(rows) - hand}

    rules = [(feature, rule) for feature in data.get('features', [])
             for rule in feature.get('rules', []) if rule['label'] == 'own']
    view = {
        'tests_changed': {'files': test_files, 'features': covered},
        'signatures_stale': stale,
        'queue': queue,
        'not_audited': ['%s/%s' % (feature['name'], rule['id'])
                        for feature, rule in rules
                        if rule['flags'].get('not_audited')],
    }

    lines = []
    if test_files:
        lines.append('%s changed, covering %s.' % (
            _plural(len(test_files), 'test file'), ', '.join(covered)))
    # Under the gate `passed` there is no signature and no queue, so no line
    # names either.
    gate = (data.get('gate') or {}).get('gate', 'passed')
    if gate != 'passed':
        if stale:
            lines.append('%s: %s.' % (
                '1 signature is stale' if len(stale) == 1
                else '%d signatures are stale' % len(stale),
                ', '.join('%s %s (%s)' % (row['feature'], row['rule'],
                                          row['reason']) for row in stale)))
        lines.append('Queue: %s. %s, %s.' % (
            _plural(queue['rules'], 'rule'),
            _plural(queue['hand_checks'], 'hand check'),
            _plural(queue['signatures'], 'signature')))
    return view, lines


# What a signature binds, in the words a stale line gives for each.
_BOUND = (('rule_hash', 'rule text changed'), ('proof_hash', 'proofs changed'),
          ('test_hash', 'tests changed'),
          ('audit_hash', 'audit findings changed'))


def _stale_reason(signature, rule):
    parts = [words for key, words in _BOUND
             if str(signature.get(key) or '') != str(rule.get(key) or '')]
    return ', '.join(parts) or 'hashes changed after the signature'


def _specs_uncommitted(project_root):
    out = _git(project_root, ['status', '--porcelain', '--untracked-files=all',
                              '--', _SPECS_DIR])
    paths = set()
    for line in out.splitlines():
        if len(line) > 3:
            path = line[3:].strip('"').split(' -> ')[-1]
            if path.endswith('.md'):
                paths.add(path)
    return len(paths)


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------

def compute_drift(project_root, since=None, network=True, data=None):
    """The whole drift report as a dict: the range and the three views."""
    rng = resolve_range(project_root, since)
    if 'error' in rng:
        return rng

    changed = _changed_files(project_root, rng)
    data = data if data is not None else payload_module.build_payload(
        project_root, generated_by='drift')
    raw_features = specs_module.scan_specs(project_root)
    markers = fingerprint_module.marker_index(project_root)
    uncommitted = _specs_uncommitted(project_root)

    built = {
        'pm': _pm_view(project_root, rng, changed),
        'eng': _eng_view(project_root, rng, changed, data, raw_features,
                         markers, network),
        'qa': _qa_view(project_root, rng, changed, data, raw_features,
                       markers),
    }
    roles = {}
    for role in ROLES:
        view, lines = built[role]
        lines = [rng['line']] + lines
        if uncommitted:
            lines.append('%s changes that are not committed.' % (
                '1 spec file has' if uncommitted == 1
                else '%d spec files have' % uncommitted))
        view['specs_uncommitted'] = uncommitted
        view['lines'] = lines
        roles[role] = view

    since_out = {key: rng[key] for key in ('from', 'to', 'commits', 'action',
                                           'when', 'line')}
    return {'since': since_out, 'roles': roles}


def drift(project_root, since=None, role=None):
    """The drift report as JSON text. A role narrows it to that role's view."""
    result = compute_drift(project_root, since)
    if role and role in ROLES and 'roles' in result:
        result = {'since': result['since'], 'role': role,
                  'view': result['roles'][role]}
    return json.dumps(result, separators=(',', ':'))
