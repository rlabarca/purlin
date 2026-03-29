#!/usr/bin/env python3
"""Credential access for Purlin MCP tools.

Reads credentials exclusively from CLAUDE_PLUGIN_OPTION_* environment variables.
These are injected by Claude Code from the plugin's userConfig (sensitive fields
are stored in the OS keychain; non-sensitive in the plugin data directory).

No credential values are ever written to project files.
"""

import os

# Registry of known credential keys and their metadata.
# Each entry: (env_var_suffix, description, field_title)
_CREDENTIAL_REGISTRY = {
    "figma_access_token": (
        "Figma personal access token for design system integration",
        "Figma Access Token",
    ),
    "deploy_token": (
        "Deployment authentication token",
        "Deploy Token",
    ),
    "confluence_token": (
        "Atlassian Confluence API token",
        "Confluence API Token",
    ),
    "confluence_email": (
        "Atlassian account email for Confluence",
        "Confluence Email",
    ),
    "confluence_base_url": (
        "Confluence instance URL (e.g., https://team.atlassian.net)",
        "Confluence Base URL",
    ),
    "default_model": (
        "Default Claude model for Purlin sessions",
        "Default Model",
    ),
}

_ENV_PREFIX = "CLAUDE_PLUGIN_OPTION_"


def get_credential(key):
    """Read a credential from the CLAUDE_PLUGIN_OPTION_<key> env var.

    Returns the value as a string, or None if not configured.
    """
    return os.environ.get(f"{_ENV_PREFIX}{key}") or None


def require_credential(key, feature_name):
    """Read a credential, raising ValueError if missing.

    The error message includes configuration instructions.
    """
    value = get_credential(key)
    if value is not None:
        return value

    desc, title = _CREDENTIAL_REGISTRY.get(key, (key, key))
    raise ValueError(
        f"Missing credential: {key}\n"
        f"  {desc}\n"
        f"\n"
        f"Required by: {feature_name}\n"
        f"\n"
        f"To configure, set it in your Claude Code plugin settings:\n"
        f"  Claude Code → Settings → Plugins → Purlin → {title}\n"
        f"\n"
        f"Or set the environment variable directly:\n"
        f"  export {_ENV_PREFIX}{key}=\"<value>\""
    )


def credential_status():
    """Return a dict of credential availability for all known keys.

    Returns: {key: {"configured": bool, "description": str, "title": str}}
    Never includes credential values.
    """
    result = {}
    for key, (desc, title) in _CREDENTIAL_REGISTRY.items():
        result[key] = {
            "configured": get_credential(key) is not None,
            "description": desc,
            "title": title,
        }
    return result
