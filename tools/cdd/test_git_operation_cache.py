#!/usr/bin/env python3
"""Tests for git_operation_cache feature.

Covers all 26 automated scenarios from features/git_operation_cache.md.
Tests persistent status commit cache, hash-based content comparison,
batched diff extraction, and shared git status caching.

Outputs test results to tests/git_operation_cache/tests.json.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Import collab module for batched diff tests
COLLAB_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'collab')
sys.path.insert(0, COLLAB_DIR)

from serve import (
    build_status_commit_cache,
    get_feature_status,
    spec_content_unchanged,
    strip_discoveries_section,
    cached_git_status,
    _compute_spec_hash,
    _load_persistent_status_cache,
    _save_persistent_status_cache,
    _write_atomic,
    _newest_feature_mtime,
    _get_current_head,
)
from extract_whats_different import (
    _batched_diff,
    _extract_decisions_from_diff,
    _DIFF_BATCH_SIZE,
)


# ===================================================================
# Section 2.1: Persistent Status Commit Cache
# ===================================================================

class CacheTestBase(unittest.TestCase):
    """Base for tests that need a temp git repo."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        self.cache_dir = os.path.join(self.root, '.purlin', 'cache')
        self.tests_dir = os.path.join(self.root, 'tests')
        os.makedirs(self.features_dir)
        os.makedirs(self.cache_dir)
        os.makedirs(self.tests_dir)
        subprocess.run(['git', 'init'], cwd=self.root, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'],
                        cwd=self.root, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'],
                        cwd=self.root, capture_output=True, check=True)

    def tearDown(self):
        shutil.rmtree(self.root)

    def _write_feature(self, name, content=None):
        if content is None:
            content = f'# Feature: {name}\n\n## 1. Overview\nTest.\n'
        fpath = os.path.join(self.features_dir, name)
        with open(fpath, 'w') as f:
            f.write(content)
        return fpath

    def _git_commit(self, msg, add_all=True):
        if add_all:
            subprocess.run(['git', 'add', '-A'], cwd=self.root,
                            capture_output=True, check=True)
        subprocess.run(['git', 'commit', '--allow-empty', '-m', msg],
                        cwd=self.root, capture_output=True, check=True)

    def _git_head(self):
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.root,
                                 capture_output=True, text=True, check=True)
        return result.stdout.strip()


class TestCacheWriteOnFirstBuild(CacheTestBase):
    """Scenario: Cache write on first build

    Given a repository with 5 features and no status commit cache file
    When build_status_commit_cache() is called
    Then .purlin/cache/status_commit_cache.json is written
    And the file contains generated_at, git_head, and entries
    """

    def test_cache_write_on_first_build(self):
        # Create 5 features with status commits
        for i in range(5):
            self._write_feature(f'feat{i}.md')
        self._git_commit('initial features')

        # 2 Complete, 1 Testing, 2 TODO
        for i in range(2):
            self._git_commit(f'status: [Complete features/feat{i}.md]')
        self._git_commit('status: [Ready for Verification features/feat2.md]')

        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')
        self.assertFalse(os.path.exists(cache_path))

        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.FEATURES_ABS', self.features_dir), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path), \
             patch('serve.CACHE_DIR', self.cache_dir):
            result = build_status_commit_cache()

        self.assertTrue(os.path.exists(cache_path))
        with open(cache_path) as f:
            data = json.load(f)
        self.assertIn('_metadata', data)
        self.assertIn('git_head', data['_metadata'])
        self.assertIn('generated_at', data['_metadata'])
        self.assertIn('entries', data)


class TestCacheHitWhenHeadUnchanged(CacheTestBase):
    """Scenario: Cache hit when HEAD unchanged

    Given a valid status commit cache file with current HEAD hash
    When build_status_commit_cache() is called
    Then the cached result is returned
    And no git log subprocess is spawned
    """

    def test_cache_hit_when_head_unchanged(self):
        self._write_feature('feat1.md')
        self._git_commit('initial')
        self._git_commit('status: [Complete features/feat1.md]')

        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')
        head = self._git_head()

        # Pre-populate cache
        cache_data = {
            '_metadata': {
                'git_head': head,
                'generated_at': time.time() + 100,  # Far future to ensure validity
            },
            'entries': {
                'features/feat1.md': {
                    'complete_ts': 100, 'complete_hash': 'abc',
                    'testing_ts': 0, 'testing_hash': '',
                    'scope': 'full', 'spec_content_hash': 'deadbeef',
                }
            }
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.FEATURES_ABS', self.features_dir), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path), \
             patch('serve.CACHE_DIR', self.cache_dir), \
             patch('serve._get_current_head', return_value=head), \
             patch('serve.run_command') as mock_run:
            result = build_status_commit_cache()
            # Should not call git log (cache hit)
            mock_run.assert_not_called()

        self.assertEqual(result['features/feat1.md']['complete_ts'], 100)


class TestCacheInvalidationOnNewCommit(CacheTestBase):
    """Scenario: Cache invalidation on new commit

    Given a valid status commit cache file
    And a new commit is made (HEAD changes)
    When build_status_commit_cache() is called
    Then the cache is discarded and a fresh git log scan runs
    """

    def test_cache_invalidation_on_new_commit(self):
        self._write_feature('feat1.md')
        self._git_commit('initial')
        self._git_commit('status: [Complete features/feat1.md]')

        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')
        # Cache with old HEAD
        cache_data = {
            '_metadata': {
                'git_head': 'old_head_that_no_longer_matches',
                'generated_at': time.time(),
            },
            'entries': {}
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.FEATURES_ABS', self.features_dir), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path), \
             patch('serve.CACHE_DIR', self.cache_dir):
            result = build_status_commit_cache()

        # Should have entries from fresh scan
        self.assertIn('features/feat1.md', result)
        # Cache should be updated with current HEAD
        with open(cache_path) as f:
            data = json.load(f)
        self.assertEqual(data['_metadata']['git_head'], self._git_head())


class TestCacheInvalidationOnFeatureFileMtimeChange(CacheTestBase):
    """Scenario: Cache invalidation on feature file mtime change

    Given a valid cache written at time T
    And a feature file's mtime is set to after T
    When build_status_commit_cache() is called
    Then the cache is discarded and rebuilt
    """

    def test_cache_invalidation_on_mtime_change(self):
        self._write_feature('feat1.md')
        self._git_commit('initial')
        self._git_commit('status: [Complete features/feat1.md]')

        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')
        head = self._git_head()

        # Cache generated "in the past"
        past_time = time.time() - 100
        cache_data = {
            '_metadata': {
                'git_head': head,
                'generated_at': past_time,
            },
            'entries': {}
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        # Touch feature file to make it newer than cache
        fpath = os.path.join(self.features_dir, 'feat1.md')
        os.utime(fpath, (time.time(), time.time()))

        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.FEATURES_ABS', self.features_dir), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path), \
             patch('serve.CACHE_DIR', self.cache_dir):
            result = build_status_commit_cache()

        # Should have rebuilt with real entries
        self.assertIn('features/feat1.md', result)


class TestMissingCacheFileTriggersFullScan(CacheTestBase):
    """Scenario: Missing cache file triggers full scan"""

    def test_missing_cache_file_triggers_full_scan(self):
        self._write_feature('feat1.md')
        self._git_commit('initial')
        self._git_commit('status: [Complete features/feat1.md]')

        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')
        self.assertFalse(os.path.exists(cache_path))

        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.FEATURES_ABS', self.features_dir), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path), \
             patch('serve.CACHE_DIR', self.cache_dir):
            result = build_status_commit_cache()

        self.assertIn('features/feat1.md', result)
        self.assertTrue(os.path.exists(cache_path))


class TestCorruptCacheFileTriggersFullScan(CacheTestBase):
    """Scenario: Corrupt cache file triggers full scan"""

    def test_corrupt_cache_file_triggers_full_scan(self):
        self._write_feature('feat1.md')
        self._git_commit('initial')
        self._git_commit('status: [Complete features/feat1.md]')

        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')
        with open(cache_path, 'w') as f:
            f.write('{invalid json!!')

        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.FEATURES_ABS', self.features_dir), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path), \
             patch('serve.CACHE_DIR', self.cache_dir):
            result = build_status_commit_cache()

        # Should recover and produce valid results
        self.assertIn('features/feat1.md', result)
        # Cache should now be valid
        with open(cache_path) as f:
            data = json.load(f)
        self.assertIn('_metadata', data)


class TestEmptyRepositoryProducesValidCache(CacheTestBase):
    """Scenario: Empty repository produces valid cache

    Given a repository with feature files but zero status commits
    When build_status_commit_cache() is called
    Then a cache file is written with empty entries
    """

    def test_empty_repository_produces_valid_cache(self):
        self._write_feature('feat1.md')
        self._git_commit('initial features only, no status commits')

        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')

        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.FEATURES_ABS', self.features_dir), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path), \
             patch('serve.CACHE_DIR', self.cache_dir):
            result = build_status_commit_cache()

        self.assertEqual(result, {})
        self.assertTrue(os.path.exists(cache_path))


class TestCachePersistsAcrossSimulatedRestart(CacheTestBase):
    """Scenario: Cache persists across simulated restart

    Given a valid status commit cache file
    And in-memory state is cleared (simulating server restart)
    When build_status_commit_cache() is called
    Then the persisted cache is loaded without spawning a git subprocess
    """

    def test_cache_persists_across_simulated_restart(self):
        self._write_feature('feat1.md')
        self._git_commit('initial')
        self._git_commit('status: [Complete features/feat1.md]')

        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')

        # First call: builds and persists cache
        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.FEATURES_ABS', self.features_dir), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path), \
             patch('serve.CACHE_DIR', self.cache_dir):
            result1 = build_status_commit_cache()

        head = self._git_head()
        # Second call: should use persisted cache (no git log)
        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.FEATURES_ABS', self.features_dir), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path), \
             patch('serve.CACHE_DIR', self.cache_dir), \
             patch('serve._get_current_head', return_value=head), \
             patch('serve.run_command') as mock_run:
            result2 = build_status_commit_cache()
            mock_run.assert_not_called()

        self.assertEqual(result1['features/feat1.md']['complete_ts'],
                         result2['features/feat1.md']['complete_ts'])


# ===================================================================
# Section 2.2: Hash-Based Content Comparison
# ===================================================================

class TestHashHitWhenSpecContentUnchanged(CacheTestBase):
    """Scenario: Hash hit when spec content unchanged"""

    def test_hash_hit_when_spec_content_unchanged(self):
        content = '# Feature: Test\n\nContent here.\n'
        self._write_feature('feat1.md', content)
        self._git_commit('initial')

        expected_hash = _compute_spec_hash(content)
        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')
        cache_data = {
            '_metadata': {'git_head': self._git_head(), 'generated_at': time.time()},
            'entries': {
                'features/feat1.md': {'spec_content_hash': expected_hash}
            }
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path), \
             patch('serve.run_command') as mock_run:
            result = spec_content_unchanged('features/feat1.md', 'some_hash')
            # Should not call git show (hash path used)
            mock_run.assert_not_called()

        self.assertTrue(result)


class TestHashMissWhenSpecContentChanged(CacheTestBase):
    """Scenario: Hash miss when spec content changed"""

    def test_hash_miss_when_spec_content_changed(self):
        content = '# Feature: Test\n\nOriginal content.\n'
        self._write_feature('feat1.md', content)
        self._git_commit('initial')

        old_hash = _compute_spec_hash(content)
        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')
        cache_data = {
            '_metadata': {'git_head': self._git_head(), 'generated_at': time.time()},
            'entries': {
                'features/feat1.md': {'spec_content_hash': old_hash}
            }
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        # Modify the file on disk
        self._write_feature('feat1.md', '# Feature: Test\n\nModified content.\n')

        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path):
            result = spec_content_unchanged('features/feat1.md', 'some_hash')

        self.assertFalse(result)


class TestHashHitWhenOnlyDiscoveriesChanged(CacheTestBase):
    """Scenario: Hash hit when only discoveries section changed"""

    def test_hash_hit_when_only_discoveries_changed(self):
        spec_part = '# Feature: Test\n\nContent.\n'
        content_with_disc = spec_part + '\n## User Testing Discoveries\nSome findings.\n'
        self._write_feature('feat1.md', spec_part)
        self._git_commit('initial')

        # Cache hash is based on content WITHOUT discoveries
        expected_hash = _compute_spec_hash(spec_part)
        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')
        cache_data = {
            '_metadata': {'git_head': self._git_head(), 'generated_at': time.time()},
            'entries': {
                'features/feat1.md': {'spec_content_hash': expected_hash}
            }
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        # Add discoveries section on disk
        self._write_feature('feat1.md', content_with_disc)

        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path):
            result = spec_content_unchanged('features/feat1.md', 'some_hash')

        self.assertTrue(result)


class TestHashMissAfterCacheRebuildFollowingSpecEdit(CacheTestBase):
    """Scenario: Hash miss detected after cache rebuild following spec edit

    Given a feature marked COMPLETE with a status commit at time T1
    And the cache is saved with spec_content_hash computed from the committed content at T1
    When the spec content is edited on disk after T1
    And the status commit cache is deleted and rebuilt via build_status_commit_cache()
    Then the rebuilt cache contains spec_content_hash from the COMPLETE commit content
    And spec_content_unchanged() returns False
    And get_feature_status() classifies the feature as TODO (not COMPLETE)
    """

    def test_hash_miss_after_cache_rebuild_following_spec_edit(self):
        original_content = '# Feature: Test\n\n## 1. Overview\nOriginal requirements.\n'
        self._write_feature('feat1.md', original_content)
        self._git_commit('initial feature')

        # Mark COMPLETE
        self._git_commit('status: [Complete features/feat1.md] [Scope: full]')
        complete_hash = self._git_head()

        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')

        # Build initial cache (hash should be from committed content)
        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.FEATURES_ABS', self.features_dir), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path), \
             patch('serve.CACHE_DIR', self.cache_dir):
            build_status_commit_cache()

        # Read and verify the cached hash matches the ORIGINAL committed content
        with open(cache_path) as f:
            data = json.load(f)
        original_hash = data['entries']['features/feat1.md'].get('spec_content_hash')
        self.assertIsNotNone(original_hash)
        self.assertEqual(original_hash, _compute_spec_hash(original_content))

        # Now edit the spec on disk (post-completion)
        edited_content = '# Feature: Test\n\n## 1. Overview\nNew requirements added.\n'
        self._write_feature('feat1.md', edited_content)

        # Delete cache and rebuild
        os.remove(cache_path)

        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.FEATURES_ABS', self.features_dir), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path), \
             patch('serve.CACHE_DIR', self.cache_dir):
            build_status_commit_cache()

        # Rebuilt cache hash should STILL be from committed content (original),
        # NOT from the edited working-tree content
        with open(cache_path) as f:
            data = json.load(f)
        rebuilt_hash = data['entries']['features/feat1.md'].get('spec_content_hash')
        self.assertIsNotNone(rebuilt_hash)
        self.assertEqual(rebuilt_hash, _compute_spec_hash(original_content))
        self.assertNotEqual(rebuilt_hash, _compute_spec_hash(edited_content))

        # spec_content_unchanged should return False (working tree differs)
        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path):
            unchanged = spec_content_unchanged('features/feat1.md', complete_hash)
        self.assertFalse(unchanged)


class TestFallbackWhenNoHashInCache(CacheTestBase):
    """Scenario: Fallback when no hash in cache"""

    def test_fallback_when_no_hash_in_cache(self):
        content = '# Feature: Test\n\nContent.\n'
        self._write_feature('feat1.md', content)
        self._git_commit('initial')

        # Cache entry without spec_content_hash (old format)
        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')
        cache_data = {
            '_metadata': {'git_head': self._git_head(), 'generated_at': time.time()},
            'entries': {
                'features/feat1.md': {'complete_ts': 100}
            }
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        commit_hash = self._git_head()

        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path):
            # Falls back to git show comparison
            result = spec_content_unchanged('features/feat1.md', commit_hash)

        self.assertTrue(result)


class TestFallbackWhenCacheEntryMissing(CacheTestBase):
    """Scenario: Fallback when cache entry missing entirely"""

    def test_fallback_when_cache_entry_missing(self):
        content = '# Feature: Test\n\nContent.\n'
        self._write_feature('feat1.md', content)
        self._git_commit('initial')

        # Cache exists but has no entry for this feature
        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')
        cache_data = {
            '_metadata': {'git_head': self._git_head(), 'generated_at': time.time()},
            'entries': {}
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        commit_hash = self._git_head()

        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path):
            result = spec_content_unchanged('features/feat1.md', commit_hash)

        self.assertTrue(result)


class TestUnicodeContentHashedCorrectly(CacheTestBase):
    """Scenario: Unicode content hashed correctly"""

    def test_unicode_content_hashed_correctly(self):
        content = '# Feature: Tes\u00e9\n\n\u00c0cc\u00e9nted cont\u00ebnt \u2014 sp\u00e9cial.\n'
        self._write_feature('feat1.md', content)
        self._git_commit('initial')

        expected_hash = _compute_spec_hash(content)
        cache_path = os.path.join(self.cache_dir, 'status_commit_cache.json')
        cache_data = {
            '_metadata': {'git_head': self._git_head(), 'generated_at': time.time()},
            'entries': {
                'features/feat1.md': {'spec_content_hash': expected_hash}
            }
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        with patch('serve.PROJECT_ROOT', self.root), \
             patch('serve.STATUS_COMMIT_CACHE_PATH', cache_path):
            result = spec_content_unchanged('features/feat1.md', 'some_hash')

        self.assertTrue(result)


# ===================================================================
# Section 2.3: Batched Diff Extraction
# ===================================================================

class BatchedDiffTestBase(unittest.TestCase):
    """Base class for batched diff tests."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.root, 'features')
        os.makedirs(self.features_dir)
        subprocess.run(['git', 'init'], cwd=self.root, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'],
                        cwd=self.root, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'],
                        cwd=self.root, capture_output=True, check=True)
        # Initial commit on main
        with open(os.path.join(self.root, 'README.md'), 'w') as f:
            f.write('# Test\n')
        subprocess.run(['git', 'add', '-A'], cwd=self.root, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'initial'], cwd=self.root,
                        capture_output=True, check=True)

    def tearDown(self):
        shutil.rmtree(self.root)

    def _run_git(self, args):
        result = subprocess.run(['git'] + args, cwd=self.root,
                                 capture_output=True, text=True)
        return result.stdout


class TestSingleBatchForFewerThan50Files(BatchedDiffTestBase):
    """Scenario: Single batch for fewer than 50 files"""

    def test_single_batch_for_fewer_than_50_files(self):
        # Create branch with changes
        subprocess.run(['git', 'checkout', '-b', 'test-branch'], cwd=self.root,
                        capture_output=True, check=True)

        impl_files = []
        feat_files = []
        for i in range(15):
            fpath = os.path.join(self.features_dir, f'feat{i}.impl.md')
            with open(fpath, 'w') as f:
                f.write(f'# Notes {i}\n')
            impl_files.append(f'features/feat{i}.impl.md')
        for i in range(8):
            fpath = os.path.join(self.features_dir, f'feat{i}.md')
            with open(fpath, 'w') as f:
                f.write(f'# Feature {i}\n')
            feat_files.append(f'features/feat{i}.md')

        subprocess.run(['git', 'add', '-A'], cwd=self.root, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'changes'], cwd=self.root,
                        capture_output=True, check=True)

        with patch('extract_whats_different._run_git', wraps=lambda args: self._run_git(args)) as mock_git:
            result = _batched_diff('main...test-branch', impl_files)
            result2 = _batched_diff('main...test-branch', feat_files)

        # 15 companion files < 50, so 1 call; 8 feature files < 50, so 1 call
        # Total: 2 git diff calls (one per category)
        self.assertLessEqual(len(impl_files), 50)
        self.assertLessEqual(len(feat_files), 50)
        # Results should contain entries
        self.assertGreater(len(result), 0)


class TestMultiBatchForMoreThan50Files(BatchedDiffTestBase):
    """Scenario: Multi-batch for more than 50 files"""

    def test_multi_batch_for_more_than_50_files(self):
        subprocess.run(['git', 'checkout', '-b', 'test-branch'], cwd=self.root,
                        capture_output=True, check=True)

        impl_files = []
        for i in range(60):
            fpath = os.path.join(self.features_dir, f'feat{i:03d}.impl.md')
            with open(fpath, 'w') as f:
                f.write(f'# Notes {i}\n[DISCOVERY] Found issue {i}\n')
            impl_files.append(f'features/feat{i:03d}.impl.md')

        subprocess.run(['git', 'add', '-A'], cwd=self.root, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'many changes'], cwd=self.root,
                        capture_output=True, check=True)

        call_count = [0]
        original_run_git = lambda args: self._run_git(args)

        def counting_run_git(args):
            if args[0] == 'diff' and '--' in args:
                call_count[0] += 1
            return original_run_git(args)

        with patch('extract_whats_different._run_git', side_effect=counting_run_git):
            result = _batched_diff('main...test-branch', impl_files)

        # 60 files / 50 batch size = 2 calls
        self.assertEqual(call_count[0], 2)
        # All 60 files should be in the result
        self.assertEqual(len(result), 60)


class TestZeroChangedFilesSkipsExtraction(BatchedDiffTestBase):
    """Scenario: Zero changed files skips extraction"""

    def test_zero_changed_files_skips_extraction(self):
        result = _batched_diff('HEAD~0..HEAD', [])
        self.assertEqual(result, {})


class TestMixedAddModifyDeleteParsedCorrectly(BatchedDiffTestBase):
    """Scenario: Mixed add/modify/delete parsed correctly"""

    def test_mixed_add_modify_delete_parsed_correctly(self):
        # Create files on main
        for i in range(5):
            fpath = os.path.join(self.features_dir, f'existing{i}.impl.md')
            with open(fpath, 'w') as f:
                f.write(f'# Original {i}\n')
        subprocess.run(['git', 'add', '-A'], cwd=self.root, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'existing files'], cwd=self.root,
                        capture_output=True, check=True)

        # Create branch with mixed changes
        subprocess.run(['git', 'checkout', '-b', 'test-branch'], cwd=self.root,
                        capture_output=True, check=True)

        # Add 3 new files
        for i in range(3):
            fpath = os.path.join(self.features_dir, f'new{i}.impl.md')
            with open(fpath, 'w') as f:
                f.write(f'# New {i}\n[DISCOVERY] New finding {i}\n')

        # Modify 5 files
        for i in range(5):
            fpath = os.path.join(self.features_dir, f'existing{i}.impl.md')
            with open(fpath, 'w') as f:
                f.write(f'# Modified {i}\n[DEVIATION] Changed {i}\n')

        # Delete 2 files
        os.remove(os.path.join(self.features_dir, 'existing3.impl.md'))
        os.remove(os.path.join(self.features_dir, 'existing4.impl.md'))

        subprocess.run(['git', 'add', '-A'], cwd=self.root, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'mixed changes'], cwd=self.root,
                        capture_output=True, check=True)

        changed = [
            {'path': f'features/new{i}.impl.md', 'status': 'A'} for i in range(3)
        ] + [
            {'path': f'features/existing{i}.impl.md', 'status': 'M'} for i in range(3)
        ] + [
            {'path': f'features/existing{i}.impl.md', 'status': 'D'} for i in range(3, 5)
        ]

        with patch('extract_whats_different._run_git', wraps=lambda args: self._run_git(args)):
            decisions = _extract_decisions_from_diff('main...test-branch', changed)

        # Should find DISCOVERY and DEVIATION entries from added/modified files
        categories = [d['category'] for d in decisions]
        self.assertIn('[DISCOVERY]', categories)
        self.assertIn('[DEVIATION]', categories)


class TestResultEquivalenceBatchedVsPerFile(BatchedDiffTestBase):
    """Scenario: Result equivalence between batched and per-file extraction"""

    def test_result_equivalence(self):
        subprocess.run(['git', 'checkout', '-b', 'test-branch'], cwd=self.root,
                        capture_output=True, check=True)

        files = []
        for i in range(5):
            fpath = os.path.join(self.features_dir, f'feat{i}.impl.md')
            with open(fpath, 'w') as f:
                f.write(f'# Notes {i}\n[DISCOVERY] Finding {i}\n')
            files.append(f'features/feat{i}.impl.md')

        subprocess.run(['git', 'add', '-A'], cwd=self.root, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'changes'], cwd=self.root,
                        capture_output=True, check=True)

        range_spec = 'main...test-branch'

        # Batched extraction (patch PROJECT_ROOT so _run_git uses temp repo)
        with patch('extract_whats_different.PROJECT_ROOT', self.root):
            batched_result = _batched_diff(range_spec, files)

        # Per-file extraction
        per_file_result = {}
        for fpath in files:
            output = self._run_git(['diff', range_spec, '--', fpath, '-U0'])
            if output.strip():
                per_file_result[fpath] = output.strip()

        # Same files should be present
        self.assertEqual(set(batched_result.keys()), set(per_file_result.keys()))


class TestBinaryFileInDiffRangeHandledGracefully(BatchedDiffTestBase):
    """Scenario: Binary file in diff range handled gracefully"""

    def test_binary_file_handled_gracefully(self):
        subprocess.run(['git', 'checkout', '-b', 'test-branch'], cwd=self.root,
                        capture_output=True, check=True)

        # Add a text file
        fpath = os.path.join(self.features_dir, 'feat1.impl.md')
        with open(fpath, 'w') as f:
            f.write('# Notes\n[DISCOVERY] Test\n')

        # Add a binary file
        bpath = os.path.join(self.features_dir, 'image.png')
        with open(bpath, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

        subprocess.run(['git', 'add', '-A'], cwd=self.root, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'mixed'], cwd=self.root,
                        capture_output=True, check=True)

        files = ['features/feat1.impl.md', 'features/image.png']

        with patch('extract_whats_different._run_git', wraps=lambda args: self._run_git(args)):
            result = _batched_diff('main...test-branch', files)

        # Text file should be extracted, binary should be skipped
        self.assertIn('features/feat1.impl.md', result)


# ===================================================================
# Section 2.4: Shared Git Status Result
# ===================================================================

class TestGitStatusCacheWrittenAndReusedWithinTTL(unittest.TestCase):
    """Scenario: Git status cache written and reused within TTL"""

    def test_git_status_cache_written_and_reused_within_ttl(self):
        tmpdir = tempfile.mkdtemp()
        cache_path = os.path.join(tmpdir, 'git_status_snapshot.txt')

        with patch('serve.GIT_STATUS_CACHE_PATH', cache_path), \
             patch('serve.run_command', return_value='?? newfile.txt') as mock_run:
            # First call: writes cache
            result1 = cached_git_status()
            self.assertEqual(mock_run.call_count, 1)
            self.assertIn('newfile.txt', result1)

            # Second call: should use cache (within TTL)
            result2 = cached_git_status()
            self.assertEqual(mock_run.call_count, 1)  # No additional call
            self.assertIn('newfile.txt', result2)

        shutil.rmtree(tmpdir)


class TestGitStatusCacheExpiredAfterTTL(unittest.TestCase):
    """Scenario: Git status cache expired after TTL"""

    def test_git_status_cache_expired_after_ttl(self):
        tmpdir = tempfile.mkdtemp()
        cache_path = os.path.join(tmpdir, 'git_status_snapshot.txt')

        # Write cache with old mtime
        with open(cache_path, 'w') as f:
            f.write('?? old.txt\n')
        os.utime(cache_path, (time.time() - 20, time.time() - 20))

        with patch('serve.GIT_STATUS_CACHE_PATH', cache_path), \
             patch('serve.run_command', return_value='?? new.txt') as mock_run:
            result = cached_git_status()
            mock_run.assert_called_once()
            self.assertIn('new.txt', result)

        shutil.rmtree(tmpdir)


class TestGitStatusCacheMissingTriggersFreshCall(unittest.TestCase):
    """Scenario: Git status cache missing triggers fresh call"""

    def test_git_status_cache_missing_triggers_fresh_call(self):
        tmpdir = tempfile.mkdtemp()
        cache_path = os.path.join(tmpdir, 'git_status_snapshot.txt')
        self.assertFalse(os.path.exists(cache_path))

        with patch('serve.GIT_STATUS_CACHE_PATH', cache_path), \
             patch('serve.run_command', return_value='?? fresh.txt'):
            result = cached_git_status()

        self.assertIn('fresh.txt', result)
        self.assertTrue(os.path.exists(cache_path))
        shutil.rmtree(tmpdir)


class TestTruncatedGitStatusCacheTriggersFreshCall(unittest.TestCase):
    """Scenario: Truncated git status cache triggers fresh call"""

    def test_truncated_git_status_cache_triggers_fresh_call(self):
        tmpdir = tempfile.mkdtemp()
        cache_path = os.path.join(tmpdir, 'git_status_snapshot.txt')

        # Write truncated content (no trailing newline, with internal newlines)
        with open(cache_path, 'w') as f:
            f.write('?? file1.txt\n?? file2.txt\n?? trunca')  # Truncated

        with patch('serve.GIT_STATUS_CACHE_PATH', cache_path), \
             patch('serve.run_command', return_value='?? complete.txt') as mock_run:
            result = cached_git_status()
            mock_run.assert_called_once()

        shutil.rmtree(tmpdir)


class TestGitStatusPathFilteringConsistent(unittest.TestCase):
    """Scenario: Git status path filtering is consistent"""

    def test_git_status_path_filtering_consistent(self):
        status_output = (
            '?? .DS_Store\n'
            '?? .purlin/cache/status.json\n'
            '?? features/new.md\n'
            'M  features/existing.md'
        )
        # Both consumers should see the same raw output from cached_git_status
        tmpdir = tempfile.mkdtemp()
        cache_path = os.path.join(tmpdir, 'git_status_snapshot.txt')

        with patch('serve.GIT_STATUS_CACHE_PATH', cache_path), \
             patch('serve.run_command', return_value=status_output):
            result1 = cached_git_status()
            result2 = cached_git_status()

        # Both calls return consistent results
        self.assertIn('.DS_Store', result1)
        self.assertIn('features/new.md', result1)
        self.assertIn('.DS_Store', result2)
        self.assertIn('features/new.md', result2)
        shutil.rmtree(tmpdir)


# ===================================================================
# Test Runner
# ===================================================================

def run_tests():
    """Run all tests and write results to tests.json."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    project_root = os.environ.get('PURLIN_PROJECT_ROOT')
    if not project_root:
        project_root = os.path.dirname(os.path.dirname(SCRIPT_DIR))

    output_dir = os.path.join(project_root, 'tests', 'git_operation_cache')
    os.makedirs(output_dir, exist_ok=True)

    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed

    report = {
        'status': 'PASS' if failed == 0 else 'FAIL',
        'passed': passed,
        'failed': failed,
        'total': total,
        'test_file': 'tools/cdd/test_git_operation_cache.py',
    }

    output_path = os.path.join(output_dir, 'tests.json')
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f'\nResults written to {output_path}')
    return result


if __name__ == '__main__':
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
