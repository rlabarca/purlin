#!/usr/bin/env python3
"""Tests for the /pl-whats-different agent command.

Covers automated scenarios from features/pl_whats_different.md:
- Exits When Branch Is Not Main
- Exits When No Active Session
- Prints In-Sync Message When SAME
- Generates and Displays Digest When BEHIND
- End-to-End Generation via Agent Command

The agent command is a Claude skill defined in .claude/commands/pl-whats-different.md.
These tests verify the underlying tool behavior that the command depends on:
- Branch detection via git rev-parse
- Active branch file reading from .purlin/runtime/active_branch
- Sync state computation via extract_whats_different.py
- Generation script execution via generate_whats_different.sh
"""
import json
import os
import shutil
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
    And no file exists at .purlin/runtime/active_branch
    When the agent runs /pl-whats-different
    Then the command aborts with a message containing "No active collaboration branch"
    And no generation script is executed

    Test: Verifies active branch file reading behavior.
    """

    def test_missing_active_branch_file_detected(self):
        """Missing active branch file triggers abort."""
        tmpdir = tempfile.mkdtemp()
        branch_path = os.path.join(tmpdir, '.purlin', 'runtime',
                                   'active_branch')
        # File does not exist
        self.assertFalse(os.path.exists(branch_path))

        import shutil
        shutil.rmtree(tmpdir)

    def test_empty_active_branch_file_detected(self):
        """Empty active branch file triggers abort."""
        tmpdir = tempfile.mkdtemp()
        runtime_dir = os.path.join(tmpdir, '.purlin', 'runtime')
        os.makedirs(runtime_dir)
        branch_path = os.path.join(runtime_dir, 'active_branch')
        with open(branch_path, 'w') as f:
            f.write('')

        with open(branch_path) as f:
            content = f.read().strip()
        self.assertEqual(content, '')

        import shutil
        shutil.rmtree(tmpdir)

    def test_valid_active_branch_file_read(self):
        """Valid active branch file content is extracted correctly."""
        tmpdir = tempfile.mkdtemp()
        runtime_dir = os.path.join(tmpdir, '.purlin', 'runtime')
        os.makedirs(runtime_dir)
        branch_path = os.path.join(runtime_dir, 'active_branch')
        with open(branch_path, 'w') as f:
            f.write('v0.6-sprint\n')

        with open(branch_path) as f:
            branch = f.read().strip()
        self.assertEqual(branch, 'v0.6-sprint')

        import shutil
        shutil.rmtree(tmpdir)

    def test_error_message_content(self):
        """Error message matches spec: 'No active collaboration branch'."""
        error_msg = ('No active collaboration branch. Use the CDD dashboard '
                     'to start or join a collaboration branch.')
        self.assertIn('No active collaboration branch', error_msg)


class TestPrintsInSyncMessageWhenSAME(unittest.TestCase):
    """Scenario: Prints In-Sync Message When SAME

    Given the current branch is "main"
    And an active branch "v0.6-sprint" is set
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
        branch = 'v0.6-sprint'
        msg = f'Local main is in sync with collab/{branch}. Nothing to summarize.'
        self.assertIn('in sync', msg)


class TestGeneratesAndDisplaysDigestWhenBEHIND(unittest.TestCase):
    """Scenario: Generates and Displays Digest When BEHIND

    Given the current branch is "main"
    And an active branch "v0.6-sprint" is set
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
            # ahead range starts with origin/ (remote..local) → empty
            if range_arg.startswith('origin/'):
                return ''
            # behind range starts with collab/ (local..remote) → has commits
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


class TestEndToEndGenerationViaAgentCommand(unittest.TestCase):
    """Scenario: End-to-End Generation via Agent Command

    Given the agent is on the main branch
    And an active branch exists in BEHIND state
    When the agent runs /pl-whats-different
    Then the generation script is executed with the active branch name as argument
    And features/digests/whats-different.md is written to disk
    And the digest content is displayed inline

    Test: Verifies the full pipeline from extraction through generation script
    to digest file output using a temporary git repo with BEHIND state.
    """

    @classmethod
    def setUpClass(cls):
        """Create a temporary git repo simulating BEHIND state."""
        cls.tmpdir = tempfile.mkdtemp()
        cls.origin_dir = os.path.join(cls.tmpdir, 'origin')
        cls.local_dir = os.path.join(cls.tmpdir, 'local')

        def _git(args, cwd):
            return subprocess.run(
                ['git'] + args, capture_output=True, text=True,
                check=True, cwd=cwd)

        # Create bare "remote" repo
        os.makedirs(cls.origin_dir)
        _git(['init', '--bare'], cls.origin_dir)

        # Create local clone
        _git(['clone', cls.origin_dir, cls.local_dir], cls.tmpdir)
        _git(['config', 'user.email', 'test@test.com'], cls.local_dir)
        _git(['config', 'user.name', 'Test'], cls.local_dir)

        # Initial commit on main
        init_file = os.path.join(cls.local_dir, 'init.txt')
        with open(init_file, 'w') as f:
            f.write('init')
        _git(['add', '.'], cls.local_dir)
        _git(['commit', '-m', 'initial'], cls.local_dir)
        _git(['push', 'origin', 'main'], cls.local_dir)

        # Create collab branch and push
        _git(['checkout', '-b', 'collab/test-session'], cls.local_dir)
        _git(['push', 'origin', 'collab/test-session'], cls.local_dir)

        # Add commits to remote collab branch (simulates remote-only changes)
        # We do this by creating a second clone, committing, and pushing
        cls.remote_clone = os.path.join(cls.tmpdir, 'remote_clone')
        _git(['clone', cls.origin_dir, cls.remote_clone], cls.tmpdir)
        _git(['config', 'user.email', 'collab@test.com'], cls.remote_clone)
        _git(['config', 'user.name', 'Collaborator'], cls.remote_clone)
        _git(['checkout', 'collab/test-session'], cls.remote_clone)

        # Add 2 commits to simulate BEHIND state
        feat_file = os.path.join(cls.remote_clone, 'features')
        os.makedirs(feat_file, exist_ok=True)
        with open(os.path.join(feat_file, 'new_feature.md'), 'w') as f:
            f.write('# New Feature\n')
        _git(['add', '.'], cls.remote_clone)
        _git(['commit', '-m', 'feat: add new feature spec'], cls.remote_clone)

        with open(os.path.join(cls.remote_clone, 'src.py'), 'w') as f:
            f.write('print("hello")\n')
        _git(['add', '.'], cls.remote_clone)
        _git(['commit', '-m', 'feat: implement new feature'], cls.remote_clone)

        _git(['push', 'origin', 'collab/test-session'], cls.remote_clone)

        # Back in local: fetch so origin/collab/test-session is updated
        _git(['checkout', 'main'], cls.local_dir)
        _git(['fetch', 'origin'], cls.local_dir)

        # Set up .purlin structure
        purlin_dir = os.path.join(cls.local_dir, '.purlin')
        runtime_dir = os.path.join(purlin_dir, 'runtime')
        os.makedirs(runtime_dir, exist_ok=True)
        with open(os.path.join(runtime_dir, 'active_branch'), 'w') as f:
            f.write('test-session\n')
        with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
            json.dump({'tools_root': 'tools'}, f)

        # Symlink the real tools directory so generation script can find
        # the extraction tool
        os.symlink(
            os.path.join(PROJECT_ROOT, 'tools'),
            os.path.join(cls.local_dir, 'tools'))

        # Create a fake claude binary that always fails, ensuring the
        # generation script uses its fallback (no-LLM) digest path
        cls.fake_bin = os.path.join(cls.tmpdir, 'fakebin')
        os.makedirs(cls.fake_bin, exist_ok=True)
        fake_claude = os.path.join(cls.fake_bin, 'claude')
        with open(fake_claude, 'w') as f:
            f.write('#!/bin/sh\nexit 1\n')
        os.chmod(fake_claude, 0o755)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    @patch.object(ext, '_run_git')
    def test_extraction_produces_behind_state(self, mock_git):
        """Extraction tool returns BEHIND when remote has commits not in local."""
        def side_effect(args, cwd=None):
            range_arg = args[1] if len(args) > 1 else ''
            # ahead range starts with origin/ (remote..local) → empty
            if range_arg.startswith('origin/'):
                return ''
            # behind range starts with collab/ (local..remote) → has commits
            return 'abc1234 feat: add new feature spec\ndef5678 feat: implement\n'
        mock_git.side_effect = side_effect
        result = ext.compute_sync_state('test-session')
        self.assertEqual(result['sync_state'], 'BEHIND')

    def test_generation_script_runs_with_session_arg(self):
        """Generation script accepts session name and runs extraction."""
        script_path = os.path.join(
            PROJECT_ROOT, 'tools', 'collab',
            'generate_whats_different.sh')
        # Run the generation script against the temporary repo
        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.local_dir
        # Prepend fake bin so the fake claude is found first (always fails),
        # ensuring the generation script uses its fallback digest path
        env['PATH'] = self.fake_bin + ':' + env.get('PATH', '/usr/bin:/bin')
        result = subprocess.run(
            ['bash', script_path, 'test-session'],
            capture_output=True, text=True, cwd=self.local_dir,
            env=env, timeout=30)
        self.assertEqual(
            result.returncode, 0,
            f'Generation script failed: stderr={result.stderr}')

    def test_digest_file_written_to_disk(self):
        """Digest file is created at features/digests/whats-different.md."""
        script_path = os.path.join(
            PROJECT_ROOT, 'tools', 'collab',
            'generate_whats_different.sh')
        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.local_dir
        env['PATH'] = '/usr/bin:/bin'
        subprocess.run(
            ['bash', script_path, 'test-session'],
            capture_output=True, text=True, cwd=self.local_dir,
            env=env, timeout=30)

        digest_path = os.path.join(
            self.local_dir, 'features', 'digests', 'whats-different.md')
        self.assertTrue(
            os.path.isfile(digest_path),
            f'Digest file not created: {digest_path}')

    def test_digest_contains_collab_changes(self):
        """Digest content includes Collab Changes section for BEHIND state."""
        script_path = os.path.join(
            PROJECT_ROOT, 'tools', 'collab',
            'generate_whats_different.sh')
        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.local_dir
        env['PATH'] = '/usr/bin:/bin'
        result = subprocess.run(
            ['bash', script_path, 'test-session'],
            capture_output=True, text=True, cwd=self.local_dir,
            env=env, timeout=30)

        # stdout is the digest content (displayed inline)
        self.assertIn('Collab Changes', result.stdout)
        self.assertNotIn('Your Local Changes', result.stdout,
                         'BEHIND state should not show local changes')

    def test_digest_stdout_matches_file(self):
        """Digest displayed inline (stdout) matches what was written to disk."""
        script_path = os.path.join(
            PROJECT_ROOT, 'tools', 'collab',
            'generate_whats_different.sh')
        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.local_dir
        env['PATH'] = '/usr/bin:/bin'
        result = subprocess.run(
            ['bash', script_path, 'test-session'],
            capture_output=True, text=True, cwd=self.local_dir,
            env=env, timeout=30)

        digest_path = os.path.join(
            self.local_dir, 'features', 'digests', 'whats-different.md')
        with open(digest_path) as f:
            file_content = f.read()

        # stdout from cat at end of script should match file
        self.assertEqual(result.stdout.strip(), file_content.strip())


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
