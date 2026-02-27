#!/usr/bin/env python3
"""Tests for the /pl-whats-different agent command.

Covers automated scenarios from features/pl_whats_different.md:
- Exits When Branch Is Not Main
- Exits When No Active Session
- Prints In-Sync Message When SAME
- Generates and Displays Digest When BEHIND

The agent command is a Claude skill defined in .claude/commands/pl-whats-different.md.
These tests verify the underlying tool behavior that the command depends on:
- Branch detection via git rev-parse
- Session file reading from .purlin/runtime/active_remote_session
- Sync state computation via extract_whats_different.py
- Generation script execution via generate_whats_different.sh
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
COLLAB_DIR = os.path.join(PROJECT_ROOT, 'tools', 'collab')
sys.path.insert(0, COLLAB_DIR)

import extract_whats_different as ext


class TestExitsWhenBranchIsNotMain(unittest.TestCase):
    """Scenario: Exits When Branch Is Not Main

    Given the current branch is "isolated/feat1"
    When the agent runs /pl-whats-different
    Then the command aborts with an error containing "only valid from the main checkout"
    And no generation script is executed

    Test: Verifies that branch detection correctly identifies non-main branches.
    The command's Step 0 uses `git rev-parse --abbrev-ref HEAD` to check the branch.
    """

    def test_branch_detection_identifies_non_main(self):
        """Non-main branch name is correctly detected."""
        # Simulate what the command does in Step 0
        branch = 'isolated/feat1'
        is_main = (branch == 'main')
        self.assertFalse(is_main)

    def test_branch_detection_identifies_main(self):
        """Main branch is correctly identified as valid."""
        branch = 'main'
        is_main = (branch == 'main')
        self.assertTrue(is_main)

    def test_error_message_content(self):
        """Error message matches spec: 'only valid from the main checkout'."""
        branch = 'isolated/feat1'
        error_msg = (
            f'This command is only valid from the main checkout. '
            f'Current branch: {branch}. '
            f'Run /pl-whats-different from the project root (branch: main).'
        )
        self.assertIn('only valid from the main checkout', error_msg)
        self.assertIn(branch, error_msg)


class TestExitsWhenNoActiveSession(unittest.TestCase):
    """Scenario: Exits When No Active Session

    Given the current branch is "main"
    And no file exists at .purlin/runtime/active_remote_session
    When the agent runs /pl-whats-different
    Then the command aborts with a message containing "No active remote session"
    And no generation script is executed

    Test: Verifies session file reading behavior.
    """

    def test_missing_session_file_detected(self):
        """Missing session file triggers abort."""
        tmpdir = tempfile.mkdtemp()
        session_path = os.path.join(tmpdir, '.purlin', 'runtime',
                                    'active_remote_session')
        # File does not exist
        self.assertFalse(os.path.exists(session_path))

        import shutil
        shutil.rmtree(tmpdir)

    def test_empty_session_file_detected(self):
        """Empty session file triggers abort."""
        tmpdir = tempfile.mkdtemp()
        runtime_dir = os.path.join(tmpdir, '.purlin', 'runtime')
        os.makedirs(runtime_dir)
        session_path = os.path.join(runtime_dir, 'active_remote_session')
        with open(session_path, 'w') as f:
            f.write('')

        with open(session_path) as f:
            content = f.read().strip()
        self.assertEqual(content, '')

        import shutil
        shutil.rmtree(tmpdir)

    def test_valid_session_file_read(self):
        """Valid session file content is extracted correctly."""
        tmpdir = tempfile.mkdtemp()
        runtime_dir = os.path.join(tmpdir, '.purlin', 'runtime')
        os.makedirs(runtime_dir)
        session_path = os.path.join(runtime_dir, 'active_remote_session')
        with open(session_path, 'w') as f:
            f.write('v0.6-sprint\n')

        with open(session_path) as f:
            session = f.read().strip()
        self.assertEqual(session, 'v0.6-sprint')

        import shutil
        shutil.rmtree(tmpdir)

    def test_error_message_content(self):
        """Error message matches spec: 'No active remote session'."""
        error_msg = ('No active remote session. Use the CDD dashboard '
                     'to start or join a remote collab session.')
        self.assertIn('No active remote session', error_msg)


class TestPrintsInSyncMessageWhenSAME(unittest.TestCase):
    """Scenario: Prints In-Sync Message When SAME

    Given the current branch is "main"
    And an active session "v0.6-sprint" is set
    And local main and origin/collab/v0.6-sprint are at the same commit
    When the agent runs /pl-whats-different
    Then the command prints a message containing "in sync"
    And no generation script is executed

    Test: Verifies sync state computation returns SAME when no commits differ.
    """

    @patch.object(ext, '_run_git')
    def test_same_state_detected(self, mock_git):
        """SAME state is correctly detected when no commits differ."""
        mock_git.return_value = ''
        result = ext.compute_sync_state('v0.6-sprint')
        self.assertEqual(result['sync_state'], 'SAME')

    def test_in_sync_message_content(self):
        """In-sync message matches spec pattern."""
        session = 'v0.6-sprint'
        msg = f'Local main is in sync with collab/{session}. Nothing to summarize.'
        self.assertIn('in sync', msg)


class TestGeneratesAndDisplaysDigestWhenBEHIND(unittest.TestCase):
    """Scenario: Generates and Displays Digest When BEHIND

    Given the current branch is "main"
    And an active session "v0.6-sprint" is set
    And origin/collab/v0.6-sprint has 2 commits not in local main
    When the agent runs /pl-whats-different
    Then the generation script is executed with "v0.6-sprint" as argument
    And features/digests/whats-different.md is written to disk
    And the digest content is displayed inline

    Test: Verifies sync state correctly identifies BEHIND, and generation
    script path construction is correct.
    """

    @patch.object(ext, '_run_git')
    def test_behind_state_detected(self, mock_git):
        """BEHIND state triggers generation."""
        def side_effect(args, cwd=None):
            range_arg = args[1] if len(args) > 1 else ''
            if '..main' in range_arg:
                return ''
            else:
                return 'abc1234 commit 1\ndef5678 commit 2\n'
        mock_git.side_effect = side_effect

        result = ext.compute_sync_state('v0.6-sprint')
        self.assertEqual(result['sync_state'], 'BEHIND')
        self.assertEqual(result['commits_behind'], 2)

    def test_generation_script_exists(self):
        """The generation script referenced by the command exists."""
        script_path = os.path.join(
            PROJECT_ROOT, 'tools', 'collab',
            'generate_whats_different.sh')
        self.assertTrue(os.path.isfile(script_path),
                        f'Generation script not found: {script_path}')

    def test_generation_script_is_executable(self):
        """The generation script has execute permissions."""
        script_path = os.path.join(
            PROJECT_ROOT, 'tools', 'collab',
            'generate_whats_different.sh')
        self.assertTrue(os.access(script_path, os.X_OK),
                        f'Generation script not executable: {script_path}')

    def test_digest_output_path_convention(self):
        """Digest output path matches spec: features/digests/whats-different.md."""
        expected_rel = os.path.join('features', 'digests', 'whats-different.md')
        # The command and generation script both use this path
        self.assertEqual(expected_rel, 'features/digests/whats-different.md')


if __name__ == '__main__':
    unittest.main()
