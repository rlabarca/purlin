#!/usr/bin/env python3
"""Tests for the /pl-web-test skill command file.

Covers structural properties from features/pl_web_test.md.
Since skills are agent instruction files (not executable code), these
tests verify the command file contains required instructions for
port resolution, server auto-start, and Playwright detection.
"""

import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, "../../")))
from tools.bootstrap import detect_project_root

PROJECT_ROOT = detect_project_root(SCRIPT_DIR)
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-web-test.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGating(unittest.TestCase):
    """Scenario: Role gate allows Engineer and QA cross-mode."""

    def test_command_file_declares_engineer_mode(self):
        content = read_command_file()
        self.assertIn("Purlin mode: Engineer", content)

    def test_command_file_allows_qa_cross_mode(self):
        content = read_command_file()
        self.assertIn("QA cross-mode", content)


class TestPortResolution(unittest.TestCase):
    """Scenario: Port resolution from Web Test metadata."""

    def test_command_file_references_port_detection(self):
        content = read_command_file()
        self.assertTrue(
            "port" in content.lower(),
            "Command file must reference port detection logic",
        )

    def test_command_file_references_web_test_metadata(self):
        content = read_command_file()
        self.assertIn("Web Test:", content)


class TestPlaywrightIntegration(unittest.TestCase):
    """Scenario: Playwright MCP detection and browser control."""

    def test_command_file_references_playwright(self):
        content = read_command_file()
        self.assertIn("Playwright", content)

    def test_command_file_references_browser_navigate(self):
        content = read_command_file()
        self.assertIn("browser_navigate", content)


class TestDesignAnchorCompliance(unittest.TestCase):
    """Verify arch_testing and design_artifact_pipeline anchor compliance."""

    def test_command_file_references_token_map(self):
        content = read_command_file()
        self.assertIn("Token Map", content)

    def test_command_file_references_visual_specification(self):
        content = read_command_file()
        self.assertIn("Visual Specification", content)


if __name__ == "__main__":
    unittest.main()
