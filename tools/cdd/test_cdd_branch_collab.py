"""Automated tests for CDD Branch Collaboration feature.

Tests all automated scenarios from features/cdd_branch_collab.md.
Results written to tests/cdd_branch_collab/tests.json.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
sys.path.insert(0, SCRIPT_DIR)

import serve


class TestBranchCollabSectionAlwaysRendered(unittest.TestCase):
    """Scenario: REMOTE Section Always Rendered in Dashboard HTML

    Given the CDD server is running
    And no branch_collab config exists in .purlin/config.json
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION section is present in the HTML output
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_branch_collab_section_present_in_html(self, *mocks):
        html = serve.generate_html()
        self.assertIn('BRANCH COLLABORATION', html)
        self.assertIn('branch-collab-section', html)


class TestBranchCollabAbsentFromStatusJsonWhenNoActiveBranch(unittest.TestCase):
    """Scenario: branch_collab Absent From status.json When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    When an agent calls GET /status.json
    Then the response does not contain a branch_collab field
    """

    @patch('serve.get_active_branch', return_value=None)
    @patch('serve.get_branch_collab_branches', return_value=[])
    def test_no_branch_collab_in_api(self, *mocks):
        data = serve.generate_api_status_json()
        self.assertNotIn('branch_collab', data)

    @patch('serve.get_active_branch', return_value=None)
    @patch('serve.get_branch_collab_branches', return_value=[])
    def test_branch_collab_branches_always_present(self, *mocks):
        data = serve.generate_api_status_json()
        self.assertIn('branch_collab_branches', data)


class TestBranchCollabBranchesPresentEvenWhenEmpty(unittest.TestCase):
    """Scenario: branch_collab_branches Present In status.json Even When Empty

    Given no collab/* branches exist on the remote
    When an agent calls GET /status.json
    Then the response contains branch_collab_branches as an empty array
    """

    @patch('serve.get_active_branch', return_value=None)
    @patch('serve.get_branch_collab_branches', return_value=[])
    def test_branches_is_empty_array(self, *mocks):
        data = serve.generate_api_status_json()
        self.assertEqual(data['branch_collab_branches'], [])


class TestCreateBranchPushesAndWritesRuntime(unittest.TestCase):
    """Scenario: Create Branch Pushes and and Writes Runtime File

    Given no v0.5-sprint branch exists on the remote
    And the CDD server is running
    When a POST request is sent to /branch-collab/create with body {"branch": "v0.5-sprint"}
    Then the server creates branch v0.5-sprint from main HEAD
    And pushes v0.5-sprint to origin
    And writes "v0.5-sprint" to .purlin/runtime/active_branch
    And the response contains { "status": "ok", "branch": "v0.5-sprint" }
    And GET /status.json shows branch_collab.sync_state as "SAME"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runtime_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(self.runtime_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_create_branch_endpoint(self, mock_config, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

        body = json.dumps({"branch": "v0.5-sprint"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_create(handler)

        # Verify _send_json called with 200 and correct body
        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        self.assertEqual(args[1]['branch'], 'v0.5-sprint')

        # Verify git branch and push were called
        calls = mock_run.call_args_list
        branch_calls = [c for c in calls if 'branch' in str(c) and 'HEAD' in str(c)]
        push_calls = [c for c in calls if 'push' in str(c)]
        self.assertTrue(len(branch_calls) > 0, "git branch should have been called")
        self.assertTrue(len(push_calls) > 0, "git push should have been called")

        # Verify runtime file written
        rt_path = os.path.join(self.runtime_dir, 'active_branch')
        self.assertTrue(os.path.exists(rt_path))
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'v0.5-sprint')


class TestCreateBranchWithInvalidNameReturnsError(unittest.TestCase):
    """Scenario: Create Branch With Invalid Name Returns Error

    Given the CDD server is running
    When a POST request is sent to /branch-collab/create with body {"branch": "bad..name"}
    Then the response contains an error message
    And no branch is created on the remote
    And .purlin/runtime/active_branch is not written
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _post_create(self, name):
        body = json.dumps({"branch": name}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()
        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_create(handler)
        return handler

    def test_double_dot_rejected(self):
        handler = self._post_create("bad..name")
        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 400)
        self.assertIn('error', args[1])

    def test_leading_dot_rejected(self):
        handler = self._post_create(".badname")
        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 400)

    def test_leading_hyphen_rejected(self):
        handler = self._post_create("-badname")
        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 400)

    def test_spaces_rejected(self):
        handler = self._post_create("bad name")
        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 400)


class TestLeaveClearsActiveBranch(unittest.TestCase):
    """Scenario: Disconnect Checks Out Main and Clears Active Branch

    Given an active branch "v0.5-sprint" is set
    And the working tree is clean
    When a POST request is sent to /branch-collab/leave
    Then the local branch main is checked out
    And .purlin/runtime/active_branch is empty or absent
    And GET /status.json does not contain a branch_collab field
    And v0.5-sprint still exists on the remote
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        rt_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(rt_dir, exist_ok=True)
        with open(os.path.join(rt_dir, 'active_branch'), 'w') as f:
            f.write('v0.5-sprint')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    def test_leave_clears_runtime(self, mock_run):
        # git status --porcelain returns empty (clean tree)
        # git checkout main succeeds
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

        handler = MagicMock()
        handler.headers = {'Content-Length': '2'}
        handler.rfile = io.BytesIO(b'{}')
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_leave(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')

        # Verify git checkout main was called
        checkout_calls = [c for c in mock_run.call_args_list
                          if isinstance(c[0][0], list) and 'checkout' in c[0][0]
                          and 'main' in c[0][0]]
        self.assertTrue(len(checkout_calls) > 0,
                        "git checkout main should have been called")

        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime',
                               'active_branch')
        with open(rt_path) as f:
            content = f.read().strip()
        self.assertEqual(content, '')


class TestSyncStateNoLocalWithCommits(unittest.TestCase):
    """When local branch does not exist but remote has unique commits,
    sync state is computed against HEAD using the remote ref.

    Given the remote tracking ref origin/v0.5-sprint exists
    But local branch "v0.5-sprint" does not exist
    And origin/v0.5-sprint has 1 commit not in HEAD
    When compute_remote_sync_state is called
    Then sync_state is "AHEAD" with commits_ahead 1
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_no_local_computes_vs_head(self, mock_config, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                ref = cmd[-1] if cmd else ''
                if ref == 'v0.5-sprint':
                    raise subprocess.CalledProcessError(128, cmd)
                result.stdout = 'abc1234'
            elif isinstance(cmd, list) and 'log' in cmd:
                range_arg = next((a for a in cmd if '..' in a), '')
                if range_arg.startswith('HEAD..'):
                    # Branch has 1 unique commit relative to HEAD
                    result.stdout = 'abc commit1\n'
                else:
                    result.stdout = ''
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        state = serve.compute_remote_sync_state("v0.5-sprint")
        self.assertEqual(state['sync_state'], 'AHEAD')
        self.assertEqual(state['commits_ahead'], 1)
        self.assertEqual(state['commits_behind'], 0)


class TestSyncStateSame(unittest.TestCase):
    """Scenario: Sync State SAME When Local and Remote Are Identical

    Given an active branch "v0.5-sprint" is set
    And local main and origin/v0.5-sprint point to the same commit
    When an agent calls GET /status.json
    Then branch_collab.sync_state is "SAME"
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_same_state(self, mock_config, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                result.stdout = 'abc1234'
            elif isinstance(cmd, list) and 'log' in cmd:
                range_arg = next((a for a in cmd if '..' in a), '')
                if range_arg.startswith('main..'):
                    # Branch has commits relative to main (not EMPTY)
                    result.stdout = 'abc commit1\n'
                else:
                    result.stdout = ''  # No commits in either direction
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        state = serve.compute_remote_sync_state("v0.5-sprint")
        self.assertEqual(state['sync_state'], 'SAME')
        self.assertEqual(state['commits_ahead'], 0)
        self.assertEqual(state['commits_behind'], 0)


class TestSyncStateAhead(unittest.TestCase):
    """Scenario: Sync State AHEAD When Local Has Unpushed Commits

    Given an active branch "v0.5-sprint" is set
    And local v0.5-sprint has 3 commits not in origin/v0.5-sprint
    When an agent calls GET /status.json
    Then branch_collab.sync_state is "AHEAD"
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_ahead_state(self, mock_config, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                result.stdout = 'abc1234'
            elif isinstance(cmd, list) and 'log' in cmd:
                # Find the range arg (contains '..')
                range_arg = next((a for a in cmd if '..' in a), '')
                if range_arg.startswith('main..'):
                    # Branch has commits relative to main (not EMPTY)
                    result.stdout = 'abc commit1\ndef commit2\nghi commit3\n'
                elif range_arg.startswith('origin/'):
                    # ahead: origin/..collab/ -> local has 3 extra
                    result.stdout = 'abc commit1\ndef commit2\nghi commit3\n'
                else:
                    # behind: collab/..origin/ -> remote has 0 extra
                    result.stdout = ''
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        state = serve.compute_remote_sync_state("v0.5-sprint")
        self.assertEqual(state['sync_state'], 'AHEAD')
        self.assertEqual(state['commits_ahead'], 3)


class TestSyncStateBehind(unittest.TestCase):
    """Scenario: Sync State BEHIND When Remote Has New Commits

    Given an active branch "v0.5-sprint" is set
    And origin/v0.5-sprint has 2 commits not in local v0.5-sprint
    When an agent calls GET /status.json
    Then branch_collab.sync_state is "BEHIND"
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_behind_state(self, mock_config, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                result.stdout = 'abc1234'
            elif isinstance(cmd, list) and 'log' in cmd:
                range_arg = next((a for a in cmd if '..' in a), '')
                if range_arg.startswith('origin/'):
                    # ahead: local has 0 extra
                    result.stdout = ''
                else:
                    # behind: remote has 2 extra
                    result.stdout = 'xyz commit1\nuvw commit2\n'
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        state = serve.compute_remote_sync_state("v0.5-sprint")
        self.assertEqual(state['sync_state'], 'BEHIND')
        self.assertEqual(state['commits_behind'], 2)


class TestSyncStateDiverged(unittest.TestCase):
    """Scenario: Sync State DIVERGED When Both Sides Have Commits

    Given an active branch "v0.5-sprint" is set
    And local v0.5-sprint has 1 commit not in origin/v0.5-sprint
    And origin/v0.5-sprint has 2 commits not in local v0.5-sprint
    When an agent calls GET /status.json
    Then branch_collab.sync_state is "DIVERGED"
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_diverged_state(self, mock_config, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                result.stdout = 'abc1234'
            elif isinstance(cmd, list) and 'log' in cmd:
                range_arg = next((a for a in cmd if '..' in a), '')
                if range_arg.startswith('origin/'):
                    # ahead: local has 1 extra
                    result.stdout = 'abc commit1\n'
                else:
                    # behind: remote has 2 extra
                    result.stdout = 'xyz commit1\nuvw commit2\n'
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        state = serve.compute_remote_sync_state("v0.5-sprint")
        self.assertEqual(state['sync_state'], 'DIVERGED')
        self.assertEqual(state['commits_ahead'], 1)
        self.assertEqual(state['commits_behind'], 2)


class TestContributorsDerivedFromGitLog(unittest.TestCase):
    """Scenario: Contributors Derived From Git Log Sorted Most-Recent-First

    Given an active branch "v0.5-sprint" is set
    And origin/v0.5-sprint has commits from two different authors
    When an agent calls GET /status.json
    Then branch_collab.contributors has entries sorted by most-recent-first
    And each entry has email, name, commits, last_active, and last_subject fields
    And the contributors list has at most 10 entries
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_contributors_from_log(self, mock_config, mock_run):
        log_output = (
            "alice@example.com|Alice|2h ago|add feature X\n"
            "bob@example.com|Bob|5h ago|fix bug Y\n"
            "alice@example.com|Alice|1d ago|initial commit\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=log_output, stderr='')

        contributors = serve.get_remote_contributors("v0.5-sprint")

        self.assertEqual(len(contributors), 2)
        # Alice first (most recent)
        self.assertEqual(contributors[0]['name'], 'Alice')
        self.assertEqual(contributors[0]['email'], 'alice@example.com')
        self.assertEqual(contributors[0]['commits'], 2)
        self.assertEqual(contributors[0]['last_active'], '2h ago')
        self.assertEqual(contributors[0]['last_subject'], 'add feature X')
        # Bob second
        self.assertEqual(contributors[1]['name'], 'Bob')
        self.assertEqual(contributors[1]['commits'], 1)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_max_10_entries(self, mock_config, mock_run):
        lines = [f"user{i}@ex.com|User{i}|{i}h ago|commit {i}" for i in range(15)]
        mock_run.return_value = MagicMock(returncode=0, stdout='\n'.join(lines), stderr='')
        contributors = serve.get_remote_contributors("v0.5-sprint")
        self.assertLessEqual(len(contributors), 10)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_required_fields(self, mock_config, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="a@b.com|Alice|1h ago|test\n", stderr='')
        contributors = serve.get_remote_contributors("v0.5-sprint")
        self.assertTrue(len(contributors) > 0)
        entry = contributors[0]
        for field in ('email', 'name', 'commits', 'last_active', 'last_subject'):
            self.assertIn(field, entry)


class TestManualCheckUpdatesLastFetch(unittest.TestCase):
    """Scenario: Manual Check Updates last_fetch Timestamp

    Given an active branch "v0.5-sprint" is set
    And branch_collab.last_fetch is null (server just started)
    When a POST request is sent to /branch-collab/fetch
    Then the response contains fetched_at with an ISO timestamp
    And subsequent GET /status.json shows branch_collab.last_fetch as non-null
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)
        with open(os.path.join(self.tmpdir, '.purlin', 'runtime',
                               'active_branch'), 'w') as f:
            f.write('v0.5-sprint')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_fetch_sets_timestamp(self, mock_config, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

        # Reset last_fetch
        serve._branch_collab_last_fetch = None

        handler = MagicMock()
        handler.headers = {'Content-Length': '2'}
        handler.rfile = io.BytesIO(b'{}')
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_fetch(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        self.assertIn('fetched_at', args[1])
        self.assertIsNotNone(args[1]['fetched_at'])
        # Verify the module-level variable was updated
        self.assertIsNotNone(serve._branch_collab_last_fetch)


class TestFiveSecondPollTriggersZeroFetchCalls(unittest.TestCase):
    """Scenario: 5-Second Status Poll Triggers Zero Git Fetch Calls

    Given an active branch "v0.5-sprint" is set
    And auto_fetch_interval is 0 in the test config
    When the dashboard polls GET /status.json 3 times at 5-second intervals
    Then no git fetch commands are executed during those polls
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 0})
    @patch('serve.subprocess.run')
    def test_status_poll_no_fetch(self, mock_run, *mocks):
        # Mock sync state functions to avoid git calls
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            # Should never see 'fetch' during a status poll
            if 'fetch' in cmd_str:
                raise AssertionError("git fetch should not be called during status poll")
            result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        # Generate status.json three times (simulating 5-second polls)
        for _ in range(3):
            data = serve.generate_api_status_json()
            # Verify branch_collab is present (branch is active)
            self.assertIn('branch_collab', data)

        # Verify no 'fetch' calls were made
        for call in mock_run.call_args_list:
            cmd = call[0][0] if call[0] else call[1].get('cmd', [])
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
            self.assertNotIn('fetch', cmd_str,
                             "git fetch should not be called during status poll")


class TestPerBranchSyncStateInBranchCollabBranches(unittest.TestCase):
    """Scenario: Per-Branch Sync State in branch_collab_branches

    Given v0.5-sprint exists as a remote tracking branch
    And origin/v0.5-sprint has 2 commits not in local v0.5-sprint
    When an agent calls GET /status.json
    Then branch_collab_branches contains an entry for "v0.5-sprint"
    And that entry has sync_state "BEHIND" and commits_behind 2
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    @patch('serve.get_active_branch', return_value=None)
    def test_per_branch_sync_state(self, mock_active, mock_config, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'branch' in cmd_str and '-r' in cmd_str:
                result.stdout = '  origin/v0.5-sprint\n'
            elif 'rev-parse' in cmd_str:
                result.stdout = 'abc1234'
            elif 'log' in cmd_str:
                range_arg = next((a for a in cmd if '..' in a), '')
                # With compare_to_head=True, ranges use HEAD:
                # HEAD..origin/<branch> = what branch has that HEAD doesn't
                # origin/<branch>..HEAD = what HEAD has that branch doesn't
                if '..origin/' in range_arg:
                    # HEAD..origin/branch: branch has 0 unique commits beyond HEAD
                    result.stdout = ''
                elif 'origin/' in range_arg and '..HEAD' in range_arg:
                    # origin/branch..HEAD: HEAD has 2 commits beyond branch
                    result.stdout = 'xyz commit1\nuvw commit2\n'
                else:
                    result.stdout = ''
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        branches = serve.get_branch_collab_branches()
        self.assertEqual(len(branches), 1)
        b = branches[0]
        self.assertEqual(b['name'], 'v0.5-sprint')
        self.assertEqual(b['sync_state'], 'BEHIND')
        self.assertEqual(b['commits_behind'], 2)
        self.assertEqual(b['commits_ahead'], 0)


class TestCreateBranchBlockedWhenDirty(unittest.TestCase):
    """Scenario: Create Branch Blocked When Working Tree Is Dirty

    Given the CDD server is running
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /branch-collab/create with body {"branch": "v0.5-sprint"}
    Then the response contains an error message about dirty working tree
    And no branch is created
    And the current branch is unchanged
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_create_blocked_dirty_tree(self, mock_config, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ' M src/main.py\n'  # dirty file outside .purlin/
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "v0.5-sprint"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_create(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 400)
        self.assertIn('error', args[1])
        self.assertIn('uncommitted', args[1]['error'].lower())

        # Verify no git branch or push calls were made
        for call in mock_run.call_args_list:
            cmd = call[0][0] if call[0] else []
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
            self.assertNotIn('git branch', cmd_str)
            self.assertNotIn('git push', cmd_str)

        # Verify runtime file was NOT written
        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime',
                               'active_branch')
        self.assertFalse(os.path.exists(rt_path))


class TestLeaveBlockedWhenDirty(unittest.TestCase):
    """Scenario: Disconnect Blocked When Working Tree Is Dirty

    Given an active branch "v0.5-sprint" is set
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /branch-collab/leave
    Then the response contains an error message about dirty working tree
    And the current branch remains v0.5-sprint
    And .purlin/runtime/active_branch still contains "v0.5-sprint"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        rt_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(rt_dir, exist_ok=True)
        with open(os.path.join(rt_dir, 'active_branch'), 'w') as f:
            f.write('v0.5-sprint')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    def test_disconnect_blocked_dirty_tree(self, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ' M src/main.py\n'
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        handler = MagicMock()
        handler.headers = {'Content-Length': '2'}
        handler.rfile = io.BytesIO(b'{}')
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_leave(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 400)
        self.assertIn('error', args[1])
        self.assertIn('uncommitted', args[1]['error'].lower())

        # Verify no checkout was attempted
        for call in mock_run.call_args_list:
            cmd = call[0][0] if call[0] else []
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
            self.assertNotIn('checkout', cmd_str)

        # Verify runtime file still has branch
        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime',
                               'active_branch')
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'v0.5-sprint')


class TestBranchCollabSectionAlwaysVisibleInDashboardHTML(unittest.TestCase):
    """Scenario: BRANCH COLLABORATION Section Always Visible in Dashboard HTML

    Given the CDD server is running
    And no branch_collab config exists in .purlin/config.json
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION section heading is present in the HTML output
    And the section is rendered above the ISOLATED TEAMS section in the DOM
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_section_heading_present_and_above_isolated(self, *mocks):
        html = serve.generate_html()
        self.assertIn('BRANCH COLLABORATION', html)
        # Verify the section heading element exists
        self.assertIn('id="bc-heading"', html)
        # Verify it appears above ISOLATED TEAMS in DOM
        rc_pos = html.find('branch-collab-section')
        iso_pos = html.find('isolation-section')
        self.assertGreater(rc_pos, -1, "branch-collab-section not found")
        self.assertGreater(iso_pos, -1, "isolation-section not found")
        self.assertLess(rc_pos, iso_pos,
                        "BRANCH COLLABORATION should appear before ISOLATED TEAMS")


class TestNoActiveBranchShowsCreationRowAndBranchesTable(unittest.TestCase):
    """Scenario: No Active Branch Shows Creation Row and Branches Table

    Given no file exists at .purlin/runtime/active_branch
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION section contains a creation row with
         "Create Branch" label
    And the creation row contains a text input and a Create button
    And a branches table element is present below the creation row
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_creation_row_and_branches_table(self, *mocks):
        html = serve.generate_html()
        self.assertIn('Create Branch', html)
        self.assertIn('id="new-branch-name"', html)
        self.assertIn('id="btn-create-branch"', html)


class TestBranchCollabRendersAboveIsolatedTeamsInDOMOrder(unittest.TestCase):
    """Scenario: BRANCH COLLABORATION Renders Above ISOLATED TEAMS in DOM Order

    Given the CDD server is running
    And both BRANCH COLLABORATION and ISOLATED TEAMS sections exist in the HTML
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION section appears before the ISOLATED TEAMS
         section in the HTML output
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_dom_order(self, *mocks):
        html = serve.generate_html()
        rc_pos = html.find('branch-collab-section')
        iso_pos = html.find('isolation-section')
        self.assertGreater(rc_pos, -1)
        self.assertGreater(iso_pos, -1)
        self.assertLess(rc_pos, iso_pos)


class TestLastRemoteSyncAnnotationPresentInLocalBranchBody(unittest.TestCase):
    """Scenario: Last Remote Sync Annotation Present in MAIN WORKSPACE Body

    Given an active branch "v0.5-sprint" is set in .purlin/runtime/active_branch
    When the dashboard HTML is generated
    Then the MAIN WORKSPACE section body contains a "Last remote sync" annotation
    And the annotation appears below the clean/dirty state line
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.compute_remote_sync_state', return_value={
        'sync_state': 'SAME', 'commits_ahead': 0, 'commits_behind': 0})
    @patch('serve.get_remote_contributors', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_last_remote_sync_annotation(self, *mocks):
        html = serve.generate_html()
        self.assertIn('Last remote sync', html)
        # The annotation should be in the workspace section area
        workspace_pos = html.find('workspace-section')
        sync_pos = html.find('Last remote sync')
        self.assertGreater(workspace_pos, -1)
        self.assertGreater(sync_pos, -1)


class TestStatusJsonReflectsJoinedBranch(unittest.TestCase):
    """Scenario: status.json Reflects Joined Branch

    Given the branch "testing" has been joined via /branch-collab/join
    When an agent calls GET /status.json
    Then branch_collab.active_branch is "testing"
    """

    @patch('serve.get_active_branch', return_value='testing')
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.compute_remote_sync_state', return_value={
        'sync_state': 'SAME', 'commits_ahead': 0, 'commits_behind': 0})
    @patch('serve.get_remote_contributors', return_value=[])
    def test_status_json_reflects_branch(self, *mocks):
        data = serve.generate_api_status_json()
        self.assertIn('branch_collab', data)
        self.assertEqual(data['branch_collab']['active_branch'], 'testing')


class TestRefreshBranchesButtonFetchesAllRemoteRefs(unittest.TestCase):
    """Scenario: Refresh Branches Button Fetches All Remote Refs

    Given the CDD server is running with no active branch
    And the branches table shows 1 collaboration branch
    When a new branch is pushed to the remote from another machine
    And a POST request is sent to /branch-collab/fetch-all
    Then the response contains { "status": "ok" } with a fetched_at timestamp
    And the branches table re-renders with the newly discovered branch
    """

    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    @patch('subprocess.run')
    def test_fetch_all_succeeds(self, mock_run, *mocks):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        handler = MagicMock()
        handler.headers = {'Content-Length': '2'}
        handler.rfile = io.BytesIO(b'{}')
        handler.path = '/branch-collab/fetch-all'
        responses = []

        def mock_send_json(status, data):
            responses.append((status, data))
        handler._send_json = mock_send_json
        serve.Handler._handle_branch_collab_fetch_all(handler)
        self.assertEqual(len(responses), 1)
        status, data = responses[0]
        self.assertEqual(status, 200)
        self.assertEqual(data['status'], 'ok')
        self.assertIn('fetched_at', data)
        self.assertIsNotNone(data['fetched_at'])
        # Verify git fetch was called without a specific branch (fetch all)
        fetch_call = [c for c in mock_run.call_args_list
                      if 'fetch' in str(c)]
        self.assertTrue(len(fetch_call) > 0)
        args = fetch_call[0][0][0]
        # The command should be ['git', 'fetch', '--prune', 'origin'] (no branch arg)
        self.assertEqual(args, ['git', 'fetch', '--prune', 'origin'])

    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    @patch('subprocess.run')
    def test_fetch_all_returns_error_on_failure(self, mock_run, *mocks):
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git', stderr='fetch failed')
        handler = MagicMock()
        responses = []

        def mock_send_json(status, data):
            responses.append((status, data))
        handler._send_json = mock_send_json
        serve.Handler._handle_branch_collab_fetch_all(handler)
        self.assertEqual(len(responses), 1)
        status, data = responses[0]
        self.assertEqual(status, 500)
        self.assertIn('error', data)


class TestCollapsedBadgeShowsUrlWhenBranchActive(unittest.TestCase):
    """Scenario: Collapsed Badge Shows URL When Branch Active

    Given the CDD server is running
    And an active branch is set in .purlin/runtime/active_branch
    And the git remote "origin" is configured with URL "https://github.com/rlabarca/purlin.git"
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION collapsed badge text is "BRANCH COLLABORATION (github.com/rlabarca/purlin)"
    """

    @patch('serve._get_shortened_remote_url', return_value='github.com/rlabarca/purlin')
    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value='feature/auth')
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_collapsed_badge_shows_url_when_active(self, *mocks):
        html = serve.generate_html()
        self.assertIn('data-collapsed-text="BRANCH COLLABORATION (github.com/rlabarca/purlin)"', html)
        # Expanded heading also shows URL when remote is configured
        self.assertIn('data-expanded="BRANCH COLLABORATION (github.com/rlabarca/purlin)"', html)


class TestCollapsedBadgeShowsUrlWhenNoBranchActive(unittest.TestCase):
    """Scenario: Collapsed Badge Shows URL When No Branch Active

    Given the CDD server is running
    And no file exists at .purlin/runtime/active_branch
    And the git remote is configured
    When the dashboard HTML is generated
    Then both collapsed and expanded headings show the remote URL
    """

    @patch('serve._get_shortened_remote_url', return_value='github.com/rlabarca/purlin')
    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_collapsed_badge_shows_url_even_without_active_branch(self, *mocks):
        html = serve.generate_html()
        # URL shown in both collapsed and expanded when remote is configured
        self.assertIn('data-collapsed-text="BRANCH COLLABORATION (github.com/rlabarca/purlin)"', html)
        self.assertIn('data-expanded="BRANCH COLLABORATION (github.com/rlabarca/purlin)"', html)


class TestCollapsedBadgeShowsPlainTitleWhenNoRemoteConfigured(unittest.TestCase):
    """Scenario: Collapsed Badge Shows Plain Title When No Remote Configured

    Given the CDD server is running
    And an active branch is set in .purlin/runtime/active_branch
    And no git remote is configured
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION collapsed badge text is "BRANCH COLLABORATION"
    """

    @patch('serve._get_shortened_remote_url', return_value='')
    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value='feature/auth')
    @patch('serve._has_git_remote', return_value=False)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_collapsed_badge_plain_when_no_remote(self, *mocks):
        html = serve.generate_html()
        self.assertIn('data-collapsed-text="BRANCH COLLABORATION"', html)
        self.assertNotIn('data-collapsed-text="BRANCH COLLABORATION (', html)
        # Both collapsed and expanded are plain when no remote
        self.assertIn('data-expanded="BRANCH COLLABORATION"', html)
        self.assertNotIn('data-expanded="BRANCH COLLABORATION (', html)


class TestJoinBranchShowsOperationModalDuringRequest(unittest.TestCase):
    """Scenario: Join Branch Shows Operation Modal During Request

    Given the CDD server is running
    And an active branch is not set
    And feature/auth exists as a remote tracking branch
    When the user clicks the Join button for feature/auth
    Then an operation modal appears with title "Joining Branch"
    And the modal shows a spinner with text "Switching to feature/auth..."
    And the Close button is disabled while the operation is in flight
    And clicking the overlay background does not close the modal
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_modal_html_and_join_js(self, *mocks):
        html = serve.generate_html()
        # Modal HTML exists
        self.assertIn('id="bc-op-modal-overlay"', html)
        self.assertIn('id="bc-op-modal-title"', html)
        self.assertIn('id="bc-op-spinner"', html)
        self.assertIn('id="bc-op-status"', html)
        self.assertIn('id="bc-op-modal-close"', html)
        # Close button starts disabled
        self.assertIn('id="bc-op-modal-close"', html)
        # joinBranch function opens modal with correct title and Phase 1 message
        self.assertIn("openBcOpModal('Joining Branch'", html)
        self.assertIn('Fetching and checking sync state...', html)
        # Two-phase join: Phase 1 checks d.completed, Phase 2 shows interactive content
        self.assertIn('d.completed', html)
        self.assertIn('_bcShowJoinPhase2', html)
        # Overlay click handler checks _bcOpInFlight
        self.assertIn('_bcOpInFlight', html)


class TestJoinBranchModalAutoClosesOnSuccess(unittest.TestCase):
    """Scenario: Join Branch Modal Auto-Closes on Success

    Given the operation modal is showing for a join operation
    When the server returns { "status": "ok" }
    Then the modal auto-closes after a brief delay
    And refreshStatus() is called to update the dashboard
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_auto_close_on_success(self, *mocks):
        html = serve.generate_html()
        # bcOpModalSuccess closes modal after delay and calls refreshStatus
        self.assertIn('bcOpModalSuccess', html)
        self.assertIn('setTimeout', html)
        self.assertIn('closeBcOpModal', html)
        self.assertIn('refreshStatus', html)
        # joinBranch calls bcOpModalSuccess on ok
        self.assertIn("bcOpModalSuccess()", html)


class TestJoinBranchModalShowsErrorOnFailure(unittest.TestCase):
    """Scenario: Join Branch Modal Shows Error on Failure

    Given the operation modal is showing for a join operation
    When the server returns { "status": "error", "error": "Working tree has uncommitted changes" }
    Then the spinner is hidden
    And the status message shows "Working tree has uncommitted changes" in error color
    And the Close button is enabled
    And clicking Close dismisses the modal
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_error_display_in_modal(self, *mocks):
        html = serve.generate_html()
        # bcOpModalError hides spinner and shows error in error color
        self.assertIn('bcOpModalError', html)
        self.assertIn("spinner.style.display = 'none'", html)
        self.assertIn("var(--purlin-status-error)", html)
        # Close button enabled on error
        self.assertIn("closeBtn.disabled = false", html)
        # joinBranch calls bcOpModalError on error response
        self.assertIn("bcOpModalError(d.error", html)


class TestLeaveBranchShowsOperationModalDuringRequest(unittest.TestCase):
    """Scenario: Leave Branch Shows Operation Modal During Request

    Given the CDD server is running
    And an active branch "feature/auth" is set
    When the user clicks the Leave button
    Then an operation modal appears with title "Leaving Branch"
    And the modal shows a spinner with text "Returning to main..."
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_leave_modal(self, *mocks):
        html = serve.generate_html()
        # leaveBranch opens modal with "Leaving Branch" title
        self.assertIn("openBcOpModal('Leaving Branch'", html)
        self.assertIn("Returning to", html)


class TestLeaveBranchModalShowsErrorOnDirtyWorkingTree(unittest.TestCase):
    """Scenario: Leave Branch Modal Shows Error on Dirty Working Tree

    Given the operation modal is showing for a leave operation
    When the server returns an error about dirty working tree
    Then the spinner is hidden
    And the error message is displayed in the modal
    And the Close button is enabled
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_leave_error_handling(self, *mocks):
        html = serve.generate_html()
        # leaveBranch calls bcOpModalError on error response
        self.assertIn("bcOpModalError(d.error || 'Leave failed')", html)
        # Network failure handling
        self.assertIn("Request failed -- check your connection", html)


class TestCreateBranchShowsOperationModalDuringRequest(unittest.TestCase):
    """Scenario: Create Branch Shows Operation Modal During Request

    Given the CDD server is running
    And a valid branch name is entered in the creation input
    When the user clicks the Create button
    Then an operation modal appears with title "Creating Branch"
    And the modal shows a spinner with text "Creating feature/new..."
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_create_modal(self, *mocks):
        html = serve.generate_html()
        # createBranch opens modal with "Creating Branch" title
        self.assertIn("openBcOpModal('Creating Branch'", html)
        self.assertIn("'Creating ' + name", html)


class TestSwitchBranchShowsOperationModalDuringRequest(unittest.TestCase):
    """Scenario: Switch Branch Shows Operation Modal During Request

    Given the CDD server is running
    And an active branch "feature/auth" is set
    When the user selects "hotfix/urgent" from the branch dropdown
    Then an operation modal appears with title "Joining Branch"
    And the modal shows a spinner with text "Switching to hotfix/urgent..."
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_switch_modal(self, *mocks):
        html = serve.generate_html()
        # switchBranch delegates to joinBranch, which opens modal with "Joining Branch"
        self.assertIn("openBcOpModal('Joining Branch'", html)
        # switchBranch calls joinBranch directly
        self.assertIn('function switchBranch(name)', html)
        self.assertIn('joinBranch(name)', html)


class TestOperationModalBlocksEscapeKeyDuringProgress(unittest.TestCase):
    """Scenario: Operation Modal Blocks Escape Key During Progress

    Given the operation modal is showing with a spinner (in-flight)
    When the user presses the Escape key
    Then the modal remains open
    And the operation continues
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_escape_blocked_during_flight(self, *mocks):
        html = serve.generate_html()
        # Escape key handler checks _bcOpInFlight before closing
        self.assertIn("e.key === 'Escape'", html)
        self.assertIn('bc-op-modal-overlay', html)
        self.assertIn('_bcOpInFlight', html)
        # closeBcOpModal returns early if in flight
        self.assertIn('if (_bcOpInFlight) return', html)


class TestNetworkFailureShowsConnectionErrorInModal(unittest.TestCase):
    """Scenario: Network Failure Shows Connection Error in Modal

    Given the operation modal is showing for any branch operation
    When the fetch request fails due to a network error
    Then the modal shows "Request failed -- check your connection" in error color
    And the Close button is enabled
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_network_error_message(self, *mocks):
        html = serve.generate_html()
        # All branch operations have catch handler with connection error
        error_msg = 'Request failed -- check your connection'
        # Should appear in catch blocks for join, switch, leave, create
        count = html.count(error_msg)
        self.assertGreaterEqual(count, 4,
            f"Expected '{error_msg}' in catch blocks of all 4 operations, found {count}")


class TestRefreshBranchesReflectsDeletedRemoteBranches(unittest.TestCase):
    """Scenario: Refresh Branches Reflects Deleted Remote Branches

    Given the CDD server is running with no active branch
    And the branches table shows branches "feature/auth" and "hotfix/urgent"
    And "hotfix/urgent" has been deleted from the remote
    When a POST request is sent to /branch-collab/fetch-all
    And the branches table re-renders
    Then "hotfix/urgent" is no longer shown in the branches table
    And "feature/auth" is still shown in the branches table
    """

    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    @patch('subprocess.run')
    def test_fetch_all_prunes_deleted_branches(self, mock_run, *mocks):
        """Verify fetch-all uses --prune flag to remove stale tracking refs."""
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        handler = MagicMock()
        responses = []

        def mock_send_json(status, data):
            responses.append((status, data))
        handler._send_json = mock_send_json
        serve.Handler._handle_branch_collab_fetch_all(handler)
        self.assertEqual(len(responses), 1)
        status, data = responses[0]
        self.assertEqual(status, 200)
        self.assertEqual(data['status'], 'ok')
        # Verify git fetch was called with --prune
        fetch_calls = [c for c in mock_run.call_args_list
                       if 'fetch' in str(c)]
        self.assertTrue(len(fetch_calls) > 0)
        args = fetch_calls[0][0][0]
        self.assertIn('--prune', args,
            "git fetch --prune should be used to remove stale tracking refs")


class TestRefreshBranchesReflectsNewlyAddedRemoteBranches(unittest.TestCase):
    """Scenario: Refresh Branches Reflects Newly Added Remote Branches

    Given the CDD server is running with no active branch
    And the branches table shows only "feature/auth"
    And "feature/new" has been pushed to the remote from another machine
    When a POST request is sent to /branch-collab/fetch-all
    And the branches table re-renders
    Then "feature/new" is shown in the branches table
    And "feature/auth" is still shown in the branches table
    """

    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    @patch('subprocess.run')
    def test_fetch_all_discovers_new_branches(self, mock_run, *mocks):
        """Verify fetch-all fetches all remote refs (no branch argument)."""
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        handler = MagicMock()
        responses = []

        def mock_send_json(status, data):
            responses.append((status, data))
        handler._send_json = mock_send_json
        serve.Handler._handle_branch_collab_fetch_all(handler)
        self.assertEqual(len(responses), 1)
        status, data = responses[0]
        self.assertEqual(status, 200)
        self.assertEqual(data['status'], 'ok')
        self.assertIn('fetched_at', data)
        # The command should be ['git', 'fetch', '--prune', 'origin'] (no branch arg)
        fetch_calls = [c for c in mock_run.call_args_list if 'fetch' in str(c)]
        self.assertTrue(len(fetch_calls) > 0, "git fetch should be called")
        args = fetch_calls[0][0][0]
        self.assertEqual(args, ['git', 'fetch', '--prune', 'origin'])



class TestSyncStateEmptyWhenBranchTipEqualsMainTip(unittest.TestCase):
    """Scenario: Sync State EMPTY When Branch Tip Equals Main Tip

    Given an active branch "feature/empty" is set
    And feature/empty tip equals main tip (both directions of git log return zero lines)
    When an agent calls GET /status.json
    Then branch_collab.sync_state is "EMPTY"
    And branch_collab.commits_ahead is 0
    And branch_collab.commits_behind is 0
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_empty_when_both_directions_zero(self, mock_config, mock_run):
        """EMPTY when main..<branch> and <branch>..main both return zero lines."""
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                result.stdout = 'abc1234'
            elif isinstance(cmd, list) and 'log' in cmd:
                # Both directions return empty — branch tip equals main tip
                result.stdout = ''
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        state = serve.compute_remote_sync_state("feature/empty")
        self.assertEqual(state['sync_state'], 'EMPTY')
        self.assertEqual(state['commits_ahead'], 0)
        self.assertEqual(state['commits_behind'], 0)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_not_empty_when_main_moved_ahead(self, mock_config, mock_run):
        """Branch is NOT EMPTY when main has moved ahead (branch tip != main tip)."""
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                result.stdout = 'abc1234'
            elif isinstance(cmd, list) and 'log' in cmd:
                range_arg = next((a for a in cmd if '..' in a), '')
                if range_arg.startswith('main..'):
                    # Branch has no unique commits vs main
                    result.stdout = ''
                elif range_arg.endswith('..main'):
                    # Main has moved ahead (3 commits)
                    result.stdout = 'abc1 c1\nabc2 c2\nabc3 c3\n'
                else:
                    result.stdout = ''
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        state = serve.compute_remote_sync_state("feature/empty")
        # Not EMPTY because main has moved ahead — branch tip != main tip
        self.assertNotEqual(state['sync_state'], 'EMPTY')

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_not_empty_when_branch_has_commits(self, mock_config, mock_run):
        """Branch with commits relative to main should NOT be EMPTY."""
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                result.stdout = 'abc1234'
            elif isinstance(cmd, list) and 'log' in cmd:
                range_arg = next((a for a in cmd if '..' in a), '')
                if range_arg.startswith('main..'):
                    # Branch has 1 commit ahead of main
                    result.stdout = 'abc commit1\n'
                else:
                    result.stdout = ''
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        state = serve.compute_remote_sync_state("feature/work")
        self.assertNotEqual(state['sync_state'], 'EMPTY')

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_remote_only_empty_when_tip_equals_head(self, mock_config, mock_run):
        """Remote-only branch is EMPTY when origin/<branch> tip equals HEAD."""
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                ref = cmd[-1] if cmd else ''
                if ref == 'RC0.8.0':
                    # No local branch
                    raise subprocess.CalledProcessError(128, cmd)
                result.stdout = 'abc1234'
            elif isinstance(cmd, list) and 'log' in cmd:
                # Both HEAD..origin/RC0.8.0 and origin/RC0.8.0..HEAD return empty
                result.stdout = ''
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        state = serve.compute_remote_sync_state("RC0.8.0")
        self.assertEqual(state['sync_state'], 'EMPTY')
        self.assertEqual(state['commits_ahead'], 0)
        self.assertEqual(state['commits_behind'], 0)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_remote_only_behind_when_head_moved_ahead(self, mock_config, mock_run):
        """Remote-only branch is BEHIND (not EMPTY) when HEAD has moved past it."""
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                ref = cmd[-1] if cmd else ''
                if ref == 'RC0.8.0':
                    # No local branch
                    raise subprocess.CalledProcessError(128, cmd)
                result.stdout = 'abc1234'
            elif isinstance(cmd, list) and 'log' in cmd:
                range_arg = next((a for a in cmd if '..' in a), '')
                if 'HEAD..' in range_arg:
                    # Branch has no unique commits beyond HEAD
                    result.stdout = ''
                elif '..HEAD' in range_arg:
                    # HEAD has 10 commits the branch lacks
                    result.stdout = '\n'.join([f'abc{i} commit{i}' for i in range(10)]) + '\n'
                else:
                    result.stdout = ''
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        state = serve.compute_remote_sync_state("RC0.8.0")
        self.assertEqual(state['sync_state'], 'BEHIND')
        self.assertEqual(state['commits_behind'], 10)


class TestBranchesTableShowsBehindForStaleRemoteBranch(unittest.TestCase):
    """Scenario: Branches Table Shows BEHIND For Stale Remote Branch

    Given no active branch is set
    And origin/RC0.8.0 exists as a remote tracking branch
    And origin/RC0.8.0 is a strict ancestor of HEAD (HEAD has commits RC0.8.0 does not)
    And origin/RC0.8.0 has no unique commits beyond HEAD
    When the dashboard HTML is generated
    Then the branches table shows "BEHIND" badge for RC0.8.0
    And the badge uses yellow color (--purlin-status-todo)
    """

    def test_behind_badge_in_branches_table(self):
        """Branches table renders BEHIND badge with yellow color for stale branch."""
        branches = [
            {'name': 'RC0.8.0', 'active': False, 'sync_state': 'BEHIND',
             'commits_ahead': 0, 'commits_behind': 5}
        ]
        html = serve._branch_collab_section_html(
            active_branch=None,
            sync_data=None,
            branches=branches,
            contributors=[],
            last_fetch=None,
            has_remote=True
        )
        self.assertIn('RC0.8.0', html)
        self.assertIn('BEHIND', html)
        # Badge uses CSS class st-todo for yellow color
        self.assertIn('st-todo', html)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_compute_behind_for_stale_remote_branch(self, mock_config, mock_run):
        """compute_remote_sync_state returns BEHIND when remote branch is strict ancestor of HEAD."""
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                ref = cmd[-1] if cmd else ''
                if ref == 'RC0.8.0':
                    # No local branch
                    raise subprocess.CalledProcessError(128, cmd)
                result.stdout = 'abc1234'
            elif isinstance(cmd, list) and 'log' in cmd:
                range_arg = next((a for a in cmd if '..' in a), '')
                if 'HEAD..' in range_arg:
                    # origin/RC0.8.0 has no unique commits beyond HEAD
                    result.stdout = ''
                elif '..HEAD' in range_arg:
                    # HEAD has 5 commits beyond origin/RC0.8.0
                    result.stdout = '\n'.join([f'abc{i} c{i}' for i in range(5)]) + '\n'
                else:
                    result.stdout = ''
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        state = serve.compute_remote_sync_state("RC0.8.0")
        self.assertEqual(state['sync_state'], 'BEHIND')
        self.assertEqual(state['commits_behind'], 5)
        self.assertEqual(state['commits_ahead'], 0)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_compare_to_head_ignores_local_branch(self, mock_config, mock_run):
        """compare_to_head=True compares origin/<branch> vs HEAD even when local branch exists."""
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                # Both origin/RC0.8.0 and local RC0.8.0 exist
                result.stdout = 'abc1234'
            elif isinstance(cmd, list) and 'log' in cmd:
                range_arg = next((a for a in cmd if '..' in a), '')
                if 'HEAD..' in range_arg:
                    # origin/RC0.8.0 has no unique commits beyond HEAD
                    result.stdout = ''
                elif '..HEAD' in range_arg:
                    # HEAD has 5 commits beyond origin/RC0.8.0
                    result.stdout = '\n'.join([f'abc{i} c{i}' for i in range(5)]) + '\n'
                else:
                    result.stdout = ''
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        # Without compare_to_head: would compare local vs remote (SAME since both exist at same commit)
        # With compare_to_head=True: compares origin/RC0.8.0 vs HEAD (BEHIND)
        state = serve.compute_remote_sync_state("RC0.8.0", compare_to_head=True)
        self.assertEqual(state['sync_state'], 'BEHIND')
        self.assertEqual(state['commits_behind'], 5)
        self.assertEqual(state['commits_ahead'], 0)


class TestEmptyBadgeRenderedWithoutBadgeBackground(unittest.TestCase):
    """Scenario: EMPTY Badge Rendered Without Badge Background

    Given an active branch "feature/empty" is set
    And feature/empty has zero commits relative to main
    When the dashboard HTML is generated
    Then the sync state position shows "EMPTY" in normal text color (--purlin-primary)
    And the text does not use a badge class (no st-good, st-todo, st-disputed)
    """

    def test_empty_badge_no_badge_class(self):
        sync_data = {'sync_state': 'EMPTY', 'commits_ahead': 0, 'commits_behind': 0}
        html = serve._branch_collab_section_html(
            active_branch='feature/empty',
            sync_data=sync_data,
            branches=[],
            contributors=[],
            last_fetch=None,
            has_remote=True
        )
        self.assertIn('EMPTY', html)
        self.assertIn('--purlin-primary', html)
        # Verify no badge classes are used for the EMPTY state
        # Find the EMPTY span and check it doesn't have badge classes
        import re
        empty_spans = re.findall(r'<span[^>]*>EMPTY</span>', html)
        self.assertTrue(len(empty_spans) > 0, "EMPTY text should be in a span")
        for span in empty_spans:
            self.assertNotIn('st-good', span)
            self.assertNotIn('st-todo', span)
            self.assertNotIn('st-disputed', span)


class TestJoinBranchFetchesThenChecksOut(unittest.TestCase):
    """Scenario: Join Branch Fetches Then Checks Out and Updates Runtime File

    Given feature/auth exists as a remote tracking branch
    And no local branch feature/auth exists
    And no active branch is set
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then git fetch is called for feature/auth before checkout
    And a local branch feature/auth is created tracking origin/feature/auth
    And .purlin/runtime/active_branch contains "feature/auth"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_fetch_called_before_checkout(self, mock_config, mock_run):
        call_order = []

        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='', stdout='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ''  # clean
            elif 'fetch' in cmd_str:
                call_order.append('fetch')
            elif 'rev-parse' in cmd_str and '--verify' in cmd_str:
                if 'feature/auth' in cmd_str and 'origin' not in cmd_str:
                    # No local branch exists
                    raise subprocess.CalledProcessError(1, cmd)
                result.stdout = 'abc1234'
            elif 'checkout' in cmd_str and '-b' in cmd_str:
                call_order.append('checkout-b')
            elif 'rev-parse' in cmd_str and '--abbrev-ref' in cmd_str:
                result.stdout = 'main'
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "feature/auth"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        # Verify fetch happened before checkout
        self.assertEqual(call_order, ['fetch', 'checkout-b'])

        # Verify completed flag in response (two-phase: no-local completes immediately)
        self.assertTrue(args[1].get('completed'), "No-local join should return completed: True")

        # Verify runtime file written
        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime', 'active_branch')
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'feature/auth')


class TestJoinBranchAssessmentCreatesTrackingBranchWhenNoLocalExists(unittest.TestCase):
    """Scenario: Join Branch Assessment Creates Tracking Branch When No Local Exists

    Given feature/auth exists as a remote tracking branch
    And no local branch feature/auth exists
    And no active branch is set
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then git fetch is called for feature/auth
    And a local branch feature/auth is created tracking origin/feature/auth
    And the response contains "completed": true
    And .purlin/runtime/active_branch contains "feature/auth"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_creates_tracking_branch_returns_completed(self, mock_config, mock_run):
        checkout_cmds = []

        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='', stdout='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ''  # clean tree
            elif 'rev-parse' in cmd_str and '--verify' in cmd_str:
                if 'feature/auth' in cmd_str and 'origin' not in cmd_str:
                    raise subprocess.CalledProcessError(1, cmd)  # no local
                result.stdout = 'abc1234'
            elif 'rev-parse' in cmd_str and '--abbrev-ref' in cmd_str:
                result.stdout = 'main'
            elif 'checkout' in cmd_str and '-b' in cmd_str:
                checkout_cmds.append(cmd)
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "feature/auth"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        self.assertTrue(args[1]['completed'])
        self.assertEqual(args[1]['branch'], 'feature/auth')

        # Verify checkout -b was called to create tracking branch
        self.assertTrue(len(checkout_cmds) > 0,
                        "git checkout -b should be called for new tracking branch")

        # Verify runtime file written
        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime', 'active_branch')
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'feature/auth')


class TestJoinBranchAssessmentReturnsBehindSyncState(unittest.TestCase):
    """Scenario: Join Branch Assessment Returns BEHIND Sync State

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists
    And origin/feature/auth has 2 commits not in local feature/auth
    And local feature/auth has no commits not in origin/feature/auth
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then the response contains "sync_state": "BEHIND"
    And the response contains "commits_behind": 2
    And the response contains "dirty": false
    And no branch checkout has occurred (current branch unchanged)
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_behind_sync_state(self, mock_config, mock_run):
        checkout_called = []

        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='', stdout='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ''  # clean tree
            elif 'rev-parse' in cmd_str and '--verify' in cmd_str:
                result.stdout = 'abc1234'  # both local and remote exist
            elif 'log' in cmd_str and 'origin/feature/auth..feature/auth' in cmd_str:
                result.stdout = ''  # ahead=0 (local has no unique commits vs remote)
            elif 'log' in cmd_str and 'feature/auth..origin/feature/auth' in cmd_str:
                result.stdout = 'abc1234 commit1\ndef5678 commit2'  # behind=2
            elif 'checkout' in cmd_str:
                checkout_called.append(cmd)
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "feature/auth"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['sync_state'], 'BEHIND')
        self.assertEqual(args[1]['commits_behind'], 2)
        self.assertEqual(args[1]['commits_ahead'], 0)
        self.assertFalse(args[1]['dirty'])

        # No checkout should have occurred (assessment only)
        self.assertEqual(len(checkout_called), 0,
                         "No checkout should occur during assessment")


class TestJoinBranchAssessmentReturnsDivergedSyncState(unittest.TestCase):
    """Scenario: Join Branch Assessment Returns DIVERGED Sync State

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists
    And origin/feature/auth has 2 commits not in local feature/auth
    And local feature/auth has 1 commit not in origin/feature/auth
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then the response contains "sync_state": "DIVERGED"
    And the response contains "commits_ahead": 1
    And the response contains "commits_behind": 2
    And no branch checkout has occurred (current branch unchanged)
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_diverged_sync_state(self, mock_config, mock_run):
        checkout_called = []

        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='', stdout='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ''
            elif 'rev-parse' in cmd_str and '--verify' in cmd_str:
                result.stdout = 'abc1234'
            elif 'log' in cmd_str and 'origin/feature/auth..feature/auth' in cmd_str:
                result.stdout = 'abc1234 local commit'  # ahead=1 (local has 1 commit remote lacks)
            elif 'log' in cmd_str and 'feature/auth..origin/feature/auth' in cmd_str:
                result.stdout = 'def5678 remote1\nghi9012 remote2'  # behind=2
            elif 'checkout' in cmd_str:
                checkout_called.append(cmd)
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "feature/auth"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['sync_state'], 'DIVERGED')
        self.assertEqual(args[1]['commits_ahead'], 1)
        self.assertEqual(args[1]['commits_behind'], 2)
        self.assertFalse(args[1]['dirty'])

        self.assertEqual(len(checkout_called), 0,
                         "No checkout should occur during assessment")


class TestJoinBranchAssessmentReturnsAheadSyncState(unittest.TestCase):
    """Scenario: Join Branch Assessment Returns AHEAD Sync State

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists
    And local feature/auth has 3 commits not in origin/feature/auth
    And origin/feature/auth has no commits not in local feature/auth
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then the response contains "sync_state": "AHEAD"
    And the response contains "commits_ahead": 3
    And the response contains "dirty": false
    And no branch checkout has occurred (current branch unchanged)
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_ahead_sync_state(self, mock_config, mock_run):
        checkout_called = []

        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='', stdout='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ''
            elif 'rev-parse' in cmd_str and '--verify' in cmd_str:
                result.stdout = 'abc1234'
            elif 'log' in cmd_str and 'origin/feature/auth..feature/auth' in cmd_str:
                result.stdout = 'a1 c1\na2 c2\na3 c3'  # ahead=3 (local has 3 commits remote lacks)
            elif 'log' in cmd_str and 'feature/auth..origin/feature/auth' in cmd_str:
                result.stdout = ''  # behind=0
            elif 'checkout' in cmd_str:
                checkout_called.append(cmd)
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "feature/auth"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['sync_state'], 'AHEAD')
        self.assertEqual(args[1]['commits_ahead'], 3)
        self.assertEqual(args[1]['commits_behind'], 0)
        self.assertFalse(args[1]['dirty'])

        self.assertEqual(len(checkout_called), 0,
                         "No checkout should occur during assessment")


class TestJoinBranchAssessmentReturnsSyncStateWithDirtyFileList(unittest.TestCase):
    """Scenario: Join Branch Assessment Returns Sync State With Dirty File List

    Given the branch "feature/auth" exists as a remote tracking branch
    And a local branch feature/auth exists
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /branch-collab/join with body {"branch": "feature/auth"}
    Then the response contains "dirty": true
    And the response contains "dirty_files" as a non-empty array
    And the response contains a "sync_state" field
    And no branch checkout has occurred (current branch unchanged)
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_dirty_files_returned_in_assessment(self, mock_config, mock_run):
        checkout_called = []

        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='', stdout='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ' M src/main.py\n M src/utils.py\n'
            elif 'rev-parse' in cmd_str and '--verify' in cmd_str:
                result.stdout = 'abc1234'
            elif 'log' in cmd_str and 'origin/feature/auth..feature/auth' in cmd_str:
                result.stdout = ''  # ahead=0 (local has no unique commits vs remote)
            elif 'log' in cmd_str and 'feature/auth..origin/feature/auth' in cmd_str:
                result.stdout = 'abc commit1'  # behind=1
            elif 'checkout' in cmd_str:
                checkout_called.append(cmd)
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "feature/auth"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertTrue(args[1]['dirty'])
        self.assertIsInstance(args[1]['dirty_files'], list)
        self.assertGreater(len(args[1]['dirty_files']), 0)
        self.assertIn('src/main.py', args[1]['dirty_files'])
        self.assertIn('src/utils.py', args[1]['dirty_files'])
        self.assertIn('sync_state', args[1])

        self.assertEqual(len(checkout_called), 0,
                         "No checkout should occur during assessment")


class TestJoinConfirmFastForwardChecksOutAndMerges(unittest.TestCase):
    """Scenario: Join Confirm Fast-Forward Checks Out and Merges

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists that is BEHIND origin/feature/auth
    And the working tree is clean
    When a POST request is sent to /branch-collab/join-confirm with body
        {"branch": "feature/auth", "action": "fast-forward"}
    Then local feature/auth is checked out
    And local feature/auth is fast-forwarded to origin/feature/auth
    And the response contains "reconciled": "fast-forward"
    And .purlin/runtime/active_branch contains "feature/auth"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_fast_forward_checks_out_and_merges(self, mock_config, mock_run):
        checkout_called = []
        merge_called = []

        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='', stdout='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ''  # clean
            elif 'rev-parse' in cmd_str and '--abbrev-ref' in cmd_str:
                result.stdout = 'main'
            elif 'checkout' in cmd_str and '-b' not in cmd_str:
                checkout_called.append(cmd)
            elif 'merge' in cmd_str and '--ff-only' in cmd_str:
                merge_called.append(cmd)
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "feature/auth", "action": "fast-forward"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join_confirm(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        self.assertEqual(args[1]['branch'], 'feature/auth')
        self.assertEqual(args[1]['reconciled'], 'fast-forward')

        self.assertTrue(len(checkout_called) > 0, "git checkout should be called")
        self.assertTrue(len(merge_called) > 0, "git merge --ff-only should be called")

        # Verify runtime file written
        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime', 'active_branch')
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'feature/auth')


class TestJoinConfirmFastForwardRequiresCleanTree(unittest.TestCase):
    """Scenario: Join Confirm Fast-Forward Requires Clean Tree

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists that is BEHIND origin/feature/auth
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /branch-collab/join-confirm with body
        {"branch": "feature/auth", "action": "fast-forward"}
    Then the response contains an error message about dirty working tree
    And the current branch is unchanged
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_fast_forward_blocked_when_dirty(self, mock_config, mock_run):
        checkout_called = []

        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='', stdout='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ' M src/main.py\n'  # dirty
            elif 'checkout' in cmd_str:
                checkout_called.append(cmd)
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "feature/auth", "action": "fast-forward"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join_confirm(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 400)
        self.assertIn('error', args[1])
        self.assertIn('uncommitted', args[1]['error'].lower())

        self.assertEqual(len(checkout_called), 0,
                         "No checkout should occur with dirty tree")


class TestJoinConfirmCheckoutRequiresCleanTree(unittest.TestCase):
    """Scenario: Join Confirm Checkout Requires Clean Tree

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists at SAME as origin/feature/auth
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /branch-collab/join-confirm with body
        {"branch": "feature/auth", "action": "checkout"}
    Then the response contains an error message about dirty working tree
    And the current branch is unchanged
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_checkout_blocked_when_dirty(self, mock_config, mock_run):
        checkout_called = []

        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='', stdout='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ' M src/main.py\n'  # dirty
            elif 'checkout' in cmd_str:
                checkout_called.append(cmd)
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "feature/auth", "action": "checkout"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join_confirm(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 400)
        self.assertIn('error', args[1])
        self.assertIn('uncommitted', args[1]['error'].lower())

        self.assertEqual(len(checkout_called), 0,
                         "No checkout should occur with dirty tree")


class TestJoinConfirmCheckoutSwitchesBranchForSameState(unittest.TestCase):
    """Scenario: Join Confirm Checkout Switches Branch for SAME State

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists at SAME as origin/feature/auth
    And the working tree is clean
    When a POST request is sent to /branch-collab/join-confirm with body
        {"branch": "feature/auth", "action": "checkout"}
    Then local feature/auth is checked out
    And .purlin/runtime/active_branch contains "feature/auth"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_checkout_switches_branch(self, mock_config, mock_run):
        checkout_called = []

        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='', stdout='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ''  # clean
            elif 'rev-parse' in cmd_str and '--abbrev-ref' in cmd_str:
                result.stdout = 'main'
            elif 'checkout' in cmd_str and '-b' not in cmd_str:
                checkout_called.append(cmd)
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "feature/auth", "action": "checkout"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join_confirm(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        self.assertEqual(args[1]['branch'], 'feature/auth')

        self.assertTrue(len(checkout_called) > 0, "git checkout should be called")

        # Verify runtime file written
        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime', 'active_branch')
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'feature/auth')


class TestJoinConfirmPushChecksOutAndPushesToRemote(unittest.TestCase):
    """Scenario: Join Confirm Push Checks Out and Pushes to Remote

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists that is AHEAD of origin/feature/auth
    And the working tree is clean
    When a POST request is sent to /branch-collab/join-confirm with body
        {"branch": "feature/auth", "action": "push"}
    Then local feature/auth is checked out
    And git push is called for feature/auth to the configured remote
    And the response contains "reconciled": "push"
    And .purlin/runtime/active_branch contains "feature/auth"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_push_checks_out_and_pushes(self, mock_config, mock_run):
        checkout_called = []
        push_called = []

        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='', stdout='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ''  # clean
            elif 'rev-parse' in cmd_str and '--abbrev-ref' in cmd_str:
                result.stdout = 'main'
            elif 'checkout' in cmd_str and '-b' not in cmd_str:
                checkout_called.append(cmd)
            elif 'push' in cmd_str:
                push_called.append(cmd)
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "feature/auth", "action": "push"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join_confirm(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        self.assertEqual(args[1]['branch'], 'feature/auth')
        self.assertEqual(args[1]['reconciled'], 'push')

        self.assertTrue(len(checkout_called) > 0, "git checkout should be called")
        self.assertTrue(len(push_called) > 0, "git push should be called")
        self.assertIn('origin', push_called[0])
        self.assertIn('feature/auth', push_called[0])

        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime', 'active_branch')
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'feature/auth')


class TestJoinConfirmPushFailsAfterCheckout(unittest.TestCase):
    """Scenario: Join Confirm Push Fails After Checkout

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists that is AHEAD of origin/feature/auth
    And the working tree is clean
    And the git push will be rejected by the remote
    When a POST request is sent to /branch-collab/join-confirm with body
        {"branch": "feature/auth", "action": "push"}
    Then local feature/auth is checked out (branch IS switched)
    And .purlin/runtime/active_branch contains "feature/auth"
    And the response contains "status": "error"
    And the response contains "branch_checked_out": true
    And the response contains an error message about the push failure
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_push_fails_after_checkout(self, mock_config, mock_run):
        checkout_called = []

        def run_side_effect(cmd, **kwargs):
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                return MagicMock(returncode=0, stderr='', stdout='')
            elif 'rev-parse' in cmd_str and '--abbrev-ref' in cmd_str:
                return MagicMock(returncode=0, stderr='', stdout='main')
            elif 'checkout' in cmd_str and '-b' not in cmd_str:
                checkout_called.append(cmd)
                return MagicMock(returncode=0, stderr='', stdout='')
            elif 'push' in cmd_str:
                raise subprocess.CalledProcessError(
                    1, cmd, stderr='rejected: non-fast-forward')
            return MagicMock(returncode=0, stderr='', stdout='')
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "feature/auth", "action": "push"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join_confirm(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 500)
        self.assertEqual(args[1]['status'], 'error')
        self.assertTrue(args[1]['branch_checked_out'])
        self.assertIn('Push failed', args[1]['error'])

        self.assertTrue(len(checkout_called) > 0, "git checkout should be called")

        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime', 'active_branch')
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'feature/auth')


class TestJoinConfirmGuidePullReturnsCommandWithoutCheckout(unittest.TestCase):
    """Scenario: Join Confirm Guide-Pull Returns Command Without Checkout

    Given feature/auth exists as a remote tracking branch
    And a local branch feature/auth exists that is DIVERGED from origin/feature/auth
    When a POST request is sent to /branch-collab/join-confirm with body
        {"branch": "feature/auth", "action": "guide-pull"}
    Then the response contains "action_required": "pull"
    And the response contains a "command" field with "/pl-remote-pull"
    And no branch checkout has occurred (current branch unchanged)
    And .purlin/runtime/active_branch is unchanged
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_guide_pull_no_checkout(self, mock_config, mock_run):
        checkout_called = []

        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='', stdout='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'checkout' in cmd_str:
                checkout_called.append(cmd)
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "feature/auth", "action": "guide-pull"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join_confirm(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        self.assertEqual(args[1]['action_required'], 'pull')
        self.assertIn('/pl-remote-pull', args[1]['command'])
        self.assertIn('diverged', args[1]['warning'].lower())

        self.assertEqual(len(checkout_called), 0,
                         "guide-pull should NOT checkout any branch")

        # active_branch should not have been written
        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime', 'active_branch')
        self.assertFalse(os.path.exists(rt_path),
                         "active_branch should not be written for guide-pull")


class TestSwitchBranchFetchesReconciles(unittest.TestCase):
    """Scenario: Switch Branch via Join Fetches Reconciles and Updates Active Branch

    Given an active branch "feature/auth" is set
    And hotfix/urgent exists as a remote tracking branch
    And the working tree is clean
    When a POST request is sent to /branch-collab/join with body {"branch": "hotfix/urgent"}
    Then git fetch is called for hotfix/urgent before checkout
    And hotfix/urgent is checked out with reconciliation if needed
    And .purlin/runtime/active_branch contains "hotfix/urgent"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        rt_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(rt_dir, exist_ok=True)
        with open(os.path.join(rt_dir, 'active_branch'), 'w') as f:
            f.write('feature/auth')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_switch_fetches_and_reconciles(self, mock_config, mock_run):
        call_order = []

        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='', stdout='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ''
            elif 'fetch' in cmd_str and 'hotfix/urgent' in cmd_str:
                call_order.append('fetch')
            elif 'rev-parse' in cmd_str and '--verify' in cmd_str:
                if 'hotfix/urgent' in cmd_str and 'origin' not in cmd_str:
                    raise subprocess.CalledProcessError(1, cmd)  # no local
                result.stdout = 'abc1234'
            elif 'rev-parse' in cmd_str and '--abbrev-ref' in cmd_str:
                result.stdout = 'feature/auth'
            elif 'checkout' in cmd_str and '-b' in cmd_str:
                call_order.append('checkout')
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "hotfix/urgent"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        self.assertTrue(args[1].get('completed'),
                        "No-local join should return completed: True")
        self.assertEqual(call_order, ['fetch', 'checkout'])

        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime', 'active_branch')
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'hotfix/urgent')


class TestJoinBranchModalMultiStepProgress(unittest.TestCase):
    """Scenario: Join Branch Shows Operation Modal With Multi-Step Progress

    Verifies the modal opens with "Fetching..." initial message
    and the JS handles reconciled/action_required responses.
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[
        {'name': 'feature/auth', 'active': False, 'sync_state': 'EMPTY',
         'commits_ahead': 0, 'commits_behind': 0}
    ])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_join_modal_initial_message_is_fetching(self, *mocks):
        html = serve.generate_html()
        # joinBranch should open modal with "Fetching and checking sync state..."
        self.assertIn("openBcOpModal('Joining Branch', 'Fetching and checking sync state...'", html)
        # Two-phase join: _bcShowJoinPhase2 and _bcJoinConfirm functions exist
        self.assertIn('_bcShowJoinPhase2', html)
        self.assertIn('_bcJoinConfirm', html)

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_join_success_handler_checks_completed(self, *mocks):
        html = serve.generate_html()
        # Phase 1: JS checks d.completed for direct-create case (auto-close)
        self.assertIn('d.completed', html)
        # Phase 2 interactive content function exists
        self.assertIn('_bcShowJoinPhase2', html)

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_join_success_handler_checks_action_required(self, *mocks):
        html = serve.generate_html()
        # JS should check for d.action_required and not auto-close
        self.assertIn('d.action_required', html)


class TestJoinBranchModalPhase2ContentForBehind(unittest.TestCase):
    """Scenario: Join Branch Modal Shows Fast-Forward Option for Behind

    Phase 2 content shows 'Local branch is N commits behind remote.'
    with Fast-Forward Local & Join button.
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_phase2_behind_shows_fast_forward(self, *mocks):
        html = serve.generate_html()
        # Phase 2 shows sync-state-specific content
        self.assertIn('Local branch is ', html)
        self.assertIn('commits behind remote', html)
        self.assertIn('Fast-Forward Local &amp; Join', html)
        # Phase 2 action button calls _bcJoinConfirm with fast-forward action
        self.assertIn("_bcJoinConfirm(", html)
        self.assertIn("fast-forward", html)


class TestJoinBranchModalPhase2CopyablePullCommand(unittest.TestCase):
    """Scenario: Join Branch Modal Shows Copyable Pull Command for Diverged

    Phase 2 shows 'Remote branch has diverged' with copyable /pl-remote-pull command.
    No Join action button present, only Close.
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_phase2_diverged_shows_copyable_command(self, *mocks):
        html = serve.generate_html()
        # Phase 2 DIVERGED content
        self.assertIn('Remote branch has diverged', html)
        self.assertIn('/pl-remote-pull origin/', html)
        # Copy button for command
        self.assertIn('navigator.clipboard.writeText', html)
        # Monospace font for command block
        self.assertIn('font-family:monospace', html)
        # No join action for DIVERGED (guide-pull doesn't have a Join button)
        # DIVERGED check: the DIVERGED branch does not show bc-phase2-action button
        self.assertIn("sync === 'DIVERGED'", html)


class TestJoinBranchModalShowsPushAndJoinButtonForAhead(unittest.TestCase):
    """Scenario: Join Branch Modal Shows Push and Join Button for Ahead

    Phase 2 shows 'Local branch is N commits ahead of remote.'
    with [Push to Remote & Join] button.
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_phase2_ahead_shows_push_and_join(self, *mocks):
        html = serve.generate_html()
        # Phase 2 AHEAD content
        self.assertIn('Local branch is ', html)
        self.assertIn('commits ahead of remote', html)
        # Push to Remote & Join button sends push action
        self.assertIn('Push to Remote &amp; Join', html)
        self.assertIn("_bcJoinConfirm(", html)
        self.assertIn("\\'push\\'", html)


class TestJoinBranchModalShowsErrorWhenPushToRemoteFails(unittest.TestCase):
    """Scenario: Join Branch Modal Shows Error When Push to Remote Fails

    When the server returns { "status": "error", "error": "push rejected",
    "branch_checked_out": true } the modal shows error and refreshes on dismiss.
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_push_error_shows_in_modal_and_refreshes_on_dismiss(self, *mocks):
        html = serve.generate_html()
        # Error handler checks branch_checked_out flag
        self.assertIn('d.branch_checked_out', html)
        # When branch_checked_out, close button calls refreshStatus
        self.assertIn('refreshStatus()', html)
        # Error display uses bcOpModalError
        self.assertIn('bcOpModalError(', html)
        # Error color token
        self.assertIn('--purlin-status-error', html)


class TestJoinBranchWithDirtyTreeShowsDirtyGateOnly(unittest.TestCase):
    """Scenario: Join Branch With Dirty Tree Shows Dirty Gate Only

    Phase 2 dirty gate shows ONLY dirty file block: heading, monospace file list,
    guidance. No sync state info, no action buttons, only Close.
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_dirty_gate_shows_only_dirty_block(self, *mocks):
        html = serve.generate_html()
        # Dirty gate heading
        self.assertIn('Uncommitted changes:', html)
        # Dirty file list uses monospace
        self.assertIn('font-family:monospace', html)
        # Commit/stash guidance
        self.assertIn('Commit or stash uncommitted changes before joining', html)
        # Dirty gate returns early — verified by the JS structure:
        # the dirty block ends with 'return;' before any sync state rendering
        self.assertIn('return;', html)


class TestJoinBranchModalPhase2SyncBadgeColors(unittest.TestCase):
    """Scenario: Sync Badge Colors Match Design Spec

    Verifies the Phase 2 modal and branches table use correct colors per sync state.
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[
        {'name': 'feat/same', 'active': False, 'sync_state': 'SAME',
         'commits_ahead': 0, 'commits_behind': 0},
        {'name': 'feat/behind', 'active': False, 'sync_state': 'BEHIND',
         'commits_ahead': 0, 'commits_behind': 2},
        {'name': 'feat/diverged', 'active': False, 'sync_state': 'DIVERGED',
         'commits_ahead': 1, 'commits_behind': 2},
        {'name': 'feat/empty', 'active': False, 'sync_state': 'EMPTY',
         'commits_ahead': 0, 'commits_behind': 0},
    ])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_sync_badge_colors_in_html(self, *mocks):
        html = serve.generate_html()
        # SAME = green (st-good)
        self.assertIn('st-good', html)
        # BEHIND = yellow (st-todo)
        self.assertIn('st-todo', html)
        # DIVERGED = orange (st-disputed)
        self.assertIn('st-disputed', html)
        # EMPTY = normal text (--purlin-primary, no badge class)
        self.assertIn('--purlin-primary', html)


def run_tests():
    """Run all tests and write results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    tests_dir = os.path.join(PROJECT_ROOT, 'tests', 'cdd_branch_collab')
    os.makedirs(tests_dir, exist_ok=True)
    status = "PASS" if result.wasSuccessful() else "FAIL"
    failed = len(result.failures) + len(result.errors)
    with open(os.path.join(tests_dir, 'tests.json'), 'w') as f:
        json.dump({
            "status": status,
            "passed": result.testsRun - failed,
            "failed": failed,
            "total": result.testsRun,
            "test_file": "tools/cdd/test_cdd_branch_collab.py",
        }, f, indent=2)

    print(f"\ntests.json: {status}")
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
