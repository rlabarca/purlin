#!/usr/bin/env python3
"""Purlin version detector.

Examines a consumer project and produces a structured fingerprint
identifying the installation model, version era, and migration state.

Usage:
    python3 version_detector.py --project-root <path>
    Output: JSON fingerprint to stdout.
"""
import json
import os
import subprocess
import sys


def _read_json(path):
    """Read a JSON file, returning None on any error."""
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (IOError, OSError, json.JSONDecodeError):
        return None


def _settings_has_purlin_plugin(project_root):
    """Check if .claude/settings.json declares Purlin as an enabled plugin."""
    settings = _read_json(os.path.join(project_root, '.claude', 'settings.json'))
    if not settings:
        return False
    enabled = settings.get('enabledPlugins', {})
    for key in enabled:
        if 'purlin' in key.lower():
            return True
    return False


def _gitmodules_has_purlin(project_root):
    """Check if .gitmodules contains a purlin submodule entry. Returns submodule path or None."""
    gitmodules_path = os.path.join(project_root, '.gitmodules')
    if not os.path.isfile(gitmodules_path):
        return None
    try:
        with open(gitmodules_path, encoding='utf-8') as f:
            content = f.read()
    except (IOError, OSError):
        return None

    # Parse .gitmodules for a purlin entry
    current_path = None
    is_purlin = False
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('[submodule'):
            # Save previous match
            if is_purlin and current_path:
                return current_path
            current_path = None
            is_purlin = 'purlin' in line.lower()
        elif '=' in line:
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip()
            if key == 'path':
                current_path = value

    if is_purlin and current_path:
        return current_path
    return None


def _detect_submodule_era(config):
    """Determine the version era from consumer config structure."""
    if not config or not isinstance(config, dict):
        return 'unknown', None

    agents = config.get('agents', {})

    # Check for agents.purlin
    purlin_agent = agents.get('purlin')
    if purlin_agent and isinstance(purlin_agent, dict):
        # Check if it's a partial migration (only model+effort, builder still present)
        purlin_keys = set(purlin_agent.keys())
        has_builder = 'builder' in agents
        minimal_keys = purlin_keys <= {'model', 'effort', 'bypass_permissions'}
        if has_builder and minimal_keys and 'find_work' not in purlin_agent:
            return 'unified-partial', 'v0.8.4'
        return 'unified', 'v0.8.5'

    # Check for agents.pm (v0.8.4)
    if 'pm' in agents:
        return 'pre-unified-with-pm', 'v0.8.4'

    # Check agents.architect for era signals
    architect = agents.get('architect', {})
    if isinstance(architect, dict):
        if 'startup_sequence' in architect:
            return 'pre-unified-legacy', 'v0.7.x'
        if 'find_work' in architect:
            return 'pre-unified-modern', 'v0.8.0-v0.8.3'

    # Has agents but no recognizable structure
    if agents:
        return 'unknown', None

    return 'unknown', None


def detect_version(project_root):
    """Detect the Purlin installation model and version era.

    Returns a fingerprint dict:
    {
        "model": "submodule" | "plugin" | "fresh" | "none",
        "era": str | None,
        "version_hint": str | None,
        "migration_version": int | None,
        "submodule_path": str | None
    }
    """
    project_root = os.path.abspath(project_root)

    # Read migration_version from config.json ONLY (not config.local.json).
    # _migration_version is project-level state that must be committed and
    # survive git resets. config.local.json is gitignored and would retain
    # stale values after a reset.
    config_json = _read_json(
        os.path.join(project_root, '.purlin', 'config.json')
    ) or {}
    migration_version = config_json.get('_migration_version')

    # Priority 1: Plugin model
    if _settings_has_purlin_plugin(project_root):
        return {
            'model': 'plugin',
            'era': 'plugin',
            'version_hint': 'v0.9.x',
            'migration_version': migration_version,
            'submodule_path': None,
        }

    # Priority 2: Submodule model
    submodule_path = _gitmodules_has_purlin(project_root)
    if submodule_path:
        # Read config for era detection (local overrides OK here, just not for migration_version)
        config = _read_json(
            os.path.join(project_root, '.purlin', 'config.local.json')
        ) or config_json
        era, version_hint = _detect_submodule_era(config)

        return {
            'model': 'submodule',
            'era': era,
            'version_hint': version_hint,
            'migration_version': migration_version,
            'submodule_path': submodule_path,
        }

    # Priority 3: Fresh project (has .purlin/ but no submodule or plugin)
    if os.path.isdir(os.path.join(project_root, '.purlin')):
        return {
            'model': 'fresh',
            'era': None,
            'version_hint': None,
            'migration_version': migration_version,
            'submodule_path': None,
        }

    # Priority 4: Not a Purlin project
    return {
        'model': 'none',
        'era': None,
        'version_hint': None,
        'migration_version': None,
        'submodule_path': None,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Detect Purlin installation model and version era.')
    parser.add_argument('--project-root', required=True,
                        help='Path to the consumer project root')
    args = parser.parse_args()

    fingerprint = detect_version(args.project_root)
    print(json.dumps(fingerprint, indent=2))


if __name__ == '__main__':
    main()
