#!/usr/bin/env python3
"""The Purlin MCP server: three tools over JSON-RPC 2.0 on stdio.

    python3 scripts/mcp/purlin/server.py

Requests arrive one JSON object per line on stdin and responses leave the same
way on stdout; stdout carries nothing else, so every message the server has
for a person goes to stderr. Claude Code starts it when the plugin is enabled.

Three tools, each taking the same optional `project_root`:

`sync_status`   the seven-state table for the workspace
`drift`         what changed since the last verification, as JSON
`purlin_config` read or write `.purlin/config.json`
"""

import json
import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from config_engine import (PROJECT_ROOT_SOURCES, resolve_config,
                           resolve_project_root, update_config)
from purlin import PURLIN_VERSION
from purlin import drift as drift_module
from purlin import payload as payload_module
from purlin import status as status_module

SERVER_INFO = {"name": "purlin", "version": PURLIN_VERSION}

# Every tool takes the same optional root, so every tool declares it the same
# way. A session opened above or beside the workspace (a monorepo root, a
# worktree) names the workspace per call instead of restarting the server,
# which resolves its default root once at startup.
_PROJECT_ROOT_PROPERTY = {
    "type": "string",
    "description": (
        "Directory of the Purlin workspace (the one holding .purlin/). "
        "Defaults to the root the server resolved at startup."
    ),
}

TOOLS = [
    {
        "name": "sync_status",
        "description": (
            "Show the state of every rule per feature. Reads specs/, the "
            "runtime proof files and .purlin/records/, and returns the "
            "seven-state table with the next step."),
        "inputSchema": {
            "type": "object",
            "properties": {"project_root": _PROJECT_ROOT_PROPERTY},
            "required": [],
        },
    },
    {
        "name": "purlin_config",
        "description": "Read or update Purlin configuration from .purlin/config.json.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform: 'read' or 'write'.",
                    "enum": ["read", "write"],
                },
                "key": {"type": "string",
                        "description": "Config key to read or write."},
                "value": {"description": "Value to set (for write action)."},
                "project_root": _PROJECT_ROOT_PROPERTY,
            },
            "required": [],
        },
    },
    {
        "name": "drift",
        "description": (
            "Structured summary of what changed since the last verification. "
            "Returns JSON with commits, classified files, spec changes, pins "
            "and the four role views for the purlin:drift skill to read."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "since": {
                    "type": "string",
                    "description": ("Override the anchor: a number of commits "
                                    "or a YYYY-MM-DD date."),
                },
                "role": {
                    "type": "string",
                    "description": "Narrow the report to one role's view.",
                    "enum": list(drift_module.ROLES),
                },
                "project_root": _PROJECT_ROOT_PROPERTY,
            },
            "required": [],
        },
    },
]


def generate_digest(project_root, generated_by='hook', network=True,
                    only_if_changed=False):
    """Write `.purlin/report-data.js` for the local dashboard.

    The refresh hook calls this after something changed what the dashboard
    reports. It never runs a test and never reaches the network when
    `network` is False: what it writes is the payload built from what is
    already on disk.
    """
    config = resolve_config(project_root)
    if not config:
        return None
    data = payload_module.build_payload(project_root,
                                        generated_by=generated_by,
                                        config=config)
    if not data['features']:
        return None
    if network:
        try:
            data['drift'] = drift_module.compute_drift(
                project_root, network=True, data=data)
        except Exception:
            pass
    return payload_module.write_report_data(project_root, data,
                                            only_if_changed=only_if_changed)


def handle_purlin_config(project_root, arguments):
    """Read or write one config key, or dump the merged config."""
    action = arguments.get('action', 'read')
    key = arguments.get('key')
    value = arguments.get('value')
    config = resolve_config(project_root)

    if action == 'read':
        if key:
            found = config.get(key)
            if found is None:
                return "Key '%s' not found in config." % key
            return json.dumps({key: found}, indent=2)
        return json.dumps(config, indent=2)
    if action == 'write':
        if not key:
            return "Error: 'key' is required for write action."
        update_config(project_root, key, value)
        return "Set '%s' = %s" % (key, json.dumps(value))
    return "Unknown action: %s. Use 'read' or 'write'." % action


def _no_workspace_text(root, source_text):
    """What a tool says instead of a report when the root holds no workspace.

    Reporting zero features for a root that was never a workspace reads as a
    project with nothing in it. Naming the root and how it was chosen turns
    that into the one fact the caller needs: they are pointed somewhere else.
    """
    return (
        'No Purlin workspace at {root}: .purlin/config.json is not there. '
        'That root came from {source}.\n'
        '→ Fix: pass project_root to this tool, or set PURLIN_PROJECT_ROOT '
        'to the workspace directory (in .claude/settings.json "env" for the '
        'project), or run purlin:init there.'
    ).format(root=root, source=source_text)


def _resolve_call_root(default_root, arguments):
    """The root for one tool call, with how it was chosen, in words."""
    arg_root = arguments.get('project_root')
    if arg_root:
        return (os.path.abspath(os.path.expanduser(arg_root)),
                'the project_root argument')
    source = resolve_project_root()[1]
    return default_root, PROJECT_ROOT_SOURCES.get(source, source)


def _text_result(req_id, text):
    return {"jsonrpc": "2.0", "id": req_id,
            "result": {"content": [{"type": "text", "text": text}]}}


def handle_request(request, project_root):
    """Handle one JSON-RPC request and return a response dict, or None."""
    method = request.get('method', '')
    req_id = request.get('id')
    params = request.get('params', {})

    if method == 'initialize':
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }

    if method == 'notifications/initialized':
        return None

    if method == 'tools/list':
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    if method == 'tools/call':
        tool_name = params.get('name', '')
        arguments = params.get('arguments', {})

        if tool_name not in ('sync_status', 'purlin_config', 'drift'):
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32601,
                              "message": "Unknown tool: %s" % tool_name}}

        call_root, root_source = _resolve_call_root(project_root, arguments)
        # One check for all three: a root with no config.json is not a
        # workspace, and every one of the three would otherwise answer as if
        # it were an empty one.
        if not os.path.isfile(os.path.join(call_root, '.purlin', 'config.json')):
            return _text_result(req_id,
                                _no_workspace_text(call_root, root_source))

        try:
            if tool_name == 'sync_status':
                text = status_module.sync_status(call_root)
            elif tool_name == 'purlin_config':
                text = handle_purlin_config(call_root, arguments)
            else:
                text = drift_module.drift(call_root,
                                          since=arguments.get('since'),
                                          role=arguments.get('role'))
        except Exception as exc:  # a tool error is an answer, never a crash
            text = 'Error running %s: %s' % (tool_name, exc)
        return _text_result(req_id, text)

    if req_id is not None:
        return {"jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601,
                          "message": "Unknown method: %s" % method}}
    return None


def main():
    """Run the server on stdio until stdin closes."""
    project_root, root_source = resolve_project_root()
    print('Purlin MCP server v%s started (root: %s, from %s)'
          % (PURLIN_VERSION, project_root,
             PROJECT_ROOT_SOURCES.get(root_source, root_source)),
          file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError:
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32700, "message": "Parse error"}}) + '\n')
            sys.stdout.flush()
            continue
        response = handle_request(request, project_root)
        if response is not None:
            sys.stdout.write(json.dumps(response) + '\n')
            sys.stdout.flush()


if __name__ == '__main__':
    main()
