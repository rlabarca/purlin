"""Unit tests for CDD Collab Mode.

Covers all 8 automated scenarios from features/cdd_collab_mode.md.
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
import http.server

from serve import (
    _detect_worktrees,
    _role_from_branch,
    _worktree_state,
    _worktree_handoff_status,
    get_collab_worktrees,
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

    def test_impl_maps_to_builder(self):
        self.assertEqual(_role_from_branch('impl/task-crud'), 'builder')

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
        'dirty': False,
        'file_count': 0,
        'last_commit': 'abc1234 feat(spec): add scenarios (45 min ago)',
        'handoff_ready': True,
        'handoff_pending_count': 0,
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

    Given worktrees on branches spec/feature-a, impl/feature-a, qa/feature-a
    Then the worktrees array contains entries with roles architect, builder, qa.
    """

    @patch('serve._worktree_handoff_status', return_value=(True, 0))
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_three_roles_mapped(self, mock_detect, mock_state, mock_handoff):
        wt_base = os.path.join(PROJECT_ROOT, '.worktrees')
        mock_detect.return_value = [
            {'abs_path': os.path.join(wt_base, 'architect-session'),
             'branch_ref': 'refs/heads/spec/feature-a'},
            {'abs_path': os.path.join(wt_base, 'builder-session'),
             'branch_ref': 'refs/heads/impl/feature-a'},
            {'abs_path': os.path.join(wt_base, 'qa-session'),
             'branch_ref': 'refs/heads/qa/feature-a'},
        ]
        mock_state.side_effect = [
            {'branch': 'spec/feature-a', 'dirty': False,
             'file_count': 0, 'last_commit': 'abc spec'},
            {'branch': 'impl/feature-a', 'dirty': False,
             'file_count': 0, 'last_commit': 'def impl'},
            {'branch': 'qa/feature-a', 'dirty': False,
             'file_count': 0, 'last_commit': 'ghi qa'},
        ]
        result = get_collab_worktrees()
        roles = [wt['role'] for wt in result]
        self.assertIn('architect', roles)
        self.assertIn('builder', roles)
        self.assertIn('qa', roles)


class TestUnknownRoleForNonStandardBranch(unittest.TestCase):
    """Scenario: Unknown Role for Non-Standard Branch."""

    @patch('serve._worktree_handoff_status', return_value=(False, 1))
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_hotfix_maps_to_unknown(self, mock_detect, mock_state,
                                     mock_handoff):
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'hotfix-session')
        mock_detect.return_value = [
            {'abs_path': wt_path,
             'branch_ref': 'refs/heads/hotfix/urgent-fix'},
        ]
        mock_state.return_value = {
            'branch': 'hotfix/urgent-fix', 'dirty': False,
            'file_count': 0, 'last_commit': 'xyz hotfix',
        }
        result = get_collab_worktrees()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['role'], 'unknown')


class TestDirtyStateDetected(unittest.TestCase):
    """Scenario: Dirty State Detected."""

    @patch('serve._worktree_handoff_status', return_value=(False, 1))
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_dirty_worktree(self, mock_detect, mock_state, mock_handoff):
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'builder-session')
        mock_detect.return_value = [
            {'abs_path': wt_path,
             'branch_ref': 'refs/heads/impl/collab'},
        ]
        mock_state.return_value = {
            'branch': 'impl/collab',
            'dirty': True,
            'file_count': 3,
            'last_commit': 'def5678 feat(impl): handlers (12 min ago)',
        }
        result = get_collab_worktrees()
        self.assertEqual(len(result), 1)
        wt = result[0]
        self.assertTrue(wt['dirty'])
        self.assertGreater(wt['file_count'], 0)


class TestHandoffReadyWhenAutoStepsPass(unittest.TestCase):
    """Scenario: Handoff Ready When Auto-Steps Pass."""

    @patch('serve._worktree_handoff_status', return_value=(True, 0))
    @patch('serve._worktree_state')
    @patch('serve._detect_worktrees')
    def test_handoff_ready(self, mock_detect, mock_state, mock_handoff):
        wt_path = os.path.join(PROJECT_ROOT, '.worktrees', 'builder-session')
        mock_detect.return_value = [
            {'abs_path': wt_path,
             'branch_ref': 'refs/heads/impl/collab'},
        ]
        mock_state.return_value = {
            'branch': 'impl/collab',
            'dirty': False,
            'file_count': 0,
            'last_commit': 'def5678 status(impl): ready (5 min ago)',
        }
        result = get_collab_worktrees()
        self.assertEqual(len(result), 1)
        wt = result[0]
        self.assertTrue(wt['handoff_ready'])
        self.assertEqual(wt['handoff_pending_count'], 0)


class TestHandoffStatusEvaluation(unittest.TestCase):
    """Test the handoff status evaluation logic directly."""

    def _mock_wt_cmd(self, responses):
        """Create a mock that returns different values per call."""
        call_count = [0]

        def _side_effect(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(responses):
                result = MagicMock()
                result.stdout.strip.return_value = responses[idx]
                return result
            raise Exception(f"Unexpected call {idx}")

        return _side_effect

    @patch('subprocess.run')
    def test_builder_clean_with_rfv_is_ready(self, mock_run):
        """Builder with clean state and RFV commit is handoff-ready."""
        mock_run.side_effect = self._mock_wt_cmd([
            '',       # git status --porcelain (clean)
            '12345',  # git log --grep RFV (found)
        ])
        ready, pending = _worktree_handoff_status('/tmp/test', 'builder')
        self.assertTrue(ready)
        self.assertEqual(pending, 0)

    @patch('subprocess.run')
    def test_builder_dirty_not_ready(self, mock_run):
        """Builder with dirty state is not handoff-ready."""
        mock_run.side_effect = self._mock_wt_cmd([
            'M file.py',  # git status --porcelain (dirty)
            '12345',      # git log --grep RFV (found)
        ])
        ready, pending = _worktree_handoff_status('/tmp/test', 'builder')
        self.assertFalse(ready)
        self.assertGreater(pending, 0)


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
        """POST /start-collab (empty body) creates worktrees on spec/collab, impl/collab, qa/collab."""
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


import subprocess

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
