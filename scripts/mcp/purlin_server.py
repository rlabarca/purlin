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
import platform
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

# A tier tag is metadata appended after the description: ` @e2e`, ` @manual(...)`.
# It must NOT match a description whose prose merely ends in an @word, e.g.
# "verify spec_format.md documents @integration, @e2e, and @windows" — which was
# read as tier=windows and had its last clause silently truncated. Requiring that
# the tag not follow a list connector (',' 'and' 'or') separates the two cases.
_TIER_TAG_BODY = r'(?<!\band)(?<!\bor)(?<!,)\s+@(\w+)(?:\(([^)]*)\))?\s*$'
_TIER_TAG_RE = re.compile(_TIER_TAG_BODY)

# A platform id becomes a proof filename, a workflow name and an environment
# variable, so the charset is what all three accept (schema_spec_format RULE-10).
_PLATFORM_ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]*$')


def _split_proof_tags(desc):
    """Split the trailing tags off a proof description.

    Returns (clean_desc, tier, platforms, warnings). Tags are read right to
    left: `@on(<platform-id>[, ...])` names the platforms the proof must be
    proved on, any other `@<name>` is the tier. At most one of each, in either
    order; a second tier tag or a second `@on` stops the scan and stays in the
    description, with a warning. `@on` alone means tier `unit`. `@on` on a
    `@manual` proof is dropped: a human stamp is not a platform result. A bare
    `@windows` tier is read as `@unit @on(windows)` with a warning naming the
    rewrite (one release of compatibility). Platform ids outside
    `[a-z0-9][a-z0-9-]*` are dropped with a warning; the survivors keep their
    order, deduplicated. `platforms` is `[]` for a platform-agnostic proof.

    The sibling module (purlin_server.py / static_checks.py) carries a
    character-identical copy of this helper and of _TIER_TAG_BODY. The two are
    independent by design: a shared import would couple the CLI to the server.
    schema_spec_format PROOF-9 keeps them in step.
    """
    desc = desc.rstrip()
    tier = None
    platforms = None
    warnings = []
    while True:
        m = _TIER_TAG_RE.search(desc)
        if not m:
            break
        name, args = m.group(1), m.group(2)
        if name == 'on':
            if platforms is not None:
                warnings.append('a second @on(...) precedes the trailing one; '
                                'only the trailing @on is read')
                break
            platforms = []
            ids = [p.strip() for p in (args or '').split(',') if p.strip()]
            if not ids:
                warnings.append('@on() names no platform: write @on(<platform-id>)')
            for pid in ids:
                if not _PLATFORM_ID_RE.match(pid):
                    warnings.append(f'platform id {pid!r} is not [a-z0-9][a-z0-9-]*; '
                                    'dropped (lower-case letters, digits and - only)')
                elif pid not in platforms:
                    platforms.append(pid)
        else:
            if tier is not None:
                warnings.append(f'a second tier tag @{name} precedes @{tier}; '
                                f'only the trailing tier tag is read')
                break
            tier = name
        desc = desc[:m.start()].rstrip()
    if tier == 'windows':
        warnings.append('@windows is a platform, not a tier: write @unit @on(windows)')
        tier = 'unit'
        if platforms is None:
            platforms = ['windows']
    if tier is None:
        tier = 'unit'
    if tier == 'manual' and platforms is not None:
        warnings.append('@on(...) on a @manual proof is ignored: '
                        'a human stamp is not a platform result')
        platforms = None
    return desc, tier, platforms or [], warnings

_PROOF_LINE_RE = re.compile(
    r'^-\s+(PROOF-\d+)\s*\((RULE-\d+(?:,\s*RULE-\d+)*)\):\s*(.+)', re.MULTILINE
)

_GLOBAL_RE = re.compile(r'^>\s*Global:\s*true\s*$', re.MULTILINE | re.IGNORECASE)
_SOURCE_RE = re.compile(r'^>\s*Source:\s*(.+)', re.MULTILINE)
_PINNED_RE = re.compile(r'^>\s*Pinned:\s*(.+)', re.MULTILINE)
_PATH_RE = re.compile(r'^>\s*Path:\s*(.+)', re.MULTILINE)
_VISUAL_REF_RE = re.compile(r'^>\s*Visual-Reference:\s*(.+)', re.MULTILINE)
_VISUAL_HASH_RE = re.compile(r'^>\s*Visual-Hash:\s*sha256:([a-f0-9]+)', re.MULTILINE)
_DESCRIPTION_RE = re.compile(r'^>\s*Description:\s*(.+)', re.MULTILINE)
_STACK_RE = re.compile(r'^>\s*Stack:\s*(.+)', re.MULTILINE)
_META_FIELD_RE = re.compile(r'^>\s*[A-Z][A-Za-z-]+:')


def _parse_description(content):
    """Parse > Description: field with multi-line continuation.

    Continuation lines start with > followed by whitespace but do not
    match a known metadata field pattern (> FieldName:).
    """
    m = _DESCRIPTION_RE.search(content)
    if not m:
        return None
    lines = [m.group(1).strip()]
    # Collect continuation lines after the match
    rest = content[m.end():]
    for line in rest.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('>') and not _META_FIELD_RE.match(stripped):
            # Continuation line — strip leading > and whitespace
            text = stripped[1:].strip()
            if text:
                lines.append(text)
        else:
            break
    result = ' '.join(lines)
    return result if result else None


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

        # Extract description from > Description: metadata field
        description = _parse_description(content)

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
        proof_tier_by_id = {}
        proof_platforms_by_id = {}
        proof_tag_warnings = []
        planned_proof_ids_by_rule = {}
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
                # Split the trailing tags (@unit, @e2e, @manual(...), @on(...))
                # off the description: tier defaults to unit, platforms to [].
                clean_desc, tier, platforms, tag_warnings = _split_proof_tags(proof_desc)
                proof_descriptions.append(proof_desc)
                proof_desc_by_id[proof_id] = clean_desc
                proof_tier_by_id[proof_id] = tier
                proof_platforms_by_id[proof_id] = platforms
                for message in tag_warnings:
                    proof_tag_warnings.append((proof_id, message))
                # Support multi-rule proofs: PROOF-8 (RULE-1, RULE-2, RULE-4)
                rule_ids = [r.strip() for r in rule_ids_raw.split(',')]
                for rule_id in rule_ids:
                    proof_desc_by_rule.setdefault(rule_id, []).append(proof_desc)
                    planned_proof_ids_by_rule.setdefault(rule_id, []).append(proof_id)
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

        # Extract pinned version and path for externally-referenced anchors
        pinned_match = _PINNED_RE.search(content)
        path_match = _PATH_RE.search(content)
        pinned = pinned_match.group(1).strip() if pinned_match else None
        source_path = path_match.group(1).strip() if path_match else None

        # Extract visual reference and hash for staleness detection
        visual_ref_match = _VISUAL_REF_RE.search(content)
        visual_hash_match = _VISUAL_HASH_RE.search(content)
        visual_ref = visual_ref_match.group(1).strip() if visual_ref_match else None
        visual_hash = visual_hash_match.group(1).strip() if visual_hash_match else None

        # Extract > Stack: metadata
        stack_match = _STACK_RE.search(content)
        stack = stack_match.group(1).strip() if stack_match else None

        # Derive category from the spec's parent directory under specs/
        # e.g. specs/skills/skill_anchor.md -> "skills", specs/_anchors/foo.md -> "_anchors"
        _parts = rel_path.split(os.sep)
        category = _parts[1] if len(_parts) >= 3 else ''

        features[feature_name] = {
            'path': rel_path,
            'category': category,
            'rules': rules,
            'deferred_rules': deferred_rules,
            'assumed_rules': assumed_rules,
            'requires': requires,
            'scope': scope,
            'is_anchor': is_anchor,
            'is_global': is_global,
            'source_url': source_url,
            'pinned': pinned,
            'source_path': source_path,
            'unnumbered_lines': unnumbered,
            'has_rules_section': rules_section is not None,
            'manual_proofs': manual_proofs,
            'proof_descriptions': proof_descriptions,
            'proof_desc_by_rule': proof_desc_by_rule,
            'proof_desc_by_id': proof_desc_by_id,
            'proof_tier_by_id': proof_tier_by_id,
            'proof_platforms_by_id': proof_platforms_by_id,
            'proof_tag_warnings': proof_tag_warnings,
            'planned_proof_ids_by_rule': planned_proof_ids_by_rule,
            'visual_ref': visual_ref,
            'visual_hash': visual_hash,
            'description': description,
            'stack': stack,
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


def _get_rule_proof_descs(key, label, src_feature, info, all_features):
    """Get proof descriptions for a rule from its source spec."""
    if label == 'own':
        return info.get('proof_desc_by_rule', {}).get(key, [])
    bare_rule = key.split('/', 1)[1] if '/' in key else key
    src_info = all_features.get(src_feature, {})
    return src_info.get('proof_desc_by_rule', {}).get(bare_rule, [])


def _get_rule_planned_proof_ids(key, label, src_feature, info, all_features):
    """Get the PROOF ids the spec declares for a rule, in declaration order."""
    if label == 'own':
        return info.get('planned_proof_ids_by_rule', {}).get(key, [])
    bare_rule = key.split('/', 1)[1] if '/' in key else key
    src_info = all_features.get(src_feature, {})
    return src_info.get('planned_proof_ids_by_rule', {}).get(bare_rule, [])


def _scope_files_exist(project_root, info):
    """True when at least one file named in the spec's `> Scope:` exists on disk.

    Distinguishes "the spec is written but nothing is built" from "code exists but
    has no tests". The two states need different next steps, and nothing in the
    report could tell them apart. A spec with no `> Scope:` is treated as built,
    since there is nothing to look for.
    """
    scope = info.get('scope_files') or info.get('scope') or []
    if isinstance(scope, str):
        scope = [p.strip() for p in scope.split(',') if p.strip()]
    if not scope:
        return True
    for rel in scope:
        if glob.glob(os.path.join(project_root, rel), recursive=True):
            return True
    return False


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


def _dedup_cache_entries(cache):
    """Deduplicate cache entries by (feature, proof_id), keeping the latest.

    Shared by the audit-cache and design-cache readers. Previously each reader
    carried its own copy of this loop, which is how they could drift.
    """
    latest = {}
    if not isinstance(cache, dict):
        return latest
    for _key, entry in cache.items():
        if not isinstance(entry, dict):
            continue
        dedup_key = (entry.get('feature', ''), entry.get('proof_id', ''))
        existing = latest.get(dedup_key)
        if existing is None or entry.get('cached_at', '') > existing.get('cached_at', ''):
            latest[dedup_key] = entry
    return latest


def _is_stale(latest_ts, max_age_seconds=86400):
    """True when the newest assessment is older than max_age (default 24h).

    Shared by both gauge readers. Design carried no staleness flag at all, so a
    project graded a year ago was indistinguishable from one graded this morning.
    """
    if not latest_ts:
        return False
    try:
        then = datetime.datetime.fromisoformat(latest_ts.replace('Z', '+00:00'))
        return (datetime.datetime.now(datetime.timezone.utc) - then
                ).total_seconds() > max_age_seconds
    except (ValueError, TypeError):
        return False


def _compute_design(provable, loose, unprovable):
    """Compute the Proof Design percentage from graded-description counts.

    Design = PROVABLE / (PROVABLE + LOOSE + UNPROVABLE) x 100. STRUCTURAL
    descriptions are excluded from both numerator and denominator, mirroring how
    EXCLUDED proofs are excluded from Proof Integrity.
    Returns (rounded percentage, denominator), or (None, 0) if nothing is gradeable.
    """
    gradeable = provable + loose + unprovable
    if gradeable == 0:
        return None, 0
    return round(provable / gradeable * 100), gradeable


def _compute_integrity(strong, weak, hollow, manual):
    """Compute integrity percentage from assessment counts.

    Integrity = (STRONG + MANUAL) / (STRONG + WEAK + HOLLOW + MANUAL) × 100.
    Measures proof quality only — NONE rules are excluded.
    Returns rounded integer percentage, or None if no behavioral proofs.
    """
    behavioral_total = strong + weak + hollow + manual
    if behavioral_total == 0:
        return None, 0
    return round((strong + manual) / behavioral_total * 100), behavioral_total


def _determine_status(proved, active_total, has_fail, has_current_receipt):
    """Determine feature status from coverage and receipt state.

    Returns one of: VERIFIED, PASSING, FAILING, PARTIAL, UNTESTED.
    """
    if active_total == 0:
        return 'UNTESTED'
    if has_fail:
        return 'FAILING'
    if proved == active_total and has_current_receipt:
        return 'VERIFIED'
    if proved == active_total:
        return 'PASSING'
    if proved > 0:
        return 'PARTIAL'
    return 'UNTESTED'


def _read_audit_summary(project_root):
    """Read audit cache and compute project-wide integrity summary.

    Integrity = (STRONG + MANUAL) / behavioral_total — measures proof quality
    only. Coverage (proved/total rules) is a separate metric.
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

    # Deduplicate via the shared helper. This function used to carry its own
    # copy of the loop, which is exactly the drift _dedup_cache_entries exists
    # to prevent.
    latest = _dedup_cache_entries(cache)

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

    integrity, behavioral_total = _compute_integrity(strong, weak, hollow, manual)
    if integrity is None:
        return None

    stale = _is_stale(latest_ts)

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


def _read_design_summary(project_root):
    """Read the design cache and compute the project-wide Proof Design summary.

    Design grades proof DESCRIPTIONS, so this is meaningful with no tests in the
    project at all — which is the point. Returns None if no design cache exists.
    """
    cache_path = os.path.join(project_root, '.purlin', 'cache', 'design_cache.json')
    if not os.path.isfile(cache_path):
        return None
    try:
        with open(cache_path) as f:
            cache = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return None
    if not isinstance(cache, dict) or not cache:
        return None

    provable = loose = unprovable = structural = 0
    latest_ts = None
    for entry in _dedup_cache_entries(cache).values():
        level = entry.get('assessment', '').upper()
        if level == 'PROVABLE':
            provable += 1
        elif level == 'LOOSE':
            loose += 1
        elif level == 'UNPROVABLE':
            unprovable += 1
        elif level == 'STRUCTURAL':
            structural += 1
        ts = entry.get('cached_at')
        if ts and (latest_ts is None or ts > latest_ts):
            latest_ts = ts

    design, gradeable = _compute_design(provable, loose, unprovable)
    if design is None:
        return None

    return {
        'design': design,
        'provable': provable,
        'loose': loose,
        'unprovable': unprovable,
        'structural': structural,
        'gradeable_total': gradeable,
        'last_design_audit': latest_ts,
        'last_design_audit_relative': _relative_time(latest_ts) if latest_ts else None,
        'stale': _is_stale(latest_ts),
    }


def _count_cache_entries(project_root, cache_name):
    """Count deduplicated entries in a quality cache. 0 when absent."""
    cache_path = os.path.join(project_root, '.purlin', 'cache', cache_name)
    if not os.path.isfile(cache_path):
        return 0
    try:
        with open(cache_path, encoding='utf-8') as f:
            cache = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return 0
    return len(_dedup_cache_entries(cache))


def _attach_gauge_coverage(project_root, features, all_proofs,
                           audit_summary, design_summary):
    """Give each gauge summary its denominator, and weight its headline by it.

    A percentage with no denominator is the first defect this closes: 100%
    Integrity computed from 24 cached assessments over a repo of ~560 executed
    proofs rendered identically to 100% over all of them.

    Stating the denominator was not enough. The headline still read 100% while
    39 of 40 feature rows read `not audited`, a roll-up contradicting every row
    beneath it. So the reported figure is weighted by measurement coverage:

        weighted = passing / (gradeable + unmeasured)

    An unassessed item is unknown, not passing, so it sits in the denominator
    until someone looks at it. An item excluded from scoring (STRUCTURAL for
    Design, EXCLUDED for Integrity) stays out of both, because that is a correct
    terminal state rather than an unknown. When coverage is complete `unmeasured`
    is 0 and `weighted` equals the assessed score exactly, so the gauge does not
    change meaning as it fills in.

    `assessed` keeps the unweighted score for context. It is the number the
    formulas in references/audit_criteria.md, skills/audit/SKILL.md and
    sync_status RULE-29/33/43 define, and the per-feature gauges keep using it:
    a feature is either fully assessed, where the two agree, or it reads
    `not audited`.

    Integrity's population is every executed proof; Design's is every declared
    proof description, because a description is gradeable with nothing built.
    """
    executed_total = sum(len(entries) for entries in all_proofs.values())
    declared_total = sum(
        len(ids)
        for info in features.values()
        for ids in info.get('planned_proof_ids_by_rule', {}).values()
    )

    for summary, cache_name, total, key, gradeable_key, passing_keys in (
        (audit_summary, 'audit_cache.json', executed_total,
         'integrity', 'behavioral_total', ('strong', 'manual')),
        (design_summary, 'design_cache.json', declared_total,
         'design', 'gradeable_total', ('provable',)),
    ):
        if summary is None:
            continue
        measured = _count_cache_entries(project_root, cache_name)
        summary['coverage'] = {
            'measured': measured,
            'total': total,
            'complete': total > 0 and measured >= total,
        }

        assessed = summary.get(key)
        summary['assessed'] = assessed
        unmeasured = max(total - measured, 0)
        gradeable = summary.get(gradeable_key) or 0
        denom = gradeable + unmeasured
        passing = sum(summary.get(k) or 0 for k in passing_keys)
        summary['weighted'] = round(passing / denom * 100) if denom else assessed


# Tiers that cannot execute on an arbitrary developer machine: they need a
# specific runner. A proof declaring one of these is not missing when it has no
# result here, it is waiting, and the two must not report identically. Adding a
# tier name here also requires adding it to the closed tier set in
# specs/_anchors/schema_proof_format.md RULE-4 and the check that enforces it in
# dev/test_schema_proof_format.py.
_RUNNER_GATED_TIERS = frozenset({'windows'})


def _runner_gated_proofs(info):
    """{proof_id: tier} for this spec's proofs that declare a runner-gated tier.

    Since the tag grammar gained `@on(...)` (schema_spec_format RULE-9), a bare
    `@windows` parses as tier `unit` with platforms `['windows']`, and an
    explicit `@unit @on(windows)` reads the same. Until the platform registry
    replaces this mechanism, a unit-tier proof whose platforms name a gated
    tier is gated under that name, so the awaiting/provenance surfaces and the
    `proofs-windows.json` result file keep working unchanged.
    """
    platforms_by_id = info.get('proof_platforms_by_id') or {}
    gated = {}
    for pid, tier in (info.get('proof_tier_by_id') or {}).items():
        if tier in _RUNNER_GATED_TIERS:
            gated[pid] = tier
            continue
        if tier == 'unit':
            for platform in platforms_by_id.get(pid) or []:
                if platform in _RUNNER_GATED_TIERS:
                    gated[pid] = platform
                    break
    return gated


def _awaiting_runner(name, info, all_proofs):
    """Declared runner-gated proofs with no executed result in their own tier.

    Keyed on (proof id, tier) rather than proof id alone: a proof declared
    @windows is satisfied only by a windows-tier result, so an entry for the
    same id at another tier does not count. Returns [(proof_id, tier)] sorted.
    """
    gated = _runner_gated_proofs(info)
    if not gated:
        return []
    executed = {(e.get('id'), e.get('tier')) for e in all_proofs.get(name, [])}
    return sorted((pid, tier) for pid, tier in gated.items()
                  if (pid, tier) not in executed)


def _runner_provenance(project_root, spec_path, feature, tier):
    """When a runner-gated tier file was last committed, and by which runner.

    Proof entries deliberately carry no timestamp: that is what makes the CI
    workflow's `git diff --cached --quiet` guard idempotent. So provenance is
    read back out of git instead of stored in the file, with the runner taken
    from the commit's `Purlin-Runner:` trailer. Zero new fields.
    """
    # spec_path is already project-relative and git runs with cwd=project_root,
    # so relativizing again would resolve against the process cwd instead.
    rel = os.path.join(os.path.dirname(spec_path), f'{feature}.proofs-{tier}.json')
    try:
        out = subprocess.run(
            ['git', 'log', '-1', '--format=%cI%x00%(trailers:key=Purlin-Runner,valueonly)',
             '--', rel],
            cwd=project_root, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    when, _, runner = out.stdout.strip().partition('\x00')
    return {'when': when.strip(), 'runner': runner.strip() or None}


def _gauge_token(gauge, which):
    """Render one feature's gauge for the text table.

    Uses the same tokens as the dashboard so the two surfaces cannot disagree
    about what a blank would have meant. The unscorable word comes from that
    gauge's own vocabulary: STRUCTURAL describes a description, EXCLUDED
    describes a test, and the two never mix (sync_status RULE-18).
    """
    if not gauge:
        return 'not audited'
    pct = gauge.get('design') if which == 'design' else gauge.get('integrity')
    if pct is not None:
        return f'{pct}%'
    if gauge.get('state') == 'excluded':
        return 'structural' if which == 'design' else 'excluded'
    return 'not audited'


def _refresh_command(audit_summary, design_summary):
    """The narrowest purlin:audit invocation that refreshes what is stale.

    Design grading is deterministic and needs no test code; Integrity grading
    needs tests and costs LLM calls. Sending someone to a full audit to refresh
    Design alone spends budget for nothing (sync_status RULE-45).
    """
    d_stale = not design_summary or design_summary.get('stale')
    a_stale = not audit_summary or audit_summary.get('stale')
    if d_stale and a_stale:
        return 'purlin:audit'
    return 'purlin:audit --design' if d_stale else 'purlin:audit --integrity'


def _gauge_headline(summary, which):
    """The figure a surface reports for a gauge: coverage-weighted, not assessed.

    `_attach_gauge_coverage` computes `weighted`. Falling back to the assessed
    score keeps this safe for a summary dict that never passed through there.
    """
    if not summary:
        return None
    weighted = summary.get('weighted')
    if weighted is not None:
        return weighted
    return summary.get('design' if which == 'design' else 'integrity')


def _gauge_suffix(summary, which, audit_summary, design_summary):
    """` (N of M measured, <age>)` for one gauge, from its own timestamp.

    A percentage printed with no denominator is what let 100% over 15 of 608
    assessments read as a project-wide result. And each age comes from that
    gauge's own cache: one shared "last audit" figure reported the Integrity
    cache's age as though it were the whole project's.
    """
    if not summary:
        return ''
    parts = []
    cov = summary.get('coverage')
    if cov and not cov.get('complete'):
        parts.append(f"{cov['measured']} of {cov['total']} measured")
        # Name the unweighted score too. Without it a weighted 2% is
        # indistinguishable from 2% of assessed proofs being STRONG, which is a
        # different problem with a different fix.
        assessed = summary.get('assessed')
        if assessed is not None and assessed != _gauge_headline(summary, which):
            parts.append(f"{assessed}% of those assessed")
    rel = summary.get('last_design_audit_relative' if which == 'design'
                      else 'last_audit_relative')
    if rel:
        parts.append(rel)
    if summary.get('stale'):
        parts.append(f"run {_refresh_command(audit_summary, design_summary)}")
    if not parts:
        return ''
    return " (" + ", ".join(parts) + ")"


_REMOTE_VERIFICATION_MODES = ('required', 'optional', 'off')


# ---------------------------------------------------------------------------
# Platform registry and host detection (sync_status RULE-50/51)
# ---------------------------------------------------------------------------

# The three family ids every project has with zero config. A config entry of
# the same id replaces the built-in, which is how a project attaches a runner
# to `windows` without inventing a second id for the same platform.
_BUILTIN_PLATFORMS = {
    'windows': {'os': 'windows'},
    'macos': {'os': 'macos'},
    'linux': {'os': 'linux'},
}
_PLATFORM_OS_VALUES = ('windows', 'macos', 'linux')
# Named so the rejection can say "not yet supported" rather than "unknown":
# the extension point exists, the support does not.
_PLATFORM_OS_RESERVED = ('ios', 'android')
_ARCH_ALIASES = {
    'x86_64': 'x86_64', 'amd64': 'x86_64', 'x64': 'x86_64',
    'arm64': 'arm64', 'aarch64': 'arm64',
}
_PLATFORM_VERSION_RE = re.compile(r'^(>=)?(\d+(?:\.\d+)*)$')
_PLATFORM_ENTRY_KEYS = ('os', 'version', 'distro', 'arch', 'runner', 'label')
_PLATFORM_RUNNER_KEYS = ('provider', 'runs_on', 'workflow')


def _normalise_arch(value):
    """Canonical `x86_64` / `arm64`, or None when the alias is unknown."""
    if not isinstance(value, str):
        return None
    return _ARCH_ALIASES.get(value.strip().lower())


def _validate_platform_entry(pid, entry):
    """Return (normalised_entry, error) for one `platforms` entry.

    Every problem is an error and the entry is dropped, including an unknown
    key: a typo like `vresion` must not vanish into an entry that then
    matches every host of its family.
    """
    if not _PLATFORM_ID_RE.match(pid):
        return None, f'{pid}: id must match [a-z0-9][a-z0-9-]*'
    if not isinstance(entry, dict):
        return None, f'{pid}: entry must be an object'
    unknown = sorted(k for k in entry if k not in _PLATFORM_ENTRY_KEYS)
    if unknown:
        return None, (f'{pid}: unknown key {unknown[0]!r} '
                      f'(allowed: {", ".join(_PLATFORM_ENTRY_KEYS)})')
    os_name = entry.get('os')
    if not isinstance(os_name, str) or not os_name:
        return None, f'{pid}: "os" is required (one of {", ".join(_PLATFORM_OS_VALUES)})'
    if os_name in _PLATFORM_OS_RESERVED:
        return None, f'{pid}: os {os_name!r} is not yet supported'
    if os_name not in _PLATFORM_OS_VALUES:
        return None, f'{pid}: os {os_name!r} must be one of {", ".join(_PLATFORM_OS_VALUES)}'
    out = {'_id': pid, 'os': os_name}

    version = entry.get('version')
    if version is not None:
        if not isinstance(version, str) or not _PLATFORM_VERSION_RE.match(version.strip()):
            return None, f'{pid}: version {version!r} must be N[.N...] or >=N[.N...]'
        out['version'] = version.strip()

    distro = entry.get('distro')
    if distro is not None:
        if not isinstance(distro, str) or not distro:
            return None, f'{pid}: distro must be a non-empty string'
        if os_name != 'linux':
            return None, f'{pid}: distro is only valid when os is linux'
        out['distro'] = distro

    arch = entry.get('arch')
    if arch is not None:
        norm = _normalise_arch(arch)
        if norm is None:
            return None, (f'{pid}: arch {arch!r} must be one of '
                          f'{", ".join(sorted(_ARCH_ALIASES))}')
        out['arch'] = norm

    runner = entry.get('runner')
    if runner is not None:
        if not isinstance(runner, dict):
            return None, f'{pid}: runner must be an object'
        bad = sorted(k for k in runner if k not in _PLATFORM_RUNNER_KEYS)
        if bad:
            return None, (f'{pid}: runner has unknown key {bad[0]!r} '
                          f'(allowed: {", ".join(_PLATFORM_RUNNER_KEYS)})')
        provider = runner.get('provider')
        if not isinstance(provider, str) or not provider:
            return None, f'{pid}: runner.provider is required'
        for key in ('runs_on', 'workflow'):
            if key in runner and not isinstance(runner[key], str):
                return None, f'{pid}: runner.{key} must be a string'
        out['runner'] = dict(runner)

    label = entry.get('label')
    if label is not None:
        if not isinstance(label, str):
            return None, f'{pid}: label must be a string'
        out['label'] = label
    return out, None


def _platform_registry(config):
    """(registry, errors): built-in family ids overlaid by config `platforms`.

    A config entry replaces the built-in of the same id. A malformed entry is
    dropped and named in `errors` (id and problem); the built-in it would have
    replaced stays, so `@on(windows)` keeps resolving while the preamble says
    what was ignored. Every entry carries `_id`.
    """
    registry = {pid: dict(entry, _id=pid) for pid, entry in _BUILTIN_PLATFORMS.items()}
    errors = []
    declared = (config or {}).get('platforms')
    if declared is None:
        return registry, errors
    if not isinstance(declared, dict):
        errors.append('platforms: must be an object mapping ids to entries')
        return registry, errors
    for pid, entry in declared.items():
        pid = str(pid)
        normalised, error = _validate_platform_entry(pid, entry)
        if error:
            errors.append(error)
            continue
        registry[pid] = normalised
    return registry, errors


def _detect_host_platform():
    """{os, version, distro, arch, id} for the machine sync_status runs on.

    `id` is `PURLIN_PLATFORM` when set, which is how a runner (or a developer
    on a pinned machine) claims a registry id that detection alone cannot
    prove, such as `windows-2022` versus any other Windows 10 build.
    """
    system = platform.system()
    family = {'Darwin': 'macos', 'Windows': 'windows', 'Linux': 'linux'}.get(
        system, (system or '').lower())
    version = ''
    distro = ''
    if family == 'macos':
        version = platform.mac_ver()[0] or ''
    elif family == 'windows':
        version = platform.win32_ver()[1] or ''
    elif family == 'linux':
        try:
            release = platform.freedesktop_os_release()
        except (AttributeError, OSError):
            release = {}
        distro = release.get('ID', '') or ''
        version = release.get('VERSION_ID', '') or ''
    machine = platform.machine() or ''
    return {
        'os': family,
        'version': version,
        'distro': distro,
        'arch': _normalise_arch(machine) or machine.lower(),
        'id': os.environ.get('PURLIN_PLATFORM') or None,
    }


def _version_tuple(text):
    """Leading dotted integers of a version string, or None when none lead."""
    m = re.match(r'(\d+(?:\.\d+)*)', (text or '').strip())
    if not m:
        return None
    return tuple(int(part) for part in m.group(1).split('.'))


def _version_satisfies(constraint, actual):
    """Two forms only. `14` is a prefix: `14` matches `14.7.1`, `14.7` does not
    match `14.8`. `>=N[.N...]` compares component-wise, shorter side padded
    with zeros. No constraint always holds; any constraint fails against an
    unknown host version, because "unknown" is not "new enough".
    """
    if constraint is None:
        return True
    actual_t = _version_tuple(actual)
    if actual_t is None:
        return False
    constraint = constraint.strip()
    if constraint.startswith('>='):
        want = _version_tuple(constraint[2:])
        if want is None:
            return False
        width = max(len(want), len(actual_t))
        pad = lambda t: t + (0,) * (width - len(t))
        return pad(actual_t) >= pad(want)
    want = _version_tuple(constraint)
    if want is None:
        return False
    return actual_t[:len(want)] == want


def _platform_satisfied_by_host(platform_def, host):
    """True when this host can prove a proof declared on `platform_def`.

    `PURLIN_PLATFORM` equal to the entry's id short-circuits: the runner
    asserts what it is. Otherwise os must match, distro and arch must match
    whenever the entry names them, and the version constraint must hold. A
    family entry with only `os` is satisfied by any host of that family.
    """
    host = host or {}
    if host.get('id') and host['id'] == platform_def.get('_id'):
        return True
    if platform_def.get('os') != host.get('os'):
        return False
    if platform_def.get('distro') and platform_def['distro'] != host.get('distro'):
        return False
    if platform_def.get('arch') and platform_def['arch'] != host.get('arch'):
        return False
    return _version_satisfies(platform_def.get('version'), host.get('version') or '')


def _host_platform_ids(registry, host):
    """Sorted registry ids this host satisfies."""
    return sorted(pid for pid, entry in registry.items()
                  if _platform_satisfied_by_host(entry, host))


def _remote_verification_line(config, awaiting_count):
    """The project's declared remote-verification mode, or '' when silent.

    Two things this line must not do. It must not present the field as the
    gate: `.purlin/config.json` is a file in the tree the agent can edit, and
    `docs/regulated-environments.md` requires policy to live outside the repo.
    The field declares the mode; branch protection marking the gate job a
    required check is what enforces it, and both halves are said together
    (sync_status RULE-49).

    And it must not swallow a typo. A mode outside the three is named as
    unrecognized rather than falling back to `off`, because a silent fallback
    would disable the declaration invisibly.
    """
    mode = config.get('remote_verification', 'off')
    declared = " Declared in config; enforcement is branch protection marking the verify-gate job a required check"

    if mode not in _REMOTE_VERIFICATION_MODES:
        return (f"Remote verification: {mode!r} is not a recognized mode "
                f"(" + " | ".join(_REMOTE_VERIFICATION_MODES) + ")")
    if mode == 'required':
        return ("Remote verification: required — runner-gated proofs must be proved "
                "before a merge." + declared)
    if mode == 'optional':
        return ("Remote verification: optional — the remote loop is available and "
                "reported; findings never block." + declared)
    # off: silent unless something is actually waiting. Keyed on awaiting
    # rather than on declared, because a project whose runner-gated proofs
    # were already proved elsewhere has nothing stuck, and telling it those
    # proofs "will stay AWAITING RUNNER" would be false.
    if not awaiting_count:
        return ''
    n = awaiting_count
    return (f"Remote verification: off — {n} proof{'s' if n != 1 else ''} "
            f"awaiting a runner will stay that way. "
            f"→ Run: purlin:test to set up a runner")


def _build_summary_table(summary_rows, audit_summary=None, design_summary=None,
                         gauges_by_feature=None, config=None, awaiting_count=0):
    """Build a coverage summary table with Unicode box-drawing characters."""
    if not summary_rows:
        return []

    # Sort: FAILING first, then PARTIAL, then PASSING, then VERIFIED, then UNTESTED
    def _sort_key(row):
        _name, proved, total, status = row
        priority = {"FAILING": 0, "PARTIAL": 1, "PASSING": 2, "VERIFIED": 3, "UNTESTED": 4}.get(status, 5)
        ratio = proved / total if total else 0
        return (priority, ratio, _name)

    summary_rows = sorted(summary_rows, key=_sort_key)
    gauges_by_feature = gauges_by_feature or {}

    # Calculate column widths
    name_width = max(len(r[0]) for r in summary_rows)
    name_width = max(name_width, len("Feature"))

    # The longest status word is 8 characters (UNTESTED, VERIFIED). The column was
    # ruled for 9 and padded to 7, so those two overflowed the right border by one —
    # and a spec-only project is 100% UNTESTED, which misaligned every single row.
    status_width = max(len(s) for s in
                       ("VERIFIED", "PASSING", "FAILING", "PARTIAL", "UNTESTED", "Status"))
    # Both gauges share a width, ruled for the longest token ("unmeasured") so a
    # row cannot overflow its border the way UNTESTED once did.
    gauge_width = max(len('not audited'), len('structural'), len('Integrity'))
    cov_rule = '\u2500' * 10
    status_rule = '\u2500' * (status_width + 2)
    gauge_rule = '\u2500' * (gauge_width + 2)

    lines = []
    lines.append(f"\u250c\u2500{'─' * name_width}\u2500\u252c{cov_rule}\u252c{status_rule}\u252c{gauge_rule}\u252c{gauge_rule}\u2510")
    lines.append(f"\u2502 {'Feature':<{name_width}} \u2502 Coverage \u2502 {'Status':<{status_width}} \u2502 {'Design':>{gauge_width}} \u2502 {'Integrity':>{gauge_width}} \u2502")
    lines.append(f"\u251c\u2500{'─' * name_width}\u2500\u253c{cov_rule}\u253c{status_rule}\u253c{gauge_rule}\u253c{gauge_rule}\u2524")

    for name, proved, total, status in summary_rows:
        coverage = f"{proved}/{total}"
        if status == "VERIFIED":
            symbol = "VERIFIED"
        elif status == "PASSING":
            symbol = "PASSING"
        elif status == "FAILING":
            symbol = "FAILING"
        elif status == "PARTIAL":
            symbol = "PARTIAL"
        else:
            symbol = "UNTESTED"
        # Anchors are labelled "<name> (anchor)" in the row; the gauge lookup
        # keys on the bare feature name.
        bare = name.split(' (', 1)[0]
        g = gauges_by_feature.get(bare, {})
        design_tok = _gauge_token(g.get('design'), 'design')
        integrity_tok = _gauge_token(g.get('audit'), 'integrity')
        lines.append(
            f"\u2502 {name:<{name_width}} \u2502 {coverage:>8} \u2502 {symbol:>{status_width}} "
            f"\u2502 {design_tok:>{gauge_width}} \u2502 {integrity_tok:>{gauge_width}} \u2502")

    lines.append(f"\u2514\u2500{'─' * name_width}\u2500\u2534{cov_rule}\u2534{status_rule}\u2534{gauge_rule}\u2534{gauge_rule}\u2518")

    # Summary line with optional integrity
    verified_count = sum(1 for _, _, _, s in summary_rows if s == "VERIFIED")
    total_features = len(summary_rows)
    summary_line = f"{verified_count}/{total_features} features VERIFIED"

    # Design first: a high Integrity score over LOOSE descriptions measures an
    # unfalsifiable spec, so the gauge that bounds the other is reported first.
    if design_summary:
        summary_line += (f" | Proof Design: {_gauge_headline(design_summary, 'design')}%"
                         + _gauge_suffix(design_summary, 'design',
                                         audit_summary, design_summary))
    else:
        # No design cache. Say so rather than dropping the gauge: an omitted
        # label is indistinguishable from a reporter that forgot to print it.
        summary_line += " | Proof Design: not measured"

    if audit_summary:
        summary_line += (f" | Proof Integrity: {_gauge_headline(audit_summary, 'integrity')}%"
                         + _gauge_suffix(audit_summary, 'integrity',
                                         audit_summary, design_summary))
    else:
        # No audit cache. Distinguish "nothing has been tested yet" from "tests
        # exist but were never audited" — reporting them identically made a
        # deliberate spec-first project look like a neglected one. summary_rows
        # carries (name, coverage_str, _, status); UNTESTED everywhere means no
        # proof has executed at all.
        all_untested = bool(summary_rows) and all(
            row[3] == 'UNTESTED' for row in summary_rows)
        if all_untested:
            summary_line += " | Proof Integrity: no tests yet \u2014 run purlin:audit for Proof Design"
        else:
            summary_line += " | No audit data \u2014 run purlin:audit for quality assessment"

    lines.append(summary_line)

    # The declared remote-verification mode, on its own line rather than
    # appended: the summary line is already carrying two gauges with their own
    # denominators and ages, and the declaration/enforcement split needs a
    # clause of its own to be readable at all.
    rv_line = _remote_verification_line(config or {}, awaiting_count)
    if rv_line:
        lines.append(rv_line)

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


def _check_legacy_mcp_entry(project_root):
    """Detect a legacy version-pinned purlin entry in the project's .mcp.json.

    Pre-0.9.4 purlin:init wrote a purlin server entry with an absolute path
    into the versioned plugin cache. Project-scope .mcp.json shadows the
    plugin-bundled server, so the entry silently pins the project to an old
    plugin version. Dev checkouts (paths outside the plugin cache) are exempt.

    Returns the pinned path string, or None when no legacy entry exists.
    """
    mcp_path = os.path.join(project_root, '.mcp.json')
    if not os.path.isfile(mcp_path):
        return None
    try:
        with open(mcp_path, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return None
    entry = data.get('mcpServers', {}).get('purlin')
    if not isinstance(entry, dict):
        return None
    candidates = [entry.get('command', '')] + list(entry.get('args', []))
    for value in candidates:
        if isinstance(value, str) and '.claude/plugins/cache/' in value:
            return value
    return None


def sync_status(project_root, role=None):
    """Generate the full sync_status report with directives."""
    features = _scan_specs(project_root)
    all_proofs = _read_proofs(project_root)

    if not features:
        return "No specs found in specs/. Run purlin:init to set up, or create specs manually."

    preamble = []

    # Config is read before the preamble and kept for the summary block: the
    # platform registry (RULE-50) reports its rejected entries up here, and the
    # summary reports the declared remote-verification mode (RULE-49).
    config = resolve_config(project_root)
    registry, registry_errors = _platform_registry(config)

    # Warn about a legacy version-pinned MCP entry (shadows the plugin-bundled server)
    legacy_mcp = _check_legacy_mcp_entry(project_root)
    if legacy_mcp:
        preamble.append('⚠ Legacy MCP config: .mcp.json pins purlin to a plugin-cache path:')
        preamble.append(f'  {legacy_mcp}')
        preamble.append('This entry shadows the plugin-bundled MCP server and stays on the old version after plugin updates.')
        preamble.append('→ Run: purlin:init --mcp (then /reload-plugins)')
        preamble.append('')

    # Check for uncommitted spec/proof changes
    uncommitted = _check_uncommitted_specs(project_root)
    if uncommitted:
        preamble.append('\u26a0 Uncommitted spec/proof changes detected:')
        for entry in uncommitted:
            preamble.append(f'  {entry}')
        preamble.append('Drift detection, staleness checks, and verification use committed state.')
        preamble.append('\u2192 Commit these files before running purlin:drift or purlin:verify')
        preamble.append('')

    # Malformed `platforms` entries are dropped from the registry, never
    # silently: a typo that vanished would leave a proof matching every host
    # of its family. Named here so the fix is one edit away.
    if registry_errors:
        n = len(registry_errors)
        preamble.append(f'\u26a0 Platform registry: {n} entr{"ies" if n != 1 else "y"} ignored:')
        for error in registry_errors:
            preamble.append(f'  {error}')
        preamble.append('\u2192 Fix: edit "platforms" in .purlin/config.json')
        preamble.append('')

    # Separate anchors from regular features
    anchors = {k: v for k, v in features.items() if v['is_anchor']}
    regular = {k: v for k, v in features.items() if not v['is_anchor']}

    # Identify global anchors (auto-applied to all features)
    global_anchors = {k: v for k, v in anchors.items() if v.get('is_global')}

    summary_rows = []
    detail = []

    # Process regular features
    # Per-feature gauges for the table's two quality columns. Same readers the
    # dashboard uses, so the CLI and the dashboard cannot disagree.
    audit_by_feature = _read_audit_cache_by_feature(project_root)
    design_by_feature = _read_audit_cache_by_feature(project_root, 'design_cache.json')
    populations = _feature_populations(features, all_proofs)
    gauges_by_feature = {
        name: {
            'audit': _build_feature_audit(audit_by_feature.get(name, []),
                                          populations.get(name, {}).get('audit')),
            'design': _build_feature_design(design_by_feature.get(name, []),
                                            populations.get(name, {}).get('design')),
        }
        for name in features
    }

    for name in sorted(regular.keys()):
        info = regular[name]
        feature_lines = _report_feature(
            name, info, features, all_proofs, project_root, role, global_anchors,
            gauges=gauges_by_feature.get(name), registry=registry,
        )
        detail.extend(feature_lines)
        detail.append('')

        # Same counting as the detail report, from the one helper both use.
        rule_entries, _ = _build_coverage_rules(name, info, features, global_anchors)
        proof_by_rule = _build_proof_lookup(name, rule_entries, all_proofs)
        active_entries, _awaiting, _gated = _active_rule_entries(
            name, info, rule_entries, all_proofs)
        active_total = len(active_entries)
        proved = sum(1 for key, _, _ in active_entries
                     if proof_by_rule.get(key, {}).get('status') == 'pass')
        has_fail = any(proof_by_rule.get(key, {}).get('status') == 'fail'
                       for key, _, _ in active_entries)

        all_proved_passing = (proved == active_total and active_total > 0)
        receipt = _read_receipt(project_root, name)
        has_current_receipt = False
        if all_proved_passing and receipt:
            cli_rule_entries, _ = _build_coverage_rules(name, info, features, global_anchors)
            cli_active, _, _ = _active_rule_entries(
                name, info, cli_rule_entries, all_proofs)
            cli_all_proofs_list = _collect_relevant_proofs(name, cli_rule_entries, all_proofs)
            cli_vhash = _compute_vhash(
                {key: True for key, _, _ in cli_active}, cli_all_proofs_list
            )
            has_current_receipt = (receipt.get('vhash') == cli_vhash)

        status = _determine_status(proved, active_total, has_fail, has_current_receipt)

        summary_rows.append((name, proved, active_total, status))

    # Process anchors
    for name in sorted(anchors.keys()):
        info = anchors[name]
        rule_count = len(info['rules'])
        if info.get('is_global'):
            detail.append(f"{name}: {rule_count} rules (global \u2014 auto-applied to all features)")
        else:
            detail.append(f"{name}: {rule_count} rules (apply to features with > Requires: {name})")
        # Show external reference info with staleness check
        if info.get('source_url'):
            detail.append(f"  Source: {info['source_url']}")
            if info.get('source_path'):
                detail.append(f"  Path: {info['source_path']}")
            if info.get('pinned'):
                pinned_val = info['pinned']
                pinned_display = pinned_val[:7] if len(pinned_val) > 10 else pinned_val
                staleness = _check_git_staleness(info['source_url'], pinned_val, project_root)
                if staleness and staleness['status'] == 'stale':
                    remote_short = staleness['remote_sha'][:7] if staleness.get('remote_sha') else '?'
                    detail.append(f"  Pinned: {pinned_display} \u26a0 STALE \u2014 remote is {remote_short}. Run: purlin:anchor sync {name}")
                elif staleness and staleness['status'] == 'error':
                    detail.append(f"  Pinned: {pinned_display} (source unreachable)")
                else:
                    detail.append(f"  Pinned: {pinned_display} (current)")
            else:
                detail.append(f"  \u26a0 Unpinned \u2014 run: purlin:anchor sync {name}")
        for rule_id, desc in sorted(info['rules'].items()):
            detail.append(f"  {rule_id}: {desc}")
        detail.append('')

        # Include anchor in summary if it has proofs
        anchor_proofs = all_proofs.get(name, [])
        if anchor_proofs:
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

            a_all_proved_passing = (proved >= active_total and active_total > 0)
            a_receipt = _read_receipt(project_root, name)
            a_has_receipt = False
            if a_all_proved_passing and a_receipt:
                a_vhash = _compute_vhash(
                    {r: True for r in active_rules}, anchor_proofs
                )
                a_has_receipt = (a_receipt.get('vhash') == a_vhash)

            a_status = _determine_status(proved, active_total, has_fail, a_has_receipt)

            summary_rows.append((f"{name} (anchor)", proved, active_total, a_status))

    # Read both quality gauges. Design needs no tests, so it is meaningful even
    # when the audit cache is absent.
    audit_summary = _read_audit_summary(project_root)
    design_summary = _read_design_summary(project_root)
    _attach_gauge_coverage(project_root, features, all_proofs,
                           audit_summary, design_summary)

    # `config` was resolved above the preamble; the summary block reports the
    # declared remote-verification mode (RULE-49), so the table builder needs it.
    awaiting_count = sum(
        len(_awaiting_runner(name, info, all_proofs))
        for name, info in features.items()
    )

    # Build summary table and combine output
    table_lines = _build_summary_table(summary_rows, audit_summary, design_summary,
                                       gauges_by_feature, config, awaiting_count)

    # Report data generation (side effect)
    if config.get('report'):
        data_path = _write_report_data(
            project_root, features, all_proofs, config, global_anchors,
            audit_summary, design_summary=design_summary,
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


def _gauge_directives(name, gauges):
    """Next steps for a fully covered feature, driven by its quality gauges.

    Coverage is the only hard gate, so a feature with every rule proved used to
    report "No action needed." however hollow its tests or however unfalsifiable
    its proof descriptions. The directive layer was blind to both gauges.

    Design is addressed before Integrity on purpose: most Integrity criteria
    compare a test against its proof description, so a LOOSE description leaves
    them nothing to catch and a high Integrity score over one measures an
    unfalsifiable spec rather than good tests (sync_status RULE-44).
    """
    gauges = gauges or {}
    design = gauges.get('design') or {}
    audit = gauges.get('audit') or {}
    out = []

    d_find = design.get('findings') or []
    if d_find:
        ids = ', '.join(f.get('proof_id', '?') for f in d_find[:3])
        more = f" (+{len(d_find) - 3} more)" if len(d_find) > 3 else ''
        out.append(f"  \u26a0 Proof Design: {len(d_find)} description"
                   f"{'s' if len(d_find) != 1 else ''} not PROVABLE \u2014 {ids}{more}")
        out.append(f"  \u2192 Run: purlin:spec {name} (the proof description is the artifact at fault)")

    a_find = audit.get('findings') or []
    if a_find:
        ids = ', '.join(f.get('proof_id', '?') for f in a_find[:3])
        more = f" (+{len(a_find) - 3} more)" if len(a_find) > 3 else ''
        out.append(f"  \u26a0 Proof Integrity: {len(a_find)} proof"
                   f"{'s' if len(a_find) != 1 else ''} WEAK or HOLLOW \u2014 {ids}{more}")
        out.append(f"  \u2192 Run: purlin:build {name} (only test code moves Integrity)")

    if not out:
        unmeasured = [label for label, g in (('Design', design), ('Integrity', audit))
                      if g.get('state') == 'unmeasured']
        if unmeasured:
            out.append(f"  \u26a0 Proof {' and Proof '.join(unmeasured)} not measured")
            flag = ' --design' if unmeasured == ['Design'] else ''
            out.append(f"  \u2192 Run: purlin:audit{flag} {name}")
        else:
            out.append("  \u2192 No action needed.")
    return out


def _runner_lines(project_root, name, info, all_proofs, awaiting, awaiting_rule_count):
    """Report runner-gated proofs: what is waiting, and what a runner already proved.

    A proof declaring @windows that has never run reported nothing at all. Its
    rule read PASS off a local proof, so the dashboard, the summary line and the
    receipt were all silent about a platform the project claims to support. That
    silence is the defect; the fix is a distinct AWAITING RUNNER signal that does
    not count against coverage and does not block a receipt.
    """
    out = []
    if awaiting:
        by_tier = {}
        for pid, tier in awaiting:
            by_tier.setdefault(tier, []).append(pid)
        for tier in sorted(by_tier):
            ids = ', '.join(by_tier[tier])
            n = len(by_tier[tier])
            out.append(f"  \u26a0 AWAITING RUNNER: {n} proof{'s' if n != 1 else ''} "
                       f"declared @{tier} with no result \u2014 {ids}")
        if awaiting_rule_count:
            out.append(f"  \u2192 {awaiting_rule_count} rule"
                       f"{'s' if awaiting_rule_count != 1 else ''} left the coverage "
                       f"denominator: every declared proof needs a runner")
        out.append("  \u2192 Run: purlin:test \u2014 it dispatches a runner for that tier "
                   "and pulls back the proofs it commits. Not a failure and not a blocker")

    # What a runner did prove, and when. Read from git rather than the proof
    # file, which carries no timestamp on purpose.
    proved_tiers = sorted(
        {tier for tier in _runner_gated_proofs(info).values()} -
        {tier for _, tier in awaiting}
    )
    for tier in proved_tiers:
        prov = _runner_provenance(project_root, info['path'], name, tier)
        if not prov:
            continue
        when = _relative_time(prov['when']) if prov.get('when') else 'unknown'
        runner = prov.get('runner') or 'runner not recorded'
        out.append(f"  \u2713 @{tier} proved remotely {when} ({runner})")
    return out


def _active_rule_entries(name, info, rule_entries, all_proofs):
    """The rules that count toward coverage, and why the others do not.

    Four surfaces computed this independently: the detail report, the summary
    table (whose comment read "must match _report_feature's counting logic"),
    the dashboard payload and the digest. They drifted the moment
    awaiting-runner rules were introduced, so the table said 1/2 PARTIAL while
    the detail beneath it said 1/1 PASSING. One definition, four callers.

    Excluded: DEFERRED rules, and rules whose every declared proof is
    runner-gated and unproved. A required anchor rule is never excluded on
    runner grounds, because it is proved under the anchor's own feature name.

    Returns (active_entries, awaiting, awaiting_rule_count).
    """
    awaiting = _awaiting_runner(name, info, all_proofs)
    awaiting_rules = set()
    if awaiting:
        awaiting_ids = {pid for pid, _ in awaiting}
        for rule_id, pids in (info.get('planned_proof_ids_by_rule') or {}).items():
            if pids and set(pids) <= awaiting_ids:
                awaiting_rules.add(rule_id)

    active, gated = [], 0
    for key, label, src, is_deferred in rule_entries:
        if is_deferred:
            continue
        if label == 'own' and key in awaiting_rules:
            gated += 1
            continue
        active.append((key, label, src))
    return active, awaiting, gated


def _report_feature(name, info, all_features, all_proofs, project_root, role,
                    global_anchors=None, gauges=None, registry=None):
    """Generate report lines for a single feature."""
    lines = []
    if global_anchors is None:
        global_anchors = {}
    if registry is None:
        registry, _ = _platform_registry({})

    # Build combined rule set (own + required + global)
    rule_entries, unresolved_requires = _build_coverage_rules(name, info, all_features, global_anchors)
    proof_by_rule = _build_proof_lookup(name, rule_entries, all_proofs)
    all_relevant_proofs = _collect_relevant_proofs(name, rule_entries, all_proofs)

    total = len(rule_entries)
    deferred_count = sum(1 for _, _, _, is_def in rule_entries if is_def)

    # Runner-gated proofs waiting for their runner. A rule whose only declared
    # proofs are runner-gated is not unproved, it is unprovable here, so it
    # leaves the coverage denominator the way a DEFERRED rule does. Warn, never
    # block: a missing Windows runner must not turn a green repo red.
    active_entries, awaiting, awaiting_rule_count = _active_rule_entries(
        name, info, rule_entries, all_proofs)
    active_total = len(active_entries)
    proved = sum(1 for key, _, _ in active_entries
                 if proof_by_rule.get(key, {}).get('status') == 'pass')

    all_proved_passing = (proved == active_total and active_total > 0)

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
    advisories = []
    # Tag grammar problems on individual proof lines (schema_spec_format
    # RULE-9/10). Printed with the structural warnings but kept out of the
    # verdict: a legacy `@windows` alias must not demote a PASSING feature.
    for proof_id, message in info.get('proof_tag_warnings') or []:
        advisories.append(f"  WARNING: {proof_id}: {message}")
    # A platform id no registry entry and no family carries (RULE-50). Also an
    # advisory: the proof is declared on a platform nobody can be, which is a
    # config gap to name, not a failing feature.
    known_platforms = set(registry) | set(_BUILTIN_PLATFORMS)
    unknown_platforms = []
    for proof_id, platforms in sorted(
            (info.get('proof_platforms_by_id') or {}).items(),
            key=lambda item: int(re.sub(r'\D', '', item[0]) or 0)):
        for pid in platforms:
            if pid not in known_platforms:
                unknown_platforms.append((proof_id, pid))
    for proof_id, pid in unknown_platforms:
        advisories.append(
            f'  WARNING: {proof_id} names platform "{pid}", which is not in '
            f'.purlin/config.json platforms and is not a family id '
            f'({", ".join(_BUILTIN_PLATFORMS)})')
    if unknown_platforms:
        advisories.append('  \u2192 Fix: add it under platforms, or use a family id')

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
        lines.extend(advisories)
        for missing_name in unresolved_requires:
            lines.append(f'  \u26a0 Requires "{missing_name}" but no spec with that name exists')
        if visual_hash_changed:
            lines.append("  \u26a0 Visual reference image was modified since rules were extracted")
            lines.append(f"  \u2192 Run: purlin:spec {name} (re-extract rules from updated image)")
        lines.append(f"  \u2192 Run: purlin:spec {name}")
        return lines

    # Build deferred suffix for header
    deferred_suffix = f" ({deferred_count} deferred)" if deferred_count else ""

    # Header — all rules proved
    if all_proved_passing and not warnings:
        all_rules_dict = {key: True for key, _, _ in active_entries}
        vhash = _compute_vhash(all_rules_dict, all_relevant_proofs)
        receipt = _read_receipt(project_root, name)
        has_current_receipt = (
            proved == active_total
            and receipt is not None
            and receipt.get('vhash') == vhash
        )

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
        lines.extend(_runner_lines(project_root, name, info, all_proofs,
                                   awaiting, awaiting_rule_count))

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
            lines.extend(_gauge_directives(name, gauges))
        if assumed_count:
            lines.append(f"  \u26a0 {assumed_count} rule{'s' if assumed_count != 1 else ''} ha{'ve' if assumed_count != 1 else 's'} (assumed) values \u2014 PM should confirm")
        for missing_name in unresolved_requires:
            lines.append(f'  \u26a0 Requires "{missing_name}" but no spec with that name exists')
        if manual_proofs and not info.get('scope'):
            lines.append("  \u26a0 Manual proof without > Scope: \u2014 staleness cannot be detected. Add > Scope: to enable stale detection.")
        _append_scope_suggestions(lines, name, info, all_features, global_anchors)
        lines.extend(advisories)
        return lines

    lines.append(f"{name}: {proved}/{active_total} rules proved{deferred_suffix}")
    lines.extend(warnings)
    lines.extend(advisories)
    lines.extend(_runner_lines(project_root, name, info, all_proofs,
                               awaiting, awaiting_rule_count))
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
            lines.append(f"  \u2192 Run: purlin:test")
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

            # Surface what the spec already planned for this rule. A spec-first
            # project has written real proof descriptions and real PROOF ids; the
            # report used to show neither, printing the literal string "PROOF-N"
            # and discarding the descriptions entirely.
            src_info = all_features.get(src_feature, {})
            planned_ids = _get_rule_planned_proof_ids(
                key, label, src_feature, info, all_features)
            planned_descs = _get_rule_proof_descs(
                key, label, src_feature, info, all_features)
            for pid, desc in zip(planned_ids, planned_descs):
                lines.append(f"     planned {pid}: {desc}")

            marker_id = planned_ids[0] if planned_ids else 'PROOF-N'
            lines.append(f'  \u2192 Fix: write a test with @pytest.mark.proof("{marker_feature}", "{marker_id}", "{rule_id}")')
            if src_info.get('is_anchor'):
                lines.append(f"  Note: read specs/_anchors/{src_feature}.md for exact assertion values before writing tests")

            # Route by what exists. purlin:build appeared nowhere in this file, so
            # nothing could send a user into the build loop: a spec with no code was
            # told to run purlin:test, which collects no tests.
            if not _scope_files_exist(project_root, info):
                lines.append(f"  \u2192 Run: purlin:build {name}")
            else:
                lines.append(f"  \u2192 Run: purlin:test")

    # If no proof files at all. The per-rule branch above already emits a directive
    # for every uncovered rule, so repeating it here just duplicated the line; emit
    # it only when there were no rules to report against.
    feature_proofs = all_proofs.get(name, [])
    if not feature_proofs and not manual_proofs and not active_entries:
        if _scope_files_exist(project_root, info):
            lines.append(f"  \u2192 Run: purlin:test")
        else:
            lines.append(f"  \u2192 Run: purlin:build {name}")

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


def _read_audit_cache_by_feature(project_root, cache_name='audit_cache.json'):
    """Read a quality cache and group entries by feature name.

    Returns dict of feature_name -> list of {assessment, criterion, fix, proof_id, rule_id, priority}.
    Uses the 'feature' field that the audit skill stores in cache entries.
    Falls back to returning an empty dict if the cache doesn't exist or has no feature info.

    The audit and design caches are shape-identical (same nine fields, level in
    `assessment`), so one reader serves both, parameterized the way
    static_checks.read_audit_cache already is.
    """
    cache_path = os.path.join(project_root, '.purlin', 'cache', cache_name)
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


def _build_feature_audit(entries, total=None):
    """Build per-feature audit data from cache entries.

    Integrity = (STRONG + MANUAL) / behavioral_total — measures proof quality
    only. Coverage (proved/total rules) is a separate metric.
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

    integrity, behavioral_total = _compute_integrity(strong, weak, hollow, manual)

    # Sort findings by priority
    prio_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    findings.sort(key=lambda f: prio_order.get(f.get('priority', ''), 4))

    return {
        'integrity': integrity,
        'strong': strong,
        'weak': weak,
        'hollow': hollow,
        'manual': manual,
        'behavioral_total': behavioral_total,
        'state': _gauge_state(entries, integrity, total),
        'coverage': _feature_coverage(entries, total),
        'findings': findings,
    }


def _gauge_state(entries, pct, total=None):
    """Classify a feature's gauge as measured / excluded / unmeasured.

    Returning None for anything unscorable collapsed two different facts into
    one blank cell: a feature whose every proof is legitimately EXCLUDED (or
    every description STRUCTURAL) looked identical to one nobody has audited.

    `excluded` is a strong claim — nothing here is gradeable — so it requires
    that every one of the feature's proofs has actually been assessed. Without
    that check, skill_audit read `excluded` off 2 assessments that both happened
    to be EXCLUDED while its other 18 executed proofs had never been looked at.
    A partially assessed feature is `unmeasured`: the answer is not known yet.
    """
    if pct is not None:
        return 'measured'
    if not entries:
        return 'unmeasured'
    if total is not None and len(entries) < total:
        return 'unmeasured'
    return 'excluded'


def _feature_populations(features, all_proofs):
    """Per feature, the population each gauge could assess.

    Integrity is scored over executed proofs; Design over declared proof
    descriptions, which is why Design is measurable with nothing built. Without
    these totals a per-feature gauge cannot tell "fully assessed, nothing
    gradeable" from "two of twenty assessed and both happened to be excluded".
    """
    pops = {}
    for name, info in features.items():
        declared = sum(len(ids) for ids in
                       info.get('planned_proof_ids_by_rule', {}).values())
        pops[name] = {
            'audit': len(all_proofs.get(name, [])),
            'design': declared,
        }
    return pops


def _feature_coverage(entries, total):
    """How much of one feature's population this gauge actually assessed.

    The project summaries carry this; per-feature gauges did not, which is why
    a row could assert "nothing gradeable" over a small audited subset.
    """
    measured = len(entries)
    if total is None:
        return {'measured': measured, 'total': None, 'complete': None}
    return {'measured': measured, 'total': total,
            'complete': total > 0 and measured >= total}


def _build_feature_design(entries, total=None):
    """Build per-feature Proof Design data from design-cache entries.

    Mirrors _build_feature_audit: Design = PROVABLE / (PROVABLE + LOOSE +
    UNPROVABLE), with STRUCTURAL excluded from both numerator and denominator
    exactly as EXCLUDED is excluded from Integrity.
    """
    provable = loose = unprovable = structural = 0
    findings = []

    for e in entries:
        level = e.get('assessment', '').upper()
        if level == 'PROVABLE':
            provable += 1
        elif level == 'STRUCTURAL':
            structural += 1
        elif level in ('LOOSE', 'UNPROVABLE'):
            if level == 'LOOSE':
                loose += 1
                default_priority = 'MEDIUM'
            else:
                unprovable += 1
                default_priority = 'HIGH'
            findings.append({
                'proof_id': e.get('proof_id', ''),
                'rule_id': e.get('rule_id', ''),
                'level': level,
                'priority': e.get('priority', default_priority),
                'criterion': e.get('criterion', ''),
                'fix': e.get('fix', ''),
            })

    design, gradeable_total = _compute_design(provable, loose, unprovable)

    prio_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    findings.sort(key=lambda f: prio_order.get(f.get('priority', ''), 4))

    return {
        'design': design,
        'provable': provable,
        'loose': loose,
        'unprovable': unprovable,
        'structural': structural,
        'gradeable_total': gradeable_total,
        'state': _gauge_state(entries, design, total),
        'coverage': _feature_coverage(entries, total),
        'findings': findings,
    }


def _check_uncommitted_all(project_root):
    """Return list of all uncommitted (non-ignored) files in the project."""
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True, text=True, cwd=project_root
        )
        if result.returncode != 0:
            return []
    except (FileNotFoundError, OSError):
        return []
    files = []
    for line in result.stdout.splitlines():
        if not line or len(line) < 4:
            continue
        files.append(line.strip())
    return files


def _build_report_data(project_root, features, all_proofs, config, global_anchors,
                       audit_summary=None, design_summary=None):
    """Build the structured PURLIN_DATA dict for the dashboard."""
    audit_by_feature = _read_audit_cache_by_feature(project_root)
    # Read the design cache here rather than accepting it as a parameter. A
    # defaulted parameter is what let generate_digest silently blank the Design
    # gauge (report_data RULE-24); reading from the cache inside the builder
    # makes both entry points correct by construction.
    design_by_feature = _read_audit_cache_by_feature(project_root, 'design_cache.json')
    populations = _feature_populations(features, all_proofs)
    # Build per-proof audit lookup: (feature_name, proof_id) -> assessment
    audit_by_proof = {}
    for feat_name, entries in audit_by_feature.items():
        for e in entries:
            pid = e.get('proof_id', '')
            if pid:
                audit_by_proof[(feat_name, pid)] = e.get('assessment', '')
    feature_list = []
    summary = {'total_features': 0, 'verified': 0, 'passing': 0, 'partial': 0, 'failing': 0, 'untested': 0}
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

        active_entries, awaiting_runner, awaiting_rule_count = _active_rule_entries(
            name, info, rule_entries, all_proofs)
        deferred_count = sum(1 for _, _, _, d in rule_entries if d)
        active_total = len(active_entries)

        has_fail = any(
            proof_by_rule.get(key, {}).get('status') == 'fail'
            for key, _, _ in active_entries
        )

        # Compute vhash when ALL proofs pass
        proved = sum(
            1 for key, _, _ in active_entries
            if proof_by_rule.get(key, {}).get('status') == 'pass'
        )
        vhash = None
        all_proved_passing = (proved == active_total and active_total > 0)
        if all_proved_passing:
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

        # Determine status
        has_current_receipt = (receipt_data is not None and not receipt_data['stale'])
        status = _determine_status(proved, active_total, has_fail, has_current_receipt)

        # Update summary for non-anchor features
        if not is_anchor:
            summary['total_features'] += 1
            if status == 'VERIFIED':
                summary['verified'] += 1
            elif status == 'PASSING':
                summary['passing'] += 1
            elif status == 'PARTIAL':
                summary['partial'] += 1
            elif status == 'FAILING':
                summary['failing'] += 1
            else:
                summary['untested'] += 1

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
                src_info = info
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

            # Planned proofs: spec PROOF-N entries with no executed result.
            # Display-only — never affects proved/total, vhash, or status.
            bare_rule = key.split('/', 1)[1] if '/' in key else key
            executed_ids = {p['id'] for p in proofs_data}
            tier_by_id = src_info.get('proof_tier_by_id', {})
            for pid in src_info.get('planned_proof_ids_by_rule', {}).get(bare_rule, []):
                if pid in executed_ids:
                    continue
                proofs_data.append({
                    'id': pid,
                    'description': desc_by_id.get(pid, ''),
                    'test_file': '',
                    'test_name': '',
                    'tier': tier_by_id.get(pid, 'unit'),
                    'status': 'planned',
                    'audit': '',
                })

            if is_deferred:
                rule_status = 'DEFERRED'
            elif best_proof and best_proof.get('status') == 'pass':
                rule_status = 'PASS'
            elif best_proof and best_proof.get('status') == 'fail':
                rule_status = 'FAIL'
            else:
                rule_status = 'NONE'

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

        # Check external anchor staleness for report data
        ext_status = None
        if is_anchor and info.get('source_url'):
            staleness = _check_git_staleness(
                info['source_url'], info.get('pinned'), project_root
            )
            if staleness:
                ext_status = staleness.get('status')

        feature_list.append({
            'name': name,
            'category': info.get('category', ''),
            'type': 'anchor' if is_anchor else 'feature',
            'is_global': info.get('is_global', False),
            'source_url': info.get('source_url'),
            'pinned': info.get('pinned'),
            'description': info.get('description'),
            'source_path': info.get('source_path'),
            'stack': info.get('stack'),
            'ext_status': ext_status,
            'proved': proved,
            'total': active_total,
            'deferred': deferred_count,
            # Proofs declared at a runner-gated tier with no result there. The
            # coverage fraction above already excludes the rules they are the
            # only proof for, so without this the dashboard would show a clean
            # 1/1 and never say a platform is unproven (sync_status RULE-47).
            'awaiting_runner': [{'id': pid, 'tier': tier} for pid, tier in awaiting_runner],
            'status': status,
            'vhash': vhash,
            'receipt': receipt_data,
            'rules': rules_list,
            'audit': _build_feature_audit(audit_by_feature.get(name, []),
                                          populations.get(name, {}).get('audit')),
            'design': _build_feature_design(design_by_feature.get(name, []),
                                            populations.get(name, {}).get('design')),
        })

    uncommitted_files = _check_uncommitted_all(project_root)

    return {
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'project': os.path.basename(os.path.abspath(project_root)),
        'version': config.get('version', ''),
        # Always present, defaulted here rather than at each reader. The CI gate
        # (scripts/ci/verify_gate.py) decides its exit code from this payload, and
        # a gate that cannot tell "mode absent" from "older payload" cannot fail
        # closed on the difference (report_data RULE-30).
        'remote_verification': config.get('remote_verification', 'off'),
        'docs_url': _get_plugin_docs_url(),
        'summary': summary,
        'features': feature_list,
        'anchors_summary': {
            'total': anchors_total,
            'with_source': anchors_with_source,
            'global': anchors_global,
        },
        'audit_summary': audit_summary,
        'design_summary': design_summary,
        'drift': None,
        'uncommitted': uncommitted_files,
    }


def read_report_payload(project_root):
    """Assemble the structured status payload without writing anything.

    `_write_report_data` is the writing path; this is the reading one. The CI
    gate (`scripts/ci/verify_gate.py`) needs exactly the payload the dashboard
    gets and must not touch the tree to get it (verify_gate RULE-5), so it
    calls this rather than re-implementing the assembly or parsing the
    rendered summary table. Returns None when the directory is not a readable
    Purlin project, which the gate turns into a bad-invocation exit.
    """
    config = resolve_config(project_root)
    if not config:
        return None
    features = _scan_specs(project_root)
    if not features:
        return None
    all_proofs = _read_proofs(project_root)
    global_anchors = {
        k: v for k, v in features.items()
        if v.get('is_anchor') and v.get('is_global')
    }
    audit_summary = _read_audit_summary(project_root)
    design_summary = _read_design_summary(project_root)
    _attach_gauge_coverage(project_root, features, all_proofs,
                           audit_summary, design_summary)
    return _build_report_data(
        project_root, features, all_proofs, config, global_anchors,
        audit_summary, design_summary=design_summary,
    )


def _write_report_data(project_root, features, all_proofs, config, global_anchors,
                       audit_summary=None, drift_data=None, git_sha=None,
                       design_summary=None):
    """Write .purlin/report-data.js for the dashboard. Returns the file path or None."""
    purlin_dir = os.path.join(project_root, '.purlin')
    if not os.path.isdir(purlin_dir):
        return None

    data = _build_report_data(
        project_root, features, all_proofs, config, global_anchors, audit_summary,
        design_summary=design_summary,
    )
    if drift_data is not None:
        data['drift'] = drift_data
    if git_sha:
        data['git_sha'] = git_sha
    data_path = os.path.join(purlin_dir, 'report-data.js')

    tmp_path = data_path + '.tmp'
    try:
        with open(tmp_path, 'w') as f:
            f.write('const PURLIN_DATA = ')
            json.dump(data, f, separators=(',', ':'))
            f.write(';\n')
        os.replace(tmp_path, data_path)
        return data_path
    except (IOError, OSError):
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
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
            if line.startswith('+++') or line.startswith('---'):
                continue
            if line.startswith('+') or line.startswith('-'):
                content = line[1:]
                m = _RULE_RE.search(content)
                if m:
                    rule_id = m.group(1)
                    if line.startswith('+'):
                        new_rules.append(rule_id)
                    else:
                        removed_rules.append(rule_id)

        changes.append({
            'spec': feature_name,
            'new_rules': new_rules,
            'removed_rules': removed_rules,
        })
    return changes


def _check_git_staleness(source_url, pinned, project_root=None):
    """Compare pinned SHA to remote HEAD for git-sourced anchors.

    Returns None for non-git URLs. Otherwise returns a dict:
      {'status': 'current'|'stale'|'unpinned'|'error', 'remote_sha': str|None}
    """
    if not source_url:
        return None
    is_git = (source_url.startswith('git@') or source_url.endswith('.git')
              or 'github.com' in source_url or 'gitlab.com' in source_url
              or source_url.startswith('/') or source_url.startswith('.'))
    if not is_git:
        return None
    if not pinned:
        return {'status': 'unpinned', 'remote_sha': None}
    try:
        result = subprocess.run(
            ['git', 'ls-remote', source_url, 'HEAD'],
            capture_output=True, text=True, timeout=10,
            cwd=project_root or '.',
        )
        if result.returncode != 0:
            return {'status': 'error', 'remote_sha': None,
                    'error': result.stderr.strip()[:200]}
        lines = result.stdout.strip().splitlines()
        if not lines:
            return {'status': 'error', 'remote_sha': None,
                    'error': 'No HEAD ref returned'}
        remote_sha = lines[0].split('\t')[0]
        if remote_sha.startswith(pinned) or pinned.startswith(remote_sha):
            return {'status': 'current', 'remote_sha': remote_sha}
        return {'status': 'stale', 'remote_sha': remote_sha}
    except subprocess.TimeoutExpired:
        return {'status': 'error', 'remote_sha': None, 'error': 'Timeout reaching remote'}
    except (subprocess.SubprocessError, OSError) as e:
        return {'status': 'error', 'remote_sha': None, 'error': str(e)[:200]}


def _compute_drift(project_root, since=None):
    """Compute drift data as a Python dict.

    Returns a dict with drift results, or a dict with 'recommendation' key
    if no verification anchor could be resolved.
    """
    since_ref, since_desc = _resolve_since_anchor(project_root, since)

    # If ref is None, _resolve_since_anchor returned a recommendation
    if since_ref is None:
        return json.loads(since_desc)  # recommendation dict

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
        active_entries, _, _ = _active_rule_entries(
            name, info, rule_entries, all_proofs)
        active_total = len(active_entries)
        proof_by_rule = _build_proof_lookup(name, rule_entries, all_proofs)
        proved = sum(1 for key, _, _ in active_entries
                     if proof_by_rule.get(key, {}).get('status') == 'pass')
        failing = [key for key, _, _ in active_entries
                   if proof_by_rule.get(key, {}).get('status') == 'fail']
        all_pass = (proved == active_total and active_total > 0)
        d_receipt = _read_receipt(project_root, name)
        d_has_receipt = False
        if all_pass and d_receipt:
            d_vhash = _compute_vhash(
                {key: True for key, _, _ in active_entries},
                _collect_relevant_proofs(name, rule_entries, all_proofs),
            )
            d_has_receipt = (d_receipt.get('vhash') == d_vhash)
        has_fail = len(failing) > 0
        status = _determine_status(proved, active_total, has_fail, d_has_receipt)
        assumed_count = len(info.get('assumed_rules', set()))
        entry = {
            'proved': proved,
            'total': active_total,
            'status': status,
            'failing_rules': failing,
        }
        if deferred_count:
            entry['deferred'] = deferred_count
        if assumed_count:
            entry['assumed'] = assumed_count
        proof_status[name] = entry

    # Annotate file entries with coverage gap flags
    for entry in file_entries:
        spec_name = entry.get('spec')
        if spec_name and entry['category'] == 'CHANGED_BEHAVIOR':
            ps = proof_status.get(spec_name, {})
            if ps.get('proved', 0) == 0 and ps.get('total', 0) > 0:
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

    # Detect external anchor drift — compare Pinned to remote HEAD
    external_anchor_drift = []
    for name, info in features.items():
        if not info.get('is_anchor') or not info.get('source_url'):
            continue
        staleness = _check_git_staleness(
            info['source_url'], info.get('pinned'), project_root
        )
        if staleness is None:
            continue
        if staleness['status'] == 'current':
            continue
        entry = {
            'anchor': name,
            'source_url': info['source_url'],
            'pinned': info.get('pinned'),
            'status': staleness['status'],
        }
        if staleness.get('remote_sha'):
            entry['remote_sha'] = staleness['remote_sha'][:7]
        if staleness.get('error'):
            entry['error'] = staleness['error']
        external_anchor_drift.append(entry)

    # Build rule-level detail for specs with changed behavior files.
    rule_details = {}
    changed_behavior_specs = set()
    for entry in file_entries:
        if entry['category'] == 'CHANGED_BEHAVIOR' and entry.get('spec'):
            changed_behavior_specs.add(entry['spec'])
    for spec_name in changed_behavior_specs:
        info = features.get(spec_name)
        if not info:
            continue
        rules = info.get('rules', {})
        if not rules:
            continue
        ps = proof_status.get(spec_name, {})
        proof_by_rule = {}
        if not info['is_anchor']:
            rule_entries, _ = _build_coverage_rules(
                spec_name, info, features, global_anchors)
            proof_by_rule = _build_proof_lookup(
                spec_name, rule_entries, all_proofs)
        changed_scope_files = [
            e['path'] for e in file_entries
            if e.get('spec') == spec_name
            and e['category'] == 'CHANGED_BEHAVIOR'
        ]
        per_rule = []
        for rule_id in sorted(rules.keys(),
                              key=lambda r: int(r.split('-')[1])):
            rule_desc = rules[rule_id]
            proof_info = proof_by_rule.get(rule_id, {})
            proof_status_val = proof_info.get('status', 'unproved')
            per_rule.append({
                'rule_id': rule_id,
                'description': rule_desc,
                'proof_status': proof_status_val,
            })
        rule_details[spec_name] = {
            'rules': per_rule,
            'changed_files': changed_scope_files,
            'total_rules': len(rules),
            'proved_rules': ps.get('proved', 0),
        }

    return {
        'since': since_desc,
        'commits': commits,
        'files': file_entries,
        'spec_changes': spec_changes,
        'proof_status': proof_status,
        'drift_flags': drift_flags,
        'broken_scopes': broken_scopes,
        'external_anchor_drift': external_anchor_drift,
        'rule_details': rule_details,
    }


def drift(project_root, since=None, role=None):
    """Generate structured drift data as JSON."""
    result = _compute_drift(project_root, since)
    return json.dumps(result, indent=2)


def generate_digest(project_root):
    """Generate the project digest file with coverage, drift, and git SHA.

    This is called by the pre-commit hook to produce .purlin/report-data.js
    with full project state for stakeholder consumption.

    IMPORTANT: Does NOT trigger a new audit. Uses cached audit data only.
    Runs sync_status internals (coverage scan) and drift.
    """
    config = resolve_config(project_root)
    if not config:
        return None

    features = _scan_specs(project_root)
    if not features:
        return None

    all_proofs = _read_proofs(project_root)
    global_anchors = {
        k: v for k, v in features.items()
        if v.get('is_anchor') and v.get('is_global')
    }

    # Read cached audit data only — never trigger a new audit. Both gauges are
    # read here: the digest path used to take audit_summary alone and leave
    # design_summary at its None default, so every pre-commit refresh blanked
    # the Proof Design card that sync_status had just populated.
    audit_summary = _read_audit_summary(project_root)
    design_summary = _read_design_summary(project_root)
    _attach_gauge_coverage(project_root, features, all_proofs,
                           audit_summary, design_summary)

    # Get git SHA
    git_sha = None
    try:
        r = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, cwd=project_root, timeout=5,
        )
        if r.returncode == 0:
            git_sha = r.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass

    # Compute drift data (returns dict, or recommendation dict if no anchor)
    drift_data = None
    try:
        drift_data = _compute_drift(project_root)
    except Exception:
        pass  # Drift failure should not block digest generation

    return _write_report_data(
        project_root, features, all_proofs, config, global_anchors,
        audit_summary, design_summary=design_summary,
        drift_data=drift_data, git_sha=git_sha,
    )


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
