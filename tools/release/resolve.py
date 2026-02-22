"""Release checklist resolution module.

Implements the auto-discovery and resolution algorithm from
features/release_checklist_core.md Section 2.5.
"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Project root detection (Section 2.11 of submodule_bootstrap.md)
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
CONFIG_PATH = os.path.join(PROJECT_ROOT, ".purlin/config.json")
CONFIG = {}
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r') as f:
            CONFIG = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        pass

TOOLS_ROOT = CONFIG.get("tools_root", "tools")

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


def load_global_steps(path=None):
    """Load step definitions from global_steps.json."""
    data = _load_json_safe(path or GLOBAL_STEPS_PATH)
    if data is None:
        return []
    return data.get("steps", [])


def load_local_steps(path=None):
    """Load step definitions from local_steps.json.

    Validates that local step IDs do not use the reserved 'purlin.' prefix.
    Returns (valid_steps, errors) where errors is a list of error messages.
    """
    data = _load_json_safe(path or LOCAL_STEPS_PATH)
    if data is None:
        return [], []

    steps = data.get("steps", [])
    valid = []
    errors = []
    for step in steps:
        step_id = step.get("id", "")
        if step_id.startswith(RESERVED_PREFIX):
            errors.append(
                f"Local step '{step_id}' uses the reserved '{RESERVED_PREFIX}' prefix"
            )
        else:
            valid.append(step)
    return valid, errors


def load_config(path=None):
    """Load the ordered config from config.json."""
    data = _load_json_safe(path or LOCAL_CONFIG_PATH)
    if data is None:
        return None
    return data.get("steps", None)


def resolve_checklist(global_path=None, local_path=None, config_path=None):
    """Resolve the full ordered release checklist.

    Implements the algorithm from release_checklist_core.md Section 2.5.

    Returns:
        (resolved_steps, warnings, errors)
        - resolved_steps: list of dicts with step fields + 'source', 'enabled', 'order'
        - warnings: list of warning strings (orphaned config entries)
        - errors: list of error strings (reserved prefix violations)
    """
    # Step 1-2: Load definitions
    global_steps = load_global_steps(global_path)
    local_steps, errors = load_local_steps(local_path)

    # Step 3: Build merged registry
    registry = {}
    source_map = {}
    for step in global_steps:
        sid = step.get("id", "")
        if sid:
            registry[sid] = step
            source_map[sid] = "global"
    for step in local_steps:
        sid = step.get("id", "")
        if sid:
            registry[sid] = step
            source_map[sid] = "local"

    # Step 4: Load config
    config_entries = load_config(config_path)

    warnings = []
    resolved = []

    if config_entries is not None:
        # Step 5-7: Process config entries
        seen_ids = set()
        for entry in config_entries:
            sid = entry.get("id", "")
            enabled = entry.get("enabled", True)

            if sid in seen_ids:
                continue
            seen_ids.add(sid)

            if sid not in registry:
                # Step 7: Orphaned entry
                warnings.append(f"Unknown step ID '{sid}' in config; skipping")
                continue

            step_def = registry[sid]
            resolved.append({
                "id": sid,
                "friendly_name": step_def.get("friendly_name", ""),
                "description": step_def.get("description", ""),
                "code": step_def.get("code"),
                "agent_instructions": step_def.get("agent_instructions"),
                "source": source_map[sid],
                "enabled": enabled,
            })

        # Step 6: Auto-discover new steps not in config
        for step in global_steps:
            sid = step.get("id", "")
            if sid and sid not in seen_ids:
                resolved.append({
                    "id": sid,
                    "friendly_name": step.get("friendly_name", ""),
                    "description": step.get("description", ""),
                    "code": step.get("code"),
                    "agent_instructions": step.get("agent_instructions"),
                    "source": "global",
                    "enabled": True,
                })
        for step in local_steps:
            sid = step.get("id", "")
            if sid and sid not in seen_ids:
                resolved.append({
                    "id": sid,
                    "friendly_name": step.get("friendly_name", ""),
                    "description": step.get("description", ""),
                    "code": step.get("code"),
                    "agent_instructions": step.get("agent_instructions"),
                    "source": "local",
                    "enabled": True,
                })
    else:
        # No config: all steps enabled in declaration order (global first, then local)
        for step in global_steps:
            sid = step.get("id", "")
            if sid:
                resolved.append({
                    "id": sid,
                    "friendly_name": step.get("friendly_name", ""),
                    "description": step.get("description", ""),
                    "code": step.get("code"),
                    "agent_instructions": step.get("agent_instructions"),
                    "source": "global",
                    "enabled": True,
                })
        for step in local_steps:
            sid = step.get("id", "")
            if sid:
                resolved.append({
                    "id": sid,
                    "friendly_name": step.get("friendly_name", ""),
                    "description": step.get("description", ""),
                    "code": step.get("code"),
                    "agent_instructions": step.get("agent_instructions"),
                    "source": "local",
                    "enabled": True,
                })

    # Add 1-based order
    for i, step in enumerate(resolved):
        step["order"] = i + 1

    return resolved, warnings, errors


if __name__ == "__main__":
    resolved, warnings, errors = resolve_checklist()
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    print(json.dumps({"steps": resolved}, indent=2))
