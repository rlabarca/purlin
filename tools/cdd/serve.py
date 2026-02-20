import http.server
import json
import socketserver
import subprocess
import os
from datetime import datetime, timezone

PORT = 8086
# When running as part of the core engine, we need to know where the host project is.
# Default to assuming we are in a subdirectory of the core engine, which is in the project root.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

# If we are embedded in another project, the root might be further up
if not os.path.exists(os.path.join(PROJECT_ROOT, ".agentic_devops")):
    # Try one level up (standard embedded structure)
    PARENT_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, "../"))
    if os.path.exists(os.path.join(PARENT_ROOT, ".agentic_devops")):
        PROJECT_ROOT = PARENT_ROOT

CONFIG_PATH = os.path.join(PROJECT_ROOT, ".agentic_devops/config.json")
CONFIG = {}
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'r') as f:
        CONFIG = json.load(f)

PORT = CONFIG.get("cdd_port", 8086)

FEATURES_REL = "features"
FEATURES_ABS = os.path.join(PROJECT_ROOT, "features")
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")

COMPLETE_CAP = 10
FEATURE_STATUS_PATH = os.path.join(os.path.dirname(__file__), "feature_status.json")


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
        elif test_ts > 0:
            if file_mod_ts <= test_ts:
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


def get_feature_qa_status(feature_stem, tests_dir):
    """Looks up tests/<feature_stem>/critic.json and returns QA status or None.

    Returns "CLEAN" or "HAS_OPEN_ITEMS", or None (when no critic.json exists).
    Reads the user_testing.status field from critic.json.
    Malformed JSON is treated as None (omitted).
    """
    critic_path = os.path.join(tests_dir, feature_stem, "critic.json")
    if not os.path.isfile(critic_path):
        return None
    try:
        with open(critic_path, 'r') as f:
            data = json.load(f)
        return data.get("user_testing", {}).get("status")
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


def generate_feature_status_json():
    """Generates the feature_status.json data structure per spec (flat schema)."""
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
        qa = get_feature_qa_status(stem, TESTS_DIR)
        if qa is not None:
            entry["qa_status"] = qa
        return entry

    features = {
        "complete": sorted([make_entry(n) for n, _ in complete_tuples], key=lambda x: x["file"]),
        "testing": sorted([make_entry(n) for n in testing], key=lambda x: x["file"]),
        "todo": sorted([make_entry(n) for n in todo], key=lambda x: x["file"]),
    }

    return {
        "features": features,
        "generated_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        "test_status": aggregate_test_statuses(all_test_statuses),
    }


def write_feature_status_json():
    """Writes feature_status.json to disk."""
    data = generate_feature_status_json()
    with open(FEATURE_STATUS_PATH, 'w') as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write('\n')


def get_git_status():
    """Gets the current git status."""
    return run_command("git status --porcelain | grep -v '.DS_Store' | grep -v '.cache/'")


def get_last_commit():
    """Gets the last commit message."""
    return run_command("git log -1 --format='%h %s (%cr)'")


def _badge_html(status, label=None):
    """Returns a colored badge span, or empty string if status is None."""
    if status is None:
        return ""
    css_map = {
        "PASS": "st-pass", "WARN": "st-warn", "FAIL": "st-fail",
        "CLEAN": "st-pass", "HAS_OPEN_ITEMS": "st-warn",
    }
    css = css_map.get(status, "st-fail")
    text = label or status
    return f'<span class="{css}">{text}</span>'


def _feature_table_html(features, css_class):
    """Renders a table of features with Test and QA badge columns."""
    if not features:
        return ""
    rows = ""
    for name in features:
        stem = os.path.splitext(name)[0]
        ts = get_feature_test_status(stem, TESTS_DIR)
        qa = get_feature_qa_status(stem, TESTS_DIR)
        rows += (
            f'<tr>'
            f'<td><span class="sq {css_class}"></span>{name}</td>'
            f'<td class="badge-cell">{_badge_html(ts)}</td>'
            f'<td class="badge-cell">{_badge_html(qa)}</td>'
            f'</tr>'
        )
    return (
        f'<table class="ft">'
        f'<thead><tr><th>Feature</th><th>Tests</th><th>QA</th></tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
    )


def generate_html():
    """Generates the full dashboard HTML."""
    git_status = get_git_status()
    last_commit = get_last_commit()
    complete_tuples, testing, todo = get_feature_status(FEATURES_REL, FEATURES_ABS)

    # Aggregate per-feature test statuses for the top-level badge
    all_test_statuses = []
    all_fnames = [n for n, _ in complete_tuples] + testing + todo
    for fname in all_fnames:
        stem = os.path.splitext(fname)[0]
        ts = get_feature_test_status(stem, TESTS_DIR)
        if ts is not None:
            all_test_statuses.append(ts)
    test_status = aggregate_test_statuses(all_test_statuses)
    test_msg = (
        "All features nominal" if test_status == "PASS"
        else "No test reports found" if test_status == "UNKNOWN"
        else f"{sum(1 for s in all_test_statuses if s == 'FAIL')} feature(s) failing"
    )

    # COMPLETE capping
    total_complete = len(complete_tuples)
    visible_complete = [name for name, _ in complete_tuples[:COMPLETE_CAP]]
    overflow = total_complete - COMPLETE_CAP

    todo_html = _feature_table_html(todo, "todo")
    testing_html = _feature_table_html(testing, "testing")
    complete_html = _feature_table_html(visible_complete, "complete")
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
.hdr{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px}}
.hdr h1{{font-size:14px;color:#FFF;font-weight:600}}
.dim{{color:#666;font-size:0.9em}}
h2{{font-size:13px;color:#FFF;margin-bottom:6px;border-bottom:1px solid #2A2F36;padding-bottom:4px}}
h3{{font-size:11px;color:#888;margin:8px 0 2px;text-transform:uppercase;letter-spacing:.5px}}
.features{{background:#1A2028;border-radius:4px;padding:8px 10px;margin-bottom:10px}}
.ft{{width:100%;border-collapse:collapse}}
.ft th{{text-align:left;color:#888;font-size:10px;text-transform:uppercase;letter-spacing:.5px;padding:2px 6px;border-bottom:1px solid #2A2F36}}
.ft td{{padding:2px 6px;line-height:1.5}}
.ft tr:hover{{background:#1E2630}}
.badge-cell{{text-align:center;width:60px}}
.sq{{width:7px;height:7px;margin-right:6px;flex-shrink:0;border-radius:1px}}
.sq.complete{{background:#32CD32}}
.sq.testing{{background:#4A90E2}}
.sq.todo{{background:#FFD700}}
.test-bar{{margin-top:8px;padding-top:6px;border-top:1px solid #2A2F36}}
.st-pass{{color:#32CD32;font-weight:bold}}
.st-fail{{color:#FF4500;font-weight:bold}}
.st-warn{{color:#FFA500;font-weight:bold}}
.st-unknown{{color:#666;font-weight:bold}}
.ctx{{background:#1A2028;border-radius:4px;padding:8px 10px}}
.clean{{color:#32CD32}}
.wip{{color:#FFD700;margin-bottom:2px}}
pre{{background:#14191F;padding:6px;border-radius:3px;white-space:pre-wrap;word-wrap:break-word;max-height:100px;overflow-y:auto;margin-top:2px}}
</style>
</head>
<body>
<div class="hdr">
  <h1>CDD Monitor</h1>
  <span class="dim">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
</div>
<div class="features">
    <h3>TODO</h3>
    {todo_html or '<p class="dim">None pending.</p>'}
    <h3>TESTING</h3>
    {testing_html or '<p class="dim">None in testing.</p>'}
    <h3>COMPLETE</h3>
    {complete_html or '<p class="dim">None complete.</p>'}
    {overflow_html}
    <div class="test-bar">
        <span class="st-{test_status.lower()}">{test_status}</span>
        <span class="dim">Tests: {test_msg}</span>
    </div>
</div>
<div class="ctx">
  <h2>Workspace</h2>
  {git_html}
  <p class="dim" style="margin-top:4px">{last_commit}</p>
</div>
</body>
</html>"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status.json':
            data = generate_feature_status_json()
            # Also write to disk as secondary artifact
            with open(FEATURE_STATUS_PATH, 'w') as f:
                json.dump(data, f, indent=2, sort_keys=True)
                f.write('\n')
            payload = json.dumps(data, indent=2, sort_keys=True).encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            write_feature_status_json()
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(generate_html().encode('utf-8'))

    def log_message(self, format, *args):
        pass  # Suppress request logging noise


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"CDD Monitor serving at http://localhost:{PORT}")
        httpd.serve_forever()
