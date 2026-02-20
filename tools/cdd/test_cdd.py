"""Unit tests for the CDD Status Monitor.

Covers automated scenarios from features/cdd_status_monitor.md.
Outputs test results to tests/cdd_status_monitor/tests.json.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import json
import sys
import tempfile
import shutil
from serve import (
    get_feature_test_status,
    get_feature_role_status,
    aggregate_test_statuses,
    get_feature_status,
    COMPLETE_CAP,
    extract_label,
    generate_internal_feature_status,
    generate_api_status_json,
    _is_feature_complete,
    _feature_urgency,
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
