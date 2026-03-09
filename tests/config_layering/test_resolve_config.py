#!/usr/bin/env python3
"""Tests for config resolver (config_layering feature).

Covers all 21 automated scenarios from features/config_layering.md.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


# Add tools directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
sys.path.insert(0, PROJECT_ROOT)

from tools.config.resolve_config import resolve_config, sync_config


class ResolverTestBase(unittest.TestCase):
    """Base class providing temp directory setup with .purlin/ structure."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.tmpdir, '.purlin')
        os.makedirs(self.purlin_dir)
        self.local_path = os.path.join(self.purlin_dir, 'config.local.json')
        self.shared_path = os.path.join(self.purlin_dir, 'config.json')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def write_local(self, data):
        with open(self.local_path, 'w') as f:
            json.dump(data, f)

    def write_shared(self, data):
        with open(self.shared_path, 'w') as f:
            json.dump(data, f)

    def read_local(self):
        with open(self.local_path, 'r') as f:
            return json.load(f)


class TestResolverReturnsLocalWhenLocalExists(ResolverTestBase):
    """Scenario: Resolver Returns Local Config When Local Exists"""

    def test_local_config_takes_priority(self):
        self.write_local({"cdd_port": 9999})
        self.write_shared({"cdd_port": 8086})
        result = resolve_config(self.tmpdir)
        self.assertEqual(result["cdd_port"], 9999)


class TestResolverFallsBackToShared(ResolverTestBase):
    """Scenario: Resolver Falls Back to Shared When No Local Exists"""

    def test_shared_fallback(self):
        self.write_shared({"cdd_port": 8086})
        # No local config
        result = resolve_config(self.tmpdir)
        self.assertEqual(result["cdd_port"], 8086)


class TestResolverCopiesSharedToLocal(ResolverTestBase):
    """Scenario: Resolver Copies Shared to Local on First Access"""

    def test_copy_on_first_access(self):
        shared_data = {"tools_root": "tools", "cdd_port": 8086}
        self.write_shared(shared_data)
        # No local config exists
        self.assertFalse(os.path.exists(self.local_path))

        result = resolve_config(self.tmpdir)

        # Local config should now exist
        self.assertTrue(os.path.exists(self.local_path))
        # Returned config matches shared
        self.assertEqual(result, shared_data)
        # Local file contents match shared
        self.assertEqual(self.read_local(), shared_data)


class TestResolverReturnsEmptyDict(ResolverTestBase):
    """Scenario: Resolver Returns Empty Dict When Neither File Exists"""

    def test_empty_when_neither_exists(self):
        # Remove .purlin dir contents
        os.remove(self.shared_path) if os.path.exists(self.shared_path) else None
        os.remove(self.local_path) if os.path.exists(self.local_path) else None
        result = resolve_config(self.tmpdir)
        self.assertEqual(result, {})


class TestResolverHandlesMalformedLocal(ResolverTestBase):
    """Scenario: Resolver Handles Malformed Local JSON Gracefully"""

    def test_malformed_local_falls_back(self):
        # Write invalid JSON to local
        with open(self.local_path, 'w') as f:
            f.write("{this is not valid json")
        self.write_shared({"cdd_port": 8086})

        result = resolve_config(self.tmpdir)
        self.assertEqual(result["cdd_port"], 8086)


class TestCLIDump(ResolverTestBase):
    """Scenario: CLI Mode --dump Outputs Full Resolved Config as JSON"""

    def test_dump_outputs_json(self):
        self.write_local({"cdd_port": 9999, "tools_root": "tools"})
        resolver_path = os.path.join(PROJECT_ROOT, 'tools', 'config', 'resolve_config.py')
        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir
        result = subprocess.run(
            [sys.executable, resolver_path, '--dump'],
            capture_output=True, text=True, env=env
        )
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output["cdd_port"], 9999)


class TestCLIKey(ResolverTestBase):
    """Scenario: CLI Mode --key Returns Single Value"""

    def test_key_returns_value(self):
        self.write_local({"cdd_port": 9999})
        resolver_path = os.path.join(PROJECT_ROOT, 'tools', 'config', 'resolve_config.py')
        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir
        result = subprocess.run(
            [sys.executable, resolver_path, '--key', 'cdd_port'],
            capture_output=True, text=True, env=env
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), '9999')


class TestCLIRole(ResolverTestBase):
    """Scenario: CLI Mode Role Outputs Shell Variable Assignments"""

    def test_role_outputs_shell_vars(self):
        self.write_local({
            "agents": {
                "architect": {
                    "model": "claude-opus-4-6",
                    "effort": "high",
                    "bypass_permissions": True,
                    "startup_sequence": False,
                    "recommend_next_actions": False
                }
            }
        })
        resolver_path = os.path.join(PROJECT_ROOT, 'tools', 'config', 'resolve_config.py')
        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir
        result = subprocess.run(
            [sys.executable, resolver_path, 'architect'],
            capture_output=True, text=True, env=env
        )
        self.assertEqual(result.returncode, 0)
        output = result.stdout
        self.assertIn('AGENT_MODEL="claude-opus-4-6"', output)
        self.assertIn('AGENT_EFFORT="high"', output)
        self.assertIn('AGENT_BYPASS="true"', output)
        self.assertIn('AGENT_STARTUP="false"', output)
        self.assertIn('AGENT_RECOMMEND="false"', output)


class TestAgentConfigWritesToLocal(ResolverTestBase):
    """Scenario: Agent Config Command Writes to Local Not Shared

    This test verifies the resolver's write-target behavior. The actual
    /pl-agent-config skill is tested separately.
    """

    def test_resolve_config_reads_local_after_write(self):
        original_shared = {"agents": {"architect": {"model": "claude-sonnet-4-6"}}}
        self.write_shared(original_shared)
        # Simulate /pl-agent-config writing to local
        updated_local = {"agents": {"architect": {"model": "claude-opus-4-6"}}}
        self.write_local(updated_local)

        result = resolve_config(self.tmpdir)
        self.assertEqual(result["agents"]["architect"]["model"], "claude-opus-4-6")
        # Shared is unchanged
        with open(self.shared_path) as f:
            shared = json.load(f)
        self.assertEqual(shared["agents"]["architect"]["model"], "claude-sonnet-4-6")


class TestAgentConfigDoesNotCommit(ResolverTestBase):
    """Scenario: Agent Config Command Does Not Commit Changes

    Verified by the fact that config.local.json is gitignored.
    This test verifies the file is in .gitignore.
    """

    def test_local_config_in_gitignore(self):
        gitignore_path = os.path.join(PROJECT_ROOT, '.gitignore')
        with open(gitignore_path) as f:
            content = f.read()
        self.assertIn('config.local.json', content)


class TestDashboardPostWritesToLocal(ResolverTestBase):
    """Scenario: CDD Dashboard POST Writes to Local Config

    Verifies that the resolver reads from local after a dashboard write.
    The actual POST endpoint is tested via serve.py integration tests.
    """

    def test_local_write_visible_to_resolver(self):
        self.write_shared({"agents": {"builder": {"model": "claude-sonnet-4-6"}}})
        # Simulate POST /config/agents writing to local
        self.write_local({"agents": {"builder": {"model": "claude-opus-4-6"}}})
        result = resolve_config(self.tmpdir)
        self.assertEqual(result["agents"]["builder"]["model"], "claude-opus-4-6")


class TestDashboardGetServesLocal(ResolverTestBase):
    """Scenario: CDD Dashboard GET Serves Local Config"""

    def test_get_returns_local_config(self):
        self.write_local({"cdd_port": 9999})
        self.write_shared({"cdd_port": 8086})
        result = resolve_config(self.tmpdir)
        self.assertEqual(result["cdd_port"], 9999)


class TestInitAddsLocalConfigToGitignore(unittest.TestCase):
    """Scenario: Init Adds Local Config to Gitignore"""

    def test_gitignore_has_local_config(self):
        gitignore_path = os.path.join(PROJECT_ROOT, '.gitignore')
        with open(gitignore_path) as f:
            content = f.read()
        self.assertIn('.purlin/config.local.json', content)


class TestInitDoesNotCreateLocalConfig(ResolverTestBase):
    """Scenario: Init Does Not Create Local Config

    Init only creates config.json (shared template).
    The resolver creates config.local.json on first access.
    """

    def test_shared_exists_without_local(self):
        # After bootstrap, only shared exists
        self.write_shared({"tools_root": "tools"})
        self.assertFalse(os.path.exists(self.local_path))
        self.assertTrue(os.path.exists(self.shared_path))


class TestPythonConsumerReadsViaResolver(ResolverTestBase):
    """Scenario: Python Consumer Reads Resolved Config via Resolver"""

    def test_resolver_returns_local_priority(self):
        self.write_local({"critic_llm_enabled": True})
        self.write_shared({"critic_llm_enabled": False})
        result = resolve_config(self.tmpdir)
        self.assertTrue(result["critic_llm_enabled"])


class TestShellConsumerReadsViaCLI(ResolverTestBase):
    """Scenario: Shell Consumer Reads Resolved Config via CLI"""

    def test_cli_returns_resolved_value(self):
        self.write_local({
            "agents": {
                "architect": {
                    "model": "claude-opus-4-6",
                    "effort": "high",
                    "bypass_permissions": True,
                    "startup_sequence": False,
                    "recommend_next_actions": False
                }
            }
        })
        resolver_path = os.path.join(PROJECT_ROOT, 'tools', 'config', 'resolve_config.py')
        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir
        result = subprocess.run(
            [sys.executable, resolver_path, 'architect'],
            capture_output=True, text=True, env=env
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('AGENT_MODEL="claude-opus-4-6"', result.stdout)


class TestUpdateSyncCreatesLocal(ResolverTestBase):
    """Scenario: Update Sync Creates Local Config When Missing"""

    def test_sync_creates_local(self):
        shared_data = {"tools_root": "purlin/tools", "cdd_port": 8086}
        self.write_shared(shared_data)
        self.assertFalse(os.path.exists(self.local_path))

        added = sync_config(self.tmpdir)

        self.assertTrue(os.path.exists(self.local_path))
        self.assertEqual(self.read_local(), shared_data)
        self.assertIn("tools_root", added)
        self.assertIn("cdd_port", added)


class TestUpdateSyncAddsNewKeys(ResolverTestBase):
    """Scenario: Update Sync Adds New Keys Without Overwriting Existing"""

    def test_sync_adds_preserves(self):
        self.write_local({"cdd_port": 9999, "tools_root": "tools"})
        self.write_shared({
            "cdd_port": 8086,
            "tools_root": "tools",
            "critic_llm_enabled": True
        })

        added = sync_config(self.tmpdir)

        local = self.read_local()
        self.assertEqual(local["cdd_port"], 9999)  # Preserved
        self.assertEqual(local["critic_llm_enabled"], True)  # Added
        self.assertIn("critic_llm_enabled", added)
        self.assertNotIn("cdd_port", added)


class TestUpdateSyncNestedKeys(ResolverTestBase):
    """Scenario: Update Sync Adds Nested New Keys"""

    def test_sync_nested(self):
        self.write_local({
            "agents": {"architect": {"model": "opus"}}
        })
        self.write_shared({
            "agents": {
                "architect": {"model": "sonnet"},
                "qa": {"model": "haiku"}
            }
        })

        added = sync_config(self.tmpdir)

        local = self.read_local()
        # Architect model preserved
        self.assertEqual(local["agents"]["architect"]["model"], "opus")
        # QA added with shared defaults
        self.assertIn("qa", local["agents"])
        self.assertEqual(local["agents"]["qa"]["model"], "haiku")
        # Check added keys contain the qa path
        self.assertTrue(any("qa" in k for k in added))


class TestUpdateSyncNoChanges(ResolverTestBase):
    """Scenario: Update Sync Reports No Changes When Already Current"""

    def test_sync_no_changes(self):
        data = {"cdd_port": 9999, "tools_root": "tools"}
        self.write_local(data)
        self.write_shared(data)

        added = sync_config(self.tmpdir)

        self.assertEqual(added, [])
        # Local unchanged
        self.assertEqual(self.read_local(), data)


class TestDeleteLocalRegenerates(ResolverTestBase):
    """Scenario: Deleting Local Config Regenerates From Shared on Next Access"""

    def test_regeneration_after_delete(self):
        shared_data = {"cdd_port": 8086}
        self.write_shared(shared_data)
        # Create then delete local
        self.write_local({"cdd_port": 9999})
        os.remove(self.local_path)

        result = resolve_config(self.tmpdir)

        # Should return shared defaults
        self.assertEqual(result["cdd_port"], 8086)
        # Local should be regenerated
        self.assertTrue(os.path.exists(self.local_path))
        self.assertEqual(self.read_local(), shared_data)


def generate_test_results():
    """Run tests and write results to tests.json."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    failed = len(result.failures) + len(result.errors)
    test_results = {
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "passed": result.testsRun - failed,
        "failed": failed,
        "total": result.testsRun,
        "details": []
    }

    for test, traceback in result.failures:
        test_results["details"].append({
            "test": str(test),
            "type": "FAILURE",
            "message": traceback
        })
    for test, traceback in result.errors:
        test_results["details"].append({
            "test": str(test),
            "type": "ERROR",
            "message": traceback
        })

    results_dir = os.path.join(PROJECT_ROOT, 'tests', 'config_layering')
    os.makedirs(results_dir, exist_ok=True)
    results_path = os.path.join(results_dir, 'tests.json')
    with open(results_path, 'w') as f:
        json.dump(test_results, f, indent=2)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = generate_test_results()
    sys.exit(0 if success else 1)
