#!/usr/bin/env python3
"""Config resolver for Purlin projects.

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


def _find_project_root(start_dir=None):
    """Detect project root using PURLIN_PROJECT_ROOT or climbing fallback.

    Uses PURLIN_PROJECT_ROOT env var if set, otherwise climbs from start_dir
    (defaulting to this script's location) looking for .purlin/ directory.
    Submodule-aware: tries further path first (3 levels up), then nearer
    (2 levels up).
    """
    env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if env_root and os.path.isdir(env_root):
        return env_root

    if start_dir is None:
        start_dir = os.path.dirname(os.path.abspath(__file__))

    # Climbing fallback: try submodule path (further) first, then standalone (nearer)
    for depth in ('../../../', '../../'):
        candidate = os.path.abspath(os.path.join(start_dir, depth))
        if os.path.exists(os.path.join(candidate, '.purlin')):
            return candidate

    # Last resort: 2 levels up from script
    return os.path.abspath(os.path.join(start_dir, '../../'))


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

    # Try local config first
    if os.path.exists(local_path):
        try:
            with open(local_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            print("Warning: config.local.json is malformed; falling back to config.json",
                  file=sys.stderr)
            # Fall through to shared config

    # No valid local config -- try shared
    if os.path.exists(shared_path):
        try:
            with open(shared_path, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            return {}

        # Copy-on-first-access: create local from shared
        if not os.path.exists(local_path):
            try:
                os.makedirs(purlin_dir, exist_ok=True)
                shutil.copy2(shared_path, local_path)
            except (IOError, OSError):
                pass  # Non-fatal: we still return the config

        return config

    # Neither file exists
    return {}


def sync_config(project_root):
    """Sync new keys from shared config into local config.

    Recursively walks config.json (shared) and finds any keys missing from
    config.local.json (local). Adds missing keys with shared defaults. Existing
    local values are never overwritten.

    Returns a list of added key paths (dot-notation).
    If local doesn't exist, creates it as a full copy and returns all key paths.
    """
    purlin_dir = os.path.join(project_root, '.purlin')
    local_path = os.path.join(purlin_dir, 'config.local.json')
    shared_path = os.path.join(purlin_dir, 'config.json')

    # Read shared config
    if not os.path.exists(shared_path):
        return []

    try:
        with open(shared_path, 'r') as f:
            shared = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return []

    # If local doesn't exist, create as full copy
    if not os.path.exists(local_path):
        try:
            os.makedirs(purlin_dir, exist_ok=True)
            shutil.copy2(shared_path, local_path)
        except (IOError, OSError):
            return []
        return _collect_all_keys(shared)

    # Read local config
    try:
        with open(local_path, 'r') as f:
            local = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        # Malformed local -- recreate from shared
        try:
            shutil.copy2(shared_path, local_path)
        except (IOError, OSError):
            pass
        return _collect_all_keys(shared)

    # Walk shared and add missing keys to local
    added = []
    _sync_recursive(shared, local, '', added)

    if added:
        # Write updated local config atomically
        tmp_path = local_path + '.tmp'
        try:
            with open(tmp_path, 'w') as f:
                json.dump(local, f, indent=4)
            os.replace(tmp_path, local_path)
        except (IOError, OSError):
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    return added


def _sync_recursive(shared, local, prefix, added):
    """Recursively add keys from shared that are missing in local.

    For array values containing objects with an 'id' field, performs id-based
    merging: entries from shared whose id does not appear in local are appended.
    Existing local entries (matched by id) are never modified or removed.
    """
    for key, value in shared.items():
        full_key = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        if key not in local:
            local[key] = value
            if isinstance(value, dict):
                added.extend(_collect_all_keys(value, full_key))
            else:
                added.append(full_key)
        elif isinstance(value, dict) and isinstance(local[key], dict):
            _sync_recursive(value, local[key], full_key, added)
        elif isinstance(value, list) and isinstance(local[key], list):
            _sync_array(value, local[key], full_key, added)


def _sync_array(shared_arr, local_arr, full_key, added):
    """Id-based merge for arrays of objects with an 'id' field.

    Entries from shared whose id is not present in local are appended to local.
    Existing local entries are never modified or removed.
    Non-id arrays are skipped (no merging).
    """
    # Only merge if both arrays contain dicts with 'id' fields
    if not shared_arr or not isinstance(shared_arr[0], dict) or 'id' not in shared_arr[0]:
        return
    if local_arr and (not isinstance(local_arr[0], dict) or 'id' not in local_arr[0]):
        return

    local_ids = {item['id'] for item in local_arr if isinstance(item, dict) and 'id' in item}
    for item in shared_arr:
        if isinstance(item, dict) and 'id' in item and item['id'] not in local_ids:
            local_arr.append(item)
            added.append(f"{full_key}[id={item['id']}]")


def _collect_all_keys(d, prefix=''):
    """Collect all leaf key paths from a dict in dot-notation."""
    keys = []
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.extend(_collect_all_keys(value, full_key))
        else:
            keys.append(full_key)
    return keys


def _cli_dump(project_root):
    """Print full resolved config as JSON to stdout."""
    config = resolve_config(project_root)
    print(json.dumps(config, indent=4))


def _cli_key(project_root, key_name):
    """Print value of a single top-level key to stdout."""
    config = resolve_config(project_root)
    value = config.get(key_name)
    if value is None:
        print('')
    elif isinstance(value, (dict, list)):
        print(json.dumps(value))
    elif isinstance(value, bool):
        print('true' if value else 'false')
    else:
        print(value)


def _cli_role(project_root, role):
    """Print shell variable assignments for agent settings."""
    config = resolve_config(project_root)
    agents = config.get('agents', {})
    agent = agents.get(role, {})

    model = agent.get('model', '')
    effort = agent.get('effort', '')
    bp = 'true' if agent.get('bypass_permissions', False) else 'false'
    fw = 'true' if agent.get('find_work', True) else 'false'
    as_ = 'true' if agent.get('auto_start', False) else 'false'

    # Look up model warning from the models array
    warning = ''
    warning_dismissible = False
    for m in config.get('models', []):
        if m.get('id') == model:
            warning = m.get('warning', '')
            warning_dismissible = bool(m.get('warning_dismissible', False))
            break

    # Check if warning has been acknowledged
    acknowledged = config.get('acknowledged_warnings', [])
    dismissed = 'false'
    if warning and warning_dismissible and model in acknowledged:
        dismissed = 'true'

    print(f'AGENT_MODEL="{model}"')
    print(f'AGENT_EFFORT="{effort}"')
    print(f'AGENT_BYPASS="{bp}"')
    print(f'AGENT_FIND_WORK="{fw}"')
    print(f'AGENT_AUTO_START="{as_}"')
    print(f'AGENT_MODEL_WARNING="{warning}"')
    print(f'AGENT_MODEL_WARNING_DISMISSED="{dismissed}"')


def _cli_acknowledge_warning(project_root, model_id):
    """Add a model ID to acknowledged_warnings in config.local.json."""
    purlin_dir = os.path.join(project_root, '.purlin')
    local_path = os.path.join(purlin_dir, 'config.local.json')

    # Read existing local config (or start fresh)
    config = {}
    if os.path.exists(local_path):
        try:
            with open(local_path, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            config = {}

    acknowledged = config.get('acknowledged_warnings', [])
    if model_id not in acknowledged:
        acknowledged.append(model_id)
        config['acknowledged_warnings'] = acknowledged

        # Write atomically
        os.makedirs(purlin_dir, exist_ok=True)
        tmp_path = local_path + '.tmp'
        try:
            with open(tmp_path, 'w') as f:
                json.dump(config, f, indent=4)
            os.replace(tmp_path, local_path)
        except (IOError, OSError):
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


def main():
    project_root = _find_project_root()

    if len(sys.argv) < 2:
        print("Usage: resolve_config.py [--dump | --key <name> | <role> | acknowledge_warning <model_id>]",
              file=sys.stderr)
        sys.exit(1)

    arg = sys.argv[1]

    if arg == '--dump':
        _cli_dump(project_root)
    elif arg == '--key':
        if len(sys.argv) < 3:
            print("Usage: resolve_config.py --key <name>", file=sys.stderr)
            sys.exit(1)
        _cli_key(project_root, sys.argv[2])
    elif arg == 'acknowledge_warning':
        if len(sys.argv) < 3:
            print("Usage: resolve_config.py acknowledge_warning <model_id>",
                  file=sys.stderr)
            sys.exit(1)
        _cli_acknowledge_warning(project_root, sys.argv[2])
    elif arg in ('architect', 'builder', 'qa', 'pm'):
        _cli_role(project_root, arg)
    else:
        print(f"Unknown argument: {arg}", file=sys.stderr)
        print("Usage: resolve_config.py [--dump | --key <name> | <role> | acknowledge_warning <model_id>]",
              file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
