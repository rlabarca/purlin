"""Unit tests for CDD Isolated Teams Mode.

Covers automated scenarios from features/cdd_isolated_teams.md.
Outputs test results to tests/cdd_isolated_teams/tests.json.
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
    _categorize_files,
    _creation_row_html,
    _detect_worktrees,
    _format_category_counts,
    _get_collaboration_branch,
    _name_from_path,
    _worktree_state,
    _compute_main_diff,
    _isolation_section_html,
    _collapsed_isolation_label,
    get_isolation_worktrees,
    get_git_status,
    generate_api_status_json,
    generate_html,
    generate_workspace_json,
    Handler,
    PROJECT_ROOT,
    TOOLS_ROOT,
)


class TestNameFromPath(unittest.TestCase):
    """Test isolation name parsing from worktree path (Section 2.2)."""

    def test_extracts_name_from_dotworktrees_path(self):
        path = os.path.join(PROJECT_ROOT, '.worktrees', 'feat1')
        self.assertEqual(_name_from_path(path), 'feat1')

    def test_extracts_name_with_hyphens(self):
        path = os.path.join(PROJECT_ROOT, '.worktrees', 'my-feature')
        self.assertEqual(_name_from_path(path), 'my-feature')

    def test_extracts_name_with_underscores(self):
        path = os.path.join(PROJECT_ROOT, '.worktrees', 'feat_1')
        self.assertEqual(_name_from_path(path), 'feat_1')


class TestDetectWorktrees(unittest.TestCase):
    """Test worktree detection from git worktree list --porcelain."""

    @patch('serve.run_command')
    def test_no_worktrees(self, mock_cmd):
        """Scenario: Isolations Inactive When No Worktrees."""
        mock_cmd.return_value = (
            f"worktree {PROJECT_ROOT}\n"
            "HEAD abc123\n"
            "branch refs/heads/main\n"
        )
        result = _detect_worktrees()
        self.assertEqual(result, [])

    @patch('serve.run_command')
    def test_detects_worktrees_under_dotworktrees(self, mock_cmd):
        """Scenario: Isolations Active When Worktrees Detected."""
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'feat1')
        mock_cmd.return_value = (
            f"worktree {PROJECT_ROOT}\n"
            "HEAD abc123\n"
            "branch refs/heads/main\n"
            "\n"
            f"worktree {wt_path}\n"
            "HEAD def456\n"
            "branch refs/heads/isolated/feat1\n"
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


class TestIsolationsInactive(unittest.TestCase):
    """Scenario: Isolations Inactive When No Worktrees."""

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.build_status_commit_cache', return_value={})
    def test_status_json_no_isolations(self, mock_cache, mock_iso):
        result = generate_api_status_json()
        self.assertNotIn('isolations_active', result)
        self.assertNotIn('worktrees', result)

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_git_status', return_value='')
    @patch('serve.get_last_commit', return_value='abc1234 initial (just now)')
    def test_workspace_json_no_isolations(self, mock_commit, mock_status,
                                          mock_iso):
        result = generate_workspace_json()
        self.assertNotIn('isolations_active', result)
        self.assertNotIn('worktrees', result)


class TestIsolationsActive(unittest.TestCase):
    """Scenario: Isolations Active When Worktrees Detected."""

    MOCK_WORKTREES = [{
        'name': 'feat1',
        'path': '.worktrees/feat1',
        'branch': 'isolated/feat1',
        'main_diff': 'SAME',
        'commits_ahead': 0,
        'last_commit': 'abc1234 feat: add scenarios (45 min ago)',
        'committed': {'specs': 0, 'tests': 0, 'other': 0},
        'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
    }]

    @patch('serve.get_isolation_worktrees')
    @patch('serve.build_status_commit_cache', return_value={})
    def test_status_json_has_isolations(self, mock_cache, mock_iso):
        mock_iso.return_value = self.MOCK_WORKTREES
        result = generate_api_status_json()
        self.assertTrue(result.get('isolations_active'))
        self.assertEqual(len(result['worktrees']), 1)
        wt = result['worktrees'][0]
        self.assertEqual(wt['path'], '.worktrees/feat1')
        self.assertEqual(wt['branch'], 'isolated/feat1')
        self.assertEqual(wt['name'], 'feat1')
        # No role field should be present
        self.assertNotIn('role', wt)


class TestIsolationNameParsedFromPath(unittest.TestCase):
    """Scenario: Isolation Name Parsed from Worktree Path.

    Given a worktree at .worktrees/ui on branch isolated/ui
    Then the worktree entry has name "ui"
    """

    @patch('serve._compute_main_diff', return_value='SAME')
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_name_parsed_from_worktree_path(self, mock_detect, mock_state,
                                            mock_diff):
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'ui')
        mock_detect.return_value = [
            {'abs_path': wt_path,
             'branch_ref': 'refs/heads/isolated/ui'},
        ]
        mock_state.return_value = {
            'branch': 'isolated/ui',
            'committed': {'specs': 0, 'tests': 0, 'other': 0},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
            'last_commit': 'abc ui', 'commits_ahead': 0,
        }
        result = get_isolation_worktrees()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'ui')
        self.assertNotIn('role', result[0])


class TestNonIsolatedBranchNoRoleAssignment(unittest.TestCase):
    """Scenario: Non-Isolated Branch Worktrees Detected Without Role Assignment.

    Given a worktree at .worktrees/hotfix on branch hotfix/urgent
    Then the worktree entry has name "hotfix" and no role field.
    """

    @patch('serve._compute_main_diff', return_value='SAME')
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_hotfix_has_name_no_role(self, mock_detect, mock_state, mock_diff):
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'hotfix')
        mock_detect.return_value = [
            {'abs_path': wt_path,
             'branch_ref': 'refs/heads/hotfix/urgent'},
        ]
        mock_state.return_value = {
            'branch': 'hotfix/urgent',
            'committed': {'specs': 0, 'tests': 0, 'other': 0},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
            'last_commit': 'xyz hotfix', 'commits_ahead': 0,
        }
        result = get_isolation_worktrees()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'hotfix')
        self.assertNotIn('role', result[0])


class TestCommittedModifiedCategorization(unittest.TestCase):
    """Scenario: Committed Modified Categorizes Files Changed Against Collaboration Branch by Type.

    Given a worktree on a branch AHEAD of the collaboration branch with commits that modified
    two files under features/ and one file outside features/ and tests/
    Then the committed field has specs=2, tests=0, other=1.
    """

    @patch('serve._compute_main_diff', return_value='AHEAD')
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_committed_categorized(self, mock_detect, mock_state, mock_diff):
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'feat1')
        mock_detect.return_value = [
            {'abs_path': wt_path,
             'branch_ref': 'refs/heads/isolated/feat1'},
        ]
        mock_state.return_value = {
            'branch': 'isolated/feat1',
            'committed': {'specs': 2, 'tests': 0, 'other': 1},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
            'last_commit': 'abc feat', 'commits_ahead': 2,
        }
        result = get_isolation_worktrees()
        self.assertEqual(len(result), 1)
        committed = result[0]['committed']
        self.assertEqual(committed['specs'], 2)
        self.assertEqual(committed['tests'], 0)
        self.assertEqual(committed['other'], 1)


class TestWorktreeStateFileCategories(unittest.TestCase):
    """Test _worktree_state() parses committed and uncommitted file categories."""

    def _mock_subprocess(self, responses):
        """Create mock for subprocess.run returning CompletedProcess-like objects.

        _worktree_state calls subprocess.run 5 times:
          0: git rev-parse --abbrev-ref HEAD (via _wt_cmd, cwd=wt_abs_path)
          1: git diff main...<branch> --name-only (three-dot, cwd=PROJECT_ROOT)
          2: git status --porcelain (cwd=wt_abs_path)
          3: git log -1 (via _wt_cmd, cwd=wt_abs_path)
          4: git rev-list --count (via _wt_cmd, cwd=wt_abs_path)
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
    def test_categorizes_committed_by_path_prefix(self, mock_run):
        """Committed: features/ count as specs, tests/ as tests, rest as other."""
        mock_run.side_effect = self._mock_subprocess([
            'isolated/feat1',    # git rev-parse (via _wt_cmd)
            'features/foo.md\nfeatures/bar.md\ntools/thing.py\n',  # git diff --name-only
            '',                  # git status --porcelain (no uncommitted)
            'abc1234 commit (5m ago)',  # git log (via _wt_cmd)
            '2',              # git rev-list (via _wt_cmd)
        ])
        state = _worktree_state('/tmp/fake-wt')
        self.assertEqual(state['committed'], {'specs': 2, 'tests': 0, 'other': 1})
        self.assertEqual(state['uncommitted'], {'specs': 0, 'tests': 0, 'other': 0})
        self.assertEqual(state['commits_ahead'], 2)

    @patch('subprocess.run')
    def test_clean_worktree(self, mock_run):
        """Branch at same position as main has all zeros in both committed and uncommitted."""
        mock_run.side_effect = self._mock_subprocess([
            'isolated/feat1',   # branch (via _wt_cmd)
            '',               # git diff --name-only (no changes vs main)
            '',               # git status --porcelain (no uncommitted)
            'def5678 commit (3m ago)',  # git log (via _wt_cmd)
            '0',              # commits ahead (via _wt_cmd)
        ])
        state = _worktree_state('/tmp/fake-wt')
        self.assertEqual(state['committed'], {'specs': 0, 'tests': 0, 'other': 0})
        self.assertEqual(state['uncommitted'], {'specs': 0, 'tests': 0, 'other': 0})

    @patch('subprocess.run')
    def test_committed_tests_directory_counted(self, mock_run):
        """Committed files under tests/ count in the tests category."""
        mock_run.side_effect = self._mock_subprocess([
            'isolated/feat1',     # branch (via _wt_cmd)
            'tests/foo/tests.json\ntests/bar/critic.json\n',  # git diff --name-only
            '',                   # git status --porcelain (no uncommitted)
            'ghi9012 commit (1m ago)',  # git log (via _wt_cmd)
            '1',             # commits ahead (via _wt_cmd)
        ])
        state = _worktree_state('/tmp/fake-wt')
        self.assertEqual(state['committed']['tests'], 2)
        self.assertEqual(state['committed']['specs'], 0)
        self.assertEqual(state['committed']['other'], 0)

    @patch('subprocess.run')
    def test_uncommitted_categorized(self, mock_run):
        """Scenario: Uncommitted Modified Categorizes Working Tree Changes by Type."""
        mock_run.side_effect = self._mock_subprocess([
            'isolated/feat1',     # branch
            '',                   # git diff --name-only (no committed changes)
            ' M features/foo.md\n M tools/bar.py\n M tools/baz.py\n',  # git status --porcelain
            'abc1234 commit (5m ago)',
            '0',
        ])
        state = _worktree_state('/tmp/fake-wt')
        self.assertEqual(state['uncommitted'], {'specs': 1, 'tests': 0, 'other': 2})

    @patch('subprocess.run')
    def test_uncommitted_nonempty_when_same(self, mock_run):
        """Scenario: Uncommitted Modified Non-Empty When Main Diff Is SAME."""
        mock_run.side_effect = self._mock_subprocess([
            'isolated/ui',        # branch
            '',                   # git diff --name-only (SAME = no committed changes)
            ' M features/a.md\n M features/b.md\n M features/c.md\n',  # git status --porcelain
            'def5678 commit (3m ago)',
            '0',
        ])
        state = _worktree_state('/tmp/fake-wt')
        self.assertEqual(state['committed'], {'specs': 0, 'tests': 0, 'other': 0})
        self.assertEqual(state['uncommitted'], {'specs': 3, 'tests': 0, 'other': 0})

    @patch('subprocess.run')
    def test_uncommitted_rename_uses_new_path(self, mock_run):
        """Renames in git status --porcelain use the new path for categorization."""
        mock_run.side_effect = self._mock_subprocess([
            'isolated/feat1',
            '',
            'R  tools/old.py -> features/new.md\n',  # rename: new path under features/
            'abc1234 commit (5m ago)',
            '0',
        ])
        state = _worktree_state('/tmp/fake-wt')
        self.assertEqual(state['uncommitted'], {'specs': 1, 'tests': 0, 'other': 0})

    @patch('subprocess.run')
    def test_uncommitted_excludes_purlin(self, mock_run):
        """Uncommitted .purlin/ files are excluded from all categories."""
        mock_run.side_effect = self._mock_subprocess([
            'isolated/feat1',
            '',
            ' M .purlin/config.json\n M features/foo.md\n',  # git status --porcelain
            'abc1234 commit (5m ago)',
            '0',
        ])
        state = _worktree_state('/tmp/fake-wt')
        self.assertEqual(state['uncommitted'], {'specs': 1, 'tests': 0, 'other': 0})


class TestCommitsAheadReported(unittest.TestCase):
    """Scenario: Commits Ahead Reported When Worktree Branch Is Ahead Of Collaboration Branch.

    Given a worktree at .worktrees/feat1 has 3 commits not yet merged to the collaboration branch
    Then the worktree entry has commits_ahead equal to 3.
    """

    @patch('serve._compute_main_diff', return_value='SAME')
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_commits_ahead(self, mock_detect, mock_state, mock_diff):
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'feat1')
        mock_detect.return_value = [
            {'abs_path': wt_path,
             'branch_ref': 'refs/heads/isolated/feat1'},
        ]
        mock_state.return_value = {
            'branch': 'isolated/feat1',
            'committed': {'specs': 0, 'tests': 0, 'other': 0},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
            'last_commit': 'def5678 feat: handlers (12 min ago)',
            'commits_ahead': 3,
        }
        result = get_isolation_worktrees()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['commits_ahead'], 3)


class TestMainDiffBehind(unittest.TestCase):
    """Scenario: Main Diff BEHIND When Worktree Branch Is Missing Collaboration Branch Commits.

    Given the collaboration branch has commits that are not in isolated/feat1
    And isolated/feat1 has no commits not in the collaboration branch
    Then the worktree entry has main_diff "BEHIND".
    """

    @patch('subprocess.run')
    def test_behind_when_main_has_extra_commits(self, mock_run):
        """_compute_main_diff returns BEHIND when only main has moved."""
        # Query 1 (branch..main): non-empty — behind
        # Query 2 (main..branch): empty — not ahead
        mock_run.side_effect = [
            MagicMock(stdout='abc1234 some commit on main\n', returncode=0),
            MagicMock(stdout='', returncode=0),
        ]
        result = _compute_main_diff('isolated/feat1')
        self.assertEqual(result, 'BEHIND')

    @patch('serve._compute_main_diff', return_value='BEHIND')
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_behind_in_worktree_entry(self, mock_detect, mock_state, mock_diff):
        """Worktree entry surfaces main_diff BEHIND."""
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'feat1')
        mock_detect.return_value = [
            {'abs_path': wt_path,
             'branch_ref': 'refs/heads/isolated/feat1'},
        ]
        mock_state.return_value = {
            'branch': 'isolated/feat1',
            'committed': {'specs': 2, 'tests': 0, 'other': 1},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
            'last_commit': 'abc feat', 'commits_ahead': 0,
        }
        result = get_isolation_worktrees()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['main_diff'], 'BEHIND')


class TestMainDiffSame(unittest.TestCase):
    """Scenario: Main Diff SAME When Branch And Collaboration Branch Are Identical.

    Given isolated/ui and the collaboration branch point to the same commit
    Then the worktree entry has main_diff "SAME".
    """

    @patch('subprocess.run')
    def test_same_when_no_missing_commits(self, mock_run):
        """_compute_main_diff returns SAME when git log output is empty."""
        mock_run.return_value = MagicMock(stdout='', returncode=0)
        result = _compute_main_diff('isolated/ui')
        self.assertEqual(result, 'SAME')

    @patch('subprocess.run')
    def test_same_on_git_error(self, mock_run):
        """_compute_main_diff defaults to SAME on git errors."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git')
        result = _compute_main_diff('nonexistent/branch')
        self.assertEqual(result, 'SAME')


class TestMainDiffAhead(unittest.TestCase):
    """Scenario: Main Diff AHEAD When Worktree Branch Has Commits Not In Collaboration Branch.

    Given isolated/feat1 has commits that are not in the collaboration branch
    And the collaboration branch has no commits that are missing from isolated/feat1
    Then the worktree entry has main_diff "AHEAD".
    """

    @patch('subprocess.run')
    def test_ahead_when_branch_has_extra_commits(self, mock_run):
        """_compute_main_diff returns AHEAD when branch is ahead of main."""
        # First call (branch..main): empty — not behind
        # Second call (main..branch): non-empty — ahead
        mock_run.side_effect = [
            MagicMock(stdout='', returncode=0),
            MagicMock(stdout='def5678 feat: new work\n', returncode=0),
        ]
        result = _compute_main_diff('isolated/feat1')
        self.assertEqual(result, 'AHEAD')

    @patch('serve._compute_main_diff', return_value='AHEAD')
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_ahead_in_worktree_entry(self, mock_detect, mock_state, mock_diff):
        """Worktree entry surfaces main_diff AHEAD."""
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'feat1')
        mock_detect.return_value = [
            {'abs_path': wt_path,
             'branch_ref': 'refs/heads/isolated/feat1'},
        ]
        mock_state.return_value = {
            'branch': 'isolated/feat1',
            'committed': {'specs': 0, 'tests': 0, 'other': 0},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
            'last_commit': 'abc feat', 'commits_ahead': 2,
        }
        result = get_isolation_worktrees()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['main_diff'], 'AHEAD')


class TestMainDiffDiverged(unittest.TestCase):
    """Scenario: Main Diff DIVERGED When Both Collaboration Branch And Branch Have Commits Beyond Common Ancestor.

    Given isolated/feat1 has commits not in the collaboration branch AND the collaboration branch has commits not in isolated/feat1
    Then the worktree entry has main_diff "DIVERGED".
    """

    @patch('subprocess.run')
    def test_diverged_when_both_have_commits(self, mock_run):
        """_compute_main_diff returns DIVERGED when both sides have moved."""
        # Query 1 (branch..main): non-empty — behind
        # Query 2 (main..branch): non-empty — ahead
        mock_run.side_effect = [
            MagicMock(stdout='abc1234 commit on main\n', returncode=0),
            MagicMock(stdout='def5678 commit on branch\n', returncode=0),
        ]
        result = _compute_main_diff('isolated/feat1')
        self.assertEqual(result, 'DIVERGED')
        self.assertEqual(mock_run.call_count, 2)


class TestCreateIsolationEndpoint(unittest.TestCase):
    """Scenario: Create Isolation via Dashboard."""

    def _make_handler(self, body_dict):
        """Create a mock Handler for POST /isolate/create."""
        handler = MagicMock(spec=Handler)
        handler.path = '/isolate/create'
        body_bytes = json.dumps(body_dict).encode('utf-8')
        handler.headers = {'Content-Length': str(len(body_bytes))}
        handler.rfile = io.BytesIO(body_bytes)
        handler._send_json = MagicMock()
        handler._handle_isolate_create = Handler._handle_isolate_create.__get__(
            handler, Handler)
        return handler

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_create_isolation_success(self, mock_exists, mock_run):
        """POST /isolate/create with valid name creates isolation."""
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        handler = self._make_handler({'name': 'feat1'})
        handler._handle_isolate_create()
        handler._send_json.assert_called_once_with(200, {'status': 'ok'})
        # Verify create_isolation.sh is called with the name
        call_args = mock_run.call_args[0][0]
        self.assertIn('create_isolation.sh', call_args[1])
        self.assertIn('feat1', call_args)

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_create_isolation_script_error(self, mock_exists, mock_run):
        """POST /isolate/create propagates script errors."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'bash', stderr='name already exists')
        handler = self._make_handler({'name': 'feat1'})
        handler._handle_isolate_create()
        handler._send_json.assert_called_once()
        args = handler._send_json.call_args
        self.assertEqual(args[0][0], 500)
        self.assertIn('name already exists', args[0][1]['error'])

    @patch('os.path.exists', return_value=True)
    def test_create_isolation_empty_name_rejected(self, mock_exists):
        """POST /isolate/create with empty name returns 400."""
        handler = self._make_handler({'name': ''})
        handler._handle_isolate_create()
        handler._send_json.assert_called_once()
        args = handler._send_json.call_args
        self.assertEqual(args[0][0], 400)


class TestKillIsolationEndpoint(unittest.TestCase):
    """Scenario: Kill Isolation via Dashboard."""

    def _make_handler(self, body_dict):
        """Create a mock Handler for POST /isolate/kill."""
        handler = MagicMock(spec=Handler)
        handler.path = '/isolate/kill'
        body_bytes = json.dumps(body_dict).encode('utf-8')
        handler.headers = {'Content-Length': str(len(body_bytes))}
        handler.rfile = io.BytesIO(body_bytes)
        handler._send_json = MagicMock()
        handler._handle_isolate_kill = Handler._handle_isolate_kill.__get__(
            handler, Handler)
        return handler

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_kill_dry_run(self, mock_exists, mock_run):
        """POST /isolate/kill dry_run returns safety JSON."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"dirty":false,"dirty_files":[],"unsynced":false,"unsynced_branch":"","unsynced_commits":0}',
            stderr='')
        handler = self._make_handler({'name': 'feat1', 'dry_run': True})
        handler._handle_isolate_kill()
        handler._send_json.assert_called_once()
        args = handler._send_json.call_args
        self.assertEqual(args[0][0], 200)
        self.assertFalse(args[0][1]['dirty'])

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_kill_force_success(self, mock_exists, mock_run):
        """POST /isolate/kill force removes isolation."""
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        handler = self._make_handler({'name': 'feat1', 'force': True})
        handler._handle_isolate_kill()
        handler._send_json.assert_called_once_with(200, {'status': 'ok'})

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_kill_force_failure(self, mock_exists, mock_run):
        """POST /isolate/kill without force fails when dirty."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='Error: Worktree has uncommitted changes.')
        handler = self._make_handler({'name': 'feat1'})
        handler._handle_isolate_kill()
        handler._send_json.assert_called_once()
        args = handler._send_json.call_args
        self.assertEqual(args[0][0], 500)
        self.assertIn('uncommitted', args[0][1]['error'])


class TestAgentConfigPropagation(unittest.TestCase):
    """Scenario: Agent Config Save Propagates to All Active Isolations.

    Given isolations_active is true with two worktrees,
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
                    'builder': {'model': 'claude-opus-4-6', 'effort': 'high',
                                'bypass_permissions': True,
                                'startup_sequence': True,
                                'recommend_next_actions': True},
                    'qa': {'model': 'claude-opus-4-6', 'effort': 'medium',
                           'bypass_permissions': True,
                           'startup_sequence': False,
                           'recommend_next_actions': False},
                }
            }
            config_path = os.path.join(purlin_dir, 'config.json')
            with open(config_path, 'w') as f:
                json.dump(config, f)

            # Setup two worktree config dirs
            for wt_name in ('feat1', 'ui'):
                wt_purlin = os.path.join(td, '.worktrees', wt_name, '.purlin')
                os.makedirs(wt_purlin)
                with open(os.path.join(wt_purlin, 'config.json'), 'w') as f:
                    json.dump(config, f)

            # Mock the handler — all 3 roles required per completeness check
            new_agents = {
                'architect': {'model': 'claude-opus-4-6', 'effort': 'medium',
                              'bypass_permissions': True,
                              'startup_sequence': True,
                              'recommend_next_actions': True},
                'builder': {'model': 'claude-opus-4-6', 'effort': 'high',
                            'bypass_permissions': True,
                            'startup_sequence': True,
                            'recommend_next_actions': True},
                'qa': {'model': 'claude-opus-4-6', 'effort': 'medium',
                       'bypass_permissions': True,
                       'startup_sequence': False,
                       'recommend_next_actions': False},
            }
            handler = MagicMock(spec=Handler)
            body = json.dumps(new_agents).encode('utf-8')
            handler.headers = {'Content-Length': str(len(body))}
            handler.rfile = io.BytesIO(body)
            handler._send_json = MagicMock()

            mock_worktrees = [
                {'name': 'feat1',
                 'path': os.path.join('.worktrees', 'feat1'),
                 'branch': 'isolated/feat1',
                 'main_diff': 'SAME', 'commits_ahead': 0,
                 'last_commit': 'abc',
                 'committed': {'specs': 0, 'tests': 0, 'other': 0},
                 'uncommitted': {'specs': 0, 'tests': 0, 'other': 0}},
                {'name': 'ui',
                 'path': os.path.join('.worktrees', 'ui'),
                 'branch': 'isolated/ui',
                 'main_diff': 'SAME', 'commits_ahead': 0,
                 'last_commit': 'def',
                 'committed': {'specs': 0, 'tests': 0, 'other': 0},
                 'uncommitted': {'specs': 0, 'tests': 0, 'other': 0}},
            ]

            with patch('serve.CONFIG_PATH', config_path), \
                 patch('serve.get_isolation_worktrees', return_value=mock_worktrees), \
                 patch('serve.PROJECT_ROOT', td):
                handler._handle_config_agents = Handler._handle_config_agents.__get__(
                    handler, Handler)
                handler._handle_config_agents()

            # Verify project root config updated
            with open(config_path, 'r') as f:
                root_config = json.load(f)
            self.assertEqual(root_config['agents']['architect']['effort'], 'medium')

            # Verify worktree configs updated (handler writes to config.local.json)
            for wt_name in ('feat1', 'ui'):
                wt_cfg_path = os.path.join(
                    td, '.worktrees', wt_name, '.purlin', 'config.local.json')
                with open(wt_cfg_path, 'r') as f:
                    wt_config = json.load(f)
                self.assertEqual(wt_config['agents']['architect']['effort'], 'medium')


class TestWorktreeStatePurlinExclusion(unittest.TestCase):
    """Files under .purlin/ are excluded from all committed and uncommitted counts (Section 2.4)."""

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
    def test_purlin_files_excluded_from_committed(self, mock_run):
        """Files under .purlin/ do not count in committed specs, tests, or other."""
        mock_run.side_effect = self._mock_subprocess([
            'isolated/feat1',    # git rev-parse
            '.purlin/config.json\nfeatures/foo.md\ntools/bar.py\n',  # git diff --name-only
            '',                  # git status --porcelain
            'abc1234 commit (5m ago)',
            '1',
        ])
        state = _worktree_state('/tmp/fake-wt')
        self.assertEqual(state['committed'], {'specs': 1, 'tests': 0, 'other': 1})

    @patch('subprocess.run')
    def test_purlin_only_changes_appear_clean(self, mock_run):
        """Branch with only .purlin/ committed changes has all-zero counts."""
        mock_run.side_effect = self._mock_subprocess([
            'isolated/feat1',
            '.purlin/config.json\n.purlin/cache/status.json\n',  # git diff --name-only
            '',  # git status --porcelain
            'def5678 commit (3m ago)',
            '0',
        ])
        state = _worktree_state('/tmp/fake-wt')
        self.assertEqual(state['committed'], {'specs': 0, 'tests': 0, 'other': 0})


class TestIsolationSectionHtmlNameColumn(unittest.TestCase):
    """Scenario: Sessions Table Displays Named Isolations in HTML.

    Sessions table has Name, Branch, Main Diff, Committed Modified,
    Uncommitted Modified columns — no Role column (Section 2.3).
    """

    def test_name_rendered_in_table(self):
        worktrees = [{
            'name': 'feat1', 'branch': 'isolated/feat1', 'main_diff': 'SAME',
            'committed': {'specs': 0, 'tests': 0, 'other': 0},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
        }]
        html = _isolation_section_html(worktrees)
        self.assertIn('<th>Name</th>', html)
        self.assertIn('<td>feat1</td>', html)
        # No Role column
        self.assertNotIn('<th>Role</th>', html)

    def test_multiple_isolations(self):
        worktrees = [
            {'name': 'feat1', 'branch': 'isolated/feat1', 'main_diff': 'AHEAD',
             'committed': {'specs': 2, 'tests': 0, 'other': 0},
             'uncommitted': {'specs': 0, 'tests': 0, 'other': 0}},
            {'name': 'ui', 'branch': 'isolated/ui', 'main_diff': 'SAME',
             'committed': {'specs': 0, 'tests': 0, 'other': 0},
             'uncommitted': {'specs': 0, 'tests': 0, 'other': 0}},
        ]
        html = _isolation_section_html(worktrees)
        self.assertIn('feat1', html)
        self.assertIn('ui', html)

    def test_two_line_column_headers(self):
        """Column headers use two-line rendering for Committed/Uncommitted Modified."""
        worktrees = [{
            'name': 'feat1', 'branch': 'isolated/feat1', 'main_diff': 'SAME',
            'committed': {'specs': 0, 'tests': 0, 'other': 0},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
        }]
        html = _isolation_section_html(worktrees)
        self.assertIn('Committed<br>Modified', html)
        self.assertIn('Uncommitted<br>Modified', html)
        # Old single "Modified" header should not be present
        self.assertNotIn('<th>Modified</th>', html)


class TestMainDiffBadgeRendering(unittest.TestCase):
    """Main Diff cell renders correct badge styling per Visual Spec Section 4."""

    def test_same_badge_green(self):
        """SAME renders with st-good (green) badge class."""
        worktrees = [{
            'name': 'feat1', 'branch': 'isolated/feat1', 'main_diff': 'SAME',
            'committed': {'specs': 0, 'tests': 0, 'other': 0},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
        }]
        html = _isolation_section_html(worktrees)
        self.assertIn('class="st-good"', html)
        self.assertIn('SAME', html)

    def test_ahead_badge_yellow(self):
        """AHEAD renders with st-todo (yellow) badge class."""
        worktrees = [{
            'name': 'feat1', 'branch': 'isolated/feat1', 'main_diff': 'AHEAD',
            'committed': {'specs': 2, 'tests': 0, 'other': 0},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
        }]
        html = _isolation_section_html(worktrees)
        self.assertIn('class="st-todo"', html)
        self.assertIn('AHEAD', html)

    def test_behind_badge_yellow(self):
        """BEHIND renders with st-todo (yellow) badge class."""
        worktrees = [{
            'name': 'feat1', 'branch': 'isolated/feat1', 'main_diff': 'BEHIND',
            'committed': {'specs': 0, 'tests': 0, 'other': 0},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
        }]
        html = _isolation_section_html(worktrees)
        self.assertIn('class="st-todo"', html)
        self.assertIn('BEHIND', html)

    def test_diverged_badge_orange(self):
        """DIVERGED renders with st-disputed (orange/warning) badge class."""
        worktrees = [{
            'name': 'feat1', 'branch': 'isolated/feat1', 'main_diff': 'DIVERGED',
            'committed': {'specs': 1, 'tests': 0, 'other': 2},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
        }]
        html = _isolation_section_html(worktrees)
        self.assertIn('class="st-disputed"', html)
        self.assertIn('DIVERGED', html)


class TestDeliveryPhaseBadgeInHtml(unittest.TestCase):
    """Scenario: Delivery Phase Badge Present in Worktree Row HTML.

    Also covers: Delivery Phase Badge Present When Delivery Plan Has Active Phase,
    Delivery Phase Badge Absent When No Delivery Plan.
    """

    def test_phase_badge_rendered_in_name_cell(self):
        """Name cell shows delivery phase badge when present."""
        worktrees = [{
            'name': 'feat1', 'branch': 'isolated/feat1', 'main_diff': 'AHEAD',
            'committed': {'specs': 2, 'tests': 0, 'other': 0},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
            'delivery_phase': {'current': 2, 'total': 3},
        }]
        html = _isolation_section_html(worktrees)
        self.assertIn('Phase 2/3', html)
        self.assertIn('--purlin-status-warning', html)

    def test_no_phase_badge_when_absent(self):
        """Name cell has no phase badge when delivery_phase is absent."""
        worktrees = [{
            'name': 'ui', 'branch': 'isolated/ui', 'main_diff': 'SAME',
            'committed': {'specs': 0, 'tests': 0, 'other': 0},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
        }]
        html = _isolation_section_html(worktrees)
        self.assertNotIn('Phase', html)


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


class TestCollapsedIsolationLabel(unittest.TestCase):
    """Scenario: Isolated Teams Heading Text With No Active Worktrees,
    Isolated Teams Heading Shows Count With Active Worktrees.

    _collapsed_isolation_label returns (badge_css, heading_text, badge_text).
    - badge_css: severity class for the badge only (not the heading)
    - heading_text: always in --purlin-muted color (no severity coloring)
    - badge_text: worst severity state name for the badge to the right
    """

    def test_no_worktrees_returns_isolated_teams(self):
        css, text, sev = _collapsed_isolation_label([])
        self.assertEqual(css, "")
        self.assertEqual(text, "ISOLATED TEAMS")
        self.assertEqual(sev, "")

    def test_one_worktree_same(self):
        wts = [{'main_diff': 'SAME'}]
        css, text, sev = _collapsed_isolation_label(wts)
        self.assertEqual(css, "st-good")
        self.assertEqual(text, "1 Isolated Team")
        self.assertEqual(sev, "SAME")

    def test_two_worktrees_all_same(self):
        wts = [{'main_diff': 'SAME'}, {'main_diff': 'SAME'}]
        css, text, sev = _collapsed_isolation_label(wts)
        self.assertEqual(css, "st-good")
        self.assertEqual(text, "2 Isolated Teams")
        self.assertEqual(sev, "SAME")

    def test_diverged_highest_severity(self):
        wts = [{'main_diff': 'SAME'}, {'main_diff': 'DIVERGED'}]
        css, text, sev = _collapsed_isolation_label(wts)
        self.assertEqual(css, "st-disputed")
        self.assertEqual(text, "2 Isolated Teams")
        self.assertEqual(sev, "DIVERGED")

    def test_behind_higher_than_ahead(self):
        wts = [{'main_diff': 'AHEAD'}, {'main_diff': 'BEHIND'}]
        css, text, sev = _collapsed_isolation_label(wts)
        self.assertEqual(css, "st-todo")
        self.assertEqual(text, "2 Isolated Teams")
        self.assertEqual(sev, "BEHIND")

    def test_ahead_only(self):
        wts = [{'main_diff': 'AHEAD'}]
        css, text, sev = _collapsed_isolation_label(wts)
        self.assertEqual(css, "st-todo")
        self.assertEqual(text, "1 Isolated Team")
        self.assertEqual(sev, "AHEAD")


class TestIsolationSectionNoSessionsHeader(unittest.TestCase):
    """_isolation_section_html returns table with no Sessions h4 header."""

    def test_no_h4_sessions_header(self):
        worktrees = [{
            'name': 'feat1', 'branch': 'isolated/feat1', 'main_diff': 'SAME',
            'committed': {'specs': 0, 'tests': 0, 'other': 0},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
        }]
        html = _isolation_section_html(worktrees)
        self.assertNotIn('<h4', html)
        self.assertIn('<table', html)

    def test_empty_worktrees_returns_empty(self):
        html = _isolation_section_html([])
        self.assertEqual(html, "")


class TestCollaborationBranchAbstraction(unittest.TestCase):
    """Collaboration branch abstraction: worktree comparisons use the branch
    the project root is on, not hardcoded 'main' (Section 2.3, 2.4)."""

    @patch('serve.run_command', return_value='collab/v0.5-sprint')
    def test_collab_branch_returns_current_branch(self, mock_cmd):
        """_get_collaboration_branch returns the current branch of PROJECT_ROOT."""
        result = _get_collaboration_branch()
        self.assertEqual(result, 'collab/v0.5-sprint')
        mock_cmd.assert_called_once_with("git rev-parse --abbrev-ref HEAD")

    @patch('serve.run_command', return_value='main')
    def test_collab_branch_returns_main_when_on_main(self, mock_cmd):
        result = _get_collaboration_branch()
        self.assertEqual(result, 'main')

    @patch('serve.run_command', return_value='')
    def test_collab_branch_defaults_to_main_on_empty(self, mock_cmd):
        result = _get_collaboration_branch()
        self.assertEqual(result, 'main')

    @patch('subprocess.run')
    def test_compute_main_diff_uses_collab_branch(self, mock_run):
        """_compute_main_diff uses the collab_branch parameter, not hardcoded main."""
        mock_run.side_effect = [
            MagicMock(stdout='', returncode=0),
            MagicMock(stdout='abc commit\n', returncode=0),
        ]
        result = _compute_main_diff('isolated/feat1', 'collab/v0.5-sprint')
        self.assertEqual(result, 'AHEAD')
        # Verify collab branch used in git commands
        calls = mock_run.call_args_list
        self.assertIn('collab/v0.5-sprint', calls[0][0][0])
        self.assertIn('collab/v0.5-sprint', calls[1][0][0])

    @patch('subprocess.run')
    def test_worktree_state_uses_collab_branch_for_committed(self, mock_run):
        """_worktree_state uses collab_branch for three-dot diff."""
        responses = [
            'isolated/feat1',
            'features/foo.md\n',
            '',
            'abc1234 commit (5m ago)',
            '1',
        ]
        call_count = [0]

        def _side_effect(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            return subprocess.CompletedProcess(
                args='mock', returncode=0, stdout=responses[idx], stderr='')

        mock_run.side_effect = _side_effect
        state = _worktree_state('/tmp/fake-wt', 'collab/v0.5-sprint')
        # Verify the git diff command used collab branch
        diff_call = mock_run.call_args_list[1]
        self.assertIn('collab/v0.5-sprint', diff_call[1].get('args', '') or diff_call[0][0])
        self.assertEqual(state['committed']['specs'], 1)

    @patch('serve._get_collaboration_branch', return_value='collab/v0.5-sprint')
    @patch('serve._compute_main_diff', return_value='AHEAD')
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_get_isolation_worktrees_passes_collab_branch(
            self, mock_detect, mock_state, mock_diff, mock_collab):
        """get_isolation_worktrees passes the collab branch to _worktree_state and _compute_main_diff."""
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'feat1')
        mock_detect.return_value = [
            {'abs_path': wt_path, 'branch_ref': 'refs/heads/isolated/feat1'},
        ]
        mock_state.return_value = {
            'branch': 'isolated/feat1',
            'committed': {'specs': 0, 'tests': 0, 'other': 0},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
            'last_commit': 'abc feat', 'commits_ahead': 2,
        }
        result = get_isolation_worktrees()
        # Verify collab branch was passed to both functions
        mock_state.assert_called_once_with(wt_path, 'collab/v0.5-sprint')
        mock_diff.assert_called_once_with('isolated/feat1', 'collab/v0.5-sprint')
        self.assertEqual(len(result), 1)


class TestCreationRowPresentWhenNoWorktrees(unittest.TestCase):
    """Scenario: Creation Row Present When No Active Worktrees.

    Given no worktrees are active under .worktrees/
    When the dashboard HTML is generated
    Then the Isolated Teams section contains a creation row with "Create An Isolated Team" label
    And the creation row contains a text input and a Create button
    And no Sessions table rows are present below the creation row.
    """

    def test_creation_row_contains_label(self):
        """Creation row HTML contains the 'Create An Isolated Team' label."""
        html = _creation_row_html()
        self.assertIn('Create An Isolated Team', html)

    def test_creation_row_contains_text_input(self):
        """Creation row HTML contains a text input with correct attributes."""
        html = _creation_row_html()
        self.assertIn('id="new-isolation-name"', html)
        self.assertIn('maxlength="12"', html)
        self.assertIn('autocapitalize="none"', html)
        self.assertIn('autocorrect="off"', html)

    def test_creation_row_contains_create_button(self):
        """Creation row HTML contains the Create button."""
        html = _creation_row_html()
        self.assertIn('id="btn-create-isolation"', html)
        self.assertIn('>Create</button>', html)

    def test_creation_row_input_styling(self):
        """Input uses the same color scheme as the header filter box (Section 2.8)."""
        html = _creation_row_html()
        self.assertIn('var(--purlin-surface)', html)
        self.assertIn('var(--purlin-primary)', html)
        self.assertIn('var(--purlin-border)', html)

    def test_no_sessions_table_when_empty(self):
        """_isolation_section_html returns empty when no worktrees exist (no table rows)."""
        html = _isolation_section_html([])
        self.assertEqual(html, "")


class TestNewIsolationInputCreatesNamedWorktree(unittest.TestCase):
    """Scenario: New Isolation Input Creates Named Worktree.

    Given no worktree exists at .worktrees/feat2
    And the CDD server is running
    When a POST request is sent to /isolate/create with body {"name": "feat2"}
    Then the response contains { "status": "ok" }
    And .worktrees/feat2/ is created on branch isolated/feat2
    And subsequent dashboard HTML contains a row with name "feat2" in the Sessions table.
    """

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_create_returns_ok(self, mock_exists, mock_run):
        """POST /isolate/create with valid name returns ok status."""
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        handler = MagicMock(spec=Handler)
        body = json.dumps({'name': 'feat2'}).encode('utf-8')
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()
        handler._handle_isolate_create = Handler._handle_isolate_create.__get__(
            handler, Handler)
        handler._handle_isolate_create()
        handler._send_json.assert_called_once_with(200, {'status': 'ok'})

    def test_created_worktree_appears_in_sessions_table(self):
        """After creation, a worktree with the name appears in generated HTML."""
        worktrees = [{
            'name': 'feat2', 'branch': 'isolated/feat2', 'main_diff': 'SAME',
            'committed': {'specs': 0, 'tests': 0, 'other': 0},
            'uncommitted': {'specs': 0, 'tests': 0, 'other': 0},
        }]
        html = _isolation_section_html(worktrees)
        self.assertIn('feat2', html)
        self.assertIn('isolated/feat2', html)


class TestLocalBranchHeadingBranchLabel(unittest.TestCase):
    """Scenarios: LOCAL BRANCH Heading Includes Branch Name,
    Branch Name Matches Git Branch, Heading Updates After Branch Change.

    Verifies that the LOCAL BRANCH section heading in generate_html()
    includes the current branch name from _get_collaboration_branch().
    """

    # Minimal mocks for generate_html dependencies
    _GH_PATCHES = {
        'serve.get_git_status': '',
        'serve.get_last_commit': 'abc1234 test (now)',
        'serve.get_isolation_worktrees': [],
        'serve.get_active_remote_session': None,
        'serve._has_git_remote': False,
        'serve.get_delivery_phase': None,
    }

    def _call_generate_html(self, branch_name):
        """Call generate_html with all deps mocked, returning the HTML string."""
        patches = {}
        for target, rv in self._GH_PATCHES.items():
            p = patch(target, return_value=rv)
            patches[target] = p.start()
        p_branch = patch('serve._get_collaboration_branch', return_value=branch_name)
        p_branch.start()
        p_api = patch('serve.generate_api_status_json', return_value={
            'features': [], 'critic_last_run': '', 'generated_at': '',
        })
        p_api.start()
        p_rc = patch('serve.get_release_checklist', return_value=([], [], []))
        p_rc.start()
        try:
            return generate_html()
        finally:
            patch.stopall()

    def test_heading_includes_branch_name(self):
        """LOCAL BRANCH heading contains the branch name (Section 2.3)."""
        html = self._call_generate_html('collab/purlincollab')
        self.assertIn('Local Branch (collab/purlincollab)', html)

    def test_branch_name_matches_mock_value(self):
        """Branch in heading matches whatever _get_collaboration_branch returns."""
        html = self._call_generate_html('feature/my-branch')
        self.assertIn('Local Branch (feature/my-branch)', html)
        self.assertNotIn('Local Branch (collab/', html)

    def test_heading_updates_after_branch_change(self):
        """Two calls with different branches produce different headings."""
        html1 = self._call_generate_html('main')
        html2 = self._call_generate_html('collab/test')
        self.assertIn('Local Branch (main)', html1)
        self.assertNotIn('Local Branch (collab/test)', html1)
        self.assertIn('Local Branch (collab/test)', html2)
        self.assertNotIn('Local Branch (main)', html2)


# ===================================================================
# Test runner with JSON result output
# ===================================================================

if __name__ == '__main__':
    # Discover project root for writing test results
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    tests_dir = os.path.join(project_root, 'tests', 'cdd_isolated_teams')
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
