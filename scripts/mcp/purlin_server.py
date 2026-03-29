#!/usr/bin/env python3
"""Purlin MCP Server — persistent process wrapping the CDD scan engine.

Implements the MCP (Model Context Protocol) stdio transport using JSON-RPC 2.0.
All tools use Python stdlib only (no external dependencies).

Usage:
    python3 scripts/mcp/purlin_server.py

The server reads JSON-RPC requests from stdin and writes responses to stdout.
It is started automatically by Claude Code when the plugin is enabled.
"""

import json
import os
import signal
import sys
import time

# Ensure this directory is on the path for local imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..')))

# Set PURLIN_PROJECT_ROOT if not already set (the MCP server runs from the
# plugin directory, but needs to operate on the project where it's activated)
if not os.environ.get('PURLIN_PROJECT_ROOT'):
    # Walk up from cwd to find project root
    cwd = os.getcwd()
    current = os.path.abspath(cwd)
    while True:
        if os.path.isdir(os.path.join(current, '.purlin')):
            os.environ['PURLIN_PROJECT_ROOT'] = current
            break
        parent = os.path.dirname(current)
        if parent == current:
            os.environ['PURLIN_PROJECT_ROOT'] = cwd
            break
        current = parent

from bootstrap import detect_project_root, load_config
from config_engine import (
    resolve_config, classify_file, get_mode, set_mode,
)
from credentials import get_credential, require_credential, credential_status

# Lazy imports for heavy modules (only loaded when their tools are called)
_scan_engine = None
_graph_engine = None


def _get_scan_engine():
    global _scan_engine
    if _scan_engine is None:
        import scan_engine
        _scan_engine = scan_engine
    return _scan_engine


def _get_graph_engine():
    global _graph_engine
    if _graph_engine is None:
        import graph_engine
        _graph_engine = graph_engine
    return _graph_engine


# ---------------------------------------------------------------------------
# In-memory scan cache
# ---------------------------------------------------------------------------

_scan_cache = None
_scan_cache_time = 0
CACHE_MAX_AGE = 60  # seconds


def _get_cached_scan():
    """Return cached scan result if fresh, else None."""
    global _scan_cache, _scan_cache_time
    if _scan_cache and (time.time() - _scan_cache_time) < CACHE_MAX_AGE:
        return _scan_cache
    return None


def _set_scan_cache(result):
    """Cache a scan result."""
    global _scan_cache, _scan_cache_time
    _scan_cache = result
    _scan_cache_time = time.time()


# ---------------------------------------------------------------------------
# MCP Tool Definitions
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "purlin_scan",
        "description": "Run a full project scan. Returns structured JSON with features, discoveries, deviations, delivery plan, dependency graph, and git state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cached": {
                    "type": "boolean",
                    "description": "Return cached result if less than 60s old",
                    "default": False,
                },
                "only": {
                    "type": "string",
                    "description": "Comma-separated sections to include (features,discoveries,deviations,plan,deps,git,smoke,invariants)",
                },
                "tombstones": {
                    "type": "boolean",
                    "description": "Include tombstone entries in features",
                    "default": False,
                },
                "skip_fields": {
                    "type": "string",
                    "description": "Comma-separated per-feature fields to skip (spec_modified,test_status,regression_status)",
                },
            },
        },
    },
    {
        "name": "purlin_status",
        "description": "Get interpreted work items organized by mode. Runs a scan and formats results for the specified mode.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["engineer", "pm", "qa"],
                    "description": "Mode to organize work items for",
                },
            },
        },
    },
    {
        "name": "purlin_graph",
        "description": "Generate or read the dependency graph. Returns cycles, orphans, and blocked features.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "regenerate": {
                    "type": "boolean",
                    "description": "Force regeneration of the graph",
                    "default": False,
                },
            },
        },
    },
    {
        "name": "purlin_classify",
        "description": "Classify a file path as CODE, SPEC, QA, or INVARIANT for mode guard enforcement.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "File path to classify (relative to project root)",
                },
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "purlin_mode",
        "description": "Get or set the current operating mode.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["engineer", "pm", "qa"],
                    "description": "Mode to set. Omit to get current mode.",
                },
            },
        },
    },
    {
        "name": "purlin_config",
        "description": "Read or write .purlin/config.json values.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write"],
                    "description": "Read the full config or write a key",
                    "default": "read",
                },
                "key": {
                    "type": "string",
                    "description": "Dot-separated key path for write (e.g., agents.purlin.model)",
                },
                "value": {
                    "description": "Value to write",
                },
            },
        },
    },
    {
        "name": "purlin_credentials",
        "description": "Check which credentials are configured for this Purlin project. Never returns credential values.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "check"],
                    "description": "status: all credentials; check: one specific key",
                    "default": "status",
                },
                "key": {
                    "type": "string",
                    "description": "Credential key to check (for 'check' action)",
                },
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool Handlers
# ---------------------------------------------------------------------------

def handle_purlin_scan(params):
    """Handle purlin_scan tool call."""
    cached = params.get("cached", False)
    only = params.get("only")
    tombstones = params.get("tombstones", False)
    skip_fields = params.get("skip_fields")

    only_set = set(s.strip() for s in only.split(",")) if only else None
    skip_set = set(s.strip() for s in skip_fields.split(",")) if skip_fields else None

    if cached:
        result = _get_cached_scan()
        if result:
            return result

    engine = _get_scan_engine()
    result = engine.run_scan(only=only_set)

    # Cache full scans
    if only_set is None and skip_set is None:
        _set_scan_cache(result)

    # Filter tombstones from output unless requested
    if not tombstones and "features" in result:
        result["features"] = [f for f in result["features"] if not f.get("tombstone")]

    # Strip per-feature fields if requested
    if skip_set and "features" in result:
        for feat in result["features"]:
            for field in skip_set:
                feat.pop(field, None)

    return result


def handle_purlin_status(params):
    """Handle purlin_status tool call."""
    mode = params.get("mode")
    engine = _get_scan_engine()
    result = engine.run_scan()
    _set_scan_cache(result)
    return {"mode": mode, "scan": result}


def handle_purlin_graph(params):
    """Handle purlin_graph tool call."""
    regenerate = params.get("regenerate", False)
    project_root = detect_project_root()

    if regenerate:
        engine = _get_graph_engine()
        features_dir = os.path.join(project_root, "features")
        graph_path = os.path.join(project_root, ".purlin", "cache", "dependency_graph.json")
        result = engine.generate_dependency_graph(
            engine.parse_features(features_dir),
            features_dir=features_dir,
            output_file=graph_path,
        )
        return result

    # Read cached graph
    graph_path = os.path.join(project_root, ".purlin", "cache", "dependency_graph.json")
    if os.path.isfile(graph_path):
        try:
            with open(graph_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    return {"total": 0, "cycles": [], "orphans": [], "features": []}


def handle_purlin_classify(params):
    """Handle purlin_classify tool call."""
    filepath = params.get("filepath", "")
    classification = classify_file(filepath)
    return {"filepath": filepath, "classification": classification}


def handle_purlin_mode(params):
    """Handle purlin_mode tool call."""
    mode = params.get("mode")
    if mode:
        set_mode(mode)
        return {"mode": mode, "action": "set"}
    return {"mode": get_mode(), "action": "get"}


def handle_purlin_config(params):
    """Handle purlin_config tool call."""
    action = params.get("action", "read")
    project_root = detect_project_root()

    if action == "read":
        config = resolve_config(project_root)
        return config

    # Write action
    key = params.get("key")
    value = params.get("value")
    if not key:
        return {"error": "key is required for write action"}

    config_path = os.path.join(project_root, ".purlin", "config.local.json")
    try:
        if os.path.isfile(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {}
    except (json.JSONDecodeError, IOError):
        config = {}

    # Set nested key
    parts = key.split(".")
    current = config
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
        f.write('\n')

    return {"action": "write", "key": key, "value": value}


def handle_purlin_credentials(params):
    """Handle purlin_credentials tool call."""
    action = params.get("action", "status")

    if action == "status":
        return credential_status()

    # check action
    key = params.get("key")
    if not key:
        return {"error": "key is required for check action"}

    status = credential_status()
    entry = status.get(key)
    if entry is None:
        return {"error": f"Unknown credential key: {key}"}

    result = {"key": key, **entry}
    if not entry["configured"]:
        result["hint"] = (
            f"To configure, set it in your Claude Code plugin settings: "
            f"Claude Code → Settings → Plugins → Purlin → {entry['title']}. "
            f"Or: export CLAUDE_PLUGIN_OPTION_{key}=\"<value>\""
        )
    return result


# Tool handler dispatch
TOOL_HANDLERS = {
    "purlin_scan": handle_purlin_scan,
    "purlin_status": handle_purlin_status,
    "purlin_graph": handle_purlin_graph,
    "purlin_classify": handle_purlin_classify,
    "purlin_mode": handle_purlin_mode,
    "purlin_config": handle_purlin_config,
    "purlin_credentials": handle_purlin_credentials,
}


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 Protocol
# ---------------------------------------------------------------------------

def make_response(id_, result=None, error=None):
    """Build a JSON-RPC 2.0 response."""
    resp = {"jsonrpc": "2.0", "id": id_}
    if error is not None:
        resp["error"] = error
    else:
        resp["result"] = result
    return resp


def handle_request(request):
    """Process a single JSON-RPC request and return a response dict."""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return make_response(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "purlin", "version": "0.9.0"},
        })

    if method == "notifications/initialized":
        return None  # No response for notifications

    if method == "tools/list":
        return make_response(req_id, {"tools": TOOLS})

    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            return make_response(req_id, error={
                "code": -32601,
                "message": f"Unknown tool: {tool_name}",
            })
        try:
            result = handler(tool_args)
            return make_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            })
        except Exception as e:
            return make_response(req_id, {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True,
            })

    # Unknown method
    return make_response(req_id, error={
        "code": -32601,
        "message": f"Method not found: {method}",
    })


def run_server():
    """Run the MCP stdio server loop."""
    # Handle graceful shutdown
    def shutdown(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # Read JSON-RPC messages from stdin, write responses to stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = make_response(None, error={
                "code": -32700,
                "message": "Parse error",
            })
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            continue

        response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_server()
