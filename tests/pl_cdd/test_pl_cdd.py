"""Tests for the /pl-cdd skill (features/pl_cdd.md).

Validates that the skill command file contains the required instructions
for all automated scenarios. Since skills are agent instructions (not
executable code), tests verify instruction presence rather than runtime behavior.
"""

import json
import os
import sys
import unittest


SKILL_PATH = os.path.join(
    os.path.dirname(__file__), '../../.claude/commands/pl-cdd.md')


class TestPlCddSkill(unittest.TestCase):
    """Verify /pl-cdd skill instructions cover all scenarios."""

    @classmethod
    def setUpClass(cls):
        with open(SKILL_PATH) as f:
            cls.content = f.read()

    def test_start_when_not_running(self):
        """Scenario: Start when not running."""
        self.assertIn('start.sh', self.content)
        self.assertIn('START_SCRIPT', self.content)
        # Skill instructs agent to print output from start.sh (URL)
        self.assertIn('Print the output from the script', self.content)

    def test_start_when_already_running_restarts(self):
        """Scenario: Start when already running restarts via start.sh."""
        # start.sh handles restart internally per cdd_lifecycle §2.9
        self.assertIn('restart logic internally', self.content)
        self.assertIn('cdd_lifecycle.md', self.content)

    def test_stop_a_running_server(self):
        """Scenario: Stop a running server."""
        self.assertIn('stop', self.content.lower())
        self.assertIn('STOP_SCRIPT', self.content)

    def test_restart_cycles_the_server(self):
        """Scenario: Restart cycles the server."""
        self.assertIn('restart', self.content.lower())
        # Restart must execute stop then start sequentially
        self.assertIn('Stop (3b), then Start (3a)', self.content)

    def test_invalid_argument_produces_error(self):
        """Scenario: Invalid argument produces error."""
        self.assertIn("Unknown argument", self.content)
        self.assertIn("Valid: stop, restart", self.content)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    failed = len(result.failures) + len(result.errors)
    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, 'tests.json'), 'w') as f:
        json.dump({
            'status': 'PASS' if result.wasSuccessful() else 'FAIL',
            'passed': result.testsRun - failed,
            'failed': failed,
            'total': result.testsRun,
        }, f)
    sys.exit(0 if result.wasSuccessful() else 1)
