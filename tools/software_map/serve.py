import http.server
import socketserver
import os
import json

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

DIRECTORY = os.path.dirname(__file__)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == '/config.json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            config_data = {"is_meta_agentic_dev": False}
            if os.path.exists(CONFIG_PATH):
                try:
                    with open(CONFIG_PATH, 'r') as f:
                        config_data = json.load(f)
                except:
                    pass
            self.wfile.write(json.dumps(config_data).encode('utf-8'))
        else:
            super().do_GET()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Software Map serving at http://localhost:{PORT}")
        httpd.serve_forever()
