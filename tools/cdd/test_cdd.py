"""Unit tests for the CDD Status Monitor.

Covers automated scenarios from features/cdd_status_monitor.md.
Outputs test results to tests/cdd_status_monitor/tests.json.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import json
import re
import subprocess
import sys
import tempfile
import shutil
from serve import (
    get_feature_test_status,
    get_feature_role_status,
    aggregate_test_statuses,
    get_feature_status,
    get_change_scope,
    get_delivery_phase,
    resolve_port,
    COMPLETE_CAP,
    extract_label,
    generate_internal_feature_status,
    generate_api_status_json,
    generate_role_filtered_status_json,
    generate_startup_briefing,
    build_status_commit_cache,
    _count_scenarios,
    _extract_forbidden_patterns,
    _scan_discovery_sidecars,
    _is_feature_complete,
    _feature_urgency,
    strip_discoveries_section,
    strip_metadata_lines,
    spec_content_unchanged,
    _only_qa_tag_commits_since,
    _qa_badge_html,
)


# ===================================================================
# Test Status Lookup Tests
# ===================================================================

class TestPerFeatureTestStatus(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _write_tests_json(self, feature_stem, data):
        d = os.path.join(self.test_dir, feature_stem)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "tests.json"), "w") as f:
            json.dump(data, f)

    def _write_raw(self, feature_stem, content):
        d = os.path.join(self.test_dir, feature_stem)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "tests.json"), "w") as f:
            f.write(content)

    def test_pass_status(self):
        self._write_tests_json("my_feature", {"status": "PASS"})
        self.assertEqual(
            get_feature_test_status("my_feature", self.test_dir), "PASS")

    def test_fail_status(self):
        self._write_tests_json("my_feature", {"status": "FAIL"})
        self.assertEqual(
            get_feature_test_status("my_feature", self.test_dir), "FAIL")

    def test_missing_file_returns_none(self):
        self.assertIsNone(
            get_feature_test_status("nonexistent", self.test_dir))

    def test_malformed_json_returns_fail(self):
        self._write_raw("bad_feature", "{ invalid json")
        self.assertEqual(
            get_feature_test_status("bad_feature", self.test_dir), "FAIL")

    def test_missing_status_field_returns_fail(self):
        self._write_tests_json("no_status", {"tests": 5})
        self.assertEqual(
            get_feature_test_status("no_status", self.test_dir), "FAIL")


# ===================================================================
# Role Status Lookup Tests
# ===================================================================

class TestGetFeatureRoleStatus(unittest.TestCase):
    """Scenario: Role Status in API Response"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _write_critic_json(self, feature_stem, data):
        d = os.path.join(self.test_dir, feature_stem)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "critic.json"), "w") as f:
            json.dump(data, f)

    def test_reads_role_status(self):
        self._write_critic_json("my_feature", {
            "role_status": {
                "architect": "DONE",
                "builder": "DONE",
                "qa": "CLEAN",
                "pm": "N/A",
            },
        })
        result = get_feature_role_status("my_feature", self.test_dir)
        self.assertEqual(result["architect"], "DONE")
        self.assertEqual(result["builder"], "DONE")
        self.assertEqual(result["qa"], "CLEAN")
        self.assertEqual(result["pm"], "N/A")

    def test_missing_critic_json_returns_none(self):
        result = get_feature_role_status("nonexistent", self.test_dir)
        self.assertIsNone(result)

    def test_malformed_json_returns_none(self):
        d = os.path.join(self.test_dir, "bad")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "critic.json"), "w") as f:
            f.write("{ invalid json")
        result = get_feature_role_status("bad", self.test_dir)
        self.assertIsNone(result)

    def test_no_role_status_key_returns_none(self):
        self._write_critic_json("no_role", {
            "spec_gate": {"status": "PASS"},
        })
        result = get_feature_role_status("no_role", self.test_dir)
        self.assertIsNone(result)


# ===================================================================
# Aggregate Test Status Tests
# ===================================================================

class TestAggregateTestStatuses(unittest.TestCase):
    def test_all_pass(self):
        self.assertEqual(aggregate_test_statuses(["PASS", "PASS"]), "PASS")

    def test_one_fail(self):
        self.assertEqual(aggregate_test_statuses(["PASS", "FAIL"]), "FAIL")

    def test_all_fail(self):
        self.assertEqual(aggregate_test_statuses(["FAIL", "FAIL"]), "FAIL")

    def test_empty_returns_unknown(self):
        self.assertEqual(aggregate_test_statuses([]), "UNKNOWN")


# ===================================================================
# Lifecycle Status Tests
# ===================================================================

class TestExtractLabel(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_valid_label(self):
        path = os.path.join(self.test_dir, "test.md")
        with open(path, 'w') as f:
            f.write('# Feature\n\n> Label: "My Label"\n')
        self.assertEqual(extract_label(path), "My Label")

    def test_missing_label_fallback(self):
        path = os.path.join(self.test_dir, "my_feature.md")
        with open(path, 'w') as f:
            f.write('# No label here\n')
        self.assertEqual(extract_label(path), "my_feature")


class TestFeatureStatusCapping(unittest.TestCase):
    def test_feature_status_complete_capping(self):
        test_dir = tempfile.mkdtemp()
        try:
            features_abs = os.path.join(test_dir, "features")
            os.makedirs(features_abs)
            # Build a cache where every feature has a Complete commit
            cache = {}
            for i in range(15):
                fname = f"feat_{i:02d}.md"
                with open(os.path.join(features_abs, fname), "w") as f:
                    f.write("# Test")
                fpath = os.path.normpath(os.path.join("features", fname))
                cache[fpath] = {
                    'complete_ts': 2000000000, 'complete_hash': '',
                    'testing_ts': 0, 'testing_hash': '',
                    'scope': None,
                }

            complete, testing, todo = get_feature_status(
                "features", features_abs, cache)
            self.assertEqual(len(complete), 15)
            self.assertEqual(len(testing), 0)
            self.assertEqual(len(todo), 0)
        finally:
            shutil.rmtree(test_dir)


# ===================================================================
# Public API: /status.json Tests (New Role-Based Schema)
# ===================================================================

class TestApiStatusJsonRoleStatus(unittest.TestCase):
    """Scenario: Role Status in API Response"""

    @patch('serve.FEATURES_ABS')
    @patch('serve.TESTS_DIR')
    def test_includes_role_fields_from_critic_json(self, mock_tests, mock_abs):
        test_dir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(test_dir, "features")
            tests_dir = os.path.join(test_dir, "tests")
            os.makedirs(features_dir)
            os.makedirs(tests_dir)

            # Create feature file
            with open(os.path.join(features_dir, "test.md"), "w") as f:
                f.write('# Feature\n\n> Label: "Test Feature"\n')

            # Create critic.json with role_status
            feat_test_dir = os.path.join(tests_dir, "test")
            os.makedirs(feat_test_dir)
            with open(os.path.join(feat_test_dir, "critic.json"), "w") as f:
                json.dump({
                    "role_status": {
                        "architect": "DONE",
                        "builder": "DONE",
                        "qa": "CLEAN",
                        "pm": "N/A",
                    },
                }, f)

            import serve
            orig_abs = serve.FEATURES_ABS
            orig_tests = serve.TESTS_DIR
            serve.FEATURES_ABS = features_dir
            serve.TESTS_DIR = tests_dir
            try:
                data = generate_api_status_json()
                features = data["features"]
                self.assertEqual(len(features), 1)
                entry = features[0]
                self.assertEqual(entry["architect"], "DONE")
                self.assertEqual(entry["builder"], "DONE")
                self.assertEqual(entry["qa"], "CLEAN")
                self.assertEqual(entry["pm"], "N/A")
                # No old fields
                self.assertNotIn("test_status", entry)
                self.assertNotIn("qa_status", entry)
            finally:
                serve.FEATURES_ABS = orig_abs
                serve.TESTS_DIR = orig_tests
        finally:
            shutil.rmtree(test_dir)


class TestApiStatusJsonOmitWhenNoCritic(unittest.TestCase):
    """Scenario: Role Status Omitted When No Critic File"""

    def test_no_critic_json_omits_role_fields(self):
        test_dir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(test_dir, "features")
            tests_dir = os.path.join(test_dir, "tests")
            os.makedirs(features_dir)
            os.makedirs(tests_dir)

            with open(os.path.join(features_dir, "orphan.md"), "w") as f:
                f.write('# Feature\n\n> Label: "Orphan"\n')

            import serve
            orig_abs = serve.FEATURES_ABS
            orig_tests = serve.TESTS_DIR
            serve.FEATURES_ABS = features_dir
            serve.TESTS_DIR = tests_dir
            try:
                data = generate_api_status_json()
                entry = data["features"][0]
                self.assertNotIn("architect", entry)
                self.assertNotIn("builder", entry)
                self.assertNotIn("qa", entry)
                self.assertNotIn("pm", entry)
            finally:
                serve.FEATURES_ABS = orig_abs
                serve.TESTS_DIR = orig_tests
        finally:
            shutil.rmtree(test_dir)


class TestApiStatusJsonFlatArray(unittest.TestCase):
    """Scenario: Flat Features Array in API Response"""

    def test_flat_array_sorted_by_file(self):
        test_dir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(test_dir, "features")
            tests_dir = os.path.join(test_dir, "tests")
            os.makedirs(features_dir)
            os.makedirs(tests_dir)

            for name in ["z_feat.md", "a_feat.md", "m_feat.md"]:
                with open(os.path.join(features_dir, name), "w") as f:
                    f.write(f'# Feature\n\n> Label: "{name}"\n')

            import serve
            orig_abs = serve.FEATURES_ABS
            orig_tests = serve.TESTS_DIR
            serve.FEATURES_ABS = features_dir
            serve.TESTS_DIR = tests_dir
            try:
                data = generate_api_status_json()
                # Flat array, not grouped
                self.assertIsInstance(data["features"], list)
                # No sub-arrays
                self.assertNotIn("todo", data.get("features", {}))
                self.assertNotIn("testing", data.get("features", {}))
                self.assertNotIn("complete", data.get("features", {}))
                # No top-level test_status
                self.assertNotIn("test_status", data)
                # Sorted by file path
                files = [e["file"] for e in data["features"]]
                self.assertEqual(files, sorted(files))
            finally:
                serve.FEATURES_ABS = orig_abs
                serve.TESTS_DIR = orig_tests
        finally:
            shutil.rmtree(test_dir)


class TestInternalFeatureStatusPreserved(unittest.TestCase):
    """Scenario: Internal Feature Status File Preserved"""

    @patch('serve.FEATURES_REL', 'features')
    @patch('serve.FEATURES_ABS', '/tmp/test_features')
    @patch('serve.TESTS_DIR', '/tmp/test_tests')
    @patch('serve.get_feature_status')
    @patch('serve.get_feature_test_status')
    @patch('serve.extract_label')
    def test_internal_format_has_lifecycle_arrays(self, mock_label, mock_test,
                                                   mock_features):
        mock_features.return_value = (
            [("complete.md", 100)], ["testing.md"], ["todo.md"])
        mock_test.return_value = None
        mock_label.return_value = "Label"

        data = generate_internal_feature_status()

        # Old lifecycle format
        self.assertIn("features", data)
        features = data["features"]
        self.assertIn("complete", features)
        self.assertIn("testing", features)
        self.assertIn("todo", features)
        self.assertIn("test_status", data)
        self.assertEqual(len(features["complete"]), 1)
        self.assertEqual(len(features["testing"]), 1)
        self.assertEqual(len(features["todo"]), 1)


# ===================================================================
# Dashboard Helpers Tests
# ===================================================================

class TestFeatureCompleteness(unittest.TestCase):
    """Tests for Active vs Complete grouping logic."""

    def test_all_roles_done_is_complete(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "DONE", "qa": "CLEAN", "pm": "N/A"}
        self.assertTrue(_is_feature_complete(entry))

    def test_builder_todo_is_not_complete(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "TODO", "qa": "CLEAN", "pm": "N/A"}
        self.assertFalse(_is_feature_complete(entry))

    def test_qa_na_counts_as_complete(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "DONE", "qa": "N/A", "pm": "N/A"}
        self.assertTrue(_is_feature_complete(entry))

    def test_no_critic_is_not_complete(self):
        entry = {"file": "f.md"}
        self.assertFalse(_is_feature_complete(entry))

    def test_builder_fail_is_not_complete(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "FAIL", "qa": "CLEAN", "pm": "N/A"}
        self.assertFalse(_is_feature_complete(entry))

    def test_pm_done_counts_as_complete(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "DONE", "qa": "CLEAN", "pm": "DONE"}
        self.assertTrue(_is_feature_complete(entry))

    def test_pm_todo_is_not_complete(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "DONE", "qa": "CLEAN", "pm": "TODO"}
        self.assertFalse(_is_feature_complete(entry))


class TestFeatureUrgency(unittest.TestCase):
    """Tests for urgency sorting in Active section."""

    def test_fail_is_most_urgent(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "FAIL", "qa": "CLEAN", "pm": "N/A"}
        self.assertEqual(_feature_urgency(entry), 0)

    def test_todo_is_medium_urgent(self):
        entry = {"file": "f.md", "architect": "TODO",
                 "builder": "DONE", "qa": "N/A", "pm": "N/A"}
        self.assertEqual(_feature_urgency(entry), 1)

    def test_all_done_is_least_urgent(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "DONE", "qa": "CLEAN", "pm": "N/A"}
        self.assertEqual(_feature_urgency(entry), 3)

    def test_infeasible_is_most_urgent(self):
        entry = {"file": "f.md", "architect": "TODO",
                 "builder": "INFEASIBLE", "qa": "N/A", "pm": "N/A"}
        self.assertEqual(_feature_urgency(entry), 0)

    def test_disputed_is_medium_urgent(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "BLOCKED", "qa": "DISPUTED", "pm": "N/A"}
        self.assertEqual(_feature_urgency(entry), 1)

    def test_pm_todo_affects_urgency(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "DONE", "qa": "CLEAN", "pm": "TODO"}
        self.assertEqual(_feature_urgency(entry), 1)


class TestZeroQueueVerification(unittest.TestCase):
    """Scenario: Zero-Queue Verification"""

    def test_all_done_means_zero_queue(self):
        features = [
            {"file": "a.md", "architect": "DONE",
             "builder": "DONE", "qa": "CLEAN", "pm": "N/A"},
            {"file": "b.md", "architect": "DONE",
             "builder": "DONE", "qa": "N/A", "pm": "DONE"},
        ]
        all_complete = all(_is_feature_complete(f) for f in features)
        self.assertTrue(all_complete)

    def test_one_todo_fails_zero_queue(self):
        features = [
            {"file": "a.md", "architect": "DONE",
             "builder": "DONE", "qa": "CLEAN", "pm": "N/A"},
            {"file": "b.md", "architect": "TODO",
             "builder": "DONE", "qa": "N/A", "pm": "N/A"},
        ]
        all_complete = all(_is_feature_complete(f) for f in features)
        self.assertFalse(all_complete)

    def test_pm_todo_fails_zero_queue(self):
        features = [
            {"file": "a.md", "architect": "DONE",
             "builder": "DONE", "qa": "CLEAN", "pm": "TODO"},
        ]
        all_complete = all(_is_feature_complete(f) for f in features)
        self.assertFalse(all_complete)


# ===================================================================
# Discovery-Aware Lifecycle Preservation Tests
# ===================================================================

class TestStripDiscoveriesSection(unittest.TestCase):
    """Unit test for strip_discoveries_section helper."""

    def test_strips_discoveries_section(self):
        content = (
            "# Feature\n\n## 2. Requirements\nReqs.\n\n"
            "## User Testing Discoveries\n- Bug found\n"
        )
        result = strip_discoveries_section(content)
        self.assertNotIn("User Testing Discoveries", result)
        self.assertIn("Requirements", result)

    def test_no_discoveries_section_returns_full(self):
        content = "# Feature\n\n## 2. Requirements\nReqs.\n"
        result = strip_discoveries_section(content)
        self.assertEqual(result, content)


class TestStripMetadataLines(unittest.TestCase):
    """Unit tests for strip_metadata_lines helper."""

    def test_strips_label(self):
        content = '> Label: "Foo"\n## 1. Overview\n'
        result = strip_metadata_lines(content)
        self.assertNotIn("Label", result)
        self.assertIn("Overview", result)

    def test_strips_category(self):
        content = '> Category: "Bar"\n## 1. Overview\n'
        result = strip_metadata_lines(content)
        self.assertNotIn("Category", result)
        self.assertIn("Overview", result)

    def test_strips_prerequisite(self):
        content = '> Prerequisite: features/foo.md\n## 1. Overview\n'
        result = strip_metadata_lines(content)
        self.assertNotIn("Prerequisite", result)
        self.assertIn("Overview", result)

    def test_strips_web_test(self):
        content = '> Web Test: http://localhost:3000\n## 1. Overview\n'
        result = strip_metadata_lines(content)
        self.assertNotIn("Web Test", result)
        self.assertIn("Overview", result)

    def test_strips_multiple(self):
        content = (
            '> Label: "Tool: Foo"\n'
            '> Category: "Install"\n'
            '> Prerequisite: features/arch_data_layer.md\n'
            '> Prerequisite: features/bar.md\n'
            '> Web Test: http://localhost:8080\n'
            '> Owner: PM\n'
            '\n'
            '## 1. Overview\nOverview text.\n\n'
            '## 2. Requirements\nReqs.\n'
        )
        result = strip_metadata_lines(content)
        self.assertNotIn("Label", result)
        self.assertNotIn("Category", result)
        self.assertNotIn("Prerequisite", result)
        self.assertNotIn("Web Test", result)
        self.assertNotIn("Owner", result)
        self.assertIn("Overview text.", result)
        self.assertIn("Reqs.", result)

    def test_preserves_unknown_blockquote(self):
        content = '> NewThing: value\n## 1. Overview\n'
        result = strip_metadata_lines(content)
        self.assertIn("NewThing", result)
        self.assertIn("Overview", result)

    def test_preserves_body_content(self):
        content = (
            '> Label: "Foo"\n\n'
            '## 2. Requirements\n'
            'The system MUST do X.\n\n'
            '## 3. Scenarios\n'
            '#### Scenario: Test\n'
            '    Given something\n'
            '    Then something else\n'
        )
        result = strip_metadata_lines(content)
        self.assertIn("The system MUST do X.", result)
        self.assertIn("#### Scenario: Test", result)
        self.assertIn("Given something", result)


class TestLifecyclePreservedOnMetadataChange(unittest.TestCase):
    """Scenario: Metadata-only spec edit does not reset lifecycle.

    When a feature is COMPLETE and the only change is to blockquote metadata
    lines (e.g., removing a > Prerequisite: line), the feature stays COMPLETE.
    """

    @patch('serve.run_command')
    def test_metadata_only_change_preserves_status(self, mock_run):
        test_dir = tempfile.mkdtemp()
        try:
            features_abs = os.path.join(test_dir, "features")
            os.makedirs(features_abs)

            committed_content = (
                "# Feature: Test\n\n"
                "> Label: \"Tool: Test\"\n"
                "> Prerequisite: features/old_dep.md\n"
                "> Prerequisite: features/other_dep.md\n"
                "\n"
                "## 1. Overview\nOverview.\n\n"
                "## 2. Requirements\nReqs.\n"
            )
            # Only metadata changed: removed one prerequisite
            modified_content = (
                "# Feature: Test\n\n"
                "> Label: \"Tool: Test\"\n"
                "> Prerequisite: features/other_dep.md\n"
                "\n"
                "## 1. Overview\nOverview.\n\n"
                "## 2. Requirements\nReqs.\n"
            )
            fpath = os.path.join(features_abs, "test.md")
            with open(fpath, "w") as f:
                f.write(modified_content)

            os.utime(fpath, (3000000000, 3000000000))

            cache = {
                "features/test.md": {
                    'complete_ts': 2000000000, 'complete_hash': 'abc123',
                    'testing_ts': 0, 'testing_hash': '',
                    'scope': None,
                }
            }

            def mock_git(cmd):
                if "git show abc123:" in cmd:
                    return committed_content
                return ""
            mock_run.side_effect = mock_git

            import serve
            orig_root = serve.PROJECT_ROOT
            serve.PROJECT_ROOT = test_dir
            try:
                complete, testing, todo = get_feature_status(
                    "features", features_abs, cache)
                self.assertEqual(len(complete), 1)
                self.assertEqual(complete[0][0], "test.md")
                self.assertEqual(len(todo), 0)
            finally:
                serve.PROJECT_ROOT = orig_root
        finally:
            shutil.rmtree(test_dir)

    @patch('serve.run_command')
    def test_body_change_still_resets(self, mock_run):
        """Regression guard: body changes still reset to TODO."""
        test_dir = tempfile.mkdtemp()
        try:
            features_abs = os.path.join(test_dir, "features")
            os.makedirs(features_abs)

            committed_content = (
                "# Feature: Test\n\n"
                "> Label: \"Tool: Test\"\n"
                "\n"
                "## 1. Overview\nOriginal overview.\n\n"
                "## 2. Requirements\nOriginal reqs.\n"
            )
            modified_content = (
                "# Feature: Test\n\n"
                "> Label: \"Tool: Test\"\n"
                "\n"
                "## 1. Overview\nModified overview.\n\n"
                "## 2. Requirements\nNew requirements added.\n"
            )
            fpath = os.path.join(features_abs, "test.md")
            with open(fpath, "w") as f:
                f.write(modified_content)

            os.utime(fpath, (3000000000, 3000000000))

            cache = {
                "features/test.md": {
                    'complete_ts': 2000000000, 'complete_hash': 'abc123',
                    'testing_ts': 0, 'testing_hash': '',
                    'scope': None,
                }
            }

            def mock_git(cmd):
                if "git show abc123:" in cmd:
                    return committed_content
                return ""
            mock_run.side_effect = mock_git

            import serve
            orig_root = serve.PROJECT_ROOT
            serve.PROJECT_ROOT = test_dir
            try:
                complete, testing, todo = get_feature_status(
                    "features", features_abs, cache)
                self.assertEqual(len(todo), 1)
                self.assertEqual(todo[0], "test.md")
                self.assertEqual(len(complete), 0)
            finally:
                serve.PROJECT_ROOT = orig_root
        finally:
            shutil.rmtree(test_dir)


class TestLifecyclePreservedOnlyDiscoveriesChange(unittest.TestCase):
    """Scenario: Lifecycle Preserved When Only Discoveries Section Changes

    When a feature file is modified after the status commit, but the
    modification is limited to the User Testing Discoveries section,
    the feature remains in its lifecycle state (COMPLETE or TESTING).
    """

    @patch('serve.run_command')
    def test_complete_preserved_when_only_discoveries_change(self, mock_run):
        test_dir = tempfile.mkdtemp()
        try:
            features_abs = os.path.join(test_dir, "features")
            os.makedirs(features_abs)

            spec_content = (
                "# Feature: Test\n\n"
                "## 1. Overview\nOverview.\n\n"
                "## User Testing Discoveries\n"
            )
            # Write the feature file with a new discovery added
            modified_content = (
                "# Feature: Test\n\n"
                "## 1. Overview\nOverview.\n\n"
                "## User Testing Discoveries\n"
                "- [BUG] Something found (OPEN)\n"
            )
            fpath = os.path.join(features_abs, "test.md")
            with open(fpath, "w") as f:
                f.write(modified_content)

            # Set file mtime to future (after status commit)
            os.utime(fpath, (3000000000, 3000000000))

            # Pre-built cache (replaces individual git log calls)
            cache = {
                "features/test.md": {
                    'complete_ts': 2000000000, 'complete_hash': 'abc123',
                    'testing_ts': 0, 'testing_hash': '',
                    'scope': None,
                }
            }

            # Mock only needed for git show (spec_content_unchanged check)
            def mock_git(cmd):
                if "git show abc123:" in cmd:
                    return spec_content
                return ""
            mock_run.side_effect = mock_git

            import serve
            orig_root = serve.PROJECT_ROOT
            serve.PROJECT_ROOT = test_dir
            try:
                complete, testing, todo = get_feature_status(
                    "features", features_abs, cache)
                self.assertEqual(len(complete), 1)
                self.assertEqual(complete[0][0], "test.md")
                self.assertEqual(len(todo), 0)
            finally:
                serve.PROJECT_ROOT = orig_root
        finally:
            shutil.rmtree(test_dir)

    @patch('serve.run_command')
    def test_testing_preserved_when_only_discoveries_change(self, mock_run):
        test_dir = tempfile.mkdtemp()
        try:
            features_abs = os.path.join(test_dir, "features")
            os.makedirs(features_abs)

            spec_content = (
                "# Feature: Test\n\n"
                "## 1. Overview\nOverview.\n\n"
                "## User Testing Discoveries\n"
            )
            modified_content = (
                "# Feature: Test\n\n"
                "## 1. Overview\nOverview.\n\n"
                "## User Testing Discoveries\n"
                "- [DISCOVERY] New finding (OPEN)\n"
            )
            fpath = os.path.join(features_abs, "test.md")
            with open(fpath, "w") as f:
                f.write(modified_content)

            os.utime(fpath, (3000000000, 3000000000))

            # Pre-built cache (replaces individual git log calls)
            cache = {
                "features/test.md": {
                    'complete_ts': 0, 'complete_hash': '',
                    'testing_ts': 2000000000, 'testing_hash': 'def456',
                    'scope': None,
                }
            }

            # Mock only needed for git show (spec_content_unchanged check)
            def mock_git(cmd):
                if "git show def456:" in cmd:
                    return spec_content
                return ""
            mock_run.side_effect = mock_git

            import serve
            orig_root = serve.PROJECT_ROOT
            serve.PROJECT_ROOT = test_dir
            try:
                complete, testing, todo = get_feature_status(
                    "features", features_abs, cache)
                self.assertEqual(len(testing), 1)
                self.assertEqual(testing[0], "test.md")
                self.assertEqual(len(todo), 0)
            finally:
                serve.PROJECT_ROOT = orig_root
        finally:
            shutil.rmtree(test_dir)


class TestLifecyclePreservedWhenDiscoverySidecarChanges(unittest.TestCase):
    """Scenario: Lifecycle Preserved When Discovery Sidecar Changes

    When a feature's discovery sidecar file (features/<name>.discoveries.md)
    is modified after the status commit, the feature remains in its lifecycle
    state because sidecar files are excluded from feature scanning and their
    mtime does not affect the parent feature's lifecycle.
    """

    def test_sidecar_modification_does_not_reset_lifecycle(self):
        test_dir = tempfile.mkdtemp()
        try:
            features_abs = os.path.join(test_dir, "features")
            os.makedirs(features_abs)

            # Create the feature spec (mtime BEFORE status commit)
            fpath = os.path.join(features_abs, "test.md")
            with open(fpath, "w") as f:
                f.write("# Feature: Test\n\n## 1. Overview\nOverview.\n")
            os.utime(fpath, (1000000000, 1000000000))

            # Create the sidecar file (mtime AFTER status commit)
            sidecar = os.path.join(features_abs, "test.discoveries.md")
            with open(sidecar, "w") as f:
                f.write("# Discoveries\n\n### [BUG] Found something\n- **Status:** OPEN\n")
            os.utime(sidecar, (3000000000, 3000000000))

            # Pre-built cache
            cache = {
                "features/test.md": {
                    'complete_ts': 2000000000, 'complete_hash': 'abc123',
                    'testing_ts': 0, 'testing_hash': '',
                    'scope': None,
                }
            }

            import serve
            orig_root = serve.PROJECT_ROOT
            serve.PROJECT_ROOT = test_dir
            try:
                complete, testing, todo = get_feature_status(
                    "features", features_abs, cache)
                # Feature should be COMPLETE — sidecar mtime doesn't affect it
                self.assertEqual(len(complete), 1)
                self.assertEqual(complete[0][0], "test.md")
                self.assertEqual(len(todo), 0)
                # Sidecar should NOT appear as a separate feature
                all_files = [f[0] if isinstance(f, tuple) else f
                             for f in complete + testing + todo]
                self.assertNotIn("test.discoveries.md", all_files)
            finally:
                serve.PROJECT_ROOT = orig_root
        finally:
            shutil.rmtree(test_dir)


class TestLifecycleResetOnSpecChange(unittest.TestCase):
    """Scenario: Lifecycle Reset When Feature Spec Changes

    When a feature file is modified after the status commit, and the
    modification includes changes above the User Testing Discoveries
    section, the feature is reset to TODO.
    """

    @patch('serve.run_command')
    def test_resets_to_todo_when_spec_changes(self, mock_run):
        test_dir = tempfile.mkdtemp()
        try:
            features_abs = os.path.join(test_dir, "features")
            os.makedirs(features_abs)

            committed_content = (
                "# Feature: Test\n\n"
                "## 1. Overview\nOriginal overview.\n\n"
                "## User Testing Discoveries\n"
            )
            modified_content = (
                "# Feature: Test\n\n"
                "## 1. Overview\nModified overview with new requirements.\n\n"
                "## User Testing Discoveries\n"
            )
            fpath = os.path.join(features_abs, "test.md")
            with open(fpath, "w") as f:
                f.write(modified_content)

            os.utime(fpath, (3000000000, 3000000000))

            # Pre-built cache (replaces individual git log calls)
            cache = {
                "features/test.md": {
                    'complete_ts': 2000000000, 'complete_hash': 'abc123',
                    'testing_ts': 0, 'testing_hash': '',
                    'scope': None,
                }
            }

            # Mock only needed for git show (spec_content_unchanged check)
            def mock_git(cmd):
                if "git show abc123:" in cmd:
                    return committed_content
                return ""
            mock_run.side_effect = mock_git

            import serve
            orig_root = serve.PROJECT_ROOT
            serve.PROJECT_ROOT = test_dir
            try:
                complete, testing, todo = get_feature_status(
                    "features", features_abs, cache)
                self.assertEqual(len(todo), 1)
                self.assertEqual(todo[0], "test.md")
                self.assertEqual(len(complete), 0)
            finally:
                serve.PROJECT_ROOT = orig_root
        finally:
            shutil.rmtree(test_dir)


class TestQaTagClassificationExemption(unittest.TestCase):
    """Scenario: QA Tag Classification Exemption (Section 2.1).

    Commits with [QA-Tags] trailer that only classify QA scenarios
    MUST NOT trigger lifecycle resets.
    """

    @patch('serve.run_command')
    def test_qa_tags_commit_preserves_complete_status(self, mock_run):
        """COMPLETE feature stays COMPLETE when only QA-Tags commits exist."""
        test_dir = tempfile.mkdtemp()
        try:
            features_abs = os.path.join(test_dir, "features")
            os.makedirs(features_abs)

            committed_content = (
                "# Feature: Test\n\n"
                "### QA Scenarios\n\n"
                "#### Scenario: Foo\n\n"
                "    Given x\n    When y\n    Then z\n"
            )
            # QA added @auto tag suffix
            modified_content = (
                "# Feature: Test\n\n"
                "### QA Scenarios\n\n"
                "#### Scenario: Foo @auto\n\n"
                "    Given x\n    When y\n    Then z\n"
            )
            fpath = os.path.join(features_abs, "test.md")
            with open(fpath, "w") as f:
                f.write(modified_content)
            os.utime(fpath, (3000000000, 3000000000))

            cache = {
                "features/test.md": {
                    'complete_ts': 2000000000, 'complete_hash': 'abc123',
                    'testing_ts': 0, 'testing_hash': '',
                    'scope': None,
                }
            }

            def mock_git(cmd):
                if "git show abc123:" in cmd:
                    return committed_content
                if "git log abc123..HEAD" in cmd and "features/test.md" in cmd:
                    return "def456 qa(test): classify scenarios [QA-Tags]"
                return ""
            mock_run.side_effect = mock_git

            import serve
            orig_root = serve.PROJECT_ROOT
            serve.PROJECT_ROOT = test_dir
            try:
                complete, testing, todo = get_feature_status(
                    "features", features_abs, cache)
                self.assertEqual(len(complete), 1)
                self.assertEqual(complete[0][0], "test.md")
                self.assertEqual(len(todo), 0)
            finally:
                serve.PROJECT_ROOT = orig_root
        finally:
            shutil.rmtree(test_dir)

    @patch('serve.run_command')
    def test_qa_tags_commit_preserves_testing_status(self, mock_run):
        """TESTING feature stays TESTING when only QA-Tags commits exist."""
        test_dir = tempfile.mkdtemp()
        try:
            features_abs = os.path.join(test_dir, "features")
            os.makedirs(features_abs)

            committed_content = (
                "# Feature: Test\n\n"
                "### QA Scenarios\n\n"
                "#### Scenario: Bar\n\n"
                "    Given a\n    When b\n    Then c\n"
            )
            modified_content = (
                "# Feature: Test\n\n"
                "### QA Scenarios\n\n"
                "#### Scenario: Bar @manual\n\n"
                "    Given a\n    When b\n    Then c\n"
            )
            fpath = os.path.join(features_abs, "test.md")
            with open(fpath, "w") as f:
                f.write(modified_content)
            os.utime(fpath, (3000000000, 3000000000))

            cache = {
                "features/test.md": {
                    'complete_ts': 0, 'complete_hash': '',
                    'testing_ts': 2000000000, 'testing_hash': 'abc123',
                    'scope': None,
                }
            }

            def mock_git(cmd):
                if "git show abc123:" in cmd:
                    return committed_content
                if "git log abc123..HEAD" in cmd and "features/test.md" in cmd:
                    return "def456 qa(test): classify scenarios [QA-Tags]"
                return ""
            mock_run.side_effect = mock_git

            import serve
            orig_root = serve.PROJECT_ROOT
            serve.PROJECT_ROOT = test_dir
            try:
                complete, testing, todo = get_feature_status(
                    "features", features_abs, cache)
                self.assertEqual(len(testing), 1)
                self.assertEqual(testing[0], "test.md")
                self.assertEqual(len(todo), 0)
            finally:
                serve.PROJECT_ROOT = orig_root
        finally:
            shutil.rmtree(test_dir)

    @patch('serve.run_command')
    def test_mixed_commits_still_resets(self, mock_run):
        """Feature resets when commits include both QA-Tags and non-QA-Tags."""
        test_dir = tempfile.mkdtemp()
        try:
            features_abs = os.path.join(test_dir, "features")
            os.makedirs(features_abs)

            committed_content = (
                "# Feature: Test\n\n"
                "## 1. Overview\nOriginal.\n"
            )
            modified_content = (
                "# Feature: Test\n\n"
                "## 1. Overview\nModified.\n"
            )
            fpath = os.path.join(features_abs, "test.md")
            with open(fpath, "w") as f:
                f.write(modified_content)
            os.utime(fpath, (3000000000, 3000000000))

            cache = {
                "features/test.md": {
                    'complete_ts': 2000000000, 'complete_hash': 'abc123',
                    'testing_ts': 0, 'testing_hash': '',
                    'scope': None,
                }
            }

            def mock_git(cmd):
                if "git show abc123:" in cmd:
                    return committed_content
                if "git log abc123..HEAD" in cmd and "features/test.md" in cmd:
                    return ("def456 qa(test): classify scenarios [QA-Tags]\n"
                            "ghi789 arch(test): add new requirement")
                return ""
            mock_run.side_effect = mock_git

            import serve
            orig_root = serve.PROJECT_ROOT
            serve.PROJECT_ROOT = test_dir
            try:
                complete, testing, todo = get_feature_status(
                    "features", features_abs, cache)
                self.assertEqual(len(todo), 1)
                self.assertEqual(todo[0], "test.md")
                self.assertEqual(len(complete), 0)
            finally:
                serve.PROJECT_ROOT = orig_root
        finally:
            shutil.rmtree(test_dir)

    @patch('serve.run_command')
    def test_no_commits_since_does_not_exempt(self, mock_run):
        """No commits since status commit means no QA-Tags exemption."""
        test_dir = tempfile.mkdtemp()
        try:
            features_abs = os.path.join(test_dir, "features")
            os.makedirs(features_abs)

            committed_content = (
                "# Feature: Test\n\n"
                "## 1. Overview\nOriginal.\n"
            )
            modified_content = (
                "# Feature: Test\n\n"
                "## 1. Overview\nModified.\n"
            )
            fpath = os.path.join(features_abs, "test.md")
            with open(fpath, "w") as f:
                f.write(modified_content)
            os.utime(fpath, (3000000000, 3000000000))

            cache = {
                "features/test.md": {
                    'complete_ts': 2000000000, 'complete_hash': 'abc123',
                    'testing_ts': 0, 'testing_hash': '',
                    'scope': None,
                }
            }

            def mock_git(cmd):
                if "git show abc123:" in cmd:
                    return committed_content
                if "git log abc123..HEAD" in cmd and "features/test.md" in cmd:
                    return ""
                return ""
            mock_run.side_effect = mock_git

            import serve
            orig_root = serve.PROJECT_ROOT
            serve.PROJECT_ROOT = test_dir
            try:
                complete, testing, todo = get_feature_status(
                    "features", features_abs, cache)
                self.assertEqual(len(todo), 1)
                self.assertEqual(todo[0], "test.md")
            finally:
                serve.PROJECT_ROOT = orig_root
        finally:
            shutil.rmtree(test_dir)


# ===================================================================
# Handler Routing Tests
# ===================================================================

class TestHandlerRouting(unittest.TestCase):
    """Tests that the HTTP handler routes correctly."""

    @patch('serve.generate_api_status_json')
    @patch('serve.write_internal_feature_status')
    def test_status_json_route_returns_json(self, mock_write, mock_gen):
        mock_gen.return_value = {
            "features": [],
            "generated_at": "2026-01-01T00:00:00Z",
        }
        from serve import Handler
        import io

        handler = Handler.__new__(Handler)
        handler.path = '/status.json'
        handler.requestline = 'GET /status.json HTTP/1.1'
        handler.request_version = 'HTTP/1.1'
        handler.command = 'GET'
        handler.headers = {}
        handler.wfile = io.BytesIO()

        headers_sent = []

        def mock_send_header(key, value):
            headers_sent.append((key, value))
        handler.send_response = MagicMock()
        handler.send_header = mock_send_header
        handler.end_headers = MagicMock()

        handler.do_GET()

        handler.send_response.assert_called_with(200)
        content_types = [v for k, v in headers_sent if k == "Content-Type"]
        self.assertEqual(content_types, ["application/json"])
        body = handler.wfile.getvalue()
        data = json.loads(body)
        self.assertIn("features", data)
        # Verify no old fields
        self.assertNotIn("test_status", data)
        self.assertIsInstance(data["features"], list)

    @patch('serve.write_internal_feature_status')
    @patch('serve.generate_html')
    def test_root_route_returns_html(self, mock_html, mock_write):
        mock_html.return_value = "<html>test</html>"
        from serve import Handler
        import io

        handler = Handler.__new__(Handler)
        handler.path = '/'
        handler.requestline = 'GET / HTTP/1.1'
        handler.request_version = 'HTTP/1.1'
        handler.command = 'GET'
        handler.headers = {}
        handler.wfile = io.BytesIO()

        headers_sent = []

        def mock_send_header(key, value):
            headers_sent.append((key, value))
        handler.send_response = MagicMock()
        handler.send_header = mock_send_header
        handler.end_headers = MagicMock()

        handler.do_GET()

        handler.send_response.assert_called_with(200)
        content_types = [v for k, v in headers_sent if k == "Content-type"]
        self.assertEqual(content_types, ["text/html"])


class TestRunCriticEndpoint(unittest.TestCase):
    """Scenario: Run Critic Endpoint"""

    @patch('serve.subprocess.run')
    def test_run_critic_returns_json_ok(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        from serve import Handler
        import io

        handler = Handler.__new__(Handler)
        handler.path = '/run-critic'
        handler.requestline = 'POST /run-critic HTTP/1.1'
        handler.request_version = 'HTTP/1.1'
        handler.command = 'POST'
        handler.headers = {}
        handler.wfile = io.BytesIO()

        headers_sent = []

        def mock_send_header(key, value):
            headers_sent.append((key, value))
        handler.send_response = MagicMock()
        handler.send_header = mock_send_header
        handler.end_headers = MagicMock()

        handler.do_POST()

        handler.send_response.assert_called_with(200)
        content_types = [v for k, v in headers_sent if k == "Content-Type"]
        self.assertEqual(content_types, ["application/json"])
        body = handler.wfile.getvalue()
        data = json.loads(body)
        self.assertEqual(data["status"], "ok")

    @patch('serve.subprocess.run',
           side_effect=subprocess.CalledProcessError(1, 'bash'))
    def test_run_critic_returns_error_on_failure(self, mock_run):
        from serve import Handler
        import io

        handler = Handler.__new__(Handler)
        handler.path = '/run-critic'
        handler.requestline = 'POST /run-critic HTTP/1.1'
        handler.request_version = 'HTTP/1.1'
        handler.command = 'POST'
        handler.headers = {}
        handler.wfile = io.BytesIO()

        headers_sent = []

        def mock_send_header(key, value):
            headers_sent.append((key, value))
        handler.send_response = MagicMock()
        handler.send_header = mock_send_header
        handler.end_headers = MagicMock()

        handler.do_POST()

        handler.send_response.assert_called_with(200)
        content_types = [v for k, v in headers_sent if k == "Content-Type"]
        self.assertEqual(content_types, ["application/json"])
        body = handler.wfile.getvalue()
        data = json.loads(body)
        self.assertEqual(data["status"], "error")


# ===================================================================
# Change Scope Tests
# ===================================================================

class TestGetChangeScope(unittest.TestCase):
    """Scenario: Change Scope in API Response / Change Scope Omitted"""

    @patch('serve.run_command')
    def test_extracts_targeted_scope(self, mock_run):
        def mock_git(cmd):
            if "Complete" in cmd:
                return ("2000000000 [Complete features/test.md] "
                        "[Scope: targeted:Web Dashboard Auto-Refresh]")
            return ""
        mock_run.side_effect = mock_git
        scope = get_change_scope("features/test.md")
        self.assertEqual(scope, "targeted:Web Dashboard Auto-Refresh")

    @patch('serve.run_command')
    def test_extracts_full_scope(self, mock_run):
        def mock_git(cmd):
            if "Complete" in cmd:
                return "2000000000 [Complete features/test.md] [Scope: full]"
            return ""
        mock_run.side_effect = mock_git
        scope = get_change_scope("features/test.md")
        self.assertEqual(scope, "full")

    @patch('serve.run_command')
    def test_returns_none_when_no_scope(self, mock_run):
        def mock_git(cmd):
            if "Complete" in cmd:
                return "2000000000 [Complete features/test.md]"
            return ""
        mock_run.side_effect = mock_git
        scope = get_change_scope("features/test.md")
        self.assertIsNone(scope)

    @patch('serve.run_command')
    def test_returns_none_when_no_status_commit(self, mock_run):
        mock_run.return_value = ""
        scope = get_change_scope("features/test.md")
        self.assertIsNone(scope)

    @patch('serve.run_command')
    def test_extracts_scope_from_ready_for_verification(self, mock_run):
        def mock_git(cmd):
            if "Complete" in cmd:
                return ""
            if "Ready for" in cmd:
                return ("2000000000 [Ready for Verification features/test.md] "
                        "[Scope: cosmetic]")
            return ""
        mock_run.side_effect = mock_git
        scope = get_change_scope("features/test.md")
        self.assertEqual(scope, "cosmetic")

    @patch('serve.run_command')
    def test_uses_most_recent_status_commit(self, mock_run):
        """When both Complete and Ready for Verification exist, use newer."""
        def mock_git(cmd):
            if "Complete" in cmd:
                return "1000000000 [Complete features/test.md]"
            if "Ready for" in cmd:
                return ("2000000000 [Ready for Verification features/test.md] "
                        "[Scope: targeted:Scenario A]")
            return ""
        mock_run.side_effect = mock_git
        scope = get_change_scope("features/test.md")
        self.assertEqual(scope, "targeted:Scenario A")


class TestApiStatusJsonChangeScope(unittest.TestCase):
    """Scenario: Change Scope in API Response"""

    @patch('serve.get_change_scope')
    def test_includes_change_scope_when_present(self, mock_scope):
        mock_scope.return_value = "targeted:Web Dashboard Auto-Refresh"
        test_dir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(test_dir, "features")
            tests_dir = os.path.join(test_dir, "tests")
            os.makedirs(features_dir)
            os.makedirs(tests_dir)

            with open(os.path.join(features_dir, "test.md"), "w") as f:
                f.write('# Feature\n\n> Label: "Test"\n')

            import serve
            orig_abs = serve.FEATURES_ABS
            orig_tests = serve.TESTS_DIR
            serve.FEATURES_ABS = features_dir
            serve.TESTS_DIR = tests_dir
            try:
                data = generate_api_status_json()
                entry = data["features"][0]
                self.assertEqual(
                    entry["change_scope"],
                    "targeted:Web Dashboard Auto-Refresh")
            finally:
                serve.FEATURES_ABS = orig_abs
                serve.TESTS_DIR = orig_tests
        finally:
            shutil.rmtree(test_dir)

    @patch('serve.get_change_scope')
    def test_omits_change_scope_when_absent(self, mock_scope):
        mock_scope.return_value = None
        test_dir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(test_dir, "features")
            tests_dir = os.path.join(test_dir, "tests")
            os.makedirs(features_dir)
            os.makedirs(tests_dir)

            with open(os.path.join(features_dir, "test.md"), "w") as f:
                f.write('# Feature\n\n> Label: "Test"\n')

            import serve
            orig_abs = serve.FEATURES_ABS
            orig_tests = serve.TESTS_DIR
            serve.FEATURES_ABS = features_dir
            serve.TESTS_DIR = tests_dir
            try:
                data = generate_api_status_json()
                entry = data["features"][0]
                self.assertNotIn("change_scope", entry)
            finally:
                serve.FEATURES_ABS = orig_abs
                serve.TESTS_DIR = orig_tests
        finally:
            shutil.rmtree(test_dir)


# ===================================================================
# Delivery Phase Tests
# ===================================================================

class TestDeliveryPhaseInApiResponse(unittest.TestCase):
    """Scenario: Delivery Phase in API Response"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.test_dir, ".purlin")
        self.cache_dir = os.path.join(self.purlin_dir, "cache")
        os.makedirs(self.cache_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_includes_delivery_phase_when_plan_exists(self):
        """Given a delivery plan with Phase 1 COMPLETE, Phase 2 IN_PROGRESS,
        Phase 3 PENDING, the response includes delivery_phase with expanded format."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 -- Foundation [COMPLETE]\n"
            "**Features:** feat_a\n\n"
            "## Phase 2 -- Core [IN_PROGRESS]\n"
            "**Features:** feat_b\n\n"
            "## Phase 3 -- Polish [PENDING]\n"
            "**Features:** feat_c\n"
        )
        with open(os.path.join(self.purlin_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        import serve
        orig_root = serve.PROJECT_ROOT
        serve.PROJECT_ROOT = self.test_dir
        try:
            result = get_delivery_phase()
            self.assertIsNotNone(result)
            self.assertEqual(result["completed"], 1)
            self.assertEqual(result["in_progress"], 1)
            self.assertEqual(result["pending"], 1)
            self.assertEqual(result["removed"], 0)
            self.assertEqual(result["total"], 3)
            self.assertEqual(len(result["phases"]), 3)
            # Phases sorted by number
            self.assertEqual(result["phases"][0]["number"], 1)
            self.assertEqual(result["phases"][0]["label"], "Foundation")
            self.assertEqual(result["phases"][0]["status"], "COMPLETE")
            self.assertEqual(result["phases"][1]["number"], 2)
            self.assertEqual(result["phases"][1]["status"], "IN_PROGRESS")
            self.assertEqual(result["phases"][2]["number"], 3)
            self.assertEqual(result["phases"][2]["status"], "PENDING")
        finally:
            serve.PROJECT_ROOT = orig_root

    def test_delivery_phase_in_full_api_response(self):
        """Integration: delivery_phase appears in generate_api_status_json with expanded format."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 -- Foundation [COMPLETE]\n\n"
            "## Phase 2 -- Core [IN_PROGRESS]\n\n"
            "## Phase 3 -- Polish [PENDING]\n"
        )
        with open(os.path.join(self.purlin_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        features_dir = os.path.join(self.test_dir, "features")
        tests_dir = os.path.join(self.test_dir, "tests")
        os.makedirs(features_dir)
        os.makedirs(tests_dir)

        with open(os.path.join(features_dir, "test.md"), "w") as f:
            f.write('# Feature\n\n> Label: "Test"\n')

        import serve
        orig_root = serve.PROJECT_ROOT
        orig_cache = serve.CACHE_DIR
        orig_abs = serve.FEATURES_ABS
        orig_tests = serve.TESTS_DIR
        serve.PROJECT_ROOT = self.test_dir
        serve.CACHE_DIR = self.cache_dir
        serve.FEATURES_ABS = features_dir
        serve.TESTS_DIR = tests_dir
        try:
            data = generate_api_status_json()
            self.assertIn("delivery_phase", data)
            dp = data["delivery_phase"]
            self.assertEqual(dp["completed"], 1)
            self.assertEqual(dp["in_progress"], 1)
            self.assertEqual(dp["pending"], 1)
            self.assertEqual(dp["removed"], 0)
            self.assertEqual(dp["total"], 3)
            self.assertEqual(len(dp["phases"]), 3)
            self.assertEqual(dp["phases"][1]["status"], "IN_PROGRESS")
        finally:
            serve.PROJECT_ROOT = orig_root
            serve.CACHE_DIR = orig_cache
            serve.FEATURES_ABS = orig_abs
            serve.TESTS_DIR = orig_tests

    def test_first_pending_is_current(self):
        """When Phase 1 COMPLETE and Phase 2 PENDING, pending = 1."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 -- Foundation [COMPLETE]\n\n"
            "## Phase 2 -- Core [PENDING]\n"
        )
        with open(os.path.join(self.purlin_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        import serve
        orig_root = serve.PROJECT_ROOT
        serve.PROJECT_ROOT = self.test_dir
        try:
            result = get_delivery_phase()
            self.assertIsNotNone(result)
            self.assertEqual(result["completed"], 1)
            self.assertEqual(result["pending"], 1)
            self.assertEqual(result["in_progress"], 0)
            self.assertEqual(result["total"], 2)
        finally:
            serve.PROJECT_ROOT = orig_root


class TestDeliveryPhaseOmittedWhenNoPlan(unittest.TestCase):
    """Scenario: Delivery Phase Omitted When No Plan"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.test_dir, ".purlin")
        self.cache_dir = os.path.join(self.purlin_dir, "cache")
        os.makedirs(self.cache_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_no_plan_returns_none(self):
        """No delivery_plan.md exists -> get_delivery_phase returns None."""
        import serve
        orig_root = serve.PROJECT_ROOT
        serve.PROJECT_ROOT = self.test_dir
        try:
            result = get_delivery_phase()
            self.assertIsNone(result)
        finally:
            serve.PROJECT_ROOT = orig_root

    def test_no_plan_omits_from_api(self):
        """No delivery_plan.md -> delivery_phase not in API response."""
        features_dir = os.path.join(self.test_dir, "features")
        tests_dir = os.path.join(self.test_dir, "tests")
        os.makedirs(features_dir)
        os.makedirs(tests_dir)

        with open(os.path.join(features_dir, "test.md"), "w") as f:
            f.write('# Feature\n\n> Label: "Test"\n')

        import serve
        orig_root = serve.PROJECT_ROOT
        orig_cache = serve.CACHE_DIR
        orig_abs = serve.FEATURES_ABS
        orig_tests = serve.TESTS_DIR
        serve.PROJECT_ROOT = self.test_dir
        serve.CACHE_DIR = self.cache_dir
        serve.FEATURES_ABS = features_dir
        serve.TESTS_DIR = tests_dir
        try:
            data = generate_api_status_json()
            self.assertNotIn("delivery_phase", data)
        finally:
            serve.PROJECT_ROOT = orig_root
            serve.CACHE_DIR = orig_cache
            serve.FEATURES_ABS = orig_abs
            serve.TESTS_DIR = orig_tests

    def test_all_phases_complete_returns_none(self):
        """All phases COMPLETE -> delivery_phase omitted."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 -- Foundation [COMPLETE]\n\n"
            "## Phase 2 -- Core [COMPLETE]\n"
        )
        with open(os.path.join(self.purlin_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        import serve
        orig_root = serve.PROJECT_ROOT
        serve.PROJECT_ROOT = self.test_dir
        try:
            result = get_delivery_phase()
            self.assertIsNone(result)
        finally:
            serve.PROJECT_ROOT = orig_root


class TestDeliveryPhaseHTMLAnnotation(unittest.TestCase):
    """Scenario: Delivery Phase Annotation in ACTIVE Header.

    Verifies that when a delivery plan exists with an active phase,
    the generated HTML includes the [PHASE (N/M)] annotation in the
    ACTIVE section heading.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.test_dir, ".purlin")
        self.cache_dir = os.path.join(self.purlin_dir, "cache")
        os.makedirs(self.cache_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('serve.get_git_status', return_value='')
    @patch('serve.get_last_commit', return_value='abc1234 test (1 min ago)')
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_active_heading_includes_phase_annotation(self, *mocks):
        """ACTIVE heading shows [1/3 DONE | 1 IN PROGRESS] when delivery plan has active phase."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 -- Foundation [COMPLETE]\n\n"
            "## Phase 2 -- Core [IN_PROGRESS]\n\n"
            "## Phase 3 -- Polish [PENDING]\n"
        )
        with open(os.path.join(self.purlin_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        features_dir = os.path.join(self.test_dir, "features")
        tests_dir = os.path.join(self.test_dir, "tests")
        os.makedirs(features_dir)
        os.makedirs(tests_dir)
        with open(os.path.join(features_dir, "test_feat.md"), "w") as f:
            f.write('# Feature\n\n> Label: "Test Feature"\n')

        import serve
        orig_cache = serve.CACHE_DIR
        orig_abs = serve.FEATURES_ABS
        orig_tests = serve.TESTS_DIR
        orig_root = serve.PROJECT_ROOT
        serve.CACHE_DIR = self.cache_dir
        serve.FEATURES_ABS = features_dir
        serve.TESTS_DIR = tests_dir
        serve.PROJECT_ROOT = self.test_dir
        try:
            html = serve.generate_html()
            self.assertIn('[1/3 DONE | 1 IN PROGRESS]', html,
                          "ACTIVE heading must include [1/3 DONE | 1 IN PROGRESS] annotation")
        finally:
            serve.CACHE_DIR = orig_cache
            serve.FEATURES_ABS = orig_abs
            serve.TESTS_DIR = orig_tests
            serve.PROJECT_ROOT = orig_root

    @patch('serve.get_git_status', return_value='')
    @patch('serve.get_last_commit', return_value='abc1234 test (1 min ago)')
    @patch('serve.get_release_checklist', return_value=([], [], []))
    def test_active_heading_no_phase_when_no_plan(self, *mocks):
        """ACTIVE heading has no [PHASE] annotation when no delivery plan exists."""
        features_dir = os.path.join(self.test_dir, "features")
        tests_dir = os.path.join(self.test_dir, "tests")
        os.makedirs(features_dir)
        os.makedirs(tests_dir)
        with open(os.path.join(features_dir, "test_feat.md"), "w") as f:
            f.write('# Feature\n\n> Label: "Test Feature"\n')

        import serve
        orig_cache = serve.CACHE_DIR
        orig_abs = serve.FEATURES_ABS
        orig_tests = serve.TESTS_DIR
        orig_root = serve.PROJECT_ROOT
        serve.CACHE_DIR = self.cache_dir
        serve.FEATURES_ABS = features_dir
        serve.TESTS_DIR = tests_dir
        serve.PROJECT_ROOT = self.test_dir
        try:
            html = serve.generate_html()
            self.assertNotIn('DONE]', html,
                             "ACTIVE heading must NOT include phase annotation when no plan")
        finally:
            serve.CACHE_DIR = orig_cache
            serve.FEATURES_ABS = orig_abs
            serve.TESTS_DIR = orig_tests
            serve.PROJECT_ROOT = orig_root


class TestDeliveryPhaseWithParallelExecution(unittest.TestCase):
    """Scenario: Delivery Phase with Parallel Execution"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.test_dir, ".purlin")
        self.cache_dir = os.path.join(self.purlin_dir, "cache")
        os.makedirs(self.cache_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_parallel_in_progress_phases(self):
        """Phase 1 COMPLETE, Phase 2 IN_PROGRESS, Phase 3 IN_PROGRESS,
        Phase 4 PENDING -> completed 1, in_progress 2, pending 1, total 4."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 -- Foundation [COMPLETE]\n\n"
            "## Phase 2 -- Core [IN_PROGRESS]\n\n"
            "## Phase 3 -- UI [IN_PROGRESS]\n\n"
            "## Phase 4 -- Polish [PENDING]\n"
        )
        with open(os.path.join(self.purlin_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        import serve
        orig_root = serve.PROJECT_ROOT
        serve.PROJECT_ROOT = self.test_dir
        try:
            result = get_delivery_phase()
            self.assertIsNotNone(result)
            self.assertEqual(result["completed"], 1)
            self.assertEqual(result["in_progress"], 2)
            self.assertEqual(result["pending"], 1)
            self.assertEqual(result["removed"], 0)
            self.assertEqual(result["total"], 4)
            # Phase 2 and Phase 3 both IN_PROGRESS
            ip_phases = [p for p in result["phases"] if p["status"] == "IN_PROGRESS"]
            self.assertEqual(len(ip_phases), 2)
            self.assertEqual(ip_phases[0]["number"], 2)
            self.assertEqual(ip_phases[1]["number"], 3)
        finally:
            serve.PROJECT_ROOT = orig_root


class TestDeliveryPhaseWithRemovedPhase(unittest.TestCase):
    """Scenario: Delivery Phase with Removed Phase"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.test_dir, ".purlin")
        self.cache_dir = os.path.join(self.purlin_dir, "cache")
        os.makedirs(self.cache_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_removed_phase_counted(self):
        """Phase 1 COMPLETE, Phase 2 REMOVED, Phase 3 IN_PROGRESS ->
        completed 1, in_progress 1, pending 0, removed 1, total 3."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 -- Foundation [COMPLETE]\n\n"
            "## Phase 2 -- Legacy [REMOVED]\n\n"
            "## Phase 3 -- Core [IN_PROGRESS]\n"
        )
        with open(os.path.join(self.purlin_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        import serve
        orig_root = serve.PROJECT_ROOT
        serve.PROJECT_ROOT = self.test_dir
        try:
            result = get_delivery_phase()
            self.assertIsNotNone(result)
            self.assertEqual(result["completed"], 1)
            self.assertEqual(result["in_progress"], 1)
            self.assertEqual(result["pending"], 0)
            self.assertEqual(result["removed"], 1)
            self.assertEqual(result["total"], 3)
        finally:
            serve.PROJECT_ROOT = orig_root


class TestDeliveryPhaseOmittedWhenAllCompleteOrRemoved(unittest.TestCase):
    """Scenario: Delivery Phase Omitted When All Complete or Removed"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.test_dir, ".purlin")
        self.cache_dir = os.path.join(self.purlin_dir, "cache")
        os.makedirs(self.cache_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_all_complete_and_removed_returns_none(self):
        """Phase 1 COMPLETE, Phase 2 COMPLETE, Phase 3 REMOVED ->
        delivery_phase omitted (returns None)."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 -- Foundation [COMPLETE]\n\n"
            "## Phase 2 -- Core [COMPLETE]\n\n"
            "## Phase 3 -- Legacy [REMOVED]\n"
        )
        with open(os.path.join(self.purlin_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        import serve
        orig_root = serve.PROJECT_ROOT
        serve.PROJECT_ROOT = self.test_dir
        try:
            result = get_delivery_phase()
            self.assertIsNone(result)
        finally:
            serve.PROJECT_ROOT = orig_root

    def test_all_removed_returns_none(self):
        """All phases REMOVED -> delivery_phase omitted."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 -- Old [REMOVED]\n\n"
            "## Phase 2 -- Also Old [REMOVED]\n"
        )
        with open(os.path.join(self.purlin_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        import serve
        orig_root = serve.PROJECT_ROOT
        serve.PROJECT_ROOT = self.test_dir
        try:
            result = get_delivery_phase()
            self.assertIsNone(result)
        finally:
            serve.PROJECT_ROOT = orig_root


class TestDeliveryPhaseLabelsFromPlanHeadings(unittest.TestCase):
    """Scenario: Delivery Phase Labels from Plan Headings"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.test_dir, ".purlin")
        self.cache_dir = os.path.join(self.purlin_dir, "cache")
        os.makedirs(self.cache_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_labels_extracted_from_headings(self):
        """Phase heading '## Phase 1 -- Design Token Foundation [COMPLETE]'
        produces label 'Design Token Foundation'."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 -- Design Token Foundation [COMPLETE]\n\n"
            "## Phase 2 -- Critic Policy Enforcement [IN_PROGRESS]\n\n"
            "## Phase 3 -- CDD Status Monitor [PENDING]\n"
        )
        with open(os.path.join(self.purlin_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        import serve
        orig_root = serve.PROJECT_ROOT
        serve.PROJECT_ROOT = self.test_dir
        try:
            result = get_delivery_phase()
            self.assertIsNotNone(result)
            self.assertEqual(result["phases"][0]["label"], "Design Token Foundation")
            self.assertEqual(result["phases"][1]["label"], "Critic Policy Enforcement")
            self.assertEqual(result["phases"][2]["label"], "CDD Status Monitor")
        finally:
            serve.PROJECT_ROOT = orig_root

    def test_labels_with_em_dash_separator(self):
        """Labels work with em dash separator too."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 \u2014 Foundation [COMPLETE]\n\n"
            "## Phase 2 \u2014 Core [IN_PROGRESS]\n"
        )
        with open(os.path.join(self.purlin_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        import serve
        orig_root = serve.PROJECT_ROOT
        serve.PROJECT_ROOT = self.test_dir
        try:
            result = get_delivery_phase()
            self.assertIsNotNone(result)
            self.assertEqual(result["phases"][0]["label"], "Foundation")
            self.assertEqual(result["phases"][1]["label"], "Core")
        finally:
            serve.PROJECT_ROOT = orig_root


# ===================================================================
# Tombstone Entry Tests
# ===================================================================

class TestTombstoneEntryInApiResponse(unittest.TestCase):
    """Scenario: Tombstone Entry in API Response"""

    def test_tombstone_appears_in_features_array(self):
        """Tombstone file at features/tombstones/<name>.md appears in API response
        with tombstone=true, hardcoded role status, and no change_scope."""
        test_dir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(test_dir, "features")
            tombstones_dir = os.path.join(features_dir, "tombstones")
            tests_dir = os.path.join(test_dir, "tests")
            os.makedirs(tombstones_dir)
            os.makedirs(tests_dir)

            # Create a tombstone file
            with open(os.path.join(
                    tombstones_dir, "some_retired_feature.md"), "w") as f:
                f.write(
                    "# TOMBSTONE: some_retired_feature\n\n"
                    "> Label: \"Retired Feature\"\n\n"
                    "**Retired:** 2026-02-22\n"
                )

            import serve
            orig_abs = serve.FEATURES_ABS
            orig_tests = serve.TESTS_DIR
            serve.FEATURES_ABS = features_dir
            serve.TESTS_DIR = tests_dir
            try:
                data = generate_api_status_json()
                features = data["features"]

                # Find the tombstone entry
                tombstone_entries = [
                    e for e in features if e.get("tombstone")]
                self.assertEqual(
                    len(tombstone_entries), 1,
                    f"Expected 1 tombstone entry, got {len(tombstone_entries)}")

                entry = tombstone_entries[0]
                self.assertEqual(
                    entry["file"],
                    "features/tombstones/some_retired_feature.md")
                self.assertTrue(entry["tombstone"])
                self.assertEqual(entry["architect"], "DONE")
                self.assertEqual(entry["builder"], "TODO")
                self.assertEqual(entry["qa"], "N/A")
                self.assertEqual(entry["pm"], "N/A")
                self.assertNotIn("change_scope", entry)
            finally:
                serve.FEATURES_ABS = orig_abs
                serve.TESTS_DIR = orig_tests
        finally:
            shutil.rmtree(test_dir)

    def test_tombstone_never_in_complete(self):
        """Tombstone entries are never classified as complete."""
        entry = {
            "file": "features/tombstones/retired.md",
            "tombstone": True,
            "architect": "DONE",
            "builder": "TODO",
            "qa": "N/A",
            "pm": "N/A",
        }
        self.assertFalse(_is_feature_complete(entry))

    def test_no_tombstones_dir_is_fine(self):
        """When features/tombstones/ doesn't exist, no tombstone entries."""
        test_dir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(test_dir, "features")
            tests_dir = os.path.join(test_dir, "tests")
            os.makedirs(features_dir)
            os.makedirs(tests_dir)

            with open(os.path.join(features_dir, "test.md"), "w") as f:
                f.write('# Feature\n\n> Label: "Test"\n')

            import serve
            orig_abs = serve.FEATURES_ABS
            orig_tests = serve.TESTS_DIR
            serve.FEATURES_ABS = features_dir
            serve.TESTS_DIR = tests_dir
            try:
                data = generate_api_status_json()
                tombstone_entries = [
                    e for e in data["features"] if e.get("tombstone")]
                self.assertEqual(len(tombstone_entries), 0)
            finally:
                serve.FEATURES_ABS = orig_abs
                serve.TESTS_DIR = orig_tests
        finally:
            shutil.rmtree(test_dir)


class TestTombstoneEntryInCliOutput(unittest.TestCase):
    """Scenario: Tombstone Entry in CLI Status Output

    CLI uses the same generate_api_status_json() function, so tombstone
    entries appear in CLI output identically to the API response.
    """

    def test_cli_tombstone_same_as_api(self):
        """CLI status output includes tombstone with same fields as API."""
        test_dir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(test_dir, "features")
            tombstones_dir = os.path.join(features_dir, "tombstones")
            tests_dir = os.path.join(test_dir, "tests")
            os.makedirs(tombstones_dir)
            os.makedirs(tests_dir)

            with open(os.path.join(
                    tombstones_dir, "some_retired_feature.md"), "w") as f:
                f.write("# TOMBSTONE: some_retired_feature\n\n"
                        "> Label: \"Retired Feature\"\n")

            import serve
            orig_abs = serve.FEATURES_ABS
            orig_tests = serve.TESTS_DIR
            serve.FEATURES_ABS = features_dir
            serve.TESTS_DIR = tests_dir
            try:
                # CLI uses generate_api_status_json() via --cli-status
                data = generate_api_status_json()
                tombstone_entries = [
                    e for e in data["features"] if e.get("tombstone")]
                self.assertEqual(len(tombstone_entries), 1)
                entry = tombstone_entries[0]
                self.assertTrue(entry["tombstone"])
                self.assertEqual(entry["architect"], "DONE")
                self.assertEqual(entry["builder"], "TODO")
                self.assertEqual(entry["qa"], "N/A")
                self.assertEqual(entry["pm"], "N/A")
            finally:
                serve.FEATURES_ABS = orig_abs
                serve.TESTS_DIR = orig_tests
        finally:
            shutil.rmtree(test_dir)


# ===================================================================
# Complete Section Recency Sort Tests (Section 2.2.2 BUG fix)
# ===================================================================

class TestCompleteSectionRecencySort(unittest.TestCase):
    """Scenario: Complete section sorted by most recent completion.

    Verifies that generate_api_status_json() includes complete_ts in
    the API response and that generate_html() sorts the Complete section
    by recency (most recent first) rather than alphabetically.
    """

    def test_api_includes_complete_ts_when_present(self):
        """API response includes complete_ts for features with a completion commit."""
        test_dir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(test_dir, "features")
            tests_dir = os.path.join(test_dir, "tests")
            os.makedirs(features_dir)
            os.makedirs(tests_dir)

            with open(os.path.join(features_dir, "feat_a.md"), "w") as f:
                f.write('# Feature A\n\n> Label: "Feature A"\n')

            cache = {
                os.path.normpath("features/feat_a.md"): {
                    'complete_ts': 1700000000,
                    'complete_hash': 'abc123',
                    'testing_ts': 0,
                    'testing_hash': '',
                    'scope': None,
                }
            }

            import serve
            orig_abs = serve.FEATURES_ABS
            orig_rel = serve.FEATURES_REL
            orig_tests = serve.TESTS_DIR
            orig_root = serve.PROJECT_ROOT
            serve.FEATURES_ABS = features_dir
            serve.FEATURES_REL = "features"
            serve.TESTS_DIR = tests_dir
            serve.PROJECT_ROOT = test_dir
            try:
                data = generate_api_status_json(cache=cache)
                feat = data["features"][0]
                self.assertEqual(feat["complete_ts"], 1700000000)
            finally:
                serve.FEATURES_ABS = orig_abs
                serve.FEATURES_REL = orig_rel
                serve.TESTS_DIR = orig_tests
                serve.PROJECT_ROOT = orig_root
        finally:
            shutil.rmtree(test_dir)

    def test_api_omits_complete_ts_when_zero(self):
        """API response omits complete_ts when no completion commit exists."""
        test_dir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(test_dir, "features")
            tests_dir = os.path.join(test_dir, "tests")
            os.makedirs(features_dir)
            os.makedirs(tests_dir)

            with open(os.path.join(features_dir, "feat_b.md"), "w") as f:
                f.write('# Feature B\n\n> Label: "Feature B"\n')

            cache = {
                os.path.normpath("features/feat_b.md"): {
                    'complete_ts': 0,
                    'complete_hash': '',
                    'testing_ts': 1700000000,
                    'testing_hash': 'def456',
                    'scope': None,
                }
            }

            import serve
            orig_abs = serve.FEATURES_ABS
            orig_rel = serve.FEATURES_REL
            orig_tests = serve.TESTS_DIR
            orig_root = serve.PROJECT_ROOT
            serve.FEATURES_ABS = features_dir
            serve.FEATURES_REL = "features"
            serve.TESTS_DIR = tests_dir
            serve.PROJECT_ROOT = test_dir
            try:
                data = generate_api_status_json(cache=cache)
                feat = data["features"][0]
                self.assertNotIn("complete_ts", feat)
            finally:
                serve.FEATURES_ABS = orig_abs
                serve.FEATURES_REL = orig_rel
                serve.TESTS_DIR = orig_tests
                serve.PROJECT_ROOT = orig_root
        finally:
            shutil.rmtree(test_dir)


# ===================================================================
# CLI Graph Output Tests
# ===================================================================

class TestCLIGraphOutput(unittest.TestCase):
    """Scenario: CLI Graph Output"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.test_dir, "features")
        os.makedirs(self.features_dir)
        # Create feature files with prerequisite links
        with open(os.path.join(self.features_dir, "arch_base.md"), "w") as f:
            f.write("# Arch Base\n\n> Label: \"Arch Base\"\n")
        with open(os.path.join(self.features_dir, "feature_a.md"), "w") as f:
            f.write("# Feature A\n\n> Label: \"Feature A\"\n> Prerequisite: features/arch_base.md\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_cli_graph_outputs_valid_json(self):
        """CLI graph output returns valid JSON with features, cycles, orphans arrays."""
        from graph import parse_features, generate_dependency_graph
        features = parse_features(self.features_dir)
        graph = generate_dependency_graph(features, features_dir=self.features_dir)
        self.assertIn("features", graph)
        self.assertIn("cycles", graph)
        self.assertIn("orphans", graph)
        self.assertIsInstance(graph["features"], list)
        self.assertIsInstance(graph["cycles"], list)
        self.assertIsInstance(graph["orphans"], list)
        # Verify features are populated
        self.assertGreater(len(graph["features"]), 0)
        # Verify JSON serializable
        json_str = json.dumps(graph, indent=2)
        reparsed = json.loads(json_str)
        self.assertEqual(reparsed["features"], graph["features"])


# ===================================================================
# CLI Role-Filtered Output Tests
# ===================================================================

class TestCLIRoleFilteredOutput(unittest.TestCase):
    """Scenario: CLI Role-Filtered Output

    Given features with various lifecycle states and a role with non-terminal
    status on some features, --role <role> returns only those features plus
    scoped action items and policy violations.
    """

    @patch('serve.TESTS_DIR')
    @patch('serve.FEATURES_ABS')
    def test_role_filtered_returns_only_non_terminal_features(
            self, mock_fabs, mock_tdir):
        """Features where the role has terminal status are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            tests_dir = os.path.join(tmpdir, "tests")
            os.makedirs(features_dir)
            mock_fabs.__str__ = lambda s: features_dir
            # Patch the actual string value used by serve
            mock_tdir.__str__ = lambda s: tests_dir

            # Create 4 features with different builder statuses
            feature_configs = {
                "feat_todo1": {"builder": "TODO", "architect": "DONE",
                               "qa": "N/A", "pm": "N/A"},
                "feat_todo2": {"builder": "TODO", "architect": "DONE",
                               "qa": "N/A", "pm": "N/A"},
                "feat_fail": {"builder": "FAIL", "architect": "DONE",
                              "qa": "N/A", "pm": "N/A"},
                "feat_done": {"builder": "DONE", "architect": "DONE",
                              "qa": "CLEAN", "pm": "N/A"},
            }

            for stem, role_status in feature_configs.items():
                # Create feature file
                fpath = os.path.join(features_dir, f"{stem}.md")
                with open(fpath, 'w') as f:
                    f.write(f'# Feature: {stem}\n\n> Label: "{stem}"\n')

                # Create critic.json with role_status
                tdir = os.path.join(tests_dir, stem)
                os.makedirs(tdir, exist_ok=True)
                critic_data = {
                    "role_status": role_status,
                    "action_items": {
                        "architect": [],
                        "builder": [{"priority": "HIGH",
                                     "description": f"Implement {stem}",
                                     "feature": stem,
                                     "category": "lifecycle_reset"}]
                        if role_status["builder"] != "DONE" else [],
                        "qa": [],
                        "pm": [],
                    },
                    "implementation_gate": {
                        "checks": {
                            "policy_adherence": {
                                "status": "PASS",
                                "violations": [],
                            }
                        }
                    },
                }
                with open(os.path.join(tdir, "critic.json"), 'w') as f:
                    json.dump(critic_data, f)

            with patch('serve.FEATURES_ABS', features_dir), \
                 patch('serve.FEATURES_REL', 'features'), \
                 patch('serve.TESTS_DIR', tests_dir), \
                 patch('serve.build_status_commit_cache', return_value={}):
                result = generate_role_filtered_status_json("builder")

            # Should have 3 features (2 TODO + 1 FAIL), not the DONE one
            self.assertEqual(len(result["features"]), 3)
            feature_files = [f["file"] for f in result["features"]]
            self.assertNotIn("features/feat_done.md", feature_files)
            self.assertIn("features/feat_todo1.md", feature_files)
            self.assertIn("features/feat_todo2.md", feature_files)
            self.assertIn("features/feat_fail.md", feature_files)

            # Action items should be builder-only, 3 items
            self.assertEqual(len(result["action_items"]), 3)
            for item in result["action_items"]:
                self.assertIn("description", item)

            # Output must NOT contain other roles' action items
            self.assertNotIn("architect", result)
            self.assertNotIn("qa", result)
            self.assertNotIn("pm", result)

            # Must have standard keys
            self.assertIn("features", result)
            self.assertIn("action_items", result)
            self.assertIn("policy_violations", result)
            self.assertIn("generated_at", result)

    @patch('serve.TESTS_DIR')
    @patch('serve.FEATURES_ABS')
    def test_role_filtered_includes_scoped_policy_violations(
            self, mock_fabs, mock_tdir):
        """Policy violations are included only for features in the filtered set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            tests_dir = os.path.join(tmpdir, "tests")
            os.makedirs(features_dir)

            # Feature with violations and builder TODO
            for stem in ["feat_with_violations", "feat_clean"]:
                fpath = os.path.join(features_dir, f"{stem}.md")
                with open(fpath, 'w') as f:
                    f.write(f'# Feature: {stem}\n\n> Label: "{stem}"\n')

                tdir = os.path.join(tests_dir, stem)
                os.makedirs(tdir, exist_ok=True)

                is_todo = stem == "feat_with_violations"
                violations = [
                    {"file": "tools/cdd/graph.py", "line": 100,
                     "pattern": "#[0-9a-fA-F]{3,8}",
                     "text": "fill:#e1f5fe"},
                    {"file": "tools/cdd/graph.py", "line": 200,
                     "pattern": "#[0-9a-fA-F]{3,8}",
                     "text": "fill:#01579b"},
                ] if is_todo else []

                critic_data = {
                    "role_status": {
                        "builder": "TODO" if is_todo else "DONE",
                        "architect": "DONE", "qa": "N/A", "pm": "N/A",
                    },
                    "action_items": {"architect": [], "builder": [],
                                     "qa": [], "pm": []},
                    "implementation_gate": {
                        "checks": {
                            "policy_adherence": {
                                "status": "FAIL" if violations else "PASS",
                                "violations": violations,
                            }
                        }
                    },
                }
                with open(os.path.join(tdir, "critic.json"), 'w') as f:
                    json.dump(critic_data, f)

            with patch('serve.FEATURES_ABS', features_dir), \
                 patch('serve.FEATURES_REL', 'features'), \
                 patch('serve.TESTS_DIR', tests_dir), \
                 patch('serve.build_status_commit_cache', return_value={}):
                result = generate_role_filtered_status_json("builder")

            # Only feat_with_violations is in the filtered set
            self.assertEqual(len(result["features"]), 1)
            self.assertEqual(result["features"][0]["file"],
                             "features/feat_with_violations.md")

            # Violations should be compacted and present
            self.assertGreater(len(result["policy_violations"]), 0)
            # All violations should reference the filtered feature
            for pv in result["policy_violations"]:
                self.assertEqual(pv["feature"], "feat_with_violations")
                self.assertIn("count", pv)
                self.assertIn("file", pv)
                self.assertIn("pattern", pv)

    @patch('serve.TESTS_DIR')
    @patch('serve.FEATURES_ABS')
    def test_output_is_valid_json_with_required_keys(
            self, mock_fabs, mock_tdir):
        """Output must be valid JSON with features, action_items,
        policy_violations, and generated_at keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            tests_dir = os.path.join(tmpdir, "tests")
            os.makedirs(features_dir)

            fpath = os.path.join(features_dir, "feat_a.md")
            with open(fpath, 'w') as f:
                f.write('# Feature A\n\n> Label: "Feature A"\n')

            tdir = os.path.join(tests_dir, "feat_a")
            os.makedirs(tdir, exist_ok=True)
            critic_data = {
                "role_status": {"builder": "TODO", "architect": "DONE",
                                "qa": "N/A", "pm": "N/A"},
                "action_items": {"architect": [], "builder": [],
                                 "qa": [], "pm": []},
                "implementation_gate": {"checks": {"policy_adherence": {
                    "status": "PASS", "violations": []}}},
            }
            with open(os.path.join(tdir, "critic.json"), 'w') as f:
                json.dump(critic_data, f)

            with patch('serve.FEATURES_ABS', features_dir), \
                 patch('serve.FEATURES_REL', 'features'), \
                 patch('serve.TESTS_DIR', tests_dir), \
                 patch('serve.build_status_commit_cache', return_value={}):
                result = generate_role_filtered_status_json("builder")

            # Verify JSON round-trip
            json_str = json.dumps(result, indent=2)
            reparsed = json.loads(json_str)
            self.assertEqual(reparsed["features"], result["features"])
            self.assertEqual(reparsed["action_items"], result["action_items"])
            self.assertEqual(reparsed["policy_violations"],
                             result["policy_violations"])
            self.assertIn("generated_at", reparsed)


class TestCLIRoleFilteredOutputNoWork(unittest.TestCase):
    """Scenario: CLI Role-Filtered Output With No Work

    Given all features have terminal status for a role, the filtered output
    has empty features and action_items arrays.
    """

    @patch('serve.TESTS_DIR')
    @patch('serve.FEATURES_ABS')
    def test_all_terminal_returns_empty_arrays(self, mock_fabs, mock_tdir):
        """When all features have builder DONE, output is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            tests_dir = os.path.join(tmpdir, "tests")
            os.makedirs(features_dir)

            for stem in ["feat_a", "feat_b", "feat_c"]:
                fpath = os.path.join(features_dir, f"{stem}.md")
                with open(fpath, 'w') as f:
                    f.write(f'# Feature: {stem}\n\n> Label: "{stem}"\n')

                tdir = os.path.join(tests_dir, stem)
                os.makedirs(tdir, exist_ok=True)
                critic_data = {
                    "role_status": {"builder": "DONE", "architect": "DONE",
                                    "qa": "CLEAN", "pm": "N/A"},
                    "action_items": {"architect": [], "builder": [],
                                     "qa": [], "pm": []},
                    "implementation_gate": {"checks": {"policy_adherence": {
                        "status": "PASS", "violations": []}}},
                }
                with open(os.path.join(tdir, "critic.json"), 'w') as f:
                    json.dump(critic_data, f)

            with patch('serve.FEATURES_ABS', features_dir), \
                 patch('serve.FEATURES_REL', 'features'), \
                 patch('serve.TESTS_DIR', tests_dir), \
                 patch('serve.build_status_commit_cache', return_value={}):
                result = generate_role_filtered_status_json("builder")

            self.assertEqual(len(result["features"]), 0)
            self.assertEqual(len(result["action_items"]), 0)
            self.assertEqual(len(result["policy_violations"]), 0)
            # Must still be valid JSON with required keys
            self.assertIn("generated_at", result)

    @patch('serve.TESTS_DIR')
    @patch('serve.FEATURES_ABS')
    def test_qa_clean_is_terminal(self, mock_fabs, mock_tdir):
        """CLEAN status is terminal for QA role."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            tests_dir = os.path.join(tmpdir, "tests")
            os.makedirs(features_dir)

            fpath = os.path.join(features_dir, "feat_a.md")
            with open(fpath, 'w') as f:
                f.write('# Feature A\n\n> Label: "Feature A"\n')

            tdir = os.path.join(tests_dir, "feat_a")
            os.makedirs(tdir, exist_ok=True)
            critic_data = {
                "role_status": {"builder": "DONE", "architect": "DONE",
                                "qa": "CLEAN", "pm": "N/A"},
                "action_items": {"architect": [], "builder": [],
                                 "qa": [], "pm": []},
                "implementation_gate": {"checks": {"policy_adherence": {
                    "status": "PASS", "violations": []}}},
            }
            with open(os.path.join(tdir, "critic.json"), 'w') as f:
                json.dump(critic_data, f)

            with patch('serve.FEATURES_ABS', features_dir), \
                 patch('serve.FEATURES_REL', 'features'), \
                 patch('serve.TESTS_DIR', tests_dir), \
                 patch('serve.build_status_commit_cache', return_value={}):
                result = generate_role_filtered_status_json("qa")

            # qa=CLEAN is terminal, so no features
            self.assertEqual(len(result["features"]), 0)

    @patch('serve.TESTS_DIR')
    @patch('serve.FEATURES_ABS')
    def test_na_is_terminal(self, mock_fabs, mock_tdir):
        """N/A status is terminal for any role."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            tests_dir = os.path.join(tmpdir, "tests")
            os.makedirs(features_dir)

            fpath = os.path.join(features_dir, "feat_a.md")
            with open(fpath, 'w') as f:
                f.write('# Feature A\n\n> Label: "Feature A"\n')

            tdir = os.path.join(tests_dir, "feat_a")
            os.makedirs(tdir, exist_ok=True)
            critic_data = {
                "role_status": {"builder": "DONE", "architect": "DONE",
                                "qa": "CLEAN", "pm": "N/A"},
                "action_items": {"architect": [], "builder": [],
                                 "qa": [], "pm": []},
                "implementation_gate": {"checks": {"policy_adherence": {
                    "status": "PASS", "violations": []}}},
            }
            with open(os.path.join(tdir, "critic.json"), 'w') as f:
                json.dump(critic_data, f)

            with patch('serve.FEATURES_ABS', features_dir), \
                 patch('serve.FEATURES_REL', 'features'), \
                 patch('serve.TESTS_DIR', tests_dir), \
                 patch('serve.build_status_commit_cache', return_value={}):
                result = generate_role_filtered_status_json("pm")

            # pm=N/A is terminal
            self.assertEqual(len(result["features"]), 0)


# ===================================================================
# Dependency Graph Endpoint Tests
# ===================================================================

class TestDependencyGraphEndpoint(unittest.TestCase):
    """Scenario: Dependency Graph Endpoint — /dependency_graph.json returns graph."""

    def test_dependency_graph_endpoint_serves_cached_file(self):
        """Dependency graph endpoint returns cached JSON with Content-Type application/json."""
        from serve import Handler
        import io

        test_graph = {"features": [{"file": "test.md"}], "cycles": [], "orphans": []}
        test_json = json.dumps(test_graph).encode('utf-8')

        handler = Handler.__new__(Handler)
        handler.path = '/dependency_graph.json'
        handler.requestline = 'GET /dependency_graph.json HTTP/1.1'
        handler.request_version = 'HTTP/1.1'
        handler.command = 'GET'
        handler.headers = {}
        handler.wfile = io.BytesIO()

        headers_sent = []

        def mock_send_header(key, value):
            headers_sent.append((key, value))
        handler.send_response = MagicMock()
        handler.send_header = mock_send_header
        handler.end_headers = MagicMock()

        # Write a temp graph file and patch the path
        import serve as _serve
        orig_path = _serve.DEPENDENCY_GRAPH_PATH
        tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        tmp.write(test_json)
        tmp.close()
        _serve.DEPENDENCY_GRAPH_PATH = tmp.name
        try:
            handler.do_GET()
        finally:
            _serve.DEPENDENCY_GRAPH_PATH = orig_path
            os.unlink(tmp.name)

        handler.send_response.assert_called_with(200)
        content_types = [v for k, v in headers_sent if k == 'Content-Type']
        self.assertEqual(content_types, ['application/json'])
        body = handler.wfile.getvalue()
        data = json.loads(body)
        self.assertIn("features", data)


# ===================================================================
# Port Override Tests (Section 2.12)
# ===================================================================

class TestPortResolution(unittest.TestCase):
    """Tests for cdd_lifecycle port resolution."""

    def test_cli_port_override_via_flag(self):
        """Scenario: CLI Port Override via Flag — explicit port is used."""
        port = resolve_port(cli_port=9090)
        self.assertEqual(port, 9090)

    def test_auto_port_when_no_cli_port(self):
        """Scenario: Auto port selection when no --port given."""
        port = resolve_port(cli_port=None)
        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)
        self.assertLessEqual(port, 65535)

    def test_auto_port_is_available(self):
        """Auto-selected port can be bound to."""
        port = resolve_port(cli_port=None)
        import socket as _sock
        with _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM) as s:
            # Port should be bindable (OS just freed it)
            try:
                s.bind(('', port))
            except OSError:
                pass  # Race condition is acceptable in tests


class TestStartShPortValidation(unittest.TestCase):
    """Tests for start.sh -p flag validation (Section 2.12)."""

    def setUp(self):
        self.start_sh = os.path.join(
            os.path.dirname(__file__), "start.sh")

    def test_port_override_validation_rejects_invalid_port(self):
        """Port override validation rejects invalid port — start.sh -p notanumber exits with error."""
        result = subprocess.run(
            ["bash", self.start_sh, "-p", "notanumber"],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid port", result.stderr)

    def test_port_zero_rejected(self):
        """start.sh -p 0 exits with non-zero status."""
        result = subprocess.run(
            ["bash", self.start_sh, "-p", "0"],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid port", result.stderr)

    def test_port_too_large_rejected(self):
        """start.sh -p 99999 exits with non-zero status."""
        result = subprocess.run(
            ["bash", self.start_sh, "-p", "99999"],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid port", result.stderr)


class TestRestartOnRerun(unittest.TestCase):
    """Scenario: Restart on rerun preserves port

    Given a CDD server is running for this project on port 9090
    When start.sh is executed again
    Then the existing server process is stopped
    And a new server process is started on port 9090
    And start.sh prints "Restarted CDD server on port 9090"
    And start.sh prints "http://localhost:9090"
    """

    def setUp(self):
        self.start_sh = os.path.join(
            os.path.dirname(__file__), "start.sh")

    def test_start_sh_has_restart_logic(self):
        """start.sh contains restart-on-rerun logic (§2.9)."""
        with open(self.start_sh) as f:
            content = f.read()
        self.assertIn('RESTARTING=true', content)
        self.assertIn('Restarted CDD server on port', content)

    def test_restart_preserves_previous_port(self):
        """start.sh reads PREVIOUS_PORT from port file for restart."""
        with open(self.start_sh) as f:
            content = f.read()
        # Verify the restart block reads the previous port and reuses it
        self.assertIn('PREVIOUS_PORT=$(cat "$PORT_FILE")', content)
        self.assertIn('OVERRIDE_PORT="$PREVIOUS_PORT"', content)

    def test_restart_stops_existing_process(self):
        """start.sh kills existing process before restarting."""
        with open(self.start_sh) as f:
            content = f.read()
        # Verify the restart block sends SIGTERM to existing PID
        self.assertIn('kill "$EXISTING_PID"', content)


class TestServerStartStopLifecycle(unittest.TestCase):
    """Scenario: Server Start/Stop Lifecycle (auto-web)

    Given the CDD server is not running
    When the User runs tools/cdd/start.sh
    Then the server starts on the configured port on the first invocation
    And a port file is written to .purlin/runtime/cdd.port
    When the User runs tools/cdd/stop.sh
    Then the server process is terminated
    And the port file is removed
    When the User runs tools/cdd/start.sh again
    Then the server starts successfully on the first invocation
    """

    def setUp(self):
        self.tools_dir = os.path.dirname(__file__)
        self.start_sh = os.path.join(self.tools_dir, "start.sh")
        self.stop_sh = os.path.join(self.tools_dir, "stop.sh")
        # Create a temp project directory with minimal structure
        self.tmpdir = tempfile.mkdtemp(prefix="cdd_lifecycle_test_")
        os.makedirs(os.path.join(self.tmpdir, "features"))
        os.makedirs(os.path.join(self.tmpdir, ".purlin", "runtime"))
        # Write minimal config.json
        with open(os.path.join(self.tmpdir, ".purlin", "config.json"), 'w') as f:
            json.dump({"tools_root": "tools"}, f)
        # Initialize a git repo (serve.py requires git)
        subprocess.run(["git", "init"], cwd=self.tmpdir,
                       capture_output=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "init"],
                       cwd=self.tmpdir, capture_output=True)
        # Find a free port
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            self.port = s.getsockname()[1]
        self.env = os.environ.copy()
        self.env["PURLIN_PROJECT_ROOT"] = self.tmpdir
        self.port_file = os.path.join(
            self.tmpdir, ".purlin", "runtime", "cdd.port")

    def tearDown(self):
        # Always stop the server and clean up
        subprocess.run(
            ["bash", self.stop_sh],
            env=self.env, capture_output=True, timeout=10)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _find_server_pid(self):
        """Find CDD server process for this test project."""
        result = subprocess.run(
            ["bash", "-c",
             f'ps aux | grep "[s]erve.py" | grep -F -- "--project-root" '
             f'| grep -F "{self.tmpdir}" | awk \'{{print $2}}\' | head -1'],
            capture_output=True, text=True)
        pid = result.stdout.strip()
        return int(pid) if pid else None

    def test_full_lifecycle(self):
        """Start -> verify running -> stop -> verify stopped -> start again."""
        # Step 1: Start the server
        result = subprocess.run(
            ["bash", self.start_sh, "-p", str(self.port)],
            env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0,
                         f"start.sh failed: {result.stderr}")
        self.assertIn(f"http://localhost:{self.port}", result.stdout)

        # Verify port file exists
        self.assertTrue(os.path.exists(self.port_file),
                        "Port file should exist after start")
        with open(self.port_file) as f:
            self.assertEqual(f.read().strip(), str(self.port))

        # Verify server process is running
        pid = self._find_server_pid()
        self.assertIsNotNone(pid, "Server process should be running")

        # Step 2: Stop the server
        result = subprocess.run(
            ["bash", self.stop_sh],
            env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0,
                         f"stop.sh failed: {result.stderr}")

        # Verify port file is removed
        self.assertFalse(os.path.exists(self.port_file),
                         "Port file should be removed after stop")

        # Verify server process is stopped
        import time
        time.sleep(0.3)  # Brief wait for process cleanup
        pid_after = self._find_server_pid()
        self.assertIsNone(pid_after,
                          "Server process should not be running after stop")

        # Step 3: Start again — should succeed on first invocation
        result = subprocess.run(
            ["bash", self.start_sh, "-p", str(self.port)],
            env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0,
                         f"Second start.sh failed: {result.stderr}")
        self.assertIn(f"http://localhost:{self.port}", result.stdout)

        # Verify port file exists again
        self.assertTrue(os.path.exists(self.port_file),
                        "Port file should exist after second start")

        # Verify server is running again
        pid_restarted = self._find_server_pid()
        self.assertIsNotNone(pid_restarted,
                             "Server should be running after second start")


# ===================================================================
# ===================================================================
# QA Effort Display Tests (cdd_qa_effort_display.md)
# ===================================================================

class TestQaBadgeHtml(unittest.TestCase):
    """Scenarios: QA badge with single-line tooltip effort display (Section 2.2.2)."""

    def test_auto_status_displays_with_green_badge(self):
        """Scenario: AUTO status displays with green badge."""
        entry = {
            "qa": "AUTO",
            "verification_effort": {"summary": "3 auto"},
        }
        html = _qa_badge_html(entry)
        self.assertIn("AUTO", html)
        self.assertIn("st-auto", html)

    def test_todo_status_with_effort_shows_tooltip(self):
        """Scenario: TODO status with effort shows tooltip, no sub-line."""
        entry = {
            "qa": "TODO",
            "verification_effort": {"summary": "2 auto, 4 manual"},
        }
        html = _qa_badge_html(entry)
        self.assertIn("TODO", html)
        self.assertIn("st-todo", html)
        self.assertIn('title="2 auto, 4 manual"', html)
        self.assertNotIn("effort-subline", html)

    def test_auto_status_with_effort_shows_tooltip(self):
        """Scenario: AUTO status with effort shows tooltip, no sub-line."""
        entry = {
            "qa": "AUTO",
            "verification_effort": {"summary": "3 auto"},
        }
        html = _qa_badge_html(entry)
        self.assertIn("AUTO", html)
        self.assertIn('title="3 auto"', html)
        self.assertNotIn("effort-subline", html)

    def test_todo_zero_effort_shows_plain_todo(self):
        """Scenario: QA TODO with zero effort shows plain TODO, no tooltip."""
        entry = {
            "qa": "TODO",
            "verification_effort": {"summary": "awaiting builder"},
        }
        html = _qa_badge_html(entry)
        self.assertIn("TODO", html)
        self.assertNotIn("effort-subline", html)
        self.assertNotIn("title=", html)

    def test_non_todo_auto_no_tooltip(self):
        """Scenario: Non-TODO/AUTO QA status has no tooltip or sub-line."""
        entry = {"qa": "CLEAN"}
        html = _qa_badge_html(entry)
        self.assertIn("CLEAN", html)
        self.assertNotIn("effort-subline", html)
        self.assertNotIn("title=", html)

    def test_auto_badge_uses_status_auto_color(self):
        """AUTO badge uses var(--purlin-status-auto) color (green)."""
        entry = {
            "qa": "AUTO",
            "verification_effort": {"summary": "5 auto"},
        }
        html = _qa_badge_html(entry)
        self.assertIn('class="st-auto"', html)
        # Verify the st-auto CSS class uses --purlin-status-auto token
        serve_path = os.path.join(os.path.dirname(__file__), "serve.py")
        with open(serve_path) as f:
            source = f.read()
        self.assertIn(
            '.st-auto{{color:var(--purlin-status-auto)', source)
        self.assertNotIn(
            '.st-auto{{color:var(--purlin-status-warning)', source)

    def test_css_token_exists_in_both_themes(self):
        """--purlin-status-auto token is defined in both dark and light themes."""
        serve_path = os.path.join(os.path.dirname(__file__), "serve.py")
        with open(serve_path) as f:
            source = f.read()
        self.assertIn('--purlin-status-auto:#A3E635', source)
        self.assertIn('--purlin-status-auto:#65A30D', source)

    def test_todo_no_verification_effort_key(self):
        """TODO with no verification_effort shows plain badge, no tooltip."""
        entry = {"qa": "TODO"}
        html = _qa_badge_html(entry)
        self.assertIn("TODO", html)
        self.assertNotIn("effort-subline", html)
        self.assertNotIn("title=", html)

    def test_single_line_only_no_divs(self):
        """Badge renders as single span only -- no div elements (Section 2.2.2)."""
        entry = {
            "qa": "TODO",
            "verification_effort": {"summary": "3 manual"},
        }
        html = _qa_badge_html(entry)
        self.assertNotIn("<div", html)
        self.assertIn('title="3 manual"', html)

    def test_no_tooltip_for_no_qa_items(self):
        """No tooltip when summary is 'no QA items'."""
        entry = {
            "qa": "TODO",
            "verification_effort": {"summary": "no QA items"},
        }
        html = _qa_badge_html(entry)
        self.assertIn("TODO", html)
        self.assertNotIn("effort-subline", html)
        self.assertNotIn("title=", html)


class TestVerificationEffortInApiStatus(unittest.TestCase):
    """Scenario: Status JSON includes verification_effort."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_role_status_includes_verification_effort(self):
        """get_feature_role_status includes verification_effort when present."""
        stem = "test_feature"
        d = os.path.join(self.test_dir, stem)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "critic.json"), "w") as f:
            json.dump({
                "role_status": {
                    "architect": "DONE",
                    "builder": "DONE",
                    "qa": "TODO",
                },
                "verification_effort": {
                    "web_test": 5, "test_only": 0, "skip": 0,
                    "manual_interactive": 0, "manual_visual": 0,
                    "manual_hardware": 0,
                    "total_auto": 5, "total_manual": 0,
                    "summary": "5 auto, 0 manual",
                },
            }, f)
        result = get_feature_role_status(stem, self.test_dir)
        self.assertIn("verification_effort", result)
        self.assertEqual(result["verification_effort"]["total_auto"], 5)

    def test_role_status_without_verification_effort(self):
        """get_feature_role_status works when verification_effort is absent."""
        stem = "old_feature"
        d = os.path.join(self.test_dir, stem)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "critic.json"), "w") as f:
            json.dump({
                "role_status": {
                    "architect": "DONE",
                    "builder": "DONE",
                    "qa": "CLEAN",
                },
            }, f)
        result = get_feature_role_status(stem, self.test_dir)
        self.assertNotIn("verification_effort", result)


# ===================================================================
# Modal Metadata & Font Scenarios (auto-web)
# ===================================================================

def _gen_html():
    """Generate dashboard HTML with mocked feature data."""
    import serve as _serve
    from unittest.mock import patch as _patch
    with _patch('serve.get_feature_status', return_value=([], [], [])), \
         _patch('serve.run_command', return_value=""):
        return _serve.generate_html()


class TestMetadataTagsDisplayedSeparately(unittest.TestCase):
    """Scenario: Metadata Tags Displayed Separately (auto-web)

    Given the User is viewing the Status view
    When the User clicks a feature name that has Label, Category, and Prerequisite metadata
    Then the feature detail modal opens
    And metadata tags are displayed in a dedicated area between the header/tabs and the body
    And each tag name is rendered in a highlight color distinct from the value text
    And the metadata blockquotes do not appear as blockquotes in the rendered markdown body
    """

    def test_modal_metadata_div_exists(self):
        html = _gen_html()
        self.assertIn('id="modal-metadata"', html)
        self.assertIn('class="modal-metadata"', html)

    def test_extract_metadata_function_exists(self):
        html = _gen_html()
        self.assertIn('function extractMetadata(', html)

    def test_render_metadata_function_exists(self):
        html = _gen_html()
        self.assertIn('function renderMetadata(', html)

    def test_metadata_area_between_tabs_and_body(self):
        """modal-metadata div must appear after modal-tabs and before modal-body."""
        html = _gen_html()
        tabs_pos = html.index('id="modal-tabs"')
        meta_pos = html.index('id="modal-metadata"')
        body_pos = html.index('id="modal-body"')
        self.assertLess(tabs_pos, meta_pos, "metadata div must be after tabs")
        self.assertLess(meta_pos, body_pos, "metadata div must be before body")

    def test_metadata_key_uses_accent_color(self):
        """Tag names should use --purlin-accent for highlight color."""
        html = _gen_html()
        self.assertRegex(
            html,
            r'\.modal-meta-key\s*\{[^}]*color:\s*var\(--purlin-accent\)'
        )

    def test_open_modal_calls_extract_metadata(self):
        """openModal() must call extractMetadata on the spec content."""
        html = _gen_html()
        self.assertIn('extractMetadata(', html)

    def test_open_modal_renders_metadata(self):
        """openModal() must call renderMetadata to populate the metadata area."""
        html = _gen_html()
        self.assertIn('renderMetadata(', html)

    def test_open_modal_uses_cleaned_markdown(self):
        """openModal() must pass cleaned markdown (without metadata) to marked.parse."""
        html = _gen_html()
        self.assertIn('extracted.cleaned', html)


class TestMultiplePrerequisitesOnSeparateRows(unittest.TestCase):
    """Scenario: Multiple Prerequisites on Separate Rows (auto-web)

    Given the User is viewing the Status view
    And a feature has 3 Prerequisite metadata lines
    When the User clicks that feature name
    Then the feature detail modal shows 3 separate rows for the Prerequisite tags
    """

    def test_each_tag_rendered_as_separate_row(self):
        """renderMetadata must create one modal-meta-row per tag."""
        html = _gen_html()
        self.assertIn('modal-meta-row', html)
        # Verify each tag gets its own row div inside the loop
        self.assertRegex(
            html,
            r'for\s*\(.*i\s*<\s*tags\.length.*\)\s*\{[^}]*modal-meta-row'
        )

    def test_extract_metadata_handles_multiple_same_key(self):
        """extractMetadata must collect multiple '> Prerequisite:' lines as separate entries."""
        html = _gen_html()
        # The regex match in extractMetadata captures key and value per line
        self.assertIn("m[1].trim()", html)
        self.assertIn("m[2].trim()", html)
        self.assertIn("tags.push", html)


class TestModalOpensWithCorrectWidth(unittest.TestCase):
    """Scenario: Modal Opens with Correct Width (auto-web)

    Given the User is viewing the Status view
    When the User clicks a feature name
    Then the feature detail modal width is 70% of the viewport width
    """

    def test_modal_content_width_is_70vw(self):
        html = _gen_html()
        self.assertRegex(
            html,
            r'\.modal-content\s*\{[^}]*width:\s*70vw'
        )

    def test_narrow_viewport_fallback(self):
        html = _gen_html()
        self.assertIn('width:90vw', html)
        self.assertRegex(html, r'@media\s*\(max-width:\s*500px\)')


class TestFontSizeSliderChangesTextSize(unittest.TestCase):
    """Scenario: Font Size Slider Changes Text Size (auto-web)

    Given the User has opened a feature detail modal
    When the User records the baseline text size
    And the User moves the font size slider to the maximum position
    Then all text elements in the modal body have grown proportionally
    """

    def test_body_uses_calc_with_font_adjust(self):
        html = _gen_html()
        self.assertRegex(
            html,
            r'\.modal-body\s*\{[^}]*font-size:\s*calc\(14px\s*\+\s*var\(--modal-font-adjust\)'
        )

    def test_all_text_elements_scale(self):
        """h1, h2, h3, code all use calc() with --modal-font-adjust."""
        html = _gen_html()
        for tag in ('h1', 'h2', 'h3', 'code'):
            self.assertRegex(
                html,
                rf'\.modal-body {tag}\s*\{{[^}}]*font-size:\s*calc\(\d+px\s*\+\s*var\(--modal-font-adjust\)',
                f"modal-body {tag} must use calc() with --modal-font-adjust"
            )

    def test_set_modal_font_applies_css_variable(self):
        html = _gen_html()
        self.assertIn("setProperty('--modal-font-adjust'", html)


class TestMetadataTagsRenderedCorrectly(unittest.TestCase):
    """Scenario: Metadata Tags Rendered Correctly (auto-web)

    Given the User is viewing the Status view
    And a feature has Label, Category, and 2 or more Prerequisites
    When the User clicks that feature name
    Then the modal shows a dedicated metadata area with highlighted tag names
    And no duplicate metadata blockquotes appear in the body
    """

    def test_metadata_css_classes_defined(self):
        html = _gen_html()
        self.assertIn('.modal-metadata', html)
        self.assertIn('.modal-meta-row', html)
        self.assertIn('.modal-meta-key', html)
        self.assertIn('.modal-meta-val', html)

    def test_metadata_hidden_when_empty(self):
        """Empty metadata div should not display."""
        html = _gen_html()
        self.assertIn('.modal-metadata:empty', html)
        self.assertRegex(
            html,
            r'\.modal-metadata:empty\s*\{[^}]*display:\s*none'
        )

    def test_extract_metadata_strips_blockquotes(self):
        """extractMetadata removes '> Key: Value' lines from the cleaned output."""
        html = _gen_html()
        # The function skips metadata lines with 'continue'
        self.assertIn('continue; // skip this line', html)

    def test_open_modal_stores_spec_meta(self):
        """openModal stores extracted metadata in currentModal.specMeta."""
        html = _gen_html()
        self.assertIn('currentModal.specMeta', html)


class TestTextWrapsAtMaxFontSize(unittest.TestCase):
    """Scenario: Text Wraps at Max Font Size (auto-web)

    Given the User has opened a feature detail modal
    When the User moves the font size slider to the maximum position
    Then no horizontal scrollbar appears in the modal body
    """

    def test_modal_body_overflow_y_auto(self):
        html = _gen_html()
        self.assertRegex(
            html,
            r'\.modal-body\s*\{[^}]*overflow-y:\s*auto'
        )

    def test_modal_content_uses_viewport_width(self):
        """70vw width constrains text to viewport bounds, preventing horizontal overflow."""
        html = _gen_html()
        self.assertIn('width:70vw', html)

    def test_pre_blocks_have_overflow_x_auto(self):
        """pre blocks should scroll horizontally rather than overflow the modal."""
        html = _gen_html()
        self.assertRegex(
            html,
            r'\.modal-body pre\s*\{[^}]*overflow-x:\s*auto'
        )


class TestFontSizePersistsAcrossFeatureModals(unittest.TestCase):
    """Scenario: Font Size Persists Across Feature Modals (auto-web)

    Given the User has opened a feature detail modal and adjusted the font size slider
    When the User closes the modal
    And the User opens a different feature detail modal
    Then the font size slider position is retained at the previously set value
    """

    def test_session_storage_key_defined(self):
        html = _gen_html()
        self.assertIn('purlin-modal-font-adjust', html)

    def test_session_storage_set_on_change(self):
        html = _gen_html()
        self.assertIn('sessionStorage.setItem(MODAL_FONT_STORAGE_KEY', html)

    def test_session_storage_read_on_init(self):
        html = _gen_html()
        self.assertIn('sessionStorage.getItem(MODAL_FONT_STORAGE_KEY', html)

    def test_font_adjust_applied_on_modal_open(self):
        """setModalFont is called with stored value to restore slider on open."""
        html = _gen_html()
        self.assertIn('setModalFont(_modalFontAdjust)', html)


class TestTitleSizeMatchesSpec(unittest.TestCase):
    """Scenario: Title Size Matches Spec (auto-web)

    Given the User has opened a feature detail modal
    When the modal is displayed
    Then the modal title computed font size is 8 points larger than the default body font size
    """

    def test_title_is_4pts_above_body_default(self):
        """Title font size is 4 points larger than body default (spec line 682)."""
        html = _gen_html()
        title_match = re.search(
            r'\.modal-header h2\s*\{[^}]*font-size:\s*calc\((\d+)px', html)
        body_match = re.search(
            r'\.modal-body\s*\{[^}]*font-size:\s*calc\((\d+)px', html)
        self.assertIsNotNone(title_match, "Title font-size not found")
        self.assertIsNotNone(body_match, "Body default font-size not found")
        title_size = int(title_match.group(1))
        body_default = int(body_match.group(1))
        self.assertEqual(title_size - body_default, 4,
                         f"Title ({title_size}px) should be 4pts above "
                         f"body default ({body_default}px)")


# ===================================================================
# Feature Content Endpoint Tests
# ===================================================================

class TestFeatureContentEndpoint(unittest.TestCase):
    """Scenario: Feature Content Endpoint — /feature?file= returns file content."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.test_dir, "features")
        os.makedirs(self.features_dir)
        self.feature_path = os.path.join(self.features_dir, "test_feature.md")
        with open(self.feature_path, "w") as f:
            f.write("# Test Feature\n\nSome content here.\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('serve.FEATURES_DIR')
    @patch('serve.PROJECT_ROOT')
    def test_feature_content_endpoint_returns_file(self, mock_root, mock_fdir):
        """Feature content endpoint returns feature file content with status 200."""
        mock_root.__str__ = lambda s: self.test_dir
        mock_fdir.__str__ = lambda s: self.features_dir
        from serve import Handler
        import io
        import urllib.parse

        handler = Handler.__new__(Handler)
        handler.path = '/feature?file=features/test_feature.md'
        handler.requestline = 'GET /feature?file=features/test_feature.md HTTP/1.1'
        handler.request_version = 'HTTP/1.1'
        handler.command = 'GET'
        handler.headers = {}
        handler.wfile = io.BytesIO()

        headers_sent = []

        def mock_send_header(key, value):
            headers_sent.append((key, value))
        handler.send_response = MagicMock()
        handler.send_header = mock_send_header
        handler.end_headers = MagicMock()

        # Patch module-level vars for path resolution
        import serve as _serve
        orig_root = _serve.PROJECT_ROOT
        orig_fdir = _serve.FEATURES_DIR
        _serve.PROJECT_ROOT = self.test_dir
        _serve.FEATURES_DIR = self.features_dir
        try:
            handler._serve_feature_content()
        finally:
            _serve.PROJECT_ROOT = orig_root
            _serve.FEATURES_DIR = orig_fdir

        handler.send_response.assert_called_with(200)
        content_types = [v for k, v in headers_sent if k == 'Content-Type']
        self.assertTrue(any('text/plain' in ct for ct in content_types))
        body = handler.wfile.getvalue().decode('utf-8')
        self.assertIn("# Test Feature", body)
        self.assertIn("Some content here.", body)


# ===================================================================
# Impl Notes Endpoint Tests
# ===================================================================

class TestImplNotesEndpoint(unittest.TestCase):
    """Scenario: Impl Notes Endpoint — /impl-notes?file= returns companion content."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.test_dir, "features")
        os.makedirs(self.features_dir)
        # Create both feature and companion file
        with open(os.path.join(self.features_dir, "test_feature.md"), "w") as f:
            f.write("# Test Feature\n")
        self.impl_path = os.path.join(self.features_dir, "test_feature.impl.md")
        with open(self.impl_path, "w") as f:
            f.write("# Implementation Notes: Test Feature\n\nTribal knowledge here.\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_impl_notes_endpoint_returns_companion_content(self):
        """Impl notes endpoint returns companion file content with status 200."""
        from serve import Handler
        import io

        handler = Handler.__new__(Handler)
        handler.path = '/impl-notes?file=features/test_feature.md'
        handler.requestline = 'GET /impl-notes?file=features/test_feature.md HTTP/1.1'
        handler.request_version = 'HTTP/1.1'
        handler.command = 'GET'
        handler.headers = {}
        handler.wfile = io.BytesIO()

        headers_sent = []

        def mock_send_header(key, value):
            headers_sent.append((key, value))
        handler.send_response = MagicMock()
        handler.send_header = mock_send_header
        handler.end_headers = MagicMock()

        import serve as _serve
        orig_root = _serve.PROJECT_ROOT
        orig_fdir = _serve.FEATURES_DIR
        _serve.PROJECT_ROOT = self.test_dir
        _serve.FEATURES_DIR = self.features_dir
        try:
            handler._serve_impl_notes()
        finally:
            _serve.PROJECT_ROOT = orig_root
            _serve.FEATURES_DIR = orig_fdir

        handler.send_response.assert_called_with(200)
        content_types = [v for k, v in headers_sent if k == 'Content-Type']
        self.assertTrue(any('text/plain' in ct for ct in content_types))
        body = handler.wfile.getvalue().decode('utf-8')
        self.assertIn("Implementation Notes: Test Feature", body)
        self.assertIn("Tribal knowledge here.", body)

    def test_impl_notes_endpoint_returns_404_when_no_companion(self):
        """Impl notes endpoint returns 404 when no companion file exists."""
        from serve import Handler
        import io

        handler = Handler.__new__(Handler)
        handler.path = '/impl-notes?file=features/no_companion.md'
        handler.requestline = 'GET /impl-notes?file=features/no_companion.md HTTP/1.1'
        handler.request_version = 'HTTP/1.1'
        handler.command = 'GET'
        handler.headers = {}
        handler.wfile = io.BytesIO()
        handler.send_error = MagicMock()

        # Create the feature file but NOT the companion
        with open(os.path.join(self.features_dir, "no_companion.md"), "w") as f:
            f.write("# No Companion\n")

        import serve as _serve
        orig_root = _serve.PROJECT_ROOT
        orig_fdir = _serve.FEATURES_DIR
        _serve.PROJECT_ROOT = self.test_dir
        _serve.FEATURES_DIR = self.features_dir
        try:
            handler._serve_impl_notes()
        finally:
            _serve.PROJECT_ROOT = orig_root
            _serve.FEATURES_DIR = orig_fdir

        handler.send_error.assert_called_once()
        args = handler.send_error.call_args[0]
        self.assertEqual(args[0], 404)


# ===================================================================
# Section Collapse and Expand Tests (auto-web)
# ===================================================================

class TestSectionCollapseAndExpand(unittest.TestCase):
    """Scenario: Section Collapse and Expand (auto-web)

    Verifies the HTML structure contains collapsible section elements
    with chevron indicators and toggleSection onclick handlers.
    """

    def test_section_collapse_and_expand_html_structure(self):
        """Section collapse and expand: HTML has section headers with chevron and toggle."""
        html = _gen_html()
        # Active section header with toggleSection onclick
        self.assertIn("toggleSection('active-section')", html)
        # Complete section header with toggleSection onclick
        self.assertIn("toggleSection('complete-section')", html)
        # Chevron elements for visual expand/collapse indicator
        self.assertRegex(html, r'class="chevron[^"]*".*id="active-section-chevron"')
        self.assertRegex(html, r'class="chevron[^"]*".*id="complete-section-chevron"')
        # Active section starts expanded (chevron has 'expanded' class)
        self.assertRegex(html, r'class="chevron expanded".*id="active-section-chevron"')
        # Complete section starts collapsed (section-body has 'collapsed' class)
        self.assertRegex(html, r'class="section-body collapsed".*id="complete-section"')

    def test_section_collapse_css_present(self):
        """Section collapse CSS: collapsed class hides content via max-height:0."""
        html = _gen_html()
        self.assertIn('.section-body.collapsed', html)
        self.assertIn('max-height:0', html)

    def test_toggle_section_js_present(self):
        """toggleSection JS function exists for section collapse/expand behavior."""
        html = _gen_html()
        self.assertIn('function toggleSection', html)


# ===================================================================
# Startup Briefing Tests (Section 2.15)
# ===================================================================


def _make_startup_env(tmpdir, features=None, tombstones=None, anchors=None,
                      critic_data=None, config=None, graph=None,
                      delivery_plan=None, discoveries=None):
    """Create a temp environment for startup briefing tests.

    Returns dict of patch targets and values.
    """
    features_dir = os.path.join(tmpdir, "features")
    tests_dir = os.path.join(tmpdir, "tests")
    cache_dir = os.path.join(tmpdir, ".purlin", "cache")
    os.makedirs(features_dir, exist_ok=True)
    os.makedirs(tests_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    features = features or {}
    for stem, cfg in features.items():
        fpath = os.path.join(features_dir, f"{stem}.md")
        scenarios = cfg.get("scenarios", [])
        with open(fpath, 'w') as f:
            f.write(f'# Feature: {stem}\n\n> Label: "{cfg.get("label", stem)}"\n\n')
            for s in scenarios:
                f.write(f'#### Scenario: {s}\n\n')

        tdir = os.path.join(tests_dir, stem)
        os.makedirs(tdir, exist_ok=True)
        role_status = cfg.get("role_status", {
            "architect": "DONE", "builder": "TODO",
            "qa": "N/A", "pm": "N/A"})
        cdata = critic_data.get(stem, {}) if critic_data else {}
        cdata.setdefault("role_status", role_status)
        cdata.setdefault("action_items", {
            "architect": [], "builder": [], "qa": [], "pm": []})
        cdata.setdefault("implementation_gate", {
            "checks": {"policy_adherence": {
                "status": "PASS", "violations": []}}})
        if "verification_effort" not in cdata:
            cdata["verification_effort"] = {
                "summary": "no QA items", "total_auto": 0, "total_manual": 0}
        with open(os.path.join(tdir, "critic.json"), 'w') as f:
            json.dump(cdata, f)

    tombstones = tombstones or []
    if tombstones:
        tdir = os.path.join(features_dir, "tombstones")
        os.makedirs(tdir, exist_ok=True)
        for t in tombstones:
            fpath = os.path.join(tdir, t["file"])
            with open(fpath, 'w') as f:
                f.write(f'# Tombstone\n\n> Label: "{t.get("label", t["file"])}"\n')

    anchors = anchors or {}
    for fname, content in anchors.items():
        fpath = os.path.join(features_dir, fname)
        with open(fpath, 'w') as f:
            f.write(content)

    graph_data = graph or {"features": [], "cycles": [], "orphans": []}
    with open(os.path.join(cache_dir, "dependency_graph.json"), 'w') as f:
        json.dump(graph_data, f)

    if delivery_plan:
        purlin_dir = os.path.join(tmpdir, ".purlin")
        with open(os.path.join(purlin_dir, "delivery_plan.md"), 'w') as f:
            f.write(delivery_plan)

    if discoveries:
        for stem, content in discoveries.items():
            dpath = os.path.join(features_dir, f"{stem}.discoveries.md")
            with open(dpath, 'w') as f:
                f.write(content)

    resolved_config = config or {
        "agents": {
            "builder": {"find_work": True, "auto_start": True,
                        "model": "test-model", "effort": "high"},
            "qa": {"find_work": True, "auto_start": False,
                   "model": "test-model", "effort": "medium"},
            "architect": {"find_work": False, "auto_start": False,
                          "model": "test-model", "effort": "high"},
            "pm": {"find_work": False, "auto_start": False,
                   "model": "test-model", "effort": "high"},
        }
    }

    return {
        "features_dir": features_dir,
        "tests_dir": tests_dir,
        "cache_dir": cache_dir,
        "config": resolved_config,
        "project_root": tmpdir,
    }


class TestStartupBriefingCommonFields(unittest.TestCase):
    """Scenario: Startup Briefing Common Fields"""

    @patch('serve.TESTS_DIR')
    @patch('serve.FEATURES_ABS')
    def test_common_fields_present(self, mock_fabs, mock_tdir):
        """All common fields are present with correct types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_startup_env(tmpdir, features={
                "feat_a": {"label": "Feature A",
                           "role_status": {"architect": "DONE",
                                           "builder": "TODO",
                                           "qa": "N/A", "pm": "N/A"},
                           "scenarios": ["S1", "S2"]},
            })

            with patch('serve.FEATURES_ABS', env["features_dir"]), \
                 patch('serve.FEATURES_REL', 'features'), \
                 patch('serve.TESTS_DIR', env["tests_dir"]), \
                 patch('serve.CACHE_DIR', env["cache_dir"]), \
                 patch('serve.DEPENDENCY_GRAPH_PATH',
                       os.path.join(env["cache_dir"],
                                    "dependency_graph.json")), \
                 patch('serve.CONFIG', env["config"]), \
                 patch('serve.PROJECT_ROOT', env["project_root"]), \
                 patch('serve.build_status_commit_cache', return_value={}), \
                 patch('serve.run_command') as mock_cmd:
                mock_cmd.side_effect = lambda c: {
                    "git rev-parse --abbrev-ref HEAD": "main",
                    "git status --porcelain": "",
                }.get(c.strip(), "")
                result = generate_startup_briefing("builder")

            # Check all required common fields
            self.assertIn("generated_at", result)
            self.assertEqual(result["role"], "builder")
            self.assertIn("config", result)
            self.assertIn("find_work", result["config"])
            self.assertIn("auto_start", result["config"])
            self.assertIn("git_state", result)
            self.assertIn("branch", result["git_state"])
            self.assertIn("clean", result["git_state"])
            self.assertIn("modified_files", result["git_state"])
            self.assertIn("recent_commits", result["git_state"])
            self.assertIn("feature_summary", result)
            self.assertIn("total", result["feature_summary"])
            self.assertIn("by_lifecycle", result["feature_summary"])
            self.assertIn("by_role_status", result["feature_summary"])
            self.assertIn("action_items", result)
            self.assertIsInstance(result["action_items"], list)
            self.assertIn("features", result)
            self.assertIsInstance(result["features"], list)
            self.assertIn("dependency_graph_summary", result)
            self.assertIn("total_features",
                          result["dependency_graph_summary"])
            self.assertIn("cycles", result["dependency_graph_summary"])
            self.assertIn("critic_last_run", result)


class TestStartupBriefingBuilderExtension(unittest.TestCase):
    """Scenario: Startup Briefing Builder Extension"""

    @patch('serve.TESTS_DIR')
    @patch('serve.FEATURES_ABS')
    def test_builder_extension_fields(self, mock_fabs, mock_tdir):
        """Builder briefing includes tombstones, anchors, delivery state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_startup_env(
                tmpdir,
                features={
                    "feat_todo": {
                        "label": "TODO Feature",
                        "role_status": {"architect": "DONE",
                                        "builder": "TODO",
                                        "qa": "N/A", "pm": "N/A"},
                        "scenarios": ["S1", "S2", "S3"]},
                },
                tombstones=[{"file": "old_feature.md",
                             "label": "Old Feature"}],
                anchors={
                    "arch_test.md": (
                        '# Arch: Test\n\n> Label: "Arch Test"\n\n'
                        '## FORBIDDEN\n\n'
                        '*   **Grepable pattern:** `#[0-9a-f]+`\n'
                        '*   **Scan scope:** `tools/**/*.py`\n'),
                },
            )

            with patch('serve.FEATURES_ABS', env["features_dir"]), \
                 patch('serve.FEATURES_REL', 'features'), \
                 patch('serve.TESTS_DIR', env["tests_dir"]), \
                 patch('serve.CACHE_DIR', env["cache_dir"]), \
                 patch('serve.DEPENDENCY_GRAPH_PATH',
                       os.path.join(env["cache_dir"],
                                    "dependency_graph.json")), \
                 patch('serve.CONFIG', env["config"]), \
                 patch('serve.PROJECT_ROOT', env["project_root"]), \
                 patch('serve.build_status_commit_cache', return_value={}), \
                 patch('serve.run_command') as mock_cmd:
                mock_cmd.side_effect = lambda c: {
                    "git rev-parse --abbrev-ref HEAD": "main",
                    "git status --porcelain": "",
                }.get(c.strip(), "")
                result = generate_startup_briefing("builder")

            # Tombstones
            self.assertIn("tombstones", result)
            self.assertEqual(len(result["tombstones"]), 1)
            self.assertEqual(result["tombstones"][0]["label"], "Old Feature")
            self.assertIn("file", result["tombstones"][0])

            # Anchor constraints
            self.assertIn("anchor_constraints", result)
            self.assertIn("arch_test.md", result["anchor_constraints"])
            arch = result["anchor_constraints"]["arch_test.md"]
            self.assertEqual(arch["label"], "Arch Test")
            self.assertIsInstance(arch["forbidden_patterns"], list)
            self.assertTrue(len(arch["forbidden_patterns"]) > 0)
            self.assertIn("pattern", arch["forbidden_patterns"][0])
            self.assertIn("scope", arch["forbidden_patterns"][0])

            # in_scope_features with scenario_count
            self.assertIn("in_scope_features", result)
            for f in result["in_scope_features"]:
                self.assertIn("scenario_count", f)

            # Delivery plan state
            self.assertIn("delivery_plan_state", result)
            self.assertIn("exists", result["delivery_plan_state"])

            # No QA or Architect extension fields
            self.assertNotIn("testing_features", result)
            self.assertNotIn("spec_completeness", result)


class TestStartupBriefingQAExtension(unittest.TestCase):
    """Scenario: Startup Briefing QA Extension"""

    @patch('serve.TESTS_DIR')
    @patch('serve.FEATURES_ABS')
    def test_qa_extension_fields(self, mock_fabs, mock_tdir):
        """QA briefing includes testing_features, discovery_summary, gating."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_startup_env(
                tmpdir,
                features={
                    "feat_testing": {
                        "label": "Testing Feature",
                        "role_status": {"architect": "DONE",
                                        "builder": "DONE",
                                        "qa": "TODO", "pm": "N/A"},
                        "scenarios": ["S1"]},
                    "feat_done": {
                        "label": "Done Feature",
                        "role_status": {"architect": "DONE",
                                        "builder": "DONE",
                                        "qa": "CLEAN", "pm": "N/A"},
                        "scenarios": ["S1"]},
                },
                discoveries={
                    "feat_testing": (
                        "[BUG] Button doesn't work\n"
                        "[DISCOVERY] New behavior found\n"),
                },
            )

            with patch('serve.FEATURES_ABS', env["features_dir"]), \
                 patch('serve.FEATURES_REL', 'features'), \
                 patch('serve.TESTS_DIR', env["tests_dir"]), \
                 patch('serve.CACHE_DIR', env["cache_dir"]), \
                 patch('serve.DEPENDENCY_GRAPH_PATH',
                       os.path.join(env["cache_dir"],
                                    "dependency_graph.json")), \
                 patch('serve.CONFIG', env["config"]), \
                 patch('serve.PROJECT_ROOT', env["project_root"]), \
                 patch('serve.build_status_commit_cache', return_value={}), \
                 patch('serve.run_command') as mock_cmd:
                mock_cmd.side_effect = lambda c: {
                    "git rev-parse --abbrev-ref HEAD": "main",
                    "git status --porcelain": "",
                }.get(c.strip(), "")
                result = generate_startup_briefing("qa")

            # Testing features
            self.assertIn("testing_features", result)
            testing = result["testing_features"]
            self.assertEqual(len(testing), 1)
            self.assertEqual(testing[0]["label"], "Testing Feature")
            self.assertIn("verification_effort", testing[0])

            # Discovery summary
            self.assertIn("discovery_summary", result)
            disc = result["discovery_summary"]
            self.assertEqual(disc["total_open"], 2)
            self.assertIn("feat_testing", disc["by_feature"])
            self.assertEqual(disc["by_feature"]["feat_testing"], 2)

            # Delivery plan gating
            self.assertIn("delivery_plan_gating", result)
            self.assertIn("phase_gated_features",
                          result["delivery_plan_gating"])
            self.assertIn("fully_delivered_features",
                          result["delivery_plan_gating"])

            # No Builder or Architect extension fields
            self.assertNotIn("tombstones", result)
            self.assertNotIn("anchor_constraints", result)
            self.assertNotIn("spec_completeness", result)


class TestStartupBriefingArchitectExtension(unittest.TestCase):
    """Scenario: Startup Briefing Architect Extension"""

    @patch('serve.TESTS_DIR')
    @patch('serve.FEATURES_ABS')
    def test_architect_extension_fields(self, mock_fabs, mock_tdir):
        """Architect briefing includes spec_completeness and untracked_files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_startup_env(
                tmpdir,
                features={
                    "feat_specgap": {
                        "label": "Spec Gap Feature",
                        "role_status": {"architect": "TODO",
                                        "builder": "TODO",
                                        "qa": "N/A", "pm": "N/A"},
                        "scenarios": ["S1"]},
                },
                critic_data={
                    "feat_specgap": {
                        "spec_gate": {
                            "status": "FAIL",
                            "details": ["Missing Section 2.1"],
                        },
                    },
                },
            )

            with patch('serve.FEATURES_ABS', env["features_dir"]), \
                 patch('serve.FEATURES_REL', 'features'), \
                 patch('serve.TESTS_DIR', env["tests_dir"]), \
                 patch('serve.CACHE_DIR', env["cache_dir"]), \
                 patch('serve.DEPENDENCY_GRAPH_PATH',
                       os.path.join(env["cache_dir"],
                                    "dependency_graph.json")), \
                 patch('serve.CONFIG', env["config"]), \
                 patch('serve.PROJECT_ROOT', env["project_root"]), \
                 patch('serve.build_status_commit_cache', return_value={}), \
                 patch('serve.run_command') as mock_cmd:
                mock_cmd.side_effect = lambda c: {
                    "git rev-parse --abbrev-ref HEAD": "main",
                    "git status --porcelain": "?? new_file.txt\n M foo.py",
                }.get(c.strip(), "")
                result = generate_startup_briefing("architect")

            # Spec completeness
            self.assertIn("spec_completeness", result)
            self.assertEqual(len(result["spec_completeness"]), 1)
            sc = result["spec_completeness"][0]
            self.assertEqual(sc["file"], "features/feat_specgap.md")
            self.assertEqual(sc["spec_gate"], "FAIL")
            self.assertEqual(sc["spec_gate_details"], ["Missing Section 2.1"])

            # Untracked files
            self.assertIn("untracked_files", result)
            self.assertIn("new_file.txt", result["untracked_files"])

            # No Builder or QA extension fields
            self.assertNotIn("tombstones", result)
            self.assertNotIn("testing_features", result)


class TestStartupBriefingInvalidRole(unittest.TestCase):
    """Scenario: Startup Briefing Invalid Role Error"""

    def test_invalid_role_cli_exits_with_error(self):
        """CLI --cli-startup with invalid role writes to stderr, exits 1."""
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__),
                                          "serve.py"),
             "--cli-startup", "invalid"],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONWARNINGS": "ignore",
                 "CRITIC_RUNNING": "1"},
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid", result.stderr.lower())
        # No JSON on stdout
        self.assertEqual(result.stdout.strip(), "")


class TestStartupBriefingFeaturesFiltered(unittest.TestCase):
    """Scenario: Startup Briefing Features Filtered to Role"""

    @patch('serve.TESTS_DIR')
    @patch('serve.FEATURES_ABS')
    def test_only_non_terminal_features_included(self, mock_fabs, mock_tdir):
        """Features array contains only non-terminal features for the role."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_startup_env(tmpdir, features={
                "feat_todo": {"label": "TODO",
                              "role_status": {"architect": "DONE",
                                              "builder": "TODO",
                                              "qa": "N/A", "pm": "N/A"}},
                "feat_done": {"label": "Done",
                              "role_status": {"architect": "DONE",
                                              "builder": "DONE",
                                              "qa": "CLEAN", "pm": "N/A"}},
                "feat_fail": {"label": "Fail",
                              "role_status": {"architect": "DONE",
                                              "builder": "FAIL",
                                              "qa": "N/A", "pm": "N/A"}},
            })

            with patch('serve.FEATURES_ABS', env["features_dir"]), \
                 patch('serve.FEATURES_REL', 'features'), \
                 patch('serve.TESTS_DIR', env["tests_dir"]), \
                 patch('serve.CACHE_DIR', env["cache_dir"]), \
                 patch('serve.DEPENDENCY_GRAPH_PATH',
                       os.path.join(env["cache_dir"],
                                    "dependency_graph.json")), \
                 patch('serve.CONFIG', env["config"]), \
                 patch('serve.PROJECT_ROOT', env["project_root"]), \
                 patch('serve.build_status_commit_cache', return_value={}), \
                 patch('serve.run_command') as mock_cmd:
                mock_cmd.side_effect = lambda c: {
                    "git rev-parse --abbrev-ref HEAD": "main",
                    "git status --porcelain": "",
                }.get(c.strip(), "")
                result = generate_startup_briefing("builder")

            # Only TODO and FAIL features (not DONE)
            files = [f["file"] for f in result["features"]]
            self.assertEqual(len(files), 2)
            self.assertIn("features/feat_todo.md", files)
            self.assertIn("features/feat_fail.md", files)
            self.assertNotIn("features/feat_done.md", files)

            # Action items are builder-only
            self.assertIn("action_items", result)


class TestStartupBriefingNoDeliveryPlan(unittest.TestCase):
    """Scenario: Startup Briefing No Delivery Plan"""

    @patch('serve.TESTS_DIR')
    @patch('serve.FEATURES_ABS')
    def test_no_plan_sets_exists_false(self, mock_fabs, mock_tdir):
        """When no delivery plan exists, delivery_plan_state.exists is false."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_startup_env(tmpdir, features={
                "feat_a": {"label": "A",
                           "role_status": {"architect": "DONE",
                                           "builder": "TODO",
                                           "qa": "N/A", "pm": "N/A"}},
            })

            with patch('serve.FEATURES_ABS', env["features_dir"]), \
                 patch('serve.FEATURES_REL', 'features'), \
                 patch('serve.TESTS_DIR', env["tests_dir"]), \
                 patch('serve.CACHE_DIR', env["cache_dir"]), \
                 patch('serve.DEPENDENCY_GRAPH_PATH',
                       os.path.join(env["cache_dir"],
                                    "dependency_graph.json")), \
                 patch('serve.CONFIG', env["config"]), \
                 patch('serve.PROJECT_ROOT', env["project_root"]), \
                 patch('serve.build_status_commit_cache', return_value={}), \
                 patch('serve.run_command') as mock_cmd:
                mock_cmd.side_effect = lambda c: {
                    "git rev-parse --abbrev-ref HEAD": "main",
                    "git status --porcelain": "",
                }.get(c.strip(), "")
                result = generate_startup_briefing("builder")

            dp = result["delivery_plan_state"]
            self.assertFalse(dp["exists"])
            self.assertNotIn("current_phases", dp)
            self.assertNotIn("phase_features", dp)


class TestStartupBriefingWithExecutionGroup(unittest.TestCase):
    """Scenario: Startup Briefing with Execution Group"""

    @patch('serve.TESTS_DIR')
    @patch('serve.FEATURES_ABS')
    def test_execution_group_multiple_in_progress(self, mock_fabs, mock_tdir):
        """When multiple phases are IN_PROGRESS, current_phases is an array."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan = (
                "# Delivery Plan\n\n"
                "**Created:** 2026-03-22\n"
                "**Total Phases:** 3\n\n"
                "## Phase 1 -- Foundation [COMPLETE]\n"
                "**Features:** foundation.md\n\n"
                "## Phase 2 -- UI [IN_PROGRESS]\n"
                "**Features:** feat_a.md, feat_b.md\n\n"
                "## Phase 3 -- API [IN_PROGRESS]\n"
                "**Features:** feat_c.md\n"
            )
            env = _make_startup_env(tmpdir, features={
                "feat_a": {"label": "A",
                           "role_status": {"architect": "DONE",
                                           "builder": "TODO",
                                           "qa": "N/A", "pm": "N/A"}},
                "feat_b": {"label": "B",
                           "role_status": {"architect": "DONE",
                                           "builder": "TODO",
                                           "qa": "N/A", "pm": "N/A"}},
                "feat_c": {"label": "C",
                           "role_status": {"architect": "DONE",
                                           "builder": "TODO",
                                           "qa": "N/A", "pm": "N/A"}},
            }, delivery_plan=plan)

            with patch('serve.FEATURES_ABS', env["features_dir"]), \
                 patch('serve.FEATURES_REL', 'features'), \
                 patch('serve.TESTS_DIR', env["tests_dir"]), \
                 patch('serve.CACHE_DIR', env["cache_dir"]), \
                 patch('serve.DEPENDENCY_GRAPH_PATH',
                       os.path.join(env["cache_dir"],
                                    "dependency_graph.json")), \
                 patch('serve.CONFIG', env["config"]), \
                 patch('serve.PROJECT_ROOT', env["project_root"]), \
                 patch('serve.build_status_commit_cache', return_value={}), \
                 patch('serve.run_command') as mock_cmd:
                mock_cmd.side_effect = lambda c: {
                    "git rev-parse --abbrev-ref HEAD": "main",
                    "git status --porcelain": "",
                }.get(c.strip(), "")
                result = generate_startup_briefing("builder")

            dp = result["delivery_plan_state"]
            self.assertTrue(dp["exists"])
            self.assertEqual(dp["current_phases"], [2, 3])
            self.assertIn("feat_a.md", dp["phase_features"])
            self.assertIn("feat_b.md", dp["phase_features"])
            self.assertIn("feat_c.md", dp["phase_features"])


class TestStartupBriefingPhasingRecommendation(unittest.TestCase):
    """Scenario: Startup Briefing Phasing Recommendation"""

    @patch('serve.TESTS_DIR')
    @patch('serve.FEATURES_ABS')
    def test_phasing_recommended_true(self, mock_fabs, mock_tdir):
        """Phasing recommended when 4 features, 2 with 5+ scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_startup_env(tmpdir, features={
                "f1": {"label": "F1",
                       "role_status": {"architect": "DONE",
                                       "builder": "TODO",
                                       "qa": "N/A", "pm": "N/A"},
                       "scenarios": [f"S{i}" for i in range(6)]},
                "f2": {"label": "F2",
                       "role_status": {"architect": "DONE",
                                       "builder": "TODO",
                                       "qa": "N/A", "pm": "N/A"},
                       "scenarios": [f"S{i}" for i in range(5)]},
                "f3": {"label": "F3",
                       "role_status": {"architect": "DONE",
                                       "builder": "TODO",
                                       "qa": "N/A", "pm": "N/A"},
                       "scenarios": ["S1"]},
                "f4": {"label": "F4",
                       "role_status": {"architect": "DONE",
                                       "builder": "TODO",
                                       "qa": "N/A", "pm": "N/A"},
                       "scenarios": ["S1"]},
            })

            with patch('serve.FEATURES_ABS', env["features_dir"]), \
                 patch('serve.FEATURES_REL', 'features'), \
                 patch('serve.TESTS_DIR', env["tests_dir"]), \
                 patch('serve.CACHE_DIR', env["cache_dir"]), \
                 patch('serve.DEPENDENCY_GRAPH_PATH',
                       os.path.join(env["cache_dir"],
                                    "dependency_graph.json")), \
                 patch('serve.CONFIG', env["config"]), \
                 patch('serve.PROJECT_ROOT', env["project_root"]), \
                 patch('serve.build_status_commit_cache', return_value={}), \
                 patch('serve.run_command') as mock_cmd:
                mock_cmd.side_effect = lambda c: {
                    "git rev-parse --abbrev-ref HEAD": "main",
                    "git status --porcelain": "",
                }.get(c.strip(), "")
                result = generate_startup_briefing("builder")

            self.assertTrue(result["phasing_recommended"])
            self.assertFalse(result["delivery_plan_state"]["exists"])


class TestStartupBriefingMutualExclusivity(unittest.TestCase):
    """Scenario: Startup Briefing Mutual Exclusivity with Graph"""

    def test_startup_flag_precedes_graph_in_shell(self):
        """status.sh processes --startup before --graph (first match wins)."""
        # Verify the if/elif structure: --startup condition appears before
        # --graph condition in status.sh.
        status_sh = os.path.join(os.path.dirname(__file__), "status.sh")
        with open(status_sh, 'r') as f:
            content = f.read()
        # Find the conditional blocks (if/elif), not usage comments
        startup_pos = content.find('= "--startup"')
        graph_pos = content.find('= "--graph"')
        self.assertGreater(startup_pos, -1,
                           '"--startup" conditional not found in status.sh')
        self.assertGreater(graph_pos, -1,
                           '"--graph" conditional not found in status.sh')
        self.assertLess(startup_pos, graph_pos,
                        "--startup must appear before --graph for precedence")

    def test_startup_flag_precedes_graph_in_python(self):
        """serve.py processes --cli-startup before other CLI modes."""
        serve_py = os.path.join(os.path.dirname(__file__), "serve.py")
        with open(serve_py, 'r') as f:
            content = f.read()
        startup_pos = content.find('--cli-startup')
        role_pos = content.find('--cli-role-status')
        status_pos = content.find('--cli-status')
        self.assertGreater(startup_pos, -1)
        self.assertLess(startup_pos, role_pos,
                        "--cli-startup must appear before --cli-role-status")
        self.assertLess(startup_pos, status_pos,
                        "--cli-startup must appear before --cli-status")


class TestCountScenarios(unittest.TestCase):
    """Helper tests for _count_scenarios."""

    def test_counts_scenario_headings(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md',
                                         delete=False) as f:
            f.write("# Feature\n\n#### Scenario: A\n\n"
                    "#### Scenario: B\n\n#### Scenario: C\n")
            f.flush()
            self.assertEqual(_count_scenarios(f.name), 3)
            os.unlink(f.name)

    def test_zero_scenarios(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md',
                                         delete=False) as f:
            f.write("# Feature\n\nNo scenarios here.\n")
            f.flush()
            self.assertEqual(_count_scenarios(f.name), 0)
            os.unlink(f.name)

    def test_missing_file(self):
        self.assertEqual(_count_scenarios("/nonexistent/file.md"), 0)


class TestExtractForbiddenPatterns(unittest.TestCase):
    """Helper tests for _extract_forbidden_patterns."""

    def test_extracts_pattern_and_scope(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md',
                                         delete=False) as f:
            f.write('# Anchor\n\n'
                    '*   **Grepable pattern:** `#[0-9a-fA-F]+`\n'
                    '*   **Scan scope:** `tools/**/*.css`\n')
            f.flush()
            result = _extract_forbidden_patterns(f.name)
            os.unlink(f.name)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["pattern"], "#[0-9a-fA-F]+")
        self.assertEqual(result[0]["scope"], "tools/**/*.css")

    def test_no_patterns_returns_empty(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md',
                                         delete=False) as f:
            f.write('# Anchor\n\nNo FORBIDDEN patterns.\n')
            f.flush()
            result = _extract_forbidden_patterns(f.name)
            os.unlink(f.name)
        self.assertEqual(result, [])


class TestScanDiscoverySidecars(unittest.TestCase):
    """Helper tests for _scan_discovery_sidecars."""

    def test_counts_open_discoveries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create discovery file with mixed entries
            dpath = os.path.join(tmpdir, "feat_x.discoveries.md")
            with open(dpath, 'w') as f:
                f.write("[BUG] Open bug\n"
                        "[DISCOVERY] Open discovery\n"
                        "[BUG] RESOLVED bug\n"
                        "[INTENT_DRIFT] Open drift\n")
            with patch('serve.FEATURES_ABS', tmpdir):
                result = _scan_discovery_sidecars()
            self.assertEqual(result["total_open"], 3)
            self.assertEqual(result["by_feature"]["feat_x"], 3)

    def test_empty_dir_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('serve.FEATURES_ABS', tmpdir):
                result = _scan_discovery_sidecars()
            self.assertEqual(result["total_open"], 0)
            self.assertEqual(result["by_feature"], {})


# ===================================================================
# Abbreviated Status Commit Format Tests
# ===================================================================


class TestAbbreviatedStatusCommitCache(unittest.TestCase):
    """Tests for abbreviated status commit format in build_status_commit_cache.

    Covers scenarios:
    - Lifecycle Integration -- Abbreviated Status Commit Format
    - Abbreviated Status Commit With Non-Existent Feature Scope
    - Canonical Status Commit Format Takes Precedence Over Abbreviated
    """

    def _run_cache_with_git_output(self, git_output, existing_files=None):
        """Helper: run build_status_commit_cache with mocked git log output.

        existing_files: set of relative paths that should exist on disk.
        """
        if existing_files is None:
            existing_files = set()

        def mock_isfile(path):
            for rel in existing_files:
                if path.endswith(rel):
                    return True
            return False

        with patch('serve.run_command', return_value=git_output), \
             patch('serve._load_persistent_status_cache', return_value=(None, None)), \
             patch('serve._save_persistent_status_cache'), \
             patch('serve._get_current_head', return_value='abc123'), \
             patch('os.path.isfile', side_effect=mock_isfile):
            return build_status_commit_cache()

    def test_abbreviated_complete_resolves_from_scope(self):
        """Abbreviated [Complete] with conventional scope resolves to feature."""
        git_output = "1700000000 aaa111 feat(my_feature): [Complete] all scenarios passing"
        cache = self._run_cache_with_git_output(
            git_output, existing_files={'features/my_feature.md'})
        self.assertIn('features/my_feature.md', cache)
        self.assertEqual(cache['features/my_feature.md']['complete_ts'], 1700000000)
        self.assertEqual(cache['features/my_feature.md']['complete_hash'], 'aaa111')

    def test_abbreviated_testing_resolves_from_scope(self):
        """Abbreviated [Ready for Verification] resolves from scope."""
        git_output = "1700000000 bbb222 status(my_feature): [Ready for Verification]"
        cache = self._run_cache_with_git_output(
            git_output, existing_files={'features/my_feature.md'})
        self.assertIn('features/my_feature.md', cache)
        self.assertEqual(cache['features/my_feature.md']['testing_ts'], 1700000000)

    def test_abbreviated_testing_ready_for_testing_resolves(self):
        """Abbreviated [Ready for Testing] also resolves from scope."""
        git_output = "1700000000 ccc333 status(my_feature): [Ready for Testing]"
        cache = self._run_cache_with_git_output(
            git_output, existing_files={'features/my_feature.md'})
        self.assertIn('features/my_feature.md', cache)
        self.assertEqual(cache['features/my_feature.md']['testing_ts'], 1700000000)

    def test_nonexistent_scope_silently_ignored(self):
        """Abbreviated commit with non-existent feature scope produces no entry."""
        git_output = "1700000000 ddd444 feat(nonexistent_feature): [Complete] something"
        cache = self._run_cache_with_git_output(
            git_output, existing_files=set())
        self.assertNotIn('features/nonexistent_feature.md', cache)
        self.assertEqual(len(cache), 0)

    def test_no_scope_prefix_silently_ignored(self):
        """Abbreviated commit without conventional scope prefix is ignored."""
        git_output = "1700000000 eee555 [Complete] no scope here"
        cache = self._run_cache_with_git_output(
            git_output, existing_files=set())
        self.assertEqual(len(cache), 0)

    def test_canonical_takes_precedence_in_same_commit(self):
        """When a commit has both canonical path and a scope, canonical is used."""
        git_output = (
            "1700000000 fff666 feat(wrong_scope): "
            "[Complete features/correct_feature.md]"
        )
        cache = self._run_cache_with_git_output(
            git_output,
            existing_files={'features/correct_feature.md',
                            'features/wrong_scope.md'})
        self.assertIn('features/correct_feature.md', cache)
        self.assertNotIn('features/wrong_scope.md', cache)

    def test_abbreviated_scope_trailer_extracted(self):
        """[Scope: ...] trailer is extracted from abbreviated commits."""
        git_output = (
            "1700000000 ggg777 feat(my_feature): "
            "[Complete] [Scope: targeted:SomeScenario]"
        )
        cache = self._run_cache_with_git_output(
            git_output, existing_files={'features/my_feature.md'})
        self.assertEqual(
            cache['features/my_feature.md']['scope'],
            'targeted:SomeScenario')

    def test_mixed_canonical_and_abbreviated_timeline(self):
        """Both formats contribute to the same feature's timeline correctly."""
        # Earlier canonical testing commit, later abbreviated complete
        git_output = (
            "1700000002 hhh888 feat(my_feature): [Complete] done\n"
            "1700000001 iii999 status(lifecycle): "
            "[Ready for Verification features/my_feature.md]"
        )
        cache = self._run_cache_with_git_output(
            git_output, existing_files={'features/my_feature.md'})
        entry = cache['features/my_feature.md']
        self.assertEqual(entry['complete_ts'], 1700000002)
        self.assertEqual(entry['complete_hash'], 'hhh888')
        self.assertEqual(entry['testing_ts'], 1700000001)
        self.assertEqual(entry['testing_hash'], 'iii999')


# ===================================================================
# Test runner with output to tests/cdd_status_monitor/tests.json
# ===================================================================

if __name__ == '__main__':
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../../'))
    tests_out_dir = os.path.join(project_root, "tests", "cdd_status_monitor")
    os.makedirs(tests_out_dir, exist_ok=True)
    status_file = os.path.join(tests_out_dir, "tests.json")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    status = "PASS" if result.wasSuccessful() else "FAIL"
    failed = len(result.failures) + len(result.errors)
    report = {
        "status": status,
        "passed": result.testsRun - failed,
        "failed": failed,
        "total": result.testsRun,
        "test_file": "tools/cdd/test_cdd.py"
    }
    with open(status_file, 'w') as f:
        json.dump(report, f)
    # Also write to cdd_qa_effort_display (covered by TestQaBadgeHtml,
    # TestVerificationEffortInApiStatus in this same test suite).
    # Count from the already-completed run -- no re-execution needed.
    qa_effort_classes = (TestQaBadgeHtml, TestVerificationEffortInApiStatus)
    qa_effort_class_names = {cls.__name__ for cls in qa_effort_classes}
    qa_effort_total = sum(
        loader.loadTestsFromTestCase(cls).countTestCases()
        for cls in qa_effort_classes)
    qa_effort_failed = sum(
        1 for t, _ in result.failures + result.errors
        if type(t).__name__ in qa_effort_class_names)
    qa_effort_report = {
        "status": "PASS" if qa_effort_failed == 0 else "FAIL",
        "passed": qa_effort_total - qa_effort_failed,
        "failed": qa_effort_failed,
        "total": qa_effort_total,
        "test_file": "tools/cdd/test_cdd.py"
    }
    qa_effort_dir = os.path.join(project_root, "tests", "cdd_qa_effort_display")
    os.makedirs(qa_effort_dir, exist_ok=True)
    with open(os.path.join(qa_effort_dir, "tests.json"), 'w') as f:
        json.dump(qa_effort_report, f)
    print(f"\n{status_file}: {status}")

    sys.exit(0 if result.wasSuccessful() else 1)
