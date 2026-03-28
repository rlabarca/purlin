"""Shared bootstrap module for Purlin tools (plugin model).

Provides canonical implementations of project root detection, config loading,
and atomic file writing. Simplified from the submodule version — no climbing
fallback needed since the plugin provides ${CLAUDE_PLUGIN_ROOT} directly.
"""

import json
import os
import sys
import tempfile

_BOOTSTRAP_DIR = os.path.dirname(os.path.abspath(__file__))


def detect_project_root(script_dir=None):
    """Detect project root using PURLIN_PROJECT_ROOT or CLAUDE_PLUGIN_ROOT.

    In the plugin model, the project root is the working directory where
    the plugin is active. PURLIN_PROJECT_ROOT is set by the MCP server
    or by the agent's environment.

    Args:
        script_dir: Directory of the calling script. Unused in plugin model
                    but preserved for API compatibility.

    Returns:
        Absolute path to the project root.
    """
    # Primary: explicit env var
    env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if env_root and os.path.isdir(env_root):
        return os.path.abspath(env_root)

    # Fallback: walk up from cwd looking for .purlin/ marker
    cwd = os.getcwd()
    current = os.path.abspath(cwd)
    while True:
        if os.path.isdir(os.path.join(current, '.purlin')):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    # Last resort: current working directory
    return os.path.abspath(cwd)


def load_config(project_root):
    """Load resolved configuration from the project.

    Reads .purlin/config.local.json (if exists) or .purlin/config.json.
    Local file wins entirely — no merging.

    Args:
        project_root: Absolute path to the project root.

    Returns:
        Configuration dict, or empty dict on failure.
    """
    try:
        config_dir = os.path.join(project_root, '.purlin')
        local_path = os.path.join(config_dir, 'config.local.json')
        default_path = os.path.join(config_dir, 'config.json')

        config_path = local_path if os.path.isfile(local_path) else default_path
        if os.path.isfile(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        pass
    return {}


def atomic_write(path, data, as_json=False):
    """Write data to path atomically via temp file + os.replace.

    Args:
        path: Target file path.
        data: String data (when as_json=False) or serializable object
              (when as_json=True).
        as_json: If True, serialize data with json.dump(indent=2) and
                 trailing newline.

    Raises:
        The original exception on write failure (temp file is cleaned up).
    """
    abs_path = os.path.abspath(path)
    parent = os.path.dirname(abs_path)
    os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            if as_json:
                json.dump(data, f, indent=2)
                f.write('\n')
            else:
                f.write(data)
        os.replace(tmp_path, abs_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
