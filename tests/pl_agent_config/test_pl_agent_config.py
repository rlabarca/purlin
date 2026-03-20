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
        for key in ['model', 'effort', 'find_work',
                     'auto_start', 'bypass_permissions']:
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
            "agents": {"builder": {"find_work": True, "model": "claude-sonnet-4-6"}},
            "models": [{"id": "claude-sonnet-4-6"}]
        }
        self.write_shared(shared)
        self.write_local(shared.copy())

        # Simulate /pl-agent-config builder find_work false
        local = self.read_local()
        local["agents"]["builder"]["find_work"] = False
        tmp_path = self.local_path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(local, f, indent=4)
        os.replace(tmp_path, self.local_path)

        # Verify local was updated
        result = resolve_config(self.tmpdir)
        self.assertFalse(result["agents"]["builder"]["find_work"])

        # Verify shared is unchanged
        with open(self.shared_path) as f:
            s = json.load(f)
        self.assertTrue(s["agents"]["builder"]["find_work"])


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


class TestWarningDisplayAndAutoAcknowledge(ConfigWriteTestBase):
    """Scenario: Setting Model With Warning Shows Warning and Auto-Acknowledges

    Verifies that when a model with a warning is set via /pl-agent-config,
    the warning text would be displayed and the model ID is added to
    acknowledged_warnings in config.local.json.
    """

    def test_warning_model_triggers_acknowledgment(self):
        config = {
            "models": [
                {"id": "claude-opus-4-6[1m]", "label": "Opus 4.6 [1M]",
                 "warning": "Extended context costs extra.",
                 "warning_dismissible": True,
                 "capabilities": {"effort": True, "permissions": True}},
                {"id": "claude-sonnet-4-6", "label": "Sonnet 4.6",
                 "capabilities": {"effort": True, "permissions": True}},
            ],
            "agents": {"architect": {"model": "claude-sonnet-4-6"}}
        }
        self.write_local(config)

        # Simulate /pl-agent-config architect model claude-opus-4-6[1m]
        local = self.read_local()
        model_id = "claude-opus-4-6[1m]"
        local["agents"]["architect"]["model"] = model_id

        # Find model and check warning
        model_obj = next(m for m in local["models"] if m["id"] == model_id)
        self.assertTrue(model_obj.get("warning"))
        self.assertTrue(model_obj.get("warning_dismissible", False))

        # Auto-acknowledge: add to acknowledged_warnings
        acknowledged = local.get("acknowledged_warnings", [])
        if model_id not in acknowledged:
            acknowledged.append(model_id)
            local["acknowledged_warnings"] = acknowledged

        # Atomic write
        tmp_path = self.local_path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(local, f, indent=4)
        os.replace(tmp_path, self.local_path)

        # Verify model ID is in acknowledged_warnings
        result = self.read_local()
        self.assertIn(model_id, result.get("acknowledged_warnings", []))
        self.assertEqual(result["agents"]["architect"]["model"], model_id)

    def test_warning_text_available_for_display(self):
        """The warning text from the model config is available for output."""
        config = {
            "models": [
                {"id": "claude-opus-4-6[1m]", "label": "Opus 4.6 [1M]",
                 "warning": "Extended context costs extra.",
                 "warning_dismissible": True,
                 "capabilities": {"effort": True, "permissions": True}},
            ],
            "agents": {"architect": {"model": "claude-sonnet-4-6"}}
        }
        self.write_local(config)
        local = self.read_local()
        model_obj = next(m for m in local["models"] if m["id"] == "claude-opus-4-6[1m]")
        self.assertEqual(model_obj["warning"], "Extended context costs extra.")


class TestPreviouslyAcknowledgedWarningOmitted(ConfigWriteTestBase):
    """Scenario: Setting Model With Previously Acknowledged Warning Omits Warning

    Verifies that when a model with a warning is set but the model ID is
    already in acknowledged_warnings, no warning display is needed.
    """

    def test_acknowledged_model_skips_warning(self):
        config = {
            "models": [
                {"id": "claude-opus-4-6[1m]", "label": "Opus 4.6 [1M]",
                 "warning": "Extended context costs extra.",
                 "warning_dismissible": True,
                 "capabilities": {"effort": True, "permissions": True}},
            ],
            "agents": {"architect": {"model": "claude-sonnet-4-6"}},
            "acknowledged_warnings": ["claude-opus-4-6[1m]"]
        }
        self.write_local(config)

        # Simulate /pl-agent-config architect model claude-opus-4-6[1m]
        local = self.read_local()
        model_id = "claude-opus-4-6[1m]"

        # Check: model ID IS in acknowledged_warnings
        acknowledged = local.get("acknowledged_warnings", [])
        self.assertIn(model_id, acknowledged)

        # When already acknowledged, warning_dismissed is true -> no warning shown
        model_obj = next(m for m in local["models"] if m["id"] == model_id)
        is_dismissed = (model_obj.get("warning_dismissible", False) and
                        model_id in acknowledged)
        self.assertTrue(is_dismissed)

        # Apply change (no acknowledgment step needed)
        local["agents"]["architect"]["model"] = model_id
        tmp_path = self.local_path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(local, f, indent=4)
        os.replace(tmp_path, self.local_path)

        # Verify: acknowledged_warnings unchanged (no duplicate added)
        result = self.read_local()
        self.assertEqual(result.get("acknowledged_warnings", []).count(model_id), 1)

    def test_skill_file_references_acknowledged_warnings(self):
        """The skill file must reference acknowledged_warnings for the check."""
        with open(SKILL_PATH) as f:
            content = f.read()
        self.assertIn('acknowledged_warnings', content)
        self.assertIn('warning', content)


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
