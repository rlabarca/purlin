"""Tests for spec_code_audit_role_clarity feature.

Verifies that the /pl-spec-code-audit command file contains role-scoped
remediation instructions distinguishing Architect and Builder artifact targets.
"""

import os
import sys
import json
import unittest

# Resolve project root
PROJECT_ROOT = os.environ.get("PURLIN_PROJECT_ROOT")
if not PROJECT_ROOT:
    # Climb from this file: tests/spec_code_audit_role_clarity/ -> project root
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-spec-code-audit.md")
TESTS_JSON = os.path.join(
    PROJECT_ROOT, "tests", "spec_code_audit_role_clarity", "tests.json"
)


class TestArchitectRemediationDescribesOnlySpecEdits(unittest.TestCase):
    """Scenario: Architect remediation plan describes only spec edits."""

    def setUp(self):
        with open(COMMAND_FILE, "r") as f:
            self.content = f.read()

    def test_architect_fix_targets_feature_specs(self):
        self.assertIn("Architect FIX edits", self.content)
        self.assertIn("feature specs", self.content)

    def test_architect_fix_targets_anchor_nodes(self):
        self.assertIn("anchor nodes", self.content)
        for prefix in ("arch_*.md", "design_*.md", "policy_*.md"):
            self.assertIn(prefix, self.content)

    def test_architect_fix_does_not_mention_source_code_targets(self):
        # The Architect FIX line should not reference implementation files
        lines = self.content.split("\n")
        architect_lines = [l for l in lines if "Architect FIX edits" in l]
        self.assertTrue(len(architect_lines) > 0)
        for line in architect_lines:
            self.assertNotIn("implementation file", line)
            self.assertNotIn("source code", line)


class TestBuilderRemediationDescribesOnlyCodeEdits(unittest.TestCase):
    """Scenario: Builder remediation plan describes only code edits."""

    def setUp(self):
        with open(COMMAND_FILE, "r") as f:
            self.content = f.read()

    def test_builder_fix_targets_source_code(self):
        self.assertIn("Builder FIX edits", self.content)
        self.assertIn("source code", self.content)

    def test_builder_fix_targets_tests(self):
        lines = self.content.split("\n")
        builder_lines = [l for l in lines if "Builder FIX edits" in l]
        self.assertTrue(len(builder_lines) > 0)
        for line in builder_lines:
            self.assertIn("test", line.lower())

    def test_builder_fix_does_not_mention_spec_targets(self):
        lines = self.content.split("\n")
        builder_lines = [l for l in lines if "Builder FIX edits" in l]
        self.assertTrue(len(builder_lines) > 0)
        for line in builder_lines:
            self.assertNotIn("feature spec", line)
            self.assertNotIn("anchor node", line)


def run_tests_and_write_json():
    """Run tests and write results to tests.json."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    status = "PASS" if result.wasSuccessful() else "FAIL"
    failures = []
    for test, traceback in result.failures + result.errors:
        failures.append({"test": str(test), "message": traceback})

    report = {
        "status": status,
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "details": failures,
    }

    os.makedirs(os.path.dirname(TESTS_JSON), exist_ok=True)
    with open(TESTS_JSON, "w") as f:
        json.dump(report, f, indent=2)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests_and_write_json()
    sys.exit(0 if success else 1)
