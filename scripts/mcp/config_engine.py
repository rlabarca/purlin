#!/usr/bin/env python3
"""Config resolver for Purlin projects.

Two-file config with merge semantics:
  - .purlin/config.json       — team defaults, committed to git
  - .purlin/config.local.json — per-user overrides, gitignored

Resolution: config.json is the base. config.local.json keys are merged on
top — local values win for any key present in both files. Keys only in
config.json are always visible. Keys only in config.local.json are user
additions (rare, but allowed).

update_config writes ONLY to config.local.json. It never modifies
config.json — that file is owned by purlin:init and version control.
"""

import json
import os
import sys


def find_project_root(start_dir=None):
    """Detect project root using PURLIN_PROJECT_ROOT or cwd climbing.

    In the plugin model, PURLIN_PROJECT_ROOT is the primary mechanism.
    Climbing fallback walks up from start_dir looking for .purlin/ marker.
    Falls back to cwd if no marker found.
    """
    env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if env_root and os.path.isdir(env_root):
        return env_root

    current = os.path.abspath(start_dir or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(current, '.purlin')):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return os.path.abspath(os.getcwd())


def _read_json(path):
    """Read a JSON file, returning its contents or None on any error."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return None
    except (json.JSONDecodeError, IOError, OSError):
        return None


def resolve_config(project_root):
    """Resolve and return the merged config as a dict.

    Resolution:
    1. Read config.json (team defaults).
    2. Read config.local.json (per-user overrides).
    3. Merge: start with config.json, overlay config.local.json on top.
    4. If config.local.json is malformed, ignore it and warn to stderr.
    5. If neither file exists, return {}.
    """
    purlin_dir = os.path.join(project_root, '.purlin')
    shared_path = os.path.join(purlin_dir, 'config.json')
    local_path = os.path.join(purlin_dir, 'config.local.json')

    # Base layer: team defaults
    base = _read_json(shared_path) or {}

    # Override layer: per-user overrides
    if os.path.isfile(local_path):
        local = _read_json(local_path)
        if local is None:
            print("Warning: config.local.json is malformed; ignoring overrides",
                  file=sys.stderr)
            return base
        # Merge: local wins
        merged = dict(base)
        merged.update(local)
        return merged

    return base


def update_config(project_root, key, value):
    """Set a top-level key in config.local.json (per-user overrides).

    Only writes to the local file. Preserves existing local overrides.
    Never modifies config.json.
    """
    purlin_dir = os.path.join(project_root, '.purlin')
    local_path = os.path.join(purlin_dir, 'config.local.json')

    # Read existing local overrides (sparse — may have few or no keys)
    local = {}
    if os.path.isfile(local_path):
        try:
            with open(local_path, 'r') as f:
                data = json.load(f)
            if isinstance(data, dict):
                local = data
        except (json.JSONDecodeError, IOError, OSError):
            pass

    local[key] = value

    os.makedirs(purlin_dir, exist_ok=True)
    tmp_path = local_path + '.tmp'
    try:
        with open(tmp_path, 'w') as f:
            json.dump(local, f, indent=4)
            f.write('\n')
        os.replace(tmp_path, local_path)
    except (IOError, OSError):
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def main():
    project_root = find_project_root()

    if len(sys.argv) < 2:
        print("Usage: config_engine.py [--dump | --key <name>]", file=sys.stderr)
        sys.exit(1)

    arg = sys.argv[1]

    if arg == '--dump':
        config = resolve_config(project_root)
        print(json.dumps(config, indent=4))
    elif arg == '--key':
        if len(sys.argv) < 3:
            print("Usage: config_engine.py --key <name>", file=sys.stderr)
            sys.exit(1)
        config = resolve_config(project_root)
        value = config.get(sys.argv[2])
        if value is None:
            print('')
        elif isinstance(value, (dict, list)):
            print(json.dumps(value))
        elif isinstance(value, bool):
            print('true' if value else 'false')
        else:
            print(value)
    else:
        print(f"Unknown argument: {arg}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
