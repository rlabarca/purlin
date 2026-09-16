"""What changed since the evidence was last written, and what it means per role.

Drift answers one question: since the evidence was last written, what moved?
It reads git for the commits and the changed files, classifies each file
against the specs' `> Scope:` lines, and adds what the payload already knows
about the cells, the signatures and the pins.

Four role views come out of the same data, because four people ask different
questions of it:

`pm`      acceptance criteria with no rule, pm-owned rules that changed,
          rules an engineer added, pins behind their source
`design`  design files that changed, design-owned rules whose signature went
          stale
`qa`      signatures gone stale, how long the review list is, how many rules
          need a person, rules no proof of which names a rejection or a
          boundary
`eng`     files touched and the rules they affect, rules with no test, rules
          with no risk or origin tag, pins behind, rules whose code changed
"""

import json
import os
import re
import subprocess
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import payload as payload_module, specs as specs_module, states

ROLES = ('pm', 'design', 'qa', 'eng')

_NO_IMPACT_PATTERNS = (
    'docs/', 'assets/', 'templates/', 'references/', '.gitignore', 'LICENSE',
    'CLAUDE.md', 'README.md', 'RELEASE_NOTES.md', '.mcp.json', 'settings.json',
)

_TEST_PATTERNS = ('test_', '_test.', '.test.', 'tests/', 'dev/test_')

# Directories holding behavioural definitions even when the files are .md.
_BEHAVIORAL_MD_PREFIXES = ('skills/', 'agents/', '.claude/agents/')

# Where designs live. A change under one of these stales the design rules that
# the anchor pinning it covers.
_DESIGN_PREFIXES = ('designs/',)

# How much of a rule description the report carries. A description is read to
# judge whether a rule went stale, and the opening clause says it.
_RULE_DESC_LIMIT = 200

_RULE_RE = re.compile(r'^-\s+(RULE-\d+):')

# A `since` value reaches drift from a model-authored tool call, so it is
# untrusted input: a commit count or an ISO date, and nothing else reaches git.
_SINCE_DAYS_RE = re.compile(r'^[0-9]+$')
_SINCE_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _cap(text, limit=_RULE_DESC_LIMIT):
    if len(text) <= limit:
        return text
    head = text[:limit]
    if not text[limit].isspace() and ' ' in head:
        head = head.rsplit(' ', 1)[0]
    return head.rstrip() + ' ...'


def _git(project_root, args, timeout=15):
    try:
        result = subprocess.run(
            ['git'] + args, capture_output=True, text=True,
            cwd=project_root, timeout=timeout)
    except (subprocess.SubprocessError, OSError):
        return ''
    return result.stdout.strip() if result.returncode == 0 else ''


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
# The anchor a drift report measures from
# ---------------------------------------------------------------------------

def resolve_since(project_root, since_arg=None):
    """`(ref, description)`, or `(None, json_text)` when there is nothing to measure.

    Without an argument the anchor is the most recent record CI or a
    developer committed, then the most recent tag, then the commit that added
    `.purlin/config.json`. A project with no record and a long history gets a
    recommendation rather than a diff of everything.
    """
    if since_arg is not None and str(since_arg).strip() != '':
        since_arg = str(since_arg).strip()
        if not (_SINCE_DAYS_RE.match(since_arg)
                or _SINCE_DATE_RE.match(since_arg)):
            return None, json.dumps({
                'error': 'rejected since',
                'reason': ('since must be a number of commits (digits only) or '
                           'a YYYY-MM-DD date; refusing to pass %r to git'
                           % since_arg),
                'since': since_arg,
            })
        if _SINCE_DAYS_RE.match(since_arg):
            count = int(since_arg)
            return 'HEAD~%d' % count, 'last %d commits' % count
        sha = _git(project_root, ['log', '--reverse', '--since=%s' % since_arg,
                                  '--format=%H', '-1'])
        if sha:
            return sha + '^', 'since %s' % since_arg
        return 'HEAD~20', 'since %s (no commits found, using last 20)' % since_arg

    record_line = _git(project_root, [
        'log', '-1', '--format=%H %ar', '--', '.purlin/records'])
    if record_line:
        parts = record_line.split(' ', 1)
        return parts[0], 'last record (%s)' % (parts[1] if len(parts) > 1 else '')

    tag = _git(project_root, ['describe', '--tags', '--abbrev=0'])
    if tag:
        when = _git(project_root, ['log', '-1', '--format=%ar',
                                   '--end-of-options', tag])
        return tag, '%s (%s)' % (tag, when)

    init_sha = _git(project_root, ['log', '--diff-filter=A', '--format=%H',
                                   '--follow', '--', '.purlin/config.json'])
    if init_sha:
        init_sha = init_sha.splitlines()[-1].strip()
        count_text = _git(project_root, ['rev-list', '--count',
                                         '--end-of-options',
                                         '%s..HEAD' % init_sha])
        count = int(count_text) if count_text.isdigit() else 0
        if count < 30:
            return init_sha, 'since purlin:init (%d commits)' % count
        return None, json.dumps({
            'recommendation': 'spec-from-code',
            'reason': ('No record and %d commits since Purlin was set up. '
                       'Drift measures between runs; for the first specs of '
                       'an existing codebase run purlin:spec-from-code.'
                       % count),
            'commits_since_init': count,
        })

    count_text = _git(project_root, ['rev-list', '--count', '--end-of-options',
                                     'HEAD'])
    count = int(count_text) if count_text.isdigit() else 0
    if count < 30:
        # `count` counts HEAD itself, so `HEAD~count` names a commit that is
        # not there. The window is one short of the whole history.
        window = max(min(count - 1, 20), 0)
        return 'HEAD~%d' % window, ('last %d commits (no record or tag found)'
                                    % window)
    return None, json.dumps({
        'recommendation': 'spec-from-code',
        'reason': ('No record and %d commits exist. Drift measures between '
                   'runs; for the first specs of an existing codebase run '
                   'purlin:spec-from-code.' % count),
        'commits_since_init': count,
    })


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------

def _diff_stats(project_root, since_ref):
    """`{path: '+N -M'}` from one numstat over the whole range."""
    stats = {}
    output = _git(project_root, ['diff', '--numstat', '--end-of-options',
                                 since_ref + '..HEAD', '--'], timeout=30)
    for line in output.splitlines():
        parts = line.split('\t')
        if len(parts) >= 3 and parts[2]:
            stats[parts[2]] = '+%s -%s' % (parts[0], parts[1])
    return stats


def _spec_rule_changes(project_root, since_ref, spec_paths):
    """Which rule ids each changed spec gained and lost."""
    changes = []
    for spec_path in spec_paths:
        diff = _git(project_root, ['diff', '--end-of-options',
                                   since_ref + '..HEAD', '--', spec_path])
        added, removed = [], []
        for line in diff.splitlines():
            if line.startswith('+++') or line.startswith('---'):
                continue
            if not line or line[0] not in '+-':
                continue
            m = _RULE_RE.search(line[1:].strip())
            if not m:
                continue
            (added if line[0] == '+' else removed).append(m.group(1))
        changes.append({
            'spec': os.path.splitext(os.path.basename(spec_path))[0],
            'new_rules': added,
            'removed_rules': removed,
        })
    return changes


def _classify(project_root, filepath, scope_to_specs, features, stats):
    if filepath.startswith('specs/') and filepath.endswith('.md'):
        return {'path': filepath, 'category': 'CHANGED_SPECS',
                'spec': os.path.splitext(os.path.basename(filepath))[0],
                'diff_stat': stats.get(filepath, '')}
    if any(prefix in filepath for prefix in _DESIGN_PREFIXES):
        return {'path': filepath, 'category': 'CHANGED_DESIGNS', 'spec': None,
                'diff_stat': stats.get(filepath, '')}
    if any(pattern in filepath for pattern in _TEST_PATTERNS):
        spec = None
        for name in features:
            if name.replace('-', '_') in filepath or name in filepath:
                spec = name
                break
        return {'path': filepath, 'category': 'TESTS_CHANGED', 'spec': spec,
                'diff_stat': stats.get(filepath, '')}
    matched = scope_to_specs.get(filepath, [])
    if not matched:
        for scope_path, names in scope_to_specs.items():
            if scope_path.endswith('/') and filepath.startswith(scope_path):
                matched = names
                break
    if matched:
        return {'path': filepath, 'category': 'CHANGED_BEHAVIOR',
                'spec': matched[0], 'diff_stat': stats.get(filepath, '')}
    behavioral_md = any(filepath.startswith(d) for d in _BEHAVIORAL_MD_PREFIXES)
    no_impact = any(filepath.startswith(p) or filepath == p
                    or filepath.endswith(p)
                    for p in _NO_IMPACT_PATTERNS) and not behavioral_md
    generic_md = filepath.endswith('.md') and not behavioral_md
    if no_impact or generic_md:
        return {'path': filepath, 'category': 'NO_IMPACT', 'spec': None,
                'diff_stat': stats.get(filepath, '')}
    return {'path': filepath, 'category': 'NEW_BEHAVIOR', 'spec': None,
            'diff_stat': stats.get(filepath, '')}


def compute_drift(project_root, since=None, network=True, data=None):
    """The whole drift report as a dict."""
    since_ref, since_desc = resolve_since(project_root, since)
    if since_ref is None:
        return json.loads(since_desc)

    commits = [line.strip() for line in
               _git(project_root, ['log', '--oneline', '--end-of-options',
                                   since_ref + '..HEAD', '--']).splitlines()
               if line.strip()]
    changed_files = [line.strip() for line in
                     _git(project_root, ['diff', '--name-only',
                                         '--end-of-options',
                                         since_ref + '..HEAD', '--']).splitlines()
                     if line.strip()]
    changed_files = [f for f in changed_files
                     if os.path.exists(os.path.join(project_root, f))]

    data = data if data is not None else payload_module.build_payload(
        project_root, generated_by='drift')
    features = {f['name']: f for f in data.get('features', [])}

    scope_to_specs = {}
    for name, feature in features.items():
        for scope_file in feature.get('scope', []):
            scope_to_specs.setdefault(scope_file, []).append(name)

    stats = _diff_stats(project_root, since_ref)
    file_entries = [_classify(project_root, path, scope_to_specs, features, stats)
                    for path in changed_files]
    spec_paths = [e['path'] for e in file_entries
                  if e['category'] == 'CHANGED_SPECS']

    broken_scopes = []
    for name, feature in sorted(features.items()):
        missing = []
        for scope_path in feature.get('scope', []):
            full = os.path.join(project_root, scope_path)
            exists = (os.path.isdir(full.rstrip('/')) if scope_path.endswith('/')
                      else os.path.exists(full))
            if not exists:
                missing.append(scope_path)
        if missing:
            broken_scopes.append({'spec': name, 'missing_paths': missing})

    raw_features = specs_module.scan_specs(project_root)
    pins = pin_report(project_root, raw_features, network=network)

    rule_details = {}
    touched = sorted({e['spec'] for e in file_entries
                      if e['category'] == 'CHANGED_BEHAVIOR' and e.get('spec')})
    for name in touched:
        feature = features.get(name)
        if not feature or not feature.get('rules'):
            continue
        rule_details[name] = {
            'spec_path': feature.get('spec_path', ''),
            'changed_files': [e['path'] for e in file_entries
                              if e.get('spec') == name
                              and e['category'] == 'CHANGED_BEHAVIOR'],
            'total_rules': len(feature['rules']),
            'met': feature['rollup']['met'],
            'unproved': [r['id'] for r in feature['rules']
                         if r['spec'] == states.DRAFTED],
            'rules': [{'rule_id': r['id'], 'description': _cap(r['text']),
                       'bucket': r['bucket'], 'risk': r['risk'],
                       'origin': r['origin']}
                      for r in feature['rules'] if r['label'] == 'own'],
        }

    report = {
        'since': since_desc,
        'commits': commits,
        'files': file_entries,
        'spec_changes': _spec_rule_changes(project_root, since_ref, spec_paths),
        'broken_scopes': broken_scopes,
        'pins': pins,
        'rule_details': rule_details,
        'summary': data.get('summary', {}),
        'review_list': data.get('review_list', []),
    }
    report['roles'] = _role_views(report, data, file_entries)
    return report


def _role_views(report, data, file_entries):
    """The four role views, each a list of lines a skill turns into prose."""
    rules = [(feature, rule) for feature in data.get('features', [])
             for rule in feature.get('rules', []) if rule['label'] == 'own']

    changed_specs = {e['spec'] for e in file_entries
                     if e['category'] == 'CHANGED_SPECS' and e.get('spec')}
    design_changed = [e['path'] for e in file_entries
                      if e['category'] == 'CHANGED_DESIGNS']
    pins_behind = [p for p in report['pins'] if p['status'] != 'current']

    pm = {
        'criteria_without_rules': sorted(
            {rule['criterion'] for _f, rule in rules if rule.get('criterion')}
            - {rule['criterion'] for _f, rule in rules
               if rule.get('criterion') and rule['proofs']}),
        'pm_rules_changed': ['%s/%s' % (feature['name'], rule['id'])
                             for feature, rule in rules
                             if rule['origin'] == 'pm'
                             and feature['name'] in changed_specs],
        'engineer_added_rules': ['%s/%s' % (feature['name'], rule['id'])
                                 for feature, rule in rules
                                 if rule['origin'] == 'eng'
                                 and feature['name'] in changed_specs],
        'pins_behind': pins_behind,
    }
    design = {
        'designs_changed': design_changed,
        'design_rules_stale': [
            '%s/%s' % (feature['name'], rule['id'])
            for feature, rule in rules
            if rule['origin'] == 'design'
            and _cell_word(rule, 'signed') == 'stale'],
    }
    qa = {
        'signatures_stale': ['%s/%s' % (feature['name'], rule['id'])
                             for feature, rule in rules
                             if rule['flags'].get('stale')],
        'review_list_size': len(data.get('review_list', [])),
        'needs_person': ['%s/%s' % (feature['name'], rule['id'])
                         for feature, rule in rules
                         if rule['flags'].get('needs_person')],
        'rules_without_a_negative_case': [
            '%s/%s' % (feature['name'], rule['id'])
            for feature, rule in rules
            if any('happy_path_only' in (p.get('findings') or [])
                   for p in rule['proofs'])],
    }
    eng = {
        'files_touched': [e['path'] for e in file_entries
                          if e['category'] in ('CHANGED_BEHAVIOR',
                                               'NEW_BEHAVIOR')],
        'rules_affected': sorted(report['rule_details']),
        'tests_missing': ['%s/%s' % (feature['name'], rule['id'])
                          for feature, rule in rules
                          if not any(p['tests'] for p in rule['proofs'])],
        'tags_missing': ['%s/%s' % (feature['name'], rule['id'])
                         for feature, rule in rules
                         if rule['risk'] == specs_module.DEFAULT_RISK
                         and rule['origin'] == specs_module.DEFAULT_ORIGIN],
        'pins_behind': pins_behind,
        'code_changed': ['%s/%s' % (feature['name'], rule['id'])
                         for feature, rule in rules
                         if rule['flags'].get('code_changed')],
    }
    return {'pm': pm, 'design': design, 'qa': qa, 'eng': eng}


def _cell_word(rule, name):
    """The word one cell of a rule reads, or None where that cell is absent."""
    return ((rule.get('cells') or {}).get(name) or {}).get('word')


def drift(project_root, since=None, role=None):
    """The drift report as JSON text. A role narrows it to that role's view."""
    result = compute_drift(project_root, since)
    if role and role in ROLES and 'roles' in result:
        result = {'since': result['since'], 'role': role,
                  'view': result['roles'][role],
                  'commits': result['commits']}
    return json.dumps(result, separators=(',', ':'))
