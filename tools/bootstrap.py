"""Shared bootstrap module for Purlin tools.

Provides canonical implementations of project root detection, config loading,
and atomic file writing. Centralizes patterns previously duplicated across
24+ files in tools/.
"""

import json
import os
import sys
import tempfile

_BOOTSTRAP_DIR = os.path.dirname(os.path.abspath(__file__))
_FRAMEWORK_ROOT = os.path.abspath(os.path.join(_BOOTSTRAP_DIR, '..'))


def detect_project_root(script_dir=None):
    """Detect project root using PURLIN_PROJECT_ROOT or climbing fallback.

    Args:
        script_dir: Directory of the calling script. If None, defaults to
                    the bootstrap module's own directory.

    Returns:
        Absolute path to the project root.
    """
    env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if env_root and os.path.isdir(env_root):
        return os.path.abspath(env_root)

    if script_dir is None:
        script_dir = _BOOTSTRAP_DIR

    script_dir = os.path.abspath(script_dir)

    # Climbing fallback: check both candidate depths for .purlin/ marker.
    # Further path (3 levels up) = consumer project root in submodule layout.
    # Nearer path (2 levels up) = standalone project root.
    further = os.path.abspath(os.path.join(script_dir, '../../..'))
    nearer = os.path.abspath(os.path.join(script_dir, '../..'))

    further_has = os.path.isdir(os.path.join(further, '.purlin'))
    nearer_has = os.path.isdir(os.path.join(nearer, '.purlin'))

    if further_has and nearer_has:
        # Both candidates have .purlin/ — disambiguate via nearer's .git type.
        # If nearer/.git is a directory, nearer is a standalone repo and the
        # further .purlin/ belongs to an unrelated parent project.
        # If nearer/.git is a file (submodule gitlink) or absent, prefer further
        # (the normal submodule case).
        nearer_git = os.path.join(nearer, '.git')
        if os.path.isdir(nearer_git):
            return nearer
        return further
    if further_has:
        return further
    if nearer_has:
        return nearer

    # Last resort: 2 levels up from script_dir (preserving legacy behavior)
    return nearer


def load_config(project_root):
    """Load resolved configuration from the project.

    Delegates to tools/config/resolve_config.py for the actual resolution
    (layered config: config.local.json over config.json).

    Args:
        project_root: Absolute path to the project root.

    Returns:
        Configuration dict, or empty dict on failure.
    """
    try:
        for p in (project_root, _FRAMEWORK_ROOT):
            if p not in sys.path:
                sys.path.insert(0, p)
        from tools.config.resolve_config import resolve_config
        return resolve_config(project_root)
    except Exception:
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
