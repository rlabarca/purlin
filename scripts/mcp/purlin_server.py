#!/usr/bin/env python3
"""Purlin MCP Server — sync_status + purlin_config.

Implements the MCP (Model Context Protocol) stdio transport using JSON-RPC 2.0.
All tools use Python stdlib only (no external dependencies).

Usage:
    python3 scripts/mcp/purlin_server.py

The server reads JSON-RPC requests from stdin and writes responses to stdout.
It is started automatically by Claude Code when the plugin is enabled.
"""

import datetime
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
_DEFERRED_TAG_RE = re.compile(r'\(deferred\)\s*$', re.IGNORECASE)
_ASSUMED_TAG_RE = re.compile(r'\(assumed\s*—\s*.+?\)\s*$', re.IGNORECASE)
_CONFIRMED_TAG_RE = re.compile(r'\(confirmed\)\s*$', re.IGNORECASE)
_REQUIRES_RE = re.compile(r'^>\s*Requires:\s*(.+)', re.MULTILINE)
_SCOPE_RE = re.compile(r'^>\s*Scope:\s*(.+)', re.MULTILINE)
_MANUAL_STAMPED_RE = re.compile(
    r'@manual\(([^,]+),\s*(\d{4}-\d{2}-\d{2}),\s*([a-f0-9]+)\)'
)
_MANUAL_UNSTAMPED_RE = re.compile(r'@manual(?:\s|$)')
_PROOF_LINE_RE = re.compile(
    r'^-\s+(PROOF-\d+)\s*\((RULE-\d+(?:,\s*RULE-\d+)*)\):\s*(.+)', re.MULTILINE
)
_STRUCTURAL_PROOF_RE = re.compile(
    r'\bgrep\b'
    r'|(?:file|directory|folder)\s+exists'
    r'|(?:section|field|heading|key|entry)\s+(?:exists|is\s+present)'
    r'|contains?\s+(?:string|line|entry|section|field|heading)'
    r'|verify\s+(?:file|section|field|heading|key)\s+(?:exists|present|appears)',
    re.IGNORECASE,
)
_BEHAVIORAL_PROOF_RE = re.compile(
    r'\brun\b|\bcall\b|\bPOST\b|\bGET\b|assert\s.*response'
    r'|assert\s.*status|assert\s.*return|exit\s+code'
    r'|verify\s.*output|\bexecute\b',
    re.IGNORECASE,
)
_GLOBAL_RE = re.compile(r'^>\s*Global:\s*true\s*$', re.MULTILINE | re.IGNORECASE)
_SOURCE_RE = re.compile(r'^>\s*Source:\s*(.+)', re.MULTILINE)
_VISUAL_REF_RE = re.compile(r'^>\s*Visual-Reference:\s*(.+)', re.MULTILINE)
_VISUAL_HASH_RE = re.compile(r'^>\s*Visual-Hash:\s*sha256:([a-f0-9]+)', re.MULTILINE)


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

        # Determine if this is an anchor
        is_anchor = '/_anchors/' in rel_path or content.lstrip().startswith('# Anchor:')

        # Detect global anchors (> Global: true)
        is_global = is_anchor and bool(_GLOBAL_RE.search(content))

        # Extract rules from ## Rules section
        rules = {}
        deferred_rules = set()
        assumed_rules = set()
        rules_section = _extract_section(content, '## Rules')
        if rules_section is not None:
            for m in _RULE_RE.finditer(rules_section):
                rule_id = m.group(1)
                rule_desc = m.group(2).strip()
                rules[rule_id] = rule_desc
                if _DEFERRED_TAG_RE.search(rule_desc):
                    deferred_rules.add(rule_id)
                elif _ASSUMED_TAG_RE.search(rule_desc):
                    assumed_rules.add(rule_id)
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
        proof_desc_by_rule = {}
        proof_desc_by_id = {}
        proof_section = _extract_section(content, '## Proof')
        if proof_section:
            for line in proof_section.strip().splitlines():
                line = line.strip()
                proof_match = _PROOF_LINE_RE.match(line)
                if not proof_match:
                    continue
                proof_id = proof_match.group(1)
                rule_ids_raw = proof_match.group(2)
                proof_desc = proof_match.group(3).strip()
                # Strip tier tags (@unit, @integration, @e2e, @manual...) from description
                clean_desc = re.sub(r'\s*@\w+(?:\([^)]*\))?\s*$', '', proof_desc).strip()
                proof_descriptions.append(proof_desc)
                proof_desc_by_id[proof_id] = clean_desc
                # Support multi-rule proofs: PROOF-8 (RULE-1, RULE-2, RULE-4)
                rule_ids = [r.strip() for r in rule_ids_raw.split(',')]
                for rule_id in rule_ids:
                    proof_desc_by_rule.setdefault(rule_id, []).append(proof_desc)
                stamp = _MANUAL_STAMPED_RE.search(line)
                for rule_id in rule_ids:
                    if stamp:
                        manual_proofs[f"{proof_id}_{rule_id}"] = {
                            'rule': rule_id,
                            'email': stamp.group(1),
                            'date': stamp.group(2),
                            'commit_sha': stamp.group(3),
                            'stamped': True,
                        }
                    elif _MANUAL_UNSTAMPED_RE.search(line):
                        manual_proofs[f"{proof_id}_{rule_id}"] = {
                            'rule': rule_id,
                            'stamped': False,
                        }

        # Extract source URL for externally-referenced anchors
        source_match = _SOURCE_RE.search(content)
        source_url = source_match.group(1).strip() if source_match else None

        # Extract visual reference and hash for staleness detection
        visual_ref_match = _VISUAL_REF_RE.search(content)
        visual_hash_match = _VISUAL_HASH_RE.search(content)
        visual_ref = visual_ref_match.group(1).strip() if visual_ref_match else None
        visual_hash = visual_hash_match.group(1).strip() if visual_hash_match else None

        features[feature_name] = {
            'path': rel_path,
            'rules': rules,
            'deferred_rules': deferred_rules,
            'assumed_rules': assumed_rules,
            'requires': requires,
            'scope': scope,
            'is_anchor': is_anchor,
            'is_global': is_global,
            'source_url': source_url,
            'unnumbered_lines': unnumbered,
            'has_rules_section': rules_section is not None,
            'manual_proofs': manual_proofs,
            'proof_descriptions': proof_descriptions,
            'proof_desc_by_rule': proof_desc_by_rule,
            'proof_desc_by_id': proof_desc_by_id,
            'visual_ref': visual_ref,
            'visual_hash': visual_hash,
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
    """Read all proof JSON files and return dict of feature -> list of proofs.

    When the same (feature, tier) proof file exists both at specs/ root and in
    a subdirectory, prefer the subdirectory version (adjacent to its spec).
    """
    spec_dir = os.path.join(project_root, 'specs')
    if not os.path.isdir(spec_dir):
        return {}

    # Build spec directory map: feature_name -> directory containing its .md
    spec_dirs = {}
    for spec_path in glob.glob(os.path.join(spec_dir, '**', '*.md'), recursive=True):
        stem = os.path.splitext(os.path.basename(spec_path))[0]
        spec_dirs[stem] = os.path.dirname(spec_path)

    # Collect all proof files, grouped by (feature_stem, tier)
    proof_files = {}  # (feature_stem, tier) -> [paths]
    proof_re = re.compile(r'^(.+)\.proofs-(.+)\.json$')
    for proof_path in glob.glob(os.path.join(spec_dir, '**', '*.proofs-*.json'), recursive=True):
        basename = os.path.basename(proof_path)
        m = proof_re.match(basename)
        if not m:
            continue
        feature_stem = m.group(1)
        tier = m.group(2)
        proof_files.setdefault((feature_stem, tier), []).append(proof_path)

    # For each (feature, tier), pick the best proof file
    all_proofs = {}
    for (feature_stem, tier), paths in proof_files.items():
        if len(paths) == 1:
            chosen = paths[0]
        else:
            # Prefer the path in the same directory as the spec
            spec_directory = spec_dirs.get(feature_stem)
            subdir_paths = [p for p in paths if os.path.dirname(p) == spec_directory] if spec_directory else []
            if subdir_paths:
                chosen = subdir_paths[0]
            else:
                # No spec match — pick most recently modified
                chosen = max(paths, key=os.path.getmtime)

        try:
            with open(chosen, 'r') as f:
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


def _check_visual_hash(project_root, visual_ref, stored_hash):
    """Check if a visual reference image's hash matches the stored hash.

    Returns True if the image has changed (hash mismatch), False otherwise.
    Returns False if the image doesn't exist or isn't a local path.
    """
    if not visual_ref or not stored_hash:
        return False
    # Only check local file paths (not figma:// or https://)
    if visual_ref.startswith(('figma://', 'http://', 'https://')):
        return False
    image_path = os.path.join(project_root, visual_ref.lstrip('./'))
    if not os.path.isfile(image_path):
        return False
    try:
        with open(image_path, 'rb') as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()
        return current_hash != stored_hash
    except (IOError, OSError):
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


def _is_structural_proof_desc(desc):
    """Return True if a single proof description is structural (grep/existence check)."""
    return bool(_STRUCTURAL_PROOF_RE.search(desc)) and not bool(_BEHAVIORAL_PROOF_RE.search(desc))


def _get_rule_proof_descs(key, label, src_feature, info, all_features):
    """Get proof descriptions for a rule from its source spec."""
    if label == 'own':
        return info.get('proof_desc_by_rule', {}).get(key, [])
    bare_rule = key.split('/', 1)[1] if '/' in key else key
    src_info = all_features.get(src_feature, {})
    return src_info.get('proof_desc_by_rule', {}).get(bare_rule, [])


def _classify_structural_rules(active_entries, info, all_features):
    """Return set of rule keys whose proof descriptions are all structural."""
    structural = set()
    for key, label, src in active_entries:
        descs = _get_rule_proof_descs(key, label, src, info, all_features)
        if descs and all(_is_structural_proof_desc(d) for d in descs):
            structural.add(key)
    return structural


def _relative_time(iso_timestamp):
    """Return human-readable relative time string from an ISO 8601 timestamp."""
    if not iso_timestamp:
        return None
    try:
        then = datetime.datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
    except (ValueError, TypeError, AttributeError):
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    delta = now - then
    secs = delta.total_seconds()
    if secs < 60:
        return "just now"
    if secs < 3600:
        mins = int(secs / 60)
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    if secs < 86400:
        hours = int(secs / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = delta.days
    return f"{days} day{'s' if days != 1 else ''} ago"


def _read_audit_summary(project_root, total_no_proof_count=0):
    """Read audit cache and compute project-wide integrity summary.

    total_no_proof_count: total own behavioral rules with no proof across all
    features. These inflate the denominator to penalize missing proofs.
    Returns dict with integrity stats or None if no cache exists.
    """
    cache_path = os.path.join(project_root, '.purlin', 'cache', 'audit_cache.json')
    if not os.path.isfile(cache_path):
        return None
    try:
        with open(cache_path) as f:
            cache = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return None
    if not isinstance(cache, dict) or not cache:
        return None

    # Deduplicate by (feature, proof_id) — keep latest entry
    latest = {}
    for _key, entry in cache.items():
        if not isinstance(entry, dict):
            continue
        dedup_key = (entry.get('feature', ''), entry.get('proof_id', ''))
        existing = latest.get(dedup_key)
        if existing is None or entry.get('cached_at', '') > existing.get('cached_at', ''):
            latest[dedup_key] = entry

    strong = 0
    weak = 0
    hollow = 0
    manual = 0
    latest_ts = None

    for entry in latest.values():
        assessment = entry.get('assessment', '').upper()
        if assessment == 'STRONG':
            strong += 1
        elif assessment == 'WEAK':
            weak += 1
        elif assessment == 'HOLLOW':
            hollow += 1
        elif assessment == 'MANUAL':
            manual += 1

        ts = entry.get('cached_at')
        if ts and (latest_ts is None or ts > latest_ts):
            latest_ts = ts

    behavioral_total = strong + weak + hollow + manual
    if behavioral_total == 0:
        return None

    denominator = behavioral_total + total_no_proof_count
    integrity = round((strong + manual) / denominator * 100)
    stale = False
    if latest_ts:
        try:
            then = datetime.datetime.fromisoformat(latest_ts.replace('Z', '+00:00'))
            delta = datetime.datetime.now(datetime.timezone.utc) - then
            stale = delta.total_seconds() > 86400
        except (ValueError, TypeError):
            pass

    return {
        'integrity': integrity,
        'strong': strong,
        'weak': weak,
        'hollow': hollow,
        'manual': manual,
        'behavioral_total': behavioral_total,
        'last_audit': latest_ts,
        'last_audit_relative': _relative_time(latest_ts) if latest_ts else None,
        'stale': stale,
    }


def _build_summary_table(summary_rows, audit_summary=None):
    """Build a coverage summary table with Unicode box-drawing characters."""
    if not summary_rows:
        return []

    # Sort: FAIL first, then PARTIAL, then PASSING, then VERIFIED, then —
    def _sort_key(row):
        _name, proved, total, status = row
        priority = {"FAIL": 0, "PARTIAL": 1, "PASSING": 2, "VERIFIED": 3}.get(status, 4)
        ratio = proved / total if total else 0
        return (priority, ratio, _name)

    summary_rows = sorted(summary_rows, key=_sort_key)

    # Calculate column widths
    name_width = max(len(r[0]) for r in summary_rows)
    name_width = max(name_width, len("Feature"))

    lines = []
    lines.append(f"\u250c\u2500{'─' * name_width}\u2500\u252c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u252c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510")
    lines.append(f"\u2502 {'Feature':<{name_width}} \u2502 Coverage \u2502 Status  \u2502")
    lines.append(f"\u251c\u2500{'─' * name_width}\u2500\u253c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u253c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524")

    for name, proved, total, status in summary_rows:
        coverage = f"{proved}/{total}"
        if status == "VERIFIED":
            symbol = "VERIFIED"
        elif status == "PASSING":
            symbol = "PASSING"
        elif status == "FAIL":
            symbol = "FAIL"
        elif status == "PARTIAL":
            symbol = "PARTIAL"
        else:
            symbol = "\u2014"
        lines.append(f"\u2502 {name:<{name_width}} \u2502 {coverage:>8} \u2502 {symbol:>7} \u2502")

    lines.append(f"\u2514\u2500{'─' * name_width}\u2500\u2534\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2534\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518")

    # Summary line with optional integrity
    verified_count = sum(1 for _, _, _, s in summary_rows if s == "VERIFIED")
    total_features = len(summary_rows)
    summary_line = f"{verified_count}/{total_features} features VERIFIED"

    if audit_summary:
        pct = audit_summary['integrity']
        rel = audit_summary.get('last_audit_relative', '')
        if audit_summary.get('stale'):
            summary_line += f" | Integrity: {pct}% (last purlin:audit: {rel} \u2014 consider re-auditing)"
        else:
            summary_line += f" | Integrity: {pct}% (last purlin:audit: {rel})"
    else:
        summary_line += " | No audit data \u2014 run purlin:audit for quality assessment"

    lines.append(summary_line)
    lines.append("")  # blank line before detail

    return lines


def _read_receipt(project_root, feature_name):
    """Read a receipt JSON for a feature, or return None if not found."""
    spec_dir = os.path.join(project_root, 'specs')
    if not os.path.isdir(spec_dir):
        return None
    for path in glob.glob(os.path.join(spec_dir, '**', f'{feature_name}.receipt.json'), recursive=True):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            continue
    return None


def _check_uncommitted_specs(project_root):
    """Check for uncommitted changes to spec/proof files in specs/.

    Returns a list of status lines (e.g. ' M specs/auth/login.md') or
    an empty list if everything is clean or git is unavailable.
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain', '--', 'specs/'],
            capture_output=True, text=True, cwd=project_root
        )
        if result.returncode != 0:
            return []
    except (FileNotFoundError, OSError):
        return []

    uncommitted = []
    for line in result.stdout.splitlines():
        if not line or len(line) < 4:
            continue
        filepath = line[3:]
        if filepath.endswith('.md') or '.proofs-' in filepath:
            uncommitted.append(line)
    return uncommitted


def sync_status(project_root, role=None):
    """Generate the full sync_status report with directives."""
    features = _scan_specs(project_root)
    all_proofs = _read_proofs(project_root)

    if not features:
        return "No specs found in specs/. Run purlin:init to set up, or create specs manually."

    preamble = []

    # Check for uncommitted spec/proof changes
    uncommitted = _check_uncommitted_specs(project_root)
    if uncommitted:
        preamble.append('\u26a0 Uncommitted spec/proof changes detected:')
        for entry in uncommitted:
            preamble.append(f'  {entry}')
        preamble.append('Drift detection, staleness checks, and verification use committed state.')
        preamble.append('\u2192 Commit these files before running purlin:drift or purlin:verify')
        preamble.append('')

    # Separate anchors from regular features
    anchors = {k: v for k, v in features.items() if v['is_anchor']}
    regular = {k: v for k, v in features.items() if not v['is_anchor']}

    # Identify global anchors (auto-applied to all features)
    global_anchors = {k: v for k, v in anchors.items() if v.get('is_global')}

    summary_rows = []
    detail = []
    total_no_proof_count = 0

    # Process regular features
    for name in sorted(regular.keys()):
        info = regular[name]
        feature_lines = _report_feature(
            name, info, features, all_proofs, project_root, role, global_anchors
        )
        detail.extend(feature_lines)
        detail.append('')

        # Collect summary data (must match _report_feature's counting logic)
        rule_entries, _ = _build_coverage_rules(name, info, features, global_anchors)
        proof_by_rule = _build_proof_lookup(name, rule_entries, all_proofs)
        active_entries = [(k, l, s) for k, l, s, is_def in rule_entries if not is_def]
        active_total = len(active_entries)
        structural_rules = _classify_structural_rules(active_entries, info, features)
        total_no_proof_count += sum(
            1 for key, label, _ in active_entries
            if label == 'own'
            and key not in structural_rules
            and not proof_by_rule.get(key)
        )
        behavioral_proved = sum(1 for key, _, _ in active_entries
                                if key not in structural_rules
                                and proof_by_rule.get(key, {}).get('status') == 'pass')
        has_fail = any(proof_by_rule.get(key, {}).get('status') == 'fail'
                       for key, _, _ in active_entries
                       if key not in structural_rules)

        # READY requires a current (non-stale) receipt
        all_passing = (behavioral_proved == active_total and active_total > 0)
        receipt = _read_receipt(project_root, name)
        has_current_receipt = False
        if all_passing and receipt:
            cli_rule_entries, _ = _build_coverage_rules(name, info, features, global_anchors)
            cli_active = [(k, l, s) for k, l, s, is_def in cli_rule_entries if not is_def]
            cli_all_proofs_list = _collect_relevant_proofs(name, cli_rule_entries, all_proofs)
            cli_vhash = _compute_vhash(
                {key: True for key, _, _ in cli_active}, cli_all_proofs_list
            )
            has_current_receipt = (receipt.get('vhash') == cli_vhash)

        if has_fail:
            status = "FAIL"
        elif all_passing and has_current_receipt:
            status = "VERIFIED"
        elif all_passing:
            status = "PASSING"
        elif behavioral_proved == 0:
            status = "\u2014"
        else:
            status = "PARTIAL"

        summary_rows.append((name, behavioral_proved, active_total, status))

    # Process anchors
    for name in sorted(anchors.keys()):
        info = anchors[name]
        rule_count = len(info['rules'])
        if info.get('is_global'):
            detail.append(f"{name}: {rule_count} rules (global \u2014 auto-applied to all features)")
        else:
            detail.append(f"{name}: {rule_count} rules (apply to features with > Requires: {name})")
        for rule_id, desc in sorted(info['rules'].items()):
            detail.append(f"  {rule_id}: {desc}")
        detail.append('')

        # Include anchor in summary if it has behavioral proofs
        anchor_proofs = all_proofs.get(name, [])
        if anchor_proofs and not _is_structural_only(info.get('proof_descriptions', [])):
            deferred = info.get('deferred_rules', set())
            active_rules = set(info['rules'].keys()) - deferred
            active_total = len(active_rules)
            passed_rules = set()
            has_fail = False
            for p in anchor_proofs:
                rule = p.get('rule', '')
                if rule in active_rules:
                    if p.get('status') == 'pass':
                        passed_rules.add(rule)
                    elif p.get('status') == 'fail':
                        has_fail = True
            proved = len(passed_rules)

            # Anchors: READY requires current receipt too
            a_all_passing = (proved >= active_total and active_total > 0)
            a_receipt = _read_receipt(project_root, name)
            a_has_receipt = False
            if a_all_passing and a_receipt:
                a_vhash = _compute_vhash(
                    {r: True for r in active_rules}, anchor_proofs
                )
                a_has_receipt = (a_receipt.get('vhash') == a_vhash)

            if has_fail:
                a_status = "FAIL"
            elif a_all_passing and a_has_receipt:
                a_status = "VERIFIED"
            elif a_all_passing:
                a_status = "PASSING"
            elif proved == 0:
                a_status = "\u2014"
            else:
                a_status = "PARTIAL"

            summary_rows.append((f"{name} (anchor)", proved, active_total, a_status))

    # Read audit cache for integrity summary
    audit_summary = _read_audit_summary(project_root, total_no_proof_count)

    # Build summary table and combine output
    table_lines = _build_summary_table(summary_rows, audit_summary)

    # Report data generation (side effect)
    config = resolve_config(project_root)
    if config.get('report'):
        data_path = _write_report_data(
            project_root, features, all_proofs, config, global_anchors,
            audit_summary,
        )
        if data_path:
            html_path = os.path.join(project_root, 'purlin-report.html')
            if os.path.isfile(html_path):
                abs_html = os.path.abspath(html_path)
                preamble.append(
                    f'\u2192 Dashboard: file://{abs_html}'
                )
                preamble.append('')

    return '\n'.join(preamble + table_lines + detail).strip()


def _scopes_overlap(scope_a, scope_b):
    """Check if two scope lists have overlapping file patterns."""
    for a in scope_a:
        for b in scope_b:
            if a.startswith(b) or b.startswith(a):
                return True
    return False


def _build_coverage_rules(name, info, all_features, global_anchors=None):
    """Build combined rule entries for a feature (own + required + global).

    Returns (entries, unresolved_requires) where entries is a list of
    (key, label, source_feature, is_deferred) tuples and unresolved_requires
    is a list of names from > Requires: that don't match any known spec.
    """
    if global_anchors is None:
        global_anchors = {}

    entries = []
    unresolved_requires = []
    deferred = info.get('deferred_rules', set())
    for rule_id in sorted(info['rules'].keys()):
        entries.append((rule_id, 'own', name, rule_id in deferred))

    for req_name in info.get('requires', []):
        req_info = all_features.get(req_name)
        if req_info:
            req_deferred = req_info.get('deferred_rules', set())
            for rule_id in sorted(req_info['rules'].keys()):
                entries.append((f"{req_name}/{rule_id}", 'required', req_name, rule_id in req_deferred))
        else:
            unresolved_requires.append(req_name)

    for anchor_name in sorted(global_anchors.keys()):
        if anchor_name in info.get('requires', []):
            continue
        anchor_info = global_anchors[anchor_name]
        anchor_deferred = anchor_info.get('deferred_rules', set())
        for rule_id in sorted(anchor_info['rules'].keys()):
            entries.append((f"{anchor_name}/{rule_id}", 'global', anchor_name, rule_id in anchor_deferred))

    return entries, unresolved_requires


def _build_proof_lookup(name, rule_entries, all_proofs):
    """Build proof-by-rule lookup for a combined rule set.

    Returns dict of rule_key -> best proof entry.
    """
    all_rule_keys = {key for key, _, _, _ in rule_entries}

    proof_by_rule = {}
    # Own proofs
    for p in all_proofs.get(name, []):
        rule = p.get('rule', '')
        if rule not in proof_by_rule or p.get('status') == 'fail':
            proof_by_rule[rule] = p

    # Required/global proofs — filed under the source feature's name
    source_features = {src for _, label, src, _ in rule_entries if label != 'own'}
    for src_name in source_features:
        for p in all_proofs.get(src_name, []):
            rule = p.get('rule', '')
            key = f"{src_name}/{rule}"
            if key in all_rule_keys:
                if key not in proof_by_rule or p.get('status') == 'fail':
                    proof_by_rule[key] = p

    return proof_by_rule


def _build_all_proofs_lookup(name, rule_entries, all_proofs):
    """Build dict of rule_key -> list of ALL proof entries (not just best).

    Used by report data to show multiple proofs per rule in the dashboard.
    """
    all_rule_keys = {key for key, _, _, _ in rule_entries}
    by_rule = {}

    for p in all_proofs.get(name, []):
        rule = p.get('rule', '')
        by_rule.setdefault(rule, []).append(p)

    source_features = {src for _, label, src, _ in rule_entries if label != 'own'}
    for src_name in source_features:
        for p in all_proofs.get(src_name, []):
            rule = p.get('rule', '')
            key = f"{src_name}/{rule}"
            if key in all_rule_keys:
                by_rule.setdefault(key, []).append(p)

    return by_rule


def _collect_relevant_proofs(name, rule_entries, all_proofs):
    """Collect all proof entries relevant to the combined rule set (for vhash)."""
    all_rule_keys = {key for key, _, _, _ in rule_entries}

    proofs = list(all_proofs.get(name, []))
    source_features = {src for _, label, src, _ in rule_entries if label != 'own'}
    for src_name in source_features:
        for p in all_proofs.get(src_name, []):
            key = f"{src_name}/{p.get('rule', '')}"
            if key in all_rule_keys:
                proofs.append(p)
    return proofs


def _report_feature(name, info, all_features, all_proofs, project_root, role,
                    global_anchors=None):
    """Generate report lines for a single feature."""
    lines = []
    if global_anchors is None:
        global_anchors = {}

    # Build combined rule set (own + required + global)
    rule_entries, unresolved_requires = _build_coverage_rules(name, info, all_features, global_anchors)
    proof_by_rule = _build_proof_lookup(name, rule_entries, all_proofs)
    all_relevant_proofs = _collect_relevant_proofs(name, rule_entries, all_proofs)

    total = len(rule_entries)
    deferred_count = sum(1 for _, _, _, is_def in rule_entries if is_def)
    active_entries = [(k, l, s) for k, l, s, is_def in rule_entries if not is_def]
    active_total = len(active_entries)
    proved = sum(1 for key, _, _ in active_entries
                 if proof_by_rule.get(key, {}).get('status') == 'pass')

    # Classify each active rule as structural or behavioral
    structural_rules = _classify_structural_rules(active_entries, info, all_features)
    behavioral_proved = sum(1 for key, _, _ in active_entries
                           if key not in structural_rules
                           and proof_by_rule.get(key, {}).get('status') == 'pass')
    structural_passing = sum(1 for key, _, _ in active_entries
                            if key in structural_rules
                            and proof_by_rule.get(key, {}).get('status') == 'pass')

    # Count assumed rules (own only)
    assumed_count = len(info.get('assumed_rules', set()))

    # Format warnings (structural issues with the spec itself)
    warnings = []
    if not info['has_rules_section']:
        warnings.append("  WARNING: No ## Rules section found.")
        warnings.append(f"  → Run: purlin:spec {name}")
    elif info['unnumbered_lines']:
        warnings.append(f"  WARNING: {len(info['unnumbered_lines'])} lines under ## Rules are not numbered.")
        warnings.append('  → Fix: rewrite as "- RULE-1: ...", "- RULE-2: ...", etc.')
        warnings.append(f"  → Run: purlin:spec {name}")

    # Check visual reference staleness (computed once, used in multiple paths)
    visual_ref = info.get('visual_ref')
    visual_hash = info.get('visual_hash')
    visual_hash_changed = _check_visual_hash(project_root, visual_ref, visual_hash)

    # Check manual proofs
    manual_proofs = info.get('manual_proofs', {})

    # Header — no rules
    if total == 0:
        lines.append(f"{name}: no rules defined")
        lines.extend(warnings)
        for missing_name in unresolved_requires:
            lines.append(f'  \u26a0 Requires "{missing_name}" but no spec with that name exists')
        if visual_hash_changed:
            lines.append("  \u26a0 Visual reference image was modified since rules were extracted")
            lines.append(f"  \u2192 Run: purlin:spec {name} (re-extract rules from updated image)")
        lines.append(f"  \u2192 Run: purlin:spec {name}")
        return lines

    # Build deferred suffix for header
    deferred_suffix = f" ({deferred_count} deferred)" if deferred_count else ""

    # Header — all active rules proved
    if proved == active_total and not warnings:
        all_rules_dict = {key: True for key, _, _ in active_entries}
        vhash = _compute_vhash(all_rules_dict, all_relevant_proofs)
        receipt = _read_receipt(project_root, name)
        has_current_receipt = (receipt and receipt.get('vhash') == vhash)

        if has_current_receipt:
            header_status = "VERIFIED"
        else:
            header_status = "PASSING"

        if visual_hash_changed:
            lines.append(f"{name}: {header_status} but visual reference changed")
        else:
            lines.append(f"{name}: {header_status}")
        lines.append(f"  {proved}/{active_total} rules proved \u2713{deferred_suffix}")
        lines.append(f"  vhash={vhash}")

        if receipt and not has_current_receipt:
            receipt_rules = set(receipt.get('rules', []))
            current_rules = set(all_rules_dict.keys())
            added_rules = current_rules - receipt_rules
            removed_rules = receipt_rules - current_rules
            anchor_added = {}
            own_added = []
            for r in sorted(added_rules):
                if '/' in r:
                    src = r.split('/')[0]
                    anchor_added.setdefault(src, []).append(r.split('/')[1])
                else:
                    own_added.append(r)
            lines.append("  \u26a0 Receipt stale (vhash mismatch)")
            if anchor_added:
                for src, rules in sorted(anchor_added.items()):
                    lines.append(f"  \u26a0 Required anchor \"{src}\" changed: added {', '.join(rules)}")
            if own_added:
                lines.append(f"  \u26a0 Own rules changed since last verification")
            if removed_rules:
                lines.append(f"  \u26a0 Rules removed since last verification: {', '.join(sorted(removed_rules))}")
            if not added_rules and not removed_rules:
                lines.append("  \u26a0 Proof statuses changed since last verification")
            lines.append(f"  \u2192 Run: purlin:verify to re-issue receipt")
        elif not receipt:
            lines.append("  \u2192 Run: purlin:verify to issue receipt")

        if visual_hash_changed:
            lines.append("  \u26a0 Visual reference image was modified since rules were extracted")
            lines.append(f"  \u2192 Run: purlin:spec {name} (re-extract rules from updated image)")
        elif has_current_receipt:
            lines.append("  \u2192 No action needed.")
        if assumed_count:
            lines.append(f"  \u26a0 {assumed_count} rule{'s' if assumed_count != 1 else ''} ha{'ve' if assumed_count != 1 else 's'} (assumed) values \u2014 PM should confirm")
        for missing_name in unresolved_requires:
            lines.append(f'  \u26a0 Requires "{missing_name}" but no spec with that name exists')
        if manual_proofs and not info.get('scope'):
            lines.append("  \u26a0 Manual proof without > Scope: \u2014 staleness cannot be detected. Add > Scope: to enable stale detection.")
        _append_scope_suggestions(lines, name, info, all_features, global_anchors)
        return lines

    lines.append(f"{name}: {proved}/{active_total} rules proved{deferred_suffix}")
    lines.extend(warnings)
    if visual_hash_changed:
        lines.append("  \u26a0 Visual reference image was modified since rules were extracted")
        lines.append(f"  \u2192 Run: purlin:spec {name} (re-extract rules from updated image)")

    # Detail each rule with label
    for key, label, src_feature, is_deferred in rule_entries:
        # Deferred rules get their own status line
        if is_deferred:
            rule_desc = info['rules'].get(key, '') if label == 'own' else ''
            if not rule_desc and '/' in key:
                src_info = all_features.get(src_feature, {})
                bare_rule = key.split('/', 1)[1]
                rule_desc = src_info.get('rules', {}).get(bare_rule, '')
            # Strip the (deferred) tag from the description for display
            short_desc = _DEFERRED_TAG_RE.sub('', rule_desc).strip()
            lines.append(f"  {key}: DEFERRED ({short_desc})")
            continue

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
            lines.append(f"  \u2192 Fix: {test_name} is failing. Check the test or fix the code.")
            lines.append(f"  \u2192 Run: purlin:unit-test")
        elif manual:
            mp_id, mp_info = manual
            if mp_info.get('stamped'):
                stale = _check_manual_staleness(
                    project_root, info.get('scope', []), mp_info.get('commit_sha', '')
                )
                if stale:
                    lines.append(f"  {key}: MANUAL PROOF STALE ({mp_id}, verified {mp_info['date']}) ({label})")
                    lines.append(f"  \u2192 Re-verify and run: purlin:verify --manual {name} {mp_id}")
                else:
                    lines.append(f"  {key}: PASS ({mp_id}, manual, verified {mp_info['date']}) ({label})")
            else:
                lines.append(f"  {key}: MANUAL PROOF NEEDED ({label})")
                lines.append(f"  \u2192 Verify manually, then run: purlin:verify --manual {name} {mp_id}")
        else:
            lines.append(f"  {key}: NO PROOF ({label})")
            # Determine proof marker feature name and rule id
            if '/' in key:
                marker_feature = src_feature
                rule_id = key.split('/', 1)[1]
            else:
                marker_feature = name
                rule_id = key
            lines.append(f'  \u2192 Fix: write a test with @pytest.mark.proof("{marker_feature}", "PROOF-N", "{rule_id}")')
            src_info = all_features.get(src_feature, {})
            if src_info.get('is_anchor'):
                lines.append(f"  Note: read specs/_anchors/{src_feature}.md for exact assertion values before writing tests")
            lines.append(f"  \u2192 Run: purlin:unit-test")

    # If no proof files at all
    feature_proofs = all_proofs.get(name, [])
    if not feature_proofs and not manual_proofs and not any(
        proof_by_rule.get(key) for key, _, _ in active_entries
    ):
        lines.append(f"  \u2192 Run: purlin:unit-test")

    if assumed_count:
        lines.append(f"  \u26a0 {assumed_count} rule{'s' if assumed_count != 1 else ''} ha{'ve' if assumed_count != 1 else 's'} (assumed) values \u2014 PM should confirm")

    for missing_name in unresolved_requires:
        lines.append(f'  \u26a0 Requires "{missing_name}" but no spec with that name exists')

    if manual_proofs and not info.get('scope'):
        lines.append("  \u26a0 Manual proof without > Scope: \u2014 staleness cannot be detected. Add > Scope: to enable stale detection.")

    _append_scope_suggestions(lines, name, info, all_features, global_anchors)
    return lines


def _append_scope_suggestions(lines, name, info, all_features, global_anchors):
    """Append scope-overlap anchor suggestions to report lines."""
    feature_scope = info.get('scope', [])
    if not feature_scope:
        return

    required_names = set(info.get('requires', []))
    required_names.update(global_anchors.keys())

    for anchor_name in sorted(all_features.keys()):
        if anchor_name == name or anchor_name in required_names:
            continue
        anchor_info = all_features[anchor_name]
        if not anchor_info.get('is_anchor'):
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
# report data generation (dashboard side-effect)
# ---------------------------------------------------------------------------

def _get_plugin_docs_url():
    """Derive documentation URL from the Purlin plugin's git remote."""
    plugin_root = os.path.dirname(os.path.dirname(SCRIPT_DIR))
    try:
        r = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, cwd=plugin_root, timeout=5,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return None
        remote_url = r.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None

    # SSH: git@host:user/repo.git
    ssh_m = re.match(r'git@([^:]+):(.+?)(?:\.git)?$', remote_url)
    if ssh_m:
        host, path = ssh_m.group(1), ssh_m.group(2)
        if 'github' in host:
            return f'https://{host}/{path}/blob/main/docs/index.md'
        if 'bitbucket' in host:
            return f'https://{host}/{path}/src/main/docs/index.md'
        return f'https://{host}/{path}/docs/index.md'

    # HTTPS: https://host/user/repo.git
    https_m = re.match(r'https?://([^/]+)/(.+?)(?:\.git)?$', remote_url)
    if https_m:
        host, path = https_m.group(1), https_m.group(2)
        if 'github' in host:
            return f'https://{host}/{path}/blob/main/docs/index.md'
        if 'bitbucket' in host:
            return f'https://{host}/{path}/src/main/docs/index.md'
        return f'https://{host}/{path}/docs/index.md'

    return None


def _read_audit_cache_by_feature(project_root):
    """Read audit cache and group entries by feature name.

    Returns dict of feature_name -> list of {assessment, criterion, fix, proof_id, rule_id, priority}.
    Uses the 'feature' field that the audit skill stores in cache entries.
    Falls back to returning an empty dict if the cache doesn't exist or has no feature info.
    """
    cache_path = os.path.join(project_root, '.purlin', 'cache', 'audit_cache.json')
    if not os.path.isfile(cache_path):
        return {}
    try:
        with open(cache_path) as f:
            cache = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return {}
    if not isinstance(cache, dict):
        return {}

    # Collect all entries, deduplicating by (feature, proof_id) — keep latest
    latest = {}  # (feature, proof_id) -> entry
    for _key, entry in cache.items():
        if not isinstance(entry, dict):
            continue
        feat = entry.get('feature')
        if not feat:
            continue
        pid = entry.get('proof_id', '')
        dedup_key = (feat, pid)
        existing = latest.get(dedup_key)
        if existing is None or entry.get('cached_at', '') > existing.get('cached_at', ''):
            latest[dedup_key] = entry

    by_feature = {}
    for (_feat, _pid), entry in latest.items():
        by_feature.setdefault(_feat, []).append(entry)
    return by_feature


def _build_feature_audit(entries, no_proof_count=0):
    """Build per-feature audit data from cache entries.

    no_proof_count: number of own behavioral rules with no proof at all.
    These inflate the denominator (penalizing missing proofs) without
    affecting the numerator.
    """
    strong = 0
    weak = 0
    hollow = 0
    manual = 0
    findings = []

    for e in entries:
        assessment = e.get('assessment', '').upper()
        if assessment == 'STRONG':
            strong += 1
        elif assessment == 'WEAK':
            weak += 1
            findings.append({
                'proof_id': e.get('proof_id', ''),
                'rule_id': e.get('rule_id', ''),
                'level': 'WEAK',
                'priority': e.get('priority', 'HIGH'),
                'criterion': e.get('criterion', ''),
                'fix': e.get('fix', ''),
            })
        elif assessment == 'HOLLOW':
            hollow += 1
            findings.append({
                'proof_id': e.get('proof_id', ''),
                'rule_id': e.get('rule_id', ''),
                'level': 'HOLLOW',
                'priority': e.get('priority', 'CRITICAL'),
                'criterion': e.get('criterion', ''),
                'fix': e.get('fix', ''),
            })
        elif assessment == 'MANUAL':
            manual += 1

    behavioral_total = strong + weak + hollow + manual
    if behavioral_total == 0 and no_proof_count == 0:
        return None

    denominator = behavioral_total + no_proof_count
    if denominator == 0:
        return None

    integrity = round((strong + manual) / denominator * 100)

    # Sort findings by priority
    prio_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    findings.sort(key=lambda f: prio_order.get(f.get('priority', ''), 4))

    return {
        'integrity': integrity,
        'strong': strong,
        'weak': weak,
        'hollow': hollow,
        'manual': manual,
        'findings': findings,
    }


def _build_report_data(project_root, features, all_proofs, config, global_anchors,
                       audit_summary=None):
    """Build the structured PURLIN_DATA dict for the dashboard."""
    audit_by_feature = _read_audit_cache_by_feature(project_root)
    # Build per-proof audit lookup: (feature_name, proof_id) -> assessment
    audit_by_proof = {}
    for feat_name, entries in audit_by_feature.items():
        for e in entries:
            pid = e.get('proof_id', '')
            if pid:
                audit_by_proof[(feat_name, pid)] = e.get('assessment', '')
    feature_list = []
    summary = {'total_features': 0, 'verified': 0, 'passing': 0, 'partial': 0, 'failing': 0, 'no_proofs': 0}
    anchors_total = 0
    anchors_with_source = 0
    anchors_global = 0

    for name in sorted(features.keys()):
        info = features[name]
        is_anchor = info.get('is_anchor', False)

        if is_anchor:
            anchors_total += 1
            if info.get('source_url'):
                anchors_with_source += 1
            if info.get('is_global'):
                anchors_global += 1

        # Build combined rule set
        ga = global_anchors if not is_anchor else {}
        rule_entries, _ = _build_coverage_rules(name, info, features, ga)
        proof_by_rule = _build_proof_lookup(name, rule_entries, all_proofs)
        all_proofs_by_rule = _build_all_proofs_lookup(name, rule_entries, all_proofs)
        all_relevant_proofs = _collect_relevant_proofs(name, rule_entries, all_proofs)

        active_entries = [(k, l, s) for k, l, s, is_def in rule_entries if not is_def]
        deferred_count = sum(1 for _, _, _, d in rule_entries if d)
        active_total = len(active_entries)

        structural_rules = _classify_structural_rules(active_entries, info, features)
        proved = sum(
            1 for key, _, _ in active_entries
            if proof_by_rule.get(key, {}).get('status') == 'pass'
        )
        structural_passing = sum(
            1 for key, _, _ in active_entries
            if key in structural_rules
            and proof_by_rule.get(key, {}).get('status') == 'pass'
        )
        has_fail = any(
            proof_by_rule.get(key, {}).get('status') == 'fail'
            for key, _, _ in active_entries
        )

        # Compute vhash when all proofs pass
        vhash = None
        all_passing = (proved == active_total and active_total > 0)
        if all_passing:
            all_rules_dict = {key: True for key, _, _ in active_entries}
            vhash = _compute_vhash(all_rules_dict, all_relevant_proofs)

        # Read receipt
        receipt_data = None
        receipt = _read_receipt(project_root, name)
        if receipt:
            receipt_data = {
                'commit': receipt.get('commit', ''),
                'timestamp': receipt.get('timestamp', ''),
                'stale': receipt.get('vhash') != vhash if vhash else True,
            }

        # Determine status — READY requires a current (non-stale) receipt
        has_current_receipt = (receipt_data is not None and not receipt_data['stale'])
        if active_total == 0:
            status = 'no_proofs'
        elif has_fail:
            status = 'FAIL'
        elif all_passing and has_current_receipt:
            status = 'VERIFIED'
        elif all_passing:
            status = 'PASSING'
        elif proved > 0:
            status = 'PARTIAL'
        else:
            status = 'no_proofs'

        # Update summary for non-anchor features
        if not is_anchor:
            summary['total_features'] += 1
            if status == 'VERIFIED':
                summary['verified'] += 1
            elif status == 'PASSING':
                summary['passing'] += 1
            elif status == 'PARTIAL':
                summary['partial'] += 1
            elif status == 'FAIL':
                summary['failing'] += 1
            else:
                summary['no_proofs'] += 1

        # Build per-rule list
        rules_list = []
        for key, label, src_feature, is_deferred in rule_entries:
            if label == 'own':
                rule_desc = info['rules'].get(key, '')
            else:
                bare_rule = key.split('/', 1)[1] if '/' in key else key
                src_info = features.get(src_feature, {})
                rule_desc = src_info.get('rules', {}).get(bare_rule, '')

            # Collect ALL proofs for this rule (not just the best one)
            best_proof = proof_by_rule.get(key)
            rule_proofs = all_proofs_by_rule.get(key, [])

            # Get proof descriptions from the source spec
            if label == 'own':
                desc_by_id = info.get('proof_desc_by_id', {})
            else:
                src_info = features.get(src_feature, {})
                desc_by_id = src_info.get('proof_desc_by_id', {})

            proofs_data = []
            audit_feat = name if label == 'own' else src_feature
            for p in rule_proofs:
                pid = p.get('id', '')
                proof_audit = audit_by_proof.get((audit_feat, pid), '')
                if not proof_audit and label != 'own':
                    proof_audit = audit_by_proof.get((name, pid), '')
                proofs_data.append({
                    'id': pid,
                    'description': desc_by_id.get(pid, ''),
                    'test_file': p.get('test_file', ''),
                    'test_name': p.get('test_name', ''),
                    'tier': p.get('tier', 'unit'),
                    'status': p.get('status', ''),
                    'audit': proof_audit,
                })

            if is_deferred:
                rule_status = 'DEFERRED'
            elif key in structural_rules and best_proof and best_proof.get('status') == 'pass':
                rule_status = 'CHECK'
            elif key in structural_rules and best_proof and best_proof.get('status') == 'fail':
                rule_status = 'CHECK_FAIL'
            elif best_proof and best_proof.get('status') == 'pass':
                rule_status = 'PASS'
            elif best_proof and best_proof.get('status') == 'fail':
                rule_status = 'FAIL'
            else:
                rule_status = 'NO_PROOF'

            rules_list.append({
                'id': key,
                'description': rule_desc,
                'label': label,
                'source': src_feature if label != 'own' else None,
                'is_deferred': is_deferred,
                'is_assumed': label == 'own' and key in info.get('assumed_rules', set()),
                'status': rule_status,
                'proofs': proofs_data,
            })

        feature_list.append({
            'name': name,
            'type': 'anchor' if is_anchor else 'feature',
            'is_global': info.get('is_global', False),
            'source_url': info.get('source_url'),
            'proved': proved,
            'total': active_total,
            'deferred': deferred_count,
            'status': status,
            'structural_checks': structural_passing,
            'vhash': vhash,
            'receipt': receipt_data,
            'rules': rules_list,
            'audit': _build_feature_audit(
                audit_by_feature.get(name, []),
                no_proof_count=sum(
                    1 for key, label, _ in active_entries
                    if label == 'own'
                    and key not in structural_rules
                    and not proof_by_rule.get(key)
                ),
            ),
        })

    return {
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'project': os.path.basename(os.path.abspath(project_root)),
        'version': config.get('version', ''),
        'docs_url': _get_plugin_docs_url(),
        'summary': summary,
        'features': feature_list,
        'anchors_summary': {
            'total': anchors_total,
            'with_source': anchors_with_source,
            'global': anchors_global,
        },
        'audit_summary': audit_summary,
        'drift': None,
    }


def _write_report_data(project_root, features, all_proofs, config, global_anchors,
                       audit_summary=None):
    """Write .purlin/report-data.js for the dashboard. Returns the file path or None."""
    purlin_dir = os.path.join(project_root, '.purlin')
    if not os.path.isdir(purlin_dir):
        return None

    data = _build_report_data(
        project_root, features, all_proofs, config, global_anchors, audit_summary
    )
    data_path = os.path.join(purlin_dir, 'report-data.js')

    try:
        with open(data_path, 'w') as f:
            f.write('const PURLIN_DATA = ')
            json.dump(data, f, separators=(',', ':'))
            f.write(';\n')
        return data_path
    except (IOError, OSError):
        return None


# ---------------------------------------------------------------------------
# drift tool
# ---------------------------------------------------------------------------

_NO_IMPACT_PATTERNS = (
    'docs/', 'assets/', 'templates/', 'references/', '.gitignore', 'LICENSE',
    'CLAUDE.md', 'README.md', 'RELEASE_NOTES.md', '.mcp.json', 'settings.json',
)

_TEST_PATTERNS = ('.proofs-', 'test_', '_test.', '.test.', 'tests/', 'dev/test_')

# Directories containing behavioral definitions even when files are .md.
# Files here must NOT be caught by the .md catch-all in NO_IMPACT.
# See references/drift_criteria.md for rationale.
_BEHAVIORAL_MD_PREFIXES = ('skills/', 'agents/', '.claude/agents/')


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

    # Smart fallback: check when Purlin was initialized
    init_sha = _run_git(['log', '--diff-filter=A', '--format=%H',
                          '--follow', '--', '.purlin/config.json'])
    # Take the earliest (last line) if multiple results
    if init_sha:
        init_sha = init_sha.strip().splitlines()[-1]
        count_str = _run_git(['rev-list', '--count', f'{init_sha}..HEAD'])
        count = int(count_str) if count_str.isdigit() else 0
        if count < 30:
            return init_sha, f'since Purlin init ({count} commits)'
        # Too many commits — return recommendation instead of drift
        return None, json.dumps({
            'recommendation': 'spec-from-code',
            'reason': (f'No verification history found and {count} commits exist '
                       f'since Purlin was initialized. Drift tracks changes between '
                       f'verifications. For initial spec coverage of an existing '
                       f'codebase, use purlin:spec-from-code.'),
            'commits_since_init': count,
            'since_init_commit': init_sha,
        })

    # No .purlin in git history — count all commits on current branch
    count_str = _run_git(['rev-list', '--count', 'HEAD'])
    count = int(count_str) if count_str.isdigit() else 0
    if count < 30:
        return 'HEAD~' + str(min(count, 20)), f'last {min(count, 20)} commits (no verification or tag found)'
    return None, json.dumps({
        'recommendation': 'spec-from-code',
        'reason': (f'No verification history found and {count} commits exist. '
                   f'Drift tracks changes between verifications. For initial spec '
                   f'coverage of an existing codebase, use purlin:spec-from-code.'),
        'commits_since_init': count,
        'since_init_commit': None,
    })


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


def drift(project_root, since=None, role=None):
    """Generate structured drift data as JSON."""
    since_ref, since_desc = _resolve_since_anchor(project_root, since)

    # If ref is None, _resolve_since_anchor returned a recommendation
    if since_ref is None:
        return since_desc  # already JSON-encoded recommendation

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

        # Check scope map → CHANGED_BEHAVIOR (exact match then prefix match)
        matched_specs = scope_to_specs.get(filepath, [])
        if not matched_specs:
            for scope_path, specs in scope_to_specs.items():
                if scope_path.endswith('/') and filepath.startswith(scope_path):
                    matched_specs = specs
                    break
        if matched_specs:
            file_entries.append({
                'path': filepath,
                'category': 'CHANGED_BEHAVIOR',
                'spec': matched_specs[0],
                'diff_stat': _get_diff_stat(project_root, since_ref, filepath),
            })
            continue

        # Docs/config/assets → NO_IMPACT (but not behavioral .md dirs)
        is_behavioral_md = any(filepath.startswith(d) for d in _BEHAVIORAL_MD_PREFIXES)
        is_no_impact = any(filepath.startswith(p) or filepath == p or filepath.endswith(p)
                           for p in _NO_IMPACT_PATTERNS) and not is_behavioral_md
        is_generic_md = filepath.endswith('.md') and not is_behavioral_md
        if is_no_impact or is_generic_md:
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
    global_anchors = {
        k: v for k, v in features.items()
        if v.get('is_anchor') and v.get('is_global')
    }
    proof_status = {}
    for name, info in features.items():
        if info['is_anchor']:
            continue
        rule_entries, _ = _build_coverage_rules(name, info, features, global_anchors)
        total = len(rule_entries)
        if total == 0:
            continue
        deferred_count = sum(1 for _, _, _, is_def in rule_entries if is_def)
        active_entries = [(k, l, s) for k, l, s, is_def in rule_entries if not is_def]
        active_total = len(active_entries)
        proof_by_rule = _build_proof_lookup(name, rule_entries, all_proofs)
        proved = sum(1 for key, _, _ in active_entries
                     if proof_by_rule.get(key, {}).get('status') == 'pass')
        failing = [key for key, _, _ in active_entries
                   if proof_by_rule.get(key, {}).get('status') == 'fail']
        structural_rules = _classify_structural_rules(active_entries, info, features)
        behavioral_proved = sum(1 for key, _, _ in active_entries
                               if key not in structural_rules
                               and proof_by_rule.get(key, {}).get('status') == 'pass')
        structural_checks = sum(1 for key, _, _ in active_entries
                               if key in structural_rules
                               and proof_by_rule.get(key, {}).get('status') == 'pass')
        all_pass = (proved == active_total)
        d_receipt = _read_receipt(project_root, name)
        d_has_receipt = False
        if all_pass and d_receipt:
            d_vhash = _compute_vhash(
                {key: True for key, _, _ in active_entries},
                _collect_relevant_proofs(name, rule_entries, all_proofs),
            )
            d_has_receipt = (d_receipt.get('vhash') == d_vhash)
        status = 'VERIFIED' if all_pass and d_has_receipt else 'PASSING' if all_pass else 'FAILING' if failing else 'PARTIAL'
        assumed_count = len(info.get('assumed_rules', set()))
        entry = {
            'proved': proved,
            'total': active_total,
            'status': status,
            'failing_rules': failing,
            'structural_checks': structural_checks,
        }
        if deferred_count:
            entry['deferred'] = deferred_count
        if assumed_count:
            entry['assumed'] = assumed_count
        proof_status[name] = entry

    # Annotate file entries with behavioral gap flags
    for entry in file_entries:
        spec_name = entry.get('spec')
        if spec_name and entry['category'] == 'CHANGED_BEHAVIOR':
            ps = proof_status.get(spec_name, {})
            sc = ps.get('structural_checks', 0)
            if sc > 0 and sc == ps.get('proved', 0):
                entry['behavioral_gap'] = True

    # Build drift_flags summary (deduplicated by spec name)
    seen_drift = set()
    drift_flags = []
    for entry in file_entries:
        if entry.get('behavioral_gap') and entry['spec'] not in seen_drift:
            seen_drift.add(entry['spec'])
            drift_flags.append({
                'spec': entry['spec'],
                'reason': 'behavioral_gap_with_code_change',
                'files': [e['path'] for e in file_entries
                          if e.get('spec') == entry['spec']
                          and e.get('behavioral_gap')],
            })

    # Detect broken scopes — spec scope paths that no longer exist on disk
    broken_scopes = []
    for name, info in features.items():
        missing_paths = []
        existing_paths = []
        for scope_path in info.get('scope', []):
            full = os.path.join(project_root, scope_path)
            if scope_path.endswith('/'):
                exists = os.path.isdir(full.rstrip('/'))
            else:
                exists = os.path.exists(full)
            if exists:
                existing_paths.append(scope_path)
            else:
                missing_paths.append(scope_path)
        if missing_paths:
            broken_scopes.append({
                'spec': name,
                'missing_paths': missing_paths,
                'existing_paths': existing_paths,
            })

    result = {
        'since': since_desc,
        'commits': commits,
        'files': file_entries,
        'spec_changes': spec_changes,
        'proof_status': proof_status,
        'drift_flags': drift_flags,
        'broken_scopes': broken_scopes,
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

def _read_version():
    """Read version from VERSION file at plugin root."""
    version_path = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), 'VERSION')
    try:
        with open(version_path) as f:
            return f.read().strip()
    except (IOError, OSError):
        return '0.0.0'

PURLIN_VERSION = _read_version()

SERVER_INFO = {
    "name": "purlin",
    "version": PURLIN_VERSION,
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
        "name": "drift",
        "description": "Structured drift summary since last verification. Returns JSON with commits, categorized files, spec changes, and proof status for the purlin:drift skill to interpret.",
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

        if tool_name == 'drift':
            try:
                result_text = drift(
                    project_root,
                    since=arguments.get('since'),
                    role=arguments.get('role'),
                )
            except Exception as e:
                result_text = f"Error running drift: {e}"
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


_SERVER_MTIME = os.path.getmtime(os.path.abspath(__file__))


def main():
    """Run the MCP server on stdio."""
    global _SERVER_MTIME
    project_root = find_project_root()

    # Log startup to stderr (stdout is reserved for JSON-RPC)
    print(f"Purlin MCP server v{PURLIN_VERSION} started (root: {project_root})", file=sys.stderr)

    mod = sys.modules[__name__]
    src_path = os.path.abspath(__file__)

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

        # Hot-reload: re-import module when source file changes
        try:
            current_mtime = os.path.getmtime(src_path)
            if current_mtime != _SERVER_MTIME:
                _SERVER_MTIME = current_mtime
                import importlib
                mod = importlib.reload(mod)
                print("Purlin MCP: reloaded", file=sys.stderr)
        except Exception:
            pass

        response = mod.handle_request(request, project_root)
        if response is not None:
            sys.stdout.write(json.dumps(response) + '\n')
            sys.stdout.flush()


if __name__ == '__main__':
    main()
