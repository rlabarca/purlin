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
    resolve_config, classify_file,
    read_sync_state, read_sync_ledger, get_sync_summary,
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
                "compact": {
                    "type": "boolean",
                    "description": "Return compact feature entries (name, lifecycle, file only)",
                    "default": False,
                },
            },
        },
    },
    {
        "name": "purlin_status",
        "description": "Get classified project status with role-based work items. Server-side summarization returns pre-bucketed work items instead of raw feature arrays.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "verbosity": {
                    "type": "string",
                    "enum": ["minimal", "focused", "full"],
                    "description": "minimal: counts + top 3 items per role. focused: all actionable items (default). full: adds complete feature names.",
                    "default": "focused",
                },
                "role": {
                    "type": "string",
                    "enum": ["engineer", "qa", "pm", "all"],
                    "description": "Filter work items to a specific role. Default: all.",
                    "default": "all",
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
        "name": "purlin_constraints",
        "description": "Get all constraint files (anchors, scoped invariants, global invariants) governing a feature via transitive prerequisite walk. Use during purlin:build Step 0 pre-flight.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feature": {
                    "type": "string",
                    "description": "Feature stem (e.g., 'purlin_build') or filename ('purlin_build.md')",
                },
            },
            "required": ["feature"],
        },
    },
    {
        "name": "purlin_classify",
        "description": "Classify a file path as CODE, SPEC, QA, or INVARIANT for write guard enforcement.",
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
        "name": "purlin_sync",
        "description": "Get per-feature sync status. Shows which features have spec-code drift, which are synced, and which have uncommitted session changes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feature": {
                    "type": "string",
                    "description": "Optional feature stem to filter results to a single feature.",
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

    # Compact mode: reduce features to name, file, lifecycle only
    if params.get("compact") and "features" in result:
        result["features"] = [
            {"name": f["name"], "file": f["file"],
             "lifecycle": f.get("lifecycle", "UNKNOWN")}
            for f in result["features"]
        ]

    return result


def handle_purlin_status(params):
    """Handle purlin_status tool call.

    Returns pre-classified work items grouped by role, with verbosity
    and role filtering applied server-side.  The raw feature array never
    leaves the server — only the summary is returned.
    """
    verbosity = params.get("verbosity", "focused")
    role_filter = params.get("role", "all")

    project_root = detect_project_root()
    engine = _get_scan_engine()

    # Full scan internally (needed for classification), then cache.
    result = engine.run_scan()
    _set_scan_cache(result)

    # Get sync summary for overlay.
    sync_summary = get_sync_summary(project_root)

    # Classify work items server-side.
    classified = engine.classify_work_items(result, sync_summary)

    # Apply role filter.
    if role_filter != "all":
        classified["work"] = {
            role_filter: classified["work"].get(
                role_filter, {"count": 0, "items": []}
            )
        }

    # Apply verbosity.
    if verbosity == "minimal":
        # Counts + top 3 items per role.
        for role_data in classified["work"].values():
            role_data["items"] = role_data["items"][:3]
    elif verbosity == "full":
        # Add list of COMPLETE feature names for reference.
        classified["complete_features"] = [
            f["name"] for f in result.get("features", [])
            if f.get("lifecycle") == "COMPLETE" and not f.get("tombstone")
        ]

    return classified


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


def handle_purlin_constraints(params):
    """Handle purlin_constraints tool call."""
    feature = params.get("feature", "")
    if not feature:
        return {"error": "feature parameter is required"}
    engine = _get_graph_engine()
    return engine.get_feature_constraints(feature)


def handle_purlin_classify(params):
    """Handle purlin_classify tool call."""
    filepath = params.get("filepath", "")
    classification = classify_file(filepath)
    return {"filepath": filepath, "classification": classification}


def handle_purlin_sync(params):
    """Handle purlin_sync tool call — returns per-feature sync status."""
    project_root = detect_project_root()
    feature = params.get("feature")

    summary = get_sync_summary(project_root)

    if feature:
        entry = summary.get(feature)
        if entry:
            return {"feature": feature, **entry}
        return {"feature": feature, "sync_status": "not_found",
                "message": f"No sync data for feature '{feature}'"}

    return {"features": summary}


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

    # Enforce coupling: auto_start requires find_work
    # - Turning on auto_start automatically turns on find_work
    # - Turning off find_work automatically turns off auto_start
    coupled = None
    if key == "agents.purlin.auto_start" and value is True:
        agents = config.get("agents", {})
        purlin = agents.get("purlin", {})
        if not purlin.get("find_work", True):
            purlin["find_work"] = True
            coupled = {"key": "agents.purlin.find_work", "value": True,
                       "reason": "auto-start requires find-work"}
    elif key == "agents.purlin.find_work" and value is False:
        agents = config.get("agents", {})
        purlin = agents.get("purlin", {})
        if purlin.get("auto_start", False):
            purlin["auto_start"] = False
            coupled = {"key": "agents.purlin.auto_start", "value": False,
                       "reason": "auto-start requires find-work"}

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
        f.write('\n')

    result = {"action": "write", "key": key, "value": value}
    if coupled:
        result["coupled"] = coupled
    return result


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
    "purlin_constraints": handle_purlin_constraints,
    "purlin_classify": handle_purlin_classify,
    "purlin_sync": handle_purlin_sync,
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
