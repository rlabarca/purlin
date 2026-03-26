#!/usr/bin/env python3
"""Migrate release steps configuration to Agentic Toolbox format.

Converts .purlin/release/ files to .purlin/toolbox/ files.
See features/toolbox_migration.md for the full specification.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../')))
from tools.bootstrap import detect_project_root, atomic_write


def _load_json_safe(path):
    """Load a JSON file, returning None on any error."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError) as e:
        print(f"Warning: could not parse {path}: {e}", file=sys.stderr)
        return None


def _sha256(content):
    """Return SHA-256 hex digest of a string or None."""
    if content is None:
        return None
    if isinstance(content, dict) or isinstance(content, list):
        content = json.dumps(content, sort_keys=True)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def _read_file_content(path):
    """Read raw file content for checksum, or None if absent."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except (IOError, OSError):
        return None


def migrate(project_root, dry_run=False):
    """Run the release-to-toolbox migration.

    Returns a dict with:
        status: "nothing_to_migrate" | "already_migrated" | "migrated"
        tools_migrated: int (count of tools migrated)
        message: str
    """
    release_dir = os.path.join(project_root, ".purlin", "release")
    toolbox_dir = os.path.join(project_root, ".purlin", "toolbox")
    marker_path = os.path.join(toolbox_dir, ".migrated_from_release")

    release_config = os.path.join(release_dir, "config.json")
    release_local = os.path.join(release_dir, "local_steps.json")

    # Detection
    has_release = os.path.exists(release_config) or os.path.exists(release_local)
    has_marker = os.path.exists(marker_path)

    if not has_release:
        return {
            "status": "nothing_to_migrate",
            "tools_migrated": 0,
            "message": "No .purlin/release/ directory found. Nothing to migrate.",
        }

    if has_marker:
        return {
            "status": "already_migrated",
            "tools_migrated": 0,
            "message": "Migration marker exists. Already migrated.",
        }

    # Read source files
    local_steps_data = _load_json_safe(release_local)
    local_steps_raw = _read_file_content(release_local)

    # Transform local steps to project tools
    source_steps = []
    if local_steps_data is not None:
        source_steps = local_steps_data.get("steps", [])

    project_tools = []
    today = date.today().isoformat()
    for step in source_steps:
        tool = {
            "id": step.get("id", ""),
            "friendly_name": step.get("friendly_name", ""),
            "description": step.get("description", ""),
            "code": step.get("code"),
            "agent_instructions": step.get("agent_instructions"),
            "tags": ["release"],
            "metadata": {
                "last_updated": today,
            },
        }
        project_tools.append(tool)

    project_tools_data = {"schema_version": "2.0", "tools": project_tools}
    community_tools_data = {"schema_version": "2.0", "tools": []}
    marker_data = {
        "migrated_at": datetime.now(timezone.utc).isoformat(),
        "source_local_steps_checksum": _sha256(local_steps_raw),
        "tools_migrated": len(project_tools),
    }

    if dry_run:
        print("[DRY RUN] Would create .purlin/toolbox/ directory structure")
        print(f"[DRY RUN] Would write project_tools.json with {len(project_tools)} tools:")
        print(json.dumps(project_tools_data, indent=2))
        print()
        print("[DRY RUN] Would write empty community_tools.json")
        print("[DRY RUN] Would write migration marker")
        return {
            "status": "migrated",
            "tools_migrated": len(project_tools),
            "message": f"[DRY RUN] Would migrate {len(project_tools)} tools.",
        }

    # Create directory structure
    os.makedirs(os.path.join(toolbox_dir, "community"), exist_ok=True)

    # Write transformed files
    atomic_write(
        os.path.join(toolbox_dir, "project_tools.json"),
        project_tools_data,
        as_json=True,
    )
    atomic_write(
        os.path.join(toolbox_dir, "community_tools.json"),
        community_tools_data,
        as_json=True,
    )

    # Write marker last (atomicity — absence means incomplete migration)
    atomic_write(marker_path, marker_data, as_json=True)

    return {
        "status": "migrated",
        "tools_migrated": len(project_tools),
        "message": f"Migrated {len(project_tools)} tools from release steps to Agentic Toolbox.",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Migrate release steps to Agentic Toolbox."
    )
    parser.add_argument(
        "--project-root", required=True, help="Project root directory"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would change without writing"
    )
    args = parser.parse_args()

    result = migrate(args.project_root, dry_run=args.dry_run)
    print(result["message"])
    if result["status"] == "migrated" and not args.dry_run:
        print(f"Tools migrated: {result['tools_migrated']}")
    sys.exit(0)


if __name__ == "__main__":
    main()
