#!/usr/bin/env python3
"""Smoke tier management for Purlin QA verification.

Manages the Test Priority Tiers table in override files, suggests features
for smoke promotion, creates simplified smoke regression files, and provides
the smoke gate ordering logic used by purlin:verify.
"""

import json
import os
import re
import sys


# ---------------------------------------------------------------------------
# Project root detection
# ---------------------------------------------------------------------------

def find_project_root(start_dir=None):
    """Detect project root using PURLIN_PROJECT_ROOT or climbing fallback."""
    env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if env_root and os.path.isdir(env_root):
        return env_root
    if start_dir is None:
        start_dir = os.path.dirname(os.path.abspath(__file__))
    for depth in ('../../../', '../../'):
        candidate = os.path.abspath(os.path.join(start_dir, depth))
        if os.path.exists(os.path.join(candidate, '.purlin')):
            return candidate
    return os.path.abspath(os.path.join(start_dir, '../../'))


# ---------------------------------------------------------------------------
# Tier Table I/O
# ---------------------------------------------------------------------------

_TIER_TABLE_HEADER = """## Test Priority Tiers

<!-- Features not listed default to 'standard'. -->

| Feature | Tier |
|---------|------|"""

_TIER_ROW_PATTERN = re.compile(r'^\|\s*(\S+)\s*\|\s*(\S+)\s*\|$')


def _read_tier_table_from_markdown(project_root):
    """Fallback: read tier table from legacy markdown override files.

    Reads from BOTH PURLIN_OVERRIDES.md and QA_OVERRIDES.md, merging results.
    Returns dict mapping feature_name -> tier_string.
    """
    result = {}
    purlin_dir = os.path.join(project_root, '.purlin')

    for filename in ('PURLIN_OVERRIDES.md', 'QA_OVERRIDES.md'):
        filepath = os.path.join(purlin_dir, filename)
        if not os.path.exists(filepath):
            continue
        try:
            with open(filepath, 'r') as f:
                content = f.read()
        except (IOError, OSError):
            continue

        in_table = False
        for line in content.splitlines():
            if '## Test Priority Tiers' in line:
                in_table = True
                continue
            if in_table:
                if line.startswith('## ') and 'Test Priority Tiers' not in line:
                    break  # New section
                m = _TIER_ROW_PATTERN.match(line.strip())
                if m:
                    feature, tier = m.group(1), m.group(2)
                    if feature.lower() not in ('feature', '---', '---------'):
                        result[feature] = tier

    return result


def read_tier_table(project_root):
    """Read the Test Priority Tiers from .purlin/config.json.

    Falls back to parsing legacy markdown override files for
    backward compatibility with un-migrated projects.
    Returns dict mapping feature_name -> tier_string.
    """
    config_path = os.path.join(project_root, '.purlin', 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        tiers = config.get('test_priority_tiers')
        if tiers:
            return tiers
    except (IOError, OSError, json.JSONDecodeError):
        pass

    # Fallback to legacy markdown parsing for un-migrated projects
    return _read_tier_table_from_markdown(project_root)


def add_to_tier_table(project_root, feature, tier='smoke', dry_run=False):
    """Add a feature to the test_priority_tiers key in .purlin/config.json.

    Returns dict with 'action' and 'file' keys.
    """
    config_path = os.path.join(project_root, '.purlin', 'config.json')

    # Read existing config
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except (IOError, OSError, json.JSONDecodeError):
        config = {}

    tiers = config.get('test_priority_tiers', {})

    # Check if feature already in table
    if feature in tiers:
        return {'action': 'already_exists', 'file': config_path,
                'current_tier': tiers[feature]}

    tiers[feature] = tier
    config['test_priority_tiers'] = tiers

    if not dry_run:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            f.write('\n')

    return {'action': 'added', 'file': config_path}


# ---------------------------------------------------------------------------
# Smoke Regression Creation
# ---------------------------------------------------------------------------

def create_smoke_regression(project_root, feature, scenarios):
    """Create a simplified smoke regression JSON file.

    Args:
        project_root: Project root path.
        feature: Feature stem name.
        scenarios: List of scenario dicts with 'name' and 'description' keys.
            Maximum 3 scenarios for smoke tier.

    Returns dict with 'file' and 'scenarios_count' keys.
    """
    if len(scenarios) > 3:
        scenarios = scenarios[:3]

    smoke_data = {
        'feature': feature,
        'frequency': 'per-feature',
        'tier': 'smoke',
        'smoke_of': f'{feature}.json',
        'scenarios': scenarios,
    }

    output_dir = os.path.join(project_root, 'tests', 'qa', 'scenarios')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'{feature}_smoke.json')

    with open(output_path, 'w') as f:
        json.dump(smoke_data, f, indent=2)
        f.write('\n')

    return {'file': output_path, 'scenarios_count': len(scenarios)}


# ---------------------------------------------------------------------------
# Smoke Feature Suggestion
# ---------------------------------------------------------------------------

# Category keywords for smoke candidates
_SMOKE_CATEGORIES = {'Install, Update & Scripts', 'Coordination & Lifecycle'}
_SMOKE_NAME_KEYWORDS = {'launcher', 'init', 'config', 'cdd', 'status'}


def _count_dependents(dep_graph):
    """Count how many features depend on each feature (fan-out).

    Returns dict mapping feature_basename -> dependent_count.
    """
    dependents = {}
    for feature in dep_graph.get('features', []):
        for prereq in feature.get('prerequisites', []):
            # Normalize: prereq may be "foo.md" or "foo.md (annotation)"
            basename = prereq.split(' ')[0].replace('.md', '')
            basename = basename.split('/')[-1]  # Strip path prefix
            dependents[basename] = dependents.get(basename, 0) + 1
    return dependents


def suggest_smoke_features(project_root, scan_data=None, dep_graph=None):
    """Identify features that should be promoted to smoke tier.

    Returns list of dicts with 'feature', 'reasons' keys.
    """
    # Load dependency graph
    if dep_graph is None:
        graph_path = os.path.join(project_root, '.purlin', 'cache',
                                  'dependency_graph.json')
        try:
            with open(graph_path, 'r') as f:
                dep_graph = json.load(f)
        except (IOError, OSError, json.JSONDecodeError):
            dep_graph = {'features': []}

    # Load scan data
    if scan_data is None:
        scan_path = os.path.join(project_root, '.purlin', 'cache', 'scan.json')
        try:
            with open(scan_path, 'r') as f:
                scan_data = json.load(f)
        except (IOError, OSError, json.JSONDecodeError):
            scan_data = {'features': []}

    # Get existing smoke features
    existing_smoke = read_tier_table(project_root)
    smoke_set = {k for k, v in existing_smoke.items() if v == 'smoke'}

    # Also check for _smoke.json files
    scenarios_dir = os.path.join(project_root, 'tests', 'qa', 'scenarios')
    if os.path.isdir(scenarios_dir):
        for f in os.listdir(scenarios_dir):
            if f.endswith('_smoke.json'):
                smoke_set.add(f.replace('_smoke.json', ''))

    # Count dependents
    dependents = _count_dependents(dep_graph)

    # Build category/label index from dependency graph
    feature_info = {}
    for f in dep_graph.get('features', []):
        basename = os.path.basename(f['file']).replace('.md', '')
        feature_info[basename] = {
            'category': f.get('category', ''),
            'label': f.get('label', ''),
        }

    # Build test status index from scan data
    test_status = {}
    for f in scan_data.get('features', []):
        test_status[f['name']] = f.get('test_status')

    suggestions = []
    all_features = set()
    for f in dep_graph.get('features', []):
        name = os.path.basename(f['file']).replace('.md', '')
        all_features.add(name)

    for feature in sorted(all_features):
        if feature in smoke_set:
            continue

        reasons = []

        # High fan-out (3+ dependents)
        dep_count = dependents.get(feature, 0)
        if dep_count >= 3:
            reasons.append(f'prerequisite for {dep_count} features')

        # Anchor nodes (including invariants and new types).
        if feature.startswith(('arch_', 'design_', 'policy_', 'ops_', 'prodbrief_', 'i_')):
            reasons.append('foundational constraint (anchor node)')

        # Core categories
        info = feature_info.get(feature, {})
        if info.get('category') in _SMOKE_CATEGORIES:
            reasons.append(f'core category: {info["category"]}')

        # Name keywords
        for keyword in _SMOKE_NAME_KEYWORDS:
            if keyword in feature:
                reasons.append(f'name contains "{keyword}"')
                break

        # Only suggest if there's at least one reason
        if reasons:
            suggestions.append({
                'feature': feature,
                'reasons': reasons,
                'has_passing_tests': test_status.get(feature) == 'PASS',
            })

    # Sort by number of reasons (most compelling first), then by name
    suggestions.sort(key=lambda s: (-len(s['reasons']), s['feature']))

    return suggestions


# ---------------------------------------------------------------------------
# Smoke Gate Ordering
# ---------------------------------------------------------------------------

def get_smoke_features(project_root):
    """Get all smoke-tier features from both tier table and _smoke.json files.

    Returns set of feature names.
    """
    smoke_set = set()

    # From tier table
    tiers = read_tier_table(project_root)
    for feature, tier in tiers.items():
        if tier == 'smoke':
            smoke_set.add(feature)

    # From _smoke.json files
    scenarios_dir = os.path.join(project_root, 'tests', 'qa', 'scenarios')
    if os.path.isdir(scenarios_dir):
        for filename in os.listdir(scenarios_dir):
            if filename.endswith('_smoke.json'):
                try:
                    filepath = os.path.join(scenarios_dir, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    if data.get('tier') == 'smoke':
                        smoke_set.add(data.get('feature', filename.replace('_smoke.json', '')))
                except (IOError, OSError, json.JSONDecodeError):
                    continue

    return smoke_set


def get_smoke_regressions(project_root):
    """Get smoke regression files.

    Returns list of dicts with 'feature', 'file', 'scenarios' keys.
    """
    regressions = []
    scenarios_dir = os.path.join(project_root, 'tests', 'qa', 'scenarios')
    if not os.path.isdir(scenarios_dir):
        return regressions

    for filename in sorted(os.listdir(scenarios_dir)):
        if not filename.endswith('_smoke.json'):
            continue
        filepath = os.path.join(scenarios_dir, filename)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            if data.get('tier') == 'smoke':
                regressions.append({
                    'feature': data.get('feature', ''),
                    'file': filepath,
                    'scenarios': data.get('scenarios', []),
                })
        except (IOError, OSError, json.JSONDecodeError):
            continue

    return regressions


def order_verification(project_root, features_to_verify):
    """Order features for verification: smoke first, then standard.

    Args:
        project_root: Project root path.
        features_to_verify: List of feature names to verify.

    Returns dict with:
        'smoke_regressions': list of smoke regression files to run first
        'smoke_features': list of smoke-tier features (for QA scenarios)
        'standard_features': list of standard-tier features
    """
    smoke_set = get_smoke_features(project_root)
    smoke_regs = get_smoke_regressions(project_root)

    smoke_features = [f for f in features_to_verify if f in smoke_set]
    standard_features = [f for f in features_to_verify if f not in smoke_set]

    return {
        'smoke_regressions': smoke_regs,
        'smoke_features': smoke_features,
        'standard_features': standard_features,
    }


def check_smoke_gate(smoke_results):
    """Check if smoke tests passed.

    Args:
        smoke_results: List of dicts with 'feature' and 'status' keys.

    Returns dict with:
        'passed': bool
        'failures': list of failed feature names
        'message': str
    """
    failures = [r['feature'] for r in smoke_results if r.get('status') != 'PASS']

    if failures:
        msg = (
            f"SMOKE FAILURE: {len(failures)} smoke test(s) failed: "
            f"{', '.join(failures)}. "
            "Further verification is blocked until smoke tests pass."
        )
        return {'passed': False, 'failures': failures, 'message': msg}

    return {'passed': True, 'failures': [], 'message': 'Smoke gate passed.'}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: smoke.py [read-tiers | add <feature> | suggest | order <feature,...>]",
              file=sys.stderr)
        sys.exit(1)

    project_root = find_project_root()
    cmd = sys.argv[1]

    if cmd == 'read-tiers':
        tiers = read_tier_table(project_root)
        print(json.dumps(tiers, indent=2))

    elif cmd == 'add':
        if len(sys.argv) < 3:
            print("Usage: smoke.py add <feature> [tier]", file=sys.stderr)
            sys.exit(1)
        feature = sys.argv[2]
        tier = sys.argv[3] if len(sys.argv) > 3 else 'smoke'
        result = add_to_tier_table(project_root, feature, tier)
        print(json.dumps(result, indent=2))

    elif cmd == 'suggest':
        suggestions = suggest_smoke_features(project_root)
        print(json.dumps(suggestions, indent=2))

    elif cmd == 'order':
        if len(sys.argv) < 3:
            print("Usage: smoke.py order <feature1,feature2,...>", file=sys.stderr)
            sys.exit(1)
        features = sys.argv[2].split(',')
        order = order_verification(project_root, features)
        print(json.dumps(order, indent=2))

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
