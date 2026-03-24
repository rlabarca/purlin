#!/usr/bin/env python3
"""Tests for remote_session_naming feature.

Covers all 7 unit test scenarios from features/remote_session_naming.md.
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

LAUNCHERS = {
    'architect': os.path.join(PROJECT_ROOT, 'pl-run-architect.sh'),
    'builder': os.path.join(PROJECT_ROOT, 'pl-run-builder.sh'),
    'qa': os.path.join(PROJECT_ROOT, 'pl-run-qa.sh'),
    'pm': os.path.join(PROJECT_ROOT, 'pl-run-pm.sh'),
}

ROLE_DISPLAY_MAP = {
    'architect': 'Architect',
    'builder': 'Builder',
    'qa': 'QA',
    'pm': 'PM',
}


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


class TestLauncherAlwaysPassesRemoteControlFlag(unittest.TestCase):
    """Scenario: Launcher Always Passes Remote Control Flag

    Verifies all 4 launcher scripts contain --remote-control with
    the "$PROJECT_NAME | $ROLE_DISPLAY" pattern and define ROLE_DISPLAY.
    """

    def test_all_launchers_have_remote_control(self):
        for role, path in LAUNCHERS.items():
            with self.subTest(role=role):
                with open(path, 'r') as f:
                    content = f.read()
                self.assertIn('--remote-control', content,
                              f"{role} launcher missing --remote-control flag")
                self.assertIn('$PROJECT_NAME', content,
                              f"{role} launcher missing $PROJECT_NAME reference")
                self.assertIn('$ROLE_DISPLAY', content,
                              f"{role} launcher missing $ROLE_DISPLAY reference")

    def test_all_launchers_define_role_display(self):
        for role, path in LAUNCHERS.items():
            expected_display = ROLE_DISPLAY_MAP[role]
            with self.subTest(role=role):
                with open(path, 'r') as f:
                    content = f.read()
                self.assertIn(f'ROLE_DISPLAY="{expected_display}"', content,
                              f"{role} launcher has wrong ROLE_DISPLAY value")

    def test_remote_control_uses_quoted_format(self):
        for role, path in LAUNCHERS.items():
            with self.subTest(role=role):
                with open(path, 'r') as f:
                    content = f.read()
                # Verify the --remote-control arg uses the correct quoted format
                self.assertRegex(
                    content,
                    r'--remote-control\s+"\$PROJECT_NAME \| \$ROLE_DISPLAY"',
                    f"{role} launcher --remote-control not properly quoted"
                )


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


class TestResumeSuggestsRenameWhenRoleChanges(unittest.TestCase):
    """Scenario: Resume Suggests Rename When Role Changes

    Verifies the /pl-resume skill file contains rename suggestion logic
    for when the explicit role argument differs from the system prompt role.
    """

    def test_resume_has_rename_suggestion(self):
        resume_path = os.path.join(PROJECT_ROOT, '.claude', 'commands', 'pl-resume.md')
        with open(resume_path, 'r') as f:
            content = f.read()
        # Must contain the rename suggestion template
        self.assertIn('Session name:', content)
        self.assertIn('/rename', content)
        self.assertIn('<ProjectName>', content)
        self.assertIn('<NewRole>', content)

    def test_rename_requires_explicit_role_argument(self):
        resume_path = os.path.join(PROJECT_ROOT, '.claude', 'commands', 'pl-resume.md')
        with open(resume_path, 'r') as f:
            content = f.read()
        self.assertIn('explicit role argument', content)
        self.assertIn('tier 1', content)

    def test_rename_requires_different_system_prompt_role(self):
        resume_path = os.path.join(PROJECT_ROOT, '.claude', 'commands', 'pl-resume.md')
        with open(resume_path, 'r') as f:
            content = f.read()
        self.assertIn('different role', content)
        self.assertIn('tier 2', content)


class TestResumeOmitsRenameWhenRoleUnchanged(unittest.TestCase):
    """Scenario: Resume Omits Rename When Role Unchanged

    Verifies the /pl-resume skill file specifies omission when
    tier 1 role matches tier 2 role.
    """

    def test_resume_specifies_omission_for_same_role(self):
        resume_path = os.path.join(PROJECT_ROOT, '.claude', 'commands', 'pl-resume.md')
        with open(resume_path, 'r') as f:
            content = f.read()
        self.assertIn('role is unchanged', content)
        self.assertIn('omitted', content)


class TestResumeOmitsRenameWhenNoSystemPromptRoleMarkers(unittest.TestCase):
    """Scenario: Resume Omits Rename When No System Prompt Role Markers

    Verifies the /pl-resume skill file specifies omission when
    the system prompt has no role identity markers (fresh session).
    """

    def test_resume_specifies_omission_for_no_markers(self):
        resume_path = os.path.join(PROJECT_ROOT, '.claude', 'commands', 'pl-resume.md')
        with open(resume_path, 'r') as f:
            content = f.read()
        self.assertIn('no system prompt role markers', content)
        self.assertIn('omitted', content)


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
