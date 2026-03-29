#!/usr/bin/env python3
"""Agentic Toolbox community tool lifecycle operations.

Implements add, pull, push, and edit helpers for community tools
per features/toolbox_community.md.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'mcp')))
from bootstrap import detect_project_root, load_config, atomic_write as _bootstrap_atomic_write

PROJECT_ROOT = detect_project_root(SCRIPT_DIR)

COMMUNITY_TOOLS_PATH = os.path.join(PROJECT_ROOT, ".purlin", "toolbox", "community_tools.json")
COMMUNITY_DIR = os.path.join(PROJECT_ROOT, ".purlin", "toolbox", "community")
PURLIN_TOOLS_PATH = os.path.join(SCRIPT_DIR, "purlin_tools.json")

# Framework repo detection: project tools live in dev/ (tracked) not .purlin/toolbox/ (gitignored)
_IS_FRAMEWORK_REPO = os.path.abspath(SCRIPT_DIR).startswith(os.path.abspath(PROJECT_ROOT))
if _IS_FRAMEWORK_REPO:
    PROJECT_TOOLS_PATH = os.path.join(PROJECT_ROOT, "dev", "project_tools.json")
else:
    PROJECT_TOOLS_PATH = os.path.join(PROJECT_ROOT, ".purlin", "toolbox", "project_tools.json")

COMMUNITY_PREFIX = "community."


def _load_json_safe(path):
    """Load a JSON file, returning None on any error."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return None


def _load_registry(path):
    """Load a tools registry, returning the tools list."""
    data = _load_json_safe(path)
    if data is None:
        return []
    return data.get("tools", data.get("steps", []))


def _save_registry(path, tools):
    """Write a tools registry atomically."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _bootstrap_atomic_write(path, {"schema_version": "2.0", "tools": tools}, as_json=True)


def _find_entry(tools, tool_id):
    """Find index of tool with given ID, or -1."""
    for i, t in enumerate(tools):
        if t.get("id") == tool_id:
            return i
    return -1


def _normalize_id(tool_id):
    """Ensure community tool ID has the community. prefix."""
    if not tool_id.startswith(COMMUNITY_PREFIX):
        return COMMUNITY_PREFIX + tool_id
    return tool_id


def _git_clone_to_temp(git_url):
    """Clone a git repo to a temporary directory. Returns (tmpdir, error_msg)."""
    tmpdir = tempfile.mkdtemp(prefix="purlin-community-")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", git_url, tmpdir],
            capture_output=True, text=True, check=True, timeout=60
        )
        return tmpdir, None
    except subprocess.CalledProcessError as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None, f"Failed to clone {git_url}: {e.stderr.strip()}"
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None, f"Clone timed out for {git_url}"


def _git_get_head_sha(tmpdir):
    """Get HEAD SHA of a git repo."""
    try:
        result = subprocess.run(
            ["git", "-C", tmpdir, "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def _git_ls_remote_head(git_url):
    """Get remote HEAD SHA without cloning. Returns (sha, error_msg)."""
    try:
        result = subprocess.run(
            ["git", "ls-remote", git_url, "HEAD"],
            capture_output=True, text=True, check=True, timeout=30
        )
        if result.stdout.strip():
            return result.stdout.strip().split()[0], None
        return None, f"No HEAD ref found at {git_url}"
    except subprocess.CalledProcessError as e:
        return None, f"Cannot reach {git_url}: {e.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return None, f"Timed out reaching {git_url}"


def _check_id_collision(tool_id):
    """Check if a tool ID collides with any existing tool. Returns error msg or None."""
    # Check community registry
    community_tools = _load_registry(COMMUNITY_TOOLS_PATH)
    if _find_entry(community_tools, tool_id) >= 0:
        return f"Tool '{tool_id}' already exists in community tools"

    # Check project registry
    project_tools = _load_registry(PROJECT_TOOLS_PATH)
    if _find_entry(project_tools, tool_id) >= 0:
        return f"Tool '{tool_id}' conflicts with project tool '{tool_id}'"

    # Check purlin registry
    purlin_tools = _load_registry(PURLIN_TOOLS_PATH)
    if _find_entry(purlin_tools, tool_id) >= 0:
        return f"Tool '{tool_id}' conflicts with purlin tool '{tool_id}'"

    return None


def cmd_add(git_url, dry_run=False):
    """Add a community tool from a git repository.

    Returns dict with status and details.
    """
    # Step 1: Clone
    tmpdir, err = _git_clone_to_temp(git_url)
    if err:
        return {"status": "error", "message": err}

    try:
        # Step 2: Validate tool.json
        tool_json_path = os.path.join(tmpdir, "tool.json")
        if not os.path.exists(tool_json_path):
            return {"status": "error", "message": (
                f"Repository {git_url} does not contain tool.json at root. "
                "Community tool repos must have a tool.json at the repository root."
            )}

        try:
            with open(tool_json_path, 'r', encoding='utf-8') as f:
                tool_def = json.load(f)
        except json.JSONDecodeError as e:
            return {"status": "error", "message": f"tool.json contains invalid JSON: {e}"}

        # Step 3: Validate required fields
        missing = [f for f in ("id", "friendly_name", "description") if not tool_def.get(f)]
        if missing:
            return {"status": "error", "message": (
                f"tool.json is missing required fields: {', '.join(missing)}"
            )}

        # Step 4: Normalize ID
        original_id = tool_def["id"]
        tool_id = _normalize_id(original_id)
        renamed = tool_id != original_id

        # Step 5: Check for collision
        collision = _check_id_collision(tool_id)
        if collision:
            return {"status": "error", "message": collision}

        # Get HEAD SHA
        head_sha = _git_get_head_sha(tmpdir)

        # Get author
        author = (tool_def.get("metadata") or {}).get("author")
        if not author:
            try:
                result = subprocess.run(
                    ["git", "config", "user.email"],
                    capture_output=True, text=True, check=True
                )
                author = result.stdout.strip()
            except subprocess.CalledProcessError:
                author = "unknown"

        # Get version
        version = tool_def.get("version", "0.0.0")

        if dry_run:
            result = {
                "status": "dry_run",
                "tool_id": tool_id,
                "friendly_name": tool_def["friendly_name"],
                "version": version,
                "source_repo": git_url,
                "author": author,
            }
            if renamed:
                result["renamed_from"] = original_id
            return result

        # Step 6: Create community directory
        tool_dir = os.path.join(COMMUNITY_DIR, tool_id)
        os.makedirs(tool_dir, exist_ok=True)

        # Step 7: Copy files
        for item in os.listdir(tmpdir):
            if item.startswith('.git'):
                continue
            src = os.path.join(tmpdir, item)
            dst = os.path.join(tool_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

        # Update tool.json with normalized ID
        tool_def["id"] = tool_id
        _bootstrap_atomic_write(
            os.path.join(tool_dir, "tool.json"), tool_def, as_json=True
        )

        # Step 8: Register in community_tools.json
        community_tools = _load_registry(COMMUNITY_TOOLS_PATH)
        registry_entry = {
            "id": tool_id,
            "source_dir": f"community/{tool_id}",
            "version": version,
            "source_repo": git_url,
            "author": author,
            "last_pull_sha": head_sha or "unknown",
        }
        community_tools.append(registry_entry)
        _save_registry(COMMUNITY_TOOLS_PATH, community_tools)

        result = {
            "status": "added",
            "tool_id": tool_id,
            "friendly_name": tool_def["friendly_name"],
            "version": version,
            "source_repo": git_url,
            "message": f"Added community tool '{tool_id}' from {git_url}. Version: {version}.",
        }
        if renamed:
            result["renamed_from"] = original_id
            result["message"] = (
                f"ID renamed from '{original_id}' to '{tool_id}'. " + result["message"]
            )
        return result

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def cmd_pull(tool_id=None, dry_run=False):
    """Update community tool(s) from source repos.

    If tool_id is None, update all community tools.
    Returns dict with summary.
    """
    community_tools = _load_registry(COMMUNITY_TOOLS_PATH)

    if tool_id is not None:
        targets = [t for t in community_tools if t.get("id") == tool_id]
        if not targets:
            return {"status": "error", "message": f"Community tool '{tool_id}' not found."}
    else:
        if not community_tools:
            return {"status": "empty", "message": "No community tools installed."}
        targets = community_tools

    updated = []
    up_to_date = []
    conflicts = []
    errors = []

    for entry in targets:
        tid = entry.get("id", "unknown")
        source_repo = entry.get("source_repo")
        last_sha = entry.get("last_pull_sha")

        if not source_repo:
            errors.append({"id": tid, "message": "No source_repo configured"})
            continue

        # Check remote HEAD
        remote_sha, err = _git_ls_remote_head(source_repo)
        if err:
            errors.append({"id": tid, "message": err})
            continue

        if remote_sha == last_sha:
            up_to_date.append(tid)
            continue

        # Clone to get new content
        tmpdir, clone_err = _git_clone_to_temp(source_repo)
        if clone_err:
            errors.append({"id": tid, "message": clone_err})
            continue

        try:
            new_tool_json_path = os.path.join(tmpdir, "tool.json")
            if not os.path.exists(new_tool_json_path):
                errors.append({"id": tid, "message": "Remote repo no longer has tool.json"})
                continue

            # Check for local edits
            local_tool_dir = os.path.join(COMMUNITY_DIR, tid)
            local_tool_json = os.path.join(local_tool_dir, "tool.json")

            has_local_edits = False
            if os.path.exists(local_tool_json) and last_sha:
                # Compare local content against what we pulled last time
                # Simple approach: compare current local with new upstream
                # If local differs from upstream, it could be local edits OR upstream changes
                # We detect local edits by checking if local differs from what we last pulled
                try:
                    with open(local_tool_json, 'r') as f:
                        local_content = f.read()
                    # Get content at last_pull_sha from remote
                    orig_result = subprocess.run(
                        ["git", "-C", tmpdir, "show", f"{last_sha}:tool.json"],
                        capture_output=True, text=True, timeout=10
                    )
                    if orig_result.returncode == 0:
                        original_content = orig_result.stdout
                        has_local_edits = local_content.strip() != original_content.strip()
                except (IOError, subprocess.SubprocessError):
                    pass

            if has_local_edits:
                conflicts.append({
                    "id": tid,
                    "source_repo": source_repo,
                    "local_path": local_tool_json,
                    "remote_sha": remote_sha,
                })
                continue

            if dry_run:
                updated.append({"id": tid, "from_sha": last_sha, "to_sha": remote_sha})
                continue

            # Auto-update: copy new files
            if os.path.exists(local_tool_dir):
                # Remove old content (except .git stuff)
                for item in os.listdir(local_tool_dir):
                    path = os.path.join(local_tool_dir, item)
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.unlink(path)

            os.makedirs(local_tool_dir, exist_ok=True)
            for item in os.listdir(tmpdir):
                if item.startswith('.git'):
                    continue
                src = os.path.join(tmpdir, item)
                dst = os.path.join(local_tool_dir, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)

            # Update registry entry
            entry["last_pull_sha"] = remote_sha
            with open(new_tool_json_path, 'r') as f:
                new_def = json.load(f)
            if new_def.get("version"):
                entry["version"] = new_def["version"]

            updated.append({"id": tid, "from_sha": last_sha, "to_sha": remote_sha})

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    # Save updated registry
    if updated and not dry_run:
        _save_registry(COMMUNITY_TOOLS_PATH, community_tools)

    return {
        "status": "complete",
        "updated": updated,
        "up_to_date": up_to_date,
        "conflicts": conflicts,
        "errors": errors,
        "message": (
            f"Updated {len(updated)} tools. "
            f"Skipped {len(up_to_date)} (up to date). "
            f"Conflicts: {len(conflicts)}."
        ),
    }


def cmd_push(tool_id, git_url=None, version=None, dry_run=False):
    """Push a tool to a git repository.

    Returns dict with status and details.
    """
    # Check purlin tools first
    purlin_tools = _load_registry(PURLIN_TOOLS_PATH)
    if _find_entry(purlin_tools, tool_id) >= 0:
        return {"status": "error", "message": (
            "Purlin tools cannot be pushed. Use 'purlin:toolbox copy' first "
            "to create a project tool, then push that."
        )}

    # Check community tools
    community_tools = _load_registry(COMMUNITY_TOOLS_PATH)
    comm_idx = _find_entry(community_tools, tool_id)

    # Check project tools
    project_tools = _load_registry(PROJECT_TOOLS_PATH)
    proj_idx = _find_entry(project_tools, tool_id)

    if comm_idx >= 0:
        # Community tool: update existing repo
        entry = community_tools[comm_idx]
        target_url = git_url or entry.get("source_repo")
        if not target_url:
            return {"status": "error", "message": (
                f"Community tool '{tool_id}' has no source_repo and no git-url provided."
            )}

        tool_dir = os.path.join(COMMUNITY_DIR, tool_id)
        tool_json_path = os.path.join(tool_dir, "tool.json")
        if not os.path.exists(tool_json_path):
            return {"status": "error", "message": f"tool.json not found at {tool_json_path}"}

        with open(tool_json_path, 'r') as f:
            tool_def = json.load(f)

        push_version = version or tool_def.get("version", "0.0.0")

        if dry_run:
            return {
                "status": "dry_run",
                "action": "update",
                "tool_id": tool_id,
                "target_url": target_url,
                "version": push_version,
            }

        # Clone existing, update, push
        tmpdir, err = _git_clone_to_temp(target_url)
        if err:
            return {"status": "error", "message": err}

        try:
            # Copy tool files to repo
            for item in os.listdir(tool_dir):
                src = os.path.join(tool_dir, item)
                dst = os.path.join(tmpdir, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)

            # Update version in tool.json
            tool_def["version"] = push_version
            tool_def.setdefault("metadata", {})["last_updated"] = date.today().isoformat()
            _bootstrap_atomic_write(os.path.join(tmpdir, "tool.json"), tool_def, as_json=True)

            # Commit and push
            subprocess.run(["git", "-C", tmpdir, "add", "-A"], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", tmpdir, "commit", "-m",
                 f"Update {tool_id} to v{push_version}"],
                check=True, capture_output=True
            )
            push_result = subprocess.run(
                ["git", "-C", tmpdir, "push"],
                capture_output=True, text=True, timeout=30
            )
            if push_result.returncode != 0:
                return {"status": "error", "message": f"Push failed: {push_result.stderr.strip()}"}

            head_sha = _git_get_head_sha(tmpdir)

            # Update registry
            entry["last_pull_sha"] = head_sha
            entry["version"] = push_version
            if git_url:
                entry["source_repo"] = git_url
            _save_registry(COMMUNITY_TOOLS_PATH, community_tools)

            # Also update local tool.json
            _bootstrap_atomic_write(
                os.path.join(tool_dir, "tool.json"), tool_def, as_json=True
            )

            return {
                "status": "pushed",
                "tool_id": tool_id,
                "version": push_version,
                "target_url": target_url,
                "message": f"Pushed '{tool_id}' to {target_url}. Version: {push_version}.",
            }
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    elif proj_idx >= 0:
        # Project tool: promote to community
        if not git_url:
            return {"status": "error", "message": (
                f"This is a project tool with no source repo. "
                f"Specify a git URL: 'purlin:toolbox push {tool_id} <git-url>'"
            )}

        tool_def = dict(project_tools[proj_idx])
        push_version = version or "1.0.0"

        # Get author
        author = (tool_def.get("metadata") or {}).get("author")
        if not author:
            try:
                result = subprocess.run(
                    ["git", "config", "user.email"],
                    capture_output=True, text=True, check=True
                )
                author = result.stdout.strip()
            except subprocess.CalledProcessError:
                author = "unknown"

        # Compute new community ID
        new_id = _normalize_id(tool_id.replace("community.", ""))

        if dry_run:
            return {
                "status": "dry_run",
                "action": "promote",
                "tool_id": tool_id,
                "new_id": new_id,
                "target_url": git_url,
                "version": push_version,
                "author": author,
            }

        # Create temp repo, add tool.json, push
        tmpdir = tempfile.mkdtemp(prefix="purlin-push-")
        try:
            subprocess.run(["git", "init", tmpdir], capture_output=True, check=True)

            # Prepare tool definition with community metadata
            tool_def["id"] = new_id
            tool_def["version"] = push_version
            tool_def.setdefault("metadata", {})
            tool_def["metadata"]["author"] = author
            tool_def["metadata"]["source_repo"] = git_url
            tool_def["metadata"]["last_updated"] = date.today().isoformat()

            _bootstrap_atomic_write(
                os.path.join(tmpdir, "tool.json"), tool_def, as_json=True
            )

            # Auto-generate README if not present
            readme_path = os.path.join(tmpdir, "README.md")
            with open(readme_path, 'w') as f:
                f.write(f"# {tool_def.get('friendly_name', new_id)}\n\n")
                f.write(f"{tool_def.get('description', '')}\n\n")
                f.write(f"Version: {push_version}\n")
                f.write(f"Author: {author}\n")

            subprocess.run(["git", "-C", tmpdir, "add", "-A"], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", tmpdir, "commit", "-m", f"Initial release v{push_version}"],
                check=True, capture_output=True
            )
            subprocess.run(
                ["git", "-C", tmpdir, "remote", "add", "origin", git_url],
                check=True, capture_output=True
            )
            push_result = subprocess.run(
                ["git", "-C", tmpdir, "push", "-u", "origin", "HEAD"],
                capture_output=True, text=True, timeout=30
            )
            if push_result.returncode != 0:
                return {"status": "error", "message": f"Push failed: {push_result.stderr.strip()}"}

            head_sha = _git_get_head_sha(tmpdir)

            # Remove from project tools
            project_tools = [t for t in project_tools if t.get("id") != tool_id]
            _save_registry(PROJECT_TOOLS_PATH, project_tools)

            # Add to community tools
            tool_dir = os.path.join(COMMUNITY_DIR, new_id)
            os.makedirs(tool_dir, exist_ok=True)
            _bootstrap_atomic_write(
                os.path.join(tool_dir, "tool.json"), tool_def, as_json=True
            )
            if os.path.exists(readme_path):
                shutil.copy2(readme_path, os.path.join(tool_dir, "README.md"))

            community_tools = _load_registry(COMMUNITY_TOOLS_PATH)
            community_tools.append({
                "id": new_id,
                "source_dir": f"community/{new_id}",
                "version": push_version,
                "source_repo": git_url,
                "author": author,
                "last_pull_sha": head_sha or "unknown",
            })
            _save_registry(COMMUNITY_TOOLS_PATH, community_tools)

            return {
                "status": "promoted",
                "old_id": tool_id,
                "new_id": new_id,
                "version": push_version,
                "target_url": git_url,
                "message": (
                    f"Pushed '{tool_id}' to {git_url} as '{new_id}'. "
                    f"Version: {push_version}. "
                    f"Removed from project_tools.json, added to community_tools.json."
                ),
            }
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    else:
        return {"status": "error", "message": f"Tool '{tool_id}' not found in any registry."}


def main():
    parser = argparse.ArgumentParser(
        description="Community tool lifecycle operations."
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-command")

    # add
    p_add = subparsers.add_parser("add", help="Add a community tool from a git repo")
    p_add.add_argument("git_url", help="Git repository URL")
    p_add.add_argument("--dry-run", action="store_true")

    # pull
    p_pull = subparsers.add_parser("pull", help="Update community tool(s)")
    p_pull.add_argument("tool_id", nargs="?", default=None, help="Tool ID (omit for all)")
    p_pull.add_argument("--dry-run", action="store_true")

    # push
    p_push = subparsers.add_parser("push", help="Push a tool to a git repo")
    p_push.add_argument("tool_id", help="Tool ID")
    p_push.add_argument("git_url", nargs="?", default=None, help="Git URL (required for project tools)")
    p_push.add_argument("--version", default=None, help="Version string")
    p_push.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    if args.command == "add":
        result = cmd_add(args.git_url, dry_run=args.dry_run)
    elif args.command == "pull":
        result = cmd_pull(args.tool_id, dry_run=args.dry_run)
    elif args.command == "push":
        result = cmd_push(args.tool_id, args.git_url, args.version, dry_run=args.dry_run)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") not in ("error",) else 1)


if __name__ == "__main__":
    main()
