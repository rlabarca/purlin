#!/usr/bin/env python3
"""Tests for git_timestamp_resilience feature.

Covers all 7 automated scenarios from features/git_timestamp_resilience.md.
Tests boundary-inclusive timestamp comparisons in critic.py and serve.py,
deterministic tiebreakers, and conservative fast-path behavior.

Outputs test results to tests/git_timestamp_resilience/tests.json.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Ensure we can import serve.py (same directory)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Also import from critic (sibling directory)
CRITIC_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'critic')
sys.path.insert(0, CRITIC_DIR)

from critic import _has_testing_phase_commit, _has_verified_complete_commit
from serve import build_status_commit_cache, get_feature_status, spec_content_unchanged


FIXED_TS = 1700000000  # 2023-11-14T22:13:20Z


class GitTimestampResilience(unittest.TestCase):
    """Base class with git repo helpers using controlled timestamps."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        subprocess.run(
            ['git', 'init'], cwd=self.root,
            capture_output=True, check=True)
        subprocess.run(
            ['git', 'config', 'user.email', 'test@test.com'], cwd=self.root,
            capture_output=True, check=True)
        subprocess.run(
            ['git', 'config', 'user.name', 'Test'], cwd=self.root,
            capture_output=True, check=True)

    def tearDown(self):
        shutil.rmtree(self.root)

    def _write_feature(self, content='# Feature: Foo\nContent.\n',
                       fname='foo.md'):
        fpath = os.path.join(self.features_dir, fname)
        with open(fpath, 'w') as f:
            f.write(content)
        return fpath

    def _git_commit_at(self, msg, ts, add_all=False):
        """Create a commit at a specific Unix timestamp."""
        iso_ts = f'@{ts}'  # Git accepts @<epoch> format
        env = os.environ.copy()
        env['GIT_COMMITTER_DATE'] = iso_ts
        env['GIT_AUTHOR_DATE'] = iso_ts
        if add_all:
            subprocess.run(
                ['git', 'add', '-A'], cwd=self.root,
                capture_output=True, check=True)
        subprocess.run(
            ['git', 'commit', '--allow-empty', '-m', msg],
            cwd=self.root, capture_output=True, check=True, env=env)

    def _git_add_commit_at(self, msg, ts):
        """Stage all and commit at a specific timestamp."""
        self._git_commit_at(msg, ts, add_all=True)


class TestSameSecondTestingCommitRecognized(GitTimestampResilience):
    """Scenario: Same-second TESTING commit is recognized

    Given a feature spec-modifying commit at Unix timestamp 1700000000
    And a TESTING-phase commit at Unix timestamp 1700000000
    When the Critic evaluates _has_testing_phase_commit()
    Then the function returns True
    """

    def test_same_second_testing_commit_recognized(self):
        self._write_feature()
        self._git_add_commit_at('initial feature', FIXED_TS)
        self._git_commit_at(
            'status: [Ready for Verification features/foo.md]', FIXED_TS)
        result = _has_testing_phase_commit(
            'features/foo.md', project_root=self.root)
        self.assertTrue(result,
                        'Same-second TESTING commit must be recognized with >= comparison')


class TestSameSecondVerifiedCompleteRecognized(GitTimestampResilience):
    """Scenario: Same-second Verified Complete commit is recognized

    Given a feature spec-modifying commit at Unix timestamp 1700000000
    And a Complete commit with [Verified] at Unix timestamp 1700000000
    When the Critic evaluates _has_verified_complete_commit()
    Then the function returns True
    """

    def test_same_second_verified_complete_recognized(self):
        self._write_feature()
        self._git_add_commit_at('initial feature', FIXED_TS)
        self._git_commit_at(
            'status: [Complete features/foo.md] [Verified]', FIXED_TS)
        result = _has_verified_complete_commit(
            'features/foo.md', project_root=self.root)
        self.assertTrue(result,
                        'Same-second Verified Complete commit must be recognized with >= comparison')


class TestEarlierTestingCommitRejected(GitTimestampResilience):
    """Scenario: Earlier TESTING commit is rejected

    Given a feature spec-modifying commit at Unix timestamp 1700000000
    And a TESTING-phase commit at Unix timestamp 1699999999
    When the Critic evaluates _has_testing_phase_commit()
    Then the function returns False
    """

    def test_earlier_testing_commit_rejected(self):
        self._write_feature()
        # TESTING commit at T-1
        self._git_add_commit_at('initial feature', FIXED_TS - 1)
        self._git_commit_at(
            'status: [Ready for Verification features/foo.md]', FIXED_TS - 1)
        # Spec modification at T (resets lifecycle)
        self._write_feature('# Feature: Foo\nUpdated.\n')
        self._git_add_commit_at('spec update', FIXED_TS)
        result = _has_testing_phase_commit(
            'features/foo.md', project_root=self.root)
        self.assertFalse(result,
                         'TESTING commit at earlier timestamp must be rejected')


class TestLaterTestingCommitAccepted(GitTimestampResilience):
    """Scenario: Later TESTING commit is accepted

    Given a feature spec-modifying commit at Unix timestamp 1700000000
    And a TESTING-phase commit at Unix timestamp 1700000001
    When the Critic evaluates _has_testing_phase_commit()
    Then the function returns True
    """

    def test_later_testing_commit_accepted(self):
        self._write_feature()
        self._git_add_commit_at('initial feature', FIXED_TS)
        self._git_commit_at(
            'status: [Ready for Verification features/foo.md]', FIXED_TS + 1)
        result = _has_testing_phase_commit(
            'features/foo.md', project_root=self.root)
        self.assertTrue(result,
                        'TESTING commit at later timestamp must be accepted')


class TestSameSecondScopeAssignmentDeterministic(GitTimestampResilience):
    """Scenario: Same-second scope assignment is deterministic

    Given a Complete commit and a TESTING commit at the same Unix timestamp
    When build_status_commit_cache() is invoked 10 times
    Then the scope value is identical across all invocations
    """

    def test_same_second_scope_assignment_deterministic(self):
        self._write_feature()
        self._git_add_commit_at('initial feature', FIXED_TS - 10)
        # Two status commits at the exact same timestamp
        self._git_commit_at(
            'status: [Complete features/foo.md] [Scope: full]', FIXED_TS)
        self._git_commit_at(
            'status: [Ready for Verification features/foo.md] [Scope: targeted:X]',
            FIXED_TS)

        results = []
        for _ in range(10):
            with patch('serve.run_command') as mock_cmd:
                # Simulate git log output with same-ts commits but different hashes
                mock_cmd.return_value = (
                    f'{FIXED_TS} aaaa0001 status: [Complete features/foo.md] [Scope: full]\n'
                    f'{FIXED_TS} bbbb0002 status: [Ready for Verification features/foo.md] [Scope: targeted:X]'
                )
                cache = build_status_commit_cache()
                scope = cache.get('features/foo.md', {}).get('scope')
                results.append(scope)

        # All 10 results must be identical
        self.assertTrue(all(r == results[0] for r in results),
                        f'Scope must be deterministic; got varying results: {set(results)}')
        # The lexicographically greater hash (bbbb0002) must win
        self.assertEqual(results[0], 'targeted:X',
                         'Lexicographically greater commit hash must win the tiebreak')


class TestSameSecondMtimeTriggersContentVerification(GitTimestampResilience):
    """Scenario: Same-second mtime triggers content verification

    Given a Complete status commit at Unix timestamp 1700000000
    And the feature file's modification time is Unix timestamp 1700000000
    When get_feature_status() is called
    Then spec_content_unchanged() is invoked (not the fast path)
    """

    def test_same_second_mtime_triggers_content_verification(self):
        self._write_feature()
        self._git_add_commit_at('initial feature', FIXED_TS - 10)

        cache = {
            'features/foo.md': {
                'complete_ts': FIXED_TS,
                'complete_hash': 'abc123',
                'testing_ts': 0,
                'testing_hash': '',
                'scope': None,
            }
        }

        # Set file mtime to exactly the same second as complete_ts
        fpath = os.path.join(self.features_dir, 'foo.md')
        os.utime(fpath, (FIXED_TS, FIXED_TS))

        with patch('serve.spec_content_unchanged', return_value=True) as mock_check:
            complete, testing, todo = get_feature_status(
                'features', self.features_dir, cache=cache)
            # spec_content_unchanged MUST be called (fast path not taken)
            mock_check.assert_called_once()
            # Feature should be COMPLETE (content unchanged)
            complete_names = [c[0] for c in complete]
            self.assertIn('foo.md', complete_names)


class TestStrictlyEarlierMtimeUsesFastPath(GitTimestampResilience):
    """Scenario: Strictly-earlier mtime uses fast path

    Given a Complete status commit at Unix timestamp 1700000000
    And the feature file's modification time is Unix timestamp 1699999999
    When get_feature_status() is called
    Then the fast path returns the cached status
    And spec_content_unchanged() is not invoked
    """

    def test_strictly_earlier_mtime_uses_fast_path(self):
        self._write_feature()
        self._git_add_commit_at('initial feature', FIXED_TS - 20)

        cache = {
            'features/foo.md': {
                'complete_ts': FIXED_TS,
                'complete_hash': 'abc123',
                'testing_ts': 0,
                'testing_hash': '',
                'scope': None,
            }
        }

        # Set file mtime to strictly before complete_ts
        fpath = os.path.join(self.features_dir, 'foo.md')
        os.utime(fpath, (FIXED_TS - 1, FIXED_TS - 1))

        with patch('serve.spec_content_unchanged') as mock_check:
            complete, testing, todo = get_feature_status(
                'features', self.features_dir, cache=cache)
            # spec_content_unchanged must NOT be called (fast path taken)
            mock_check.assert_not_called()
            # Feature should be COMPLETE via fast path
            complete_names = [c[0] for c in complete]
            self.assertIn('foo.md', complete_names)


# ===================================================================
# Test Runner — produces tests/git_timestamp_resilience/tests.json
# ===================================================================

def run_tests():
    """Run all tests and write results to tests.json."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Determine project root
    project_root = os.environ.get('PURLIN_PROJECT_ROOT')
    if not project_root:
        # Climb from tools/cdd/ -> project root
        project_root = os.path.dirname(os.path.dirname(SCRIPT_DIR))

    output_dir = os.path.join(project_root, 'tests', 'git_timestamp_resilience')
    os.makedirs(output_dir, exist_ok=True)

    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed

    report = {
        'status': 'PASS' if failed == 0 else 'FAIL',
        'passed': passed,
        'failed': failed,
        'total': total,
        'test_file': 'tools/cdd/test_timestamp_resilience.py',
    }

    output_path = os.path.join(output_dir, 'tests.json')
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f'\nResults written to {output_path}')
    return result


if __name__ == '__main__':
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
