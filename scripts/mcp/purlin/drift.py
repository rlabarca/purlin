"""What changed since your last pull, in one view.

Drift is for a person who has just brought someone else's changes into their
checkout. It reads git's own log of HEAD for the last action that brought
changes in, a pull, a merge, a merge committed after its conflicts were
resolved, a rebase, a checkout, a clone or a reset, and reports what changed
between where HEAD stood before that action and HEAD. It reports facts and
judges nothing.

The one view names, after a first line naming the range: the rules added,
changed and removed; the proofs added, changed and moved; each number a spec
of this checkout writes twice, with the line that keeps it, each proof that
follows a moved rule, and how old this checkout's copy of the default branch
is; each test comment whose proof's
wording changed after its test was last changed, as `wording.py` finds it;
and each remote anchor that is not current, checked against its source
without pulling it. Lines the status already prints are not repeated here.
While a merge is in progress and not committed, the second line says so.

Drift reads only this checkout: it writes no file, fetches nothing and
pulls no anchor. The view is a list of lines beside the facts each line was
built from.
"""

import json
import os
import re
import subprocess
import sys
import time

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from config_engine import config_problem
from purlin import (markers as markers_module, notices,
                    specs as specs_module,
                    wording as wording_module)

# The view's keys, the facts its lines are built from.
VIEW_KEYS = ('anchors_behind', 'comments_changed', 'default_branch', 'lines',
             'merge_in_progress', 'numbers_twice', 'proofs_added',
             'proofs_changed', 'proofs_moved', 'rules_added', 'rules_changed',
             'rules_removed')

# How far back drift reads when git's log of HEAD names no action that
# brought changes in, or names only the clone.
DEFAULT_WINDOW = 20

# A `since` value reaches drift from a model-authored tool call, so it is
# untrusted input: a commit count or an ISO date, and nothing else reaches git.
_SINCE_DAYS_RE = re.compile(r'^[0-9]+$')
_SINCE_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

# The reflog actions that bring changes in, as the first word of an entry's
# subject, and how the first line of a view names each. A merge that stopped
# on conflicts is finished by a commit, which git logs as `commit (merge)`;
# it is read as a merge.
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


# The reason an anchor whose `> Source:` names no repository cannot be
# checked: the source as written, then the anchor's name.
NOT_A_SPEC_SOURCE = (
    "its source, %s, is not a spec in Purlin's format kept in a git "
    "repository, so it cannot be checked. Run purlin:spec %s to take out its "
    "> Source: and > Pinned: lines and keep it as this project's own anchor.")


def not_a_spec_source(name, source):
    """`NOT_A_SPEC_SOURCE` filled in for the anchor `name`."""
    return NOT_A_SPEC_SOURCE % (source, name)


def source_is_repository(project_root, source):
    """False when a `> Source:` value names no repository, True otherwise.

    A value holding whitespace is a description in words, and a value naming
    a file that exists, joined to the project root or as written, is a file
    on disk. Every other value is taken as a repository and asked with git.
    """
    source = source or ''
    if re.search(r'\s', source):
        return False
    candidates = [source]
    if project_root:
        candidates.append(os.path.join(project_root, source))
    for candidate in candidates:
        try:
            if os.path.isfile(candidate):
                return False
        except (ValueError, OSError):
            continue
    return True


def check_pin(project_root, source_url, pinned, cache=None):
    """`{'status', 'remote_sha', ...}` for one remote anchor, or None.

    `status` is `current`, `behind`, `unpinned` or `error`. One
    `git ls-remote` per source per run: the cache is keyed on the url, so an
    anchor repo serving six anchors is reached once. A source that names no
    repository is `error` with `not_a_spec`, and no process is handed it.
    """
    if not source_url:
        return None
    safe, reason = source_url_is_safe(source_url)
    if not safe:
        return {'status': 'error', 'remote_sha': None,
                'error': 'rejected source url', 'reason': reason}
    if not source_is_repository(project_root, source_url):
        return {'status': 'error', 'remote_sha': None, 'not_a_spec': True}
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
# with a slash, so the test below names both, to read a local clone on that
# operating system as a git repository.
_ABSOLUTE_WINDOWS_PATH = re.compile(r'^(?:[A-Za-z]:[\\/]|\\\\[^\\/])')


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
    """One row per remote anchor that is not current."""
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
        if result.get('not_a_spec'):
            row['not_a_spec'] = True
            row['error'] = not_a_spec_source(name, info['source'])
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
    `pick` or `finish`. `commit (merge)`, the commit that finishes a merge
    whose conflicts were resolved, is a merge in one entry; any other commit
    is not an action.
    """
    head = subject.split(':', 1)[0]
    words = head.split()
    stage = None
    match = re.search(r'\((\w+)\)\s*$', head)
    if match:
        stage = match.group(1)
    if words[:1] == ['commit'] and stage == 'merge':
        return 'merge', None
    if not words or words[0] not in _ACTIONS:
        return None, None
    return words[0], stage


def last_action(project_root):
    """The newest reflog entry that brought changes in, or None.

    `{'action', 'when', 'old', 'new'}`. `old` is where HEAD stood before the
    action: the entry below it in the log. A pull or a rebase that ran as
    several entries is measured from where HEAD stood before its first, its
    `start`. A checkout that leaves HEAD at the commit it stood at, as
    `git checkout -b` does, brought nothing in and is passed over. A clone
    has no old sha.
    """
    entries = _reflog(project_root)
    for index, (sha, when, subject) in enumerate(entries):
        action, stage = _action_of(subject)
        if action is None or (stage is not None and stage != 'finish'):
            continue
        if (action == 'checkout' and index + 1 < len(entries)
                and entries[index + 1][0] == sha):
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


def _last_commits(project_root, count, head):
    """`(from_sha or None, commits)` for the last `count` commits to `head`.

    With fewer commits than that the range reaches the first commit, and
    there is no sha before it.
    """
    shas = _lines(_git(project_root, ['rev-list', '--max-count=%d' % (count + 1),
                                      '--end-of-options', head, '--']))
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
                           'a YYYY-MM-DD date; refusing to pass %s to git'
                           % json.dumps(since_arg)),
                'since': since_arg,
            }

    head = _git(project_root, ['rev-parse', '--verify', '-q', 'HEAD'])
    if not head:
        return {'error': 'no commits',
                'reason': 'drift reads git, and HEAD names no commit here'}

    if since_arg:
        if _SINCE_DAYS_RE.match(since_arg):
            from_sha, commits = _last_commits(project_root, int(since_arg),
                                              head)
            phrase = 'in %s' % _last(commits)
            opening = 'The %s' % _last(commits)
            action = 'commits'
        else:
            first = _git(project_root, ['log', '--reverse',
                                        '--since=%s' % since_arg,
                                        '--format=%H', 'HEAD', '--'])
            first = first.splitlines()[0] if first else ''
            if first:
                from_sha = _git(project_root, ['rev-parse', '--verify', '-q',
                                               '--end-of-options',
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

    from_sha, commits = _last_commits(project_root, DEFAULT_WINDOW, head)
    phrase = 'in %s' % _last(commits)
    if found:
        opening = 'Since the clone, %s, %s' % (found['when'], _last(commits))
        return _range(from_sha, head, commits, 'clone', found['when'],
                      phrase, opening)
    return _range(from_sha, head, commits, None, None, phrase,
                  'The %s' % _last(commits),
                  ' Git\'s log of HEAD names no pull, merge, rebase, checkout, '
                  'clone or reset.')


def _last(commits):
    """`last commit` for one commit, `last <n> commits` for any other count."""
    return 'last commit' if commits == 1 else 'last %d commits' % commits


def _range(from_sha, head, commits, action, when, phrase, opening, tail=''):
    span = ('%s..%s' % (from_sha[:7], head[:7]) if from_sha
            else 'up to %s' % head[:7])
    line = '%s (%s, %s).%s' % (opening, span, _plural(commits, 'commit'), tail)
    return {'from': from_sha, 'to': head, 'commits': commits,
            'action': action, 'when': when, 'phrase': phrase, 'line': line}


def _empty_tree(project_root):
    return _git(project_root, ['hash-object', '-t', 'tree', '--stdin'],
                stdin='')


def _changed_files(project_root, rng, paths):
    """The paths under `paths` the range added, modified or deleted, sorted."""
    if not paths:
        return []
    base = rng['from'] or _empty_tree(project_root)
    return sorted(_lines(_git(project_root, [
        'diff', '--name-only', '--no-renames', '--end-of-options',
        base, rng['to'], '--'] + list(paths), timeout=30)))


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
# The view
# ---------------------------------------------------------------------------

def _spec_map(project_root, ref, paths):
    """`{feature: parsed spec}` for the specs among `paths` at `ref`."""
    found = {}
    if not ref:
        return found
    for path in paths:
        content = _git(project_root, ['show', '--end-of-options',
                                      '%s:%s' % (ref, path)])
        if not content:
            continue
        name = os.path.splitext(os.path.basename(path))[0]
        found[name] = specs_module._parse_spec(name, path, content)
    return found


def _spec_paths(changed):
    return [path for path in changed
            if path.startswith(_SPECS_DIR) and path.endswith('.md')]


def _rules_view(rng, before, after):
    """The rules the range added, changed and removed, and their lines.

    A number a spec writes twice at either end is named as written twice,
    and never here.
    """
    added, changed_rules, removed = [], [], []
    for name in sorted(set(before) | set(after)):
        twice = _twice(before.get(name), after.get(name))
        old = {rule_id: text for rule_id, text
               in before.get(name, {}).get('rules', {}).items()
               if rule_id not in twice}
        new = {rule_id: text for rule_id, text
               in after.get(name, {}).get('rules', {}).items()
               if rule_id not in twice}
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


def _proof_texts(parsed):
    return {proof_id: proof['text']
            for proof_id, proof in (parsed or {}).get('proofs', {}).items()}


def _twice(*parsed):
    """Every id any of `parsed` writes twice."""
    return {item for spec in parsed
            for item in ((spec or {}).get('doubled_lines') or {})}


def _proofs_view(before, after):
    """The proofs the range added, changed and moved, and their lines.

    A proof moved when its text at the range's start is, unchanged, under
    another id of the same spec at its end, an id that did not hold that
    text at the start. An id whose text differs between the two ends is
    changed; one absent at the start and not a move is added. A number
    written twice at either end is named as written twice, and never here.
    """
    added, changed, moved = [], [], []
    for name in sorted(set(before) | set(after)):
        twice = _twice(before.get(name), after.get(name))
        old = {proof_id: text for proof_id, text
               in _proof_texts(before.get(name)).items() if proof_id not in twice}
        new = {proof_id: text for proof_id, text
               in _proof_texts(after.get(name)).items() if proof_id not in twice}
        targets = set()
        for proof_id in sorted(old, key=_rule_number):
            text = old[proof_id]
            if new.get(proof_id) == text:
                continue
            to = [other for other in sorted(new, key=_rule_number)
                  if other != proof_id and new[other] == text
                  and old.get(other) != text and other not in targets]
            if to:
                targets.add(to[0])
                moved.append({'feature': name, 'from': proof_id, 'to': to[0]})
        for proof_id in sorted(new, key=_rule_number):
            if proof_id not in old:
                if proof_id not in targets:
                    added.append((name, proof_id))
            elif old[proof_id] != new[proof_id]:
                changed.append({'feature': name, 'id': proof_id,
                                'old': old[proof_id], 'new': new[proof_id]})

    view = {'proofs_added': _by_feature(added), 'proofs_changed': changed,
            'proofs_moved': moved}
    lines = []
    if view['proofs_added']:
        lines.append('%s added: %s.' % (
            _plural(_rule_count(view['proofs_added']), 'proof'),
            _rules_text(view['proofs_added'])))
    for entry in changed:
        lines.append('%s %s changed: it read "%s" and now reads "%s".' % (
            entry['feature'], entry['id'], entry['old'], entry['new']))
    for entry in moved:
        lines.append('%s %s moved to %s.' % (entry['feature'], entry['from'],
                                             entry['to']))
    return view, lines


# What an anchor's line says is wrong, after `<anchor>: <kind>.`
PIN_BEHIND = 'The pin %s is behind its source, now %s.'
PIN_MISSING = 'It names a source and no pin.'
SOURCE_UNREAD = 'Its source could not be read (%s).'
SOURCE_UNREAD_DO = 'Check its > Source: line, then run purlin:anchor sync %s.'
SOURCE_REFUSED = 'Its > Source: line %s.'


def pin_line(row):
    """One row of `pin_report` as the line the status, the dashboard and
    drift print for it."""
    name = row['anchor']
    sync = notices.run('purlin:anchor sync %s' % name)
    if row.get('not_a_spec'):
        error = row['error']
        return notices.line('source_not_spec', name,
                            error[:1].upper() + error[1:], feature=name)
    if row.get('reason'):
        return notices.line('source_refused', name,
                            SOURCE_REFUSED % row['reason'],
                            notices.run('purlin:spec %s' % name), feature=name)
    if row['status'] == 'behind':
        return notices.line('pin_behind', name, PIN_BEHIND % (
            (row.get('pinned') or '')[:7], (row.get('remote_sha') or '')[:7]),
            sync,
            feature=name)
    if row['status'] == 'unpinned':
        return notices.line('pin_missing', name, PIN_MISSING, sync,
                            feature=name)
    return notices.line('source_unread', name,
                        SOURCE_UNREAD % row.get('error', 'unknown'),
                        SOURCE_UNREAD_DO % name, feature=name)


# ---------------------------------------------------------------------------
# This checkout against its copy of the default branch
# ---------------------------------------------------------------------------

_REMOTES = 'refs/remotes/'

# What a number written twice's line says, after `<spec> <id>: number
# written twice.`: which line keeps it, then what to do, the line that moves
# shown by its first words.
NUMBER_KEPT = 'The line on %s keeps it.'
NUMBER_NEITHER = 'Neither line is on %s, and the one that reaches it first keeps the number.'
NUMBER_ON_DEFAULT = '%s itself writes it twice.'
NUMBER_NO_DEFAULT = 'This checkout has no copy of a default branch to say which line keeps it.'
RENUMBER_OTHER = 'Renumber the other to %s and move its test comments with it.'
RENUMBER_SECOND = 'Renumber the second to %s and move its test comments with it.'
RENUMBER_UNMERGED = ('Renumber the one not yet merged to %s and move its test '
                     'comments with it.')
RENUMBER_SHOWN = ' It reads "%s".'
PROOF_WILL_NAME = '%s: %s will name %s.'
MERGE_LINE = notices.line(
    'merge', 'MERGE_HEAD', 'The range above stops before it.',
    'Commit the merge, then run purlin:drift.')
AGE_KNOWN = 'It was %s ago, and drift does not fetch.'
AGE_UNKNOWN = 'None is on record, and drift does not fetch.'
AGE_DO = 'Run git fetch, then purlin:drift.'


def _number_line(name, item, wrong, do, text=None):
    """One number written twice, the line that moves shown by its first
    `notices.WORDS_SHOWN` words where `text` gives it."""
    if text:
        do += RENUMBER_SHOWN % notices.shown(text)
    return notices.line('number_twice', '%s %s' % (name, item), wrong, do,
                        feature=name,
                        rule=item if item.startswith('RULE-') else None)


def merge_in_progress(project_root):
    """True while a merge has stopped and is not committed: git holds
    `MERGE_HEAD` until the commit that finishes it."""
    return bool(_git(project_root, ['rev-parse', '-q', '--verify',
                                    '--end-of-options', 'MERGE_HEAD']))


def default_branch(project_root):
    """The default branch as this checkout knows it, as `origin/main`, or None.

    `origin/HEAD` where git recorded it, else the first of `origin/main` and
    `origin/master` that exists. Nothing is fetched.
    """
    ref = _git(project_root, ['symbolic-ref', '--quiet', '--end-of-options',
                              _REMOTES + 'origin/HEAD'])
    if ref.startswith(_REMOTES):
        return ref[len(_REMOTES):]
    for name in ('origin/main', 'origin/master'):
        if _git(project_root, ['rev-parse', '--verify', '-q',
                               '--end-of-options', _REMOTES + name]):
            return name
    return None


def fetched_age(project_root, ref):
    """Seconds since this checkout last updated `ref`, or None.

    The newest entry of the ref's own log, else the time `FETCH_HEAD` was
    written, else unknown.
    """
    if not ref:
        return None
    # `%gd` under `--date=unix` names the entry's own time, `<ref>@{<secs>}`;
    # `%ct` would name the time of the commit the entry points at.
    entry = _git(project_root, ['reflog', 'show', '-1', '--date=unix',
                                '--format=%gd', '--end-of-options',
                                _REMOTES + ref, '--'])
    when = entry[entry.rfind('{') + 1:-1] if entry.endswith('}') else ''
    if when.isdigit():
        return max(0, int(time.time()) - int(when))
    path = _git(project_root, ['rev-parse', '--git-path', 'FETCH_HEAD'])
    if path:
        try:
            written = os.path.getmtime(os.path.join(project_root, path))
        except OSError:
            return None
        return max(0, int(time.time() - written))
    return None


def _age_words(seconds):
    """`under a minute`, then whole minutes, hours or days, rounded down."""
    if seconds < 60:
        return 'under a minute'
    for size, word in ((86400, 'day'), (3600, 'hour'), (60, 'minute')):
        if seconds >= size:
            return _plural(seconds // size, word)
    return 'under a minute'


def _age_line(ref, age):
    if age is None:
        return notices.line('fetch_age', ref, AGE_UNKNOWN, AGE_DO)
    return notices.line('fetch_age', ref, AGE_KNOWN % _age_words(age), AGE_DO)


def text_of(parsed, item_id):
    """The text `parsed` holds for a rule or proof id, or None."""
    if item_id.startswith('RULE-'):
        return parsed.get('rules', {}).get(item_id)
    proof = parsed.get('proofs', {}).get(item_id)
    return proof['text'] if proof else None


def _written_twice(parsed):
    """The ids `parsed` writes twice, rules first, each in first-written order."""
    doubled = parsed.get('doubled_lines') or {}
    rules = [item for item in parsed.get('doubled_rules') or ()
             if item in doubled]
    proofs = [item for item in parsed.get('doubled_proofs') or ()
              if item in doubled]
    rest = [item for item in doubled if item not in rules + proofs]
    return rules + proofs + sorted(rest, key=lambda item: (
        not item.startswith('RULE-'), _rule_number(item)))


def _next_free(parsed, kind, taken):
    """`max(highest, every number of the kind in the spec) + 1`, past `taken`."""
    highest = parsed.get('highest_rule' if kind == 'RULE' else 'highest_proof')
    ids = parsed.get('rules' if kind == 'RULE' else 'proofs', {})
    numbers = [_rule_number(item) for item in ids]
    numbers += [_rule_number(item) for item in parsed.get('doubled_lines') or {}
                if item.startswith(kind + '-')]
    number = max([highest or 0] + numbers + taken.get(kind, [])) + 1
    taken.setdefault(kind, []).append(number)
    return '%s-%d' % (kind, number)


def _spec_lines(project_root, info):
    """The lines of the spec `info` as the file on disk holds them."""
    path = os.path.join(project_root, *info['spec_path'].split('/'))
    try:
        with open(path, encoding='utf-8') as handle:
            return handle.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return []


def _follows(project_root, ref, info, rule_id, lines):
    """`[{'proof', 'line'}]`: each proof line of `lines` that names
    `rule_id` and is not on `ref`'s copy of the spec, in file order."""
    on_default = set(_lines(_git(project_root, [
        'show', '--end-of-options', '%s:%s' % (ref, info['spec_path'])])))
    found = []
    for number, text in enumerate(lines, 1):
        match = specs_module._PROOF_LINE_RE.match(text.strip())
        if (match and rule_id in specs_module._split_list(match.group(2))
                and text.strip() not in on_default):
            found.append({'proof': match.group(1), 'line': number})
    return found


def numbers_twice(project_root, features, ref, spec_lines=None):
    """One entry per number a spec of this checkout writes twice.

    `features` is `specs.scan_specs`'s answer. The line whose text equals the
    id's text on `ref`, the default branch, keeps the number; the other
    moves to the next free number of its kind. Where neither line is on
    `ref`, `ref` writes the id twice too, or there is no `ref`, the later
    line in the file moves. `case` names which of the four it was, and
    `moves` is the line that moves, `{'line', 'text'}`.

    An entry for a rule carries `follows`, `[{'proof', 'line'}]`: the proof
    lines naming the rule that are not on `ref`'s copy, which follow it to
    its new number; none where there is no `ref`. `spec_lines` gives a
    spec's lines, `{feature: [line, ...]}`, where the caller parsed
    `features` out of them; any other spec's are read out of its file.
    """
    found = []
    for name in sorted(features):
        info = features[name]
        taken = {}
        default = default_spec(project_root, ref, info)
        lines = None
        for item in _written_twice(info):
            written = info['doubled_lines'][item]
            to = _next_free(info, item.split('-')[0], taken)
            entry = {'feature': name, 'id': item, 'to': to, 'text': None,
                     'moves': written[-1]}
            if default is None:
                entry['case'] = 'no_default'
                entry['line'] = _number_line(name, item, NUMBER_NO_DEFAULT,
                                             RENUMBER_UNMERGED % to)
            elif item in (default.get('doubled_lines') or {}):
                entry['case'] = 'on_default'
                entry['text'] = written[-1]['text']
                entry['line'] = _number_line(
                    name, item, NUMBER_ON_DEFAULT % ref, RENUMBER_SECOND % to,
                    entry['text'])
            else:
                kept = text_of(default, item)
                keeper = next((index for index, line in enumerate(written)
                               if kept is not None and line['text'] == kept),
                              None)
                if keeper is None:
                    entry['case'] = 'neither'
                    entry['line'] = _number_line(
                        name, item, NUMBER_NEITHER % ref, RENUMBER_OTHER % to)
                else:
                    other = next(line for index, line in enumerate(written)
                                 if index != keeper)
                    entry['case'] = 'kept'
                    entry['moves'] = other
                    entry['text'] = other['text']
                    entry['line'] = _number_line(
                        name, item, NUMBER_KEPT % ref, RENUMBER_OTHER % to,
                        entry['text'])
            if item.startswith('RULE-'):
                entry['follows'] = []
                if ref:
                    if lines is None:
                        lines = ((spec_lines or {}).get(name)
                                 or _spec_lines(project_root, info))
                    entry['follows'] = _follows(project_root, ref, info, item,
                                                lines)
            found.append(entry)
    return found


def default_spec(project_root, ref, info):
    """The spec `info` as `ref` holds it, parsed; `{}` where `ref` holds no
    such file, and None where there is no `ref`."""
    if not ref:
        return None
    content = _git(project_root, ['show', '--end-of-options',
                                  '%s:%s' % (ref, info['spec_path'])])
    return (specs_module._parse_spec(info['name'], info['spec_path'], content)
            if content else {})


def spec_at(project_root, sha, feature, spec_path, cache):
    """The spec at `spec_path` as the commit `sha` holds it, parsed, or `{}`.
    `cache` keeps each commit's reading for the next comment."""
    key = (sha, spec_path)
    if key not in cache:
        content = _git(project_root, ['show', '--end-of-options',
                                      '%s:%s' % key])
        cache[key] = (specs_module._parse_spec(feature, spec_path, content)
                      if content else {})
    return cache[key]


def _blamed_commit(project_root, path, line, rev=None):
    """The commit that last wrote one line of a file, at `rev` where given,
    or None where the line is not committed. The path follows `--`, so it is
    never read as an option."""
    out = _git(project_root, ['blame', '--porcelain', '-L', '%d,%d' % (line, line)]
               + ([rev] if rev else []) + ['--', path])
    sha = out.split(' ', 1)[0] if out else ''
    return sha if sha and sha.strip('0') else None


def comments_changed(project_root, rng, features, before, after):
    """`wording.stale_comments`' entries the range touches: each test comment
    whose proof's wording changed after its test was last changed, where the
    range changed that proof or that test's file. By file, then line."""
    differs = set()
    for name in set(before) | set(after):
        old = _proof_texts(before.get(name))
        new = _proof_texts(after.get(name))
        differs.update((name, item) for item in new if old.get(item) != new[item])
    marked = markers_module.scan(project_root, tracked_only=True)
    changed = set(_changed_files(project_root, rng, sorted(marked)))
    scanned = {path: listing for path, listing in marked.items()
               if path in changed
               or any(marker.key() in differs for marker in listing.markers)}
    if not scanned:
        return []
    return [entry for entry in wording_module.stale_comments(
                project_root, features, scanned=scanned)
            if entry['file'] in changed
            or (entry['feature'], entry['id']) in differs]


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------

def compute_drift(project_root, since=None, network=True):
    """The whole drift report as a dict: the range and the one view."""
    rng = resolve_range(project_root, since)
    if 'error' in rng:
        return rng

    features = specs_module.scan_specs(project_root)

    spec_paths = _spec_paths(_changed_files(project_root, rng, [_SPECS_DIR]))
    before = _spec_map(project_root, rng['from'], spec_paths)
    after = _spec_map(project_root, rng['to'], spec_paths)
    view, lines = _rules_view(rng, before, after)
    proofs_view, proof_lines = _proofs_view(before, after)
    view.update(proofs_view)
    lines += proof_lines

    ref = default_branch(project_root)
    branch = ({'ref': ref, 'age_seconds': fetched_age(project_root, ref)}
              if ref else None)
    twice = numbers_twice(project_root, features, ref)
    comments = comments_changed(project_root, rng, features, before, after)
    for entry in twice:
        lines.append(entry['line'])
        lines += [PROOF_WILL_NAME % (entry['feature'], follow['proof'],
                                     entry['to'])
                  for follow in entry.get('follows') or ()]
    lines += [entry['text'] for entry in comments]
    if twice and ref:
        lines.append(_age_line(ref, branch['age_seconds']))

    anchors = pin_report(project_root, features, network=network)
    lines += [pin_line(row) for row in anchors]

    merging = merge_in_progress(project_root)
    view.update({'anchors_behind': anchors, 'comments_changed': comments,
                 'default_branch': branch, 'numbers_twice': twice,
                 'merge_in_progress': merging,
                 'lines': ([rng['line']] + ([MERGE_LINE] if merging else [])
                           + lines)})
    since_out = {key: rng[key] for key in ('from', 'to', 'commits', 'action',
                                           'when', 'line')}
    return {'since': since_out, 'view': {key: view[key] for key in VIEW_KEYS}}


def drift(project_root, since=None):
    """The drift report as JSON text.

    A settings file that cannot be read stops it before anything is read:
    the answer is the sentence saying so, in place of the JSON.
    """
    problem = config_problem(project_root)
    if problem:
        return problem
    return json.dumps(compute_drift(project_root, since), separators=(',', ':'))
