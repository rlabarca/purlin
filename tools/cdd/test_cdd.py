"""Unit tests for the CDD Status Monitor.

Covers automated scenarios from features/cdd_status_monitor.md.
Outputs test results to tests/cdd_status_monitor/tests.json.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import json
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
    COMPLETE_CAP,
    extract_label,
    generate_internal_feature_status,
    generate_api_status_json,
    _is_feature_complete,
    _feature_urgency,
    strip_discoveries_section,
    spec_content_unchanged,
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
            },
        })
        result = get_feature_role_status("my_feature", self.test_dir)
        self.assertEqual(result["architect"], "DONE")
        self.assertEqual(result["builder"], "DONE")
        self.assertEqual(result["qa"], "CLEAN")

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
    @patch('serve.run_command')
    def test_feature_status_complete_capping(self, mock_run):
        test_dir = tempfile.mkdtemp()
        try:
            features_abs = os.path.join(test_dir, "features")
            os.makedirs(features_abs)
            for i in range(15):
                fname = f"feat_{i:02d}.md"
                with open(os.path.join(features_abs, fname), "w") as f:
                    f.write("# Test")

            def mock_git(cmd):
                if "Complete" in cmd:
                    return "2000000000"
                return ""
            mock_run.side_effect = mock_git

            complete, testing, todo = get_feature_status(
                "features", features_abs)
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
                 "builder": "DONE", "qa": "CLEAN"}
        self.assertTrue(_is_feature_complete(entry))

    def test_builder_todo_is_not_complete(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "TODO", "qa": "CLEAN"}
        self.assertFalse(_is_feature_complete(entry))

    def test_qa_na_counts_as_complete(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "DONE", "qa": "N/A"}
        self.assertTrue(_is_feature_complete(entry))

    def test_no_critic_is_not_complete(self):
        entry = {"file": "f.md"}
        self.assertFalse(_is_feature_complete(entry))

    def test_builder_fail_is_not_complete(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "FAIL", "qa": "CLEAN"}
        self.assertFalse(_is_feature_complete(entry))


class TestFeatureUrgency(unittest.TestCase):
    """Tests for urgency sorting in Active section."""

    def test_fail_is_most_urgent(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "FAIL", "qa": "CLEAN"}
        self.assertEqual(_feature_urgency(entry), 0)

    def test_todo_is_medium_urgent(self):
        entry = {"file": "f.md", "architect": "TODO",
                 "builder": "DONE", "qa": "N/A"}
        self.assertEqual(_feature_urgency(entry), 1)

    def test_all_done_is_least_urgent(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "DONE", "qa": "CLEAN"}
        self.assertEqual(_feature_urgency(entry), 3)

    def test_infeasible_is_most_urgent(self):
        entry = {"file": "f.md", "architect": "TODO",
                 "builder": "INFEASIBLE", "qa": "N/A"}
        self.assertEqual(_feature_urgency(entry), 0)

    def test_disputed_is_medium_urgent(self):
        entry = {"file": "f.md", "architect": "DONE",
                 "builder": "BLOCKED", "qa": "DISPUTED"}
        self.assertEqual(_feature_urgency(entry), 1)


class TestZeroQueueVerification(unittest.TestCase):
    """Scenario: Zero-Queue Verification"""

    def test_all_done_means_zero_queue(self):
        features = [
            {"file": "a.md", "architect": "DONE",
             "builder": "DONE", "qa": "CLEAN"},
            {"file": "b.md", "architect": "DONE",
             "builder": "DONE", "qa": "N/A"},
        ]
        all_complete = all(_is_feature_complete(f) for f in features)
        self.assertTrue(all_complete)

    def test_one_todo_fails_zero_queue(self):
        features = [
            {"file": "a.md", "architect": "DONE",
             "builder": "DONE", "qa": "CLEAN"},
            {"file": "b.md", "architect": "TODO",
             "builder": "DONE", "qa": "N/A"},
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

            def mock_git(cmd):
                if "Complete" in cmd and "%ct" in cmd:
                    return "2000000000"  # status commit timestamp
                if "Complete" in cmd and "%H" in cmd:
                    return "abc123"  # commit hash
                if "Ready for" in cmd:
                    return ""
                if "git show abc123:" in cmd:
                    return spec_content  # content at status commit
                return ""
            mock_run.side_effect = mock_git

            import serve
            orig_root = serve.PROJECT_ROOT
            serve.PROJECT_ROOT = test_dir
            try:
                complete, testing, todo = get_feature_status(
                    "features", features_abs)
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

            def mock_git(cmd):
                if "Complete" in cmd:
                    return ""
                if "Ready for" in cmd and "%ct" in cmd:
                    return "2000000000"
                if "Ready for" in cmd and "%H" in cmd:
                    return "def456"
                if "git show def456:" in cmd:
                    return spec_content
                return ""
            mock_run.side_effect = mock_git

            import serve
            orig_root = serve.PROJECT_ROOT
            serve.PROJECT_ROOT = test_dir
            try:
                complete, testing, todo = get_feature_status(
                    "features", features_abs)
                self.assertEqual(len(testing), 1)
                self.assertEqual(testing[0], "test.md")
                self.assertEqual(len(todo), 0)
            finally:
                serve.PROJECT_ROOT = orig_root
        finally:
            shutil.rmtree(test_dir)


class TestLifecycleResetOnSpecChange(unittest.TestCase):
    """Scenario: Lifecycle Reset When Spec Content Changes

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

            def mock_git(cmd):
                if "Complete" in cmd and "%ct" in cmd:
                    return "2000000000"
                if "Complete" in cmd and "%H" in cmd:
                    return "abc123"
                if "Ready for" in cmd:
                    return ""
                if "git show abc123:" in cmd:
                    return committed_content
                return ""
            mock_run.side_effect = mock_git

            import serve
            orig_root = serve.PROJECT_ROOT
            serve.PROJECT_ROOT = test_dir
            try:
                complete, testing, todo = get_feature_status(
                    "features", features_abs)
                self.assertEqual(len(todo), 1)
                self.assertEqual(todo[0], "test.md")
                self.assertEqual(len(complete), 0)
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
        self.cache_dir = os.path.join(self.test_dir, ".purlin", "cache")
        os.makedirs(self.cache_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_includes_delivery_phase_when_plan_exists(self):
        """Given a delivery plan with Phase 1 COMPLETE, Phase 2 IN_PROGRESS,
        Phase 3 PENDING, the response includes delivery_phase with current 2
        and total 3."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 — Foundation [COMPLETE]\n"
            "**Features:** feat_a\n\n"
            "## Phase 2 — Core [IN_PROGRESS]\n"
            "**Features:** feat_b\n\n"
            "## Phase 3 — Polish [PENDING]\n"
            "**Features:** feat_c\n"
        )
        with open(os.path.join(self.cache_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        import serve
        orig_cache = serve.CACHE_DIR
        serve.CACHE_DIR = self.cache_dir
        try:
            result = get_delivery_phase()
            self.assertIsNotNone(result)
            self.assertEqual(result["current"], 2)
            self.assertEqual(result["total"], 3)
        finally:
            serve.CACHE_DIR = orig_cache

    def test_delivery_phase_in_full_api_response(self):
        """Integration: delivery_phase appears in generate_api_status_json."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 — Foundation [COMPLETE]\n\n"
            "## Phase 2 — Core [IN_PROGRESS]\n\n"
            "## Phase 3 — Polish [PENDING]\n"
        )
        with open(os.path.join(self.cache_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        features_dir = os.path.join(self.test_dir, "features")
        tests_dir = os.path.join(self.test_dir, "tests")
        os.makedirs(features_dir)
        os.makedirs(tests_dir)

        with open(os.path.join(features_dir, "test.md"), "w") as f:
            f.write('# Feature\n\n> Label: "Test"\n')

        import serve
        orig_cache = serve.CACHE_DIR
        orig_abs = serve.FEATURES_ABS
        orig_tests = serve.TESTS_DIR
        serve.CACHE_DIR = self.cache_dir
        serve.FEATURES_ABS = features_dir
        serve.TESTS_DIR = tests_dir
        try:
            data = generate_api_status_json()
            self.assertIn("delivery_phase", data)
            self.assertEqual(data["delivery_phase"]["current"], 2)
            self.assertEqual(data["delivery_phase"]["total"], 3)
        finally:
            serve.CACHE_DIR = orig_cache
            serve.FEATURES_ABS = orig_abs
            serve.TESTS_DIR = orig_tests

    def test_first_pending_is_current(self):
        """When Phase 1 COMPLETE and Phase 2 PENDING, current = 2."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 — Foundation [COMPLETE]\n\n"
            "## Phase 2 — Core [PENDING]\n"
        )
        with open(os.path.join(self.cache_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        import serve
        orig_cache = serve.CACHE_DIR
        serve.CACHE_DIR = self.cache_dir
        try:
            result = get_delivery_phase()
            self.assertIsNotNone(result)
            self.assertEqual(result["current"], 2)
            self.assertEqual(result["total"], 2)
        finally:
            serve.CACHE_DIR = orig_cache


class TestDeliveryPhaseOmittedWhenNoPlan(unittest.TestCase):
    """Scenario: Delivery Phase Omitted When No Plan"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.test_dir, ".purlin", "cache")
        os.makedirs(self.cache_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_no_plan_returns_none(self):
        """No delivery_plan.md exists -> get_delivery_phase returns None."""
        import serve
        orig_cache = serve.CACHE_DIR
        serve.CACHE_DIR = self.cache_dir
        try:
            result = get_delivery_phase()
            self.assertIsNone(result)
        finally:
            serve.CACHE_DIR = orig_cache

    def test_no_plan_omits_from_api(self):
        """No delivery_plan.md -> delivery_phase not in API response."""
        features_dir = os.path.join(self.test_dir, "features")
        tests_dir = os.path.join(self.test_dir, "tests")
        os.makedirs(features_dir)
        os.makedirs(tests_dir)

        with open(os.path.join(features_dir, "test.md"), "w") as f:
            f.write('# Feature\n\n> Label: "Test"\n')

        import serve
        orig_cache = serve.CACHE_DIR
        orig_abs = serve.FEATURES_ABS
        orig_tests = serve.TESTS_DIR
        serve.CACHE_DIR = self.cache_dir
        serve.FEATURES_ABS = features_dir
        serve.TESTS_DIR = tests_dir
        try:
            data = generate_api_status_json()
            self.assertNotIn("delivery_phase", data)
        finally:
            serve.CACHE_DIR = orig_cache
            serve.FEATURES_ABS = orig_abs
            serve.TESTS_DIR = orig_tests

    def test_all_phases_complete_returns_none(self):
        """All phases COMPLETE -> delivery_phase omitted."""
        plan_content = (
            "# Delivery Plan\n\n"
            "## Phase 1 — Foundation [COMPLETE]\n\n"
            "## Phase 2 — Core [COMPLETE]\n"
        )
        with open(os.path.join(self.cache_dir, "delivery_plan.md"), "w") as f:
            f.write(plan_content)

        import serve
        orig_cache = serve.CACHE_DIR
        serve.CACHE_DIR = self.cache_dir
        try:
            result = get_delivery_phase()
            self.assertIsNone(result)
        finally:
            serve.CACHE_DIR = orig_cache


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
            finally:
                serve.FEATURES_ABS = orig_abs
                serve.TESTS_DIR = orig_tests
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
        """--cli-graph outputs valid JSON with features, cycles, orphans arrays."""
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
    with open(status_file, 'w') as f:
        json.dump({
            "status": status,
            "tests": result.testsRun,
            "failures": len(result.failures) + len(result.errors),
            "tool": "cdd",
            "runner": "unittest"
        }, f)
    print(f"\n{status_file}: {status}")

    sys.exit(0 if result.wasSuccessful() else 1)
