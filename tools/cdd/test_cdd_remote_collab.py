"""Automated tests for CDD Remote Collaboration feature.

Tests all automated scenarios from features/cdd_remote_collab.md.
Results written to tests/cdd_remote_collab/tests.json.
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


class TestRemoteSectionAlwaysRendered(unittest.TestCase):
    """Scenario: REMOTE Section Always Rendered in Dashboard HTML

    Given the CDD server is running
    And no remote_collab config exists in .purlin/config.json
    When the dashboard HTML is generated
    Then the REMOTE COLLABORATION section is present in the HTML output
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_remote_session', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_remote_collab_sessions', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_remote_section_present_in_html(self, *mocks):
        html = serve.generate_html()
        self.assertIn('REMOTE COLLABORATION', html)
        self.assertIn('remote-collab-section', html)


class TestRemoteCollabAbsentFromStatusJsonWhenNoSession(unittest.TestCase):
    """Scenario: remote_collab Absent From status.json When No Active Session

    Given no file exists at .purlin/runtime/active_remote_session
    When an agent calls GET /status.json
    Then the response does not contain a remote_collab field
    """

    @patch('serve.get_active_remote_session', return_value=None)
    @patch('serve.get_remote_collab_sessions', return_value=[])
    def test_no_remote_collab_in_api(self, *mocks):
        data = serve.generate_api_status_json()
        self.assertNotIn('remote_collab', data)

    @patch('serve.get_active_remote_session', return_value=None)
    @patch('serve.get_remote_collab_sessions', return_value=[])
    def test_remote_collab_sessions_always_present(self, *mocks):
        data = serve.generate_api_status_json()
        self.assertIn('remote_collab_sessions', data)


class TestRemoteCollabSessionsPresentEvenWhenEmpty(unittest.TestCase):
    """Scenario: remote_collab_sessions Present In status.json Even When Empty

    Given no collab/* branches exist on the remote
    When an agent calls GET /status.json
    Then the response contains remote_collab_sessions as an empty array
    """

    @patch('serve.get_active_remote_session', return_value=None)
    @patch('serve.get_remote_collab_sessions', return_value=[])
    def test_sessions_is_empty_array(self, *mocks):
        data = serve.generate_api_status_json()
        self.assertEqual(data['remote_collab_sessions'], [])


class TestCreateSessionPushesBranchAndWritesRuntime(unittest.TestCase):
    """Scenario: Create Session Pushes Branch and Writes Runtime File

    Given no collab/v0.5-sprint branch exists on the remote
    And the CDD server is running
    When a POST request is sent to /remote-collab/create with body {"name": "v0.5-sprint"}
    Then the server creates branch collab/v0.5-sprint from main HEAD
    And pushes collab/v0.5-sprint to origin
    And writes "v0.5-sprint" to .purlin/runtime/active_remote_session
    And the response contains { "status": "ok", "session": "v0.5-sprint" }
    And GET /status.json shows remote_collab.sync_state as "SAME"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runtime_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(self.runtime_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_create_session_endpoint(self, mock_config, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

        body = json.dumps({"name": "v0.5-sprint"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_create(handler)

        # Verify _send_json called with 200 and correct body
        handler._send_json.assert_called_once()
        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        self.assertEqual(args[1]['session'], 'v0.5-sprint')
        self.assertEqual(args[1]['branch'], 'collab/v0.5-sprint')

        # Verify git branch and push were called
        calls = mock_run.call_args_list
        branch_calls = [c for c in calls if 'branch' in str(c) and 'collab' in str(c)]
        push_calls = [c for c in calls if 'push' in str(c)]
        self.assertTrue(len(branch_calls) > 0, "git branch should have been called")
        self.assertTrue(len(push_calls) > 0, "git push should have been called")

        # Verify runtime file written
        rt_path = os.path.join(self.runtime_dir, 'active_remote_session')
        self.assertTrue(os.path.exists(rt_path))
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'v0.5-sprint')


class TestCreateSessionWithInvalidNameReturnsError(unittest.TestCase):
    """Scenario: Create Session With Invalid Name Returns Error

    Given the CDD server is running
    When a POST request is sent to /remote-collab/create with body {"name": "bad..name"}
    Then the response contains an error message
    And no branch is created on the remote
    And .purlin/runtime/active_remote_session is not written
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _post_create(self, name):
        body = json.dumps({"name": name}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()
        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_create(handler)
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


class TestJoinExistingSessionUpdatesRuntime(unittest.TestCase):
    """Scenario: Join Existing Session Updates Runtime File

    Given collab/v0.5-sprint exists as a remote tracking branch
    And no active session is set
    When a POST request is sent to /remote-collab/switch with body {"name": "v0.5-sprint"}
    Then .purlin/runtime/active_remote_session contains "v0.5-sprint"
    And GET /status.json shows remote_collab.active_session as "v0.5-sprint"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_switch_writes_runtime(self, mock_config, mock_run):
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

        body = json.dumps({"name": "v0.5-sprint"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_switch(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        self.assertEqual(args[1]['session'], 'v0.5-sprint')

        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime',
                               'active_remote_session')
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'v0.5-sprint')


class TestDisconnectClearsActiveSession(unittest.TestCase):
    """Scenario: Disconnect Checks Out Main and Clears Active Session

    Given an active session "v0.5-sprint" is set
    And the working tree is clean
    When a POST request is sent to /remote-collab/disconnect
    Then the local branch main is checked out
    And .purlin/runtime/active_remote_session is empty or absent
    And GET /status.json does not contain a remote_collab field
    And collab/v0.5-sprint still exists on the remote
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        rt_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(rt_dir, exist_ok=True)
        with open(os.path.join(rt_dir, 'active_remote_session'), 'w') as f:
            f.write('v0.5-sprint')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    def test_disconnect_clears_runtime(self, mock_run):
        # git status --porcelain returns empty (clean tree)
        # git checkout main succeeds
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

        handler = MagicMock()
        handler.headers = {'Content-Length': '2'}
        handler.rfile = io.BytesIO(b'{}')
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_disconnect(handler)

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
                               'active_remote_session')
        with open(rt_path) as f:
            content = f.read().strip()
        self.assertEqual(content, '')


class TestSwitchSessionUpdatesActiveSession(unittest.TestCase):
    """Scenario: Switch Session Updates Active Session

    Given an active session "v0.5-sprint" is set
    And collab/hotfix-auth exists as a remote tracking branch
    When a POST request is sent to /remote-collab/switch with body {"name": "hotfix-auth"}
    Then .purlin/runtime/active_remote_session contains "hotfix-auth"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        rt_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(rt_dir, exist_ok=True)
        with open(os.path.join(rt_dir, 'active_remote_session'), 'w') as f:
            f.write('v0.5-sprint')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_switch_updates_to_new_session(self, mock_config, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='abc', stderr='')

        body = json.dumps({"name": "hotfix-auth"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_switch(handler)

        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime',
                               'active_remote_session')
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'hotfix-auth')


class TestSyncStateNoLocal(unittest.TestCase):
    """When local collab branch does not exist, sync state returns NO_LOCAL.

    Given an active session "v0.5-sprint" is set
    And the remote tracking ref origin/collab/v0.5-sprint exists
    But local branch "collab/v0.5-sprint" does not exist
    When compute_remote_sync_state is called
    Then sync_state is "NO_LOCAL"
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_no_local_state(self, mock_config, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                ref = cmd[-1] if cmd else ''
                if ref == 'collab/v0.5-sprint':
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

    Given an active session "v0.5-sprint" is set
    And local main and origin/collab/v0.5-sprint point to the same commit
    When an agent calls GET /status.json
    Then remote_collab.sync_state is "SAME"
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
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

    Given an active session "v0.5-sprint" is set
    And local collab/v0.5-sprint has 3 commits not in origin/collab/v0.5-sprint
    When an agent calls GET /status.json
    Then remote_collab.sync_state is "AHEAD"
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_ahead_state(self, mock_config, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                result.stdout = 'abc1234'
            elif isinstance(cmd, list) and 'log' in cmd:
                # Find the range arg (contains '..')
                range_arg = next((a for a in cmd if '..' in a), '')
                if range_arg.startswith('origin/'):
                    # ahead: origin/collab/..collab/ -> local has 3 extra
                    result.stdout = 'abc commit1\ndef commit2\nghi commit3\n'
                else:
                    # behind: collab/..origin/collab/ -> remote has 0 extra
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

    Given an active session "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has 2 commits not in local collab/v0.5-sprint
    When an agent calls GET /status.json
    Then remote_collab.sync_state is "BEHIND"
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
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

    Given an active session "v0.5-sprint" is set
    And local collab/v0.5-sprint has 1 commit not in origin/collab/v0.5-sprint
    And origin/collab/v0.5-sprint has 2 commits not in local collab/v0.5-sprint
    When an agent calls GET /status.json
    Then remote_collab.sync_state is "DIVERGED"
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
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

    Given an active session "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has commits from two different authors
    When an agent calls GET /status.json
    Then remote_collab.contributors has entries sorted by most-recent-first
    And each entry has email, name, commits, last_active, and last_subject fields
    And the contributors list has at most 10 entries
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
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
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_max_10_entries(self, mock_config, mock_run):
        lines = [f"user{i}@ex.com|User{i}|{i}h ago|commit {i}" for i in range(15)]
        mock_run.return_value = MagicMock(returncode=0, stdout='\n'.join(lines), stderr='')
        contributors = serve.get_remote_contributors("v0.5-sprint")
        self.assertLessEqual(len(contributors), 10)

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
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

    Given an active session "v0.5-sprint" is set
    And remote_collab.last_fetch is null (server just started)
    When a POST request is sent to /remote-collab/fetch
    Then the response contains fetched_at with an ISO timestamp
    And subsequent GET /status.json shows remote_collab.last_fetch as non-null
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)
        with open(os.path.join(self.tmpdir, '.purlin', 'runtime',
                               'active_remote_session'), 'w') as f:
            f.write('v0.5-sprint')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_fetch_sets_timestamp(self, mock_config, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

        # Reset last_fetch
        serve._remote_collab_last_fetch = None

        handler = MagicMock()
        handler.headers = {'Content-Length': '2'}
        handler.rfile = io.BytesIO(b'{}')
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_fetch(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        self.assertIn('fetched_at', args[1])
        self.assertIsNotNone(args[1]['fetched_at'])
        # Verify the module-level variable was updated
        self.assertIsNotNone(serve._remote_collab_last_fetch)


class TestFiveSecondPollTriggersZeroFetchCalls(unittest.TestCase):
    """Scenario: 5-Second Status Poll Triggers Zero Git Fetch Calls

    Given an active session "v0.5-sprint" is set
    And auto_fetch_interval is 0 in the test config
    When the dashboard polls GET /status.json 3 times at 5-second intervals
    Then no git fetch commands are executed during those polls
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_remote_session', return_value='v0.5-sprint')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 0})
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
            # Verify remote_collab is present (session is active)
            self.assertIn('remote_collab', data)

        # Verify no 'fetch' calls were made
        for call in mock_run.call_args_list:
            cmd = call[0][0] if call[0] else call[1].get('cmd', [])
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
            self.assertNotIn('fetch', cmd_str,
                             "git fetch should not be called during status poll")


class TestDeleteSessionRemovesRemoteBranch(unittest.TestCase):
    """Scenario: Delete Session Removes Remote Branch and Returns Success

    Given collab/v0.5-sprint exists as a remote tracking branch
    And the CDD server is running
    When a POST request is sent to /remote-collab/delete with body {"name": "v0.5-sprint"}
    Then the server deletes collab/v0.5-sprint from the remote
    And the local tracking branch collab/v0.5-sprint is removed if it existed
    And the response contains { "status": "ok", "session": "v0.5-sprint" }
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    @patch('serve.get_active_remote_session', return_value=None)
    def test_delete_session_success(self, mock_active, mock_config, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

        body = json.dumps({"name": "v0.5-sprint"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_delete(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        self.assertEqual(args[1]['session'], 'v0.5-sprint')
        self.assertEqual(args[1]['deleted_branch'], 'collab/v0.5-sprint')

        # Verify git push --delete was called
        calls = mock_run.call_args_list
        delete_calls = [c for c in calls if '--delete' in str(c)]
        self.assertTrue(len(delete_calls) > 0,
                        "git push --delete should have been called")


class TestDeleteActiveSessionClearsRuntime(unittest.TestCase):
    """Scenario: Delete Active Session Also Clears Runtime File

    Given an active session "v0.5-sprint" is set
    And collab/v0.5-sprint exists as a remote tracking branch
    When a POST request is sent to /remote-collab/delete with body {"name": "v0.5-sprint"}
    Then the server deletes collab/v0.5-sprint from the remote
    And .purlin/runtime/active_remote_session is empty or absent
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        rt_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(rt_dir, exist_ok=True)
        with open(os.path.join(rt_dir, 'active_remote_session'), 'w') as f:
            f.write('v0.5-sprint')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_delete_active_clears_runtime(self, mock_config, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

        body = json.dumps({"name": "v0.5-sprint"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_delete(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')

        # Verify runtime file was cleared
        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime',
                               'active_remote_session')
        with open(rt_path) as f:
            content = f.read().strip()
        self.assertEqual(content, '')


class TestDeleteNonexistentSessionReturnsError(unittest.TestCase):
    """Scenario: Delete Nonexistent Session Returns Error

    Given no collab/nonexistent branch exists on the remote
    When a POST request is sent to /remote-collab/delete with body {"name": "nonexistent"}
    Then the response contains an error message
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_delete_nonexistent_returns_error(self, mock_config, mock_run):
        # git push --delete fails for nonexistent branch
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ['git', 'push'], stderr='error: unable to delete')

        body = json.dumps({"name": "nonexistent"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_delete(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 500)
        self.assertIn('error', args[1])


class TestPerSessionSyncStateInRemoteCollabSessions(unittest.TestCase):
    """Scenario: Per-Session Sync State in remote_collab_sessions

    Given collab/v0.5-sprint exists as a remote tracking branch
    And origin/collab/v0.5-sprint has 2 commits not in local collab/v0.5-sprint
    When an agent calls GET /status.json
    Then remote_collab_sessions contains an entry for "v0.5-sprint"
    And that entry has sync_state "BEHIND" and commits_behind 2
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    @patch('serve.get_active_remote_session', return_value=None)
    def test_per_session_sync_state(self, mock_active, mock_config, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            if 'branch' in cmd_str and '-r' in cmd_str:
                result.stdout = '  origin/collab/v0.5-sprint\n'
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

        sessions = serve.get_remote_collab_sessions()
        self.assertEqual(len(sessions), 1)
        s = sessions[0]
        self.assertEqual(s['name'], 'v0.5-sprint')
        self.assertEqual(s['sync_state'], 'BEHIND')
        self.assertEqual(s['commits_behind'], 2)
        self.assertEqual(s['commits_ahead'], 0)


class TestCreateSessionBlockedWhenDirty(unittest.TestCase):
    """Scenario: Create Session Blocked When Working Tree Is Dirty

    Given the CDD server is running
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /remote-collab/create with body {"name": "v0.5-sprint"}
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
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
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

        body = json.dumps({"name": "v0.5-sprint"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_create(handler)

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
                               'active_remote_session')
        self.assertFalse(os.path.exists(rt_path))


class TestDisconnectBlockedWhenDirty(unittest.TestCase):
    """Scenario: Disconnect Blocked When Working Tree Is Dirty

    Given an active session "v0.5-sprint" is set
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /remote-collab/disconnect
    Then the response contains an error message about dirty working tree
    And the current branch remains collab/v0.5-sprint
    And .purlin/runtime/active_remote_session still contains "v0.5-sprint"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        rt_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(rt_dir, exist_ok=True)
        with open(os.path.join(rt_dir, 'active_remote_session'), 'w') as f:
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
            serve.Handler._handle_remote_collab_disconnect(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 400)
        self.assertIn('error', args[1])
        self.assertIn('uncommitted', args[1]['error'].lower())

        # Verify no checkout was attempted
        for call in mock_run.call_args_list:
            cmd = call[0][0] if call[0] else []
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else str(cmd)
            self.assertNotIn('checkout', cmd_str)

        # Verify runtime file still has session
        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime',
                               'active_remote_session')
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'v0.5-sprint')


class TestSwitchSessionBlockedWhenDirty(unittest.TestCase):
    """Scenario: Switch Session Blocked When Working Tree Is Dirty

    Given an active session "v0.5-sprint" is set
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /remote-collab/switch with body {"name": "hotfix-auth"}
    Then the response contains an error message about dirty working tree
    And the current branch remains collab/v0.5-sprint
    And .purlin/runtime/active_remote_session still contains "v0.5-sprint"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        rt_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(rt_dir, exist_ok=True)
        with open(os.path.join(rt_dir, 'active_remote_session'), 'w') as f:
            f.write('v0.5-sprint')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
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

        body = json.dumps({"name": "hotfix-auth"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_switch(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 400)
        self.assertIn('error', args[1])
        self.assertIn('uncommitted', args[1]['error'].lower())

        # Verify runtime file still has original session
        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime',
                               'active_remote_session')
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'v0.5-sprint')


class TestDeleteSessionRemovesCachedDigestAndAnalysisFiles(unittest.TestCase):
    """Scenario: Delete Session Removes Cached Digest and Analysis Files

    Given an active session "v0.5-sprint" is set in .purlin/runtime/active_remote_session
    And collab/v0.5-sprint exists as a remote tracking branch
    And features/digests/whats-different.md exists on disk
    And features/digests/whats-different-analysis.md exists on disk
    When a POST request is sent to /remote-collab/delete with body {"name": "v0.5-sprint"}
    Then the response contains { "status": "ok" }
    And features/digests/whats-different.md does not exist on disk
    And features/digests/whats-different-analysis.md does not exist on disk
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        rt_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(rt_dir, exist_ok=True)
        with open(os.path.join(rt_dir, 'active_remote_session'), 'w') as f:
            f.write('v0.5-sprint')
        # Create digest files
        digest_dir = os.path.join(self.tmpdir, 'features', 'digests')
        os.makedirs(digest_dir, exist_ok=True)
        with open(os.path.join(digest_dir, 'whats-different.md'), 'w') as f:
            f.write('# Digest content')
        with open(os.path.join(digest_dir, 'whats-different-analysis.md'), 'w') as f:
            f.write('# Analysis content')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_delete_removes_digest_files(self, mock_config, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

        body = json.dumps({"name": "v0.5-sprint"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_delete(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')

        digest_dir = os.path.join(self.tmpdir, 'features', 'digests')
        self.assertFalse(
            os.path.exists(os.path.join(digest_dir, 'whats-different.md')),
            "whats-different.md should have been deleted")
        self.assertFalse(
            os.path.exists(os.path.join(digest_dir, 'whats-different-analysis.md')),
            "whats-different-analysis.md should have been deleted")


class TestRemoteCollabSectionAlwaysVisibleInDashboardHTML(unittest.TestCase):
    """Scenario: REMOTE COLLABORATION Section Always Visible in Dashboard HTML

    Given the CDD server is running
    And no remote_collab config exists in .purlin/config.json
    When the dashboard HTML is generated
    Then the REMOTE COLLABORATION section heading is present in the HTML output
    And the section is rendered above the ISOLATED TEAMS section in the DOM
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_remote_session', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_remote_collab_sessions', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_section_heading_present_and_above_isolated(self, *mocks):
        html = serve.generate_html()
        self.assertIn('REMOTE COLLABORATION', html)
        # Verify the section heading element exists
        self.assertIn('id="rc-heading"', html)
        # Verify it appears above ISOLATED TEAMS in DOM
        rc_pos = html.find('remote-collab-section')
        iso_pos = html.find('isolation-section')
        self.assertGreater(rc_pos, -1, "remote-collab-section not found")
        self.assertGreater(iso_pos, -1, "isolation-section not found")
        self.assertLess(rc_pos, iso_pos,
                        "REMOTE COLLABORATION should appear before ISOLATED TEAMS")


class TestNoActiveSessionShowsCreationRowAndKnownSessionsTable(unittest.TestCase):
    """Scenario: No-Active-Session Shows Creation Row and Known Sessions Table

    Given no file exists at .purlin/runtime/active_remote_session
    When the dashboard HTML is generated
    Then the REMOTE COLLABORATION section contains a creation row with
         "Start Remote Session" label
    And the creation row contains a text input and a Create button
    And a known sessions table element is present below the creation row
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_remote_session', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_remote_collab_sessions', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_creation_row_and_sessions_table(self, *mocks):
        html = serve.generate_html()
        self.assertIn('Start Remote Session', html)
        self.assertIn('id="new-session-name"', html)
        self.assertIn('id="btn-create-session"', html)


class TestRemoteCollabRendersAboveIsolatedTeamsInDOMOrder(unittest.TestCase):
    """Scenario: REMOTE COLLABORATION Renders Above ISOLATED TEAMS in DOM Order

    Given the CDD server is running
    And both REMOTE COLLABORATION and ISOLATED TEAMS sections exist in the HTML
    When the dashboard HTML is generated
    Then the REMOTE COLLABORATION section appears before the ISOLATED TEAMS
         section in the HTML output
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_remote_session', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_remote_collab_sessions', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_dom_order(self, *mocks):
        html = serve.generate_html()
        rc_pos = html.find('remote-collab-section')
        iso_pos = html.find('isolation-section')
        self.assertGreater(rc_pos, -1)
        self.assertGreater(iso_pos, -1)
        self.assertLess(rc_pos, iso_pos)


class TestLastRemoteSyncAnnotationPresentInMainWorkspaceBody(unittest.TestCase):
    """Scenario: Last Remote Sync Annotation Present in MAIN WORKSPACE Body

    Given an active session "v0.5-sprint" is set in .purlin/runtime/active_remote_session
    When the dashboard HTML is generated
    Then the MAIN WORKSPACE section body contains a "Last remote sync" annotation
    And the annotation appears below the clean/dirty state line
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_remote_session', return_value='v0.5-sprint')
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_remote_collab_sessions', return_value=[])
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


class TestDeleteButtonPresentInKnownSessionsTableRows(unittest.TestCase):
    """Scenario: Delete Button Present in Known Sessions Table Rows

    Given no file exists at .purlin/runtime/active_remote_session
    And at least one collab session exists on the remote
    When the dashboard HTML is generated
    Then each session row in the known sessions table contains a Delete button
    And the Delete button appears before the Join button in each row
    """

    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_remote_session', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_remote_collab_sessions', return_value=[
        {'name': 'v0.5-sprint', 'branch': 'collab/v0.5-sprint',
         'active': False, 'sync_state': 'SAME',
         'commits_ahead': 0, 'commits_behind': 0}
    ])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_delete_button_before_join(self, *mocks):
        html = serve.generate_html()
        # Find the session row with Delete and Join
        self.assertIn('showDeleteSessionModal', html)
        # Verify Delete appears before Join in the row
        delete_pos = html.find('showDeleteSessionModal')
        join_pos = html.find('joinRemoteSession')
        self.assertGreater(delete_pos, -1, "Delete button not found")
        self.assertGreater(join_pos, -1, "Join button not found")
        self.assertLess(delete_pos, join_pos,
                        "Delete button should appear before Join button")


class TestJoinExistingChecksOutBranchAndWritesRuntimeFile(unittest.TestCase):
    """Scenario: Join-Existing Endpoint Checks Out Branch and Writes Runtime File

    Given the branch "testing" exists as a remote tracking branch
    And no active session is set
    And the working tree is clean
    When a POST request is sent to /remote-collab/join-existing with body {"branch": "testing"}
    Then the local branch "testing" is checked out
    And .purlin/runtime/active_remote_session contains "testing"
    And the response contains { "status": "ok", "session": "testing", "branch": "testing" }
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runtime_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(self.runtime_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve._is_working_tree_dirty', return_value=False)
    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_join_existing_success(self, mock_config, mock_run, mock_dirty):
        mock_run.return_value = MagicMock(returncode=0, stdout='main\n', stderr='')

        body = json.dumps({"branch": "testing"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_join_existing(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')
        self.assertEqual(args[1]['session'], 'testing')
        self.assertEqual(args[1]['branch'], 'testing')

        # Verify runtime file written
        rt_path = os.path.join(self.runtime_dir, 'active_remote_session')
        self.assertTrue(os.path.exists(rt_path))
        with open(rt_path) as f:
            self.assertEqual(f.read().strip(), 'testing')

        # Verify active_remote_branch written
        branch_path = os.path.join(self.runtime_dir, 'active_remote_branch')
        self.assertTrue(os.path.exists(branch_path))
        with open(branch_path) as f:
            self.assertEqual(f.read().strip(), 'testing')


class TestJoinExistingWithDirtyWorkingTreeReturnsError(unittest.TestCase):
    """Scenario: Join-Existing With Dirty Working Tree Returns Error

    Given the branch "testing" exists as a remote tracking branch
    And the working tree has uncommitted changes outside .purlin/
    When a POST request is sent to /remote-collab/join-existing with body {"branch": "testing"}
    Then the response contains an error message about dirty working tree
    And the current branch is unchanged
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve._is_working_tree_dirty', return_value=True)
    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_dirty_tree_returns_error(self, mock_config, mock_run, mock_dirty):
        # rev-parse --verify succeeds (branch exists on remote)
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

        body = json.dumps({"branch": "testing"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_join_existing(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 400)
        self.assertIn('error', args[1])
        self.assertIn('uncommitted', args[1]['error'].lower())

        # Verify no runtime file written
        rt_path = os.path.join(self.tmpdir, '.purlin', 'runtime', 'active_remote_session')
        if os.path.exists(rt_path):
            with open(rt_path) as f:
                self.assertEqual(f.read().strip(), '')


class TestJoinExistingWithNonexistentRemoteBranchReturnsError(unittest.TestCase):
    """Scenario: Join-Existing With Nonexistent Remote Branch Returns Error

    Given no branch "nonexistent" exists as a remote tracking branch
    When a POST request is sent to /remote-collab/join-existing with body {"branch": "nonexistent"}
    Then the response contains an error message
    And no branch checkout occurs
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, '.purlin', 'runtime'), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_nonexistent_branch_returns_error(self, mock_config, mock_run):
        # rev-parse --verify fails (branch not found on remote)
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git')

        body = json.dumps({"branch": "nonexistent"}).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_join_existing(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 400)
        self.assertIn('error', args[1])
        self.assertIn('not found', args[1]['error'].lower())


class TestStatusJsonReflectsJoinedBranchForNonCollabBranch(unittest.TestCase):
    """Scenario: status.json Reflects Joined Branch for Non-Collab Branch

    Given the branch "testing" has been joined via /remote-collab/join-existing
    When an agent calls GET /status.json
    Then remote_collab.branch is "testing"
    And remote_collab.active_session is "testing"
    """

    @patch('serve._read_active_remote_branch', return_value='testing')
    @patch('serve.get_active_remote_session', return_value='testing')
    @patch('serve.get_remote_collab_sessions', return_value=[])
    @patch('serve.compute_remote_sync_state', return_value={
        'sync_state': 'SAME', 'commits_ahead': 0, 'commits_behind': 0})
    @patch('serve.get_remote_contributors', return_value=[])
    def test_status_json_branch_and_session(self, *mocks):
        data = serve.generate_api_status_json()
        self.assertIn('remote_collab', data)
        self.assertEqual(data['remote_collab']['branch'], 'testing')
        self.assertEqual(data['remote_collab']['active_session'], 'testing')


class TestExistingBranchDropdownPopulatedInHtml(unittest.TestCase):
    """Scenario: Existing Branch Dropdown Populated in HTML

    Given no file exists at .purlin/runtime/active_remote_session
    And remote tracking branches "origin/testing" and "origin/feature/auth" exist
    And no collab/* branches match those names
    When the dashboard HTML is generated
    Then the REMOTE COLLABORATION section contains a select element with
         "testing" and "feature/auth" options
    """

    @patch('serve.get_eligible_remote_branches', return_value=['feature/auth', 'testing'])
    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_remote_session', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_remote_collab_sessions', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_dropdown_populated(self, *mocks):
        html = serve.generate_html()
        self.assertIn('id="existing-branch-select"', html)
        self.assertIn('Join Existing Branch', html)
        self.assertIn('<option value="testing">testing</option>', html)
        self.assertIn('<option value="feature/auth">feature/auth</option>', html)
        self.assertIn('id="btn-join-existing"', html)


class TestCollabBranchesExcludedFromExistingBranchDropdown(unittest.TestCase):
    """Scenario: Collab Branches Excluded From Existing Branch Dropdown

    Given no file exists at .purlin/runtime/active_remote_session
    And remote tracking branches "origin/collab/sprint1" and "origin/testing" exist
    And "collab/sprint1" is listed in the known sessions table
    When the dashboard HTML is generated
    Then the existing branch dropdown contains "testing"
    And the existing branch dropdown does not contain "collab/sprint1"
    """

    @patch('serve.get_eligible_remote_branches', return_value=['testing'])
    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_remote_session', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_remote_collab_sessions', return_value=[
        {'name': 'sprint1', 'branch': 'collab/sprint1',
         'active': False, 'sync_state': 'SAME',
         'commits_ahead': 0, 'commits_behind': 0}
    ])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_collab_excluded_non_collab_included(self, *mocks):
        html = serve.generate_html()
        self.assertIn('<option value="testing">testing</option>', html)
        self.assertNotIn('collab/sprint1', html.split('existing-branch-select')[1].split('</select>')[0]
                         if 'existing-branch-select' in html else '')


class TestRefreshSessionsButtonFetchesAllRemoteRefs(unittest.TestCase):
    """Scenario: Refresh Sessions Button Fetches All Remote Refs

    Given the CDD server is running with no active session
    And the known sessions table shows 1 collab session
    When a new collab branch is pushed to the remote from another machine
    And a POST request is sent to /remote-collab/fetch-all
    Then the response contains { "status": "ok" } with a fetched_at timestamp
    And the known sessions table re-renders with the newly discovered collab branch
    """

    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    @patch('subprocess.run')
    def test_fetch_all_succeeds(self, mock_run, *mocks):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        handler = MagicMock()
        handler.headers = {'Content-Length': '2'}
        handler.rfile = io.BytesIO(b'{}')
        handler.path = '/remote-collab/fetch-all'
        responses = []

        def mock_send_json(status, data):
            responses.append((status, data))
        handler._send_json = mock_send_json
        serve.Handler._handle_remote_collab_fetch_all(handler)
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

    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    @patch('subprocess.run')
    def test_fetch_all_returns_error_on_failure(self, mock_run, *mocks):
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git', stderr='fetch failed')
        handler = MagicMock()
        responses = []

        def mock_send_json(status, data):
            responses.append((status, data))
        handler._send_json = mock_send_json
        serve.Handler._handle_remote_collab_fetch_all(handler)
        self.assertEqual(len(responses), 1)
        status, data = responses[0]
        self.assertEqual(status, 500)
        self.assertIn('error', data)


class TestSectionHeadingShowsShortenedRemoteUrl(unittest.TestCase):
    """Scenario: Section Heading Shows Shortened Remote URL

    Given the CDD server is running
    And the git remote "origin" is configured with URL "https://github.com/rlabarca/purlin.git"
    When the dashboard HTML is generated
    Then the REMOTE COLLABORATION section heading expanded text includes "(github.com/rlabarca/purlin)"
    """

    @patch('serve._get_shortened_remote_url', return_value='github.com/rlabarca/purlin')
    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_remote_session', return_value=None)
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_remote_collab_sessions', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_heading_includes_shortened_url(self, *mocks):
        html = serve.generate_html()
        self.assertIn('REMOTE COLLABORATION (github.com/rlabarca/purlin)', html)
        self.assertIn('data-expanded="REMOTE COLLABORATION (github.com/rlabarca/purlin)"', html)


class TestSectionHeadingWithoutRemote(unittest.TestCase):
    """Scenario: Section Heading Without Remote

    Given the CDD server is running
    And no git remote is configured
    When the dashboard HTML is generated
    Then the REMOTE COLLABORATION section heading expanded text is "REMOTE COLLABORATION" with no parenthetical
    """

    @patch('serve._get_shortened_remote_url', return_value='')
    @patch('serve.get_isolation_worktrees', return_value=[])
    @patch('serve.get_active_remote_session', return_value=None)
    @patch('serve._has_git_remote', return_value=False)
    @patch('serve.get_remote_collab_sessions', return_value=[])
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_heading_plain_without_remote(self, *mocks):
        html = serve.generate_html()
        self.assertIn('data-expanded="REMOTE COLLABORATION"', html)
        self.assertNotIn('data-expanded="REMOTE COLLABORATION (', html)


def run_tests():
    """Run all tests and write results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    tests_dir = os.path.join(PROJECT_ROOT, 'tests', 'cdd_remote_collab')
    os.makedirs(tests_dir, exist_ok=True)
    status = "PASS" if result.wasSuccessful() else "FAIL"
    with open(os.path.join(tests_dir, 'tests.json'), 'w') as f:
        json.dump({"status": status}, f)

    print(f"\ntests.json: {status}")
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
