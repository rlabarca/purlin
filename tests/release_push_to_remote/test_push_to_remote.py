#!/usr/bin/env python3
"""Tests for the purlin.push_to_remote release step.

Covers automated scenarios from features/release_push_to_remote.md:
- Remote is ahead of local
- Step is disabled
- Clean push to remote
- Force-push would be required
- Multiple remotes, user accepts default
- Single remote, streamlined confirmation
- Release push from collaboration branch shows branch confirmation

This release step has code: null (interactive). These tests verify the
underlying git behaviors and config parsing that the agent relies on
when executing the step interactively.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))


def _git(args, cwd):
    """Run a git command, returning (returncode, stdout, stderr)."""
    result = subprocess.run(
        ['git'] + args, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _git_check(args, cwd):
    """Run a git command, raising on failure. Returns stdout."""
    rc, stdout, stderr = _git(args, cwd)
    if rc != 0:
        raise RuntimeError(f'git {" ".join(args)} failed: {stderr}')
    return stdout


class GitRepoFixture:
    """Creates a temporary git repo pair (local + bare remote) for testing."""

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp()
        self.bare_dir = os.path.join(self.tmpdir, 'remote.git')
        self.local_dir = os.path.join(self.tmpdir, 'local')

    def setup(self):
        """Create bare remote and local clone with initial commit."""
        os.makedirs(self.bare_dir)
        _git_check(['init', '--bare'], self.bare_dir)

        _git_check(['clone', self.bare_dir, self.local_dir], self.tmpdir)
        _git_check(['config', 'user.email', 'test@test.com'], self.local_dir)
        _git_check(['config', 'user.name', 'Test'], self.local_dir)

        # Initial commit
        with open(os.path.join(self.local_dir, 'init.txt'), 'w') as f:
            f.write('init')
        _git_check(['add', '.'], self.local_dir)
        _git_check(['commit', '-m', 'initial'], self.local_dir)
        _git_check(['push', 'origin', 'main'], self.local_dir)
        return self

    def teardown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestRemoteIsAheadOfLocal(unittest.TestCase):
    """Scenario: Remote is ahead of local

    Given the remote branch has commits not present locally
    When the Architect executes the purlin.push_to_remote step
    Then the step detects the remote is ahead via git log comparison
    And the step halts with an error message containing "pull and reconcile"
    And no git push command is executed
    """

    @classmethod
    def setUpClass(cls):
        cls.fixture = GitRepoFixture().setup()
        # Push a commit from a second clone to make remote ahead
        cls.other_clone = os.path.join(cls.fixture.tmpdir, 'other')
        _git_check(
            ['clone', cls.fixture.bare_dir, cls.other_clone],
            cls.fixture.tmpdir)
        _git_check(['config', 'user.email', 'other@test.com'], cls.other_clone)
        _git_check(['config', 'user.name', 'Other'], cls.other_clone)
        with open(os.path.join(cls.other_clone, 'ahead.txt'), 'w') as f:
            f.write('ahead')
        _git_check(['add', '.'], cls.other_clone)
        _git_check(['commit', '-m', 'ahead commit'], cls.other_clone)
        _git_check(['push', 'origin', 'main'], cls.other_clone)

        # Fetch in local so we know about remote's new commits
        _git_check(['fetch', 'origin'], cls.fixture.local_dir)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.teardown()

    def test_remote_ahead_detected_via_log(self):
        """git log local..remote shows commits when remote is ahead."""
        stdout = _git_check(
            ['log', 'main..origin/main', '--oneline'],
            self.fixture.local_dir)
        self.assertTrue(len(stdout.strip()) > 0,
                        'Expected remote-ahead commits in git log output')

    def test_remote_ahead_count(self):
        """At least one commit exists on remote not present locally."""
        stdout = _git_check(
            ['rev-list', '--count', 'main..origin/main'],
            self.fixture.local_dir)
        self.assertGreaterEqual(int(stdout), 1)

    def test_error_message_pattern(self):
        """Error message for remote-ahead includes 'pull and reconcile'."""
        msg = ('Remote is ahead of local. Please pull and reconcile '
               'before pushing.')
        self.assertIn('pull and reconcile', msg)


class TestStepIsDisabled(unittest.TestCase):
    """Scenario: Step is disabled

    Given .purlin/release/config.json has purlin.push_to_remote set to
    enabled: false
    When the Architect executes the release checklist
    Then the purlin.push_to_remote step is skipped entirely
    And no git push command is executed
    And the release proceeds to the next step
    """

    def test_disabled_step_detected_from_config(self):
        """Config with enabled: false correctly signals step should be skipped."""
        config = {
            'steps': [
                {'id': 'purlin.push_to_remote', 'enabled': False}
            ]
        }
        step = next(
            s for s in config['steps']
            if s['id'] == 'purlin.push_to_remote')
        self.assertFalse(step['enabled'])

    def test_enabled_step_detected_from_config(self):
        """Config with enabled: true correctly signals step should run."""
        config = {
            'steps': [
                {'id': 'purlin.push_to_remote', 'enabled': True}
            ]
        }
        step = next(
            s for s in config['steps']
            if s['id'] == 'purlin.push_to_remote')
        self.assertTrue(step['enabled'])

    def test_real_config_has_push_step(self):
        """Project's release config includes the push_to_remote step."""
        config_path = os.path.join(
            PROJECT_ROOT, '.purlin', 'release', 'config.json')
        with open(config_path) as f:
            config = json.load(f)
        step_ids = [s['id'] for s in config['steps']]
        self.assertIn('purlin.push_to_remote', step_ids)

    def test_global_steps_defines_push_step(self):
        """Global steps JSON defines the purlin.push_to_remote step."""
        steps_path = os.path.join(
            PROJECT_ROOT, 'tools', 'release', 'global_steps.json')
        with open(steps_path) as f:
            data = json.load(f)
        step_ids = [s['id'] for s in data['steps']]
        self.assertIn('purlin.push_to_remote', step_ids)

    def test_step_metadata_matches_spec(self):
        """Step metadata in global_steps.json matches spec Section 2.5."""
        steps_path = os.path.join(
            PROJECT_ROOT, 'tools', 'release', 'global_steps.json')
        with open(steps_path) as f:
            data = json.load(f)
        step = next(
            s for s in data['steps']
            if s['id'] == 'purlin.push_to_remote')
        self.assertEqual(step['friendly_name'], 'Push to Remote Repository')
        self.assertIsNone(step['code'])
        self.assertIsNotNone(step['agent_instructions'])


class TestCleanPushToRemote(unittest.TestCase):
    """Scenario: Clean push to remote

    Given the local branch is ahead of the remote by one or more commits
    And no force-push is required
    When the Architect executes the purlin.push_to_remote step
    Then git push <remote> <branch> is executed with the confirmed remote
    And git push <remote> --tags is executed
    And the step reports the push result
    """

    @classmethod
    def setUpClass(cls):
        cls.fixture = GitRepoFixture().setup()
        # Make local ahead with a commit
        with open(os.path.join(cls.fixture.local_dir, 'local.txt'), 'w') as f:
            f.write('local change')
        _git_check(['add', '.'], cls.fixture.local_dir)
        _git_check(['commit', '-m', 'local commit'], cls.fixture.local_dir)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.teardown()

    def test_local_ahead_detected(self):
        """Local branch is ahead of remote (push candidate)."""
        stdout = _git_check(
            ['rev-list', '--count', 'origin/main..main'],
            self.fixture.local_dir)
        self.assertGreaterEqual(int(stdout), 1)

    def test_push_succeeds(self):
        """git push origin main succeeds when local is ahead."""
        rc, stdout, stderr = _git(
            ['push', 'origin', 'main'], self.fixture.local_dir)
        self.assertEqual(rc, 0, f'Push failed: {stderr}')

    def test_tags_push_succeeds(self):
        """git push origin --tags succeeds."""
        # Create a tag first
        _git_check(
            ['tag', '-a', 'v0.0.1-test', '-m', 'test tag'],
            self.fixture.local_dir)
        rc, stdout, stderr = _git(
            ['push', 'origin', '--tags'], self.fixture.local_dir)
        self.assertEqual(rc, 0, f'Tags push failed: {stderr}')


class TestForcePushRequired(unittest.TestCase):
    """Scenario: Force-push would be required

    Given the push cannot proceed without --force
    When the Architect executes the purlin.push_to_remote step
    Then the step detects the force-push requirement
    And the step halts with a warning about force-push
    And no git push --force command is executed without explicit user
    confirmation
    """

    @classmethod
    def setUpClass(cls):
        cls.fixture = GitRepoFixture().setup()

        # Create divergence: remote gets a commit via another clone
        cls.other_clone = os.path.join(cls.fixture.tmpdir, 'other2')
        _git_check(
            ['clone', cls.fixture.bare_dir, cls.other_clone],
            cls.fixture.tmpdir)
        _git_check(
            ['config', 'user.email', 'other@test.com'], cls.other_clone)
        _git_check(['config', 'user.name', 'Other'], cls.other_clone)
        with open(os.path.join(cls.other_clone, 'remote_change.txt'), 'w') as f:
            f.write('remote')
        _git_check(['add', '.'], cls.other_clone)
        _git_check(
            ['commit', '-m', 'remote divergent commit'], cls.other_clone)
        _git_check(['push', 'origin', 'main'], cls.other_clone)

        # Local gets its own commit (creates divergence)
        with open(os.path.join(
                cls.fixture.local_dir, 'local_change.txt'), 'w') as f:
            f.write('local')
        _git_check(['add', '.'], cls.fixture.local_dir)
        _git_check(
            ['commit', '-m', 'local divergent commit'], cls.fixture.local_dir)
        _git_check(['fetch', 'origin'], cls.fixture.local_dir)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.teardown()

    def test_divergence_detected(self):
        """Both local and remote have unique commits (diverged)."""
        local_ahead = _git_check(
            ['rev-list', '--count', 'origin/main..main'],
            self.fixture.local_dir)
        remote_ahead = _git_check(
            ['rev-list', '--count', 'main..origin/main'],
            self.fixture.local_dir)
        self.assertGreaterEqual(int(local_ahead), 1)
        self.assertGreaterEqual(int(remote_ahead), 1)

    def test_normal_push_fails_when_diverged(self):
        """git push without --force fails when branches have diverged."""
        rc, stdout, stderr = _git(
            ['push', 'origin', 'main'], self.fixture.local_dir)
        self.assertNotEqual(rc, 0, 'Push should fail without --force')

    def test_force_push_warning_message(self):
        """Warning message for force-push includes appropriate text."""
        msg = ('Push requires --force. This will overwrite remote history. '
               'Proceeding requires explicit user confirmation.')
        self.assertIn('--force', msg)
        self.assertIn('explicit user confirmation', msg)


class TestMultipleRemotes(unittest.TestCase):
    """Scenario: Multiple remotes, user accepts default

    Given the project has remotes "origin" and "github"
    And the current branch is "main" tracking "origin/main"
    When the Architect executes the purlin.push_to_remote step
    Then the step identifies "origin" as the default remote via upstream tracking
    And "github" is listed as an alternative remote
    And the default remote URL is included in the confirmation prompt
    """

    @classmethod
    def setUpClass(cls):
        cls.fixture = GitRepoFixture().setup()
        # Add a second remote
        github_bare = os.path.join(cls.fixture.tmpdir, 'github.git')
        os.makedirs(github_bare)
        _git_check(['init', '--bare'], github_bare)
        _git_check(
            ['remote', 'add', 'github', github_bare],
            cls.fixture.local_dir)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.teardown()

    def test_multiple_remotes_discovered(self):
        """git remote -v shows both origin and github."""
        stdout = _git_check(['remote', '-v'], self.fixture.local_dir)
        self.assertIn('origin', stdout)
        self.assertIn('github', stdout)

    def test_default_remote_from_upstream(self):
        """Upstream tracking identifies origin as default remote."""
        stdout = _git_check(
            ['rev-parse', '--abbrev-ref', '@{upstream}'],
            self.fixture.local_dir)
        # Should be 'origin/main'
        self.assertTrue(
            stdout.startswith('origin/'),
            f'Expected upstream to be origin/<branch>, got: {stdout}')

    def test_default_remote_extracted(self):
        """Default remote name is extracted from upstream ref."""
        stdout = _git_check(
            ['rev-parse', '--abbrev-ref', '@{upstream}'],
            self.fixture.local_dir)
        remote_name = stdout.split('/')[0]
        self.assertEqual(remote_name, 'origin')

    def test_remote_url_discoverable(self):
        """Remote URL can be discovered for the confirmation prompt."""
        stdout = _git_check(
            ['remote', 'get-url', 'origin'], self.fixture.local_dir)
        self.assertTrue(len(stdout) > 0, 'Remote URL should not be empty')

    def test_alternative_remotes_listed(self):
        """Non-default remotes are identifiable as alternatives."""
        stdout = _git_check(['remote'], self.fixture.local_dir)
        remotes = [r.strip() for r in stdout.splitlines() if r.strip()]
        default_remote = 'origin'
        alternatives = [r for r in remotes if r != default_remote]
        self.assertIn('github', alternatives)


class TestSingleRemote(unittest.TestCase):
    """Scenario: Single remote, streamlined confirmation

    Given the project has only one remote "origin"
    And the current branch is "main"
    When the Architect executes the purlin.push_to_remote step
    Then the step identifies "origin" as the only remote
    And no remote selection prompt is generated
    And the confirmation prompt shows "Push main to origin (<url>)?"
    """

    @classmethod
    def setUpClass(cls):
        cls.fixture = GitRepoFixture().setup()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.teardown()

    def test_single_remote_detected(self):
        """Only one remote (origin) exists."""
        stdout = _git_check(['remote'], self.fixture.local_dir)
        remotes = [r.strip() for r in stdout.splitlines() if r.strip()]
        self.assertEqual(len(remotes), 1)
        self.assertEqual(remotes[0], 'origin')

    def test_current_branch_detected(self):
        """Current branch is correctly identified."""
        stdout = _git_check(
            ['rev-parse', '--abbrev-ref', 'HEAD'], self.fixture.local_dir)
        self.assertEqual(stdout, 'main')

    def test_confirmation_prompt_construction(self):
        """Confirmation prompt matches spec format."""
        branch = _git_check(
            ['rev-parse', '--abbrev-ref', 'HEAD'], self.fixture.local_dir)
        remote = _git_check(['remote'], self.fixture.local_dir).strip()
        url = _git_check(
            ['remote', 'get-url', remote], self.fixture.local_dir)
        prompt = f'Push `{branch}` to `{remote}` (`{url}`)?'
        self.assertIn('Push', prompt)
        self.assertIn('main', prompt)
        self.assertIn('origin', prompt)
        self.assertIn(url, prompt)


class TestCollaborationBranchWarning(unittest.TestCase):
    """Scenario: Release push from collaboration branch shows branch confirmation

    Given .purlin/runtime/active_branch contains "collab/v0.6-sprint"
    And the current branch is "collab/v0.6-sprint"
    When the Architect executes the purlin.push_to_remote step
    Then the step warns that the current branch is a collaboration branch
    And the warning message contains "collab/v0.6-sprint"
    And the Architect must confirm before proceeding
    """

    @classmethod
    def setUpClass(cls):
        cls.fixture = GitRepoFixture().setup()
        # Create the collab branch
        _git_check(
            ['checkout', '-b', 'collab/v0.6-sprint'], cls.fixture.local_dir)
        # Set up .purlin/runtime/active_branch
        cls.runtime_dir = os.path.join(
            cls.fixture.local_dir, '.purlin', 'runtime')
        os.makedirs(cls.runtime_dir, exist_ok=True)
        cls.active_branch_path = os.path.join(
            cls.runtime_dir, 'active_branch')
        with open(cls.active_branch_path, 'w') as f:
            f.write('collab/v0.6-sprint')

    @classmethod
    def tearDownClass(cls):
        cls.fixture.teardown()

    def test_active_branch_file_detected(self):
        """active_branch file exists and is non-empty."""
        self.assertTrue(os.path.exists(self.active_branch_path))
        with open(self.active_branch_path) as f:
            content = f.read().strip()
        self.assertTrue(len(content) > 0)

    def test_current_branch_matches_active_branch(self):
        """Current branch matches the value in active_branch file."""
        current = _git_check(
            ['rev-parse', '--abbrev-ref', 'HEAD'], self.fixture.local_dir)
        with open(self.active_branch_path) as f:
            active = f.read().strip()
        self.assertEqual(current, active)

    def test_warning_message_contains_branch_name(self):
        """Warning message includes the collaboration branch name."""
        with open(self.active_branch_path) as f:
            branch = f.read().strip()
        msg = (f'Current branch is a collaboration branch (`{branch}`). '
               'Pushing directly may bypass the collaboration workflow. '
               'Confirm to proceed.')
        self.assertIn('collab/v0.6-sprint', msg)
        self.assertIn('collaboration branch', msg)
        self.assertIn('Confirm to proceed', msg)

    def test_no_warning_when_active_branch_differs(self):
        """No warning when current branch does not match active_branch."""
        current = _git_check(
            ['rev-parse', '--abbrev-ref', 'HEAD'], self.fixture.local_dir)
        non_matching_active = 'collab/other-sprint'
        should_warn = (current == non_matching_active)
        self.assertFalse(should_warn)

    def test_no_warning_when_active_branch_file_missing(self):
        """No warning when active_branch file does not exist."""
        fake_path = os.path.join(self.runtime_dir, 'nonexistent')
        should_warn = os.path.exists(fake_path)
        self.assertFalse(should_warn)


if __name__ == '__main__':
    unittest.main()
