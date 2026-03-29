"""Agentic Toolbox resolution module.

Implements the three-source resolution algorithm from
features/toolbox_core.md Section 2.5.
"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'mcp')))
from bootstrap import detect_project_root, load_config

PROJECT_ROOT = detect_project_root(SCRIPT_DIR)
CONFIG = load_config(PROJECT_ROOT)

PURLIN_TOOLS_PATH = os.path.join(SCRIPT_DIR, "purlin_tools.json")

# Framework repo detection: if purlin_tools.json lives directly under
# PROJECT_ROOT/scripts/toolbox/, we're developing Purlin itself.
# Project tools go to dev/ (tracked in git) instead of .purlin/toolbox/ (gitignored).
_IS_FRAMEWORK_REPO = os.path.abspath(SCRIPT_DIR).startswith(os.path.abspath(PROJECT_ROOT))
if _IS_FRAMEWORK_REPO:
    PROJECT_TOOLS_PATH = os.path.join(PROJECT_ROOT, "dev", "project_tools.json")
else:
    PROJECT_TOOLS_PATH = os.path.join(PROJECT_ROOT, ".purlin", "toolbox", "project_tools.json")

COMMUNITY_TOOLS_PATH = os.path.join(PROJECT_ROOT, ".purlin", "toolbox", "community_tools.json")
COMMUNITY_DIR = os.path.join(PROJECT_ROOT, ".purlin", "toolbox", "community")

RESERVED_PREFIXES = ("purlin.", "community.")


def _load_json_safe(path):
    """Load a JSON file, returning None on any error."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return None


def _load_json_strict(path):
    """Load a JSON file, raising on invalid JSON (hard error per spec)."""
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _extract_tools(data):
    """Extract tools array from registry data, handling old and new formats."""
    if data is None:
        return []
    # New format: "tools" key with schema_version
    if "tools" in data:
        return data["tools"]
    # Old format: "steps" key without schema_version
    if "steps" in data:
        return data["steps"]
    return []


def _make_resolved_entry(tool_def, category, warnings=None):
    """Build a resolved tool entry from a tool definition.

    Args:
        tool_def: Tool definition dict from a registry file.
        category: One of "purlin", "project", "community".
        warnings: Optional list to append warning strings to when
                  unrecognized fields are encountered.
    """
    entry = {
        "id": tool_def.get("id", ""),
        "friendly_name": tool_def.get("friendly_name", ""),
        "description": tool_def.get("description", ""),
        "code": tool_def.get("code"),
        "agent_instructions": tool_def.get("agent_instructions"),
        "version": tool_def.get("version"),
        "metadata": tool_def.get("metadata"),
        "category": category,
    }
    # Preserve any unrecognized fields and emit warnings
    known_keys = {"id", "friendly_name", "description", "code",
                  "agent_instructions", "version", "metadata"}
    for key, value in tool_def.items():
        if key not in known_keys:
            entry[key] = value
            if warnings is not None:
                warnings.append(
                    f"Tool '{tool_def.get('id', 'unknown')}' has unrecognized field '{key}' (preserved)"
                )
    return entry


def load_purlin_tools(path=None):
    """Load tool definitions from the purlin tools registry."""
    target = path or PURLIN_TOOLS_PATH
    data = _load_json_strict(target)
    return _extract_tools(data)


def load_project_tools(path=None):
    """Load tool definitions from the project tools registry.

    Validates that project tool IDs do not use reserved prefixes.
    Returns (valid_tools, errors).
    """
    target = path or PROJECT_TOOLS_PATH
    data = _load_json_safe(target)
    tools = _extract_tools(data)

    valid = []
    errors = []
    for tool in tools:
        tool_id = tool.get("id", "")
        for prefix in RESERVED_PREFIXES:
            if tool_id.startswith(prefix):
                errors.append(
                    f"Project tool '{tool_id}' uses the reserved '{prefix}' prefix"
                )
                break
        else:
            valid.append(tool)
    return valid, errors


def load_community_tools(index_path=None, community_dir=None):
    """Load community tool definitions from the index and per-tool directories.

    Returns (tools, warnings) where tools is a list of full tool definitions
    and warnings is a list of warning strings.
    """
    idx_path = index_path or COMMUNITY_TOOLS_PATH
    com_dir = community_dir or COMMUNITY_DIR
    data = _load_json_safe(idx_path)
    entries = _extract_tools(data)

    tools = []
    warnings = []
    for entry in entries:
        tool_id = entry.get("id", "")
        source_dir = entry.get("source_dir", "")
        tool_json_path = os.path.join(
            os.path.dirname(idx_path), source_dir, "tool.json"
        ) if source_dir else os.path.join(com_dir, tool_id, "tool.json")

        tool_data = _load_json_safe(tool_json_path)
        if tool_data is None:
            warnings.append(
                f"Community tool '{tool_id}': tool.json not found at {tool_json_path}"
            )
            continue

        # Merge index metadata into tool definition
        tool_data.setdefault("id", tool_id)
        if entry.get("version"):
            tool_data["version"] = entry["version"]
        if entry.get("source_repo") or entry.get("author"):
            meta = tool_data.setdefault("metadata", {})
            if entry.get("source_repo"):
                meta["source_repo"] = entry["source_repo"]
            if entry.get("author"):
                meta["author"] = entry["author"]
        tools.append(tool_data)

    return tools, warnings


def resolve_toolbox(purlin_path=None, project_path=None,
                    community_index_path=None, community_dir=None):
    """Resolve the full toolbox from all three sources.

    Returns:
        (resolved_tools, warnings, errors)
        - resolved_tools: list of dicts with tool fields + 'category'
        - warnings: list of warning strings
        - errors: list of error strings
    """
    warnings = []
    errors = []

    # Step 1: Load purlin tools
    try:
        purlin_tools = load_purlin_tools(purlin_path)
    except (json.JSONDecodeError, IOError, OSError) as e:
        errors.append(f"Error: {purlin_path or PURLIN_TOOLS_PATH} contains invalid JSON: {e}")
        return [], warnings, errors

    # Step 2: Load project tools
    project_tools, project_errors = load_project_tools(project_path)
    errors.extend(project_errors)

    # Step 3: Load community tools
    community_tools, community_warnings = load_community_tools(
        community_index_path, community_dir
    )
    warnings.extend(community_warnings)

    # Step 4: Build merged registry
    resolved = []
    seen_ids = set()

    for tool in purlin_tools:
        tool_id = tool.get("id", "")
        if tool_id:
            resolved.append(_make_resolved_entry(tool, "purlin", warnings))
            seen_ids.add(tool_id)

    for tool in project_tools:
        tool_id = tool.get("id", "")
        if tool_id:
            if tool_id in seen_ids:
                # Exact ID collision between project and another source
                warnings.append(
                    f"Project tool '{tool_id}' shadows an existing tool"
                )
            resolved.append(_make_resolved_entry(tool, "project", warnings))
            seen_ids.add(tool_id)

    for tool in community_tools:
        tool_id = tool.get("id", "")
        if tool_id:
            if tool_id in seen_ids:
                errors.append(
                    f"Community tool '{tool_id}' conflicts with an existing tool ID"
                )
                continue
            resolved.append(_make_resolved_entry(tool, "community", warnings))
            seen_ids.add(tool_id)

    return resolved, warnings, errors


def fuzzy_match(query, resolved_tools):
    """Find tools matching a query string.

    Returns list of matching tool entries. Exact ID match always wins.
    Falls back to case-insensitive substring match on ID and friendly_name.
    """
    query_lower = query.lower()

    # Exact ID match
    for tool in resolved_tools:
        if tool["id"] == query:
            return [tool]

    # Substring match on ID and friendly_name
    matches = []
    for tool in resolved_tools:
        if (query_lower in tool["id"].lower() or
                query_lower in tool.get("friendly_name", "").lower()):
            matches.append(tool)
    return matches


if __name__ == "__main__":
    resolved, warnings, errors = resolve_toolbox()
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    print(json.dumps({"tools": resolved}, indent=2))
