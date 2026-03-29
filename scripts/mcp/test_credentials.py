"""Unit tests for the credential storage module.

Tests the credentials.py module and the purlin_credentials MCP tool handler.
Covers all scenarios from features/purlin_credential_storage.md Section 3.
"""
import json
import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from credentials import (
    get_credential,
    require_credential,
    credential_status,
    _CREDENTIAL_REGISTRY,
    _ENV_PREFIX,
)


class TestGetCredential(unittest.TestCase):
    """Tests for get_credential()."""

    def test_returns_value_when_env_var_set(self):
        os.environ[f"{_ENV_PREFIX}figma_access_token"] = "test-token"
        try:
            self.assertEqual(get_credential("figma_access_token"), "test-token")
        finally:
            del os.environ[f"{_ENV_PREFIX}figma_access_token"]

    def test_returns_none_when_env_var_missing(self):
        os.environ.pop(f"{_ENV_PREFIX}deploy_token", None)
        self.assertIsNone(get_credential("deploy_token"))

    def test_returns_none_for_empty_string(self):
        os.environ[f"{_ENV_PREFIX}deploy_token"] = ""
        try:
            self.assertIsNone(get_credential("deploy_token"))
        finally:
            del os.environ[f"{_ENV_PREFIX}deploy_token"]

    def test_returns_none_for_unknown_key(self):
        self.assertIsNone(get_credential("nonexistent_key"))

    def test_reads_correct_env_var_prefix(self):
        os.environ["CLAUDE_PLUGIN_OPTION_my_token"] = "val"
        try:
            self.assertEqual(get_credential("my_token"), "val")
        finally:
            del os.environ["CLAUDE_PLUGIN_OPTION_my_token"]


class TestRequireCredential(unittest.TestCase):
    """Tests for require_credential()."""

    def test_returns_value_when_configured(self):
        os.environ[f"{_ENV_PREFIX}figma_access_token"] = "test-token"
        try:
            result = require_credential("figma_access_token", "Figma ingest")
            self.assertEqual(result, "test-token")
        finally:
            del os.environ[f"{_ENV_PREFIX}figma_access_token"]

    def test_raises_valueerror_when_missing(self):
        os.environ.pop(f"{_ENV_PREFIX}confluence_token", None)
        with self.assertRaises(ValueError) as ctx:
            require_credential("confluence_token", "Confluence sync")

        msg = str(ctx.exception)
        self.assertIn("confluence_token", msg)
        self.assertIn("Confluence sync", msg)

    def test_error_includes_env_var_name(self):
        os.environ.pop(f"{_ENV_PREFIX}confluence_token", None)
        with self.assertRaises(ValueError) as ctx:
            require_credential("confluence_token", "Confluence sync")

        msg = str(ctx.exception)
        self.assertIn(f"{_ENV_PREFIX}confluence_token", msg)

    def test_error_includes_plugin_settings_path(self):
        os.environ.pop(f"{_ENV_PREFIX}deploy_token", None)
        with self.assertRaises(ValueError) as ctx:
            require_credential("deploy_token", "Deploy")

        msg = str(ctx.exception)
        self.assertIn("Claude Code", msg)
        self.assertIn("Plugins", msg)
        self.assertIn("Purlin", msg)

    def test_error_includes_field_title(self):
        os.environ.pop(f"{_ENV_PREFIX}deploy_token", None)
        with self.assertRaises(ValueError) as ctx:
            require_credential("deploy_token", "Deploy")

        msg = str(ctx.exception)
        self.assertIn("Deploy Token", msg)

    def test_unknown_key_still_raises(self):
        with self.assertRaises(ValueError) as ctx:
            require_credential("unknown_key", "Some feature")
        self.assertIn("unknown_key", str(ctx.exception))


class TestCredentialStatus(unittest.TestCase):
    """Tests for credential_status()."""

    def test_returns_all_known_keys(self):
        status = credential_status()
        self.assertEqual(set(status.keys()), set(_CREDENTIAL_REGISTRY.keys()))

    def test_each_entry_has_required_fields(self):
        status = credential_status()
        for key, entry in status.items():
            self.assertIn("configured", entry, f"{key} missing 'configured'")
            self.assertIn("description", entry, f"{key} missing 'description'")
            self.assertIn("title", entry, f"{key} missing 'title'")

    def test_reflects_env_var_state(self):
        os.environ[f"{_ENV_PREFIX}figma_access_token"] = "token"
        os.environ.pop(f"{_ENV_PREFIX}deploy_token", None)
        try:
            status = credential_status()
            self.assertTrue(status["figma_access_token"]["configured"])
            self.assertFalse(status["deploy_token"]["configured"])
        finally:
            del os.environ[f"{_ENV_PREFIX}figma_access_token"]

    def test_no_credential_values_in_output(self):
        os.environ[f"{_ENV_PREFIX}figma_access_token"] = "secret-token-abc"
        try:
            status = credential_status()
            serialized = json.dumps(status)
            self.assertNotIn("secret-token-abc", serialized)
        finally:
            del os.environ[f"{_ENV_PREFIX}figma_access_token"]

    def test_configured_count_matches_set_env_vars(self):
        # Clear all credential env vars
        for key in _CREDENTIAL_REGISTRY:
            os.environ.pop(f"{_ENV_PREFIX}{key}", None)

        # Set exactly two
        os.environ[f"{_ENV_PREFIX}figma_access_token"] = "a"
        os.environ[f"{_ENV_PREFIX}deploy_token"] = "b"
        try:
            status = credential_status()
            configured = sum(1 for v in status.values() if v["configured"])
            self.assertEqual(configured, 2)
        finally:
            del os.environ[f"{_ENV_PREFIX}figma_access_token"]
            del os.environ[f"{_ENV_PREFIX}deploy_token"]


class TestRegistryMatchesPluginJson(unittest.TestCase):
    """Verify credential registry stays in sync with plugin.json userConfig."""

    def test_registry_keys_match_plugin_json(self):
        plugin_json_path = os.path.join(
            SCRIPT_DIR, "..", "..", ".claude-plugin", "plugin.json"
        )
        if not os.path.isfile(plugin_json_path):
            self.skipTest("plugin.json not found at expected path")

        with open(plugin_json_path) as f:
            plugin = json.load(f)

        user_config_keys = set(plugin.get("userConfig", {}).keys())
        registry_keys = set(_CREDENTIAL_REGISTRY.keys())

        self.assertEqual(
            user_config_keys,
            registry_keys,
            f"Mismatch — in plugin.json only: {user_config_keys - registry_keys}, "
            f"in registry only: {registry_keys - user_config_keys}",
        )


class TestMcpToolHandler(unittest.TestCase):
    """Tests for the purlin_credentials MCP tool handler."""

    def setUp(self):
        # Import here to avoid circular import issues during collection
        from purlin_server import handle_purlin_credentials
        self.handler = handle_purlin_credentials

    def test_status_action_returns_all_keys(self):
        result = self.handler({"action": "status"})
        self.assertEqual(set(result.keys()), set(_CREDENTIAL_REGISTRY.keys()))

    def test_status_is_default_action(self):
        result = self.handler({})
        self.assertEqual(set(result.keys()), set(_CREDENTIAL_REGISTRY.keys()))

    def test_check_action_missing_key_returns_error(self):
        result = self.handler({"action": "check"})
        self.assertIn("error", result)
        self.assertIn("key is required", result["error"])

    def test_check_action_unknown_key_returns_error(self):
        result = self.handler({"action": "check", "key": "nonexistent"})
        self.assertIn("error", result)
        self.assertIn("Unknown credential key", result["error"])

    def test_check_action_unconfigured_includes_hint(self):
        os.environ.pop(f"{_ENV_PREFIX}deploy_token", None)
        result = self.handler({"action": "check", "key": "deploy_token"})
        self.assertFalse(result["configured"])
        self.assertIn("hint", result)
        self.assertIn("CLAUDE_PLUGIN_OPTION_deploy_token", result["hint"])

    def test_check_action_configured_no_hint(self):
        os.environ[f"{_ENV_PREFIX}deploy_token"] = "tok"
        try:
            result = self.handler({"action": "check", "key": "deploy_token"})
            self.assertTrue(result["configured"])
            self.assertNotIn("hint", result)
        finally:
            del os.environ[f"{_ENV_PREFIX}deploy_token"]

    def test_status_never_contains_values(self):
        os.environ[f"{_ENV_PREFIX}figma_access_token"] = "super-secret-123"
        try:
            result = self.handler({"action": "status"})
            serialized = json.dumps(result)
            self.assertNotIn("super-secret-123", serialized)
        finally:
            del os.environ[f"{_ENV_PREFIX}figma_access_token"]

    def test_check_never_contains_values(self):
        os.environ[f"{_ENV_PREFIX}figma_access_token"] = "super-secret-123"
        try:
            result = self.handler(
                {"action": "check", "key": "figma_access_token"}
            )
            serialized = json.dumps(result)
            self.assertNotIn("super-secret-123", serialized)
        finally:
            del os.environ[f"{_ENV_PREFIX}figma_access_token"]


class TestPluginJsonSensitiveFlags(unittest.TestCase):
    """Verify sensitive fields are correctly marked in plugin.json."""

    EXPECTED_SENSITIVE = {"figma_access_token", "deploy_token", "confluence_token"}
    EXPECTED_NON_SENSITIVE = {"confluence_email", "confluence_base_url", "default_model"}

    def test_sensitive_flags(self):
        plugin_json_path = os.path.join(
            SCRIPT_DIR, "..", "..", ".claude-plugin", "plugin.json"
        )
        if not os.path.isfile(plugin_json_path):
            self.skipTest("plugin.json not found")

        with open(plugin_json_path) as f:
            plugin = json.load(f)
        user_config = plugin.get("userConfig", {})

        for key in self.EXPECTED_SENSITIVE:
            self.assertTrue(
                user_config[key].get("sensitive", False),
                f"{key} should be marked sensitive",
            )

        for key in self.EXPECTED_NON_SENSITIVE:
            self.assertFalse(
                user_config[key].get("sensitive", False),
                f"{key} should NOT be marked sensitive",
            )


if __name__ == "__main__":
    unittest.main()
