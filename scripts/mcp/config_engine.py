#!/usr/bin/env python3
"""Config resolver for Purlin v2 projects.

Centralizes all config access through a two-file resolution system:
  - .purlin/config.local.json (gitignored, per-user preferences)
  - .purlin/config.json (committed, team defaults/template)

Resolution rule: read config.local.json if it exists, otherwise fall back
to config.json. No merging at read time.

Copy-on-first-access: when config.local.json doesn't exist but config.json
does, copy config.json to config.local.json automatically.
"""

import json
import os
import shutil
import sys


def find_project_root(start_dir=None):
    """Detect project root using PURLIN_PROJECT_ROOT or cwd climbing.

    In the plugin model, PURLIN_PROJECT_ROOT is the primary mechanism.
    Climbing fallback walks up from cwd looking for .purlin/ marker.
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


def resolve_config(project_root):
    """Resolve and return the active config as a dict.

    Resolution order:
    1. If config.local.json exists and contains valid JSON, return its contents.
    2. If config.local.json doesn't exist but config.json does, copy config.json
       to config.local.json (copy-on-first-access) and return its contents.
    3. If config.local.json exists but contains invalid JSON, fall back to
       config.json (log warning to stderr).
    4. If neither exists, return an empty dict.
    """
    purlin_dir = os.path.join(project_root, '.purlin')
    local_path = os.path.join(purlin_dir, 'config.local.json')
    shared_path = os.path.join(purlin_dir, 'config.json')

    if os.path.exists(local_path):
        try:
            with open(local_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            print("Warning: config.local.json is malformed; falling back to config.json",
                  file=sys.stderr)

    if os.path.exists(shared_path):
        try:
            with open(shared_path, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            return {}

        if not os.path.exists(local_path):
            try:
                os.makedirs(purlin_dir, exist_ok=True)
                shutil.copy2(shared_path, local_path)
            except (IOError, OSError):
                pass

        return config

    return {}


def update_config(project_root, key, value):
    """Set a top-level key in config.local.json."""
    purlin_dir = os.path.join(project_root, '.purlin')
    local_path = os.path.join(purlin_dir, 'config.local.json')

    config = {}
    if os.path.exists(local_path):
        try:
            with open(local_path, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            config = {}

    config[key] = value

    os.makedirs(purlin_dir, exist_ok=True)
    tmp_path = local_path + '.tmp'
    try:
        with open(tmp_path, 'w') as f:
            json.dump(config, f, indent=4)
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
