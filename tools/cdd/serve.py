import http.server
import json
import re
import socketserver
import subprocess
import os
import sys
import threading
import time
import urllib.parse
from collections import Counter
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Project root detection (Section 2.11)
_env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
if _env_root and os.path.isdir(_env_root):
    PROJECT_ROOT = _env_root
else:
    # Climbing fallback: try FURTHER path first (submodule), then nearer (standalone)
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
    for depth in ('../../../', '../../'):
        candidate = os.path.abspath(os.path.join(SCRIPT_DIR, depth))
        if os.path.exists(os.path.join(candidate, '.purlin')):
            PROJECT_ROOT = candidate
            break

# Config loading with resilience (Section 2.13)
CONFIG_PATH = os.path.join(PROJECT_ROOT, ".purlin/config.json")
CONFIG = {}
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r') as f:
            CONFIG = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        print("Warning: Failed to parse .purlin/config.json; using defaults",
              file=sys.stderr)

PORT = CONFIG.get("cdd_port", 8086)
PROJECT_NAME = CONFIG.get("project_name", "") or os.path.basename(PROJECT_ROOT)

FEATURES_REL = "features"
FEATURES_ABS = os.path.join(PROJECT_ROOT, "features")
FEATURES_DIR = FEATURES_ABS  # alias used by /feature endpoint
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")

COMPLETE_CAP = 10
# Artifact isolation (Section 2.12): write to .purlin/cache/
CACHE_DIR = os.path.join(PROJECT_ROOT, ".purlin", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
FEATURE_STATUS_PATH = os.path.join(CACHE_DIR, "feature_status.json")
DEPENDENCY_GRAPH_PATH = os.path.join(CACHE_DIR, "dependency_graph.json")
TOOLS_ROOT = CONFIG.get("tools_root", "tools")
POLL_INTERVAL = 2  # seconds for file watcher polling

# Release checklist module
RELEASE_RESOLVE_DIR = os.path.join(PROJECT_ROOT, TOOLS_ROOT, "release")
sys.path.insert(0, RELEASE_RESOLVE_DIR)
try:
    from resolve import resolve_checklist as _resolve_checklist
    RELEASE_RESOLVE_AVAILABLE = True
except ImportError:
    RELEASE_RESOLVE_AVAILABLE = False

RELEASE_CONFIG_PATH = os.path.join(
    PROJECT_ROOT, ".purlin", "release", "config.json")


def get_release_checklist():
    """Resolve the release checklist using the core module."""
    if not RELEASE_RESOLVE_AVAILABLE:
        return [], [], []
    global_path = os.path.join(
        PROJECT_ROOT, TOOLS_ROOT, "release", "global_steps.json")
    local_path = os.path.join(
        PROJECT_ROOT, ".purlin", "release", "local_steps.json")
    return _resolve_checklist(
        global_path=global_path,
        local_path=local_path,
        config_path=RELEASE_CONFIG_PATH,
    )


def run_command(command):
    """Runs a shell command and returns its stdout."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True,
            cwd=PROJECT_ROOT
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def build_status_commit_cache():
    """Build a cache of all status commits with a single git log command.

    Replaces ~100+ individual git log subprocess calls with ONE call.
    Returns a dict mapping normalized feature paths to their status info:
    {
        "features/foo.md": {
            "complete_ts": int,    # 0 if no Complete commit
            "complete_hash": str,  # "" if no Complete commit
            "testing_ts": int,     # 0 if no Testing commit
            "testing_hash": str,   # "" if no Testing commit
            "scope": str or None,  # [Scope: ...] from most recent status commit
        }
    }
    """
    output = run_command(
        "git log --grep='\\[Complete features/' "
        "--grep='\\[Ready for' --format='%ct %H %s'"
    )
    if not output:
        return {}

    cache = {}
    complete_re = re.compile(r'\[Complete (features/\S+\.md)\]')
    testing_re = re.compile(r'\[Ready for \w+ (features/\S+\.md)\]')
    scope_re = re.compile(r'\[Scope:\s*([^\]]+)\]')

    for line in output.splitlines():
        parts = line.split(' ', 2)
        if len(parts) < 3:
            continue
        try:
            ts = int(parts[0])
        except ValueError:
            continue
        commit_hash = parts[1]
        subject = parts[2]

        fpath = None
        commit_type = None

        m = complete_re.search(subject)
        if m:
            fpath = os.path.normpath(m.group(1))
            commit_type = 'complete'
        else:
            m = testing_re.search(subject)
            if m:
                fpath = os.path.normpath(m.group(1))
                commit_type = 'testing'

        if not fpath:
            continue

        if fpath not in cache:
            cache[fpath] = {
                'complete_ts': 0, 'complete_hash': '',
                'testing_ts': 0, 'testing_hash': '',
                'scope': None, '_best_ts': 0,
            }

        info = cache[fpath]

        # git log is reverse-chronological: first match = most recent
        ts_key = f'{commit_type}_ts'
        hash_key = f'{commit_type}_hash'
        if info[ts_key] == 0:
            info[ts_key] = ts
            info[hash_key] = commit_hash

        # Scope comes from the most recent status commit of either type
        if ts > info['_best_ts']:
            info['_best_ts'] = ts
            sm = scope_re.search(subject)
            info['scope'] = sm.group(1).strip() if sm else None

    # Clean up internal tracking field
    for info in cache.values():
        del info['_best_ts']

    return cache


def extract_label(filepath):
    """Extracts the Label from a feature file's frontmatter."""
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('> Label:'):
                    return line[len('> Label:'):].strip().strip('"')
    except (IOError, OSError):
        pass
    return os.path.splitext(os.path.basename(filepath))[0]


def strip_discoveries_section(content):
    """Strip the '## User Testing Discoveries' section and everything below.

    Returns the spec content above that section for comparison purposes.
    """
    match = re.search(r'^## User Testing Discoveries', content, re.MULTILINE)
    if not match:
        return content
    return content[:match.start()]


def spec_content_unchanged(f_path, commit_hash):
    """Check if spec content (above Discoveries section) is unchanged since commit.

    Retrieves file content at the given commit hash via git show, strips the
    User Testing Discoveries section from both versions, and compares.
    Returns True if spec content is identical (only Discoveries changed).
    """
    try:
        committed_content = run_command(
            f"git show {commit_hash}:{f_path}"
        )
        if not committed_content:
            return False
    except Exception:
        return False

    try:
        abs_path = os.path.join(PROJECT_ROOT, f_path)
        with open(abs_path, 'r') as f:
            current_content = f.read()
    except (IOError, OSError):
        return False

    committed_spec = strip_discoveries_section(committed_content).rstrip()
    current_spec = strip_discoveries_section(current_content).rstrip()
    return committed_spec == current_spec


def get_feature_status(features_rel, features_abs, cache=None):
    """Gathers the status of all features for the project's features directory."""
    if not os.path.isdir(features_abs):
        return [], [], []

    if cache is None:
        cache = build_status_commit_cache()

    complete, testing, todo = [], [], []
    feature_files = [f for f in os.listdir(features_abs) if f.endswith('.md') and not f.endswith('.impl.md')]

    for fname in feature_files:
        f_path = os.path.normpath(os.path.join(features_rel, fname))
        info = cache.get(f_path, {})

        complete_ts = info.get('complete_ts', 0)
        test_ts = info.get('testing_ts', 0)

        f_abs_path = os.path.join(features_abs, fname)
        file_mod_ts = int(os.path.getmtime(f_abs_path)) if os.path.exists(f_abs_path) else 0

        status = "TODO"
        if complete_ts > test_ts:
            if file_mod_ts <= complete_ts:
                status = "COMPLETE"
            else:
                # File modified after status commit — check if only Discoveries changed
                commit_hash = info.get('complete_hash', '')
                if commit_hash and spec_content_unchanged(f_path, commit_hash):
                    status = "COMPLETE"
        elif test_ts > 0:
            if file_mod_ts <= test_ts:
                status = "TESTING"
            else:
                # File modified after status commit — check if only Discoveries changed
                commit_hash = info.get('testing_hash', '')
                if commit_hash and spec_content_unchanged(f_path, commit_hash):
                    status = "TESTING"

        if status == "COMPLETE":
            complete.append((fname, complete_ts))
        elif status == "TESTING":
            testing.append(fname)
        else:
            todo.append(fname)

    complete.sort(key=lambda x: x[1], reverse=True)
    return complete, sorted(testing), sorted(todo)


def get_feature_test_status(feature_stem, tests_dir):
    """Looks up tests/<feature_stem>/tests.json and returns status or None.

    Returns "PASS", "FAIL", or None (when no tests.json exists).
    Malformed JSON is treated as FAIL.
    """
    tests_path = os.path.join(tests_dir, feature_stem, "tests.json")
    if not os.path.isfile(tests_path):
        return None
    try:
        with open(tests_path, 'r') as f:
            data = json.load(f)
        if data.get("status") == "PASS":
            return "PASS"
        return "FAIL"
    except (json.JSONDecodeError, IOError, OSError):
        return "FAIL"


def get_feature_role_status(feature_stem, tests_dir):
    """Reads role_status from tests/<feature_stem>/critic.json.

    Returns dict with 'architect', 'builder', 'qa' keys, or None
    if no critic.json exists or it lacks role_status.
    """
    critic_path = os.path.join(tests_dir, feature_stem, "critic.json")
    if not os.path.isfile(critic_path):
        return None
    try:
        with open(critic_path, 'r') as f:
            data = json.load(f)
        return data.get("role_status")
    except (json.JSONDecodeError, IOError, OSError):
        return None


def aggregate_test_statuses(statuses):
    """Aggregates per-feature test statuses into a top-level status.

    statuses: list of non-None per-feature test status values.
    Returns "FAIL" if any FAIL, "PASS" if all PASS, "UNKNOWN" if empty.
    """
    if not statuses:
        return "UNKNOWN"
    if any(s == "FAIL" for s in statuses):
        return "FAIL"
    return "PASS"


def get_delivery_phase():
    """Parse the delivery plan and return the current phase info.

    Reads `.purlin/cache/delivery_plan.md`, counts phase headings,
    and finds the first PENDING or IN_PROGRESS phase.

    Supports the canonical format: `## Phase N — Label [STATUS]`

    Returns {"current": int, "total": int} or None if no plan exists
    or all phases are COMPLETE.
    """
    plan_path = os.path.join(CACHE_DIR, "delivery_plan.md")
    if not os.path.isfile(plan_path):
        return None

    try:
        with open(plan_path, 'r') as f:
            content = f.read()
    except (IOError, OSError):
        return None

    # Match canonical format: ## Phase N — Label [STATUS]
    phase_pattern = re.compile(
        r'^##\s+Phase\s+(\d+)\s.*?\[(\w+)\]',
        re.MULTILINE
    )
    matches = phase_pattern.findall(content)
    if not matches:
        return None

    total = len(matches)

    # Find the first phase with PENDING or IN_PROGRESS status
    current = None
    for phase_num_str, status in matches:
        if status.upper() in ('PENDING', 'IN_PROGRESS'):
            current = int(phase_num_str)
            break

    if current is None:
        # All phases are COMPLETE — omit delivery_phase
        return None

    return {"current": current, "total": total}


def get_change_scope(f_path, cache=None):
    """Extract change_scope from the most recent status commit for a feature.

    When cache is provided (from build_status_commit_cache), uses the
    pre-computed scope. Otherwise falls back to individual git log calls.
    """
    f_path_norm = os.path.normpath(f_path)

    if cache is not None:
        info = cache.get(f_path_norm, {})
        return info.get('scope')

    # Fallback: individual git log calls (used only if no cache provided)
    best_ts = 0
    best_msg = None
    for pattern in (
        f"\\[Complete {f_path}\\]",
        f"\\[Ready for .* {f_path}\\]",
    ):
        result = run_command(
            f"git log -1 --grep='{pattern}' --format='%ct %s'"
        )
        if result:
            parts = result.split(' ', 1)
            try:
                ts = int(parts[0])
            except (ValueError, IndexError):
                continue
            if ts > best_ts:
                best_ts = ts
                best_msg = parts[1] if len(parts) > 1 else ''

    if best_msg:
        match = re.search(r'\[Scope:\s*([^\]]+)\]', best_msg)
        if match:
            return match.group(1).strip()
    return None


# ===================================================================
# Internal Feature Status (old lifecycle format, for Critic consumption)
# ===================================================================

def generate_internal_feature_status(cache=None):
    """Generates the internal feature_status.json (old lifecycle-based format).

    This is consumed by the Critic for lifecycle-state-dependent computations.
    NOT part of the public API contract.
    """
    if cache is None:
        cache = build_status_commit_cache()

    complete_tuples, testing, todo = get_feature_status(FEATURES_REL, FEATURES_ABS, cache)

    all_test_statuses = []

    def make_entry(fname):
        rel_path = os.path.normpath(os.path.join(FEATURES_REL, fname))
        label = extract_label(os.path.join(FEATURES_ABS, fname))
        entry = {"file": rel_path, "label": label}
        stem = os.path.splitext(fname)[0]
        ts = get_feature_test_status(stem, TESTS_DIR)
        if ts is not None:
            entry["test_status"] = ts
            all_test_statuses.append(ts)
        scope = get_change_scope(rel_path, cache)
        if scope:
            entry["change_scope"] = scope
        return entry

    features = {
        "complete": sorted([make_entry(n) for n, _ in complete_tuples],
                           key=lambda x: x["file"]),
        "testing": sorted([make_entry(n) for n in testing],
                          key=lambda x: x["file"]),
        "todo": sorted([make_entry(n) for n in todo],
                       key=lambda x: x["file"]),
    }

    return {
        "features": features,
        "generated_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        "test_status": aggregate_test_statuses(all_test_statuses),
    }


def write_internal_feature_status(cache=None):
    """Writes internal feature_status.json to disk."""
    data = generate_internal_feature_status(cache)
    with open(FEATURE_STATUS_PATH, 'w') as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write('\n')


# ===================================================================
# Public API: /status.json (flat schema with role fields)
# ===================================================================

def generate_api_status_json(cache=None):
    """Generates the public /status.json response (flat array with role fields).

    Per spec Section 2.4:
    - Flat features array (no todo/testing/complete sub-arrays)
    - Per-feature: file, label, architect, builder, qa from role_status
    - No test_status or qa_status fields
    - No top-level test_status
    - Sorted by file path
    """
    if not os.path.isdir(FEATURES_ABS):
        return {
            "features": [],
            "generated_at": datetime.now(timezone.utc).strftime(
                '%Y-%m-%dT%H:%M:%SZ'),
        }

    if cache is None:
        cache = build_status_commit_cache()

    feature_files = sorted(
        f for f in os.listdir(FEATURES_ABS)
        if f.endswith('.md') and not f.endswith('.impl.md'))

    features = []
    for fname in feature_files:
        rel_path = os.path.normpath(os.path.join(FEATURES_REL, fname))
        label = extract_label(os.path.join(FEATURES_ABS, fname))
        entry = {"file": rel_path, "label": label}

        stem = os.path.splitext(fname)[0]
        role_status = get_feature_role_status(stem, TESTS_DIR)
        if role_status:
            if 'architect' in role_status:
                entry["architect"] = role_status["architect"]
            if 'builder' in role_status:
                entry["builder"] = role_status["builder"]
            if 'qa' in role_status:
                entry["qa"] = role_status["qa"]

        scope = get_change_scope(rel_path, cache)
        if scope:
            entry["change_scope"] = scope

        features.append(entry)

    # Scan tombstones (Section 2.2.5 / 2.4 / 2.5)
    tombstones_dir = os.path.join(FEATURES_ABS, "tombstones")
    if os.path.isdir(tombstones_dir):
        tombstone_files = sorted(
            f for f in os.listdir(tombstones_dir) if f.endswith('.md'))
        for fname in tombstone_files:
            rel_path = os.path.normpath(
                os.path.join(FEATURES_REL, "tombstones", fname))
            label = extract_label(os.path.join(tombstones_dir, fname))
            features.append({
                "file": rel_path,
                "label": label,
                "tombstone": True,
                "architect": "DONE",
                "builder": "TODO",
                "qa": "N/A",
            })

    result = {
        "features": sorted(features, key=lambda x: x["file"]),
        "generated_at": datetime.now(timezone.utc).strftime(
            '%Y-%m-%dT%H:%M:%SZ'),
    }

    # critic_last_run: mtime of CRITIC_REPORT.md (Section 2.4 / 2.7)
    critic_report_path = os.path.join(PROJECT_ROOT, "CRITIC_REPORT.md")
    if os.path.isfile(critic_report_path):
        mtime = os.path.getmtime(critic_report_path)
        result["critic_last_run"] = datetime.fromtimestamp(
            mtime, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    delivery_phase = get_delivery_phase()
    if delivery_phase:
        result["delivery_phase"] = delivery_phase

    # Isolated Teams: worktree data (Section 2.5 of cdd_isolated_teams spec)
    isolation_worktrees = get_isolation_worktrees()
    if isolation_worktrees:
        result["isolations_active"] = True
        result["worktrees"] = isolation_worktrees

    return result


# ===================================================================
# Web Dashboard (role-based columns, Active/Complete grouping)
# ===================================================================

def get_git_status():
    """Gets the current git status."""
    return run_command("git status --porcelain | grep -v '.DS_Store' | grep -v '.cache/' | grep -v '.purlin/'")


def get_last_commit():
    """Gets the last commit message."""
    return run_command("git log -1 --format='%h %s (%cr)'")


def generate_workspace_json():
    """Generates workspace data for the /workspace.json endpoint.

    Returns git status (clean or list of modified files) and last commit summary.
    """
    git_status = get_git_status()
    last_commit = get_last_commit()
    result = {
        "clean": not bool(git_status),
        "files": git_status.splitlines() if git_status else [],
        "last_commit": last_commit,
    }
    isolation = get_isolation_worktrees()
    if isolation:
        result["isolations_active"] = True
        result["worktrees"] = isolation
    return result


# ===================================================================
# Isolated Teams: worktree detection and state reading
# ===================================================================


def _detect_worktrees():
    """Detect active git worktrees under .worktrees/ relative to PROJECT_ROOT.

    Returns list of dicts: [{"path": str, "head": str}] for worktrees
    whose path is under .worktrees/.
    """
    output = run_command("git worktree list --porcelain")
    if not output:
        return []

    worktrees = []
    current = {}
    worktrees_prefix = os.path.join(PROJECT_ROOT, '.worktrees')

    for line in output.splitlines():
        if line.startswith('worktree '):
            if current:
                worktrees.append(current)
            current = {'abs_path': line[len('worktree '):].strip()}
        elif line.startswith('HEAD '):
            current['head'] = line[len('HEAD '):].strip()
        elif line.startswith('branch '):
            current['branch_ref'] = line[len('branch '):].strip()
        elif line == '' and current:
            worktrees.append(current)
            current = {}

    if current:
        worktrees.append(current)

    # Filter to worktrees under .worktrees/
    result = []
    for wt in worktrees:
        abs_path = wt.get('abs_path', '')
        if abs_path.startswith(worktrees_prefix + os.sep) or abs_path.startswith(worktrees_prefix + '/'):
            result.append(wt)

    return result


def _name_from_path(worktree_abs_path):
    """Extract isolation name from worktree path.

    .worktrees/feat1 -> "feat1"
    """
    return os.path.basename(worktree_abs_path)


def _read_delivery_phase(worktree_abs_path):
    """Read delivery phase from worktree's delivery plan, if any.

    Returns dict {"current": N, "total": M} or None.
    """
    plan_path = os.path.join(worktree_abs_path, '.purlin', 'cache', 'delivery_plan.md')
    if not os.path.isfile(plan_path):
        return None
    try:
        with open(plan_path, 'r') as f:
            content = f.read()
        # Parse total phases
        total = 0
        current = 0
        import re
        phase_pattern = re.compile(r'^## Phase (\d+)\b.*\[(IN_PROGRESS|PENDING|COMPLETE)\]', re.MULTILINE)
        for m in phase_pattern.finditer(content):
            total += 1
            if m.group(2) == 'IN_PROGRESS':
                current = int(m.group(1))
        if current > 0 and total > 0:
            return {"current": current, "total": total}
    except Exception:
        pass
    return None


def _categorize_files(lines):
    """Categorize file paths into specs/tests/other counts.

    Excludes .purlin/ files entirely. Categorizes features/ as specs,
    tests/ as tests, everything else as other.
    """
    specs = 0
    tests = 0
    other = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('.purlin/'):
            continue
        if line.startswith('features/'):
            specs += 1
        elif line.startswith('tests/'):
            tests += 1
        else:
            other += 1
    return {'specs': specs, 'tests': tests, 'other': other}


def _worktree_state(wt_abs_path):
    """Read state of a single worktree using git -C commands.

    Returns dict with branch, last_commit, commits_ahead, committed
    (files changed in branch commits vs main), and uncommitted
    (files with uncommitted changes in the working tree).
    Both committed and uncommitted are objects with specs, tests, other
    integer counts.
    """
    def _wt_cmd(cmd):
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                check=True, cwd=wt_abs_path)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

    branch = _wt_cmd("git rev-parse --abbrev-ref HEAD")

    # Committed: files changed in this branch's commits relative to main
    # Uses git diff main...<branch> --name-only (three-dot) from PROJECT_ROOT
    # Three-dot diffs the branch against common ancestor — always empty for
    # SAME/BEHIND, reflects only branch-side changes for AHEAD/DIVERGED.
    committed = {'specs': 0, 'tests': 0, 'other': 0}
    try:
        diff_result = subprocess.run(
            f"git diff main...{branch} --name-only",
            shell=True, capture_output=True, text=True,
            cwd=PROJECT_ROOT)
        committed = _categorize_files(diff_result.stdout.splitlines())
    except Exception:
        pass

    # Uncommitted: files in the worktree's working tree not yet committed
    # Uses git status --porcelain from the worktree directory.
    # Captures staged, unstaged, and untracked changes.
    # Format: XY filename (filename starts at column 3)
    # For renames: XY old -> new (use the new path)
    uncommitted = {'specs': 0, 'tests': 0, 'other': 0}
    try:
        status_result = subprocess.run(
            "git status --porcelain",
            shell=True, capture_output=True, text=True,
            cwd=wt_abs_path)
        file_paths = []
        for line in status_result.stdout.splitlines():
            if len(line) < 4:
                continue
            # Extract filename from column 3 onwards
            path = line[3:]
            # For renames (XY old -> new), use the new path
            if ' -> ' in path:
                path = path.split(' -> ', 1)[1]
            file_paths.append(path)
        uncommitted = _categorize_files(file_paths)
    except Exception:
        pass

    last_commit = _wt_cmd("git log -1 --format='%h %s (%cr)'")
    commits_ahead_str = _wt_cmd("git rev-list --count main..HEAD")
    try:
        commits_ahead = int(commits_ahead_str)
    except (ValueError, TypeError):
        commits_ahead = 0

    return {
        'branch': branch,
        'committed': committed,
        'uncommitted': uncommitted,
        'last_commit': last_commit,
        'commits_ahead': commits_ahead,
    }


def _compute_main_diff(branch):
    """Determine sync state between a worktree branch and main.

    Runs two git log range queries from PROJECT_ROOT (not per-worktree)
    to ensure 'main' resolves correctly. Returns one of four states:
    "DIVERGED", "BEHIND", "AHEAD", or "SAME".
    """
    try:
        # Query 1: commits on main not in branch (branch is behind)
        behind_result = subprocess.run(
            f"git log {branch}..main --oneline",
            shell=True, capture_output=True, text=True,
            check=True, cwd=PROJECT_ROOT)
        is_behind = bool(behind_result.stdout.strip())

        # Query 2: commits on branch not in main (branch is ahead)
        ahead_result = subprocess.run(
            f"git log main..{branch} --oneline",
            shell=True, capture_output=True, text=True,
            check=True, cwd=PROJECT_ROOT)
        is_ahead = bool(ahead_result.stdout.strip())

        if is_behind and is_ahead:
            return "DIVERGED"
        elif is_behind:
            return "BEHIND"
        elif is_ahead:
            return "AHEAD"
        else:
            return "SAME"
    except subprocess.CalledProcessError:
        return "SAME"


def get_isolation_worktrees():
    """Get isolation worktree data for API and dashboard.

    Returns list of worktree info dicts, or empty list if no isolations
    are active. Isolations are active when at least one worktree exists
    under .worktrees/.
    """
    worktrees = _detect_worktrees()
    if not worktrees:
        return []

    result = []
    for wt in worktrees:
        abs_path = wt.get('abs_path', '')
        state = _worktree_state(abs_path)
        branch = state['branch']
        name = _name_from_path(abs_path)

        # Relative path from project root
        try:
            rel_path = os.path.relpath(abs_path, PROJECT_ROOT)
        except ValueError:
            rel_path = abs_path

        # Main diff: run from project root (Section 2.4 of cdd_isolated_teams)
        main_diff = _compute_main_diff(branch)

        entry = {
            'name': name,
            'path': rel_path,
            'branch': branch,
            'main_diff': main_diff,
            'commits_ahead': state.get('commits_ahead', 0),
            'last_commit': state['last_commit'],
            'committed': state['committed'],
            'uncommitted': state['uncommitted'],
        }

        # Delivery phase badge (Section 2.10)
        delivery_phase = _read_delivery_phase(abs_path)
        if delivery_phase:
            entry['delivery_phase'] = delivery_phase

        result.append(entry)

    return result


# Badge CSS class mapping for role statuses
ROLE_BADGE_CSS = {
    "DONE": "st-done",
    "CLEAN": "st-done",
    "TODO": "st-todo",
    "FAIL": "st-fail",
    "INFEASIBLE": "st-fail",
    "BLOCKED": "st-blocked",
    "DISPUTED": "st-disputed",
    "N/A": "st-na",
}

# Urgency order for Active section sorting (lower = more urgent)
URGENCY_ORDER = {
    "FAIL": 0, "INFEASIBLE": 0,
    "TODO": 1, "DISPUTED": 1,
    "BLOCKED": 2,
    "DONE": 3, "CLEAN": 3, "N/A": 3,
}


def _role_badge_html(status):
    """Returns a colored badge span for a role status, or '??' if None."""
    if status is None:
        return '<span class="st-na">??</span>'
    css = ROLE_BADGE_CSS.get(status, "st-na")
    return f'<span class="{css}">{status}</span>'


def _format_category_counts(counts):
    """Format a {specs, tests, other} dict as space-separated category counts.

    Returns empty string when all zeros. Zero-count categories are omitted.
    """
    specs = counts.get('specs', 0)
    tests_count = counts.get('tests', 0)
    other = counts.get('other', 0)
    if specs == 0 and tests_count == 0 and other == 0:
        return ''
    parts = []
    if specs > 0:
        parts.append(f'{specs} Specs')
    if tests_count > 0:
        parts.append(f'{tests_count} Tests')
    if other > 0:
        parts.append(f'{other} Code/Other')
    return ' '.join(parts)


def _isolation_section_html(worktrees):
    """Generate HTML for the Isolated Teams Sessions table (no heading)."""
    if not worktrees:
        return ""

    # Sessions table: Name, Branch, Main Diff, Committed Modified, Uncommitted Modified, Kill
    rows = ""
    for wt in worktrees:
        name = wt.get('name', '')
        branch = wt.get('branch', '')

        # Name cell with optional delivery phase badge
        name_html = name
        delivery_phase = wt.get('delivery_phase')
        if delivery_phase:
            name_html += (
                f' <span style="color:var(--purlin-status-warning);font-size:11px">'
                f'(Phase {delivery_phase["current"]}/{delivery_phase["total"]})</span>'
            )

        # Main Diff badge (Section 2.6 Visual Design)
        main_diff = wt.get('main_diff', 'SAME')
        if main_diff == 'DIVERGED':
            diff_html = '<span class="st-disputed">DIVERGED</span>'
        elif main_diff == 'BEHIND':
            diff_html = '<span class="st-todo">BEHIND</span>'
        elif main_diff == 'AHEAD':
            diff_html = '<span class="st-todo">AHEAD</span>'
        else:
            diff_html = '<span class="st-good">SAME</span>'

        # Committed Modified column
        committed_text = _format_category_counts(wt.get('committed', {}))

        # Uncommitted Modified column
        uncommitted_text = _format_category_counts(wt.get('uncommitted', {}))

        # Kill button per row
        kill_btn = (
            f'<button class="btn-critic" onclick="killIsolationPrompt(\'{name}\')"'
            f' style="font-size:10px;padding:2px 8px">Kill</button>'
        )

        rows += (
            f'<tr><td>{name_html}</td><td><code>{branch}</code></td>'
            f'<td>{diff_html}</td>'
            f'<td class="dim">{committed_text}</td>'
            f'<td class="dim">{uncommitted_text}</td>'
            f'<td style="text-align:right">{kill_btn}</td></tr>'
        )

    return (
        '<table class="ft" style="width:100%"><thead><tr>'
        '<th>Name</th><th>Branch</th><th>Main Diff</th>'
        '<th>Committed<br>Modified</th><th>Uncommitted<br>Modified</th><th></th>'
        '</tr></thead><tbody>' + rows + '</tbody></table>'
    )


def _collapsed_isolation_label(worktrees):
    """Compute collapsed sub-heading label and severity badge for Isolated Teams.

    Returns (badge_css, heading_text, badge_text) tuple.
    - badge_css: severity CSS class for the badge only (not the heading)
    - heading_text: text shown in the heading when collapsed (always --purlin-muted)
    - badge_text: worst severity state name shown in the badge to the right
    """
    if not worktrees:
        return ("", "ISOLATED TEAMS", "")
    n = len(worktrees)
    severity_order = {"DIVERGED": 3, "BEHIND": 2, "AHEAD": 1, "SAME": 0}
    severity_names = {3: "DIVERGED", 2: "BEHIND", 1: "AHEAD", 0: "SAME"}
    max_sev = 0
    for wt in worktrees:
        md = wt.get("main_diff", "SAME")
        max_sev = max(max_sev, severity_order.get(md, 0))
    if max_sev >= 3:
        css = "st-disputed"  # orange
    elif max_sev >= 1:
        css = "st-todo"  # yellow
    else:
        css = "st-good"  # green
    sev_name = severity_names.get(max_sev, "SAME")
    return (css, f"{n} Isolated Team{'s' if n != 1 else ''}", sev_name)


def _feature_urgency(entry):
    """Compute urgency score for sorting Active features.

    Lower score = more urgent. Red states first, then yellow/orange, then rest.
    """
    scores = []
    for role in ('architect', 'builder', 'qa'):
        val = entry.get(role)
        if val is not None:
            scores.append(URGENCY_ORDER.get(val, 3))
    return min(scores) if scores else 3


def _is_feature_complete(entry):
    """Check if all roles are fully satisfied."""
    # Tombstone entries are NEVER complete (always Active)
    if entry.get('tombstone'):
        return False

    arch = entry.get('architect')
    builder = entry.get('builder')
    qa = entry.get('qa')

    # If no critic.json exists (no role fields), not complete
    if arch is None and builder is None and qa is None:
        return False

    arch_ok = arch in ('DONE', None)
    builder_ok = builder in ('DONE', None)
    qa_ok = qa in ('CLEAN', 'N/A', None)

    return arch_ok and builder_ok and qa_ok


def generate_html(cache=None):
    """Generates the full dashboard HTML with role-based columns,
    view toggle (Status/Spec Map), search, collapsible sections,
    feature detail modal, and Cytoscape.js graph view."""
    git_status = get_git_status()
    last_commit = get_last_commit()

    # Get API data for dashboard
    api_data = generate_api_status_json(cache)
    all_features = api_data["features"]

    # Split into Active vs Complete
    active_features = []
    complete_features = []
    for entry in all_features:
        if _is_feature_complete(entry):
            complete_features.append(entry)
        else:
            active_features.append(entry)

    # Sort Active by urgency (red first, then yellow/orange, then alphabetical)
    active_features.sort(key=lambda e: (_feature_urgency(e), e["file"]))

    # Cap Complete at COMPLETE_CAP
    total_complete = len(complete_features)
    visible_complete = complete_features[:COMPLETE_CAP]
    overflow = total_complete - COMPLETE_CAP

    # Build Active table
    active_html = _role_table_html(active_features) if active_features else ""
    complete_html = _role_table_html(visible_complete) if visible_complete else ""
    overflow_html = (
        f'<p class="dim">and {overflow} more&hellip;</p>' if overflow > 0 else ""
    )

    if not git_status:
        git_html = '<p class="clean">Clean Slate</p>'
    else:
        git_html = '<p class="wip">Work in Progress:</p><pre>' + git_status + '</pre>'

    # Isolated Teams detection for dashboard
    isolation_worktrees = get_isolation_worktrees()
    isolations_active = bool(isolation_worktrees)
    isolation_html = _isolation_section_html(isolation_worktrees)

    # Collapsed sub-heading label for Isolated Teams
    iso_badge_css, iso_badge_text, iso_sev_text = _collapsed_isolation_label(
        isolation_worktrees)
    if iso_badge_css and iso_sev_text:
        isolation_badge = f'<span class="{iso_badge_css}">{iso_sev_text}</span>'
    else:
        isolation_badge = ''

    # Creation row (always first item in Isolated Teams sub-section)
    creation_row_html = (
        '<div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;padding-top:4px">'
        '<span style="color:var(--purlin-muted);font-size:11px;white-space:nowrap">'
        'Create An Isolated Team</span>'
        '<input type="text" id="new-isolation-name" maxlength="12" placeholder="name"'
        ' autocapitalize="none" autocorrect="off"'
        ' style="width:80px;font-size:11px;padding:3px 6px;background:var(--purlin-surface);'
        'color:var(--purlin-primary);border:1px solid var(--purlin-border);border-radius:3px"'
        ' oninput="validateIsolationName(this)">'
        '<button class="btn-critic" onclick="createIsolation()" id="btn-create-isolation"'
        ' style="font-size:11px" disabled>Create</button>'
        '<span id="isolation-ctrl-err" style="color:var(--purlin-status-error);font-size:11px;margin-left:4px"></span>'
        '</div>'
        '<span id="isolation-name-hint" style="color:var(--purlin-muted);font-size:10px;display:none"></span>'
    )

    # Count badges for collapsed summary
    active_count = len(active_features)
    complete_count = len(complete_features)

    # critic_last_run for Run Critic button annotation (Section 2.7)
    critic_last_run_ts = api_data.get("critic_last_run", "")

    # Delivery phase annotation for ACTIVE heading
    delivery_phase = get_delivery_phase()
    phase_annotation = ""
    if delivery_phase:
        phase_annotation = (
            f' <span class="st-todo" style="font-weight:normal">'
            f'[PHASE ({delivery_phase["current"]}/{delivery_phase["total"]})]'
            f'</span>'
        )

    # Agents section collapsed badge
    def _agents_badge(config):
        models_list = config.get('models', [])
        agents = config.get('agents', {})
        roles = ['architect', 'builder', 'qa']
        labels = []
        for role in roles:
            acfg = agents.get(role, {})
            mid = acfg.get('model', '')
            lbl = next((m.get('label', mid) for m in models_list if m.get('id') == mid), mid or '?')
            labels.append(lbl)
        # Group by label, sort by count descending then alphabetically
        counts = Counter(labels)
        segments = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        return ' | '.join(f'{c}x {lbl}' for lbl, c in segments)

    agents_badge = _agents_badge(CONFIG)
    agents_heading = "Agent Config (applies across all local isolations)" if isolations_active else "Agent Config"

    # Release checklist badge
    rc_steps, _rc_warnings, _rc_errors = get_release_checklist()
    rc_enabled = sum(1 for s in rc_steps if s.get("enabled"))
    rc_disabled = len(rc_steps) - rc_enabled
    rc_badge = (
        f'<span style="color:var(--purlin-status-good)">{rc_enabled} enabled</span>'
        f' <span style="color:var(--purlin-dim)">&middot; {rc_disabled} disabled</span>'
    )
    # Build release checklist rows HTML
    rc_rows_html = ""
    for s in rc_steps:
        disabled_cls = " rc-disabled" if not s.get("enabled") else ""
        source_tag = s.get("source", "").upper()
        source_badge = (
            f'<span style="background:var(--purlin-tag-fill);border:1px solid var(--purlin-tag-outline);'
            f'font-family:var(--font-body);font-size:10px;font-weight:700;text-transform:uppercase;'
            f'padding:0 4px;border-radius:2px;margin-right:4px;min-width:52px;text-align:center;display:inline-block">{source_tag}</span>'
        ) if source_tag else ""
        checked = " checked" if s.get("enabled") else ""
        sid_escaped = s["id"].replace("'", "\\'")
        fname_escaped = s["friendly_name"].replace("'", "\\'")
        rc_rows_html += (
            f'<tr class="{disabled_cls.strip()}" data-step-id="{s["id"]}">'
            f'<td onmousedown="rcHandleDown(event)" '
            f'style="width:24px;color:var(--purlin-dim);cursor:grab;text-align:center;user-select:none">\u28FF</td>'
            f'<td style="width:32px;text-align:right;font-family:monospace;'
            f'color:var(--purlin-muted)">{s["order"]}</td>'
            f'<td style="width:60px">{source_badge}</td>'
            f'<td style="flex:1">'
            f'<span class="feature-link" onclick="openStepModal(\'{sid_escaped}\')">'
            f'{s["friendly_name"]}</span></td>'
            f'<td style="width:32px;text-align:center">'
            f'<input type="checkbox"{checked} '
            f'onchange="rcToggle(\'{sid_escaped}\', this.checked)"></td>'
            f'</tr>'
        )

    # Compute summary badges for collapsed sections
    def _section_summary_badge(features_list):
        """Return a single priority badge for the Active section (spec 2.2.2):
        No badge if empty, TODO if any TODO with no FAIL/WARN, most-severe otherwise.
        Priority: FAIL > INFEASIBLE > DISPUTED > TODO.
        """
        if not features_list:
            return ''
        severity = {
            'FAIL': 6, 'INFEASIBLE': 5, 'DISPUTED': 4,
            'TODO': 3, 'BLOCKED': 2, 'DONE': 1, 'CLEAN': 1, 'N/A': 0,
        }
        all_statuses = []
        for e in features_list:
            for role in ('architect', 'builder', 'qa'):
                val = e.get(role)
                if val:
                    all_statuses.append(val)
        if not all_statuses:
            return '<span class="st-na">??</span>'
        # DONE only if every feature has all three roles fully satisfied
        def _satisfied(e):
            return (e.get('architect') in ('DONE',) and
                    e.get('builder') in ('DONE',) and
                    e.get('qa') in ('CLEAN', 'N/A'))
        if all(_satisfied(e) for e in features_list):
            return '<span class="st-done">DONE</span>'
        top = max(all_statuses, key=lambda s: severity.get(s, 0))
        css = ROLE_BADGE_CSS.get(top, 'st-na')
        return f'<span class="{css}">{top}</span>'

    active_summary = _section_summary_badge(active_features)
    complete_summary = ''  # Complete section shows no badge when collapsed (spec 2.2.2)

    # Workspace collapsed summary
    if not git_status:
        workspace_summary = '<span class="st-done">Clean Slate</span>'
    else:
        file_count = len(git_status.strip().splitlines())
        workspace_summary = f'<span class="st-todo">{file_count} file{"s" if file_count != 1 else ""} changed</span>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Purlin CDD Dashboard</title>
<script>
(function(){{var t=localStorage.getItem('purlin-theme');if(t==='light')document.documentElement.setAttribute('data-theme','light')}})();
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&family=Montserrat:wght@200;800;900&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.30.4/dist/cytoscape.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dagre@0.8.5/dist/dagre.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked@15.0.6/marked.min.js"></script>
<style>
:root{{
  --purlin-bg:#0B131A;--purlin-surface:#162531;--purlin-primary:#E2E8F0;
  --purlin-accent:#38BDF8;--purlin-muted:#94A3B8;--purlin-border:#1E293B;
  --purlin-status-good:#34D399;--purlin-status-todo:#FCD34D;
  --purlin-status-warning:#FB923C;--purlin-status-error:#F87171;
  --purlin-dim:#8B9DB0;--purlin-tag-fill:#1E293B;--purlin-tag-outline:#334155;
  --font-display:'Montserrat',sans-serif;--font-body:'Inter',sans-serif;
}}
[data-theme='light']{{
  --purlin-bg:#F5F6F0;--purlin-surface:#FFFFFF;--purlin-primary:#0C2637;
  --purlin-accent:#0284C7;--purlin-muted:#64748B;--purlin-border:#E2E8F0;
  --purlin-status-good:#059669;--purlin-status-todo:#D97706;
  --purlin-status-warning:#EA580C;--purlin-status-error:#DC2626;
  --purlin-dim:#94A3B8;--purlin-tag-fill:#F1F5F9;--purlin-tag-outline:#CBD5E1;
  --font-display:'Montserrat',sans-serif;--font-body:'Inter',sans-serif;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;overflow:hidden}}
body{{
  background:var(--purlin-bg);color:var(--purlin-muted);
  font-family:'Menlo','Monaco','Consolas',monospace;
  font-size:12px;display:flex;flex-direction:column;
}}
.hdr{{
  background:var(--purlin-surface);
  border-bottom:1px solid var(--purlin-border);flex-shrink:0;
  padding:6px 12px;
}}
.hdr-row1{{display:flex;justify-content:space-between;align-items:center}}
.hdr-row2{{display:flex;justify-content:space-between;align-items:center;margin-top:0;border-top:1px solid var(--purlin-border);padding-top:4px}}
.hdr-row1-left{{display:flex;align-items:center;gap:10px}}
.hdr-row1-right{{display:flex;align-items:center;gap:8px}}
.hdr-row2-left{{display:flex;align-items:center}}
.hdr-row2-right{{display:flex;align-items:center;gap:6px}}
.hdr-title-block{{display:flex;flex-direction:column}}
.hdr h1{{
  font-family:var(--font-display);font-size:14px;font-weight:200;
  color:var(--purlin-primary);white-space:nowrap;
  letter-spacing:0.12em;text-transform:uppercase;
}}
.project-name{{
  font-family:var(--font-body);font-size:14px;font-weight:500;
  color:var(--purlin-primary);line-height:1.2;
}}
.hdr-logo{{height:24px;width:auto;flex-shrink:0}}
.hdr-logo .logo-sketch{{stroke:var(--purlin-dim);fill:none}}
.hdr-logo .logo-fill{{fill:var(--purlin-primary)}}
.theme-toggle{{
  background:none;border:1px solid var(--purlin-border);
  color:var(--purlin-muted);border-radius:3px;padding:2px 6px;
  cursor:pointer;font-size:14px;line-height:1;
}}
.theme-toggle:hover{{color:var(--purlin-primary);border-color:var(--purlin-muted)}}
.view-toggle{{display:flex;gap:2px}}
.view-btn{{
  background:var(--purlin-surface);color:var(--purlin-muted);
  border:1px solid var(--purlin-border);
  border-radius:3px;padding:2px 10px;font-family:var(--font-body);font-size:11px;
  cursor:pointer;line-height:1.5;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;
}}
.view-btn:hover{{background:var(--purlin-border);color:var(--purlin-primary)}}
.view-btn.active{{
  background:var(--purlin-accent);color:#FFF;
  border-color:var(--purlin-accent);
}}
.btn-critic{{
  background:var(--purlin-surface);color:var(--purlin-muted);
  border:1px solid var(--purlin-border);
  border-radius:3px;padding:2px 8px;font-family:var(--font-body);font-size:11px;
  cursor:pointer;line-height:1.5;
}}
.btn-critic:hover{{background:var(--purlin-border);color:var(--purlin-primary)}}
.btn-critic:disabled{{cursor:not-allowed;opacity:.5}}
.btn-critic-err{{color:var(--purlin-status-error);font-size:10px;margin-right:4px}}
.agent-hdr{{display:grid;grid-template-columns:64px 140px 80px 60px 60px 60px;align-items:end;gap:6px;padding:2px 0 4px 0;border-bottom:1px solid var(--purlin-border)}}
.agent-hdr-cell{{font-size:10px;font-weight:600;color:var(--purlin-muted);text-transform:uppercase;letter-spacing:0.5px;line-height:1.2}}
.agent-hdr-cell.center{{text-align:center}}
.agent-row{{display:grid;grid-template-columns:64px 140px 80px 60px 60px 60px;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid var(--purlin-border)}}
.agent-row:last-child{{border-bottom:none}}
.agent-lbl{{font-family:var(--font-body);font-size:12px;font-weight:500;color:var(--purlin-primary);text-transform:uppercase}}
.agent-sel{{background:var(--purlin-bg);border:1px solid var(--purlin-border);border-radius:3px;color:var(--purlin-muted);font-size:11px;font-family:inherit;padding:2px 4px;outline:none;cursor:pointer;width:100%}}
.agent-sel:focus{{border-color:var(--purlin-accent)}}
.agent-chk-lbl{{display:flex;align-items:center;justify-content:center;cursor:pointer}}
.agent-chk-lbl.disabled{{opacity:0.4;cursor:default}}
#search-input{{
  background:var(--purlin-bg);border:1px solid var(--purlin-border);
  border-radius:3px;color:var(--purlin-muted);padding:3px 8px;
  font-size:11px;width:180px;font-family:inherit;outline:none;
}}
#search-input:focus{{border-color:var(--purlin-accent)}}
#search-input::placeholder,#new-isolation-name::placeholder{{color:var(--purlin-dim)}}
.dim{{color:var(--purlin-dim);font-size:0.9em}}
.content-area{{flex:1;overflow:hidden;display:flex;flex-direction:column}}
.view-panel{{display:none;flex:1;overflow:hidden;flex-direction:column}}
.view-panel.active{{display:flex}}
#status-view{{overflow-y:auto;padding:8px 12px}}
#map-view{{flex:1;position:relative}}
#cy{{width:100%;height:100%;background:var(--purlin-bg)}}
h2{{font-family:var(--font-body);font-size:13px;font-weight:700;color:var(--purlin-primary);margin-bottom:6px;border-bottom:1px solid var(--purlin-border);padding-bottom:4px;text-transform:uppercase;letter-spacing:0.1em}}
.section-hdr{{
  display:flex;align-items:center;gap:6px;cursor:pointer;
  padding:4px 0;user-select:none;
}}
.section-hdr h3{{
  font-family:var(--font-body);font-size:11px;font-weight:700;
  color:var(--purlin-dim);margin:0;
  text-transform:uppercase;letter-spacing:0.1em;flex:1;
  border-bottom:1px solid var(--purlin-border);padding-bottom:3px;
}}
.chevron{{
  font-size:10px;color:var(--purlin-dim);transition:transform 0.15s;
  display:inline-block;width:12px;text-align:center;flex-shrink:0;
}}
.chevron.expanded{{transform:rotate(90deg)}}
.section-badge{{font-size:10px;margin-left:4px;flex-shrink:0}}
.subsection-hdr{{padding-left:12px}}
.section-body{{overflow:hidden;transition:max-height 0.2s ease}}
.section-body.collapsed{{max-height:0 !important;overflow:hidden}}
.features{{background:var(--purlin-surface);border-radius:4px;padding:8px 10px;margin-bottom:10px}}
.ft{{width:100%;border-collapse:collapse}}
.ft th{{text-align:left;font-family:var(--font-body);font-weight:700;color:var(--purlin-dim);font-size:10px;text-transform:uppercase;letter-spacing:0.1em;padding:2px 6px;border-bottom:1px solid var(--purlin-border)}}
.ft th.badge-col{{text-align:center}}.col-abbr{{display:none}}@media(max-width:600px){{.col-full{{display:none}}.col-abbr{{display:inline}}}}
.ft td{{padding:2px 6px;line-height:1.5}}
.ft tr:hover{{background:var(--purlin-tag-fill)}}
.badge-cell{{text-align:center;width:70px}}
.feature-link{{color:var(--purlin-accent);cursor:pointer;text-decoration:none}}
.feature-link:hover{{text-decoration:underline}}
tr.rc-disabled td,tr.rc-disabled td *{{color:var(--purlin-dim) !important}}
tr.rc-drag-over td{{border-top:2px solid var(--purlin-accent)}}
.ctx{{background:var(--purlin-surface);border-radius:4px;padding:8px 10px}}
.clean{{color:var(--purlin-status-good)}}
.wip{{color:var(--purlin-status-todo);margin-bottom:2px}}
pre{{background:var(--purlin-bg);padding:6px;border-radius:3px;white-space:pre-wrap;word-wrap:break-word;max-height:100px;overflow-y:auto;margin-top:2px}}
.st-done{{color:var(--purlin-status-good);font-weight:bold}}
.st-todo{{color:var(--purlin-status-todo);font-weight:bold}}
.st-fail{{color:var(--purlin-status-error);font-weight:bold}}
.st-blocked{{color:var(--purlin-dim);font-weight:bold}}
.st-disputed{{color:var(--purlin-status-warning);font-weight:bold}}
.st-na{{color:var(--purlin-dim);font-weight:bold}}
/* Feature Detail Modal */
.modal-overlay{{
  display:none;position:fixed;inset:0;
  background:rgba(0,0,0,0.7);z-index:1000;
  justify-content:center;align-items:center;
}}
.modal-overlay.visible{{display:flex}}
.modal-content{{
  background:var(--purlin-surface);border:1px solid var(--purlin-border);
  border-radius:6px;width:700px;max-width:90vw;
  max-height:80vh;display:flex;flex-direction:column;
  position:relative;
}}
.modal-header{{
  display:flex;justify-content:space-between;align-items:center;
  padding:10px 14px;border-bottom:1px solid var(--purlin-border);flex-shrink:0;
}}
.modal-header h2{{font-size:13px;color:var(--purlin-primary);margin:0;border:0;padding:0}}
.modal-close{{
  background:none;border:1px solid var(--purlin-border);color:var(--purlin-muted);
  cursor:pointer;font-size:14px;width:24px;height:24px;
  border-radius:3px;display:flex;align-items:center;
  justify-content:center;line-height:1;
}}
.modal-close:hover{{background:var(--purlin-tag-fill);color:var(--purlin-primary);border-color:var(--purlin-muted)}}
.modal-tabs{{
  display:flex;gap:0;border-bottom:1px solid var(--purlin-border);
  padding:0 14px;flex-shrink:0;
}}
.modal-tab{{
  padding:6px 12px;font-size:11px;color:var(--purlin-dim);
  cursor:pointer;border-bottom:2px solid transparent;
  font-family:inherit;background:none;border-top:0;border-left:0;border-right:0;
}}
.modal-tab:hover{{color:var(--purlin-primary)}}
.modal-tab.active{{color:var(--purlin-accent);border-bottom-color:var(--purlin-accent)}}
.modal-body{{
  padding:14px;overflow-y:auto;flex:1;
  line-height:1.6;color:var(--purlin-muted);
}}
.modal-body h1,.modal-body h2,.modal-body h3{{color:var(--purlin-primary);margin:12px 0 6px}}
.modal-body h1{{font-size:16px}}
.modal-body h2{{font-size:14px;border:0;padding:0}}
.modal-body h3{{font-size:12px}}
.modal-body p{{margin:6px 0}}
.modal-body ul,.modal-body ol{{margin:6px 0 6px 20px}}
.modal-body li{{margin:2px 0}}
.modal-body code{{
  background:var(--purlin-bg);padding:1px 4px;border-radius:2px;
  font-size:11px;color:var(--purlin-accent);
}}
.modal-body pre{{background:var(--purlin-bg);padding:8px;border-radius:3px;overflow-x:auto;margin:6px 0}}
.modal-body pre code{{padding:0;background:none}}
.modal-body blockquote{{border-left:3px solid var(--purlin-accent);padding-left:10px;color:var(--purlin-dim);margin:6px 0}}
</style>
</head>
<body>
<div class="hdr">
  <div class="hdr-row1">
    <div class="hdr-row1-left">
      <svg class="hdr-logo" viewBox="140 100 720 420" xmlns="http://www.w3.org/2000/svg">
        <g class="logo-sketch" stroke-width="2">
          <line x1="500" y1="120" x2="500" y2="480" stroke-dasharray="8,8"/>
          <line x1="500" y1="145" x2="170" y2="409"/>
          <line x1="500" y1="145" x2="830" y2="409"/>
          <line x1="400" y1="210" x2="400" y2="255"/>
          <line x1="600" y1="210" x2="600" y2="255"/>
        </g>
        <polyline class="logo-fill" points="400,280 500,390 600,280" fill="none" stroke="currentColor" stroke-width="14" stroke-linejoin="miter" style="fill:none;stroke:var(--purlin-primary)"/>
        <path class="logo-fill" d="M500 160L190 408L190 440L810 440L810 408ZM500 200L262.5 390L737.5 390Z" fill-rule="evenodd"/>
      </svg>
      <div class="hdr-title-block">
        <h1>Purlin CDD Dashboard</h1>
        <span class="project-name">{PROJECT_NAME}</span>
      </div>
    </div>
    <div class="hdr-row1-right">
      <span id="last-refreshed" style="font-family:'Menlo','Monaco','Consolas',monospace;color:var(--purlin-dim);font-size:11px">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
      <button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()" title="Toggle theme">
        <span id="theme-icon-sun" style="display:none">&#9788;</span>
        <span id="theme-icon-moon">&#9790;</span>
      </button>
    </div>
  </div>
  <div class="hdr-row2">
    <div class="hdr-row2-left">
      <div class="view-toggle">
        <button class="view-btn active" id="btn-status" onclick="switchView('status')">Status</button>
        <button class="view-btn" id="btn-map" onclick="switchView('map')">Spec Map</button>
      </div>
    </div>
    <div class="hdr-row2-right">
      <span id="critic-err" class="btn-critic-err"></span>
      <button id="btn-critic" class="btn-critic" onclick="runCritic()">Run Critic</button>
      <input type="text" id="search-input" placeholder="Filter..." />
    </div>
  </div>
</div>
<div class="content-area">
  <!-- Status View -->
  <div class="view-panel active" id="status-view">
    <span id="critic-last-run-data" style="display:none" data-ts="{critic_last_run_ts}"></span>
    <div class="features">
      <div class="section-hdr" onclick="toggleSection('active-section')">
        <span class="chevron expanded" id="active-section-chevron">&#9654;</span>
        <h3>Active ({active_count}){phase_annotation}</h3>
        <span class="section-badge" id="active-section-badge" style="display:none">{active_summary}</span>
      </div>
      <div class="section-body" id="active-section">
        {active_html or '<p class="dim">No active features.</p>'}
      </div>
      <div class="section-hdr" onclick="toggleSection('complete-section')">
        <span class="chevron" id="complete-section-chevron">&#9654;</span>
        <h3>Complete ({complete_count})</h3>
        <span class="section-badge" id="complete-section-badge">{complete_summary}</span>
      </div>
      <div class="section-body collapsed" id="complete-section">
        {complete_html or '<p class="dim">None complete.</p>'}
        {overflow_html}
      </div>
    </div>
    <div class="ctx">
      <div class="section-hdr" onclick="toggleSection('workspace-section')">
        <span class="chevron" id="workspace-section-chevron">&#9654;</span>
        <h3>Workspace</h3>
        <span class="section-badge" id="workspace-section-badge">{workspace_summary}</span>
      </div>
      <div class="section-body collapsed" id="workspace-section">
        {git_html}
        <p class="dim" style="margin-top:4px">{last_commit}</p>
      </div>
    </div>
    <div class="ctx" style="margin-top:10px">
      <div class="section-hdr" onclick="toggleSection('isolation-section')">
        <span class="chevron" id="isolation-section-chevron">&#9654;</span>
        <span id="isolation-heading" data-expanded="ISOLATED TEAMS" data-collapsed-text="{iso_badge_text}" style="font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--purlin-dim);border-bottom:1px solid var(--purlin-border);padding-bottom:3px;flex:1">ISOLATED TEAMS</span>
        <span class="section-badge" id="isolation-section-badge" style="display:none">{isolation_badge}</span>
      </div>
      <div class="section-body collapsed" id="isolation-section">
        {creation_row_html}
        {isolation_html}
      </div>
    </div>
    <div class="ctx" style="margin-top:10px">
      <div class="section-hdr" onclick="toggleSection('agents-section')">
        <span class="chevron" id="agents-section-chevron">&#9654;</span>
        <h3>{agents_heading}</h3>
        <span class="section-badge" id="agents-section-badge">{agents_badge}</span>
      </div>
      <div class="section-body collapsed" id="agents-section">
        <div id="agents-rows" style="margin-bottom:8px"></div>
      </div>
    </div>
    <div class="ctx" style="margin-top:10px">
      <div class="section-hdr" onclick="toggleSection('release-checklist')">
        <span class="chevron" id="release-checklist-chevron">&#9654;</span>
        <h3>Release Checklist</h3>
        <span class="section-badge" id="release-checklist-badge">{rc_badge}</span>
      </div>
      <div class="section-body collapsed" id="release-checklist">
        <table class="ft" style="width:100%"><tbody id="rc-tbody">
          {rc_rows_html}
        </tbody></table>
      </div>
    </div>
  </div>
  <!-- Spec Map View -->
  <div class="view-panel" id="map-view">
    <div id="cy"></div>
    <button id="recenter-btn" class="btn-critic" style="position:absolute;bottom:12px;right:12px;font-size:11px;padding:4px 10px;z-index:10" onclick="recenterGraph()">Recenter Graph</button>
  </div>
</div>

<!-- Feature Detail Modal -->
<div class="modal-overlay" id="modal-overlay">
  <div class="modal-content">
    <div class="modal-header">
      <h2 id="modal-title">Feature</h2>
      <button class="modal-close" id="modal-close" title="Close">X</button>
    </div>
    <div class="modal-tabs" id="modal-tabs" style="display:none">
      <button class="modal-tab active" data-tab="spec" onclick="switchModalTab('spec')">Specification</button>
      <button class="modal-tab" data-tab="impl" onclick="switchModalTab('impl')">Implementation Notes</button>
    </div>
    <div class="modal-body" id="modal-body"></div>
  </div>
</div>

<!-- Kill Isolation Modal -->
<div class="modal-overlay" id="kill-modal-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:200;align-items:center;justify-content:center">
  <div style="background:var(--purlin-bg);border:1px solid var(--purlin-border);border-radius:6px;max-width:480px;width:90%;padding:16px">
    <h3 style="margin:0 0 10px;font-size:14px" id="kill-modal-title">Kill Isolation</h3>
    <div id="kill-modal-body"></div>
    <div id="kill-modal-checkbox-row" style="display:none;margin-top:10px">
      <label style="font-size:12px;cursor:pointer">
        <input type="checkbox" id="kill-modal-checkbox" onchange="killCheckboxChanged(this)">
        I understand, the branch still exists
      </label>
    </div>
    <div style="margin-top:12px;text-align:right">
      <button class="btn-critic" onclick="killModalCancel()" style="font-size:11px;margin-right:6px">Cancel</button>
      <button class="btn-critic" id="kill-modal-confirm" onclick="killModalConfirm()" style="font-size:11px">Confirm</button>
    </div>
  </div>
</div>

<!-- Step Detail Modal -->
<div class="modal-overlay" id="step-modal-overlay">
  <div class="modal-content">
    <div class="modal-header">
      <h2 id="step-modal-title">Step</h2>
      <button class="modal-close" onclick="closeStepModal()" title="Close">X</button>
    </div>
    <div class="modal-body" id="step-modal-body" style="padding:14px;overflow-y:auto"></div>
    <div style="padding:8px 14px;border-top:1px solid var(--purlin-border);text-align:right">
      <button class="btn-critic" onclick="closeStepModal()">Close</button>
    </div>
  </div>
</div>

<script>
// ============================
// State
// ============================
var currentView = 'status';
var cy = null;
var graphData = null;
var userModifiedView = false;
var userModifiedNodes = false;
var lastContentHash = null;
var mapRefreshTimer = null;
var inactivityTimer = null;
var INACTIVITY_TIMEOUT = 300000; // 5 minutes
var statusRefreshTimer = null;
var modalCache = {{}};

// ============================
// Theme Toggle
// ============================
function getThemeColors() {{
  var s = getComputedStyle(document.documentElement);
  return {{
    bg: s.getPropertyValue('--purlin-bg').trim(),
    surface: s.getPropertyValue('--purlin-surface').trim(),
    primary: s.getPropertyValue('--purlin-primary').trim(),
    accent: s.getPropertyValue('--purlin-accent').trim(),
    muted: s.getPropertyValue('--purlin-muted').trim(),
    border: s.getPropertyValue('--purlin-border').trim(),
    dim: s.getPropertyValue('--purlin-dim').trim(),
  }};
}}

function updateThemeIcons() {{
  var isLight = document.documentElement.getAttribute('data-theme') === 'light';
  document.getElementById('theme-icon-sun').style.display = isLight ? '' : 'none';
  document.getElementById('theme-icon-moon').style.display = isLight ? 'none' : '';
}}

function toggleTheme() {{
  var html = document.documentElement;
  var isLight = html.getAttribute('data-theme') === 'light';
  if (isLight) {{
    html.removeAttribute('data-theme');
    localStorage.setItem('purlin-theme', 'dark');
  }} else {{
    html.setAttribute('data-theme', 'light');
    localStorage.setItem('purlin-theme', 'light');
  }}
  updateThemeIcons();
  if (currentView === 'map' && graphData) renderGraph();
}}

updateThemeIcons();

// ============================
// View Toggle + Hash Routing
// ============================
function switchView(view) {{
  currentView = view;
  document.getElementById('status-view').classList.toggle('active', view === 'status');
  document.getElementById('map-view').classList.toggle('active', view === 'map');
  document.getElementById('btn-status').classList.toggle('active', view === 'status');
  document.getElementById('btn-map').classList.toggle('active', view === 'map');
  window.location.hash = '#' + view;

  if (view === 'map') {{
    userModifiedView = false;
    userModifiedNodes = false;
    startMapRefresh();
    if (!graphData) loadGraph();
    else {{ renderGraph(); }}
  }} else {{
    stopMapRefresh();
    if (inactivityTimer) {{ clearTimeout(inactivityTimer); inactivityTimer = null; }}
  }}

  applySearchFilter();
}}

function initFromHash() {{
  var hash = window.location.hash.replace('#', '');
  if (hash === 'map') switchView('map');
  else switchView('status');
}}

window.addEventListener('hashchange', function() {{
  var hash = window.location.hash.replace('#', '');
  if (hash === 'map' && currentView !== 'map') switchView('map');
  else if (hash !== 'map' && currentView !== 'status') switchView('status');
}});

// ============================
// Status View Auto-Refresh
// ============================
function updateTimestamp() {{
  var el = document.getElementById('last-refreshed');
  if (el) {{
    var d = new Date();
    var pad = function(n) {{ return n < 10 ? '0' + n : '' + n; }};
    el.textContent = d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()) +
      ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }}
}}

function refreshStatus() {{
  if (rcIsolationPending) return;
  // Skip refresh while user is typing in the isolation name input
  var isoInput = document.getElementById('new-isolation-name');
  if (isoInput && document.activeElement === isoInput) return;
  // Save isolation name input value before DOM refresh
  var _isoHadFocus = false;
  if (isoInput) _pendingIsolationName = isoInput.value;
  return fetch('/?_t=' + Date.now())
    .then(function(r) {{ return r.text(); }})
    .then(function(html) {{
      var parser = new DOMParser();
      var doc = parser.parseFromString(html, 'text/html');
      var newStatusView = doc.getElementById('status-view');
      if (newStatusView) {{
        var current = document.getElementById('status-view');
        // Preserve release checklist rows during pending save to prevent snap-back
        var savedRcTbody = null;
        if (rcPendingSave) {{
          var rcT = document.getElementById('rc-tbody');
          if (rcT) savedRcTbody = rcT.innerHTML;
        }}
        current.innerHTML = newStatusView.innerHTML;
        if (savedRcTbody) {{
          var rcT = document.getElementById('rc-tbody');
          if (rcT) rcT.innerHTML = savedRcTbody;
        }}
        // Restore section states from localStorage
        applySectionStates();
        // Re-apply search filter
        applySearchFilter();
        // Re-populate agents section (dynamic JS content cleared by innerHTML replace)
        initAgentsSection();
        // Incremental refresh for release checklist (diff-based, skips during pending saves)
        refreshReleaseChecklist();
        // Update Run Critic button annotation (Section 2.7)
        updateCriticLabel();
        // Restore isolation name input value and focus after DOM refresh
        var restoredInput = document.getElementById('new-isolation-name');
        if (restoredInput && _pendingIsolationName) {{
          restoredInput.value = _pendingIsolationName;
          validateIsolationName(restoredInput);
        }}
        if (restoredInput && _isoHadFocus) {{
          restoredInput.focus();
        }}
      }}
      updateTimestamp();
    }})
    .catch(function() {{}});
}}

statusRefreshTimer = setInterval(refreshStatus, 5000);

// ============================
// Collapsible Sections with localStorage persistence
// ============================
function getSectionStates() {{
  try {{
    var raw = localStorage.getItem('purlin-section-states');
    return raw ? JSON.parse(raw) : {{}};
  }} catch(e) {{ return {{}}; }}
}}

function saveSectionStates() {{
  var states = {{}};
  ['active-section', 'complete-section', 'workspace-section', 'agents-section', 'release-checklist', 'isolation-section'].forEach(function(id) {{
    var el = document.getElementById(id);
    if (el) states[id] = el.classList.contains('collapsed') ? 'collapsed' : 'expanded';
  }});
  localStorage.setItem('purlin-section-states', JSON.stringify(states));
}}

function applySectionStates() {{
  var states = getSectionStates();
  ['active-section', 'complete-section', 'workspace-section', 'agents-section', 'release-checklist', 'isolation-section'].forEach(function(id) {{
    var saved = states[id];
    if (!saved) return;
    var body = document.getElementById(id);
    var chevron = document.getElementById(id + '-chevron');
    var badge = document.getElementById(id + '-badge');
    if (!body) return;
    if (saved === 'collapsed') {{
      body.classList.add('collapsed');
      if (chevron) chevron.classList.remove('expanded');
      if (badge) badge.style.display = '';
    }} else {{
      body.classList.remove('collapsed');
      if (chevron) chevron.classList.add('expanded');
      if (badge) badge.style.display = 'none';
    }}
  }});
  // Apply isolation sub-heading label swap
  applyIsolationHeadingState();
}}

function toggleSection(sectionId) {{
  var body = document.getElementById(sectionId);
  var chevron = document.getElementById(sectionId + '-chevron');
  var badge = document.getElementById(sectionId + '-badge');
  if (!body) return;
  var isCollapsed = body.classList.contains('collapsed');
  if (isCollapsed) {{
    body.classList.remove('collapsed');
    if (chevron) chevron.classList.add('expanded');
    if (badge) badge.style.display = 'none';
  }} else {{
    body.classList.add('collapsed');
    if (chevron) chevron.classList.remove('expanded');
    if (badge) badge.style.display = '';
  }}
  // Isolation sub-heading: swap heading text on collapse/expand
  if (sectionId === 'isolation-section') {{
    applyIsolationHeadingState();
  }}
  saveSectionStates();
}}

function applyIsolationHeadingState() {{
  var heading = document.getElementById('isolation-heading');
  var body = document.getElementById('isolation-section');
  if (!heading || !body) return;
  var isCollapsed = body.classList.contains('collapsed');
  if (isCollapsed) {{
    var collapsedText = heading.getAttribute('data-collapsed-text');
    if (collapsedText) {{
      heading.textContent = collapsedText;
      heading.className = '';
      heading.style.fontSize = '11px';
      heading.style.fontWeight = '700';
      heading.style.letterSpacing = '0.1em';
      heading.style.textTransform = 'uppercase';
      heading.style.color = 'var(--purlin-muted)';
    }}
  }} else {{
    heading.textContent = heading.getAttribute('data-expanded') || 'ISOLATED TEAMS';
    heading.className = '';
    heading.style.fontSize = '11px';
    heading.style.fontWeight = '700';
    heading.style.letterSpacing = '0.1em';
    heading.style.textTransform = 'uppercase';
    heading.style.color = 'var(--purlin-dim)';
  }}
}}

// ============================
// Release Checklist
// ============================
var rcStepsCache = null;
var rcPendingSave = false;
var rcIsolationPending = false;

function loadReleaseChecklist() {{
  fetch('/release-checklist')
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      rcStepsCache = data.steps || [];
    }})
    .catch(function() {{}});
}}

loadReleaseChecklist();

function refreshReleaseChecklist() {{
  if (rcPendingSave) return;
  fetch('/release-checklist')
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (rcPendingSave) return;
      var newSteps = data.steps || [];
      if (JSON.stringify(newSteps) === JSON.stringify(rcStepsCache)) return;
      rcStepsCache = newSteps;
      var tbody = document.getElementById('rc-tbody');
      if (!tbody) return;
      var existingRows = Array.from(tbody.querySelectorAll('tr'));
      var existingIds = existingRows.map(function(r) {{ return r.dataset.stepId; }});
      var newIds = newSteps.map(function(s) {{ return s.id; }});
      // Check if order changed
      var orderChanged = existingIds.join(',') !== newIds.join(',');
      if (orderChanged) {{
        // Rebuild rows in new order
        newSteps.forEach(function(step) {{
          var row = tbody.querySelector('tr[data-step-id="' + step.id + '"]');
          if (row) tbody.appendChild(row);
        }});
        rcUpdateNumbers();
      }}
      // Diff-update enabled state per row
      newSteps.forEach(function(step) {{
        var row = tbody.querySelector('tr[data-step-id="' + step.id + '"]');
        if (!row) return;
        var cb = row.querySelector('input[type=checkbox]');
        if (cb && cb.checked !== step.enabled) {{
          cb.checked = step.enabled;
          if (step.enabled) {{
            row.classList.remove('rc-disabled');
          }} else {{
            row.classList.add('rc-disabled');
          }}
        }}
      }});
      rcUpdateBadge();
    }})
    .catch(function() {{}});
}}

var rcDragRow = null;

function rcHandleDown(e) {{
  e.preventDefault();
  var td = e.target.closest('td');
  var row = td ? td.closest('tr') : null;
  if (!row) return;
  rcDragRow = row;
  row.style.opacity = '0.4';
  document.addEventListener('mousemove', rcMouseMove);
  document.addEventListener('mouseup', rcMouseUp);
}}

function rcMouseMove(e) {{
  if (!rcDragRow) return;
  e.preventDefault();
  var tbody = document.getElementById('rc-tbody');
  if (!tbody) return;
  var rows = Array.from(tbody.querySelectorAll('tr'));
  rows.forEach(function(r) {{ r.classList.remove('rc-drag-over'); }});
  for (var i = 0; i < rows.length; i++) {{
    var rect = rows[i].getBoundingClientRect();
    if (e.clientY >= rect.top && e.clientY <= rect.bottom && rows[i] !== rcDragRow) {{
      rows[i].classList.add('rc-drag-over');
      break;
    }}
  }}
}}

function rcMouseUp(e) {{
  document.removeEventListener('mousemove', rcMouseMove);
  document.removeEventListener('mouseup', rcMouseUp);
  if (!rcDragRow) return;
  rcDragRow.style.opacity = '1';
  var tbody = document.getElementById('rc-tbody');
  if (!tbody) {{ rcDragRow = null; return; }}
  var rows = Array.from(tbody.querySelectorAll('tr'));
  rows.forEach(function(r) {{ r.classList.remove('rc-drag-over'); }});
  var targetRow = null;
  for (var i = 0; i < rows.length; i++) {{
    var rect = rows[i].getBoundingClientRect();
    if (e.clientY >= rect.top && e.clientY <= rect.bottom && rows[i] !== rcDragRow) {{
      targetRow = rows[i];
      break;
    }}
  }}
  if (targetRow) {{
    var srcIdx = rows.indexOf(rcDragRow);
    var tgtIdx = rows.indexOf(targetRow);
    if (srcIdx >= 0 && tgtIdx >= 0) {{
      if (srcIdx < tgtIdx) {{
        tbody.insertBefore(rcDragRow, targetRow.nextSibling);
      }} else {{
        tbody.insertBefore(rcDragRow, targetRow);
      }}
      rcUpdateNumbers();
      rcPersistConfig();
    }}
  }}
  rcDragRow = null;
}}

function rcUpdateNumbers() {{
  var rows = document.querySelectorAll('#rc-tbody tr');
  rows.forEach(function(row, i) {{
    var numCell = row.querySelectorAll('td')[1];
    if (numCell) numCell.textContent = (i + 1);
  }});
}}

function rcToggle(stepId, enabled) {{
  var row = document.querySelector('tr[data-step-id="' + stepId + '"]');
  if (row) {{
    if (enabled) {{
      row.classList.remove('rc-disabled');
    }} else {{
      row.classList.add('rc-disabled');
    }}
  }}
  rcPersistConfig();
  rcUpdateBadge();
}}

function rcUpdateBadge() {{
  var rows = document.querySelectorAll('#rc-tbody tr');
  var en = 0, dis = 0;
  rows.forEach(function(r) {{
    var cb = r.querySelector('input[type=checkbox]');
    if (cb && cb.checked) en++; else dis++;
  }});
  var badge = document.getElementById('release-checklist-badge');
  if (badge) {{
    badge.innerHTML = '<span style="color:var(--purlin-status-good)">' + en + ' enabled</span>' +
      ' <span style="color:var(--purlin-dim)">&middot; ' + dis + ' disabled</span>';
  }}
}}

function rcPersistConfig() {{
  var rows = document.querySelectorAll('#rc-tbody tr');
  var steps = [];
  rows.forEach(function(row) {{
    var cb = row.querySelector('input[type=checkbox]');
    steps.push({{id: row.dataset.stepId, enabled: cb ? cb.checked : true}});
  }});
  // Optimistically update cache to match DOM order/state
  if (rcStepsCache) {{
    var cacheMap = {{}};
    rcStepsCache.forEach(function(s) {{ cacheMap[s.id] = s; }});
    rcStepsCache = steps.map(function(s) {{
      var full = cacheMap[s.id];
      if (full) {{ full = JSON.parse(JSON.stringify(full)); full.enabled = s.enabled; return full; }}
      return s;
    }});
  }}
  rcPendingSave = true;
  fetch('/release-checklist/config', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{steps: steps}})
  }})
  .then(function(r) {{ return r.json(); }})
  .then(function() {{
    rcPendingSave = false;
    loadReleaseChecklist();
  }})
  .catch(function() {{ rcPendingSave = false; }});
}}

function openStepModal(stepId) {{
  if (!rcStepsCache) return;
  var step = null;
  for (var i = 0; i < rcStepsCache.length; i++) {{
    if (rcStepsCache[i].id === stepId) {{ step = rcStepsCache[i]; break; }}
  }}
  if (!step) return;

  var titleEl = document.getElementById('step-modal-title');
  var bodyEl = document.getElementById('step-modal-body');
  var source = (step.source || '').toUpperCase();
  var sourceBadge = source ? ('<span style="background:var(--purlin-tag-fill);border:1px solid var(--purlin-tag-outline);'
    + 'font-family:var(--font-body);font-size:10px;font-weight:700;text-transform:uppercase;'
    + 'padding:0 4px;border-radius:2px;margin-left:8px;min-width:52px;text-align:center;display:inline-block">' + source + '</span>') : '';
  titleEl.innerHTML = step.friendly_name + sourceBadge;

  var html = '';
  if (step.description) {{
    html += '<div style="margin-bottom:12px"><div style="font-family:var(--font-body);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--purlin-muted);margin-bottom:4px">DESCRIPTION</div>';
    html += '<div style="color:var(--purlin-primary);font-size:12px;line-height:1.5">' + step.description + '</div></div>';
  }}
  if (step.code !== null && step.code !== undefined) {{
    html += '<div style="margin-bottom:12px"><div style="font-family:var(--font-body);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--purlin-muted);margin-bottom:4px">CODE</div>';
    html += '<pre style="background:var(--purlin-surface);padding:8px;border-radius:3px;border:1px solid var(--purlin-border);font-size:12px;color:var(--purlin-primary)">' + step.code + '</pre></div>';
  }}
  if (step.agent_instructions !== null && step.agent_instructions !== undefined) {{
    html += '<div style="margin-bottom:12px"><div style="font-family:var(--font-body);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--purlin-muted);margin-bottom:4px">AGENT INSTRUCTIONS</div>';
    html += '<div style="color:var(--purlin-primary);font-size:12px;line-height:1.5">' + step.agent_instructions + '</div></div>';
  }}
  bodyEl.innerHTML = html;
  document.getElementById('step-modal-overlay').classList.add('visible');
}}

function closeStepModal() {{
  document.getElementById('step-modal-overlay').classList.remove('visible');
}}

document.getElementById('step-modal-overlay').addEventListener('click', function(e) {{
  if (e.target === this) closeStepModal();
}});

document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape' && document.getElementById('step-modal-overlay').classList.contains('visible')) {{
    closeStepModal();
  }}
}});

// ============================
// Run Critic (Section 2.7 — last-run annotation)
// ============================
function updateCriticLabel() {{
  var el = document.getElementById('critic-last-run-data');
  var btn = document.getElementById('btn-critic');
  if (!el || !btn || btn.disabled) return;
  var ts = el.getAttribute('data-ts');
  if (!ts) {{ btn.textContent = 'Run Critic'; return; }}
  var elapsed = (Date.now() - new Date(ts).getTime()) / 1000;
  if (elapsed < 60) {{ btn.textContent = 'Run Critic'; return; }}
  if (elapsed < 3600) {{ btn.textContent = 'Run Critic (' + Math.floor(elapsed / 60) + 'm)'; return; }}
  if (elapsed < 86400) {{ btn.textContent = 'Run Critic (' + Math.floor(elapsed / 3600) + 'h)'; return; }}
  btn.textContent = 'Run Critic (' + Math.floor(elapsed / 86400) + 'd)';
}}

function runCritic() {{
  var btn = document.getElementById('btn-critic');
  var err = document.getElementById('critic-err');
  btn.disabled = true; btn.textContent = 'Running\u2026'; err.textContent = '';
  fetch('/run-critic', {{method: 'POST'}})
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{
      if (d.status === 'ok') {{
        refreshStatus().then(function() {{ btn.disabled = false; }});
      }} else {{
        err.textContent = 'Critic run failed'; btn.disabled = false; updateCriticLabel();
      }}
    }})
    .catch(function() {{ err.textContent = 'Critic run failed'; btn.disabled = false; updateCriticLabel(); }});
}}

// ============================
// Isolation Controls
// ============================
var _killTargetName = '';
var _pendingIsolationName = '';

function validateIsolationName(input) {{
  var btn = document.getElementById('btn-create-isolation');
  var hint = document.getElementById('isolation-name-hint');
  var val = input.value;
  var valid = /^[a-zA-Z0-9_-]+$/.test(val) && val.length >= 1 && val.length <= 12;
  if (btn) btn.disabled = !valid;
  if (hint) {{
    if (val.length > 0 && !valid) {{
      hint.style.display = '';
      if (val.length > 12) hint.textContent = 'Max 12 characters';
      else hint.textContent = 'Only letters, numbers, hyphens, underscores';
    }} else {{
      hint.style.display = 'none';
    }}
  }}
}}

function createIsolation() {{
  var input = document.getElementById('new-isolation-name');
  var errEl = document.getElementById('isolation-ctrl-err');
  var btn = document.getElementById('btn-create-isolation');
  if (!input || !input.value) return;
  var name = input.value;
  if (errEl) errEl.textContent = '';
  if (btn) btn.disabled = true;
  rcIsolationPending = true;
  fetch('/isolate/create', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{name:name}}) }})
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{
      rcIsolationPending = false;
      if (d.status === 'ok') {{ input.value = ''; _pendingIsolationName = ''; refreshStatus(); }}
      else {{ if (errEl) errEl.textContent = d.error || 'Failed'; if (btn) btn.disabled = false; }}
    }})
    .catch(function() {{ rcIsolationPending = false; if (errEl) errEl.textContent = 'Request failed'; if (btn) btn.disabled = false; }});
}}

function killIsolationPrompt(name) {{
  _killTargetName = name;
  rcIsolationPending = true;
  fetch('/isolate/kill', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{name:name, dry_run:true}}) }})
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{ rcIsolationPending = false; showKillModal(name, d); }})
    .catch(function() {{ rcIsolationPending = false; }});
}}

function showKillModal(name, dryRunData) {{
  var overlay = document.getElementById('kill-modal-overlay');
  if (!overlay) return;
  var title = document.getElementById('kill-modal-title');
  var body = document.getElementById('kill-modal-body');
  var confirmBtn = document.getElementById('kill-modal-confirm');
  var checkbox = document.getElementById('kill-modal-checkbox');
  var checkboxRow = document.getElementById('kill-modal-checkbox-row');
  if (title) title.textContent = 'Kill Isolation: ' + name;
  if (checkbox) {{ checkbox.checked = false; }}
  if (checkboxRow) {{ checkboxRow.style.display = 'none'; }}
  if (confirmBtn) {{ confirmBtn.disabled = false; }}

  if (dryRunData.dirty) {{
    // Dirty: list files, disable confirm
    var html = '<p style="color:var(--purlin-status-error);font-weight:600">Cannot kill: uncommitted changes.</p>';
    html += '<p style="margin-top:6px">Commit or stash changes before killing this isolation:</p><ul>';
    (dryRunData.dirty_files || []).forEach(function(f) {{
      html += '<li>' + f + '</li>';
    }});
    html += '</ul>';
    if (body) body.innerHTML = html;
    if (confirmBtn) confirmBtn.disabled = true;
  }} else if (dryRunData.unsynced) {{
    // Unsynced: warn, require checkbox
    var html = '<p style="color:var(--purlin-status-warning);font-weight:600">Branch has ' + dryRunData.unsynced_commits + ' commit(s) not merged to main.</p>';
    html += '<p style="margin-top:6px">Removing the worktree does <strong>not</strong> delete the branch &mdash; it can be re-added later.</p>';
    if (body) body.innerHTML = html;
    if (checkboxRow) checkboxRow.style.display = '';
    if (confirmBtn) confirmBtn.disabled = true;
  }} else {{
    // Clean: simple confirm
    if (body) body.innerHTML = '<p>Remove isolation <strong>' + name + '</strong>?</p>';
  }}
  overlay.style.display = 'flex';
}}

function killCheckboxChanged(cb) {{
  var confirmBtn = document.getElementById('kill-modal-confirm');
  if (confirmBtn) confirmBtn.disabled = !cb.checked;
}}

function killModalConfirm() {{
  var overlay = document.getElementById('kill-modal-overlay');
  var errEl = document.getElementById('isolation-ctrl-err');
  if (overlay) overlay.style.display = 'none';
  rcIsolationPending = true;
  fetch('/isolate/kill', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{name:_killTargetName, force:true}}) }})
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{
      rcIsolationPending = false;
      if (d.status === 'ok') {{ refreshStatus(); }}
      else {{ if (errEl) errEl.textContent = d.error || 'Kill failed'; }}
    }})
    .catch(function() {{ rcIsolationPending = false; if (errEl) errEl.textContent = 'Kill request failed'; }});
}}

function killModalCancel() {{
  var overlay = document.getElementById('kill-modal-overlay');
  if (overlay) overlay.style.display = 'none';
}}

// ============================
// Search/Filter
// ============================
document.getElementById('search-input').addEventListener('input', function() {{
  applySearchFilter();
}});

function applySearchFilter() {{
  var query = document.getElementById('search-input').value.trim().toLowerCase();

  // Status view: filter table rows
  if (currentView === 'status') {{
    var rows = document.querySelectorAll('#status-view .ft tbody tr');
    rows.forEach(function(row) {{
      var text = row.textContent.toLowerCase();
      row.style.display = (!query || text.includes(query)) ? '' : 'none';
    }});

    // Per spec 2.2.3: hide entire section when no rows match
    ['active-section', 'complete-section'].forEach(function(sectionId) {{
      var body = document.getElementById(sectionId);
      if (!body) return;
      var hdr = body.previousElementSibling;
      if (!hdr || !hdr.classList.contains('section-hdr')) return;
      var sectionRows = body.querySelectorAll('.ft tbody tr');
      if (sectionRows.length === 0) return;
      var allHidden = query && Array.from(sectionRows).every(function(r) {{
        return r.style.display === 'none';
      }});
      hdr.style.display = allHidden ? 'none' : '';
      body.style.display = allHidden ? 'none' : '';
    }});
  }}

  // Spec Map view: filter graph nodes
  if (currentView === 'map' && cy) {{
    if (!query) {{
      cy.elements().removeClass('search-hidden');
      return;
    }}
    cy.nodes().forEach(function(node) {{
      var name = (node.data('friendlyName') || node.data('label') || '').toLowerCase();
      var file = (node.data('file') || '').toLowerCase();
      var filename = (node.data('filename') || '').toLowerCase();
      if (name.includes(query) || file.includes(query) || filename.includes(query)) {{
        node.removeClass('search-hidden');
      }} else {{
        node.addClass('search-hidden');
      }}
    }});
    cy.edges().forEach(function(edge) {{
      var src = edge.source();
      var tgt = edge.target();
      if (src.hasClass('search-hidden') && tgt.hasClass('search-hidden')) {{
        edge.addClass('search-hidden');
      }} else {{
        edge.removeClass('search-hidden');
      }}
    }});
  }}
}}

// ============================
// Feature Detail Modal
// ============================
function openModal(filePath, label) {{
  var overlay = document.getElementById('modal-overlay');
  var title = document.getElementById('modal-title');
  var body = document.getElementById('modal-body');
  var tabs = document.getElementById('modal-tabs');

  title.textContent = label || filePath;
  body.innerHTML = '<p style="color:#666">Loading...</p>';
  overlay.classList.add('visible');

  // Reset tab state
  var currentModal = {{ file: filePath, specContent: null, implContent: null, hasImpl: false }};
  window._currentModal = currentModal;

  // Check if impl.md exists (derive path: features/foo.md -> features/foo.impl.md)
  var implPath = filePath.replace(/\\.md$/, '.impl.md');

  // Load spec
  var specPromise = modalCache[filePath]
    ? Promise.resolve(modalCache[filePath])
    : fetch('/feature?file=' + encodeURIComponent(filePath))
        .then(function(r) {{ if (!r.ok) throw new Error('Failed'); return r.text(); }})
        .then(function(md) {{ modalCache[filePath] = md; return md; }});

  // Try loading impl
  var implPromise = modalCache[implPath]
    ? Promise.resolve(modalCache[implPath])
    : fetch('/impl-notes?file=' + encodeURIComponent(implPath))
        .then(function(r) {{ if (!r.ok) return null; return r.text(); }})
        .then(function(md) {{ if (md) modalCache[implPath] = md; return md; }})
        .catch(function() {{ return null; }});

  Promise.all([specPromise, implPromise]).then(function(results) {{
    currentModal.specContent = results[0];
    currentModal.implContent = results[1];
    currentModal.hasImpl = !!results[1];

    if (currentModal.hasImpl) {{
      tabs.style.display = '';
      // Reset tabs to spec
      tabs.querySelectorAll('.modal-tab').forEach(function(t) {{
        t.classList.toggle('active', t.getAttribute('data-tab') === 'spec');
      }});
    }} else {{
      tabs.style.display = 'none';
    }}

    body.innerHTML = marked.parse(currentModal.specContent || '');
  }}).catch(function() {{
    body.innerHTML = '<p style="color:#FF4500">Could not load feature content.</p>';
  }});
}}

function switchModalTab(tab) {{
  var tabs = document.getElementById('modal-tabs');
  var body = document.getElementById('modal-body');
  var m = window._currentModal;
  if (!m) return;

  tabs.querySelectorAll('.modal-tab').forEach(function(t) {{
    t.classList.toggle('active', t.getAttribute('data-tab') === tab);
  }});

  if (tab === 'impl' && m.implContent) {{
    body.innerHTML = marked.parse(m.implContent);
  }} else if (m.specContent) {{
    body.innerHTML = marked.parse(m.specContent);
  }}
}}

function openTombstoneModal(filePath, label) {{
  var overlay = document.getElementById('modal-overlay');
  var title = document.getElementById('modal-title');
  var body = document.getElementById('modal-body');
  var tabs = document.getElementById('modal-tabs');
  var content = document.querySelector('#modal-overlay .modal-content');

  title.textContent = label || filePath;
  title.style.color = 'var(--purlin-status-error)';
  content.style.borderColor = 'var(--purlin-status-error)';
  body.innerHTML = '<p style="color:var(--purlin-dim)">Loading...</p>';
  tabs.style.display = 'none';
  overlay.classList.add('visible');
  window._tombstoneModal = true;

  fetch('/feature?file=' + encodeURIComponent(filePath))
    .then(function(r) {{ if (!r.ok) throw new Error('Failed'); return r.text(); }})
    .then(function(md) {{
      body.innerHTML =
        '<div style="background:var(--purlin-status-error);color:#fff;' +
        'padding:8px 14px;margin:-14px -14px 14px -14px;font-weight:bold;' +
        'text-align:center;font-family:var(--font-body);font-size:13px;' +
        'letter-spacing:0.05em">READY FOR DELETION</div>' +
        marked.parse(md);
    }})
    .catch(function() {{
      body.innerHTML = '<p style="color:var(--purlin-status-error)">Could not load tombstone content.</p>';
    }});
}}

function closeModal() {{
  var overlay = document.getElementById('modal-overlay');
  overlay.classList.remove('visible');
  if (window._tombstoneModal) {{
    document.getElementById('modal-title').style.color = '';
    document.querySelector('#modal-overlay .modal-content').style.borderColor = '';
    window._tombstoneModal = false;
  }}
}}

document.getElementById('modal-close').addEventListener('click', closeModal);
document.getElementById('modal-overlay').addEventListener('click', function(e) {{
  if (e.target === this) closeModal();
}});
document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') closeModal();
}});

// ============================
// Cytoscape.js Spec Map View
// ============================
var SVG_WIDTH = 200;
var LABEL_FONT_SIZE = 14;
var LABEL_LINE_HEIGHT = 18;
var FILENAME_FONT_SIZE = 9;
var FILENAME_LINE_HEIGHT = 14;
var CHARS_PER_LINE = 22;

var CATEGORY_COLORS = {{
  'DevOps Tools': '#0288d1',
  'Auth': '#7B1FA2',
  'Core': '#2E7D32',
  'UI': '#7B1FA2',
  'Hardware': '#2E7D32',
  'Release': '#E65100',
  'Process': '#558B2F',
}};
var DEFAULT_NODE_COLOR = '#01579b';

function wrapText(text, maxChars) {{
  var words = text.split(/\\s+/);
  var lines = [];
  var currentLine = '';
  for (var i = 0; i < words.length; i++) {{
    var word = words[i];
    if (!currentLine) {{
      currentLine = word;
    }} else if ((currentLine + ' ' + word).length <= maxChars) {{
      currentLine += ' ' + word;
    }} else {{
      lines.push(currentLine);
      currentLine = word;
    }}
  }}
  if (currentLine) lines.push(currentLine);
  return lines;
}}

function createNodeLabelSVG(name, filename, colors) {{
  var esc = function(s) {{ return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }};
  var labelColor = (colors && colors.primary) || '#E2E8F0';
  var fileColor = (colors && colors.dim) || '#8B9DB0';
  var nameLines = wrapText(name, CHARS_PER_LINE);
  var nameBlockHeight = nameLines.length * LABEL_LINE_HEIGHT;
  var totalHeight = nameBlockHeight + FILENAME_LINE_HEIGHT + 8;

  var tspans = '';
  nameLines.forEach(function(line, i) {{
    tspans += '<tspan x="' + (SVG_WIDTH / 2) + '" dy="' + (i === 0 ? 0 : LABEL_LINE_HEIGHT) + '">' + esc(line) + '</tspan>';
  }});

  var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + SVG_WIDTH + '" height="' + totalHeight + '">' +
    '<text x="' + (SVG_WIDTH / 2) + '" y="' + LABEL_LINE_HEIGHT + '" text-anchor="middle" font-size="' + LABEL_FONT_SIZE + '" font-weight="bold" fill="' + labelColor + '" font-family="Menlo,Monaco,Consolas,monospace">' + tspans + '</text>' +
    '<text x="' + (SVG_WIDTH / 2) + '" y="' + (nameBlockHeight + FILENAME_LINE_HEIGHT + 4) + '" text-anchor="middle" font-size="' + FILENAME_FONT_SIZE + '" fill="' + fileColor + '" font-family="Menlo,Monaco,Consolas,monospace">' + esc(filename) + '</text>' +
    '</svg>';
  return {{ url: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg), height: totalHeight }};
}}

function buildCytoscapeElements(features, colors) {{
  var nodes = [];
  var edges = [];
  var fileToId = {{}};
  var categories = new Set();

  features.forEach(function(f) {{
    var id = f.file.replace(/[^a-zA-Z0-9]/g, '_');
    fileToId[f.file] = id;
    var basename = f.file.split('/').pop();
    fileToId[basename] = id;
    categories.add(f.category);
  }});

  categories.forEach(function(cat) {{
    var catId = 'cat_' + cat.replace(/[^a-zA-Z0-9]/g, '_');
    nodes.push({{
      data: {{ id: catId, label: cat, isCategory: true }}
    }});
  }});

  features.forEach(function(f) {{
    var id = fileToId[f.file];
    var color = CATEGORY_COLORS[f.category] || DEFAULT_NODE_COLOR;
    var catId = 'cat_' + f.category.replace(/[^a-zA-Z0-9]/g, '_');
    var filename = f.file.split('/').pop();
    var svgResult = createNodeLabelSVG(f.label, filename, colors);
    nodes.push({{
      data: {{
        id: id,
        friendlyName: f.label,
        filename: filename,
        file: f.file,
        category: f.category,
        prerequisites: f.prerequisites || [],
        color: color,
        parent: catId,
        svgLabel: svgResult.url,
        nodeHeight: svgResult.height + 12,
      }}
    }});

    (f.prerequisites || []).forEach(function(prereq) {{
      var sourceId = fileToId[prereq];
      if (sourceId) {{
        edges.push({{
          data: {{
            id: 'e_' + sourceId + '_' + id,
            source: sourceId,
            target: id,
          }}
        }});
      }}
    }});
  }});

  return {{ nodes: nodes, edges: edges }};
}}

// ============================
// Node Position Persistence
// ============================
function computeContentHash(features) {{
  var parts = features.map(function(f) {{ return f.file + ':' + (f.category || ''); }});
  parts.sort();
  var str = parts.join('|');
  var hash = 5381;
  for (var i = 0; i < str.length; i++) {{
    hash = ((hash << 5) + hash) + str.charCodeAt(i);
    hash = hash & hash;
  }}
  return 'purlin-node-pos-' + Math.abs(hash).toString(36);
}}

function saveNodePositions(key) {{
  if (!cy) return;
  var positions = {{}};
  cy.nodes().forEach(function(node) {{
    var pos = node.position();
    positions[node.id()] = {{ x: pos.x, y: pos.y }};
  }});
  localStorage.setItem(key, JSON.stringify(positions));
}}

function restoreNodePositions(key) {{
  if (!cy) return false;
  try {{
    var raw = localStorage.getItem(key);
    if (!raw) return false;
    var positions = JSON.parse(raw);
    var restored = false;
    cy.nodes().forEach(function(node) {{
      var saved = positions[node.id()];
      if (saved) {{
        node.position(saved);
        restored = true;
      }}
    }});
    return restored;
  }} catch(e) {{ return false; }}
}}

function resetInactivityTimer() {{
  if (inactivityTimer) clearTimeout(inactivityTimer);
  inactivityTimer = setTimeout(function() {{
    if (currentView === 'map') {{
      userModifiedView = false;
      userModifiedNodes = false;
      if (lastContentHash) localStorage.removeItem(lastContentHash);
      renderGraph();
    }}
  }}, INACTIVITY_TIMEOUT);
}}

function createCytoscape(elements, colors) {{
  var c = colors || getThemeColors();
  var instance = cytoscape({{
    container: document.getElementById('cy'),
    elements: elements.nodes.concat(elements.edges),
    style: [
      {{
        selector: 'node[!isCategory]',
        style: {{
          'label': '',
          'shape': 'round-rectangle',
          'width': 220,
          'height': 'data(nodeHeight)',
          'background-color': 'data(color)',
          'background-opacity': 0.15,
          'background-image': 'data(svgLabel)',
          'background-fit': 'contain',
          'border-width': 2,
          'border-color': 'data(color)',
          'border-opacity': 0.6,
        }}
      }},
      {{
        selector: '$node > node',
        style: {{
          'label': 'data(label)',
          'background-color': c.surface,
          'background-opacity': 0.8,
          'border-width': 1,
          'border-color': c.border,
          'border-style': 'dashed',
          'color': c.dim,
          'font-size': '12px',
          'font-weight': 'bold',
          'text-valign': 'top',
          'text-halign': 'center',
          'text-margin-y': -8,
          'padding': '24px',
          'shape': 'round-rectangle',
        }}
      }},
      {{
        selector: 'edge',
        style: {{
          'width': 2,
          'line-color': c.border,
          'target-arrow-color': c.border,
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'arrow-scale': 0.8,
        }}
      }},
      {{
        selector: 'node.highlighted',
        style: {{
          'border-color': '#FF7043',
          'border-width': 3,
          'border-opacity': 1,
          'background-opacity': 0.3,
          'z-index': 10,
        }}
      }},
      {{
        selector: 'node.center-hover',
        style: {{
          'border-color': '#4FC3F7',
          'border-width': 3,
          'border-opacity': 1,
          'background-opacity': 0.35,
          'z-index': 11,
        }}
      }},
      {{
        selector: 'edge.highlighted',
        style: {{
          'line-color': '#FF7043',
          'target-arrow-color': '#FF7043',
          'width': 3,
          'z-index': 10,
        }}
      }},
      {{
        selector: 'node.dimmed',
        style: {{ 'opacity': 0.2 }}
      }},
      {{
        selector: 'edge.dimmed',
        style: {{ 'opacity': 0.1 }}
      }},
      {{
        selector: 'node.search-hidden',
        style: {{ 'opacity': 0.1 }}
      }},
      {{
        selector: 'edge.search-hidden',
        style: {{ 'opacity': 0.05 }}
      }},
    ],
    layout: {{
      name: 'dagre',
      rankDir: 'TB',
      nodeSep: 80,
      rankSep: 100,
      padding: 50,
    }},
    wheelSensitivity: 0.3,
    minZoom: 0.1,
    maxZoom: 5,
  }});

  // Hover highlighting (feature nodes only, not category parents)
  instance.on('mouseover', 'node[!isCategory]', function(evt) {{
    var node = evt.target;
    var neighborhood = node.neighborhood().add(node);
    instance.elements().addClass('dimmed');
    instance.nodes('$node > node').removeClass('dimmed');
    neighborhood.removeClass('dimmed');
    node.addClass('center-hover');
    neighborhood.nodes().not(node).filter('[!isCategory]').addClass('highlighted');
    neighborhood.edges().addClass('highlighted');
  }});

  instance.on('mouseout', 'node[!isCategory]', function() {{
    instance.elements().removeClass('dimmed highlighted center-hover');
  }});

  // Click for detail modal
  instance.on('tap', 'node[!isCategory]', function(evt) {{
    var file = evt.target.data('file');
    var label = evt.target.data('friendlyName');
    if (file) openModal(file, label);
    resetInactivityTimer();
  }});

  // Node drag — track position modification and persist
  instance.on('dragfree', 'node', function() {{
    userModifiedNodes = true;
    if (lastContentHash) saveNodePositions(lastContentHash);
    resetInactivityTimer();
  }});

  return instance;
}}

var programmaticViewport = false;

function renderGraph() {{
  if (!graphData || !graphData.features) return;
  var colors = getThemeColors();
  var elements = buildCytoscapeElements(graphData.features, colors);

  // Compute content hash for position persistence
  var newHash = computeContentHash(graphData.features);
  var hashChanged = (lastContentHash !== null && newHash !== lastContentHash);
  if (hashChanged) {{
    // Substantive change: discard saved positions, reset node interaction state
    if (lastContentHash) localStorage.removeItem(lastContentHash);
    userModifiedNodes = false;
  }}
  lastContentHash = newHash;

  if (cy) {{
    var zoom = cy.zoom();
    var pan = cy.pan();
    cy.destroy();
    cy = createCytoscape(elements, colors);

    // Restore node positions if user has moved nodes and graph hasn't changed
    if (userModifiedNodes && !hashChanged) {{
      restoreNodePositions(newHash);
    }}

    if (userModifiedView) {{
      programmaticViewport = true;
      cy.zoom(zoom);
      cy.pan(pan);
      programmaticViewport = false;
    }} else {{
      programmaticViewport = true;
      cy.fit(undefined, 40);
      programmaticViewport = false;
    }}
  }} else {{
    cy = createCytoscape(elements, colors);
    // Restore node positions on initial load if saved
    if (userModifiedNodes) {{
      restoreNodePositions(newHash);
    }}
    programmaticViewport = true;
    cy.fit(undefined, 40);
    programmaticViewport = false;
  }}

  cy.on('viewport', function() {{
    if (!programmaticViewport) {{
      userModifiedView = true;
      resetInactivityTimer();
    }}
  }});

  applySearchFilter();
}}

function recenterGraph() {{
  if (cy) {{
    userModifiedView = false;
    userModifiedNodes = false;
    if (lastContentHash) localStorage.removeItem(lastContentHash);
    // Re-run layout to reset node positions to auto-layout
    cy.layout({{
      name: 'dagre', rankDir: 'TB', nodeSep: 80, rankSep: 100, padding: 50,
    }}).run();
    programmaticViewport = true;
    cy.fit(undefined, 40);
    programmaticViewport = false;
  }}
}}

function loadGraph() {{
  return fetch('/dependency_graph.json?t=' + Date.now())
    .then(function(resp) {{
      if (!resp.ok) return;
      return resp.json();
    }})
    .then(function(data) {{
      if (data) {{
        graphData = data;
        renderGraph();
      }}
    }})
    .catch(function(e) {{
      console.error('Failed to load dependency graph:', e);
    }});
}}

function startMapRefresh() {{
  if (mapRefreshTimer) return;
  mapRefreshTimer = setInterval(function() {{
    if (currentView === 'map') loadGraph();
  }}, 5000);
}}

function stopMapRefresh() {{
  if (mapRefreshTimer) {{
    clearInterval(mapRefreshTimer);
    mapRefreshTimer = null;
  }}
}}

// ============================
// Agents Section
// ============================
var agentsConfig = null;
var agentsSaveTimer = null;
var pendingWrites = new Map();

function applyPendingWrites() {{
  if (pendingWrites.size === 0) return;
  pendingWrites.forEach(function(val, key) {{
    var dot = key.indexOf('.');
    var role = key.substring(0, dot);
    var field = key.substring(dot + 1);
    if (field === 'model') {{
      var sel = document.getElementById('agent-model-' + role);
      if (sel) {{ sel.value = val; syncCapabilityControls(role); }}
    }} else if (field === 'effort') {{
      var sel = document.getElementById('agent-effort-' + role);
      if (sel) sel.value = val;
    }} else if (field === 'bypass_permissions') {{
      var chk = document.getElementById('agent-bypass-' + role);
      if (chk) chk.checked = val;
    }} else if (field === 'startup_sequence') {{
      var chk = document.getElementById('agent-startup-' + role);
      if (chk) chk.checked = val;
    }} else if (field === 'recommend_next_actions') {{
      var chk = document.getElementById('agent-recommend-' + role);
      if (chk) chk.checked = val;
    }}
  }});
}}

function initAgentsSection() {{
  // Synchronous restore from cache after innerHTML replacement clears the DOM
  if (agentsConfig && !document.getElementById('agent-model-architect')) {{
    renderAgentsRows(agentsConfig);
    applyPendingWrites();
    updateAgentsBadge(agentsConfig);
  }}
  // Async fetch for config updates
  fetch('/config.json')
    .then(function(r) {{ return r.json(); }})
    .then(function(cfg) {{
      var domExists = !!document.getElementById('agent-model-architect');
      var configChanged = !agentsConfig ||
          JSON.stringify(cfg.agents) !== JSON.stringify(agentsConfig.agents) ||
          JSON.stringify(cfg.models) !== JSON.stringify(agentsConfig.models);
      agentsConfig = cfg;
      if (!domExists) {{
        renderAgentsRows(cfg);
        applyPendingWrites();
      }} else if (configChanged) {{
        diffUpdateAgentRows(cfg);
      }}
      updateAgentsBadge(cfg);
    }})
    .catch(function() {{}});
}}

function renderAgentsRows(cfg) {{
  var container = document.getElementById('agents-rows');
  if (!container) return;
  var agents = cfg.agents || {{}};
  var roles = ['architect', 'builder', 'qa'];
  var html = '<div class="agent-hdr">' +
    '<span></span>' +
    '<span class="agent-hdr-cell">MODEL</span>' +
    '<span class="agent-hdr-cell">EFFORT</span>' +
    '<span class="agent-hdr-cell center">YOLO</span>' +
    '<span class="agent-hdr-cell center">Startup<br>Sequence</span>' +
    '<span class="agent-hdr-cell center">Suggest<br>Next</span>' +
  '</div>';
  roles.forEach(function(role) {{
    html += buildAgentRowHtml(role, agents[role] || {{}});
  }});
  container.innerHTML = html;
  roles.forEach(function(role) {{
    var modSel = document.getElementById('agent-model-' + role);
    var effSel = document.getElementById('agent-effort-' + role);
    var bypassChk = document.getElementById('agent-bypass-' + role);
    if (modSel) modSel.addEventListener('change', function() {{
      pendingWrites.set(role + '.model', modSel.value);
      syncCapabilityControls(role);
      scheduleAgentSave();
    }});
    if (effSel) effSel.addEventListener('change', function() {{
      pendingWrites.set(role + '.effort', effSel.value);
      scheduleAgentSave();
    }});
    if (bypassChk) bypassChk.addEventListener('change', function() {{
      pendingWrites.set(role + '.bypass_permissions', bypassChk.checked);
      scheduleAgentSave();
    }});
    var startupChk = document.getElementById('agent-startup-' + role);
    var recommendChk = document.getElementById('agent-recommend-' + role);
    if (startupChk) startupChk.addEventListener('change', function() {{
      pendingWrites.set(role + '.startup_sequence', startupChk.checked);
      var recLbl = document.getElementById('agent-recommend-lbl-' + role);
      if (!startupChk.checked) {{
        if (recommendChk && recommendChk.checked) {{
          recommendChk.dataset.prevState = 'true';
        }}
        if (recommendChk) {{ recommendChk.checked = false; recommendChk.disabled = true; }}
        if (recLbl) recLbl.classList.add('disabled');
        pendingWrites.set(role + '.recommend_next_actions', false);
      }} else {{
        if (recommendChk) {{
          recommendChk.disabled = false;
          if (recommendChk.dataset.prevState === 'true') recommendChk.checked = true;
        }}
        if (recLbl) recLbl.classList.remove('disabled');
        pendingWrites.set(role + '.recommend_next_actions', recommendChk ? recommendChk.checked : true);
      }}
      scheduleAgentSave();
    }});
    if (recommendChk) recommendChk.addEventListener('change', function() {{
      pendingWrites.set(role + '.recommend_next_actions', recommendChk.checked);
      scheduleAgentSave();
    }});
    syncCapabilityControls(role);
  }});
}}

function diffUpdateAgentRows(cfg) {{
  var agents = cfg.agents || {{}};
  var roles = ['architect', 'builder', 'qa'];
  roles.forEach(function(role) {{
    var acfg = agents[role] || {{}};
    var modSel = document.getElementById('agent-model-' + role);
    var effSel = document.getElementById('agent-effort-' + role);
    var bypassChk = document.getElementById('agent-bypass-' + role);
    if (!modSel) return;
    if (!pendingWrites.has(role + '.model') && modSel.value !== (acfg.model || '')) {{
      modSel.value = acfg.model || '';
    }}
    if (effSel && !pendingWrites.has(role + '.effort') && effSel.value !== (acfg.effort || 'high')) effSel.value = acfg.effort || 'high';
    var yoloMode = acfg.bypass_permissions === true;
    if (bypassChk && !pendingWrites.has(role + '.bypass_permissions') && bypassChk.checked !== yoloMode) bypassChk.checked = yoloMode;
    var startupChk = document.getElementById('agent-startup-' + role);
    var recommendChk = document.getElementById('agent-recommend-' + role);
    var recLbl = document.getElementById('agent-recommend-lbl-' + role);
    var startupVal = acfg.startup_sequence !== false;
    var recommendVal = acfg.recommend_next_actions !== false;
    if (startupChk && !pendingWrites.has(role + '.startup_sequence') && startupChk.checked !== startupVal) startupChk.checked = startupVal;
    if (recommendChk && !pendingWrites.has(role + '.recommend_next_actions')) {{
      var shouldDisable = !startupVal;
      recommendChk.disabled = shouldDisable;
      if (shouldDisable) {{
        recommendChk.checked = false;
        if (recLbl) recLbl.classList.add('disabled');
      }} else {{
        if (recommendChk.checked !== recommendVal) recommendChk.checked = recommendVal;
        if (recLbl) recLbl.classList.remove('disabled');
      }}
    }}
    syncCapabilityControls(role);
  }});
}}

function buildAgentRowHtml(role, agentCfg) {{
  var currentModel = agentCfg.model || '';
  var currentEffort = agentCfg.effort || 'high';
  var yoloMode = agentCfg.bypass_permissions === true;
  var startupSeq = agentCfg.startup_sequence !== false;
  var suggestNext = agentCfg.recommend_next_actions !== false;
  var suggestDisabled = !startupSeq;
  var modelsList = (agentsConfig && agentsConfig.models) || [];
  var modOptions = modelsList.map(function(m) {{
    return '<option value="' + m.id + '"' + (m.id === currentModel ? ' selected' : '') + '>' + m.label + '</option>';
  }}).join('');
  if (!modOptions) modOptions = '<option value="' + currentModel + '" selected>' + currentModel + '</option>';
  var effortOptions = ['low', 'medium', 'high'].map(function(e) {{
    return '<option value="' + e + '"' + (e === currentEffort ? ' selected' : '') + '>' + e + '</option>';
  }}).join('');
  return '<div class="agent-row">' +
    '<span class="agent-lbl">' + role.toUpperCase() + '</span>' +
    '<select id="agent-model-' + role + '" class="agent-sel">' + modOptions + '</select>' +
    '<select id="agent-effort-' + role + '" class="agent-sel" style="visibility:hidden">' + effortOptions + '</select>' +
    '<label class="agent-chk-lbl" id="agent-bypass-lbl-' + role + '" style="visibility:hidden">' +
      '<input type="checkbox" id="agent-bypass-' + role + '" style="accent-color:var(--purlin-accent)"' + (yoloMode ? ' checked' : '') + '>' +
    '</label>' +
    '<label class="agent-chk-lbl" id="agent-startup-lbl-' + role + '" style="visibility:hidden">' +
      '<input type="checkbox" id="agent-startup-' + role + '" style="accent-color:var(--purlin-accent)"' + (startupSeq ? ' checked' : '') + '>' +
    '</label>' +
    '<label class="agent-chk-lbl' + (suggestDisabled ? ' disabled' : '') + '" id="agent-recommend-lbl-' + role + '" style="visibility:hidden">' +
      '<input type="checkbox" id="agent-recommend-' + role + '" style="accent-color:var(--purlin-accent)"' + (suggestNext && !suggestDisabled ? ' checked' : '') + (suggestDisabled ? ' disabled' : '') + '>' +
    '</label>' +
  '</div>';
}}

function populateModelDropdown(role, selectedModel) {{
  var modSel = document.getElementById('agent-model-' + role);
  if (!modSel) return;
  var models = (agentsConfig && agentsConfig.models) || [];
  modSel.innerHTML = models.map(function(m) {{
    return '<option value="' + m.id + '"' + (m.id === selectedModel ? ' selected' : '') + '>' + m.label + '</option>';
  }}).join('');
}}

function syncCapabilityControls(role) {{
  var modSel = document.getElementById('agent-model-' + role);
  if (!modSel) return;
  var models = (agentsConfig && agentsConfig.models) || [];
  var modelObj = null;
  for (var i = 0; i < models.length; i++) {{
    if (models[i].id === modSel.value) {{ modelObj = models[i]; break; }}
  }}
  var caps = (modelObj || {{}}).capabilities || {{}};
  var effSel = document.getElementById('agent-effort-' + role);
  var bypassLbl = document.getElementById('agent-bypass-lbl-' + role);
  var startupLbl = document.getElementById('agent-startup-lbl-' + role);
  var recommendLbl = document.getElementById('agent-recommend-lbl-' + role);
  if (effSel) effSel.style.visibility = caps.effort ? 'visible' : 'hidden';
  if (bypassLbl) bypassLbl.style.visibility = caps.permissions ? 'visible' : 'hidden';
  if (startupLbl) startupLbl.style.visibility = caps.permissions ? 'visible' : 'hidden';
  if (recommendLbl) recommendLbl.style.visibility = caps.permissions ? 'visible' : 'hidden';
}}

function updateAgentsBadge(cfg) {{
  var badge = document.getElementById('agents-section-badge');
  if (!badge) return;
  var modelsList = cfg.models || [];
  var agents = cfg.agents || {{}};
  var roles = ['architect', 'builder', 'qa'];
  var labels = roles.map(function(role) {{
    var acfg = agents[role] || {{}};
    var mid = acfg.model || '';
    for (var i = 0; i < modelsList.length; i++) {{
      if (modelsList[i].id === mid) return modelsList[i].label;
    }}
    return mid || '?';
  }});
  // Group by label, count, sort by count desc then alphabetically
  var counts = {{}};
  labels.forEach(function(l) {{ counts[l] = (counts[l] || 0) + 1; }});
  var segments = Object.keys(counts).map(function(l) {{ return {{label: l, count: counts[l]}}; }});
  segments.sort(function(a, b) {{ return b.count - a.count || a.label.localeCompare(b.label); }});
  badge.textContent = segments.map(function(s) {{ return s.count + 'x ' + s.label; }}).join(' | ');
}}

function scheduleAgentSave() {{
  if (agentsSaveTimer) clearTimeout(agentsSaveTimer);
  agentsSaveTimer = setTimeout(saveAgentConfig, 600);
}}

function saveAgentConfig() {{
  var roles = ['architect', 'builder', 'qa'];
  var agentsPayload = {{}};
  roles.forEach(function(role) {{
    var modSel = document.getElementById('agent-model-' + role);
    var effSel = document.getElementById('agent-effort-' + role);
    var bypassChk = document.getElementById('agent-bypass-' + role);
    var startupChk = document.getElementById('agent-startup-' + role);
    var recommendChk = document.getElementById('agent-recommend-' + role);
    if (!modSel) return;
    agentsPayload[role] = {{
      model: modSel.value,
      effort: effSel ? effSel.value : 'high',
      bypass_permissions: bypassChk ? bypassChk.checked : false,
      startup_sequence: startupChk ? startupChk.checked : true,
      recommend_next_actions: recommendChk ? recommendChk.checked : true
    }};
  }});
  fetch('/config/agents', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify(agentsPayload)
  }})
  .then(function(r) {{ return r.json(); }})
  .then(function(d) {{
    pendingWrites.clear();
    if (agentsConfig && d.agents) {{
      agentsConfig.agents = d.agents;
      updateAgentsBadge(agentsConfig);
    }}
  }})
  .catch(function() {{ pendingWrites.clear(); }});
}}

// ============================
// Initialize
// ============================
applySectionStates();
initAgentsSection();
updateCriticLabel();
initFromHash();
</script>
</body>
</html>"""


def _role_table_html(features):
    """Renders a table of features with Architect, Builder, QA role columns.
    Feature names are clickable to open the detail modal."""
    if not features:
        return ""
    rows = ""
    for entry in features:
        fname = entry["file"]
        label = entry.get("label", fname)
        arch = _role_badge_html(entry.get("architect"))
        builder = _role_badge_html(entry.get("builder"))
        qa = _role_badge_html(entry.get("qa"))
        escaped_fname = fname.replace("'", "\\'")
        escaped_label = label.replace("'", "\\'")

        is_tombstone = entry.get("tombstone", False)
        if is_tombstone:
            # Extract short name from features/tombstones/<name>.md
            short_name = os.path.splitext(os.path.basename(fname))[0]
            display_name = (
                f'<span style="color:var(--purlin-status-error)">'
                f'{short_name} <b>[TOMBSTONE]</b></span>'
            )
            onclick = (
                f"openTombstoneModal(\'{escaped_fname}\',\'{escaped_label}\')"
            )
        else:
            display_name = fname
            onclick = (
                f"openModal(\'{escaped_fname}\',\'{escaped_label}\')"
            )

        rows += (
            f'<tr>'
            f'<td><a class="feature-link" onclick="{onclick}">'
            f'{display_name}</a></td>'
            f'<td class="badge-cell">{arch}</td>'
            f'<td class="badge-cell">{builder}</td>'
            f'<td class="badge-cell">{qa}</td>'
            f'</tr>'
        )
    return (
        f'<table class="ft">'
        f'<thead><tr><th>Feature</th>'
        f'<th class="badge-col"><span class="col-full">Architect</span><span class="col-abbr">Arch</span></th>'
        f'<th class="badge-col"><span class="col-full">Builder</span><span class="col-abbr">Build</span></th>'
        f'<th class="badge-col">QA</th></tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
    )


# ===================================================================
# File Watcher for Reactive Graph Generation (cdd_spec_map)
# ===================================================================

def _get_features_snapshot(directory):
    """Get a dict of {filename: mtime} for all .md files in a directory."""
    snapshot = {}
    if not os.path.exists(directory):
        return snapshot
    for entry in os.scandir(directory):
        if entry.is_file() and entry.name.endswith(".md"):
            snapshot[entry.name] = entry.stat().st_mtime
    return snapshot


def _run_graph_generation():
    """Run graph generation via the graph module.

    Returns True on success, False on failure.
    """
    try:
        from graph import run_full_generation
        run_full_generation()
        print(f"[watcher] Regenerated graph at {time.strftime('%H:%M:%S')}")
        return True
    except Exception as e:
        print(f"[watcher] Graph generation failed: {e}")
        return False


def _file_watcher():
    """Poll features directory for changes and regenerate graph on modification."""
    snapshot = _get_features_snapshot(FEATURES_ABS)

    while True:
        time.sleep(POLL_INTERVAL)
        new_snapshot = _get_features_snapshot(FEATURES_ABS)
        if new_snapshot != snapshot:
            print("[watcher] Change detected, regenerating...")
            if _run_graph_generation():
                snapshot = new_snapshot
            # On failure, keep old snapshot so watcher retries next cycle


def start_file_watcher():
    """Start the file watcher in a background daemon thread."""
    watcher_thread = threading.Thread(target=_file_watcher, daemon=True)
    watcher_thread.start()
    print(f"[watcher] File watcher active (polling every {POLL_INTERVAL}s)")


class Handler(http.server.SimpleHTTPRequestHandler):
    def _send_json(self, data):
        payload = json.dumps(data, indent=2, sort_keys=True).encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == '/status.json':
            # Public API: flat array with role fields
            cache = build_status_commit_cache()
            api_data = generate_api_status_json(cache)

            # Also write internal feature_status.json (old format)
            write_internal_feature_status(cache)

            self._send_json(200, api_data)
        elif self.path == '/workspace.json':
            # Dynamic workspace data for client-side refresh
            self._send_json(200, generate_workspace_json())
        elif self.path == '/dependency_graph.json' or self.path.startswith(
                '/dependency_graph.json?'):
            # Serve dependency graph from cache directory (Section 2.12)
            if os.path.isfile(DEPENDENCY_GRAPH_PATH):
                with open(DEPENDENCY_GRAPH_PATH, 'rb') as f:
                    payload = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            else:
                self.send_error(404, "dependency_graph.json not found")
        elif self.path.startswith('/feature?'):
            self._serve_feature_content()
        elif self.path.startswith('/impl-notes?'):
            self._serve_impl_notes()
        elif self.path == '/config.json':
            self._serve_config_json()
        elif self.path == '/release-checklist':
            self._serve_release_checklist()
        else:
            # Dashboard request: also regenerate internal file
            cache = build_status_commit_cache()
            write_internal_feature_status(cache)
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(generate_html(cache).encode('utf-8'))

    def _serve_feature_content(self):
        """Serve the raw markdown content of a feature file."""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        file_param = params.get('file', [''])[0]

        abs_path = os.path.normpath(os.path.join(PROJECT_ROOT, file_param))
        allowed_dir = os.path.normpath(FEATURES_DIR)
        if not abs_path.startswith(allowed_dir):
            self.send_error(403, "Access denied")
            return

        if not os.path.isfile(abs_path):
            self.send_error(404, "Feature file not found")
            return

        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            payload = content.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception:
            self.send_error(500, "Error reading file")

    def _serve_impl_notes(self):
        """Serve the raw markdown content of an implementation notes file."""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        file_param = params.get('file', [''])[0]

        abs_path = os.path.normpath(os.path.join(PROJECT_ROOT, file_param))
        allowed_dir = os.path.normpath(FEATURES_DIR)
        if not abs_path.startswith(allowed_dir):
            self.send_error(403, "Access denied")
            return

        if not os.path.isfile(abs_path):
            self.send_error(404, "Implementation notes not found")
            return

        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            payload = content.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception:
            self.send_error(500, "Error reading file")

    def _serve_config_json(self):
        """Serve the project config.json with resolved project name."""
        config_data = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r') as f:
                    config_data = json.load(f)
            except (json.JSONDecodeError, IOError, OSError):
                pass
        payload = json.dumps(config_data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if self.path == '/run-critic':
            try:
                critic_script = os.path.join(
                    PROJECT_ROOT,
                    CONFIG.get('tools_root', 'tools'),
                    'critic', 'run.sh')
                subprocess.run(
                    ['bash', critic_script],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=120,
                )
                payload = json.dumps({"status": "ok"}).encode('utf-8')
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                    OSError) as exc:
                payload = json.dumps({
                    "status": "error",
                    "detail": str(exc),
                }).encode('utf-8')

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == '/isolate/create':
            self._handle_isolate_create()
        elif self.path == '/isolate/kill':
            self._handle_isolate_kill()
        elif self.path == '/config/agents':
            self._handle_config_agents()
        elif self.path == '/release-checklist/config':
            self._handle_release_config()
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, status, data):
        payload = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_isolate_create(self):
        """POST /isolate/create — run create_isolation.sh <name>."""
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
        except (ValueError, json.JSONDecodeError) as e:
            self._send_json(400, {'error': f'Invalid JSON: {e}'})
            return

        name = body.get('name', '').strip()
        if not name:
            self._send_json(400, {'error': 'Name is required'})
            return

        create_script = os.path.join(
            PROJECT_ROOT, TOOLS_ROOT, 'collab', 'create_isolation.sh')
        if not os.path.exists(create_script):
            self._send_json(500, {
                'error': f'create_isolation.sh not found at {create_script}'})
            return

        try:
            subprocess.run(
                ['bash', create_script, name,
                 '--project-root', PROJECT_ROOT],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            self._send_json(200, {'status': 'ok'})
        except subprocess.CalledProcessError as exc:
            self._send_json(500, {
                'error': exc.stderr.strip() or exc.stdout.strip() or str(exc)
            })
        except subprocess.TimeoutExpired:
            self._send_json(500, {'error': 'create_isolation.sh timed out'})

    def _handle_isolate_kill(self):
        """POST /isolate/kill — run kill_isolation.sh <name> (dry-run or force)."""
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
        except (ValueError, json.JSONDecodeError) as e:
            self._send_json(400, {'error': f'Invalid JSON: {e}'})
            return

        name = body.get('name', '').strip()
        if not name:
            self._send_json(400, {'error': 'Name is required'})
            return

        kill_script = os.path.join(
            PROJECT_ROOT, TOOLS_ROOT, 'collab', 'kill_isolation.sh')
        if not os.path.exists(kill_script):
            self._send_json(500, {
                'error': f'kill_isolation.sh not found at {kill_script}'})
            return

        dry_run = body.get('dry_run', False)
        force = body.get('force', False)

        cmd = ['bash', kill_script, name, '--project-root', PROJECT_ROOT]
        if dry_run:
            cmd.append('--dry-run')
        elif force:
            cmd.append('--force')

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if dry_run:
                try:
                    safety_data = json.loads(result.stdout)
                    self._send_json(200, safety_data)
                except json.JSONDecodeError:
                    self._send_json(200, {
                        'name': name,
                        'dirty': False,
                        'dirty_files': [],
                        'unsynced': False,
                        'unsynced_branch': '',
                        'unsynced_commits': 0,
                    })
            else:
                if result.returncode != 0:
                    self._send_json(500, {
                        'error': result.stderr.strip()
                                 or result.stdout.strip()
                                 or f'kill_isolation exited with code {result.returncode}'
                    })
                else:
                    self._send_json(200, {'status': 'ok'})
        except subprocess.TimeoutExpired:
            self._send_json(500, {
                'error': 'kill_isolation.sh timed out'})

    def _handle_config_agents(self):
        """POST /config/agents — update agent configuration in config.json, validated against flat models array."""
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
        except (ValueError, json.JSONDecodeError) as e:
            self._send_json(400, {'error': f'Invalid JSON: {e}'})
            return

        agents_data = body.get('agents', body) if isinstance(body, dict) else body

        if not isinstance(agents_data, dict):
            self._send_json(400, {'error': 'agents must be an object'})
            return

        # Completeness check: all three roles must be present
        required_roles = {'architect', 'builder', 'qa'}
        if not required_roles.issubset(agents_data.keys()):
            self._send_json(400, {'error': 'agents payload must include all three roles: architect, builder, qa'})
            return

        # Load current config
        current = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r') as f:
                    current = json.load(f)
            except (json.JSONDecodeError, IOError, OSError):
                pass

        # Collect valid model IDs from the flat models array
        all_model_ids = {
            m['id']
            for m in current.get('models', [])
        }
        valid_efforts = {'low', 'medium', 'high'}
        errors = []
        for role, cfg in agents_data.items():
            if not isinstance(cfg, dict):
                errors.append(f'{role}: must be an object')
                continue
            effort = cfg.get('effort', 'high')
            if effort not in valid_efforts:
                errors.append(f'{role}: invalid effort "{effort}"')
            model = cfg.get('model', '')
            if model and model not in all_model_ids:
                errors.append(f'{role}: unknown model "{model}"')
            # Validate startup controls
            for bool_field in ('startup_sequence', 'recommend_next_actions'):
                if bool_field in cfg and not isinstance(cfg[bool_field], bool):
                    errors.append(f'{role}: {bool_field} must be a boolean')
            ss = cfg.get('startup_sequence', True)
            rna = cfg.get('recommend_next_actions', True)
            if ss is False and rna is True:
                errors.append(f'{role}: startup_sequence=false with recommend_next_actions=true is invalid')

        if errors:
            self._send_json(400, {'error': '; '.join(errors)})
            return

        # Merge semantics: merge incoming roles into existing agents, preserving absent roles
        existing_agents = current.get('agents', {})
        existing_agents.update(agents_data)
        current['agents'] = existing_agents

        tmp = CONFIG_PATH + '.tmp'
        try:
            with open(tmp, 'w') as f:
                json.dump(current, f, indent=4)
            os.replace(tmp, CONFIG_PATH)
        except Exception as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            self._send_json(500, {'error': str(e)})
            return

        response = {'agents': current['agents']}

        # Isolated Teams: propagate config to all active worktrees (Section 2.9)
        isolation_wts = get_isolation_worktrees()
        if isolation_wts:
            warnings = []
            for wt in isolation_wts:
                wt_config_path = os.path.join(
                    PROJECT_ROOT, wt['path'], '.purlin', 'config.json')
                try:
                    # Merge semantics: read worktree config, merge agents, write back
                    wt_current = dict(current)
                    if os.path.exists(wt_config_path):
                        try:
                            with open(wt_config_path, 'r') as f:
                                wt_current = json.load(f)
                            wt_existing = wt_current.get('agents', {})
                            wt_existing.update(current['agents'])
                            wt_current['agents'] = wt_existing
                        except (json.JSONDecodeError, IOError, OSError):
                            wt_current = dict(current)
                    wt_tmp = wt_config_path + '.tmp'
                    with open(wt_tmp, 'w') as f:
                        json.dump(wt_current, f, indent=4)
                    os.replace(wt_tmp, wt_config_path)
                except Exception as e:
                    warnings.append(
                        f"Failed to propagate config to {wt['path']}: {e}")
                    if os.path.exists(wt_tmp):
                        try:
                            os.remove(wt_tmp)
                        except OSError:
                            pass
            if warnings:
                response['warnings'] = warnings

        self._send_json(200, response)

    def _serve_release_checklist(self):
        """GET /release-checklist — return resolved, ordered release steps."""
        steps, warnings, errors = get_release_checklist()
        self._send_json(200, {"steps": steps})

    def _handle_release_config(self):
        """POST /release-checklist/config — update release config."""
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
        except (ValueError, json.JSONDecodeError) as e:
            self._send_json(400, {"ok": False, "error": f"Invalid JSON: {e}"})
            return

        config_steps = body.get("steps")
        if not isinstance(config_steps, list):
            self._send_json(400, {"ok": False, "error": "steps must be an array"})
            return

        # Validate no duplicate IDs
        seen = set()
        for entry in config_steps:
            sid = entry.get("id", "")
            if sid in seen:
                self._send_json(400, {
                    "ok": False,
                    "error": f"Duplicate step ID: {sid}"
                })
                return
            seen.add(sid)

        # Write to disk
        config_dir = os.path.dirname(RELEASE_CONFIG_PATH)
        os.makedirs(config_dir, exist_ok=True)
        try:
            with open(RELEASE_CONFIG_PATH, 'w') as f:
                json.dump({"steps": config_steps}, f, indent=2)
            self._send_json(200, {"ok": True})
        except (IOError, OSError) as e:
            self._send_json(500, {"ok": False, "error": str(e)})

    def log_message(self, format, *args):
        pass  # Suppress request logging noise


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli-status":
        # CLI mode: output API JSON to stdout, regenerate internal file
        cache = build_status_commit_cache()
        write_internal_feature_status(cache)
        api_data = generate_api_status_json(cache)
        json.dump(api_data, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write('\n')
    elif len(sys.argv) > 1 and sys.argv[1] == "--cli-graph":
        # CLI graph mode: regenerate and output dependency_graph.json to stdout
        from graph import run_full_generation
        graph = run_full_generation()
        if graph:
            json.dump(graph, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write('\n')
        else:
            print("Error: graph generation failed", file=sys.stderr)
            sys.exit(1)
    else:
        # Server mode: run initial graph generation, start file watcher, serve
        print("Running initial graph generation...")
        try:
            from graph import run_full_generation
            run_full_generation()
        except Exception as e:
            print(f"Warning: Initial graph generation failed: {e}",
                  file=sys.stderr)

        start_file_watcher()

        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"CDD Dashboard serving at http://localhost:{PORT}")
            httpd.serve_forever()
