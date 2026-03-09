#!/usr/bin/env python3
"""Tests for /pl-agent-config skill (pl_agent_config feature).

The skill is an agent instruction file (.claude/commands/pl-agent-config.md).
These tests verify the structural contract and integration with the config
resolver.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
sys.path.insert(0, PROJECT_ROOT)

from tools.config.resolve_config import resolve_config


SKILL_PATH = os.path.join(PROJECT_ROOT, '.claude', 'commands', 'pl-agent-config.md')


class TestSkillFileContract(unittest.TestCase):
    """Verify the skill file references the correct config file and steps."""

    def setUp(self):
        with open(SKILL_PATH, 'r') as f:
            self.content = f.read()

    def test_skill_file_exists(self):
        self.assertTrue(os.path.exists(SKILL_PATH))

    def test_targets_local_config(self):
        """The skill must reference config.local.json as the write target."""
        self.assertIn('config.local.json', self.content)

    def test_does_not_commit(self):
        """The skill must NOT contain git commit/add commands."""
        self.assertNotIn('git -C', self.content)
        self.assertNotIn('git add', self.content)
        # "git commit" as a command (in code blocks) should not appear,
        # but "No git commit is made" as prose is expected.
        # Check there's no ### step header for committing
        self.assertNotIn('### 7. Commit', self.content)
        self.assertNotIn('### 8. Commit', self.content)
        self.assertNotIn('Stage and commit', self.content)

    def test_no_commit_confirmation(self):
        """The confirmation step must not reference a commit."""
        self.assertNotIn('Commit:', self.content)

    def test_gitignored_note(self):
        """The skill must note that config.local.json is gitignored."""
        self.assertIn('gitignored', self.content)

    def test_valid_keys_listed(self):
        """All five valid config keys must be listed."""
        for key in ['model', 'effort', 'startup_sequence',
                     'recommend_next_actions', 'bypass_permissions']:
            self.assertIn(key, self.content)

    def test_copy_on_first_access(self):
        """The skill must handle missing config.local.json by copying from config.json."""
        self.assertIn('copy', self.content.lower())


class ConfigWriteTestBase(unittest.TestCase):
    """Base class providing temp directory with .purlin/ structure."""

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
            json.dump(data, f, indent=4)

    def write_shared(self, data):
        with open(self.shared_path, 'w') as f:
            json.dump(data, f, indent=4)

    def read_local(self):
        with open(self.local_path, 'r') as f:
            return json.load(f)

    def read_shared(self):
        with open(self.shared_path, 'r') as f:
            return json.load(f)


class TestConfigChangeAppliedToLocalConfig(ConfigWriteTestBase):
    """Scenario: Config Change Applied to Local Config

    Simulates the write that /pl-agent-config performs: update config.local.json,
    leave config.json unchanged, no git commit.
    """

    def test_local_updated_shared_unchanged(self):
        shared = {
            "agents": {"builder": {"startup_sequence": True, "model": "claude-sonnet-4-6"}},
            "models": [{"id": "claude-sonnet-4-6"}]
        }
        self.write_shared(shared)
        self.write_local(shared.copy())

        # Simulate /pl-agent-config builder startup_sequence false
        local = self.read_local()
        local["agents"]["builder"]["startup_sequence"] = False
        tmp_path = self.local_path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(local, f, indent=4)
        os.replace(tmp_path, self.local_path)

        # Verify local was updated
        result = resolve_config(self.tmpdir)
        self.assertFalse(result["agents"]["builder"]["startup_sequence"])

        # Verify shared is unchanged
        with open(self.shared_path) as f:
            s = json.load(f)
        self.assertTrue(s["agents"]["builder"]["startup_sequence"])


class TestInvalidKeyRejected(unittest.TestCase):
    """Scenario: Invalid Key Rejected

    Verifies the skill file lists the valid keys and the error message format.
    """

    def test_error_message_format(self):
        with open(SKILL_PATH) as f:
            content = f.read()
        self.assertIn("Unknown key", content)
        self.assertIn("Valid keys:", content)


class TestInvalidModelValueRejected(ConfigWriteTestBase):
    """Scenario: Invalid Model Value Rejected

    Verifies that model validation checks against the models array in config.
    """

    def test_model_validation_against_config(self):
        config = {
            "models": [
                {"id": "claude-sonnet-4-6", "label": "Sonnet 4.6"},
                {"id": "claude-haiku-4-5", "label": "Haiku 4.5"}
            ],
            "agents": {"architect": {"model": "claude-sonnet-4-6"}}
        }
        self.write_local(config)
        result = resolve_config(self.tmpdir)
        valid_ids = [m["id"] for m in result.get("models", [])]

        # Valid model should pass
        self.assertIn("claude-sonnet-4-6", valid_ids)
        # Invalid model should fail validation
        self.assertNotIn("claude-gpt-5", valid_ids)

    def test_skill_lists_model_validation(self):
        with open(SKILL_PATH) as f:
            content = f.read()
        self.assertIn("models", content)
        self.assertIn("model", content)


def generate_test_results():
    """Run tests and write results to tests.json."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    test_results = {
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "passed": result.testsRun - len(result.failures) - len(result.errors),
        "failed": len(result.failures) + len(result.errors),
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

    results_dir = os.path.join(PROJECT_ROOT, 'tests', 'pl_agent_config')
    os.makedirs(results_dir, exist_ok=True)
    results_path = os.path.join(results_dir, 'tests.json')
    with open(results_path, 'w') as f:
        json.dump(test_results, f, indent=2)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = generate_test_results()
    sys.exit(0 if success else 1)
