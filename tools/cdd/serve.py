import http.server
import json
import socketserver
import subprocess
import os
from datetime import datetime

PORT = 8086
# When running as part of the core engine, we need to know where the host project is.
# Default to assuming we are in a subdirectory of the core engine, which is in the project root.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))

# Adjust if we are running in standalone mode (within the core engine itself)
if not os.path.exists(os.path.join(PROJECT_ROOT, "features")):
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))

# Try to find the agentic core directory relative to PROJECT_ROOT
CORE_DIR_NAME = os.path.basename(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
CORE_ABS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
CORE_REL_PATH = os.path.relpath(CORE_ABS_PATH, PROJECT_ROOT)

DOMAINS = [
    {
        "label": "Application",
        "features_rel": "features",
        "features_abs": os.path.join(PROJECT_ROOT, "features"),
        "test_mode": "auto", # Can be project-specific
        "test_label": "App Tests",
    },
    {
        "label": "Agentic Core",
        "features_rel": os.path.join(CORE_REL_PATH, "features"),
        "features_abs": os.path.join(CORE_ABS_PATH, "features"),
        "test_mode": "devops_aggregate",
        "tools_dir": os.path.join(CORE_ABS_PATH, "tools"),
        "test_label": "Core Tests",
    },
]

COMPLETE_CAP = 10


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


def get_feature_status(features_rel, features_abs):
    """Gathers the status of all features for a given domain directory."""
    if not os.path.isdir(features_abs):
        return [], [], []

    complete, testing, todo = [], [], []
    feature_files = [f for f in os.listdir(features_abs) if f.endswith('.md')]

    for fname in feature_files:
        f_path = os.path.join(features_rel, fname)

        complete_ts_str = run_command(
            f"git log -1 --grep='\[Complete {f_path}\]' --format=%ct"
        )
        test_ts_str = run_command(
            f"git log -1 --grep='\[Ready for .* {f_path}\]' --format=%ct"
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


def get_project_test_status(project_root):
    """Placeholder for project-specific test status discovery."""
    # This can be expanded to look for common test summary files (PIO, pytest, etc.)
    summary_path = os.path.join(project_root, ".pio/testing/last_summary.json")
    if os.path.exists(summary_path):
        with open(summary_path, 'r') as f:
            content = f.read()
            if '"error_nums": 0' in content and '"failure_nums": 0' in content:
                return "PASS", "Systems Nominal"
            return "FAIL", "Logic Broken"
    return "UNKNOWN", "No Test History"


def get_devops_aggregated_test_status(tools_dir):
    """Aggregates test_status.json from all tool subdirectories."""
    if not os.path.isdir(tools_dir):
        return "UNKNOWN", "No tools directory"

    found_any = False
    failures = []

    for entry in sorted(os.listdir(tools_dir)):
        status_path = os.path.join(tools_dir, entry, "test_status.json")
        if not os.path.isfile(status_path):
            continue

        found_any = True
        try:
            with open(status_path, 'r') as f:
                data = json.load(f)
            if data.get("status") != "PASS":
                failures.append(entry)
        except (json.JSONDecodeError, KeyError):
            failures.append(entry)

    if not found_any:
        return "UNKNOWN", "No test reports found"

    if failures:
        return "FAIL", f"Failing: {', '.join(failures)}"

    return "PASS", "All tools nominal"


def get_domain_test_status(domain):
    """Dispatches to the correct test status reader based on domain config."""
    if domain.get("test_mode") == "devops_aggregate":
        return get_devops_aggregated_test_status(domain["tools_dir"])
    return get_project_test_status(PROJECT_ROOT)


def get_git_status():
    """Gets the current git status."""
    return run_command("git status --porcelain | grep -v '.DS_Store' | grep -v '.cache/'")


def get_last_commit():
    """Gets the last commit message."""
    return run_command("git log -1 --format='%h %s (%cr)'")


def _feature_list_html(features, css_class):
    """Renders a <ul> of feature names with status squares."""
    if not features:
        return ""
    items = ''.join(
        f'<li><span class="sq {css_class}"></span>{name}</li>'
        for name in features
    )
    return f'<ul class="fl">{items}</ul>'


def _domain_column_html(domain):
    """Builds the HTML for one domain column."""
    complete_tuples, testing, todo = get_feature_status(
        domain["features_rel"], domain["features_abs"]
    )

    # COMPLETE capping
    total_complete = len(complete_tuples)
    visible_complete = [name for name, _ in complete_tuples[:COMPLETE_CAP]]
    overflow = total_complete - COMPLETE_CAP

    todo_html = _feature_list_html(todo, "todo")
    testing_html = _feature_list_html(testing, "testing")
    complete_html = _feature_list_html(visible_complete, "complete")
    overflow_html = (
        f'<p class="dim">and {overflow} more&hellip;</p>' if overflow > 0 else ""
    )

    test_status, test_msg = get_domain_test_status(domain)

    return f"""
    <div class="domain-col">
        <h2>{domain["label"]}</h2>
        <h3>TODO</h3>
        {todo_html or '<p class="dim">None pending.</p>'}
        <h3>TESTING</h3>
        {testing_html or '<p class="dim">None in testing.</p>'}
        <h3>COMPLETE</h3>
        {complete_html or '<p class="dim">None complete.</p>'}
        {overflow_html}
        <div class="test-bar">
            <span class="st-{test_status.lower()}">{test_status}</span>
            <span class="dim">{domain["test_label"]}: {test_msg}</span>
        </div>
    </div>"""


def generate_html():
    """Generates the full dashboard HTML."""
    git_status = get_git_status()
    last_commit = get_last_commit()

    if not git_status:
        git_html = '<p class="clean">Clean State <span class="dim">(Ready for next task)</span></p>'
    else:
        git_html = '<p class="wip">Work in Progress:</p><pre>' + git_status + '</pre>'

    domain_columns = ''.join(_domain_column_html(d) for d in DOMAINS)

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
.domains{{display:flex;gap:16px;margin-bottom:10px}}
.domain-col{{flex:1;min-width:0;background:#1A2028;border-radius:4px;padding:8px 10px}}
.fl{{list-style:none}}
.fl li{{display:flex;align-items:center;margin-bottom:1px;line-height:1.5}}
.sq{{width:7px;height:7px;margin-right:6px;flex-shrink:0;border-radius:1px}}
.sq.complete{{background:#32CD32}}
.sq.testing{{background:#4A90E2}}
.sq.todo{{background:#FFD700}}
.test-bar{{margin-top:8px;padding-top:6px;border-top:1px solid #2A2F36}}
.st-pass{{color:#32CD32;font-weight:bold}}
.st-fail{{color:#FF4500;font-weight:bold}}
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
<div class="domains">
  {domain_columns}
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
