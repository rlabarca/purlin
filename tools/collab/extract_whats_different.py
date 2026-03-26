#!/usr/bin/env python3
"""Extraction tool for the What's Different? feature.

Produces structured JSON from git range queries comparing HEAD vs
origin/<branch>. Input: branch name. Output: JSON to stdout.

Categorizes changed files into specs, code, tests, companion files,
purlin config, and submodule changes. Parses status commits for
lifecycle transitions.
"""
import glob
import json
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../')))
from tools.bootstrap import detect_project_root, load_config

PROJECT_ROOT = detect_project_root(SCRIPT_DIR)
_cfg = load_config(PROJECT_ROOT)

REMOTE = _cfg.get('branch_collab', _cfg.get('remote_collab', {})).get('remote', 'origin')


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


def compute_sync_state(branch_name):
    """Determine SAME/AHEAD/BEHIND/DIVERGED between HEAD and remote branch."""
    # Try collab/ prefix first (convention), then bare name
    collab_ref = f'{REMOTE}/collab/{branch_name}'
    bare_ref = f'{REMOTE}/{branch_name}'
    # Use collab ref if it exists, otherwise bare
    check = _run_git(['rev-parse', '--verify', collab_ref])
    remote_ref = collab_ref if check.strip() else bare_ref
    local_ref = 'HEAD'

    # Commits HEAD has that remote does not
    ahead_lines = _run_git(
        ['log', f'{remote_ref}..{local_ref}', '--oneline']).strip().splitlines()
    ahead_lines = [l for l in ahead_lines if l.strip()]

    # Commits remote has that HEAD does not
    behind_lines = _run_git(
        ['log', f'{local_ref}..{remote_ref}', '--oneline']).strip().splitlines()
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

# Purlin infrastructure launcher scripts (bootstrap only)
_PURLIN_LAUNCHER_RE = re.compile(
    r'^pl-run-.*(?:architect|builder|qa|pm)\.sh$')

# Patterns for scope tags in commit messages
_SCOPE_RE = re.compile(r'\[Scope:\s*(\S+)\]')

# Commit scope pattern: mode(scope1,scope2): message
_COMMIT_SCOPE_RE = re.compile(r'^\w+\(([^)]+)\):')


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
        if basename.endswith('.impl.md') or basename.endswith('.discoveries.md'):
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

    # Purlin infrastructure files (launchers and command definitions)
    basename = os.path.basename(path)
    if _PURLIN_LAUNCHER_RE.match(basename):
        return 'purlin_config'
    if path.startswith('.claude/commands/pl-'):
        return 'purlin_config'

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


# --- Decision extraction (Section 2.5) ---

# Categories from Implementation Notes (companion files)
_IMPL_DECISION_RE = re.compile(
    r'\[(INFEASIBLE|DEVIATION|DISCOVERY)\]\s*(.*?)(?:\(Severity:|\s*$)',
    re.IGNORECASE)

# Categories from User Testing Discoveries (feature files)
_UT_DECISION_RE = re.compile(
    r'\[(BUG|INTENT_DRIFT|SPEC_DISPUTE|DISCOVERY)\]\s*(.*)',
    re.IGNORECASE)

# Routing rules per spec Section 2.5
_DECISION_ROUTING = {
    'INFEASIBLE': 'pm',
    'DEVIATION': 'pm',
    'INTENT_DRIFT': 'pm',
    'SPEC_DISPUTE': 'pm',
}
# DISCOVERY routing depends on source; BUG defaults to engineer


_DIFF_BATCH_SIZE = 50  # Max files per git diff call to avoid ARG_MAX


def _batched_diff(range_spec, file_list):
    """Run git diff for a list of files in batches of _DIFF_BATCH_SIZE.

    Returns a dict mapping file paths to their diff output.
    Skips binary files gracefully.
    """
    if not file_list:
        return {}

    result = {}
    for i in range(0, len(file_list), _DIFF_BATCH_SIZE):
        batch = file_list[i:i + _DIFF_BATCH_SIZE]
        diff_output = _run_git(
            ['diff', range_spec, '-U0', '--'] + batch)
        # Split batched output by file using the diff header pattern
        current_file = None
        current_lines = []
        for line in diff_output.splitlines():
            if line.startswith('diff --git'):
                # Save previous file
                if current_file is not None:
                    result[current_file] = '\n'.join(current_lines)
                # Extract file path from 'diff --git a/path b/path'
                parts = line.split(' b/', 1)
                current_file = parts[1] if len(parts) == 2 else None
                current_lines = [line]
            elif line.startswith('Binary files'):
                # Skip binary files
                current_file = None
                current_lines = []
            elif current_file is not None:
                current_lines.append(line)
        # Save last file
        if current_file is not None:
            result[current_file] = '\n'.join(current_lines)
    return result


def _extract_decisions_from_diff(range_spec, changed_files):
    """Extract structured decision entries from diff content.

    Scans added lines in the diff for decision tags in companion files
    (Implementation Notes) and feature files (User Testing Discoveries).
    Uses batched git diff calls (one per category) instead of per-file calls.

    Returns list of dicts: [{category, feature, summary, role}].
    """
    decisions = []
    action_required_re = re.compile(
        r'Action Required:\s*PM', re.IGNORECASE)

    # Identify relevant files
    impl_files = [f['path'] for f in changed_files
                  if f['path'].endswith('.impl.md')]
    feature_files = [f['path'] for f in changed_files
                     if f['path'].startswith('features/')
                     and f['path'].endswith('.md')
                     and not f['path'].endswith('.impl.md')]

    # Batched diff for companion files
    impl_diffs = _batched_diff(range_spec, impl_files)
    for fpath, diff_output in impl_diffs.items():
        feature_stem = os.path.basename(fpath).replace('.impl.md', '.md')
        for line in diff_output.splitlines():
            if not line.startswith('+') or line.startswith('+++'):
                continue
            match = _IMPL_DECISION_RE.search(line)
            if match:
                category = match.group(1).upper()
                summary = match.group(2).strip().rstrip('.')
                if not summary:
                    summary = f'{category} entry in {feature_stem}'
                decisions.append({
                    'category': f'[{category}]',
                    'feature': feature_stem,
                    'summary': summary,
                    'role': _DECISION_ROUTING.get(category, 'architect'),
                })

    # Batched diff for feature files
    feature_diffs = _batched_diff(range_spec, feature_files)
    for fpath, diff_output in feature_diffs.items():
        feature_name = os.path.basename(fpath)
        for line in diff_output.splitlines():
            if not line.startswith('+') or line.startswith('+++'):
                continue
            match = _UT_DECISION_RE.search(line)
            if match:
                category = match.group(1).upper()
                summary = match.group(2).strip().rstrip('.')
                if not summary:
                    summary = f'{category} entry in {feature_name}'
                if category == 'BUG':
                    role = 'engineer'
                elif category == 'DISCOVERY':
                    role = 'pm'
                else:
                    role = _DECISION_ROUTING.get(category, 'pm')
                decisions.append({
                    'category': f'[{category}]',
                    'feature': feature_name,
                    'summary': summary,
                    'role': role,
                })
            # Check for Action Required: PM override on BUG entries
            if (decisions and decisions[-1]['category'] == '[BUG]'
                    and action_required_re.search(line)):
                decisions[-1]['role'] = 'pm'

    return decisions


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


def _infer_feature_stems(commits, changed_files):
    """Infer which features were touched by code changes.

    Uses two heuristics per spec §2.7.1:
    1. Commit scope parsing: mode(scope): message
    2. Test directory mapping: tests/<stem>/

    Returns dict mapping feature_stem -> {code_files, inferred_via}.
    """
    features = {}  # stem -> {'code_files': set, 'inferred_via': str}

    # Heuristic 1: commit scope parsing
    for commit in commits:
        match = _COMMIT_SCOPE_RE.match(commit['subject'])
        if match:
            scopes = [s.strip() for s in match.group(1).split(',')]
            for scope in scopes:
                if scope not in features:
                    features[scope] = {
                        'code_files': set(), 'inferred_via': 'commit_scope'}

    # Heuristic 2: test directory mapping
    for f in changed_files:
        path = f['path']
        if path.startswith('tests/'):
            parts = path.split('/', 2)
            if len(parts) >= 2:
                stem = parts[1]
                if stem not in features:
                    features[stem] = {
                        'code_files': set(),
                        'inferred_via': 'test_directory'}

    # Count code files per feature from commit scopes
    code_files = [f for f in changed_files
                  if categorize_file(f['path']) in ('code', 'test')]
    for stem in features:
        for f in code_files:
            features[stem]['code_files'].add(f['path'])

    return features


def _check_companion_staleness(inferred_features, changed_companions):
    """Cross-reference code changes against companion file updates.

    Per spec §2.7.2: flag features where code changed, companion exists
    on disk, but companion was NOT updated in the range.

    Returns list of dicts for the companion_staleness field.
    """
    # Build set of companion stems that were updated in this range
    updated_companions = set()
    for f in changed_companions:
        basename = os.path.basename(f['path'])
        if basename.endswith('.impl.md'):
            updated_companions.add(basename.replace('.impl.md', ''))

    # Check each inferred feature
    staleness = []
    features_dir = os.path.join(PROJECT_ROOT, 'features')
    for stem, info in inferred_features.items():
        companion_path = os.path.join(features_dir, f'{stem}.impl.md')
        if not os.path.isfile(companion_path):
            continue
        if stem in updated_companions:
            continue
        code_count = len(info['code_files'])
        if code_count == 0:
            continue
        staleness.append({
            'feature': f'{stem}.md',
            'companion': f'{stem}.impl.md',
            'code_files_changed': code_count,
            'inferred_via': info['inferred_via'],
        })

    return staleness


def extract_direction(range_spec):
    """Extract structured data for one direction (local or collab).

    Args:
        range_spec: git range like 'origin/branch..HEAD' or
                    'HEAD..origin/branch'

    Returns dict with: commits, changed_files, categories, transitions,
    discovery_count, decisions.
    """
    commits = _get_commits(range_spec)
    changed_files = _get_changed_files(range_spec)
    categories = _categorize_changes(changed_files)
    transitions = _parse_lifecycle_transitions(commits)
    discovery_count = _parse_discoveries(commits, changed_files)
    decisions = _extract_decisions_from_diff(range_spec, changed_files)
    inferred_features = _infer_feature_stems(commits, changed_files)
    companion_staleness = _check_companion_staleness(
        inferred_features, categories.get('companion_files', []))

    return {
        'commits': commits,
        'changed_files': changed_files,
        'categories': categories,
        'transitions': transitions,
        'discovery_count': discovery_count,
        'decisions': decisions,
        'companion_staleness': companion_staleness,
    }


def extract(branch_name):
    """Main extraction function.

    Returns the full structured JSON for both directions.
    """
    remote_ref = f'{REMOTE}/{branch_name}'
    local_ref = 'HEAD'
    sync = compute_sync_state(branch_name)
    state = sync['sync_state']

    result = {
        'branch': branch_name,
        'sync_state': state,
        'commits_ahead': sync['commits_ahead'],
        'commits_behind': sync['commits_behind'],
        'local_changes': [],
        'collab_changes': [],
    }

    if state == 'SAME':
        return result

    # Local changes (what HEAD has that remote doesn't)
    if state in ('AHEAD', 'DIVERGED'):
        local = extract_direction(f'{remote_ref}..{local_ref}')
        result['local_changes'] = local

    # Collab changes (what remote has that HEAD doesn't)
    if state in ('BEHIND', 'DIVERGED'):
        collab = extract_direction(f'{local_ref}..{remote_ref}')
        result['collab_changes'] = collab

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_whats_different.py <branch_name>",
              file=sys.stderr)
        sys.exit(1)

    branch_name = sys.argv[1]
    data = extract(branch_name)
    json.dump(data, sys.stdout, indent=2)
    print()  # trailing newline


if __name__ == '__main__':
    main()
