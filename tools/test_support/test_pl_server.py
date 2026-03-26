#!/usr/bin/env python3
"""Tests for the /pl-server skill command file.

Covers all 5 unit test scenarios from features/pl_server.md.
Since skills are agent instruction files (not executable code), these
tests verify structural properties of the command file that ensure
correct runtime behavior.
"""

import os
import re
import json
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, "../../")))
from tools.bootstrap import detect_project_root

PROJECT_ROOT = detect_project_root(SCRIPT_DIR)
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-server.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonEngineerQA(unittest.TestCase):
    """Scenario: Role gate rejects non-Engineer/QA invocation

    Given an PM agent session
    When the agent invokes /pl-server
    Then the command responds with a redirect message

    Structural test: the command file's first line declares shared access
    for Engineer and QA only, and contains a redirect message for other roles.
    """

    def test_first_line_declares_shared_builder_qa(self):
        """First line must declare the command as shared between Engineer and QA."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        lower = first_line.lower()
        self.assertIn("shared", lower)
        self.assertIn("builder", lower)
        self.assertIn("qa", lower)

    def test_first_line_not_all_roles(self):
        """Command must NOT be shared with all roles -- only Engineer and QA."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertNotIn("all roles", first_line.lower())

    def test_redirect_message_for_other_roles(self):
        """Non-Engineer/QA agents must receive a redirect/stop message."""
        content = read_command_file()
        lower = content.lower()
        self.assertTrue(
            "not operating as" in lower or "redirect" in lower or "stop" in lower,
            "Command file must contain a redirect message for unauthorized roles",
        )


class TestPortConflictSelectsAlternatePort(unittest.TestCase):
    """Scenario: Port conflict selects alternate port

    Given port 3000 is already in use
    When /pl-server starts a dev server with default port 3000
    Then port 3100 is selected instead
    And the user is informed of the alternate port

    Structural test: the command file describes port conflict handling
    with default + 100 offset strategy.
    """

    def test_port_availability_check_present(self):
        """Command file must describe checking port availability."""
        content = read_command_file()
        self.assertTrue(
            "port" in content.lower() and ("availab" in content.lower() or "in use" in content.lower() or "occupied" in content.lower()),
            "Command file must describe port availability checking",
        )

    def test_alternate_port_offset_documented(self):
        """Command file must describe the +100 port offset strategy."""
        content = read_command_file()
        self.assertIn("100", content,
                       "Command file must reference the +100 port offset")

    def test_port_conflict_example(self):
        """Command file must show an example like 3000 -> 3100."""
        content = read_command_file()
        self.assertIn("3100", content,
                       "Command file must include the 3100 alternate port example")

    def test_lsof_port_check_command(self):
        """Command file must include lsof command for port checking."""
        content = read_command_file()
        self.assertRegex(content, r"lsof.*-i.*:",
                         "Command file must include lsof command for port checking")


class TestStateFileTracksRunningServer(unittest.TestCase):
    """Scenario: State file tracks running server

    Given a dev server is started on port 3000 with PID 12345
    When the server is running
    Then .purlin/runtime/dev_server.json contains pid and port

    Structural test: the command file references .purlin/runtime/dev_server.json
    for tracking PID and port.
    """

    def test_state_file_path_referenced(self):
        """Command file must reference the state file path."""
        content = read_command_file()
        self.assertIn(".purlin/runtime/dev_server.json", content)

    def test_pid_field_in_state_file(self):
        """State file format must include pid field."""
        content = read_command_file()
        self.assertIn('"pid"', content,
                       "State file format must include pid field")

    def test_port_field_in_state_file(self):
        """State file format must include port field."""
        content = read_command_file()
        self.assertIn('"port"', content,
                       "State file format must include port field")

    def test_state_file_is_gitignored(self):
        """Command file must note the state file is gitignored."""
        content = read_command_file()
        self.assertIn("gitignore", content.lower(),
                       "Command file must note the state file is gitignored")


class TestStaleServerDetectedOnSessionStart(unittest.TestCase):
    """Scenario: Stale server detected on session start

    Given dev_server.json exists from a previous session
    And the tracked PID is still running
    When a new session starts
    Then a warning about the stale server is displayed
    And the user is asked whether to kill it

    Structural test: the command file describes stale server detection
    from previous sessions.
    """

    def test_stale_detection_described(self):
        """Command file must describe stale server detection."""
        content = read_command_file()
        self.assertIn("stale", content.lower(),
                       "Command file must describe stale server detection")

    def test_previous_session_mentioned(self):
        """Command file must reference detection from previous sessions."""
        content = read_command_file()
        self.assertIn("previous session", content.lower(),
                       "Command file must reference previous sessions")

    def test_warning_message_present(self):
        """Command file must include a warning message for stale servers."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)stale.*server.*detected",
            "Command file must include a stale server warning message",
        )

    def test_asks_user_about_kill(self):
        """Command file must describe asking the user whether to kill the stale server."""
        content = read_command_file()
        lower = content.lower()
        self.assertTrue(
            "ask" in lower or "whether to kill" in lower,
            "Command file must describe asking user whether to kill stale server",
        )


class TestCleanupStopsServerAndRemovesStateFile(unittest.TestCase):
    """Scenario: Cleanup stops server and removes state

    Given a dev server is tracked in dev_server.json
    When /pl-server stop is invoked
    Then the tracked PID is killed
    And dev_server.json is removed

    Structural test: the command file describes the cleanup protocol
    including stopping the server and removing the state file.
    """

    def test_kill_tracked_pid_described(self):
        """Command file must describe killing the tracked PID."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)kill.*pid|kill.*<pid>",
            "Command file must describe killing the tracked PID",
        )

    def test_remove_state_file_described(self):
        """Command file must describe removing dev_server.json."""
        content = read_command_file()
        lower = content.lower()
        self.assertTrue(
            "remove" in lower and "dev_server.json" in content,
            "Command file must describe removing dev_server.json",
        )

    def test_stop_confirmation_message(self):
        """Command file must include a stop confirmation message."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)dev server stopped",
            "Command file must include a stop confirmation message",
        )

    def test_cleanup_on_session_end(self):
        """Command file must describe cleanup on session end."""
        content = read_command_file()
        lower = content.lower()
        self.assertTrue(
            "session end" in lower or "on session end" in lower,
            "Command file must describe cleanup on session end",
        )


# ===================================================================
# Test result output
# ===================================================================

class JsonTestResult(unittest.TextTestResult):
    """Custom result that collects pass/fail for JSON output."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.results = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.results.append({"test": str(test), "status": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.results.append({"test": str(test), "status": "FAIL", "message": str(err[1])})

    def addError(self, test, err):
        super().addError(test, err)
        self.results.append({"test": str(test), "status": "ERROR", "message": str(err[1])})


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(resultclass=JsonTestResult, verbosity=2)
    result = runner.run(suite)

    # Write tests.json
    if PROJECT_ROOT:
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_server")
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "tests.json")

        all_passed = len(result.failures) == 0 and len(result.errors) == 0
        failed = len(result.failures) + len(result.errors)
        with open(out_file, "w") as f:
            json.dump(
                {
                    "status": "PASS" if all_passed else "FAIL",
                    "passed": result.testsRun - failed,
                    "failed": failed,
                    "total": result.testsRun,
                    "test_file": "tools/test_support/test_pl_server.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
