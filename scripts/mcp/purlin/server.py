#!/usr/bin/env python3
"""The Purlin MCP server: three tools over JSON-RPC 2.0 on stdio.

    python3 scripts/mcp/purlin/server.py

Requests arrive one JSON object per line on stdin and responses leave the same
way on stdout; stdout carries nothing else, so every message the server has
for a person goes to stderr. Claude Code starts it when the plugin is enabled.

Three tools, each naming the folder it answers for with `project_root`:

`sync_status`   one row per spec and the cells of every rule, as a table
`drift`         what changed since your last pull, in one view, as JSON
`purlin_config` read or write `.purlin/config.json`

A call that names no `project_root` is refused: the server never answers for
the folder it was started in, since a session may work in several checkouts.
"""

import json
import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from config_engine import (KNOWN_KEYS, PROJECT_ROOT_SOURCES, config_problem,
                           resolve_config, resolve_project_root,
                           update_config)
from purlin import PURLIN_VERSION
from purlin import console as console_module
from purlin import drift as drift_module
from purlin import status as status_module

SERVER_INFO = {"name": "purlin", "version": PURLIN_VERSION}

# Every tool takes the same root, so every tool declares it the same way. It
# is not listed as required, so a client sends a call that names none and the
# server answers it with the one line that says what to pass.
_PROJECT_ROOT_PROPERTY = {
    "type": "string",
    "description": (
        "The top folder of the git checkout you are working in, the one "
        "holding .purlin/. Every call names it."
    ),
}

TOOLS = [
    {
        "name": "sync_status",
        "description": (
            "Show one row per spec and the cells of every rule per feature. "
            "Reads specs/ and .purlin/evidence/, and returns the table with "
            "the next step."),
        "inputSchema": {
            "type": "object",
            "properties": {"project_root": _PROJECT_ROOT_PROPERTY},
            "required": [],
        },
    },
    {
        "name": "purlin_config",
        "description": (
            "Read .purlin/config.json, or write its tests setting. The file "
            "holds version and tests."),
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
            "What changed since the last git action that brought changes "
            "in: the newest pull, merge, rebase, checkout, clone or reset in "
            "git's log of HEAD, else the last 20 commits. Returns JSON with "
            "the range and one view of it, for the purlin:drift skill to "
            "print."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "since": {
                    "type": "string",
                    "description": ("Override where the range starts: a "
                                    "number of commits or a YYYY-MM-DD "
                                    "date."),
                },
                "project_root": _PROJECT_ROOT_PROPERTY,
            },
            "required": [],
        },
    },
]

TOOL_NAMES = tuple(tool['name'] for tool in TOOLS)


NEEDS_PROJECT_ROOT = ('%s needs project_root: pass the top folder of the git '
                      'checkout you are working in.')
NO_PROJECT_HERE = ('No Purlin project root at %s: .purlin/config.json is not '
                   'there. Run purlin:init there, or pass the top folder of a '
                   'Purlin project as project_root.')
NOT_SAVED = 'The setting was not saved: %s.'
NO_KEY = 'A change needs a key; nothing was saved.'
SAVED = '%s is now %s; saved to .purlin/config.json.'
NO_VALUE = 'A change needs a value; nothing was saved.'
NOT_ACCEPTED = '"%s" is not accepted for %s; it takes %s. Nothing was saved.'
VERSION_NOT_WRITTEN = ("version is written by purlin:init from Purlin's own "
                       "version; nothing was saved.")
NOT_A_SETTING = ('%s is not a setting; .purlin/config.json holds version and '
                 'tests. Nothing was saved.')
UNKNOWN_ACTION = "Unknown action: %s. Use 'read' or 'write'."


def _write_refusal(key, arguments):
    """Why a write of `key` is refused, in the tool's words, or None."""
    if key == 'version':
        return VERSION_NOT_WRITTEN
    if key not in KNOWN_KEYS:
        return NOT_A_SETTING % key
    if 'value' not in arguments:
        return NO_VALUE
    value = arguments['value']
    if isinstance(value, list):
        return None
    shown = value if isinstance(value, str) else json.dumps(value)
    return NOT_ACCEPTED % (shown, key, 'a list')


def handle_purlin_config(project_root, arguments):
    """Read or write one key of `.purlin/config.json`, or dump the whole file.

    A key that is absent or stored as null reads as `{"<key>": null}`, the
    shape of a found key, so a reader handles one shape. A write sets `tests`
    alone; every other write is refused and the file left as it was.
    """
    action = arguments.get('action', 'read')
    key = arguments.get('key')
    value = arguments.get('value')

    if action == 'read':
        config = resolve_config(project_root)
        if key:
            return json.dumps({key: config.get(key)}, indent=2)
        return json.dumps(config, indent=2)
    if action == 'write':
        if not key:
            return NO_KEY
        refusal = _write_refusal(key, arguments)
        if refusal:
            return refusal
        try:
            update_config(project_root, key, value)
        except OSError as error:
            return NOT_SAVED % (error.strerror or error)
        return SAVED % (key, json.dumps(value))
    return UNKNOWN_ACTION % action


def _call_root(arguments):
    """The folder a call names, resolved, `~` standing for the home folder;
    None when it names none."""
    named = arguments.get('project_root')
    if not isinstance(named, str) or not named.strip():
        return None
    return os.path.abspath(os.path.expanduser(named))


def _text_result(req_id, text):
    return {"jsonrpc": "2.0", "id": req_id,
            "result": {"content": [{"type": "text", "text": text}]}}


def handle_request(request):
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

        if tool_name not in TOOL_NAMES:
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32601,
                              "message": "Unknown tool: %s" % tool_name}}

        call_root = _call_root(arguments)
        if call_root is None:
            return _text_result(req_id, NEEDS_PROJECT_ROOT % tool_name)
        # One check for all three: a root with no config.json is not a
        # project root, and every one of the three would otherwise answer as
        # if it were an empty one.
        if not os.path.isfile(os.path.join(call_root, '.purlin', 'config.json')):
            return _text_result(req_id, NO_PROJECT_HERE % call_root)
        # A settings file that cannot be read stops every tool the same way,
        # before anything reads it as empty or writes over it.
        problem = config_problem(call_root)
        if problem:
            return _text_result(req_id, problem)

        try:
            if tool_name == 'sync_status':
                text = status_module.sync_status(call_root)
            elif tool_name == 'purlin_config':
                text = handle_purlin_config(call_root, arguments)
            else:
                text = drift_module.drift(call_root,
                                          since=arguments.get('since'))
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
    console_module.force_utf8_stdio()
    # One answer is one line ending in a line feed on every system: Windows
    # would otherwise end each line on stdout with a carriage return too.
    try:
        sys.stdout.reconfigure(newline='\n')
    except (AttributeError, ValueError, OSError):
        pass
    # The folder the server was started in, named for a person reading the
    # log; no call is answered for it.
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
        response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + '\n')
            sys.stdout.flush()


if __name__ == '__main__':
    main()
