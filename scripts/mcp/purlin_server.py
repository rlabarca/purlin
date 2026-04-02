#!/usr/bin/env python3
"""Purlin MCP Server — sync_status + purlin_config.

Implements the MCP (Model Context Protocol) stdio transport using JSON-RPC 2.0.
All tools use Python stdlib only (no external dependencies).

Usage:
    python3 scripts/mcp/purlin_server.py

The server reads JSON-RPC requests from stdin and writes responses to stdout.
It is started automatically by Claude Code when the plugin is enabled.
"""

import glob
import hashlib
import json
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from config_engine import find_project_root, resolve_config, update_config

# ---------------------------------------------------------------------------
# sync_status — the core coverage tool
# ---------------------------------------------------------------------------

_RULE_RE = re.compile(r'^-\s+(RULE-\d+):\s*(.+)', re.MULTILINE)
_REQUIRES_RE = re.compile(r'^>\s*Requires:\s*(.+)', re.MULTILINE)
_SCOPE_RE = re.compile(r'^>\s*Scope:\s*(.+)', re.MULTILINE)
_MANUAL_STAMPED_RE = re.compile(
    r'@manual\(([^,]+),\s*(\d{4}-\d{2}-\d{2}),\s*([a-f0-9]+)\)'
)
_MANUAL_UNSTAMPED_RE = re.compile(r'@manual(?:\s|$)')
_PROOF_LINE_RE = re.compile(
    r'^-\s+(PROOF-\d+)\s*\((RULE-\d+)\):\s*(.+)', re.MULTILINE
)
_STRUCTURAL_PROOF_RE = re.compile(
    r'grep|verify\s.*exist|verify\s.*present|verify\s.*section'
    r'|verify\s.*field|verify\s.*appear|verify\s.*contain',
    re.IGNORECASE,
)
_BEHAVIORAL_PROOF_RE = re.compile(
    r'\brun\b|\bcall\b|\bPOST\b|\bGET\b|assert\s.*response'
    r'|assert\s.*status|assert\s.*return|exit\s+code'
    r'|verify\s.*output|\bexecute\b',
    re.IGNORECASE,
)
_GLOBAL_RE = re.compile(r'^>\s*Global:\s*true\s*$', re.MULTILINE | re.IGNORECASE)
_ANCHOR_PREFIXES = (
    'design_', 'api_', 'security_', 'brand_',
    'platform_', 'schema_', 'legal_', 'prodbrief_',
)


def _scan_specs(project_root):
    """Scan all specs and return a dict of feature -> spec info."""
    spec_dir = os.path.join(project_root, 'specs')
    if not os.path.isdir(spec_dir):
        return {}

    features = {}
    for spec_path in glob.glob(os.path.join(spec_dir, '**', '*.md'), recursive=True):
        # Skip proof files and non-spec files
        basename = os.path.basename(spec_path)
        if basename.startswith('.'):
            continue

        feature_name = os.path.splitext(basename)[0]
        rel_path = os.path.relpath(spec_path, project_root)

        with open(spec_path, 'r') as f:
            content = f.read()

        # Determine if this is an invariant
        is_invariant = '/_invariants/' in rel_path

        # Detect global invariants (> Global: true)
        is_global = is_invariant and bool(_GLOBAL_RE.search(content))

        # Extract rules from ## Rules section
        rules = {}
        rules_section = _extract_section(content, '## Rules')
        if rules_section is not None:
            for m in _RULE_RE.finditer(rules_section):
                rules[m.group(1)] = m.group(2).strip()
            # Check for unnumbered rule lines
            unnumbered = []
            for line in rules_section.strip().splitlines():
                line = line.strip()
                if line.startswith('- ') and not _RULE_RE.match(line):
                    unnumbered.append(line)
        else:
            unnumbered = []

        # Extract requires
        requires = []
        req_match = _REQUIRES_RE.search(content)
        if req_match:
            requires = [r.strip() for r in req_match.group(1).split(',') if r.strip()]

        # Extract scope
        scope = []
        scope_match = _SCOPE_RE.search(content)
        if scope_match:
            scope = [s.strip() for s in scope_match.group(1).split(',') if s.strip()]

        # Parse manual proof stamps and collect proof descriptions from ## Proof section
        manual_proofs = {}
        proof_descriptions = []
        proof_section = _extract_section(content, '## Proof')
        if proof_section:
            for line in proof_section.strip().splitlines():
                line = line.strip()
                proof_match = _PROOF_LINE_RE.match(line)
                if not proof_match:
                    continue
                proof_id = proof_match.group(1)
                rule_id = proof_match.group(2)
                proof_desc = proof_match.group(3).strip()
                proof_descriptions.append(proof_desc)
                stamp = _MANUAL_STAMPED_RE.search(line)
                if stamp:
                    manual_proofs[proof_id] = {
                        'rule': rule_id,
                        'email': stamp.group(1),
                        'date': stamp.group(2),
                        'commit_sha': stamp.group(3),
                        'stamped': True,
                    }
                elif _MANUAL_UNSTAMPED_RE.search(line):
                    manual_proofs[proof_id] = {
                        'rule': rule_id,
                        'stamped': False,
                    }

        features[feature_name] = {
            'path': rel_path,
            'rules': rules,
            'requires': requires,
            'scope': scope,
            'is_invariant': is_invariant,
            'is_global': is_global,
            'unnumbered_lines': unnumbered,
            'has_rules_section': rules_section is not None,
            'manual_proofs': manual_proofs,
            'proof_descriptions': proof_descriptions,
        }

    return features


def _extract_section(content, heading):
    """Extract content under a markdown heading until the next heading."""
    pattern = re.compile(
        r'^' + re.escape(heading) + r'\s*\n(.*?)(?=^## |\Z)',
        re.MULTILINE | re.DOTALL
    )
    m = pattern.search(content)
    return m.group(1) if m else None


def _read_proofs(project_root):
    """Read all proof JSON files and return dict of feature -> list of proofs."""
    spec_dir = os.path.join(project_root, 'specs')
    if not os.path.isdir(spec_dir):
        return {}

    all_proofs = {}
    for proof_path in glob.glob(os.path.join(spec_dir, '**', '*.proofs-*.json'), recursive=True):
        try:
            with open(proof_path, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            continue

        for entry in data.get('proofs', []):
            feature = entry.get('feature', '')
            all_proofs.setdefault(feature, []).append(entry)

    return all_proofs


def _check_manual_staleness(project_root, scope_files, commit_sha):
    """Check if any scope files have commits newer than the manual stamp's SHA."""
    if not scope_files or not commit_sha:
        return False
    try:
        result = subprocess.run(
            ['git', 'log', '--oneline', f'{commit_sha}..HEAD', '--'] + scope_files,
            capture_output=True, text=True, cwd=project_root, timeout=5
        )
        return bool(result.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        return False


def _compute_vhash(rules, proofs):
    """Compute verification hash from sorted rule IDs + sorted proof IDs/statuses."""
    rule_ids = sorted(rules.keys())
    proof_parts = sorted(f"{p['id']}:{p['status']}" for p in proofs)
    payload = ','.join(rule_ids) + '|' + ','.join(proof_parts)
    return hashlib.sha256(payload.encode()).hexdigest()[:8]


def _is_structural_only(proof_descriptions):
    """Return True if ALL proof descriptions are grep/existence checks with no behavioral tests."""
    if not proof_descriptions:
        return False
    for desc in proof_descriptions:
        if not _STRUCTURAL_PROOF_RE.search(desc):
            return False
        if _BEHAVIORAL_PROOF_RE.search(desc):
            return False
    return True


def sync_status(project_root, role=None):
    """Generate the full sync_status report with directives."""
    features = _scan_specs(project_root)
    all_proofs = _read_proofs(project_root)

    if not features:
        return "No specs found in specs/. Run purlin:init to set up, or create specs manually."

    lines = []

    # Separate invariants from regular features
    invariants = {k: v for k, v in features.items() if v['is_invariant']}
    regular = {k: v for k, v in features.items() if not v['is_invariant']}

    # Identify global invariants (auto-applied to all features)
    global_invariants = {k: v for k, v in invariants.items() if v.get('is_global')}

    # Process regular features
    for name in sorted(regular.keys()):
        info = regular[name]
        feature_lines = _report_feature(
            name, info, features, all_proofs, project_root, role, global_invariants
        )
        lines.extend(feature_lines)
        lines.append('')

    # Process invariants
    for name in sorted(invariants.keys()):
        info = invariants[name]
        rule_count = len(info['rules'])
        if info.get('is_global'):
            lines.append(f"{name}: {rule_count} rules (global — auto-applied to all features)")
        else:
            lines.append(f"{name}: {rule_count} rules (apply to features with > Requires: {name})")
        for rule_id, desc in sorted(info['rules'].items()):
            lines.append(f"  {rule_id}: {desc}")
        lines.append('')

    return '\n'.join(lines).strip()


def _scopes_overlap(scope_a, scope_b):
    """Check if two scope lists have overlapping file patterns."""
    for a in scope_a:
        for b in scope_b:
            if a.startswith(b) or b.startswith(a):
                return True
    return False


def _build_coverage_rules(name, info, all_features, global_invariants=None):
    """Build combined rule entries for a feature (own + required + global).

    Returns list of (key, label, source_feature) tuples.
    """
    if global_invariants is None:
        global_invariants = {}

    entries = []
    for rule_id in sorted(info['rules'].keys()):
        entries.append((rule_id, 'own', name))

    for req_name in info.get('requires', []):
        req_info = all_features.get(req_name)
        if req_info:
            for rule_id in sorted(req_info['rules'].keys()):
                entries.append((f"{req_name}/{rule_id}", 'required', req_name))

    for inv_name in sorted(global_invariants.keys()):
        if inv_name in info.get('requires', []):
            continue
        inv_info = global_invariants[inv_name]
        for rule_id in sorted(inv_info['rules'].keys()):
            entries.append((f"{inv_name}/{rule_id}", 'global', inv_name))

    return entries


def _build_proof_lookup(name, rule_entries, all_proofs):
    """Build proof-by-rule lookup for a combined rule set.

    Returns dict of rule_key -> best proof entry.
    """
    all_rule_keys = {key for key, _, _ in rule_entries}

    proof_by_rule = {}
    # Own proofs
    for p in all_proofs.get(name, []):
        rule = p.get('rule', '')
        if rule not in proof_by_rule or p.get('status') == 'fail':
            proof_by_rule[rule] = p

    # Required/global proofs — filed under the source feature's name
    source_features = {src for _, label, src in rule_entries if label != 'own'}
    for src_name in source_features:
        for p in all_proofs.get(src_name, []):
            rule = p.get('rule', '')
            key = f"{src_name}/{rule}"
            if key in all_rule_keys:
                if key not in proof_by_rule or p.get('status') == 'fail':
                    proof_by_rule[key] = p

    return proof_by_rule


def _collect_relevant_proofs(name, rule_entries, all_proofs):
    """Collect all proof entries relevant to the combined rule set (for vhash)."""
    all_rule_keys = {key for key, _, _ in rule_entries}

    proofs = list(all_proofs.get(name, []))
    source_features = {src for _, label, src in rule_entries if label != 'own'}
    for src_name in source_features:
        for p in all_proofs.get(src_name, []):
            key = f"{src_name}/{p.get('rule', '')}"
            if key in all_rule_keys:
                proofs.append(p)
    return proofs


def _report_feature(name, info, all_features, all_proofs, project_root, role,
                    global_invariants=None):
    """Generate report lines for a single feature."""
    lines = []
    if global_invariants is None:
        global_invariants = {}

    # Build combined rule set (own + required + global)
    rule_entries = _build_coverage_rules(name, info, all_features, global_invariants)
    proof_by_rule = _build_proof_lookup(name, rule_entries, all_proofs)
    all_relevant_proofs = _collect_relevant_proofs(name, rule_entries, all_proofs)

    total = len(rule_entries)
    proved = sum(1 for key, _, _ in rule_entries
                 if proof_by_rule.get(key, {}).get('status') == 'pass')

    # Format warnings
    warnings = []
    if not info['has_rules_section']:
        warnings.append("  WARNING: No ## Rules section found.")
        warnings.append(f"  → Run: purlin:spec {name}")
    elif info['unnumbered_lines']:
        warnings.append(f"  WARNING: {len(info['unnumbered_lines'])} lines under ## Rules are not numbered.")
        warnings.append('  → Fix: rewrite as "- RULE-1: ...", "- RULE-2: ...", etc.')
        warnings.append(f"  → Run: purlin:spec {name}")

    # Check manual proofs
    manual_proofs = info.get('manual_proofs', {})

    # Header — no rules
    if total == 0:
        lines.append(f"{name}: no rules defined")
        lines.extend(warnings)
        lines.append(f"  → Run: purlin:spec {name}")
        return lines

    # Header — all proved
    if proved == total and not warnings:
        structural_only = _is_structural_only(info.get('proof_descriptions', []))
        if structural_only:
            lines.append(f"{name}: READY (structural only)")
        else:
            lines.append(f"{name}: READY")
        lines.append(f"  {proved}/{total} rules proved ✓")
        all_rules_dict = {key: True for key, _, _ in rule_entries}
        vhash = _compute_vhash(all_rules_dict, all_relevant_proofs)
        lines.append(f"  vhash={vhash}")
        if structural_only:
            lines.append(f"  → Note: all {total} proofs are grep/existence checks. No behavioral tests verify the agent follows these instructions.")
            lines.append("  → Consider: create E2E proofs in specs/integration/ that test actual behavior")
        else:
            lines.append("  → No action needed.")
        _append_scope_suggestions(lines, name, info, all_features, global_invariants)
        return lines

    lines.append(f"{name}: {proved}/{total} rules proved")
    lines.extend(warnings)

    # Detail each rule with label
    for key, label, src_feature in rule_entries:
        proof = proof_by_rule.get(key)
        manual = None

        # Check manual proofs (only for own rules)
        if label == 'own':
            for mp_id, mp_info in manual_proofs.items():
                if mp_info.get('rule') == key:
                    manual = (mp_id, mp_info)
                    break

        if proof and proof.get('status') == 'pass':
            lines.append(f"  {key}: PASS ({label})")
        elif proof and proof.get('status') == 'fail':
            test_name = proof.get('test_name', '?')
            lines.append(f"  {key}: FAIL ({label})")
            lines.append(f"  → Fix: {test_name} is failing. Check the test or fix the code.")
            lines.append(f"  → Run: purlin:unit-test")
        elif manual:
            mp_id, mp_info = manual
            if mp_info.get('stamped'):
                stale = _check_manual_staleness(
                    project_root, info.get('scope', []), mp_info.get('commit_sha', '')
                )
                if stale:
                    lines.append(f"  {key}: MANUAL PROOF STALE ({mp_id}, verified {mp_info['date']}) ({label})")
                    lines.append(f"  → Re-verify and run: purlin:verify --manual {name} {mp_id}")
                else:
                    lines.append(f"  {key}: PASS ({mp_id}, manual, verified {mp_info['date']}) ({label})")
            else:
                lines.append(f"  {key}: MANUAL PROOF NEEDED ({label})")
                lines.append(f"  → Verify manually, then run: purlin:verify --manual {name} {mp_id}")
        else:
            lines.append(f"  {key}: NO PROOF ({label})")
            # Determine proof marker feature name and rule id
            if '/' in key:
                marker_feature = src_feature
                rule_id = key.split('/', 1)[1]
            else:
                marker_feature = name
                rule_id = key
            lines.append(f'  → Fix: write a test with @pytest.mark.proof("{marker_feature}", "PROOF-N", "{rule_id}")')
            src_info = all_features.get(src_feature, {})
            if src_info.get('is_invariant'):
                lines.append(f"  Note: read specs/_invariants/{src_feature}.md for exact assertion values before writing tests")
            lines.append(f"  → Run: purlin:unit-test")

    # If no proof files at all
    feature_proofs = all_proofs.get(name, [])
    if not feature_proofs and not manual_proofs and not any(
        proof_by_rule.get(key) for key, _, _ in rule_entries
    ):
        lines.append(f"  → Run: purlin:unit-test")

    _append_scope_suggestions(lines, name, info, all_features, global_invariants)
    return lines


def _append_scope_suggestions(lines, name, info, all_features, global_invariants):
    """Append scope-overlap anchor suggestions to report lines."""
    feature_scope = info.get('scope', [])
    if not feature_scope:
        return

    required_names = set(info.get('requires', []))
    required_names.update(global_invariants.keys())

    for anchor_name in sorted(all_features.keys()):
        if anchor_name == name or anchor_name in required_names:
            continue
        anchor_info = all_features[anchor_name]
        if anchor_info['is_invariant']:
            continue
        if not any(anchor_name.startswith(p) for p in _ANCHOR_PREFIXES):
            continue
        anchor_scope = anchor_info.get('scope', [])
        if not anchor_scope:
            continue
        if _scopes_overlap(feature_scope, anchor_scope):
            overlap_parts = [s for s in anchor_scope
                             if any(f.startswith(s) or s.startswith(f) for f in feature_scope)]
            overlap_str = ', '.join(overlap_parts) if overlap_parts else ', '.join(anchor_scope)
            lines.append(f"  \u26a0 Anchor {anchor_name} has overlapping scope ({overlap_str}) but is not required")
            lines.append(f"  \u2192 Consider: add > Requires: {anchor_name}")


# ---------------------------------------------------------------------------
# changelog tool
# ---------------------------------------------------------------------------

_NO_IMPACT_PATTERNS = (
    'docs/', 'assets/', 'templates/', 'references/', '.gitignore', 'LICENSE',
    'CLAUDE.md', 'README.md', 'RELEASE_NOTES.md', '.mcp.json', 'settings.json',
)

_TEST_PATTERNS = ('.proofs-', 'test_', '_test.', '.test.', 'tests/', 'dev/test_')


def _resolve_since_anchor(project_root, since_arg=None):
    """Resolve the 'since' anchor to a (ref, description) tuple."""
    def _run_git(args):
        try:
            r = subprocess.run(
                ['git'] + args, capture_output=True, text=True,
                cwd=project_root, timeout=10,
            )
            return r.stdout.strip() if r.returncode == 0 else ''
        except (subprocess.SubprocessError, OSError):
            return ''

    if since_arg:
        # Integer → HEAD~N
        try:
            n = int(since_arg)
            ref = f'HEAD~{n}'
            return ref, f'last {n} commits'
        except ValueError:
            pass
        # Date → find earliest commit since that date
        sha = _run_git(['log', '--oneline', '--reverse', f'--since={since_arg}',
                         '--format=%H', '-1'])
        if sha:
            return f'{sha}^', f'since {since_arg}'
        return 'HEAD~20', f'since {since_arg} (no commits found, using last 20)'

    # Most recent verify: commit
    verify_line = _run_git(['log', '--oneline', '--grep=^verify:', '-1',
                             '--format=%H %ar'])
    if verify_line:
        parts = verify_line.split(' ', 1)
        sha = parts[0]
        relative = parts[1] if len(parts) > 1 else ''
        return sha, f'last verification ({relative})'

    # Most recent tag
    tag = _run_git(['describe', '--tags', '--abbrev=0'])
    if tag:
        relative = _run_git(['log', '-1', '--format=%ar', tag])
        return tag, f'{tag} ({relative})'

    # Fallback
    return 'HEAD~20', 'last 20 commits (no verification or tag found)'


def _get_diff_stat(project_root, since_ref, filepath):
    """Get +/- line counts for a single file."""
    try:
        r = subprocess.run(
            ['git', 'diff', '--numstat', since_ref + '..HEAD', '--', filepath],
            capture_output=True, text=True, cwd=project_root, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            parts = r.stdout.strip().split('\t')
            if len(parts) >= 2:
                return f'+{parts[0]} -{parts[1]}'
    except (subprocess.SubprocessError, OSError):
        pass
    return ''


def _detect_spec_changes(project_root, since_ref, spec_files_in_diff):
    """For changed spec files, detect new/removed rules."""
    changes = []
    for spec_path in spec_files_in_diff:
        feature_name = os.path.splitext(os.path.basename(spec_path))[0]
        try:
            r = subprocess.run(
                ['git', 'diff', since_ref + '..HEAD', '--', spec_path],
                capture_output=True, text=True, cwd=project_root, timeout=5,
            )
            diff_text = r.stdout if r.returncode == 0 else ''
        except (subprocess.SubprocessError, OSError):
            diff_text = ''

        new_rules = []
        removed_rules = []
        for line in diff_text.splitlines():
            m = _RULE_RE.search(line)
            if m:
                rule_id = m.group(1)
                if line.startswith('+') and not line.startswith('+++'):
                    new_rules.append(rule_id)
                elif line.startswith('-') and not line.startswith('---'):
                    removed_rules.append(rule_id)

        changes.append({
            'spec': feature_name,
            'new_rules': new_rules,
            'removed_rules': removed_rules,
        })
    return changes


def changelog(project_root, since=None, role=None):
    """Generate structured changelog data as JSON."""
    since_ref, since_desc = _resolve_since_anchor(project_root, since)

    # Gather commits
    try:
        r = subprocess.run(
            ['git', 'log', '--oneline', since_ref + '..HEAD'],
            capture_output=True, text=True, cwd=project_root, timeout=10,
        )
        commits = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()] \
            if r.returncode == 0 else []
    except (subprocess.SubprocessError, OSError):
        commits = []

    # Gather changed files
    try:
        r = subprocess.run(
            ['git', 'diff', '--name-only', since_ref + '..HEAD'],
            capture_output=True, text=True, cwd=project_root, timeout=10,
        )
        changed_files = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()] \
            if r.returncode == 0 else []
    except (subprocess.SubprocessError, OSError):
        changed_files = []

    # Filter deleted files — only keep files that exist on disk
    changed_files = [
        f for f in changed_files
        if os.path.exists(os.path.join(project_root, f))
    ]

    # Build scope map from specs
    features = _scan_specs(project_root)
    scope_to_specs = {}  # source_file → [spec_names]
    for name, info in features.items():
        for scope_file in info.get('scope', []):
            scope_to_specs.setdefault(scope_file, []).append(name)

    # Classify each file
    file_entries = []
    spec_files_in_diff = []

    for filepath in changed_files:
        # specs/ → CHANGED_SPECS
        if filepath.startswith('specs/') and filepath.endswith('.md'):
            spec_files_in_diff.append(filepath)
            spec_name = os.path.splitext(os.path.basename(filepath))[0]
            file_entries.append({
                'path': filepath,
                'category': 'CHANGED_SPECS',
                'spec': spec_name,
                'diff_stat': _get_diff_stat(project_root, since_ref, filepath),
            })
            continue

        # Test files or proof files → TESTS_ADDED
        if any(p in filepath for p in _TEST_PATTERNS):
            # Try to find associated spec
            spec_name = None
            for sname in features:
                if sname.replace('-', '_') in filepath or sname in filepath:
                    spec_name = sname
                    break
            file_entries.append({
                'path': filepath,
                'category': 'TESTS_ADDED',
                'spec': spec_name,
                'diff_stat': _get_diff_stat(project_root, since_ref, filepath),
            })
            continue

        # Check scope map → CHANGED_BEHAVIOR
        matched_specs = scope_to_specs.get(filepath, [])
        if matched_specs:
            file_entries.append({
                'path': filepath,
                'category': 'CHANGED_BEHAVIOR',
                'spec': matched_specs[0],
                'diff_stat': _get_diff_stat(project_root, since_ref, filepath),
            })
            continue

        # Docs/config/assets → NO_IMPACT
        if any(filepath.startswith(p) or filepath == p or filepath.endswith(p)
               for p in _NO_IMPACT_PATTERNS) or filepath.endswith('.md'):
            file_entries.append({
                'path': filepath,
                'category': 'NO_IMPACT',
                'spec': None,
                'diff_stat': _get_diff_stat(project_root, since_ref, filepath),
            })
            continue

        # Everything else unscoped → NEW_BEHAVIOR
        file_entries.append({
            'path': filepath,
            'category': 'NEW_BEHAVIOR',
            'spec': None,
            'diff_stat': _get_diff_stat(project_root, since_ref, filepath),
        })

    # Detect spec rule changes
    spec_changes = _detect_spec_changes(project_root, since_ref, spec_files_in_diff)

    # Collect proof status per feature (including required + global rules)
    all_proofs = _read_proofs(project_root)
    global_invariants = {
        k: v for k, v in features.items()
        if v.get('is_invariant') and v.get('is_global')
    }
    proof_status = {}
    for name, info in features.items():
        if info['is_invariant']:
            continue
        rule_entries = _build_coverage_rules(name, info, features, global_invariants)
        total = len(rule_entries)
        if total == 0:
            continue
        proof_by_rule = _build_proof_lookup(name, rule_entries, all_proofs)
        proved = sum(1 for key, _, _ in rule_entries
                     if proof_by_rule.get(key, {}).get('status') == 'pass')
        failing = [key for key, _, _ in rule_entries
                   if proof_by_rule.get(key, {}).get('status') == 'fail']
        status = 'READY' if proved == total else 'FAILING' if failing else 'partial'
        structural_only = (
            status == 'READY'
            and _is_structural_only(info.get('proof_descriptions', []))
        )
        proof_status[name] = {
            'proved': proved,
            'total': total,
            'status': status,
            'failing_rules': failing,
            'structural_only': structural_only,
        }

    result = {
        'since': since_desc,
        'commits': commits,
        'files': file_entries,
        'spec_changes': spec_changes,
        'proof_status': proof_status,
    }

    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# purlin_config tool
# ---------------------------------------------------------------------------

def handle_purlin_config(project_root, arguments):
    """Handle purlin_config MCP tool calls."""
    action = arguments.get('action', 'read')
    key = arguments.get('key')
    value = arguments.get('value')

    config = resolve_config(project_root)

    if action == 'read':
        if key:
            val = config.get(key)
            if val is None:
                return f"Key '{key}' not found in config."
            return json.dumps({key: val}, indent=2)
        return json.dumps(config, indent=2)
    elif action == 'write':
        if not key:
            return "Error: 'key' is required for write action."
        update_config(project_root, key, value)
        return f"Set '{key}' = {json.dumps(value)}"
    else:
        return f"Unknown action: {action}. Use 'read' or 'write'."


# ---------------------------------------------------------------------------
# MCP JSON-RPC transport
# ---------------------------------------------------------------------------

SERVER_INFO = {
    "name": "purlin",
    "version": "0.9.0",
}

TOOLS = [
    {
        "name": "sync_status",
        "description": "Show rule coverage per feature. Greps specs for RULE-N, reads *.proofs-*.json, diffs them. Returns coverage report with actionable → directives.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "description": "Optional role filter (pm, dev, qa) to prioritize relevant items.",
                    "enum": ["pm", "dev", "qa"]
                }
            },
            "required": []
        }
    },
    {
        "name": "purlin_config",
        "description": "Read or update Purlin configuration from .purlin/config.json.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform: 'read' or 'write'.",
                    "enum": ["read", "write"]
                },
                "key": {
                    "type": "string",
                    "description": "Config key to read or write."
                },
                "value": {
                    "description": "Value to set (for write action)."
                }
            },
            "required": []
        }
    },
    {
        "name": "changelog",
        "description": "Structured changelog since last verification. Returns JSON with commits, categorized files, spec changes, and proof status for the purlin:changelog skill to interpret.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "since": {
                    "type": "string",
                    "description": "Override anchor: integer for last N commits, or YYYY-MM-DD date."
                },
                "role": {
                    "type": "string",
                    "description": "Role filter for TOP PRIORITIES: pm, eng, qa, or all.",
                    "enum": ["pm", "eng", "qa", "all"]
                }
            },
            "required": []
        }
    }
]


def handle_request(request, project_root):
    """Handle a single JSON-RPC request and return a response dict."""
    method = request.get('method', '')
    req_id = request.get('id')
    params = request.get('params', {})

    if method == 'initialize':
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            }
        }

    if method == 'notifications/initialized':
        return None  # No response for notifications

    if method == 'tools/list':
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS}
        }

    if method == 'tools/call':
        tool_name = params.get('name', '')
        arguments = params.get('arguments', {})

        if tool_name == 'sync_status':
            try:
                result_text = sync_status(project_root, role=arguments.get('role'))
            except Exception as e:
                result_text = f"Error running sync_status: {e}"
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": result_text}]
                }
            }

        if tool_name == 'purlin_config':
            try:
                result_text = handle_purlin_config(project_root, arguments)
            except Exception as e:
                result_text = f"Error: {e}"
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": result_text}]
                }
            }

        if tool_name == 'changelog':
            try:
                result_text = changelog(
                    project_root,
                    since=arguments.get('since'),
                    role=arguments.get('role'),
                )
            except Exception as e:
                result_text = f"Error running changelog: {e}"
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": result_text}]
                }
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
        }

    # Unknown method
    if req_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"}
        }
    return None


def main():
    """Run the MCP server on stdio."""
    project_root = find_project_root()

    # Log startup to stderr (stdout is reserved for JSON-RPC)
    print(f"Purlin MCP server v0.9.0 started (root: {project_root})", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }
            sys.stdout.write(json.dumps(response) + '\n')
            sys.stdout.flush()
            continue

        response = handle_request(request, project_root)
        if response is not None:
            sys.stdout.write(json.dumps(response) + '\n')
            sys.stdout.flush()


if __name__ == '__main__':
    main()
