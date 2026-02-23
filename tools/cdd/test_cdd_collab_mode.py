"""Unit tests for CDD Collab Mode.

Covers automated scenarios from features/cdd_collab_mode.md.
Outputs test results to tests/cdd_collab_mode/tests.json.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import io
import json
import sys
import tempfile
import shutil
import subprocess
import http.server

from serve import (
    _detect_worktrees,
    _role_from_branch,
    _worktree_state,
    _compute_main_diff,
    _collab_section_html,
    get_collab_worktrees,
    get_git_status,
    generate_api_status_json,
    generate_workspace_json,
    Handler,
    PROJECT_ROOT,
    TOOLS_ROOT,
)


class TestRoleFromBranch(unittest.TestCase):
    """Test role mapping from branch prefix (Scenario: Role Mapped)."""

    def test_spec_maps_to_architect(self):
        self.assertEqual(_role_from_branch('spec/task-crud'), 'architect')

    def test_build_maps_to_builder(self):
        self.assertEqual(_role_from_branch('build/task-crud'), 'builder')

    def test_qa_maps_to_qa(self):
        self.assertEqual(_role_from_branch('qa/task-crud'), 'qa')

    def test_unknown_prefix(self):
        self.assertEqual(_role_from_branch('hotfix/urgent-fix'), 'unknown')

    def test_no_slash(self):
        self.assertEqual(_role_from_branch('main'), 'unknown')


class TestDetectWorktrees(unittest.TestCase):
    """Test worktree detection from git worktree list --porcelain."""

    @patch('serve.run_command')
    def test_no_worktrees(self, mock_cmd):
        """Scenario: Collab Mode Inactive When No Worktrees."""
        # git worktree list --porcelain with only main checkout
        mock_cmd.return_value = (
            f"worktree {PROJECT_ROOT}\n"
            "HEAD abc123\n"
            "branch refs/heads/main\n"
        )
        result = _detect_worktrees()
        self.assertEqual(result, [])

    @patch('serve.run_command')
    def test_detects_worktrees_under_dotworktrees(self, mock_cmd):
        """Scenario: Collab Mode Active When Worktrees Detected."""
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'architect-session')
        mock_cmd.return_value = (
            f"worktree {PROJECT_ROOT}\n"
            "HEAD abc123\n"
            "branch refs/heads/main\n"
            "\n"
            f"worktree {wt_path}\n"
            "HEAD def456\n"
            "branch refs/heads/spec/task-crud\n"
        )
        result = _detect_worktrees()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['abs_path'], wt_path)

    @patch('serve.run_command')
    def test_ignores_worktrees_outside_dotworktrees(self, mock_cmd):
        """Worktrees not under .worktrees/ are ignored."""
        other_path = os.path.join(PROJECT_ROOT, 'other', 'worktree')
        mock_cmd.return_value = (
            f"worktree {PROJECT_ROOT}\n"
            "HEAD abc123\n"
            "branch refs/heads/main\n"
            "\n"
            f"worktree {other_path}\n"
            "HEAD def456\n"
            "branch refs/heads/feature/x\n"
        )
        result = _detect_worktrees()
        self.assertEqual(result, [])


class TestCollabModeInactive(unittest.TestCase):
    """Scenario: Collab Mode Inactive When No Worktrees."""

    @patch('serve.get_collab_worktrees', return_value=[])
    @patch('serve.build_status_commit_cache', return_value={})
    def test_status_json_no_collab(self, mock_cache, mock_collab):
        result = generate_api_status_json()
        self.assertNotIn('collab_mode', result)
        self.assertNotIn('worktrees', result)

    @patch('serve.get_collab_worktrees', return_value=[])
    @patch('serve.get_git_status', return_value='')
    @patch('serve.get_last_commit', return_value='abc1234 initial (just now)')
    def test_workspace_json_no_collab(self, mock_commit, mock_status,
                                      mock_collab):
        result = generate_workspace_json()
        self.assertNotIn('collab_mode', result)
        self.assertNotIn('worktrees', result)


class TestCollabModeActive(unittest.TestCase):
    """Scenario: Collab Mode Active When Worktrees Detected."""

    MOCK_WORKTREES = [{
        'path': '.worktrees/architect-session',
        'branch': 'spec/collab',
        'role': 'architect',
        'main_diff': 'SAME',
        'commits_ahead': 0,
        'last_commit': 'abc1234 feat(spec): add scenarios (45 min ago)',
        'modified': {'specs': 0, 'tests': 0, 'other': 0},
    }]

    @patch('serve.get_collab_worktrees')
    @patch('serve.build_status_commit_cache', return_value={})
    def test_status_json_has_collab(self, mock_cache, mock_collab):
        mock_collab.return_value = self.MOCK_WORKTREES
        result = generate_api_status_json()
        self.assertTrue(result.get('collab_mode'))
        self.assertEqual(len(result['worktrees']), 1)
        wt = result['worktrees'][0]
        self.assertEqual(wt['path'], '.worktrees/architect-session')
        self.assertEqual(wt['branch'], 'spec/collab')
        self.assertEqual(wt['role'], 'architect')


class TestRoleMappedFromBranchPrefix(unittest.TestCase):
    """Scenario: Role Mapped from Branch Prefix.

    Given worktrees on branches spec/feature-a, build/feature-a, qa/feature-a
    Then the worktrees array contains entries with roles architect, builder, qa.
    """

    @patch('serve._compute_main_diff', return_value='SAME')
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_three_roles_mapped(self, mock_detect, mock_state, mock_diff):
        wt_base = os.path.join(PROJECT_ROOT, '.worktrees')
        mock_detect.return_value = [
            {'abs_path': os.path.join(wt_base, 'architect-session'),
             'branch_ref': 'refs/heads/spec/feature-a'},
            {'abs_path': os.path.join(wt_base, 'build-session'),
             'branch_ref': 'refs/heads/build/feature-a'},
            {'abs_path': os.path.join(wt_base, 'qa-session'),
             'branch_ref': 'refs/heads/qa/feature-a'},
        ]
        mock_state.side_effect = [
            {'branch': 'spec/feature-a',
             'modified': {'specs': 0, 'tests': 0, 'other': 0},
             'last_commit': 'abc spec', 'commits_ahead': 0},
            {'branch': 'build/feature-a',
             'modified': {'specs': 0, 'tests': 0, 'other': 0},
             'last_commit': 'def build', 'commits_ahead': 0},
            {'branch': 'qa/feature-a',
             'modified': {'specs': 0, 'tests': 0, 'other': 0},
             'last_commit': 'ghi qa', 'commits_ahead': 0},
        ]
        result = get_collab_worktrees()
        roles = [wt['role'] for wt in result]
        self.assertIn('architect', roles)
        self.assertIn('builder', roles)
        self.assertIn('qa', roles)


class TestUnknownRoleForNonStandardBranch(unittest.TestCase):
    """Scenario: Unknown Role for Non-Standard Branch."""

    @patch('serve._compute_main_diff', return_value='SAME')
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_hotfix_maps_to_unknown(self, mock_detect, mock_state, mock_diff):
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'hotfix-session')
        mock_detect.return_value = [
            {'abs_path': wt_path,
             'branch_ref': 'refs/heads/hotfix/urgent-fix'},
        ]
        mock_state.return_value = {
            'branch': 'hotfix/urgent-fix',
            'modified': {'specs': 0, 'tests': 0, 'other': 0},
            'last_commit': 'xyz hotfix', 'commits_ahead': 0,
        }
        result = get_collab_worktrees()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['role'], 'unknown')


class TestModifiedColumnCategorization(unittest.TestCase):
    """Scenario: Modified Column Categorizes Uncommitted Files by Type.

    Given a worktree has two modified files under features/
    And one modified file outside features/ and tests/
    Then the modified field has specs=2, tests=0, other=1.
    """

    @patch('serve._compute_main_diff', return_value='SAME')
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_modified_categorized(self, mock_detect, mock_state, mock_diff):
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'architect-session')
        mock_detect.return_value = [
            {'abs_path': wt_path,
             'branch_ref': 'refs/heads/spec/collab'},
        ]
        mock_state.return_value = {
            'branch': 'spec/collab',
            'modified': {'specs': 2, 'tests': 0, 'other': 1},
            'last_commit': 'abc spec', 'commits_ahead': 0,
        }
        result = get_collab_worktrees()
        self.assertEqual(len(result), 1)
        mod = result[0]['modified']
        self.assertEqual(mod['specs'], 2)
        self.assertEqual(mod['tests'], 0)
        self.assertEqual(mod['other'], 1)


class TestWorktreeStateFileCategories(unittest.TestCase):
    """Test _worktree_state() parses git status --porcelain into categories."""

    def _mock_subprocess(self, responses):
        """Create mock for subprocess.run returning CompletedProcess-like objects.

        _worktree_state calls subprocess.run 4 times:
          0: git rev-parse --abbrev-ref HEAD (via _wt_cmd, .strip())
          1: git status --porcelain (direct, raw stdout)
          2: git log -1 (via _wt_cmd, .strip())
          3: git rev-list --count (via _wt_cmd, .strip())
        """
        call_count = [0]

        def _side_effect(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(responses):
                return subprocess.CompletedProcess(
                    args='mock', returncode=0, stdout=responses[idx], stderr='')
            raise Exception(f"Unexpected subprocess.run call {idx}")

        return _side_effect

    @patch('subprocess.run')
    def test_categorizes_by_path_prefix(self, mock_run):
        """Files under features/ count as specs, tests/ as tests, rest as other."""
        mock_run.side_effect = self._mock_subprocess([
            'spec/collab',    # git rev-parse (via _wt_cmd)
            ' M features/foo.md\n M features/bar.md\n M tools/thing.py\n',  # git status (raw)
            'abc1234 commit (5m ago)',  # git log (via _wt_cmd)
            '2',              # git rev-list (via _wt_cmd)
        ])
        state = _worktree_state('/tmp/fake-wt')
        self.assertEqual(state['modified'], {'specs': 2, 'tests': 0, 'other': 1})
        self.assertEqual(state['commits_ahead'], 2)

    @patch('subprocess.run')
    def test_clean_worktree(self, mock_run):
        """Clean worktree has all zeros in modified."""
        mock_run.side_effect = self._mock_subprocess([
            'build/collab',   # branch (via _wt_cmd)
            '',               # git status (raw, clean)
            'def5678 commit (3m ago)',  # git log (via _wt_cmd)
            '0',              # commits ahead (via _wt_cmd)
        ])
        state = _worktree_state('/tmp/fake-wt')
        self.assertEqual(state['modified'], {'specs': 0, 'tests': 0, 'other': 0})

    @patch('subprocess.run')
    def test_tests_directory_counted(self, mock_run):
        """Files under tests/ count in the tests category."""
        mock_run.side_effect = self._mock_subprocess([
            'qa/collab',     # branch (via _wt_cmd)
            ' M tests/foo/tests.json\nA  tests/bar/critic.json\n',  # git status (raw)
            'ghi9012 commit (1m ago)',  # git log (via _wt_cmd)
            '1',             # commits ahead (via _wt_cmd)
        ])
        state = _worktree_state('/tmp/fake-wt')
        self.assertEqual(state['modified']['tests'], 2)
        self.assertEqual(state['modified']['specs'], 0)
        self.assertEqual(state['modified']['other'], 0)


class TestCommitsAheadReported(unittest.TestCase):
    """Scenario: Commits Ahead Reported When Worktree Branch Is Ahead Of Main.

    Given a worktree has 3 commits not yet merged to main
    Then the worktree entry has commits_ahead equal to 3.
    """

    @patch('serve._compute_main_diff', return_value='SAME')
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_commits_ahead(self, mock_detect, mock_state, mock_diff):
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'builder-session')
        mock_detect.return_value = [
            {'abs_path': wt_path,
             'branch_ref': 'refs/heads/build/collab'},
        ]
        mock_state.return_value = {
            'branch': 'build/collab',
            'modified': {'specs': 0, 'tests': 0, 'other': 0},
            'last_commit': 'def5678 feat(build): handlers (12 min ago)',
            'commits_ahead': 3,
        }
        result = get_collab_worktrees()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['commits_ahead'], 3)


class TestMainDiffBehind(unittest.TestCase):
    """Scenario: Main Diff BEHIND When Worktree Branch Is Missing Main Commits.

    Given main has commits that are not in spec/collab
    Then the worktree entry has main_diff "BEHIND".
    """

    @patch('subprocess.run')
    def test_behind_when_main_has_extra_commits(self, mock_run):
        """_compute_main_diff returns BEHIND when git log shows output."""
        mock_run.return_value = MagicMock(
            stdout='abc1234 some commit on main\n', returncode=0)
        result = _compute_main_diff('spec/collab')
        self.assertEqual(result, 'BEHIND')

    @patch('serve._compute_main_diff', return_value='BEHIND')
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_behind_in_worktree_entry(self, mock_detect, mock_state, mock_diff):
        """Worktree entry surfaces main_diff BEHIND."""
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'architect-session')
        mock_detect.return_value = [
            {'abs_path': wt_path,
             'branch_ref': 'refs/heads/spec/collab'},
        ]
        mock_state.return_value = {
            'branch': 'spec/collab',
            'modified': {'specs': 2, 'tests': 0, 'other': 1},
            'last_commit': 'abc spec', 'commits_ahead': 0,
        }
        result = get_collab_worktrees()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['main_diff'], 'BEHIND')


class TestMainDiffSame(unittest.TestCase):
    """Scenario: Main Diff SAME When Worktree Branch Has All Main Commits.

    Given build/collab has all commits that are in main
    Then the worktree entry has main_diff "SAME".
    """

    @patch('subprocess.run')
    def test_same_when_no_missing_commits(self, mock_run):
        """_compute_main_diff returns SAME when git log output is empty."""
        mock_run.return_value = MagicMock(stdout='', returncode=0)
        result = _compute_main_diff('build/collab')
        self.assertEqual(result, 'SAME')

    @patch('subprocess.run')
    def test_same_on_git_error(self, mock_run):
        """_compute_main_diff defaults to SAME on git errors."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git')
        result = _compute_main_diff('nonexistent/branch')
        self.assertEqual(result, 'SAME')


class TestStartCollabEndpoint(unittest.TestCase):
    """Scenario: Start Collab Creates Worktrees via Dashboard."""

    def _make_handler(self):
        """Create a mock Handler for POST /start-collab."""
        handler = MagicMock(spec=Handler)
        handler.path = '/start-collab'
        handler._send_json = MagicMock()
        # Bind the real method
        handler._handle_start_collab = Handler._handle_start_collab.__get__(
            handler, Handler)
        return handler

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_start_collab_success(self, mock_exists, mock_run):
        """POST /start-collab (empty body) creates worktrees."""
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        handler = self._make_handler()
        handler._handle_start_collab()
        handler._send_json.assert_called_once_with(200, {'status': 'ok'})
        # Verify --feature is not passed to the script
        call_args = mock_run.call_args[0][0]
        self.assertNotIn('--feature', call_args)

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_start_collab_script_error(self, mock_exists, mock_run):
        """POST /start-collab propagates script errors."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'bash', stderr='not gitignored')
        handler = self._make_handler()
        handler._handle_start_collab()
        handler._send_json.assert_called_once()
        args = handler._send_json.call_args
        self.assertEqual(args[0][0], 500)
        self.assertIn('not gitignored', args[0][1]['error'])


class TestEndCollabEndpoint(unittest.TestCase):
    """Scenario: End Collab Removes Worktrees via Dashboard."""

    def _make_handler(self, body_dict):
        """Create a mock Handler for POST /end-collab."""
        handler = MagicMock(spec=Handler)
        handler.path = '/end-collab'
        handler.headers = {'Content-Length': str(len(json.dumps(body_dict)))}
        handler.rfile = io.BytesIO(json.dumps(body_dict).encode('utf-8'))
        handler._send_json = MagicMock()
        handler._handle_end_collab = Handler._handle_end_collab.__get__(
            handler, Handler)
        return handler

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_end_collab_dry_run(self, mock_exists, mock_run):
        """POST /end-collab dry_run returns safety JSON."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"dirty_count":0,"dirty_worktrees":[],"unsynced_count":0,"unsynced_worktrees":[]}',
            stderr='')
        handler = self._make_handler({'dry_run': True})
        handler._handle_end_collab()
        handler._send_json.assert_called_once()
        args = handler._send_json.call_args
        self.assertEqual(args[0][0], 200)
        self.assertEqual(args[0][1]['dirty_count'], 0)

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_end_collab_force_success(self, mock_exists, mock_run):
        """POST /end-collab force removes worktrees."""
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        handler = self._make_handler({'force': True})
        handler._handle_end_collab()
        handler._send_json.assert_called_once_with(200, {'status': 'ok'})

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_end_collab_dirty_blocks(self, mock_exists, mock_run):
        """POST /end-collab without force fails when dirty."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='Error: Worktrees have uncommitted changes.')
        handler = self._make_handler({})
        handler._handle_end_collab()
        handler._send_json.assert_called_once()
        args = handler._send_json.call_args
        self.assertEqual(args[0][0], 500)
        self.assertIn('uncommitted', args[0][1]['error'])


class TestAgentConfigPropagation(unittest.TestCase):
    """Scenario: Agent Config Save Propagates to All Active Worktrees.

    Given collab mode is active with two worktrees,
    When a POST request is sent to /config/agents with updated values,
    Then the project root and all worktree configs reflect the new values.
    """

    def test_config_propagated_to_worktrees(self):
        """Config save writes to project root and all active worktree paths."""
        with tempfile.TemporaryDirectory() as td:
            # Setup project root config
            purlin_dir = os.path.join(td, '.purlin')
            os.makedirs(purlin_dir)
            config = {
                'models': [{'id': 'claude-opus-4-6', 'label': 'Opus'}],
                'agents': {
                    'architect': {'model': 'claude-opus-4-6', 'effort': 'high',
                                  'bypass_permissions': True,
                                  'startup_sequence': True,
                                  'recommend_next_actions': True},
                }
            }
            config_path = os.path.join(purlin_dir, 'config.json')
            with open(config_path, 'w') as f:
                json.dump(config, f)

            # Setup two worktree config dirs
            for wt_name in ('architect-session', 'builder-session'):
                wt_purlin = os.path.join(td, '.worktrees', wt_name, '.purlin')
                os.makedirs(wt_purlin)
                with open(os.path.join(wt_purlin, 'config.json'), 'w') as f:
                    json.dump(config, f)

            # Mock the handler
            new_agents = {
                'architect': {'model': 'claude-opus-4-6', 'effort': 'medium',
                              'bypass_permissions': True,
                              'startup_sequence': True,
                              'recommend_next_actions': True},
            }
            handler = MagicMock(spec=Handler)
            body = json.dumps(new_agents).encode('utf-8')
            handler.headers = {'Content-Length': str(len(body))}
            handler.rfile = io.BytesIO(body)
            handler._send_json = MagicMock()

            mock_worktrees = [
                {'path': os.path.join('.worktrees', 'architect-session'),
                 'branch': 'spec/collab', 'role': 'architect',
                 'main_diff': 'SAME', 'commits_ahead': 0,
                 'last_commit': 'abc', 'modified': {'specs': 0, 'tests': 0, 'other': 0}},
                {'path': os.path.join('.worktrees', 'builder-session'),
                 'branch': 'build/collab', 'role': 'builder',
                 'main_diff': 'SAME', 'commits_ahead': 0,
                 'last_commit': 'def', 'modified': {'specs': 0, 'tests': 0, 'other': 0}},
            ]

            with patch('serve.CONFIG_PATH', config_path), \
                 patch('serve.get_collab_worktrees', return_value=mock_worktrees), \
                 patch('serve.PROJECT_ROOT', td):
                handler._handle_config_agents = Handler._handle_config_agents.__get__(
                    handler, Handler)
                handler._handle_config_agents()

            # Verify project root config updated
            with open(config_path, 'r') as f:
                root_config = json.load(f)
            self.assertEqual(root_config['agents']['architect']['effort'], 'medium')

            # Verify worktree configs updated
            for wt_name in ('architect-session', 'builder-session'):
                wt_cfg_path = os.path.join(
                    td, '.worktrees', wt_name, '.purlin', 'config.json')
                with open(wt_cfg_path, 'r') as f:
                    wt_config = json.load(f)
                self.assertEqual(wt_config['agents']['architect']['effort'], 'medium')


class TestWorktreeStatePurlinExclusion(unittest.TestCase):
    """Files under .purlin/ are excluded from all Modified counts (Section 2.4)."""

    def _mock_subprocess(self, responses):
        call_count = [0]

        def _side_effect(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(responses):
                return subprocess.CompletedProcess(
                    args='mock', returncode=0, stdout=responses[idx], stderr='')
            raise Exception(f"Unexpected subprocess.run call {idx}")

        return _side_effect

    @patch('subprocess.run')
    def test_purlin_files_excluded(self, mock_run):
        """Files under .purlin/ do not count in specs, tests, or other."""
        mock_run.side_effect = self._mock_subprocess([
            'spec/collab',    # git rev-parse
            ' M .purlin/config.json\n M features/foo.md\n M tools/bar.py\n',
            'abc1234 commit (5m ago)',
            '1',
        ])
        state = _worktree_state('/tmp/fake-wt')
        self.assertEqual(state['modified'], {'specs': 1, 'tests': 0, 'other': 1})

    @patch('subprocess.run')
    def test_purlin_only_changes_appear_clean(self, mock_run):
        """Worktree with only .purlin/ changes has all-zero modified counts."""
        mock_run.side_effect = self._mock_subprocess([
            'build/collab',
            ' M .purlin/config.json\n M .purlin/cache/status.json\n',
            'def5678 commit (3m ago)',
            '0',
        ])
        state = _worktree_state('/tmp/fake-wt')
        self.assertEqual(state['modified'], {'specs': 0, 'tests': 0, 'other': 0})


class TestRoleDisplayLabel(unittest.TestCase):
    """Role column renders "QA" (all caps) per Section 2.2 display label rule."""

    def test_qa_rendered_as_all_caps(self):
        """QA role displays as 'QA', not 'Qa'."""
        worktrees = [{
            'role': 'qa', 'branch': 'qa/collab', 'main_diff': 'SAME',
            'modified': {'specs': 0, 'tests': 0, 'other': 0},
        }]
        html = _collab_section_html(worktrees)
        self.assertIn('<td>QA</td>', html)
        self.assertNotIn('<td>Qa</td>', html)

    def test_architect_capitalized(self):
        worktrees = [{
            'role': 'architect', 'branch': 'spec/collab', 'main_diff': 'SAME',
            'modified': {'specs': 0, 'tests': 0, 'other': 0},
        }]
        html = _collab_section_html(worktrees)
        self.assertIn('<td>Architect</td>', html)

    def test_unknown_capitalized(self):
        worktrees = [{
            'role': 'unknown', 'branch': 'hotfix/x', 'main_diff': 'SAME',
            'modified': {'specs': 0, 'tests': 0, 'other': 0},
        }]
        html = _collab_section_html(worktrees)
        self.assertIn('<td>Unknown</td>', html)


class TestGetGitStatusPurlinExclusion(unittest.TestCase):
    """get_git_status() excludes .purlin/ files from clean/dirty (Section 2.3)."""

    @patch('serve.run_command')
    def test_purlin_filtered_from_status(self, mock_cmd):
        """Verifies .purlin/ filter is present in the git status command."""
        mock_cmd.return_value = ''
        get_git_status()
        cmd_arg = mock_cmd.call_args[0][0]
        self.assertIn('.purlin/', cmd_arg)
        self.assertIn('grep -v', cmd_arg)


# ===================================================================
# Test runner with JSON result output
# ===================================================================

if __name__ == '__main__':
    # Discover project root for writing test results
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    tests_dir = os.path.join(project_root, 'tests', 'cdd_collab_mode')
    os.makedirs(tests_dir, exist_ok=True)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed
    status = "PASS" if failed == 0 else "FAIL"

    with open(os.path.join(tests_dir, 'tests.json'), 'w') as f:
        json.dump({
            "status": status,
            "passed": passed,
            "failed": failed,
            "total": total,
        }, f)

    print(f"\nResults: {passed} passed, {failed} failed out of {total}")
    sys.exit(0 if failed == 0 else 1)
