#!/usr/bin/env python3
"""Tests for remote_session_naming feature.

Covers unit test scenarios from features/remote_session_naming.md.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
sys.path.insert(0, PROJECT_ROOT)

from tools.config.resolve_config import resolve_config

UNIFIED_LAUNCHER = os.path.join(PROJECT_ROOT, 'pl-run.sh')

CONSUMER_LAUNCHER_TEMPLATE = os.path.join(PROJECT_ROOT, 'tools', 'init.sh')


class ResolverTestBase(unittest.TestCase):
    """Base class with temp .purlin/ setup."""

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


class TestLauncherPassesRemoteControlAndNameFlags(unittest.TestCase):
    """Scenario: Launcher Passes Remote Control and Name Flags

    Verifies the unified launcher (pl-run.sh) passes both --remote-control
    and --name with the "<ProjectName> | <Badge>" format via SESSION_NAME.
    """

    def test_launcher_has_remote_control(self):
        with open(UNIFIED_LAUNCHER, 'r') as f:
            content = f.read()
        self.assertIn('--remote-control', content,
                      "Unified launcher missing --remote-control flag")

    def test_launcher_has_name_with_session_name(self):
        with open(UNIFIED_LAUNCHER, 'r') as f:
            content = f.read()
        self.assertIn('--name "$SESSION_NAME"', content,
                      "Unified launcher --name should use $SESSION_NAME")

    def test_session_name_computed_from_project_and_badge(self):
        with open(UNIFIED_LAUNCHER, 'r') as f:
            content = f.read()
        self.assertIn('SESSION_NAME="$_PROJECT_DISPLAY | $ROLE_DISPLAY"', content,
                      "SESSION_NAME should be <ProjectName> | <Badge>")

    def test_remote_control_uses_session_name(self):
        with open(UNIFIED_LAUNCHER, 'r') as f:
            content = f.read()
        self.assertIn('--remote-control "$SESSION_NAME"', content,
                      "Unified launcher --remote-control should use $SESSION_NAME")

    def test_consumer_template_uses_session_name(self):
        with open(CONSUMER_LAUNCHER_TEMPLATE, 'r') as f:
            content = f.read()
        self.assertIn('SESSION_NAME="$PROJECT_NAME | $DISPLAY_NAME"', content,
                      "Consumer launcher template SESSION_NAME should be <ProjectName> | <Badge>")
        self.assertIn('--remote-control "$SESSION_NAME"', content,
                      "Consumer launcher template --remote-control should use $SESSION_NAME")
        self.assertIn('--name "$SESSION_NAME"', content,
                      "Consumer launcher template --name should use $SESSION_NAME")


class TestSessionNameUsesProjectNameFromConfig(ResolverTestBase):
    """Scenario: Session Name Uses project_name From Config"""

    def test_project_name_from_config(self):
        self.write_local({
            "project_name": "My App",
            "agents": {"builder": {"model": "claude-sonnet-4-6"}}
        })
        resolver_path = os.path.join(PROJECT_ROOT, 'tools', 'config', 'resolve_config.py')
        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir
        result = subprocess.run(
            [sys.executable, resolver_path, 'builder'],
            capture_output=True, text=True, env=env
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('PROJECT_NAME="My App"', result.stdout)


class TestSessionNameFallsBackToDirectoryBasename(ResolverTestBase):
    """Scenario: Session Name Falls Back to Directory Basename"""

    def test_basename_fallback_when_no_key(self):
        self.write_local({
            "agents": {"builder": {"model": "claude-sonnet-4-6"}}
        })
        resolver_path = os.path.join(PROJECT_ROOT, 'tools', 'config', 'resolve_config.py')
        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir
        result = subprocess.run(
            [sys.executable, resolver_path, 'builder'],
            capture_output=True, text=True, env=env
        )
        self.assertEqual(result.returncode, 0)
        expected_name = os.path.basename(self.tmpdir)
        self.assertIn(f'PROJECT_NAME="{expected_name}"', result.stdout)

    def test_basename_fallback_when_empty_key(self):
        self.write_local({
            "project_name": "",
            "agents": {"builder": {"model": "claude-sonnet-4-6"}}
        })
        resolver_path = os.path.join(PROJECT_ROOT, 'tools', 'config', 'resolve_config.py')
        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir
        result = subprocess.run(
            [sys.executable, resolver_path, 'builder'],
            capture_output=True, text=True, env=env
        )
        self.assertEqual(result.returncode, 0)
        expected_name = os.path.basename(self.tmpdir)
        self.assertIn(f'PROJECT_NAME="{expected_name}"', result.stdout)


class TestResolverOutputsProjectNameVariable(ResolverTestBase):
    """Scenario: Resolver Outputs PROJECT_NAME Variable"""

    def test_project_name_in_role_output(self):
        self.write_local({
            "project_name": "Purlin",
            "agents": {"builder": {"model": "claude-sonnet-4-6"}}
        })
        resolver_path = os.path.join(PROJECT_ROOT, 'tools', 'config', 'resolve_config.py')
        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir
        result = subprocess.run(
            [sys.executable, resolver_path, 'builder'],
            capture_output=True, text=True, env=env
        )
        self.assertEqual(result.returncode, 0)
        # Verify PROJECT_NAME appears as a shell assignment on its own line
        self.assertRegex(result.stdout, r'(?m)^PROJECT_NAME="Purlin"$')

    def test_project_name_for_all_roles(self):
        self.write_local({
            "project_name": "TestProject",
            "agents": {
                "architect": {"model": "m"},
                "builder": {"model": "m"},
                "qa": {"model": "m"},
                "pm": {"model": "m"},
            }
        })
        resolver_path = os.path.join(PROJECT_ROOT, 'tools', 'config', 'resolve_config.py')
        for role in ['architect', 'builder', 'qa', 'pm']:
            with self.subTest(role=role):
                env = os.environ.copy()
                env['PURLIN_PROJECT_ROOT'] = self.tmpdir
                result = subprocess.run(
                    [sys.executable, resolver_path, role],
                    capture_output=True, text=True, env=env
                )
                self.assertEqual(result.returncode, 0)
                self.assertIn('PROJECT_NAME="TestProject"', result.stdout)


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
        "test_file": "tests/remote_session_naming/test_remote_session_naming.py",
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

    results_dir = os.path.join(PROJECT_ROOT, 'tests', 'remote_session_naming')
    os.makedirs(results_dir, exist_ok=True)
    results_path = os.path.join(results_dir, 'tests.json')
    with open(results_path, 'w') as f:
        json.dump(test_results, f, indent=2)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = generate_test_results()
    sys.exit(0 if success else 1)
