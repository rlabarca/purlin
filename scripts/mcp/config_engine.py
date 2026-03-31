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

    acf = 'true' if agent.get('auto_create_features', False) else 'false'
    print(f'AGENT_AUTO_CREATE="{acf}"')

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
    _BOOLEAN_FIELDS = {'bypass_permissions', 'find_work', 'auto_start', 'auto_create_features'}

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
        print("Usage: config_engine.py [--dump | --key <name> | classify <path> | <role> | ...]",
              file=sys.stderr)
        sys.exit(1)

    arg = sys.argv[1]

    if arg == '--dump':
        _cli_dump(project_root)
    elif arg == '--key':
        if len(sys.argv) < 3:
            print("Usage: config_engine.py --key <name>", file=sys.stderr)
            sys.exit(1)
        _cli_key(project_root, sys.argv[2])
    elif arg == 'classify':
        if len(sys.argv) < 3:
            print("Usage: config_engine.py classify <filepath>", file=sys.stderr)
            sys.exit(1)
        print(classify_file(sys.argv[2]))
    elif arg == 'acknowledge_warning':
        if len(sys.argv) < 3:
            print("Usage: config_engine.py acknowledge_warning <model_id>",
                  file=sys.stderr)
            sys.exit(1)
        _cli_acknowledge_warning(project_root, sys.argv[2])
    elif arg == 'has_agent_config':
        if len(sys.argv) < 3:
            print("Usage: config_engine.py has_agent_config <role>",
                  file=sys.stderr)
            sys.exit(1)
        _cli_has_agent_config(project_root, sys.argv[2])
    elif arg == 'set_agent_config':
        if len(sys.argv) < 5:
            print("Usage: config_engine.py set_agent_config <role> <key> <value>",
                  file=sys.stderr)
            sys.exit(1)
        _cli_set_agent_config(project_root, sys.argv[2], sys.argv[3], sys.argv[4])
    elif arg in ('architect', 'builder', 'qa', 'pm', 'purlin'):
        _cli_role(project_root, arg)
    else:
        print(f"Unknown argument: {arg}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# File classification for write guard
# ---------------------------------------------------------------------------

def _read_claude_md_classifications():
    """Read custom file classifications from the project's CLAUDE.md.

    Looks for a '## Purlin File Classifications' section with lines like:
        - `docs/` → SPEC
        - `config/` → CODE

    Returns a list of (pattern, classification) tuples. INVARIANT assignments
    are ignored (invariants are managed exclusively by purlin:invariant).
    Results are cached for the lifetime of the process.
    """
    if hasattr(_read_claude_md_classifications, '_cache'):
        return _read_claude_md_classifications._cache

    rules = []
    project_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if not project_root:
        _read_claude_md_classifications._cache = rules
        return rules

    claude_md = os.path.join(project_root, 'CLAUDE.md')
    if not os.path.isfile(claude_md):
        _read_claude_md_classifications._cache = rules
        return rules

    try:
        with open(claude_md, 'r') as f:
            content = f.read()
    except (IOError, OSError):
        _read_claude_md_classifications._cache = rules
        return rules

    import re
    # Find the section
    in_section = False
    valid = {'CODE', 'SPEC', 'QA'}
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == '## Purlin File Classifications':
            in_section = True
            continue
        if in_section:
            # Stop at next heading
            if stripped.startswith('## ') or stripped.startswith('# '):
                break
            # Parse: - `pattern` → CLASSIFICATION
            m = re.match(r'^-\s+`([^`]+)`\s*→\s*(\w+)', stripped)
            if m:
                pattern, classification = m.group(1), m.group(2).upper()
                if classification in valid:
                    rules.append((pattern, classification))

    _read_claude_md_classifications._cache = rules
    return rules


def _read_write_exceptions():
    """Read write_exceptions from the project's .purlin/config.json.

    Returns a list of exception patterns. Trailing '/' means directory prefix;
    no trailing '/' means exact filename match at project root.
    """
    project_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if not project_root:
        project_root = _find_project_root()
    config = resolve_config(project_root)
    return config.get('write_exceptions', [])


def classify_file(filepath):
    """Classify a file as CODE, SPEC, QA, INVARIANT, or OTHER for write guard.

    Rules are evaluated in order; first match wins.
    Custom rules from CLAUDE.md are checked before built-in rules.
    OTHER is returned for paths matching write_exceptions in config.
    """
    path = filepath.replace('\\', '/')

    # --- Custom rules from CLAUDE.md (project-specific overrides) ---
    for pattern, classification in _read_claude_md_classifications():
        if path.startswith(pattern):
            return classification

    # --- INVARIANT — always blocked by write guard ---
    if '/features/i_' in path or path.startswith('features/i_'):
        return 'INVARIANT'
    if '/_invariants/' in path or path.startswith('_invariants/'):
        return 'INVARIANT'
    if '/features/_invariants/' in path or path.startswith('features/_invariants/'):
        return 'INVARIANT'

    # --- QA-owned ---
    if path.endswith('.discoveries.md'):
        return 'QA'
    if '/tests/' in path and path.endswith('regression.json'):
        return 'QA'
    if '/tests/qa/scenarios/' in path or path.startswith('tests/qa/scenarios/'):
        return 'QA'

    # --- SPEC ---
    if '/features/' in path or path.startswith('features/'):
        if path.endswith('.impl.md'):
            return 'CODE'  # Companion files are code artifacts
        return 'SPEC'
    basename = path.rsplit('/', 1)[-1] if '/' in path else path
    if basename.startswith('design_') and basename.endswith('.md'):
        return 'SPEC'
    if basename.startswith('policy_') and basename.endswith('.md'):
        return 'SPEC'

    # --- OTHER (write exceptions from config) ---
    for pattern in _read_write_exceptions():
        if pattern.endswith('/'):
            if path.startswith(pattern):
                return 'OTHER'
        elif basename == pattern or path == pattern:
            return 'OTHER'

    # --- CODE — explicit patterns ---
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

    return 'UNKNOWN'


# ---------------------------------------------------------------------------
# Sync state management
# ---------------------------------------------------------------------------

def read_sync_state(project_root=None):
    """Read the ephemeral session sync state (.purlin/runtime/sync_state.json).

    Returns the sync state dict or an empty structure if not found.
    """
    if not project_root:
        project_root = os.environ.get('PURLIN_PROJECT_ROOT', os.getcwd())
    state_file = os.path.join(project_root, '.purlin', 'runtime', 'sync_state.json')
    try:
        with open(state_file) as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError, OSError):
        return {'features': {}, 'unclassified_writes': []}


def read_sync_ledger(project_root=None):
    """Read the committed sync ledger (.purlin/sync_ledger.json).

    Returns the ledger dict or empty dict if not found.
    """
    if not project_root:
        project_root = os.environ.get('PURLIN_PROJECT_ROOT', os.getcwd())
    ledger_file = os.path.join(project_root, '.purlin', 'sync_ledger.json')
    try:
        with open(ledger_file) as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError, OSError):
        return {}


def get_sync_summary(project_root=None):
    """Return per-feature sync status combining ledger + session state.

    For each feature, returns:
      - sync_status: synced, code_ahead, spec_ahead, new, unknown
      - last_code_date, last_spec_date, last_impl_date (from ledger)
      - session overlay: any in-session changes not yet committed

    Returns a dict of {stem: {status info}}.
    """
    if not project_root:
        project_root = os.environ.get('PURLIN_PROJECT_ROOT', os.getcwd())

    ledger = read_sync_ledger(project_root)
    session = read_sync_state(project_root)

    summary = {}

    # Start with ledger entries
    for stem, entry in ledger.items():
        summary[stem] = {
            'sync_status': entry.get('sync_status', 'unknown'),
            'last_code_date': entry.get('last_code_date'),
            'last_spec_date': entry.get('last_spec_date'),
            'last_impl_date': entry.get('last_impl_date'),
            'session_changes': False,
        }

    # Overlay session state (more recent, uncommitted changes)
    for stem, feat in session.get('features', {}).items():
        if stem not in summary:
            summary[stem] = {
                'sync_status': 'unknown',
                'last_code_date': None,
                'last_spec_date': None,
                'last_impl_date': None,
                'session_changes': True,
            }
        else:
            summary[stem]['session_changes'] = True

        has_code = bool(feat.get('code_files') or feat.get('test_files'))
        has_spec = feat.get('spec_changed', False)
        has_impl = feat.get('impl_changed', False)

        # Session changes override ledger status
        if has_code and has_spec:
            summary[stem]['sync_status'] = 'synced'
        elif has_code and has_impl:
            summary[stem]['sync_status'] = 'synced'
        elif has_code:
            summary[stem]['sync_status'] = 'code_ahead'
        elif has_spec and not has_code:
            # Check if code exists in ledger
            if summary[stem].get('last_code_date'):
                summary[stem]['sync_status'] = 'spec_ahead'
            else:
                summary[stem]['sync_status'] = 'new'

    return summary


if __name__ == '__main__':
    main()
