import http.server
import json
import socketserver
import subprocess
import os
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Project root detection (Section 2.11)
_env_root = os.environ.get('AGENTIC_PROJECT_ROOT', '')
if _env_root and os.path.isdir(_env_root):
    PROJECT_ROOT = _env_root
else:
    # Climbing fallback: try FURTHER path first (submodule), then nearer (standalone)
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
    for depth in ('../../../', '../../'):
        candidate = os.path.abspath(os.path.join(SCRIPT_DIR, depth))
        if os.path.exists(os.path.join(candidate, '.agentic_devops')):
            PROJECT_ROOT = candidate
            break

# Config loading with resilience (Section 2.13)
CONFIG_PATH = os.path.join(PROJECT_ROOT, ".agentic_devops/config.json")
CONFIG = {}
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r') as f:
            CONFIG = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        print("Warning: Failed to parse .agentic_devops/config.json; using defaults",
              file=sys.stderr)

PORT = CONFIG.get("cdd_port", 8086)

FEATURES_REL = "features"
FEATURES_ABS = os.path.join(PROJECT_ROOT, "features")
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")

COMPLETE_CAP = 10
# Artifact isolation (Section 2.12): write to .agentic_devops/cache/
CACHE_DIR = os.path.join(PROJECT_ROOT, ".agentic_devops", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
FEATURE_STATUS_PATH = os.path.join(CACHE_DIR, "feature_status.json")


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
    marker = '## User Testing Discoveries'
    idx = content.find(marker)
    if idx == -1:
        return content
    return content[:idx]


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

    committed_spec = strip_discoveries_section(committed_content)
    current_spec = strip_discoveries_section(current_content)
    return committed_spec == current_spec


def get_feature_status(features_rel, features_abs):
    """Gathers the status of all features for the project's features directory."""
    if not os.path.isdir(features_abs):
        return [], [], []

    complete, testing, todo = [], [], []
    feature_files = [f for f in os.listdir(features_abs) if f.endswith('.md')]

    for fname in feature_files:
        f_path = os.path.normpath(os.path.join(features_rel, fname))

        complete_ts_str = run_command(
            f"git log -1 --grep='\\[Complete {f_path}\\]' --format=%ct"
        )
        test_ts_str = run_command(
            f"git log -1 --grep='\\[Ready for .* {f_path}\\]' --format=%ct"
        )
        f_abs_path = os.path.join(features_abs, fname)
        file_mod_ts = int(os.path.getmtime(f_abs_path)) if os.path.exists(f_abs_path) else 0

        complete_ts = int(complete_ts_str) if complete_ts_str else 0
        test_ts = int(test_ts_str) if test_ts_str else 0

        status = "TODO"
        if complete_ts > test_ts:
            if file_mod_ts <= complete_ts:
                status = "COMPLETE"
            else:
                # File modified after status commit — check if only Discoveries changed
                commit_hash = run_command(
                    f"git log -1 --grep='\\[Complete {f_path}\\]' --format=%H"
                )
                if commit_hash and spec_content_unchanged(f_path, commit_hash):
                    status = "COMPLETE"
        elif test_ts > 0:
            if file_mod_ts <= test_ts:
                status = "TESTING"
            else:
                # File modified after status commit — check if only Discoveries changed
                commit_hash = run_command(
                    f"git log -1 --grep='\\[Ready for .* {f_path}\\]' --format=%H"
                )
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


# ===================================================================
# Internal Feature Status (old lifecycle format, for Critic consumption)
# ===================================================================

def generate_internal_feature_status():
    """Generates the internal feature_status.json (old lifecycle-based format).

    This is consumed by the Critic for lifecycle-state-dependent computations.
    NOT part of the public API contract.
    """
    complete_tuples, testing, todo = get_feature_status(FEATURES_REL, FEATURES_ABS)

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


def write_internal_feature_status():
    """Writes internal feature_status.json to disk."""
    data = generate_internal_feature_status()
    with open(FEATURE_STATUS_PATH, 'w') as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write('\n')


# ===================================================================
# Public API: /status.json (flat schema with role fields)
# ===================================================================

def generate_api_status_json():
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

    feature_files = sorted(
        f for f in os.listdir(FEATURES_ABS) if f.endswith('.md'))

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

        features.append(entry)

    return {
        "features": sorted(features, key=lambda x: x["file"]),
        "generated_at": datetime.now(timezone.utc).strftime(
            '%Y-%m-%dT%H:%M:%SZ'),
    }


# ===================================================================
# Web Dashboard (role-based columns, Active/Complete grouping)
# ===================================================================

def get_git_status():
    """Gets the current git status."""
    return run_command("git status --porcelain | grep -v '.DS_Store' | grep -v '.cache/'")


def get_last_commit():
    """Gets the last commit message."""
    return run_command("git log -1 --format='%h %s (%cr)'")


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


def generate_html():
    """Generates the full dashboard HTML with role-based columns."""
    git_status = get_git_status()
    last_commit = get_last_commit()

    # Get API data for dashboard
    api_data = generate_api_status_json()
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
        git_html = '<p class="clean">Clean State <span class="dim">(Ready for next task)</span></p>'
    else:
        git_html = '<p class="wip">Work in Progress:</p><pre>' + git_status + '</pre>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CDD Monitor</title>
<meta http-equiv="refresh" content="5">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{
  background:#14191F;color:#B0B0B0;
  font-family:'Menlo','Monaco','Consolas',monospace;
  font-size:12px;padding:8px 12px;
}}
.hdr{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}}
.hdr h1{{font-size:14px;color:#FFF;font-weight:600}}
.hdr-right{{display:flex;align-items:center;gap:8px}}
.btn-critic{{
  background:#2A2F36;color:#B0B0B0;border:1px solid #3A3F46;
  border-radius:3px;padding:2px 8px;font-family:inherit;font-size:11px;
  cursor:pointer;line-height:1.5;
}}
.btn-critic:hover{{background:#3A3F46;color:#FFF}}
.btn-critic:disabled{{cursor:not-allowed;opacity:.5}}
.btn-critic-err{{color:#FF4500;font-size:10px;margin-right:4px}}
.dim{{color:#666;font-size:0.9em}}
h2{{font-size:13px;color:#FFF;margin-bottom:6px;border-bottom:1px solid #2A2F36;padding-bottom:4px}}
h3{{font-size:11px;color:#888;margin:8px 0 2px;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #2A2F36;padding-bottom:3px}}
.features{{background:#1A2028;border-radius:4px;padding:8px 10px;margin-bottom:10px}}
.ft{{width:100%;border-collapse:collapse}}
.ft th{{text-align:left;color:#888;font-size:10px;text-transform:uppercase;letter-spacing:.5px;padding:2px 6px;border-bottom:1px solid #2A2F36}}
.ft td{{padding:2px 6px;line-height:1.5}}
.ft tr:hover{{background:#1E2630}}
.badge-cell{{text-align:center;width:70px}}
.ctx{{background:#1A2028;border-radius:4px;padding:8px 10px}}
.clean{{color:#32CD32}}
.wip{{color:#FFD700;margin-bottom:2px}}
pre{{background:#14191F;padding:6px;border-radius:3px;white-space:pre-wrap;word-wrap:break-word;max-height:100px;overflow-y:auto;margin-top:2px}}
.st-done{{color:#32CD32;font-weight:bold}}
.st-todo{{color:#FFD700;font-weight:bold}}
.st-fail{{color:#FF4500;font-weight:bold}}
.st-blocked{{color:#888;font-weight:bold}}
.st-disputed{{color:#FFA500;font-weight:bold}}
.st-na{{color:#444;font-weight:bold}}
</style>
</head>
<body>
<div class="hdr">
  <h1>CDD Monitor</h1>
  <div class="hdr-right">
    <span id="critic-err" class="btn-critic-err"></span>
    <button id="btn-critic" class="btn-critic" onclick="runCritic()">Run Critic</button>
    <span class="dim">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
  </div>
</div>
<div class="features">
    <h3>Active</h3>
    {active_html or '<p class="dim">No active features.</p>'}
    <h3>Complete</h3>
    {complete_html or '<p class="dim">None complete.</p>'}
    {overflow_html}
</div>
<div class="ctx">
  <h2>Workspace</h2>
  {git_html}
  <p class="dim" style="margin-top:4px">{last_commit}</p>
</div>
<script>
function runCritic(){{
  var btn=document.getElementById('btn-critic');
  var err=document.getElementById('critic-err');
  btn.disabled=true;btn.textContent='Running\u2026';err.textContent='';
  fetch('/run-critic',{{method:'POST'}})
    .then(function(r){{return r.json();}})
    .then(function(d){{
      if(d.status==='ok'){{location.reload();}}
      else{{err.textContent='Critic run failed';btn.disabled=false;btn.textContent='Run Critic';}}
    }})
    .catch(function(){{err.textContent='Critic run failed';btn.disabled=false;btn.textContent='Run Critic';}});
}}
</script>
</body>
</html>"""


def _role_table_html(features):
    """Renders a table of features with Architect, Builder, QA role columns."""
    if not features:
        return ""
    rows = ""
    for entry in features:
        fname = entry["file"]
        arch = _role_badge_html(entry.get("architect"))
        builder = _role_badge_html(entry.get("builder"))
        qa = _role_badge_html(entry.get("qa"))
        rows += (
            f'<tr>'
            f'<td>{fname}</td>'
            f'<td class="badge-cell">{arch}</td>'
            f'<td class="badge-cell">{builder}</td>'
            f'<td class="badge-cell">{qa}</td>'
            f'</tr>'
        )
    return (
        f'<table class="ft">'
        f'<thead><tr><th>Feature</th><th>Architect</th>'
        f'<th>Builder</th><th>QA</th></tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
    )


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status.json':
            # Public API: flat array with role fields
            api_data = generate_api_status_json()

            # Also write internal feature_status.json (old format)
            write_internal_feature_status()

            payload = json.dumps(api_data, indent=2, sort_keys=True).encode(
                'utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            # Dashboard request: also regenerate internal file
            write_internal_feature_status()
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(generate_html().encode('utf-8'))

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
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress request logging noise


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli-status":
        # CLI mode: output API JSON to stdout, regenerate internal file
        write_internal_feature_status()
        api_data = generate_api_status_json()
        json.dump(api_data, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write('\n')
    else:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"CDD Monitor serving at http://localhost:{PORT}")
            httpd.serve_forever()
