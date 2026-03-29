#!/usr/bin/env python3
"""Agentic Toolbox management CLI.

Implements create, modify, and delete sub-commands for managing project tools
per features/purlin_toolbox.md.
"""
import argparse
import json
import os
import sys
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'mcp')))
from bootstrap import detect_project_root, load_config, atomic_write as _bootstrap_atomic_write

PROJECT_ROOT = detect_project_root(SCRIPT_DIR)

PURLIN_TOOLS_PATH = os.path.join(SCRIPT_DIR, "purlin_tools.json")

# Framework repo detection: project tools live in dev/ (tracked) not .purlin/toolbox/ (gitignored)
_IS_FRAMEWORK_REPO = os.path.abspath(SCRIPT_DIR).startswith(os.path.abspath(PROJECT_ROOT))
if _IS_FRAMEWORK_REPO:
    PROJECT_TOOLS_PATH = os.path.join(PROJECT_ROOT, "dev", "project_tools.json")
else:
    PROJECT_TOOLS_PATH = os.path.join(PROJECT_ROOT, ".purlin", "toolbox", "project_tools.json")

RESERVED_PREFIXES = ("purlin.", "community.")


def _load_json_safe(path):
    """Load a JSON file, returning None on any error."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return None


def _load_tools(path):
    """Load tools array from a JSON file. Returns [] if absent."""
    data = _load_json_safe(path)
    if data is None:
        return []
    return data.get("tools", data.get("steps", []))


def _atomic_write(path, data):
    """Write JSON atomically via bootstrap module."""
    _bootstrap_atomic_write(path, data, as_json=True)


def _find_tool_index(tools, tool_id):
    """Find index of tool with given ID, or -1."""
    for i, t in enumerate(tools):
        if t.get("id") == tool_id:
            return i
    return -1


def _write_project_tools(tools):
    """Write project tools registry."""
    os.makedirs(os.path.dirname(PROJECT_TOOLS_PATH), exist_ok=True)
    _atomic_write(PROJECT_TOOLS_PATH, {"schema_version": "2.0", "tools": tools})


def cmd_create(args):
    tool_id = args.id
    friendly_name = args.name
    description = args.desc

    if not tool_id:
        print("Error: tool ID must not be empty.", file=sys.stderr)
        return 1

    for prefix in RESERVED_PREFIXES:
        if tool_id.startswith(prefix):
            print(
                f"Error: tool ID '{tool_id}' uses the reserved '{prefix}' prefix. "
                f"Project tools must not start with 'purlin.' or 'community.'.",
                file=sys.stderr,
            )
            return 1

    if not friendly_name:
        print("Error: friendly_name must be non-empty.", file=sys.stderr)
        return 1

    if not description:
        print("Error: description must be non-empty.", file=sys.stderr)
        return 1

    project_tools = _load_tools(PROJECT_TOOLS_PATH)
    if _find_tool_index(project_tools, tool_id) >= 0:
        print(
            f"Error: tool '{tool_id}' already exists in project tools.",
            file=sys.stderr,
        )
        return 1

    purlin_tools = _load_tools(PURLIN_TOOLS_PATH)
    if _find_tool_index(purlin_tools, tool_id) >= 0:
        print(
            f"Error: tool '{tool_id}' already exists in purlin tools.",
            file=sys.stderr,
        )
        return 1

    new_tool = {
        "id": tool_id,
        "friendly_name": friendly_name,
        "description": description,
        "code": args.code if args.code else None,
        "agent_instructions": args.agent_instructions if args.agent_instructions else None,
        "metadata": {
            "last_updated": date.today().isoformat(),
        },
    }

    new_data = {"schema_version": "2.0", "tools": project_tools + [new_tool]}

    if args.dry_run:
        print("[DRY RUN] project_tools.json would be written as:")
        print(json.dumps(new_data, indent=2))
        return 0

    _write_project_tools(project_tools + [new_tool])
    print(f"Created tool '{tool_id}' in project_tools.json.")
    return 0


def cmd_modify(args):
    tool_id = args.id

    has_field = any([
        args.name is not None,
        args.desc is not None,
        args.code is not None,
        args.agent_instructions is not None,
        args.clear_code,
        args.clear_agent_instructions,
    ])
    if not has_field:
        print(
            "Error: at least one field flag is required for modify.",
            file=sys.stderr,
        )
        return 1

    if args.code is not None and args.clear_code:
        print(
            "Error: --code and --clear-code are mutually exclusive.",
            file=sys.stderr,
        )
        return 1
    if args.agent_instructions is not None and args.clear_agent_instructions:
        print(
            "Error: --agent-instructions and --clear-agent-instructions are mutually exclusive.",
            file=sys.stderr,
        )
        return 1

    project_tools = _load_tools(PROJECT_TOOLS_PATH)
    idx = _find_tool_index(project_tools, tool_id)
    if idx < 0:
        print(f"Error: tool not found in project tools: {tool_id}", file=sys.stderr)
        return 1

    tool = dict(project_tools[idx])

    if args.name is not None:
        tool["friendly_name"] = args.name
    if args.desc is not None:
        tool["description"] = args.desc
    if args.clear_code:
        tool["code"] = None
    elif args.code is not None:
        tool["code"] = args.code
    if args.clear_agent_instructions:
        tool["agent_instructions"] = None
    elif args.agent_instructions is not None:
        tool["agent_instructions"] = args.agent_instructions
    tool.setdefault("metadata", {})
    tool["metadata"]["last_updated"] = date.today().isoformat()

    updated_tools = list(project_tools)
    updated_tools[idx] = tool

    if args.dry_run:
        print("[DRY RUN] project_tools.json would be written as:")
        print(json.dumps({"schema_version": "2.0", "tools": updated_tools}, indent=2))
        return 0

    _write_project_tools(updated_tools)
    print(f"Updated tool '{tool_id}' in project_tools.json.")
    return 0


def cmd_delete(args):
    tool_id = args.id

    project_tools = _load_tools(PROJECT_TOOLS_PATH)
    idx = _find_tool_index(project_tools, tool_id)
    if idx < 0:
        print(f"Error: tool not found in project tools: {tool_id}", file=sys.stderr)
        return 1

    updated_tools = [t for t in project_tools if t.get("id") != tool_id]

    if args.dry_run:
        print("[DRY RUN] project_tools.json would be written as:")
        print(json.dumps({"schema_version": "2.0", "tools": updated_tools}, indent=2))
        return 0

    _write_project_tools(updated_tools)
    print(f"Deleted tool '{tool_id}' from project_tools.json.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Manage Agentic Toolbox project tools."
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-command")

    # create
    p_create = subparsers.add_parser("create", help="Create a new project tool")
    p_create.add_argument("--id", required=True, help="Tool ID")
    p_create.add_argument("--name", required=True, help="Friendly name")
    p_create.add_argument("--desc", required=True, help="Description")
    p_create.add_argument("--code", default=None, help="Shell command")
    p_create.add_argument(
        "--agent-instructions", default=None, help="Agent instructions"
    )
    p_create.add_argument(
        "--dry-run", action="store_true", help="Print proposed output without writing"
    )

    # modify
    p_modify = subparsers.add_parser("modify", help="Modify an existing project tool")
    p_modify.add_argument("id", help="Tool ID to modify")
    p_modify.add_argument("--name", default=None, help="New friendly name")
    p_modify.add_argument("--desc", default=None, help="New description")
    p_modify.add_argument("--code", default=None, help="New shell command")
    p_modify.add_argument(
        "--agent-instructions", default=None, help="New agent instructions"
    )
    p_modify.add_argument(
        "--clear-code", action="store_true", help="Set code to null"
    )
    p_modify.add_argument(
        "--clear-agent-instructions",
        action="store_true",
        help="Set agent_instructions to null",
    )
    p_modify.add_argument(
        "--dry-run", action="store_true", help="Print proposed output without writing"
    )

    # delete
    p_delete = subparsers.add_parser("delete", help="Delete a project tool")
    p_delete.add_argument("id", help="Tool ID to delete")
    p_delete.add_argument(
        "--dry-run", action="store_true", help="Print proposed output without writing"
    )

    args = parser.parse_args()

    if args.command == "create":
        sys.exit(cmd_create(args))
    elif args.command == "modify":
        sys.exit(cmd_modify(args))
    elif args.command == "delete":
        sys.exit(cmd_delete(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
