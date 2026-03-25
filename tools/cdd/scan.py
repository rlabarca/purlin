#!/usr/bin/env python3
"""Lightweight status scanner for the Purlin agent.

Gathers project facts and outputs structured JSON to stdout.
Replaces the heavy critic.py with a simple fact-gathering script.
The agent interprets the facts -- this script only collects them.

Usage:
    python3 tools/cdd/scan.py            # scan and output JSON
    python3 tools/cdd/scan.py --cached   # return cached result if < 60s old
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../')))
from tools.bootstrap import detect_project_root, atomic_write

PROJECT_ROOT = detect_project_root(SCRIPT_DIR)
FEATURES_DIR = os.path.join(PROJECT_ROOT, "features")
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")
CACHE_DIR = os.path.join(PROJECT_ROOT, ".purlin", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "scan.json")
DELIVERY_PLAN = os.path.join(PROJECT_ROOT, ".purlin", "delivery_plan.md")
DEP_GRAPH_FILE = os.path.join(CACHE_DIR, "dependency_graph.json")

# Max age of cache in seconds before a rescan is required.
CACHE_MAX_AGE = 60


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
_status_commit_cache = None


def _build_status_commit_index():
    """Fetch all status( commits once and index by feature filename.

    Returns a dict mapping basename -> lifecycle tag for the most recent
    status commit mentioning that feature.
    """
    index = {}
    log_output = _run_git(
        "log", "--all", "--grep=status(", "--format=%s",
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
                index[basename] = _TAG_MAP.get(tag_str, tag_str.upper())

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
        return _status_commit_cache[basename]

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
    """Extract > Prerequisite: links from a feature file."""
    prereqs = []
    try:
        with open(feature_file, 'r', encoding='utf-8') as f:
            for line in f:
                m = re.match(r'^>\s*Prerequisite:\s*(.*)', line)
                if m:
                    for part in m.group(1).split(','):
                        part = part.strip()
                        if part:
                            prereqs.append(part)
    except Exception:
        pass
    return prereqs


def _check_sections(feature_file):
    """Check for key section headings in a feature file."""
    sections = {
        "requirements": False,
        "unit_tests": False,
        "qa_scenarios": False,
        "visual_spec": False,
    }
    try:
        with open(feature_file, 'r', encoding='utf-8') as f:
            for line in f:
                lower = line.lower().strip()
                if lower.startswith("## requirements") or lower.startswith("## overview"):
                    sections["requirements"] = True
                elif lower.startswith("### unit tests"):
                    sections["unit_tests"] = True
                elif lower.startswith("### qa scenarios"):
                    sections["qa_scenarios"] = True
                elif lower.startswith("## visual specification"):
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

        features.append({
            "name": stem,
            "file": _relpath(filepath),
            "lifecycle": _extract_lifecycle(filepath),
            "owner": _extract_owner(filepath),
            "prerequisites": _extract_prerequisites(filepath),
            "test_status": test_status,
            "sections": _check_sections(filepath),
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
# Changes since last scan
# ---------------------------------------------------------------------------

def scan_changes_since_last(last_scan_time):
    """Detect files modified since the last scan timestamp.

    Uses git to find files changed after the given ISO timestamp.
    Returns a dict categorizing changed files.
    """
    result = {
        "specs_modified": [],
        "code_modified": [],
        "companions_modified": [],
        "discoveries_modified": [],
    }

    if not last_scan_time:
        return result

    diff_output = _run_git(
        "diff", "--name-only",
        "--diff-filter=ACMR",
        f"--since={last_scan_time}",
        "HEAD",
    )
    # Fallback: use log-based approach.
    if not diff_output:
        diff_output = _run_git(
            "log", f"--since={last_scan_time}",
            "--name-only", "--format=",
        )

    if not diff_output:
        return result

    seen = set()
    for path in diff_output.splitlines():
        path = path.strip()
        if not path or path in seen:
            continue
        seen.add(path)

        if path.startswith("features/") and path.endswith(".discoveries.md"):
            result["discoveries_modified"].append(path)
        elif path.startswith("features/") and path.endswith(".impl.md"):
            result["companions_modified"].append(path)
        elif path.startswith("features/") and path.endswith(".md"):
            result["specs_modified"].append(path)
        elif not path.startswith("features/") and not path.startswith(".purlin/"):
            result["code_modified"].append(path)

    return result


# ---------------------------------------------------------------------------
# Main scan orchestration
# ---------------------------------------------------------------------------

def run_scan():
    """Execute all scans and return the complete result dict."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Read previous scan time for change detection.
    prev_scan = _read_json_safe(CACHE_FILE)
    last_scan_time = prev_scan.get("scanned_at") if prev_scan else None

    git_state = scan_git_state()

    result = {
        "scanned_at": now,
        "features": scan_features(),
        "changes_since_last_scan": scan_changes_since_last(last_scan_time),
        "open_discoveries": [
            d for d in scan_discoveries() if d.get("status") == "OPEN"
        ],
        "unacknowledged_deviations": scan_unacknowledged_deviations(),
        "delivery_plan": scan_delivery_plan(),
        "dependency_graph": scan_dependency_graph(),
        "git_state": {
            "branch": git_state["branch"],
            "clean": git_state["clean"],
            "recent_commits": git_state["recent_commits"],
            "worktrees": scan_worktrees(),
        },
    }

    return result


def main():
    """Entry point: handle --cached flag and output JSON."""
    use_cached = "--cached" in sys.argv

    if use_cached and os.path.isfile(CACHE_FILE):
        try:
            stat = os.stat(CACHE_FILE)
            age = time.time() - stat.st_mtime
            if age < CACHE_MAX_AGE:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    print(f.read())
                return
        except Exception:
            pass  # Fall through to fresh scan.

    result = run_scan()

    # Write to cache.
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        atomic_write(CACHE_FILE, result, as_json=True)
    except Exception as e:
        print(f"Warning: could not write cache: {e}", file=sys.stderr)

    # Print to stdout.
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
