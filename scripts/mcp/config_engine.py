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
    """Detect project root using PURLIN_PROJECT_ROOT or cwd climbing.

    In the plugin model, PURLIN_PROJECT_ROOT is the primary mechanism.
    Climbing fallback walks up from cwd looking for .purlin/ marker.
    """
    env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if env_root and os.path.isdir(env_root):
        return env_root

    # Climb from cwd looking for .purlin/ marker
    current = os.path.abspath(start_dir or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(current, '.purlin')):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    # Last resort: current working directory
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
    # Purlin agent falls back to builder config during transition
    if role == 'purlin' and not agent:
        agent = agents.get('builder', {})

    bp = 'true' if agent.get('bypass_permissions', False) else 'false'
    fw = 'true' if agent.get('find_work', True) else 'false'
    as_ = 'true' if agent.get('auto_start', False) else 'false'

    print(f'AGENT_BYPASS="{bp}"')
    print(f'AGENT_FIND_WORK="{fw}"')
    print(f'AGENT_AUTO_START="{as_}"')

    # Project name: config key with basename fallback
    project_name = config.get('project_name', '') or os.path.basename(project_root)
    print(f'PROJECT_NAME="{project_name}"')


def _cli_has_agent_config(project_root, role):
    """Print 'true' if agents.<role> exists in resolved config, 'false' otherwise."""
    config = resolve_config(project_root)
    agents = config.get('agents', {})
    agent = agents.get(role, {})
    print('true' if agent else 'false')


def _cli_set_agent_config(project_root, role, key, value):
    """Set agents.<role>.<key> = value in config.local.json.

    Boolean config fields (bypass_permissions, find_work, auto_start) are
    coerced from CLI strings to proper JSON booleans.
    """
    _BOOLEAN_FIELDS = {'bypass_permissions', 'find_work', 'auto_start'}

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

    # Coerce string booleans to proper JSON booleans for known fields
    if key in _BOOLEAN_FIELDS and isinstance(value, str):
        value = value.lower() == 'true'

    agents = config.setdefault('agents', {})
    agent = agents.setdefault(role, {})
    agent[key] = value

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
        print("Usage: resolve_config.py [--dump | --key <name> | <role> | has_agent_config <role> | set_agent_config <role> <key> <value> | acknowledge_warning <model_id>]",
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
    elif arg == 'has_agent_config':
        if len(sys.argv) < 3:
            print("Usage: resolve_config.py has_agent_config <role>",
                  file=sys.stderr)
            sys.exit(1)
        _cli_has_agent_config(project_root, sys.argv[2])
    elif arg == 'set_agent_config':
        if len(sys.argv) < 5:
            print("Usage: resolve_config.py set_agent_config <role> <key> <value>",
                  file=sys.stderr)
            sys.exit(1)
        _cli_set_agent_config(project_root, sys.argv[2], sys.argv[3], sys.argv[4])
    elif arg in ('architect', 'builder', 'qa', 'pm', 'purlin'):
        _cli_role(project_root, arg)
    else:
        print(f"Unknown argument: {arg}", file=sys.stderr)
        print("Usage: resolve_config.py [--dump | --key <name> | <role> | has_agent_config <role> | set_agent_config <role> <key> <value> | acknowledge_warning <model_id>]",
              file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# File classification for mode guard (plugin model)
# ---------------------------------------------------------------------------

# Mode state — persisted to .purlin/runtime/ so hook scripts
# (which run in separate processes) can read it.
# Scoped by agent_id (for parallel subagents) or PURLIN_SESSION_ID
# (for concurrent terminals) to prevent mode file collisions.
# The cache is keyed by scope identifier because the MCP server is a
# single process shared across all agents — a global would be corrupted
# by concurrent subagents overwriting each other's state.
_mode_cache = {}  # {scope_key: mode_string_or_None}


def _mode_scope_key(agent_id=None):
    """Return the scope key for mode file and cache lookups."""
    if agent_id:
        return agent_id
    return os.environ.get('PURLIN_SESSION_ID', '')


def _mode_file_path(agent_id=None):
    """Return path to the mode state file (scoped when possible)."""
    project_root = os.environ.get('PURLIN_PROJECT_ROOT', os.getcwd())
    scope = _mode_scope_key(agent_id)
    if scope:
        return os.path.join(project_root, '.purlin', 'runtime',
                            f'current_mode_{scope}')
    return os.path.join(project_root, '.purlin', 'runtime', 'current_mode')


def _mode_file_path_unscoped():
    """Return path to the unscoped mode state file (fallback)."""
    project_root = os.environ.get('PURLIN_PROJECT_ROOT', os.getcwd())
    return os.path.join(project_root, '.purlin', 'runtime', 'current_mode')


def get_mode(agent_id=None):
    """Return current operating mode or None.

    Args:
        agent_id: Optional agent identifier for subagent-scoped mode lookup.
    """
    scope = _mode_scope_key(agent_id)
    if scope in _mode_cache and _mode_cache[scope] is not None:
        return _mode_cache[scope]
    # Read from persisted state — scoped first, then unscoped fallback.
    # If scoped file EXISTS (even if empty), it is authoritative —
    # do not fall back to unscoped. This ensures plan-exit-mode-clear
    # (which empties the file) isn't bypassed by a stale unscoped file.
    if scope:
        try:
            path = _mode_file_path(agent_id)
            if os.path.isfile(path):
                with open(path, 'r') as f:
                    mode = f.read().strip()
                if mode in ('engineer', 'pm', 'qa'):
                    _mode_cache[scope] = mode
                    return mode
                # File exists but is empty/invalid — mode was cleared
                return None
        except (IOError, OSError):
            pass
    # No scope or no scoped file — try unscoped
    try:
        path = _mode_file_path_unscoped()
        if os.path.isfile(path):
            with open(path, 'r') as f:
                mode = f.read().strip()
            if mode in ('engineer', 'pm', 'qa'):
                _mode_cache[scope] = mode
                return mode
    except (IOError, OSError):
        pass
    return None


def set_mode(mode, agent_id=None):
    """Set current operating mode (engineer, pm, qa, or None).

    Args:
        mode: Mode string or None to clear.
        agent_id: Optional agent identifier for subagent-scoped mode.
    """
    scope = _mode_scope_key(agent_id)
    _mode_cache[scope] = mode
    # Persist to file for cross-process access (hooks)
    try:
        path = _mode_file_path(agent_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(mode or '')
    except (IOError, OSError):
        pass


def classify_file(filepath):
    """Classify a file as CODE, SPEC, QA, or INVARIANT for mode guard.

    IMPORTANT: This function is the permission gate for marketplace plugins.
    Every exit-0 path in mode-guard.sh returns permissionDecision:"allow"
    based on this classification. Be conservative — when in doubt, classify
    as CODE (most restrictive for PM/QA modes).

    Rules are evaluated in order; first match wins.
    """
    path = filepath.replace('\\', '/')

    # --- INVARIANT — no mode can write ---
    if '/features/i_' in path or path.startswith('features/i_'):
        return 'INVARIANT'

    # --- QA-owned ---
    # Discovery sidecars
    if path.endswith('.discoveries.md'):
        return 'QA'
    # Regression test results
    if '/tests/' in path and path.endswith('regression.json'):
        return 'QA'
    # QA scenario files
    if '/tests/qa/scenarios/' in path or path.startswith('tests/qa/scenarios/'):
        return 'QA'

    # --- SPEC (PM-owned) ---
    # Feature specs in features/ (but NOT companion .impl.md files)
    if '/features/' in path or path.startswith('features/'):
        if path.endswith('.impl.md'):
            return 'CODE'  # Companion files are Engineer-owned
        return 'SPEC'
    # Design and policy anchors (can be at any path depth)
    basename = path.rsplit('/', 1)[-1] if '/' in path else path
    if basename.startswith('design_') and basename.endswith('.md'):
        return 'SPEC'
    if basename.startswith('policy_') and basename.endswith('.md'):
        return 'SPEC'

    # --- CODE (Engineer-owned) — explicit patterns for clarity ---
    # Skills, scripts, hooks, agents, references, templates, tests, .purlin config
    for prefix in ('skills/', 'scripts/', 'hooks/', 'agents/', 'references/',
                   'templates/', 'tests/', 'src/', 'lib/', 'app/', 'dev/',
                   '.claude/', '.purlin/', '.claude-plugin/'):
        if path.startswith(prefix) or f'/{prefix}' in path:
            return 'CODE'

    # Config and dotfiles at project root
    if basename in ('package.json', 'tsconfig.json', 'pyproject.toml',
                    'Cargo.toml', 'go.mod', 'Makefile', 'Dockerfile',
                    '.gitignore', '.eslintrc', '.prettierrc', 'CLAUDE.md',
                    'README.md', 'CHANGELOG.md', 'LICENSE'):
        return 'CODE'

    # Default: everything else is CODE (most restrictive for PM/QA)
    return 'CODE'


if __name__ == '__main__':
    main()
