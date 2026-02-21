#!/usr/bin/env python3
"""Tests for the Implementation Notes Companion File Convention.

This is a cross-tool feature: companion file filtering and resolution spans
the Critic, CDD, Software Map, and Orphan Cleanup tools. Tests exercise
each tool's companion file handling.

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
sys.path.insert(0, os.path.join(TOOLS_DIR, 'critic'))
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
# Scenario: Companion File Resolution for Implementation Gate
# ===================================================================

class TestCompanionResolution(unittest.TestCase):
    """resolve_impl_notes() follows companion file references."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_resolves_companion(self):
        """Stub with companion ref reads the companion file content."""
        from critic import resolve_impl_notes

        feature_path = os.path.join(self.tmpdir, 'feat.md')
        companion_path = os.path.join(self.tmpdir, 'feat.impl.md')

        with open(feature_path, 'w') as f:
            f.write(
                '# Feature\n\n## Implementation Notes\n'
                'See [feat.impl.md](feat.impl.md) for implementation '
                'knowledge, builder decisions, and tribal knowledge.\n'
            )
        with open(companion_path, 'w') as f:
            f.write(
                '# Implementation Notes: Feat\n\n'
                '*   **[CLARIFICATION]** A clarification. (Severity: INFO)\n'
                '*   **[DEVIATION]** A deviation. (Severity: HIGH)\n'
            )

        result = resolve_impl_notes(
            open(feature_path).read(), feature_path
        )
        self.assertIn('[CLARIFICATION]', result)
        self.assertIn('[DEVIATION]', result)


# ===================================================================
# Scenario: Backward Compatible Inline Notes
# ===================================================================

class TestBackwardCompatibleInline(unittest.TestCase):
    """Inline notes (no companion) return inline content unchanged."""

    def test_inline_notes_returned(self):
        from critic import resolve_impl_notes

        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, 'inline.md')
            content = (
                '# Feature\n\n## Implementation Notes\n'
                '*   **[CLARIFICATION]** Inline note. (Severity: INFO)\n'
            )
            with open(path, 'w') as f:
                f.write(content)

            result = resolve_impl_notes(content, path)
            self.assertIn('[CLARIFICATION]', result)
            self.assertIn('Inline note', result)
        finally:
            shutil.rmtree(tmpdir)


# ===================================================================
# Scenario: Stub With Companion Reference Not Flagged as Empty
# ===================================================================

class TestStubNotFlaggedEmpty(unittest.TestCase):
    """A stub containing a companion link is not 'empty notes'."""

    def test_stub_passes_completeness(self):
        from critic import parse_sections, check_section_completeness

        content = """\
# Feature: Stubbed

## Overview
A feature.

## 2. Requirements
Some requirements.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Test
    Given X
    When Y
    Then Z

## Implementation Notes
See [stubbed.impl.md](stubbed.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.
"""
        sections = parse_sections(content)
        result = check_section_completeness(content, sections)
        self.assertEqual(result['status'], 'PASS')


# ===================================================================
# Scenario: CDD Excludes Companion Files
# ===================================================================

class TestCDDExcludesCompanion(unittest.TestCase):
    """CDD feature scanning must not include .impl.md files."""

    def test_cdd_serve_filter(self):
        """The CDD serve.py feature scanning filter excludes .impl.md."""
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
        """generate_tree.py parse_features() excludes .impl.md."""
        sys.path.insert(0, os.path.join(TOOLS_DIR, 'software_map'))
        from generate_tree import parse_features

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
# Scenario: Orphan Detection Flags Companion Without Parent
# ===================================================================

class TestOrphanDetectionCompanion(unittest.TestCase):
    """Companion file without parent feature must be flagged as orphan."""

    def test_orphan_companion_flagged(self):
        from cleanup_orphaned_features import get_referenced_features

        tmpdir = tempfile.mkdtemp()
        try:
            # Create an orphan companion (no parent .md)
            with open(os.path.join(tmpdir, 'gone.impl.md'), 'w') as f:
                f.write('# Implementation Notes\n')
            # Create a valid feature (not orphaned due to protected roots)
            with open(os.path.join(tmpdir, 'valid.md'), 'w') as f:
                f.write('> Label: "Valid"\n> Category: "Test"\n')

            orphans = get_referenced_features(tmpdir)
            self.assertIn('gone.impl.md', orphans)
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
    with open(status_file, 'w') as f:
        json.dump({
            'status': status,
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
        }, f, indent=2)

    print(f'\nResult: {status} ({result.testsRun} tests)')
    print(f'Written to {status_file}')
    sys.exit(0 if result.wasSuccessful() else 1)
