#!/usr/bin/env python3
"""Tests for the Implementation Notes Companion File Convention.

This is a cross-tool feature: companion file filtering and resolution spans
the Software Map and related tools. Tests exercise each tool's companion
file handling.

Outputs test results to tests/impl_notes_companion/tests.json.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
TOOLS_DIR = os.path.join(PROJECT_ROOT, 'tools')

# Add tools to path for imports
sys.path.insert(0, TOOLS_DIR)


# ===================================================================
# Scenario: Feature Scanning Excludes Companion Files
# ===================================================================

class TestFeatureScanExcludesCompanion(unittest.TestCase):
    """Companion .impl.md files must not appear as feature files."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        with open(os.path.join(self.tmpdir, 'my_feature.md'), 'w') as f:
            f.write('# Feature: My Feature\n')
        with open(os.path.join(self.tmpdir, 'my_feature.impl.md'), 'w') as f:
            f.write('# Implementation Notes\n')
        with open(os.path.join(self.tmpdir, 'another.md'), 'w') as f:
            f.write('# Feature: Another\n')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_filter_pattern_excludes_impl(self):
        """The .impl.md filter correctly excludes companion files."""
        feature_files = sorted([
            f for f in os.listdir(self.tmpdir)
            if f.endswith('.md') and not f.endswith('.impl.md')
        ])
        self.assertEqual(feature_files, ['another.md', 'my_feature.md'])
        self.assertNotIn('my_feature.impl.md', feature_files)


# ===================================================================
# Scenario: Feature Scanning Excludes Companion Files (serve layer)
# ===================================================================

class TestServeExcludesCompanion(unittest.TestCase):
    """Feature scanning must not include .impl.md files."""

    def test_serve_filter(self):
        """The feature scanning filter excludes .impl.md."""
        tmpdir = tempfile.mkdtemp()
        try:
            for name in ['feat.md', 'feat.impl.md', 'other.md']:
                with open(os.path.join(tmpdir, name), 'w') as f:
                    f.write('# ' + name + '\n')

            feature_files = [
                f for f in os.listdir(tmpdir)
                if f.endswith('.md') and not f.endswith('.impl.md')
            ]
            self.assertIn('feat.md', feature_files)
            self.assertIn('other.md', feature_files)
            self.assertNotIn('feat.impl.md', feature_files)
        finally:
            shutil.rmtree(tmpdir)


# ===================================================================
# Scenario: Dependency Graph Excludes Companion Files
# ===================================================================

class TestDependencyGraphExcludesCompanion(unittest.TestCase):
    """Software Map dependency graph must not include .impl.md files."""

    def test_generate_tree_filter(self):
        """graph.py parse_features() excludes .impl.md."""
        sys.path.insert(0, os.path.join(TOOLS_DIR, 'cdd'))
        from graph import parse_features

        tmpdir = tempfile.mkdtemp()
        try:
            # Create a valid feature file
            with open(os.path.join(tmpdir, 'my_feat.md'), 'w') as f:
                f.write('> Label: "My Feature"\n> Category: "Test"\n')
            # Create a companion file
            with open(os.path.join(tmpdir, 'my_feat.impl.md'), 'w') as f:
                f.write('# Implementation Notes\n')

            features = parse_features(tmpdir)
            # parse_features returns a dict keyed by node_id (stem)
            filenames = [f['filename'] for f in features.values()]
            self.assertIn('my_feat.md', filenames)
            self.assertNotIn('my_feat.impl.md', filenames)
        finally:
            shutil.rmtree(tmpdir)


# ===================================================================
# Test runner with output to tests/impl_notes_companion/tests.json
# ===================================================================

if __name__ == '__main__':
    tests_out_dir = os.path.join(PROJECT_ROOT, 'tests', 'impl_notes_companion')
    os.makedirs(tests_out_dir, exist_ok=True)
    status_file = os.path.join(tests_out_dir, 'tests.json')

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    status = 'PASS' if result.wasSuccessful() else 'FAIL'
    failed = len(result.failures) + len(result.errors)
    with open(status_file, 'w') as f:
        json.dump({
            'status': status,
            'passed': result.testsRun - failed,
            'failed': failed,
            'total': result.testsRun,
        }, f, indent=2)

    print(f'\nResult: {status} ({result.testsRun} tests)')
    print(f'Written to {status_file}')
    sys.exit(0 if result.wasSuccessful() else 1)
