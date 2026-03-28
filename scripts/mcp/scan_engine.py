#!/usr/bin/env python3
"""Lightweight status scanner for the Purlin agent.

Gathers project facts and outputs structured JSON to stdout.
The agent interprets the facts -- this script only collects them.

Usage:
    python3 tools/cdd/scan.py                            # full scan (no tombstones)
    python3 tools/cdd/scan.py --cached                   # cached if < 60s old
    python3 tools/cdd/scan.py --tombstones               # include tombstone entries
    python3 tools/cdd/scan.py --only features,git        # focused output (skip other sections)
    python3 tools/cdd/scan.py --cached --only features   # filter cached output

Sections for --only: features, discoveries, deviations, companion_debt, plan, deps, git, smoke, invariants
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
# Add scripts/ parent for smoke module access
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..')))
from bootstrap import detect_project_root, atomic_write
from invariant_engine import (
    is_invariant_node, is_anchor_node as _invariant_is_anchor,
    ANCHOR_PREFIXES as _ALL_ANCHOR_PREFIXES, extract_metadata as _extract_inv_metadata,
    compute_content_hash, validate_invariant,
)
from smoke.smoke import suggest_smoke_features

PROJECT_ROOT = detect_project_root(SCRIPT_DIR)
FEATURES_DIR = os.path.join(PROJECT_ROOT, "features")
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")
CACHE_DIR = os.path.join(PROJECT_ROOT, ".purlin", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "scan.json")
DELIVERY_PLAN = os.path.join(PROJECT_ROOT, ".purlin", "delivery_plan.md")
DEP_GRAPH_FILE = os.path.join(CACHE_DIR, "dependency_graph.json")

# Max age of cache in seconds before a rescan is required.
CACHE_MAX_AGE = 60

# Maps --only section names to JSON output keys.
SECTION_MAP = {
    "features": "features",
    "discoveries": "open_discoveries",
    "deviations": "unacknowledged_deviations",
    "companion_debt": "companion_debt",
    "plan": "delivery_plan",
    "deps": "dependency_graph",
    "git": "git_state",
    "smoke": "smoke_candidates",
    "invariants": "invariants",
}


def _parse_args():
    """Parse CLI arguments. Returns (cached, tombstones, only_set_or_None)."""
    cached = "--cached" in sys.argv
    tombstones = "--tombstones" in sys.argv
    only = None
    for i, arg in enumerate(sys.argv):
        if arg == "--only" and i + 1 < len(sys.argv):
            only = set(sys.argv[i + 1].split(","))
            break
    return cached, tombstones, only


def _filter_tombstones(result):
    """Remove tombstone entries from features array (mutates in-place)."""
    if "features" in result:
        result["features"] = [f for f in result["features"]
                              if not f.get("tombstone")]


def _filter_sections(result, only):
    """Filter result dict to only include requested sections."""
    filtered = {"scanned_at": result.get("scanned_at", "")}
    for section_name in only:
        json_key = SECTION_MAP.get(section_name)
        if json_key and json_key in result:
            filtered[json_key] = result[json_key]
    return filtered


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_git(*args):
    """Run a git command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=10,
            cwd=PROJECT_ROOT,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _relpath(path):
    """Return a path relative to PROJECT_ROOT."""
    return os.path.relpath(path, PROJECT_ROOT)


def _read_json_safe(path):
    """Read a JSON file, returning None on any failure."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 1. Features
# ---------------------------------------------------------------------------

_TAG_MAP = {
    "Complete": "COMPLETE",
    "Ready for Verification": "TESTING",
    "Verified": "VERIFIED",
    "TODO": "TODO",
}

# Cached status commit index: built once per scan run.
# Maps basename -> {"tag": str, "timestamp": int}
_status_commit_cache = None


def _build_status_commit_index():
    """Fetch all status( commits once and index by feature filename.

    Returns a dict mapping basename -> {"tag": lifecycle_tag, "timestamp": unix_epoch}
    for the most recent status commit mentioning that feature.
    """
    index = {}
    log_output = _run_git(
        "log", "--grep=status(", "--format=%ct %s",
    )
    if not log_output:
        return index

    tag_re = re.compile(r'\[(Complete|Ready for Verification|Verified|TODO)\s+features/(\S+\.md)\]')

    for line in log_output.splitlines():
        m = tag_re.search(line)
        if m:
            tag_str = m.group(1)
            feat_file = m.group(2)
            basename = os.path.basename(feat_file)
            # Only keep the first (most recent) match per feature.
            if basename not in index:
                # Extract timestamp from beginning of line
                try:
                    ts = int(line.split()[0])
                except (ValueError, IndexError):
                    ts = 0
                index[basename] = {
                    "tag": _TAG_MAP.get(tag_str, tag_str.upper()),
                    "timestamp": ts,
                }

    return index


def _extract_lifecycle(feature_file):
    """Extract lifecycle tag from the most recent status commit for a feature.

    Uses a cached index of all status commits (built once per scan) for
    performance. Falls back to reading an inline tag from the file.
    """
    global _status_commit_cache
    if _status_commit_cache is None:
        _status_commit_cache = _build_status_commit_index()

    basename = os.path.basename(feature_file)
    if basename in _status_commit_cache:
        return _status_commit_cache[basename]["tag"]

    # Fallback: read inline tag from file content (e.g. [TODO] on its own line).
    try:
        with open(feature_file, 'r', encoding='utf-8') as f:
            for line in f:
                m = re.match(r'^\[(TODO|COMPLETE|TESTING|VERIFIED|IN_PROGRESS)\]', line.strip())
                if m:
                    return m.group(1)
    except Exception:
        pass

    return "TODO"


# Cached spec modification timestamps: built once per scan run.
_spec_mod_cache = None


def _build_spec_mod_index():
    """Batch-fetch last modification timestamps for all feature spec files.

    Returns dict mapping basename -> unix_epoch of last commit touching that file.
    """
    index = {}
    log_output = _run_git(
        "log", "--name-only", "--format=%ct", "--diff-filter=AM",
        "--", "features/*.md",
    )
    if not log_output:
        return index

    current_ts = None
    for line in log_output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            current_ts = int(line)
            continue
        except ValueError:
            pass
        # It's a filename
        basename = os.path.basename(line)
        if basename.endswith('.impl.md') or basename.endswith('.discoveries.md'):
            continue
        if basename not in index:
            index[basename] = current_ts or 0

    return index


_EXEMPT_TAGS = re.compile(r'\[(Migration|Spec-FMT|QA-Tags)\]', re.IGNORECASE)

# Cached exemption check index: maps basename -> list of commit messages since status commit
_exemption_index = None


def _build_exemption_index():
    """Batch-fetch commit timestamps and messages for all feature spec files.

    Returns dict mapping basename -> [(timestamp, message), ...] for all
    commits touching that file since the earliest status commit globally.
    The per-feature timestamp filtering happens at query time in
    _check_spec_modified_after_completion.
    """
    global _status_commit_cache
    if _status_commit_cache is None:
        _status_commit_cache = _build_status_commit_index()

    # Find the earliest status commit timestamp to bound the query
    if not _status_commit_cache:
        return {}

    min_ts = min(entry["timestamp"] for entry in _status_commit_cache.values())

    # One git call: all commits touching features/*.md since earliest status commit
    log_output = _run_git(
        "log", "--name-only", "--format=__COMMIT__%ct %s",
        f"--since={min_ts}",
        "--", "features/*.md",
    )
    if not log_output:
        return {}

    index = {}  # basename -> [(timestamp, message)]
    current_ts = 0
    current_msg = None

    for line in log_output.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("__COMMIT__"):
            payload = line[10:]  # Strip prefix
            # Parse "timestamp message"
            parts = payload.split(" ", 1)
            try:
                current_ts = int(parts[0])
                current_msg = parts[1] if len(parts) > 1 else ""
            except (ValueError, IndexError):
                current_ts = 0
                current_msg = payload
            continue
        # It's a filename
        basename = os.path.basename(line)
        if basename.endswith('.impl.md') or basename.endswith('.discoveries.md'):
            continue
        if current_msg is not None:
            if basename not in index:
                index[basename] = []
            index[basename].append((current_ts, current_msg))

    return index


def _check_spec_modified_after_completion(feature_file):
    """Check if the spec was modified after the last status commit.

    Returns True if non-exempt modifications exist after completion,
    False if not (or all modifications are exempt), None if no status
    commit exists.
    """
    global _status_commit_cache, _spec_mod_cache, _exemption_index
    if _status_commit_cache is None:
        _status_commit_cache = _build_status_commit_index()
    if _spec_mod_cache is None:
        _spec_mod_cache = _build_spec_mod_index()

    basename = os.path.basename(feature_file)
    status_entry = _status_commit_cache.get(basename)
    if status_entry is None:
        return None  # Never completed

    spec_mod_ts = _spec_mod_cache.get(basename, 0)
    status_ts = status_entry["timestamp"]

    if spec_mod_ts <= status_ts:
        return False  # Not modified after completion

    # Spec was modified after completion — check if ALL intervening commits
    # have exemption tags using the batch index.
    if _exemption_index is None:
        _exemption_index = _build_exemption_index()

    entries = _exemption_index.get(basename, [])
    if not entries:
        return False  # No commits found in index (edge case)

    for ts, msg in entries:
        # Only check commits AFTER this feature's status commit
        if ts <= status_ts:
            continue
        # Skip the status commit itself
        if msg.startswith("status("):
            continue
        # Check for exemption tag
        if not _EXEMPT_TAGS.search(msg):
            return True  # Non-exempt commit found

    return False  # All commits were exempt


def _extract_owner(feature_file):
    """Extract > Owner: tag from a feature file. Default: 'PM'."""
    try:
        with open(feature_file, 'r', encoding='utf-8') as f:
            for line in f:
                m = re.match(r'^>\s*Owner:\s*(.+)', line)
                if m:
                    return m.group(1).strip().strip('"')
    except Exception:
        pass
    return "PM"


def _extract_prerequisites(feature_file):
    """Extract > Prerequisite: links from a feature file.

    Each prerequisite is on its own ``> Prerequisite:`` line.
    Inline comments after the .md reference are stripped, e.g.:
        > Prerequisite: features/foo.md (some note)
    becomes just ``features/foo.md``.
    """
    prereqs = []
    try:
        with open(feature_file, 'r', encoding='utf-8') as f:
            for line in f:
                m = re.match(r'^>\s*Prerequisite:\s*(.*)', line)
                if m:
                    value = m.group(1).strip()
                    if not value:
                        continue
                    # Extract the .md file reference, ignoring trailing comments
                    ref_match = re.match(r'([\w/.\-]+\.md)\b', value)
                    prereqs.append(ref_match.group(1) if ref_match else value)
    except Exception:
        pass
    return prereqs


# Pre-compiled regexes for section heading detection.
# These handle both numbered (## 2. Requirements) and unnumbered (## Requirements) forms.
_RE_REQUIREMENTS = re.compile(r'^##\s+(\d+\.\s*)?requirements\b', re.IGNORECASE)
_RE_UNIT_TESTS = re.compile(r'^###\s+(\d+\.\s*)?unit\s+tests\b', re.IGNORECASE)
_RE_QA_SCENARIOS = re.compile(r'^###\s+(\d+\.\s*)?qa\s+scenarios\b', re.IGNORECASE)
_RE_VISUAL_SPEC = re.compile(r'^##\s+(\d+\.\s*)?visual\s+specification\b', re.IGNORECASE)

# Anchor node section headings (arch_*, design_*, policy_* files).
# These use ## Purpose and ## Invariants instead of ## Requirements.
_RE_PURPOSE = re.compile(r'^##\s+(\d+\.\s*)?purpose\b', re.IGNORECASE)
_RE_INVARIANTS = re.compile(r'^##\s+(\d+\.\s*)?\w*\s*invariants\b', re.IGNORECASE)

_ANCHOR_PREFIXES = ('arch_', 'design_', 'policy_', 'ops_', 'prodbrief_')


def _is_invariant_node(filename):
    """Check if a filename is an invariant node (i_<anchor_type>_*)."""
    return is_invariant_node(filename)


def _is_anchor_node(filename):
    """Check if a filename is an anchor node (regular or invariant).

    Handles: arch_*, design_*, policy_*, ops_*, prodbrief_*, and their i_* variants.
    """
    return _invariant_is_anchor(filename)


_RE_USER_STORIES = re.compile(r'^##\s+(\d+\.\s*)?user\s+stories\b', re.IGNORECASE)
_RE_SUCCESS_CRITERIA = re.compile(r'^##\s+(\d+\.\s*)?success\s+criteria\b', re.IGNORECASE)


def _check_sections(feature_file):
    """Check for key section headings in a feature file.

    For regular features: checks Requirements, Unit Tests, QA Scenarios, Visual Spec.
    For anchor nodes: checks Purpose and Invariants instead of Requirements.
    For prodbrief nodes: checks Purpose, User Stories, and Success Criteria.
    """
    filename = os.path.basename(feature_file)
    is_anchor = _is_anchor_node(filename)
    # Detect prodbrief type (with or without i_ prefix).
    stripped_name = filename[2:] if _is_invariant_node(filename) else filename
    is_prodbrief = stripped_name.startswith('prodbrief_')

    sections = {
        "requirements": False,
        "unit_tests": False,
        "qa_scenarios": False,
        "visual_spec": False,
    }
    try:
        with open(feature_file, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if is_prodbrief:
                    # Prodbrief uses Purpose + User Stories + Success Criteria.
                    if (_RE_PURPOSE.match(stripped)
                            or _RE_USER_STORIES.match(stripped)
                            or _RE_SUCCESS_CRITERIA.match(stripped)):
                        sections["requirements"] = True
                elif is_anchor:
                    # Anchor nodes use Purpose + Invariants instead of Requirements
                    if _RE_PURPOSE.match(stripped) or _RE_INVARIANTS.match(stripped):
                        sections["requirements"] = True
                else:
                    if _RE_REQUIREMENTS.match(stripped):
                        sections["requirements"] = True
                if _RE_UNIT_TESTS.match(stripped):
                    sections["unit_tests"] = True
                elif _RE_QA_SCENARIOS.match(stripped):
                    sections["qa_scenarios"] = True
                elif _RE_VISUAL_SPEC.match(stripped):
                    sections["visual_spec"] = True
    except Exception:
        pass
    return sections


def scan_features():
    """Scan features/*.md for metadata. Returns list of feature dicts."""
    features = []
    if not os.path.isdir(FEATURES_DIR):
        return features

    for filename in sorted(os.listdir(FEATURES_DIR)):
        if not filename.endswith(".md"):
            continue
        # Skip companion, discovery, and tombstone files.
        if filename.endswith(".impl.md") or filename.endswith(".discoveries.md"):
            continue
        filepath = os.path.join(FEATURES_DIR, filename)
        if not os.path.isfile(filepath):
            continue
        # Skip tombstones directory entries if any file somehow matches.
        if "tombstones" in filepath:
            continue

        stem = filename[:-3]  # remove .md

        # Test status
        test_json_path = os.path.join(TESTS_DIR, stem, "tests.json")
        test_data = _read_json_safe(test_json_path)
        test_status = None
        if test_data is not None:
            test_status = test_data.get("status", None)

        # Regression test status
        regression_json_path = os.path.join(TESTS_DIR, stem, "regression.json")
        regression_data = _read_json_safe(regression_json_path)
        regression_status = None
        regression_failed = None
        regression_passed = None
        if regression_data is not None:
            regression_status = regression_data.get("status", None)
            regression_failed = regression_data.get("failed", None)
            regression_passed = regression_data.get("passed", None)

        # Also check QA-authored regression suites
        qa_scenario_path = os.path.join(TESTS_DIR, "qa", "scenarios", f"{stem}.json")
        qa_regression_data = _read_json_safe(qa_scenario_path)
        qa_regression_status = None
        if qa_regression_data is not None:
            qa_regression_status = qa_regression_data.get("status", None)

        feature_entry = {
            "name": stem,
            "file": _relpath(filepath),
            "lifecycle": _extract_lifecycle(filepath),
            "owner": _extract_owner(filepath),
            "prerequisites": _extract_prerequisites(filepath),
            "test_status": test_status,
            "regression_status": regression_status,
            "spec_modified_after_completion": _check_spec_modified_after_completion(filepath),
            "sections": _check_sections(filepath),
        }
        if _is_invariant_node(filename):
            feature_entry["invariant"] = True
        if regression_failed is not None:
            feature_entry["regression_failed"] = regression_failed
            feature_entry["regression_passed"] = regression_passed
        if qa_regression_status is not None:
            feature_entry["qa_regression_status"] = qa_regression_status

        features.append(feature_entry)

    # Append tombstone entries.
    tombstones_dir = os.path.join(FEATURES_DIR, "tombstones")
    if os.path.isdir(tombstones_dir):
        for filename in sorted(os.listdir(tombstones_dir)):
            if not filename.endswith(".md"):
                continue
            # Skip companion and discovery artifacts alongside tombstones.
            if filename.endswith(".impl.md") or filename.endswith(
                    ".discoveries.md"):
                continue
            filepath = os.path.join(tombstones_dir, filename)
            if not os.path.isfile(filepath):
                continue
            stem = filename[:-3]  # remove .md
            features.append({
                "name": stem,
                "file": _relpath(filepath),
                "lifecycle": "TOMBSTONE",
                "owner": None,
                "prerequisites": [],
                "test_status": None,
                "regression_status": None,
                "spec_modified_after_completion": None,
                "sections": {
                    "requirements": False,
                    "unit_tests": False,
                    "qa_scenarios": False,
                    "visual_spec": False,
                },
                "tombstone": True,
            })

    return features


# ---------------------------------------------------------------------------
# 2. Test status (covered inline in scan_features above)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 3. Open discoveries
# ---------------------------------------------------------------------------

_DISCOVERY_TYPE_RE = re.compile(
    r'^###\s*\[(BUG|DISCOVERY|INTENT_DRIFT|SPEC_DISPUTE)\]',
    re.IGNORECASE,
)
_STATUS_RE = re.compile(r'^\s*-\s*\*\*Status:\*\*\s*(\S+)', re.IGNORECASE)
_ACTION_RE = re.compile(r'^\s*-\s*\*\*Action Required:\*\*\s*(.+)', re.IGNORECASE)


def scan_discoveries():
    """Scan features/*.discoveries.md for open entries.

    Returns a list of discovery dicts with type, status, feature, and action.
    """
    discoveries = []
    if not os.path.isdir(FEATURES_DIR):
        return discoveries

    for filename in sorted(os.listdir(FEATURES_DIR)):
        if not filename.endswith(".discoveries.md"):
            continue
        filepath = os.path.join(FEATURES_DIR, filename)
        feature_stem = filename.replace(".discoveries.md", "")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            continue

        current_type = None
        current_title = None
        current_status = None
        current_action = None

        def _flush():
            if current_type and current_status:
                discoveries.append({
                    "feature": feature_stem,
                    "file": _relpath(filepath),
                    "type": current_type,
                    "title": current_title or "",
                    "status": current_status,
                    "action_required": current_action,
                })

        for line in lines:
            m = _DISCOVERY_TYPE_RE.match(line)
            if m:
                _flush()
                current_type = m.group(1).upper()
                current_title = line.strip().lstrip("#").strip()
                current_status = None
                current_action = None
                continue

            sm = _STATUS_RE.match(line)
            if sm:
                current_status = sm.group(1).upper()
                continue

            am = _ACTION_RE.match(line)
            if am:
                current_action = am.group(1).strip()
                continue

        _flush()

    return discoveries


# ---------------------------------------------------------------------------
# 4. Unacknowledged deviations
# ---------------------------------------------------------------------------

_DEVIATION_TAG_RE = re.compile(
    r'\[(DEVIATION|DISCOVERY|INFEASIBLE|SPEC_PROPOSAL)\]'
)
_ACKNOWLEDGED_RE = re.compile(r'ACKNOWLEDGED', re.IGNORECASE)
_PM_PENDING_RE = re.compile(r'PM\s+status:\s*PENDING', re.IGNORECASE)


def scan_unacknowledged_deviations():
    """Scan features/*.impl.md for unacknowledged deviations.

    Returns a list of dicts with feature, file, tag, and line content.
    """
    deviations = []
    if not os.path.isdir(FEATURES_DIR):
        return deviations

    for filename in sorted(os.listdir(FEATURES_DIR)):
        if not filename.endswith(".impl.md"):
            continue
        filepath = os.path.join(FEATURES_DIR, filename)
        feature_stem = filename.replace(".impl.md", "")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            continue

        for i, line in enumerate(lines, 1):
            # Check for deviation tags NOT followed by ACKNOWLEDGED on the same line.
            tag_match = _DEVIATION_TAG_RE.search(line)
            if tag_match and not _ACKNOWLEDGED_RE.search(line):
                deviations.append({
                    "feature": feature_stem,
                    "file": _relpath(filepath),
                    "tag": tag_match.group(1),
                    "line": i,
                    "text": line.strip(),
                })

            # Check for Active Deviations table rows with PM status: PENDING.
            if _PM_PENDING_RE.search(line):
                deviations.append({
                    "feature": feature_stem,
                    "file": _relpath(filepath),
                    "tag": "PM_PENDING",
                    "line": i,
                    "text": line.strip(),
                })

    return deviations


# ---------------------------------------------------------------------------
# 4b. Companion debt (per policy_spec_code_sync.md)
# ---------------------------------------------------------------------------

def scan_companion_debt():
    """Detect features with code commits more recent than companion file updates.

    Compares git log timestamps for feature-related code against the companion
    file's last modification time.  Returns a list of dicts with feature, file,
    and debt_type ('missing' or 'stale').
    """
    debt = []
    if not os.path.isdir(FEATURES_DIR):
        return debt

    # Build set of feature stems that have companion files and their mtimes.
    companion_mtimes = {}
    for filename in os.listdir(FEATURES_DIR):
        if filename.endswith(".impl.md"):
            stem = filename.replace(".impl.md", "")
            filepath = os.path.join(FEATURES_DIR, filename)
            try:
                companion_mtimes[stem] = os.path.getmtime(filepath)
            except OSError:
                continue

    # For each feature spec, check if there are code commits more recent
    # than the companion file.  We use the tests/<stem>/ directory and
    # the companion file's Tool Location / Source Mapping as proxies for
    # "code files that belong to this feature."
    for filename in sorted(os.listdir(FEATURES_DIR)):
        if not filename.endswith(".md"):
            continue
        if filename.endswith(".impl.md") or filename.endswith(".discoveries.md"):
            continue
        stem = filename[:-3]

        # Skip anchors and invariants — they don't have code.
        if _is_anchor_node(filename):
            continue

        # Check if tests directory exists (proxy for "has implementation").
        test_dir = os.path.join(TESTS_DIR, stem)
        if not os.path.isdir(test_dir):
            continue

        # Get the latest code commit timestamp for this feature's test dir.
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ct", "--", test_dir],
                capture_output=True, text=True, timeout=5,
                cwd=PROJECT_ROOT,
            )
            if result.returncode != 0 or not result.stdout.strip():
                continue
            latest_code_ts = float(result.stdout.strip())
        except Exception:
            continue

        companion_mtime = companion_mtimes.get(stem)

        if companion_mtime is None:
            # No companion file at all — companion debt (missing).
            debt.append({
                "feature": stem,
                "file": f"features/{stem}.impl.md",
                "debt_type": "missing",
                "latest_code_commit": datetime.fromtimestamp(
                    latest_code_ts, tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
        elif latest_code_ts > companion_mtime:
            # Companion exists but is older than latest code commit — stale.
            debt.append({
                "feature": stem,
                "file": _relpath(os.path.join(FEATURES_DIR, f"{stem}.impl.md")),
                "debt_type": "stale",
                "latest_code_commit": datetime.fromtimestamp(
                    latest_code_ts, tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "companion_mtime": datetime.fromtimestamp(
                    companion_mtime, tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })

    return debt


# ---------------------------------------------------------------------------
# 5. Delivery plan
# ---------------------------------------------------------------------------

_PHASE_RE = re.compile(
    r'^##\s+Phase\s+(\d+)\b.*?\((PENDING|IN_PROGRESS|COMPLETE|REMOVED)\)',
    re.IGNORECASE,
)
_FEATURE_BULLET_RE = re.compile(r'^\s*[-*]\s+`?features/(\S+\.md)`?')


def scan_delivery_plan():
    """Parse .purlin/delivery_plan.md if it exists.

    Returns a dict with phases list or None if no plan.
    """
    if not os.path.isfile(DELIVERY_PLAN):
        return None

    try:
        with open(DELIVERY_PLAN, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return None

    phases = []
    current_phase = None

    for line in lines:
        pm = _PHASE_RE.match(line)
        if pm:
            if current_phase:
                phases.append(current_phase)
            current_phase = {
                "number": int(pm.group(1)),
                "status": pm.group(2).upper(),
                "features": [],
            }
            continue

        if current_phase:
            fm = _FEATURE_BULLET_RE.match(line)
            if fm:
                current_phase["features"].append(fm.group(1))

    if current_phase:
        phases.append(current_phase)

    return {"phases": phases} if phases else None


# ---------------------------------------------------------------------------
# 6. Dependency graph
# ---------------------------------------------------------------------------

def scan_dependency_graph():
    """Read .purlin/cache/dependency_graph.json if it exists."""
    data = _read_json_safe(DEP_GRAPH_FILE)
    if data is None:
        return {"total": 0, "cycles": [], "blocked": []}

    features = data.get("features", [])
    cycles = data.get("cycles", [])

    # Identify blocked features (those with prerequisites not in the graph).
    all_files = {f.get("file", "") for f in features}
    blocked = []
    for f in features:
        for prereq in f.get("prerequisites", []):
            prereq_path = "features/" + prereq if not prereq.startswith("features/") else prereq
            if prereq_path not in all_files:
                blocked.append({
                    "feature": f.get("file", ""),
                    "missing_prereq": prereq,
                })

    return {
        "total": len(features),
        "cycles": cycles,
        "blocked": blocked,
    }


# ---------------------------------------------------------------------------
# 7. Git state
# ---------------------------------------------------------------------------

def scan_git_state():
    """Gather current git state."""
    branch = _run_git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"

    # Clean/dirty status
    status_output = _run_git("status", "--porcelain")
    # Filter out .purlin/ and .DS_Store noise.
    dirty_files = []
    if status_output:
        for line in status_output.splitlines():
            # Porcelain format: XY filename (or XY old -> new for renames)
            path = line[3:].strip()
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            if path.startswith(".purlin/") or path == ".DS_Store":
                continue
            dirty_files.append(path)

    clean = len(dirty_files) == 0

    # Recent commits
    log_output = _run_git(
        "log", "-5", "--format=%H|%s|%ci"
    )
    recent_commits = []
    if log_output:
        for line in log_output.splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                recent_commits.append({
                    "hash": parts[0][:8],
                    "message": parts[1],
                    "date": parts[2],
                })

    # Modified files since last commit
    diff_output = _run_git("diff", "--name-only", "HEAD")
    modified_since_commit = diff_output.splitlines() if diff_output else []

    return {
        "branch": branch,
        "clean": clean,
        "dirty_files": dirty_files,
        "recent_commits": recent_commits,
        "modified_since_commit": modified_since_commit,
    }


# ---------------------------------------------------------------------------
# 8. Worktrees
# ---------------------------------------------------------------------------

def scan_worktrees():
    """List existing git worktrees."""
    output = _run_git("worktree", "list", "--porcelain")
    worktrees = []
    if output:
        current_wt = {}
        for line in output.splitlines():
            if line.startswith("worktree "):
                if current_wt:
                    worktrees.append(current_wt)
                current_wt = {"path": line[9:]}
            elif line.startswith("HEAD "):
                current_wt["head"] = line[5:]
            elif line.startswith("branch "):
                current_wt["branch"] = line[7:]
            elif line == "bare":
                current_wt["bare"] = True
        if current_wt:
            worktrees.append(current_wt)

    return worktrees


# ---------------------------------------------------------------------------
# Invariant integrity
# ---------------------------------------------------------------------------

# Commit tag that marks legitimate invariant updates via /pl-invariant sync.
_INVARIANT_SYNC_RE = re.compile(r'invariant-sync\(')


def scan_invariant_integrity():
    """Scan features/i_*.md for integrity and metadata.

    For each invariant file:
    - Compute SHA-256 of content.
    - Compare against cached hash from previous scan.
    - Flag as tampered if hash changed without a recent invariant-sync commit.
    - Extract key metadata (version, scope, source).

    Returns a list of invariant dicts.
    """
    invariants = []
    if not os.path.isdir(FEATURES_DIR):
        return invariants

    # Load previous scan hashes for tamper detection.
    prev_hashes = {}
    prev_scan = _read_json_safe(CACHE_FILE)
    if prev_scan and "invariants" in prev_scan:
        for inv in prev_scan["invariants"]:
            prev_hashes[inv.get("file", "")] = inv.get("content_hash", "")

    # Check for recent invariant-sync commits (last 20 commits).
    recent_sync_files = set()
    log_output = _run_git("log", "-20", "--format=%s")
    if log_output:
        for line in log_output.splitlines():
            if _INVARIANT_SYNC_RE.search(line):
                # Extract filename from invariant-sync(features/i_xxx.md)
                m = re.search(r'invariant-(?:sync|add)\((features/[^)]+)\)', line)
                if m:
                    recent_sync_files.add(m.group(1))

    for filename in sorted(os.listdir(FEATURES_DIR)):
        if not filename.endswith(".md"):
            continue
        if not is_invariant_node(filename):
            continue
        filepath = os.path.join(FEATURES_DIR, filename)
        if not os.path.isfile(filepath):
            continue

        relpath = _relpath(filepath)
        content_hash = compute_content_hash(filepath)
        metadata = _extract_inv_metadata(filepath)

        # Tamper detection.
        prev_hash = prev_hashes.get(relpath, "")
        tampered = False
        if prev_hash and content_hash and prev_hash != content_hash:
            # Hash changed — check if there's a recent sync commit for this file.
            if relpath not in recent_sync_files:
                tampered = True

        # Validation issues.
        issues = validate_invariant(filepath)

        invariants.append({
            "file": relpath,
            "name": filename[:-3],  # strip .md
            "version": metadata.get("Version", ""),
            "scope": metadata.get("Scope", ""),
            "source": metadata.get("Source", ""),
            "format_version": metadata.get("Format-Version", ""),
            "content_hash": content_hash or "",
            "tampered": tampered,
            "validation_issues": issues,
        })

    return invariants


# ---------------------------------------------------------------------------
# Smoke candidate detection
# ---------------------------------------------------------------------------

def _scan_smoke_candidates(features):
    """Identify completed features that should be promoted to smoke tier.

    Reuses suggest_smoke_features() from tools/smoke/smoke.py and filters
    to only include features with COMPLETE lifecycle status.
    """
    try:
        scan_data = {"features": features}
        # Let suggest_smoke_features load the raw dep graph from disk
        suggestions = suggest_smoke_features(
            PROJECT_ROOT, scan_data=scan_data, dep_graph=None
        )
    except Exception:
        return []

    # Build lifecycle index from scanned features
    lifecycle_by_name = {f["name"]: f.get("lifecycle") for f in features}

    # Filter: only completed features with 3+ dependents (high fan-out)
    candidates = []
    for s in suggestions:
        if lifecycle_by_name.get(s["feature"]) != "COMPLETE":
            continue
        dep_count = 0
        for reason in s["reasons"]:
            if reason.startswith("prerequisite for "):
                try:
                    dep_count = int(reason.split()[2])
                except (IndexError, ValueError):
                    pass
                break
        if dep_count < 3:
            continue
        candidates.append({
            "feature": s["feature"],
            "dependents": dep_count,
            "reasons": s["reasons"],
        })

    return candidates


# ---------------------------------------------------------------------------
# Main scan orchestration
# ---------------------------------------------------------------------------

def run_scan(only=None):
    """Execute scans and return result dict.

    Args:
        only: set of section names to compute, or None for full scan.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = {"scanned_at": now}

    # Features are needed by "features" and "smoke" sections.
    need_features = only is None or "features" in only or "smoke" in only
    features = scan_features() if need_features else []

    if only is None or "features" in only:
        result["features"] = features
    if only is None or "discoveries" in only:
        result["open_discoveries"] = [
            d for d in scan_discoveries() if d.get("status") == "OPEN"
        ]
    if only is None or "deviations" in only:
        result["unacknowledged_deviations"] = scan_unacknowledged_deviations()
    if only is None or "companion_debt" in only:
        result["companion_debt"] = scan_companion_debt()
    if only is None or "plan" in only:
        result["delivery_plan"] = scan_delivery_plan()
    if only is None or "deps" in only:
        result["dependency_graph"] = scan_dependency_graph()
    if only is None or "smoke" in only:
        result["smoke_candidates"] = _scan_smoke_candidates(features)
    if only is None or "invariants" in only:
        result["invariants"] = scan_invariant_integrity()
    if only is None or "git" in only:
        git_state = scan_git_state()
        result["git_state"] = {
            "branch": git_state["branch"],
            "clean": git_state["clean"],
            "recent_commits": git_state["recent_commits"],
            "worktrees": scan_worktrees(),
        }

    return result


def main():
    """Entry point: handle flags and output JSON."""
    cached, tombstones, only = _parse_args()

    if cached and os.path.isfile(CACHE_FILE):
        try:
            stat = os.stat(CACHE_FILE)
            age = time.time() - stat.st_mtime
            if age < CACHE_MAX_AGE:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                if not tombstones:
                    _filter_tombstones(result)
                if only:
                    result = _filter_sections(result, only)
                print(json.dumps(result, indent=2))
                return
        except Exception:
            pass  # Fall through to fresh scan.

    result = run_scan(only=only)

    # Only write to cache on full scans (--only produces partial results).
    if only is None:
        os.makedirs(CACHE_DIR, exist_ok=True)
        try:
            atomic_write(CACHE_FILE, result, as_json=True)
        except Exception as e:
            print(f"Warning: could not write cache: {e}", file=sys.stderr)

    # Filter tombstones from output unless --tombstones.
    if not tombstones:
        _filter_tombstones(result)

    # Print to stdout.
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
