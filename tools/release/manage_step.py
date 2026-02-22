#!/usr/bin/env python3
"""Local release step management CLI.

Implements create, modify, and delete sub-commands for managing local release
steps per features/release_step_management.md.
"""
import argparse
import json
import os
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Project root detection (submodule_bootstrap.md Section 2.11)
_env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
if _env_root and os.path.isdir(_env_root):
    PROJECT_ROOT = _env_root
else:
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
    for depth in ('../../../', '../../'):
        candidate = os.path.abspath(os.path.join(SCRIPT_DIR, depth))
        if os.path.exists(os.path.join(candidate, '.purlin')):
            PROJECT_ROOT = candidate
            break

# Config loading with resilience (Section 2.13)
_config_path = os.path.join(PROJECT_ROOT, ".purlin/config.json")
_config = {}
if os.path.exists(_config_path):
    try:
        with open(_config_path, 'r') as f:
            _config = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        pass

TOOLS_ROOT = _config.get("tools_root", "tools")

GLOBAL_STEPS_PATH = os.path.join(PROJECT_ROOT, TOOLS_ROOT, "release", "global_steps.json")
LOCAL_STEPS_PATH = os.path.join(PROJECT_ROOT, ".purlin", "release", "local_steps.json")
LOCAL_CONFIG_PATH = os.path.join(PROJECT_ROOT, ".purlin", "release", "config.json")

RESERVED_PREFIX = "purlin."


def _load_json_safe(path):
    """Load a JSON file, returning None on any error."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return None


def _load_steps(path):
    """Load steps array from a JSON file. Returns [] if absent."""
    data = _load_json_safe(path)
    if data is None:
        return []
    return data.get("steps", [])


def _atomic_write(path, data):
    """Write JSON atomically: temp file in same dir, then rename."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(path), suffix=".tmp"
    )
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _find_step_index(steps, step_id):
    """Find index of step with given ID, or -1."""
    for i, s in enumerate(steps):
        if s.get("id") == step_id:
            return i
    return -1


def cmd_create(args):
    step_id = args.id
    friendly_name = args.name
    description = args.desc

    # Validation: empty ID
    if not step_id:
        print("Error: step ID must not be empty.", file=sys.stderr)
        return 1

    # Validation: reserved prefix
    if step_id.startswith(RESERVED_PREFIX):
        print(
            f"Error: step ID '{step_id}' uses the reserved '{RESERVED_PREFIX}' prefix.",
            file=sys.stderr,
        )
        return 1

    # Validation: empty name
    if not friendly_name:
        print("Error: friendly_name must be non-empty.", file=sys.stderr)
        return 1

    # Validation: empty description
    if not description:
        print("Error: description must be non-empty.", file=sys.stderr)
        return 1

    # Validation: duplicate in local steps
    local_steps = _load_steps(LOCAL_STEPS_PATH)
    if _find_step_index(local_steps, step_id) >= 0:
        print(
            f"Error: step '{step_id}' already exists in local steps.",
            file=sys.stderr,
        )
        return 1

    # Validation: duplicate in global steps
    global_steps = _load_steps(GLOBAL_STEPS_PATH)
    if _find_step_index(global_steps, step_id) >= 0:
        print(
            f"Error: step '{step_id}' already exists in global steps.",
            file=sys.stderr,
        )
        return 1

    new_step = {
        "id": step_id,
        "friendly_name": friendly_name,
        "description": description,
        "code": args.code if args.code else None,
        "agent_instructions": args.agent_instructions if args.agent_instructions else None,
    }

    new_local_data = {"steps": local_steps + [new_step]}

    config_steps = _load_steps(LOCAL_CONFIG_PATH)
    new_config_data = {
        "steps": config_steps + [{"id": step_id, "enabled": True}]
    }

    if args.dry_run:
        print("[DRY RUN] local_steps.json would be written as:")
        print(json.dumps(new_local_data, indent=2))
        print()
        print("[DRY RUN] config.json would be written as:")
        print(json.dumps(new_config_data, indent=2))
        return 0

    _atomic_write(LOCAL_STEPS_PATH, new_local_data)
    _atomic_write(LOCAL_CONFIG_PATH, new_config_data)
    print(f"Created step '{step_id}' in local_steps.json and config.json.")
    return 0


def cmd_modify(args):
    step_id = args.id

    # Check for mutually exclusive flags
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

    # Check at least one field flag provided
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
            "Error: at least one field flag is required for modify. "
            "Use --name, --desc, --code, --agent-instructions, "
            "--clear-code, or --clear-agent-instructions.",
            file=sys.stderr,
        )
        return 1

    local_steps = _load_steps(LOCAL_STEPS_PATH)
    idx = _find_step_index(local_steps, step_id)
    if idx < 0:
        print(f"Error: step not found: {step_id}", file=sys.stderr)
        return 1

    step = dict(local_steps[idx])

    if args.name is not None:
        step["friendly_name"] = args.name
    if args.desc is not None:
        step["description"] = args.desc
    if args.clear_code:
        step["code"] = None
    elif args.code is not None:
        step["code"] = args.code
    if args.clear_agent_instructions:
        step["agent_instructions"] = None
    elif args.agent_instructions is not None:
        step["agent_instructions"] = args.agent_instructions

    updated_steps = list(local_steps)
    updated_steps[idx] = step
    new_local_data = {"steps": updated_steps}

    if args.dry_run:
        print("[DRY RUN] local_steps.json would be written as:")
        print(json.dumps(new_local_data, indent=2))
        return 0

    _atomic_write(LOCAL_STEPS_PATH, new_local_data)
    print(f"Updated step '{step_id}' in local_steps.json.")
    return 0


def cmd_delete(args):
    step_id = args.id

    local_steps = _load_steps(LOCAL_STEPS_PATH)
    idx = _find_step_index(local_steps, step_id)
    if idx < 0:
        print(f"Error: step not found: {step_id}", file=sys.stderr)
        return 1

    updated_steps = [s for s in local_steps if s.get("id") != step_id]
    new_local_data = {"steps": updated_steps}

    config_steps = _load_steps(LOCAL_CONFIG_PATH)
    updated_config = [e for e in config_steps if e.get("id") != step_id]
    new_config_data = {"steps": updated_config}

    if args.dry_run:
        print("[DRY RUN] local_steps.json would be written as:")
        print(json.dumps(new_local_data, indent=2))
        print()
        print("[DRY RUN] config.json would be written as:")
        print(json.dumps(new_config_data, indent=2))
        return 0

    _atomic_write(LOCAL_STEPS_PATH, new_local_data)
    _atomic_write(LOCAL_CONFIG_PATH, new_config_data)
    print(f"Deleted step '{step_id}' from local_steps.json and config.json.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Manage local release steps."
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-command")

    # create
    p_create = subparsers.add_parser("create", help="Create a new local step")
    p_create.add_argument("--id", required=True, help="Step ID")
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
    p_modify = subparsers.add_parser("modify", help="Modify an existing local step")
    p_modify.add_argument("id", help="Step ID to modify")
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
    p_delete = subparsers.add_parser("delete", help="Delete a local step")
    p_delete.add_argument("id", help="Step ID to delete")
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
