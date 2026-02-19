import unittest
from unittest.mock import patch, MagicMock
import os
import json
import sys
import tempfile
import shutil
from serve import (get_feature_test_status, get_feature_critic_status,
                    aggregate_test_statuses,
                    get_feature_status, COMPLETE_CAP, extract_label,
                    generate_feature_status_json)


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
        self.assertEqual(get_feature_test_status("my_feature", self.test_dir), "PASS")

    def test_fail_status(self):
        self._write_tests_json("my_feature", {"status": "FAIL"})
        self.assertEqual(get_feature_test_status("my_feature", self.test_dir), "FAIL")

    def test_missing_file_returns_none(self):
        self.assertIsNone(get_feature_test_status("nonexistent", self.test_dir))

    def test_malformed_json_returns_fail(self):
        self._write_raw("bad_feature", "{ invalid json")
        self.assertEqual(get_feature_test_status("bad_feature", self.test_dir), "FAIL")

    def test_missing_status_field_returns_fail(self):
        self._write_tests_json("no_status", {"tests": 5})
        self.assertEqual(get_feature_test_status("no_status", self.test_dir), "FAIL")

    def test_extra_metadata_ignored(self):
        self._write_tests_json("detailed", {"status": "PASS", "tests": 10, "failures": 0})
        self.assertEqual(get_feature_test_status("detailed", self.test_dir), "PASS")


class TestPerFeatureCriticStatus(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _write_critic_json(self, feature_stem, data):
        d = os.path.join(self.test_dir, feature_stem)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "critic.json"), "w") as f:
            json.dump(data, f)

    def _write_raw(self, feature_stem, content):
        d = os.path.join(self.test_dir, feature_stem)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "critic.json"), "w") as f:
            f.write(content)

    def test_critic_pass_status(self):
        self._write_critic_json("my_feature", {
            "spec_gate": {"status": "PASS"},
            "implementation_gate": {"status": "PASS"}
        })
        self.assertEqual(get_feature_critic_status("my_feature", self.test_dir), "PASS")

    def test_critic_warn_status(self):
        self._write_critic_json("my_feature", {
            "spec_gate": {"status": "WARN"},
            "implementation_gate": {"status": "PASS"}
        })
        self.assertEqual(get_feature_critic_status("my_feature", self.test_dir), "WARN")

    def test_critic_fail_status(self):
        self._write_critic_json("my_feature", {
            "spec_gate": {"status": "PASS"},
            "implementation_gate": {"status": "FAIL"}
        })
        self.assertEqual(get_feature_critic_status("my_feature", self.test_dir), "FAIL")

    def test_critic_missing_file_returns_none(self):
        self.assertIsNone(get_feature_critic_status("nonexistent", self.test_dir))

    def test_critic_malformed_json_returns_fail(self):
        self._write_raw("bad_feature", "{ invalid json")
        self.assertEqual(get_feature_critic_status("bad_feature", self.test_dir), "FAIL")


class TestAggregateTestStatuses(unittest.TestCase):
    def test_all_pass(self):
        self.assertEqual(aggregate_test_statuses(["PASS", "PASS"]), "PASS")

    def test_one_fail(self):
        self.assertEqual(aggregate_test_statuses(["PASS", "FAIL"]), "FAIL")

    def test_all_fail(self):
        self.assertEqual(aggregate_test_statuses(["FAIL", "FAIL"]), "FAIL")

    def test_empty_returns_unknown(self):
        self.assertEqual(aggregate_test_statuses([]), "UNKNOWN")


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

            complete, testing, todo = get_feature_status("features", features_abs)
            self.assertEqual(len(complete), 15)
            self.assertEqual(len(testing), 0)
            self.assertEqual(len(todo), 0)
        finally:
            shutil.rmtree(test_dir)


class TestExtractLabel(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_valid_label(self):
        path = os.path.join(self.test_dir, "test.md")
        with open(path, 'w') as f:
            f.write('# Feature: Test\n\n> Label: "My Label"\n> Category: "Test"\n')
        self.assertEqual(extract_label(path), "My Label")

    def test_label_with_colon(self):
        path = os.path.join(self.test_dir, "test.md")
        with open(path, 'w') as f:
            f.write('> Label: "Tool: CDD Monitor"\n')
        self.assertEqual(extract_label(path), "Tool: CDD Monitor")

    def test_missing_label_fallback(self):
        path = os.path.join(self.test_dir, "my_feature.md")
        with open(path, 'w') as f:
            f.write('# No label here\n')
        self.assertEqual(extract_label(path), "my_feature")

    def test_nonexistent_file_fallback(self):
        self.assertEqual(extract_label("/nonexistent/foo.md"), "foo")


class TestFeatureStatusJSON(unittest.TestCase):

    @patch('serve.FEATURES_REL', 'features')
    @patch('serve.FEATURES_ABS', '/tmp/test_features')
    @patch('serve.TESTS_DIR', '/tmp/test_tests')
    @patch('serve.get_feature_status')
    @patch('serve.get_feature_test_status')
    @patch('serve.extract_label')
    def test_json_structure_flat(self, mock_label, mock_test, mock_features):
        mock_features.return_value = ([("feat_a.md", 100)], ["feat_b.md"], ["feat_c.md"])
        mock_test.return_value = None  # No test files
        mock_label.return_value = "Test Label"

        data = generate_feature_status_json()

        self.assertIn("generated_at", data)
        self.assertIn("features", data)
        self.assertIn("test_status", data)
        self.assertNotIn("domains", data)

        self.assertEqual(data["test_status"], "UNKNOWN")
        self.assertEqual(len(data["features"]["complete"]), 1)
        self.assertEqual(len(data["features"]["testing"]), 1)
        self.assertEqual(len(data["features"]["todo"]), 1)
        for entry in data["features"]["todo"]:
            self.assertIn("file", entry)
            self.assertIn("label", entry)

    @patch('serve.FEATURES_REL', 'features')
    @patch('serve.FEATURES_ABS', '/tmp/test_features')
    @patch('serve.TESTS_DIR', '/tmp/test_tests')
    @patch('serve.get_feature_status')
    @patch('serve.get_feature_test_status')
    @patch('serve.extract_label')
    def test_per_feature_test_status_included(self, mock_label, mock_test, mock_features):
        mock_features.return_value = ([], [], ["feat_with_tests.md", "feat_no_tests.md"])
        mock_label.return_value = "Label"

        def side_effect(stem, _tests_dir):
            if stem == "feat_with_tests":
                return "PASS"
            return None
        mock_test.side_effect = side_effect

        data = generate_feature_status_json()

        todo = data["features"]["todo"]
        entry_with = next(e for e in todo if "feat_with_tests" in e["file"])
        entry_without = next(e for e in todo if "feat_no_tests" in e["file"])

        self.assertEqual(entry_with["test_status"], "PASS")
        self.assertNotIn("test_status", entry_without)
        self.assertEqual(data["test_status"], "PASS")

    @patch('serve.FEATURES_REL', 'features')
    @patch('serve.FEATURES_ABS', '/tmp/test_features')
    @patch('serve.TESTS_DIR', '/tmp/test_tests')
    @patch('serve.get_feature_status')
    @patch('serve.get_feature_test_status')
    @patch('serve.extract_label')
    def test_aggregate_fail_propagates(self, mock_label, mock_test, mock_features):
        mock_features.return_value = ([], [], ["good.md", "bad.md"])
        mock_label.return_value = "Label"

        def side_effect(stem, _tests_dir):
            return "PASS" if stem == "good" else "FAIL"
        mock_test.side_effect = side_effect

        data = generate_feature_status_json()
        self.assertEqual(data["test_status"], "FAIL")

    @patch('serve.FEATURES_REL', 'features')
    @patch('serve.FEATURES_ABS', '/tmp/test_features')
    @patch('serve.TESTS_DIR', '/tmp/test_tests')
    @patch('serve.get_feature_status')
    @patch('serve.get_feature_test_status')
    @patch('serve.extract_label')
    def test_arrays_sorted_by_file(self, mock_label, mock_test, mock_features):
        mock_features.return_value = (
            [("z_feat.md", 300), ("a_feat.md", 100), ("m_feat.md", 200)],
            ["z_test.md", "a_test.md"],
            ["z_todo.md", "a_todo.md"],
        )
        mock_test.return_value = None
        mock_label.return_value = "Label"

        data = generate_feature_status_json()

        for status_key in ["complete", "testing", "todo"]:
            items = data["features"][status_key]
            files = [item["file"] for item in items]
            self.assertEqual(files, sorted(files),
                             f"{status_key} array not sorted by file path")

    @patch('serve.FEATURES_REL', 'features')
    @patch('serve.FEATURES_ABS', '/tmp/test_features')
    @patch('serve.TESTS_DIR', '/tmp/test_tests')
    @patch('serve.get_feature_status')
    @patch('serve.get_feature_test_status')
    @patch('serve.get_feature_critic_status')
    @patch('serve.extract_label')
    def test_per_feature_critic_status_included(self, mock_label, mock_critic, mock_test, mock_features):
        mock_features.return_value = ([], [], ["feat_with_critic.md"])
        mock_label.return_value = "Label"
        mock_test.return_value = None

        def critic_side_effect(stem, _tests_dir):
            if stem == "feat_with_critic":
                return "WARN"
            return None
        mock_critic.side_effect = critic_side_effect

        data = generate_feature_status_json()
        entry = data["features"]["todo"][0]
        self.assertEqual(entry["critic_status"], "WARN")

    @patch('serve.FEATURES_REL', 'features')
    @patch('serve.FEATURES_ABS', '/tmp/test_features')
    @patch('serve.TESTS_DIR', '/tmp/test_tests')
    @patch('serve.get_feature_status')
    @patch('serve.get_feature_test_status')
    @patch('serve.get_feature_critic_status')
    @patch('serve.extract_label')
    def test_per_feature_critic_status_omitted(self, mock_label, mock_critic, mock_test, mock_features):
        mock_features.return_value = ([], [], ["feat_no_critic.md"])
        mock_label.return_value = "Label"
        mock_test.return_value = None
        mock_critic.return_value = None

        data = generate_feature_status_json()
        entry = data["features"]["todo"][0]
        self.assertNotIn("critic_status", entry)

    @patch('serve.FEATURES_REL', 'features')
    @patch('serve.FEATURES_ABS', '/tmp/test_features')
    @patch('serve.TESTS_DIR', '/tmp/test_tests')
    @patch('serve.get_feature_status')
    @patch('serve.get_feature_test_status')
    @patch('serve.get_feature_critic_status')
    @patch('serve.extract_label')
    def test_aggregate_critic_status(self, mock_label, mock_critic, mock_test, mock_features):
        mock_features.return_value = ([], [], ["good.md", "bad.md"])
        mock_label.return_value = "Label"
        mock_test.return_value = None

        def critic_side_effect(stem, _tests_dir):
            return "PASS" if stem == "good" else "FAIL"
        mock_critic.side_effect = critic_side_effect

        data = generate_feature_status_json()
        self.assertEqual(data["critic_status"], "FAIL")

    @patch('serve.FEATURES_REL', 'features')
    @patch('serve.FEATURES_ABS', '/tmp/test_features')
    @patch('serve.TESTS_DIR', '/tmp/test_tests')
    @patch('serve.get_feature_status')
    @patch('serve.get_feature_test_status')
    @patch('serve.extract_label')
    def test_json_keys_sorted(self, mock_label, mock_test, mock_features):
        mock_features.return_value = ([], [], ["feat.md"])
        mock_test.return_value = None
        mock_label.return_value = "Label"

        data = generate_feature_status_json()
        json_str = json.dumps(data, sort_keys=True)
        reparsed = json.loads(json_str)
        json_str2 = json.dumps(reparsed, sort_keys=True)
        self.assertEqual(json_str, json_str2)


class TestHandlerRouting(unittest.TestCase):
    """Tests that the HTTP handler routes /status.json to JSON and all else to HTML."""

    @patch('serve.generate_feature_status_json')
    @patch('serve.FEATURE_STATUS_PATH', '/dev/null')
    def test_status_json_route_returns_json(self, mock_gen):
        mock_gen.return_value = {"features": {}, "generated_at": "2026-01-01T00:00:00Z", "test_status": "UNKNOWN"}
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
        self.assertNotIn("domains", data)

    @patch('serve.write_feature_status_json')
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


if __name__ == '__main__':
    # Run tests and produce tests/cdd_status_monitor/tests.json
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
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
