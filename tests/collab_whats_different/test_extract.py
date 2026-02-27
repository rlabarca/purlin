#!/usr/bin/env python3
"""Tests for the What's Different extraction tool.

Covers automated scenarios from features/collab_whats_different.md:
- Extraction Tool Produces Correct JSON for SAME/AHEAD/BEHIND/DIVERGED State
- Feature File Changes Correctly Categorized
- Status Commits Parsed Into Lifecycle Transitions
"""
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add the tools/collab directory to the path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
COLLAB_DIR = os.path.join(PROJECT_ROOT, 'tools', 'collab')
sys.path.insert(0, COLLAB_DIR)

import extract_whats_different as ext


class TestSyncStateComputation(unittest.TestCase):
    """Test compute_sync_state returns correct states."""

    @patch.object(ext, '_run_git')
    def test_same_state(self, mock_git):
        """Scenario: Extraction Tool Produces Correct JSON for SAME State"""
        # Both ranges return empty — no commits in either direction
        mock_git.return_value = ''
        result = ext.compute_sync_state('test-session')
        self.assertEqual(result['sync_state'], 'SAME')
        self.assertEqual(result['commits_ahead'], 0)
        self.assertEqual(result['commits_behind'], 0)

    @patch.object(ext, '_run_git')
    def test_ahead_state(self, mock_git):
        """Scenario: Extraction Tool Produces Correct JSON for AHEAD State"""
        def side_effect(args, cwd=None):
            range_arg = args[1] if len(args) > 1 else ''
            if '..main' in range_arg:
                # Local ahead of remote
                return 'abc1234 commit 1\ndef5678 commit 2\nghi9012 commit 3\n'
            else:
                # Remote has nothing ahead
                return ''
        mock_git.side_effect = side_effect

        result = ext.compute_sync_state('test-session')
        self.assertEqual(result['sync_state'], 'AHEAD')
        self.assertEqual(result['commits_ahead'], 3)
        self.assertEqual(result['commits_behind'], 0)

    @patch.object(ext, '_run_git')
    def test_behind_state(self, mock_git):
        """Scenario: Extraction Tool Produces Correct JSON for BEHIND State"""
        def side_effect(args, cwd=None):
            range_arg = args[1] if len(args) > 1 else ''
            if '..main' in range_arg:
                return ''
            else:
                return 'abc1234 commit 1\ndef5678 commit 2\n'
        mock_git.side_effect = side_effect

        result = ext.compute_sync_state('test-session')
        self.assertEqual(result['sync_state'], 'BEHIND')
        self.assertEqual(result['commits_ahead'], 0)
        self.assertEqual(result['commits_behind'], 2)

    @patch.object(ext, '_run_git')
    def test_diverged_state(self, mock_git):
        """Scenario: Extraction Tool Produces Correct JSON for DIVERGED State"""
        def side_effect(args, cwd=None):
            range_arg = args[1] if len(args) > 1 else ''
            if '..main' in range_arg:
                return 'abc1234 local commit\n'
            else:
                return 'xyz7890 remote commit 1\nuvw3456 remote commit 2\n'
        mock_git.side_effect = side_effect

        result = ext.compute_sync_state('test-session')
        self.assertEqual(result['sync_state'], 'DIVERGED')
        self.assertEqual(result['commits_ahead'], 1)
        self.assertEqual(result['commits_behind'], 2)


class TestFullExtraction(unittest.TestCase):
    """Test the full extract() function produces correct structure."""

    @patch.object(ext, '_run_git')
    def test_same_state_empty_arrays(self, mock_git):
        """Scenario: SAME state produces empty arrays."""
        mock_git.return_value = ''
        result = ext.extract('test-session')
        self.assertEqual(result['sync_state'], 'SAME')
        self.assertEqual(result['local_changes'], [])
        self.assertEqual(result['collab_changes'], [])

    @patch.object(ext, '_run_git')
    def test_ahead_has_local_changes_only(self, mock_git):
        """Scenario: AHEAD state has local_changes populated, collab_changes empty."""
        call_count = [0]
        def side_effect(args, cwd=None):
            # compute_sync_state calls
            if args[0] == 'log':
                range_arg = args[1] if len(args) > 1 else ''
                if '..main' in range_arg:
                    return 'abc1234 feat: add login\ndef5678 test: add tests\nghi9012 fix: typo\n'
                else:
                    return ''
            # extract_direction calls (diff --name-status)
            if args[0] == 'diff':
                return 'M\ttools/auth/login.py\nA\ttests/auth/test_login.py\n'
            return ''
        mock_git.side_effect = side_effect

        result = ext.extract('test-session')
        self.assertEqual(result['sync_state'], 'AHEAD')
        self.assertNotEqual(result['local_changes'], [])
        self.assertEqual(result['collab_changes'], [])
        self.assertEqual(result['commits_ahead'], 3)

    @patch.object(ext, '_run_git')
    def test_behind_has_collab_changes_only(self, mock_git):
        """Scenario: BEHIND state has collab_changes populated, local_changes empty."""
        def side_effect(args, cwd=None):
            if args[0] == 'log':
                range_arg = args[1] if len(args) > 1 else ''
                if '..main' in range_arg:
                    return ''
                else:
                    return 'abc1234 feat: remote change 1\ndef5678 feat: remote change 2\n'
            if args[0] == 'diff':
                return 'M\tfeatures/login.md\nA\ttools/auth/remote.py\n'
            return ''
        mock_git.side_effect = side_effect

        result = ext.extract('test-session')
        self.assertEqual(result['sync_state'], 'BEHIND')
        self.assertEqual(result['local_changes'], [])
        self.assertNotEqual(result['collab_changes'], [])

    @patch.object(ext, '_run_git')
    def test_diverged_has_both_directions(self, mock_git):
        """Scenario: DIVERGED state has both local_changes and collab_changes."""
        def side_effect(args, cwd=None):
            if args[0] == 'log':
                range_arg = args[1] if len(args) > 1 else ''
                if '..main' in range_arg:
                    return 'abc1234 local commit\n'
                else:
                    return 'xyz7890 remote commit 1\nuvw3456 remote commit 2\n'
            if args[0] == 'diff':
                range_arg = args[1] if len(args) > 1 else ''
                if '..main' in range_arg:
                    return 'M\ttools/local_file.py\n'
                else:
                    return 'M\ttools/remote_file.py\n'
            return ''
        mock_git.side_effect = side_effect

        result = ext.extract('test-session')
        self.assertEqual(result['sync_state'], 'DIVERGED')
        self.assertNotEqual(result['local_changes'], [])
        self.assertNotEqual(result['collab_changes'], [])


class TestFileCategorization(unittest.TestCase):
    """Test categorize_file correctly classifies file paths.

    Scenario: Feature File Changes Correctly Categorized
    """

    def test_feature_spec(self):
        self.assertEqual(ext.categorize_file('features/login.md'), 'feature_spec')

    def test_anchor_node_arch(self):
        self.assertEqual(ext.categorize_file('features/arch_data_layer.md'), 'anchor_node')

    def test_anchor_node_design(self):
        self.assertEqual(ext.categorize_file('features/design_visual_standards.md'), 'anchor_node')

    def test_policy_node(self):
        self.assertEqual(ext.categorize_file('features/policy_critic.md'), 'policy_node')

    def test_companion_file(self):
        self.assertEqual(ext.categorize_file('features/login.impl.md'), 'companion')

    def test_visual_spec_design_dir(self):
        self.assertEqual(ext.categorize_file('features/design/login/mockup.png'), 'visual_spec')

    def test_test_file(self):
        self.assertEqual(ext.categorize_file('tests/auth/test_login.py'), 'test')

    def test_code_file(self):
        self.assertEqual(ext.categorize_file('tools/auth/login.py'), 'code')

    def test_purlin_config(self):
        self.assertEqual(ext.categorize_file('.purlin/config.json'), 'purlin_config')

    def test_submodule(self):
        self.assertEqual(ext.categorize_file('purlin/tools/cdd/serve.py'), 'submodule')

    def test_gitmodules(self):
        self.assertEqual(ext.categorize_file('.gitmodules'), 'submodule')


class TestLifecycleTransitions(unittest.TestCase):
    """Test _parse_lifecycle_transitions extracts status changes.

    Scenario: Status Commits Parsed Into Lifecycle Transitions
    """

    def test_complete_transition(self):
        commits = [
            {'hash': 'abc', 'subject': '[Complete features/login.md] [Scope: full]'},
        ]
        transitions = ext._parse_lifecycle_transitions(commits)
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0]['feature'], 'login.md')
        self.assertEqual(transitions[0]['from_state'], 'TESTING')
        self.assertEqual(transitions[0]['to_state'], 'COMPLETE')

    def test_ready_for_verification_transition(self):
        commits = [
            {'hash': 'def', 'subject': '[Ready for Verification features/auth.md] [Scope: targeted:Login]'},
        ]
        transitions = ext._parse_lifecycle_transitions(commits)
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0]['feature'], 'auth.md')
        self.assertEqual(transitions[0]['from_state'], 'TODO')
        self.assertEqual(transitions[0]['to_state'], 'TESTING')

    def test_non_status_commit_no_transition(self):
        commits = [
            {'hash': 'ghi', 'subject': 'spec(auth): add edge-case scenarios'},
        ]
        transitions = ext._parse_lifecycle_transitions(commits)
        self.assertEqual(len(transitions), 0)

    def test_mixed_commits(self):
        commits = [
            {'hash': 'abc', 'subject': '[Complete features/login.md] [Scope: full]'},
            {'hash': 'def', 'subject': 'feat(auth): implement login flow'},
            {'hash': 'ghi', 'subject': '[Ready for Verification features/auth.md]'},
        ]
        transitions = ext._parse_lifecycle_transitions(commits)
        self.assertEqual(len(transitions), 2)
        features = {t['feature'] for t in transitions}
        self.assertIn('login.md', features)
        self.assertIn('auth.md', features)


class TestChangesCategorization(unittest.TestCase):
    """Test _categorize_changes groups files correctly."""

    def test_mixed_files_grouped(self):
        files = [
            {'path': 'features/login.md', 'status': 'M'},
            {'path': 'features/arch_data_layer.md', 'status': 'M'},
            {'path': 'features/login.impl.md', 'status': 'A'},
            {'path': 'tools/auth/login.py', 'status': 'M'},
            {'path': 'tests/auth/test_login.py', 'status': 'A'},
            {'path': '.purlin/config.json', 'status': 'M'},
        ]
        cats = ext._categorize_changes(files)
        self.assertEqual(len(cats['feature_specs']), 1)
        self.assertEqual(len(cats['anchor_nodes']), 1)
        self.assertEqual(len(cats['companion_files']), 1)
        self.assertEqual(len(cats['code']), 1)
        self.assertEqual(len(cats['tests']), 1)
        self.assertEqual(len(cats['purlin_config']), 1)


if __name__ == '__main__':
    unittest.main()
