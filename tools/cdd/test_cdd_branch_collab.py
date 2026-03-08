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


class TestJoinBranchUpdatesRuntime(unittest.TestCase):
    """Scenario: Join Branch Updates Runtime File

    Given v0.5-sprint exists as a remote tracking branch
    And no active branch is set
    When a POST request is sent to /branch-collab/join with body {"branch": "v0.5-sprint"}
    Then .purlin/runtime/active_branch contains "v0.5-sprint"
    And GET /status.json shows branch_collab.active_branch as "v0.5-sprint"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_join_writes_runtime(self, mock_config, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ''  # clean working tree
            elif 'rev-parse' in cmd_str:
                result.stdout = 'abc1234'
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
            serve.Handler._handle_branch_collab_join(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        self.assertEqual(args[1]['branch'], 'v0.5-sprint')

        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime',
                               'active_branch')
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'v0.5-sprint')


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


class TestSwitchBranchUpdatesActiveBranch(unittest.TestCase):
    """Scenario: Switch Branch Updates Active Branch

    Given an active branch "v0.5-sprint" is set
    And hotfix-auth exists as a remote tracking branch
    When a POST request is sent to /branch-collab/join with body {"branch": "hotfix-auth"}
    Then .purlin/runtime/active_branch contains "hotfix-auth"
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
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_switch_updates_to_new_branch(self, mock_config, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='abc', stderr='')

        body = json.dumps({"branch": "hotfix-auth"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join(handler)

        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime',
                               'active_branch')
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'hotfix-auth')


class TestSyncStateNoLocal(unittest.TestCase):
    """When local branch does not exist, sync state returns NO_LOCAL.

    Given an active branch "v0.5-sprint" is set
    And the remote tracking ref origin/v0.5-sprint exists
    But local branch "v0.5-sprint" does not exist
    When compute_remote_sync_state is called
    Then sync_state is "NO_LOCAL"
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_no_local_state(self, mock_config, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                ref = cmd[-1] if cmd else ''
                if ref == 'v0.5-sprint':
                    raise subprocess.CalledProcessError(128, cmd)
                result.stdout = 'abc1234'
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        state = serve.compute_remote_sync_state("v0.5-sprint")
        self.assertEqual(state['sync_state'], 'NO_LOCAL')
        self.assertEqual(state['commits_ahead'], 0)
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
            else:
                result.stdout = ''  # No commits in either direction
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
                if range_arg.startswith('origin/'):
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


class TestSwitchBranchBlockedWhenDirty(unittest.TestCase):
    """Scenario: Switch Branch Blocked When Working Tree Is Dirty

    Given an active branch "v0.5-sprint" is set
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /branch-collab/join with body {"branch": "hotfix-auth"}
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
    @patch('serve.get_branch_collab_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_switch_blocked_dirty_tree(self, mock_config, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'status' in cmd_str and '--porcelain' in cmd_str:
                result.stdout = ' M src/main.py\n'
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        body = json.dumps({"branch": "hotfix-auth"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_branch_collab_join(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 400)
        self.assertIn('error', args[1])
        self.assertIn('uncommitted', args[1]['error'].lower())

        # Verify runtime file still has original branch
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
        # The command should be ['git', 'fetch', 'origin'] (no branch arg)
        self.assertEqual(args, ['git', 'fetch', 'origin'])

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
        # Expanded heading is always plain
        self.assertIn('data-expanded="BRANCH COLLABORATION"', html)
        self.assertNotIn('data-expanded="BRANCH COLLABORATION (', html)


class TestCollapsedBadgeShowsPlainTitleWhenNoBranchActive(unittest.TestCase):
    """Scenario: Collapsed Badge Shows Plain Title When No Branch Active

    Given the CDD server is running
    And no file exists at .purlin/runtime/active_branch
    When the dashboard HTML is generated
    Then the BRANCH COLLABORATION collapsed badge text is "BRANCH COLLABORATION"
    """

    @patch('serve._get_shortened_remote_url', return_value='github.com/rlabarca/purlin')
    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_branch', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_branch_collab_branches', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_collapsed_badge_plain_when_no_active_branch(self, *mocks):
        html = serve.generate_html()
        self.assertIn('data-collapsed-text="BRANCH COLLABORATION"', html)
        self.assertNotIn('data-collapsed-text="BRANCH COLLABORATION (', html)
        self.assertIn('data-expanded="BRANCH COLLABORATION"', html)


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
        self.assertIn('data-expanded="BRANCH COLLABORATION"', html)


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
