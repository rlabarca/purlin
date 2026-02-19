import http.server
import socketserver
import os
import json
import threading
import time
import subprocess
import sys
import urllib.parse

# When running as part of the core engine, we need to know where the host project is.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

# If we are embedded in another project, the root might be further up
if not os.path.exists(os.path.join(PROJECT_ROOT, ".agentic_devops")):
    # Try one level up (standard embedded structure)
    PARENT_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, "../"))
    if os.path.exists(os.path.join(PARENT_ROOT, ".agentic_devops")):
        PROJECT_ROOT = PARENT_ROOT

CONFIG_PATH = os.path.join(PROJECT_ROOT, ".agentic_devops/config.json")
PORT = 8087
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
        PORT = config.get("map_port", 8087)

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
GENERATE_SCRIPT = os.path.join(DIRECTORY, "generate_tree.py")
FEATURES_DIR = os.path.join(PROJECT_ROOT, "features")
POLL_INTERVAL = 2  # seconds


def get_dir_snapshot(directory):
    """Get a dict of {filename: mtime} for all .md files in a directory."""
    snapshot = {}
    if not os.path.exists(directory):
        return snapshot
    for entry in os.scandir(directory):
        if entry.is_file() and entry.name.endswith(".md"):
            snapshot[entry.name] = entry.stat().st_mtime
    return snapshot


def run_generator():
    """Run generate_tree.py to regenerate all outputs."""
    python_exe = sys.executable
    try:
        result = subprocess.run(
            [python_exe, GENERATE_SCRIPT],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print(f"[watcher] Regenerated outputs at {time.strftime('%H:%M:%S')}")
        else:
            print(f"[watcher] Generation failed: {result.stderr}")
    except Exception as e:
        print(f"[watcher] Error running generator: {e}")


def file_watcher():
    """Poll features directory for changes and regenerate on modification."""
    snapshot = get_dir_snapshot(FEATURES_DIR)

    while True:
        time.sleep(POLL_INTERVAL)
        new_snapshot = get_dir_snapshot(FEATURES_DIR)
        if new_snapshot != snapshot:
            print(f"[watcher] Change detected, regenerating...")
            snapshot = new_snapshot
            run_generator()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == '/config.json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            config_data = {}
            if os.path.exists(CONFIG_PATH):
                try:
                    with open(CONFIG_PATH, 'r') as f:
                        config_data = json.load(f)
                except:
                    pass
            self.wfile.write(json.dumps(config_data).encode('utf-8'))
        elif self.path.startswith('/feature?'):
            self._serve_feature_content()
        else:
            super().do_GET()

    def _serve_feature_content(self):
        """Serve the raw markdown content of a feature file."""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        file_param = params.get('file', [''])[0]

        # Resolve to absolute path
        abs_path = os.path.normpath(os.path.join(PROJECT_ROOT, file_param))

        # Security: ensure path is within the features directory
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

    def log_message(self, format, *args):
        pass  # Suppress request logging noise


if __name__ == "__main__":
    # Initial generation on startup
    print("Running initial generation...")
    run_generator()

    # Start file watcher in background thread
    watcher_thread = threading.Thread(target=file_watcher, daemon=True)
    watcher_thread.start()
    print(f"File watcher active (polling every {POLL_INTERVAL}s)")

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Software Map serving at http://localhost:{PORT}")
        httpd.serve_forever()
