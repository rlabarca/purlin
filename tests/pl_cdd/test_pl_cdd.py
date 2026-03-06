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
        # Skill instructs agent to relay URL output from start.sh
        self.assertIn('prints the URL', self.content)

    def test_start_when_already_running_restarts(self):
        """Scenario: Start when already running restarts on same port."""
        # Must stop existing instance before restarting
        self.assertIn('STOP_SCRIPT', self.content)
        # Must read current port and pass as preference
        self.assertIn('cdd.port', self.content)
        self.assertIn('PREFERRED_PORT', self.content)
        self.assertIn('-p', self.content)

    def test_restart_falls_back_to_new_port(self):
        """Scenario: Restart falls back to new port when preferred port unavailable."""
        # Must retry without -p if preferred port fails
        self.assertIn('retry without', self.content.lower())

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
