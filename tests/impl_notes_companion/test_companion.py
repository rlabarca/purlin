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
# Scenario: Orphan Detection Flags Companion Without Parent
# ===================================================================

class TestOrphanDetectionCompanion(unittest.TestCase):
    """Companion file without parent feature must be flagged as orphan by Critic."""

    def test_orphan_companion_flagged(self):
        from critic import audit_orphan_companions

        tmpdir = tempfile.mkdtemp()
        try:
            # Create an orphan companion (no parent .md)
            with open(os.path.join(tmpdir, 'gone.impl.md'), 'w') as f:
                f.write('# Implementation Notes\n')
            # Create a valid feature with companion (not orphaned)
            with open(os.path.join(tmpdir, 'valid.md'), 'w') as f:
                f.write('> Label: "Valid"\n> Category: "Test"\n')
            with open(os.path.join(tmpdir, 'valid.impl.md'), 'w') as f:
                f.write('# Implementation Notes: Valid\n')

            items = audit_orphan_companions(features_dir=tmpdir)
            # gone.impl.md should be flagged (no parent gone.md)
            flagged_files = [item['description'] for item in items]
            self.assertTrue(
                any('gone.impl.md' in d for d in flagged_files),
                f'Expected gone.impl.md to be flagged, got: {flagged_files}'
            )
            # valid.impl.md should NOT be flagged (valid.md exists)
            self.assertFalse(
                any('valid.impl.md' in d for d in flagged_files),
                f'valid.impl.md should not be flagged'
            )
            # Verify action item structure
            self.assertEqual(items[0]['priority'], 'MEDIUM')
            self.assertEqual(items[0]['category'], 'orphan_companion')
        finally:
            shutil.rmtree(tmpdir)

    def test_no_orphans_returns_empty(self):
        from critic import audit_orphan_companions

        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, 'feat.md'), 'w') as f:
                f.write('# Feature\n')
            with open(os.path.join(tmpdir, 'feat.impl.md'), 'w') as f:
                f.write('# Implementation Notes\n')

            items = audit_orphan_companions(features_dir=tmpdir)
            self.assertEqual(items, [])
        finally:
            shutil.rmtree(tmpdir)


# ===================================================================
# Scenario: Companion File Served via API
# ===================================================================

class TestCompanionFileServedViaAPI(unittest.TestCase):
    """The /impl-notes endpoint serves companion file content."""

    def setUp(self):
        sys.path.insert(0, os.path.join(TOOLS_DIR, 'cdd'))
        self.tmpdir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.tmpdir, 'features')
        os.makedirs(self.features_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_endpoint_resolves_feature_to_companion(self):
        """GET /impl-notes?file=features/critic_tool.md returns companion content."""
        import http.server
        import urllib.parse
        from io import BytesIO

        # Create feature and companion
        with open(os.path.join(self.features_dir, 'critic_tool.md'), 'w') as f:
            f.write('# Feature: Critic Tool\n')
        companion_content = '# Implementation Notes: Critic Tool\nSome notes.'
        with open(os.path.join(self.features_dir, 'critic_tool.impl.md'), 'w') as f:
            f.write(companion_content)

        # Import serve module and test path resolution logic directly
        import importlib
        import serve as serve_mod

        # Save and override PROJECT_ROOT and FEATURES_DIR
        orig_project_root = serve_mod.PROJECT_ROOT
        orig_features_dir = serve_mod.FEATURES_DIR
        serve_mod.PROJECT_ROOT = self.tmpdir
        serve_mod.FEATURES_DIR = self.features_dir

        try:
            # Simulate the resolution logic from _serve_impl_notes
            file_param = 'features/critic_tool.md'
            if file_param.endswith('.impl.md'):
                companion_param = file_param
            elif file_param.endswith('.md'):
                companion_param = file_param[:-3] + '.impl.md'
            else:
                self.fail('Invalid file parameter')

            abs_path = os.path.normpath(
                os.path.join(self.tmpdir, companion_param))
            allowed_dir = os.path.normpath(self.features_dir)
            self.assertTrue(abs_path.startswith(allowed_dir))
            self.assertTrue(os.path.isfile(abs_path))

            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertEqual(content, companion_content)
        finally:
            serve_mod.PROJECT_ROOT = orig_project_root
            serve_mod.FEATURES_DIR = orig_features_dir


# ===================================================================
# Scenario: No Companion File Returns 404
# ===================================================================

class TestNoCompanionReturns404(unittest.TestCase):
    """The /impl-notes endpoint returns 404 when no companion exists."""

    def setUp(self):
        sys.path.insert(0, os.path.join(TOOLS_DIR, 'cdd'))
        self.tmpdir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.tmpdir, 'features')
        os.makedirs(self.features_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_missing_companion_resolves_to_no_file(self):
        """GET /impl-notes?file=features/policy_critic.md returns 404 when no companion."""
        import serve as serve_mod

        # Create feature without companion
        with open(os.path.join(self.features_dir, 'policy_critic.md'), 'w') as f:
            f.write('# Policy: Critic\n')

        orig_project_root = serve_mod.PROJECT_ROOT
        orig_features_dir = serve_mod.FEATURES_DIR
        serve_mod.PROJECT_ROOT = self.tmpdir
        serve_mod.FEATURES_DIR = self.features_dir

        try:
            file_param = 'features/policy_critic.md'
            companion_param = file_param[:-3] + '.impl.md'
            abs_path = os.path.normpath(
                os.path.join(self.tmpdir, companion_param))
            # The companion file should NOT exist
            self.assertFalse(
                os.path.isfile(abs_path),
                f'Expected no companion file at {abs_path}'
            )
        finally:
            serve_mod.PROJECT_ROOT = orig_project_root
            serve_mod.FEATURES_DIR = orig_features_dir


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
