#!/usr/bin/env python3
"""Extraction tool for the What's Different? feature.

Produces structured JSON from git range queries comparing local main
vs a remote collab branch. Input: session name. Output: JSON to stdout.

Categorizes changed files into specs, code, tests, companion files,
purlin config, and submodule changes. Parses status commits for
lifecycle transitions.
"""
import json
import os
import re
import subprocess
import sys

# Project root detection (Section 2.11)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
if _env_root and os.path.isdir(_env_root):
    PROJECT_ROOT = _env_root
else:
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
    for depth in ('../../../', '../../'):
        candidate = os.path.abspath(os.path.join(SCRIPT_DIR, depth))
        if os.path.exists(os.path.join(candidate, '.purlin')):
            PROJECT_ROOT = candidate
            break

# Config loading with resilience (Section 2.13)
CONFIG_PATH = os.path.join(PROJECT_ROOT, '.purlin', 'config.json')
try:
    with open(CONFIG_PATH, 'r') as _f:
        _cfg = json.load(_f)
except (json.JSONDecodeError, IOError, OSError):
    _cfg = {}

REMOTE = _cfg.get('remote_collab', {}).get('remote', 'origin')


def _run_git(args, cwd=None):
    """Run a git command and return stdout. Returns empty string on failure."""
    try:
        result = subprocess.run(
            ['git'] + args,
            capture_output=True, text=True, check=True,
            cwd=cwd or PROJECT_ROOT, timeout=30)
        return result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ''


def compute_sync_state(session_name):
    """Determine SAME/AHEAD/BEHIND/DIVERGED between local main and remote collab branch."""
    ref = f'{REMOTE}/collab/{session_name}'

    # Commits local main has that remote does not
    ahead_lines = _run_git(
        ['log', f'{ref}..main', '--oneline']).strip().splitlines()
    ahead_lines = [l for l in ahead_lines if l.strip()]

    # Commits remote has that local main does not
    behind_lines = _run_git(
        ['log', f'main..{ref}', '--oneline']).strip().splitlines()
    behind_lines = [l for l in behind_lines if l.strip()]

    ahead = len(ahead_lines)
    behind = len(behind_lines)

    if ahead == 0 and behind == 0:
        state = 'SAME'
    elif ahead > 0 and behind == 0:
        state = 'AHEAD'
    elif ahead == 0 and behind > 0:
        state = 'BEHIND'
    else:
        state = 'DIVERGED'

    return {
        'sync_state': state,
        'commits_ahead': ahead,
        'commits_behind': behind,
    }


# --- File categorization ---

# Patterns for lifecycle status commits
_STATUS_RE = re.compile(
    r'\[(Complete|Ready for Verification|TODO)\s+features/(\S+\.md)\]')

# Patterns for scope tags in commit messages
_SCOPE_RE = re.compile(r'\[Scope:\s*(\S+)\]')


def categorize_file(path):
    """Classify a file path into a category.

    Returns one of: 'feature_spec', 'anchor_node', 'policy_node',
    'companion', 'visual_spec', 'test', 'code', 'purlin_config',
    'submodule'.
    """
    # Purlin submodule changes
    if path.startswith('purlin/') or path == '.gitmodules':
        return 'submodule'

    # Purlin config and overrides
    if path.startswith('.purlin/'):
        return 'purlin_config'

    # Feature specs and related
    if path.startswith('features/'):
        basename = os.path.basename(path)
        if basename.endswith('.impl.md'):
            return 'companion'
        if path.startswith('features/design/'):
            return 'visual_spec'
        if basename.startswith('arch_'):
            return 'anchor_node'
        if basename.startswith('design_'):
            return 'anchor_node'
        if basename.startswith('policy_'):
            return 'policy_node'
        if basename.endswith('.md'):
            return 'feature_spec'
        return 'visual_spec'

    # Tests
    if path.startswith('tests/') or '/test_' in path or path.endswith('_test.py'):
        return 'test'

    # Everything else is code
    return 'code'


def _get_changed_files(range_spec):
    """Get list of changed files in a git range.

    Returns list of dicts: [{path, status}] where status is A/M/D.
    """
    output = _run_git(['diff', '--name-status', range_spec])
    files = []
    for line in output.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split('\t', 1)
        if len(parts) == 2:
            status_char = parts[0].strip()[0] if parts[0].strip() else 'M'
            files.append({'path': parts[1].strip(), 'status': status_char})
    return files


def _get_commits(range_spec):
    """Get list of commits in a git range.

    Returns list of dicts: [{hash, subject}].
    """
    output = _run_git(
        ['log', range_spec, '--format=%H|%s'])
    commits = []
    for line in output.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split('|', 1)
        if len(parts) == 2:
            commits.append({
                'hash': parts[0].strip(),
                'subject': parts[1].strip(),
            })
    return commits


def _parse_lifecycle_transitions(commits):
    """Extract lifecycle transitions from commit messages.

    Returns list of dicts: [{feature, from_state, to_state}].
    """
    transitions = []
    for commit in commits:
        match = _STATUS_RE.search(commit['subject'])
        if match:
            tag = match.group(1)
            feature = match.group(2)
            if tag == 'Complete':
                transitions.append({
                    'feature': feature,
                    'from_state': 'TESTING',
                    'to_state': 'COMPLETE',
                })
            elif tag == 'Ready for Verification':
                transitions.append({
                    'feature': feature,
                    'from_state': 'TODO',
                    'to_state': 'TESTING',
                })
            elif tag == 'TODO':
                transitions.append({
                    'feature': feature,
                    'from_state': None,
                    'to_state': 'TODO',
                })
    return transitions


def _parse_discoveries(commits, changed_files):
    """Detect new discovery entries from changed feature files.

    Looks for BUG, DISCOVERY, INTENT_DRIFT, SPEC_DISPUTE patterns
    in commit subjects or in diff content of feature files.
    Returns count of discovery-type entries found.
    """
    count = 0
    discovery_pattern = re.compile(
        r'\[(BUG|DISCOVERY|INTENT_DRIFT|SPEC_DISPUTE)\]', re.IGNORECASE)
    for commit in commits:
        if discovery_pattern.search(commit['subject']):
            count += 1
    return count


def _categorize_changes(changed_files):
    """Group changed files by category.

    Returns dict keyed by category name, each value is a list of file dicts.
    """
    categories = {
        'feature_specs': [],
        'anchor_nodes': [],
        'policy_nodes': [],
        'companion_files': [],
        'visual_specs': [],
        'tests': [],
        'code': [],
        'purlin_config': [],
        'submodule': [],
    }
    category_map = {
        'feature_spec': 'feature_specs',
        'anchor_node': 'anchor_nodes',
        'policy_node': 'policy_nodes',
        'companion': 'companion_files',
        'visual_spec': 'visual_specs',
        'test': 'tests',
        'code': 'code',
        'purlin_config': 'purlin_config',
        'submodule': 'submodule',
    }
    for f in changed_files:
        cat = categorize_file(f['path'])
        key = category_map.get(cat, 'code')
        categories[key].append(f)
    return categories


def extract_direction(range_spec):
    """Extract structured data for one direction (local or collab).

    Args:
        range_spec: git range like 'origin/collab/session..main' or
                    'main..origin/collab/session'

    Returns dict with: commits, changed_files, categories, transitions, discovery_count.
    """
    commits = _get_commits(range_spec)
    changed_files = _get_changed_files(range_spec)
    categories = _categorize_changes(changed_files)
    transitions = _parse_lifecycle_transitions(commits)
    discovery_count = _parse_discoveries(commits, changed_files)

    return {
        'commits': commits,
        'changed_files': changed_files,
        'categories': categories,
        'transitions': transitions,
        'discovery_count': discovery_count,
    }


def extract(session_name):
    """Main extraction function.

    Returns the full structured JSON for both directions.
    """
    ref = f'{REMOTE}/collab/{session_name}'
    sync = compute_sync_state(session_name)
    state = sync['sync_state']

    result = {
        'session': session_name,
        'sync_state': state,
        'commits_ahead': sync['commits_ahead'],
        'commits_behind': sync['commits_behind'],
        'local_changes': [],
        'collab_changes': [],
    }

    if state == 'SAME':
        return result

    # Local changes (what main has that collab doesn't)
    if state in ('AHEAD', 'DIVERGED'):
        local = extract_direction(f'{ref}..main')
        result['local_changes'] = local

    # Collab changes (what collab has that main doesn't)
    if state in ('BEHIND', 'DIVERGED'):
        collab = extract_direction(f'main..{ref}')
        result['collab_changes'] = collab

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_whats_different.py <session_name>",
              file=sys.stderr)
        sys.exit(1)

    session_name = sys.argv[1]
    data = extract(session_name)
    json.dump(data, sys.stdout, indent=2)
    print()  # trailing newline


if __name__ == '__main__':
    main()
