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
        # First call (rev-parse) succeeds = ref exists
        mock_run.return_value = MagicMock(returncode=0, stdout='abc1234', stderr='')

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
    """Scenario: Disconnect Clears Active Session

    Given an active session "v0.5-sprint" is set
    When a POST request is sent to /remote-collab/disconnect
    Then .purlin/runtime/active_remote_session is empty or absent
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

    def test_disconnect_clears_runtime(self):
        handler = MagicMock()
        handler.headers = {'Content-Length': '2'}
        handler.rfile = io.BytesIO(b'{}')
        handler._send_json = MagicMock()

        with patch.object(serve, 'PROJECT_ROOT', self.tmpdir):
            serve.Handler._handle_remote_collab_disconnect(handler)

        args = handler._send_json.call_args[0]
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1]['status'], 'ok')

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


class TestSyncStateNoMain(unittest.TestCase):
    """When local main branch does not exist, sync state returns NO_MAIN.

    Given an active session "v0.5-sprint" is set
    And the remote tracking ref origin/collab/v0.5-sprint exists
    But local branch "main" does not exist
    When compute_remote_sync_state is called
    Then sync_state is "NO_MAIN"
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_remote_config', return_value={'remote': 'origin', 'auto_fetch_interval': 300})
    def test_no_main_state(self, mock_config, mock_run):
        def run_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stderr='')
            if isinstance(cmd, list) and 'rev-parse' in cmd:
                ref = cmd[-1] if cmd else ''
                if ref == 'main':
                    raise subprocess.CalledProcessError(128, cmd)
                result.stdout = 'abc1234'
            else:
                result.stdout = ''
            return result
        mock_run.side_effect = run_side_effect

        state = serve.compute_remote_sync_state("v0.5-sprint")
        self.assertEqual(state['sync_state'], 'NO_MAIN')
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
    And local main has 3 commits not in origin/collab/v0.5-sprint
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
                # Check direction
                cmd_str = ' '.join(cmd)
                if '..main' in cmd_str:
                    result.stdout = 'abc commit1\ndef commit2\nghi commit3\n'
                else:
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
    And origin/collab/v0.5-sprint has 2 commits not in local main
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
                cmd_str = ' '.join(cmd)
                if '..main' in cmd_str:
                    result.stdout = ''  # ahead = 0
                else:
                    result.stdout = 'xyz commit1\nuvw commit2\n'  # behind = 2
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
    And local main has 1 commit not in origin/collab/v0.5-sprint
    And origin/collab/v0.5-sprint has 2 commits not in local main
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
                cmd_str = ' '.join(cmd)
                if '..main' in cmd_str:
                    result.stdout = 'abc commit1\n'  # ahead = 1
                else:
                    result.stdout = 'xyz commit1\nuvw commit2\n'  # behind = 2
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
    And origin/collab/v0.5-sprint has 2 commits not in local main
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
                if '..main' in cmd_str:
                    result.stdout = ''  # ahead = 0
                else:
                    result.stdout = 'xyz commit1\nuvw commit2\n'  # behind = 2
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
