"""Tests for the /pl-cdd skill (features/pl_cdd.md).

Validates that the skill command file contains the required instructions
for all automated scenarios. Since skills are agent instructions (not
executable code), tests verify instruction presence rather than runtime behavior.
"""

import os
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
        self.assertIn('http://localhost', self.content)

    def test_start_when_already_running_shows_url(self):
        """Scenario: Start when already running shows URL."""
        self.assertIn('already running', self.content.lower())
        self.assertIn('cdd.port', self.content)

    def test_stop_a_running_server(self):
        """Scenario: Stop a running server."""
        self.assertIn('stop', self.content.lower())
        self.assertIn('STOP_SCRIPT', self.content)

    def test_restart_cycles_the_server(self):
        """Scenario: Restart cycles the server."""
        self.assertIn('restart', self.content.lower())
        # Restart must execute stop then start sequentially
        self.assertIn('Stop (4b), then Start (4a)', self.content)

    def test_invalid_argument_produces_error(self):
        """Scenario: Invalid argument produces error."""
        self.assertIn("Unknown argument", self.content)
        self.assertIn("Valid: stop, restart", self.content)


if __name__ == '__main__':
    unittest.main()
