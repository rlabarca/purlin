import unittest
from unittest.mock import patch, MagicMock
import os
import json
import tempfile
import shutil
from serve import (get_devops_aggregated_test_status, get_feature_status,
                    COMPLETE_CAP, extract_label, generate_feature_status_json)

class TestCDD(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.tools_dir = os.path.join(self.test_dir, "tools")
        os.makedirs(self.tools_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_aggregation_all_pass(self):
        # Create two tool dirs with PASS
        for tool in ["tool1", "tool2"]:
            d = os.path.join(self.tools_dir, tool)
            os.makedirs(d)
            with open(os.path.join(d, "test_status.json"), "w") as f:
                json.dump({"status": "PASS"}, f)
        
        status, msg = get_devops_aggregated_test_status(self.tools_dir)
        self.assertEqual(status, "PASS")
        self.assertIn("All tools nominal", msg)

    def test_aggregation_one_fail(self):
        # One PASS, one FAIL
        d1 = os.path.join(self.tools_dir, "tool_ok")
        os.makedirs(d1)
        with open(os.path.join(d1, "test_status.json"), "w") as f:
            json.dump({"status": "PASS"}, f)
            
        d2 = os.path.join(self.tools_dir, "tool_bad")
        os.makedirs(d2)
        with open(os.path.join(d2, "test_status.json"), "w") as f:
            json.dump({"status": "FAIL"}, f)

        status, msg = get_devops_aggregated_test_status(self.tools_dir)
        self.assertEqual(status, "FAIL")
        self.assertIn("tool_bad", msg)

    def test_aggregation_malformed_json(self):
        d = os.path.join(self.tools_dir, "tool_corrupt")
        os.makedirs(d)
        with open(os.path.join(d, "test_status.json"), "w") as f:
            f.write("{ invalid json")
            
        status, msg = get_devops_aggregated_test_status(self.tools_dir)
        self.assertEqual(status, "FAIL")
        self.assertIn("tool_corrupt", msg)

    def test_aggregation_missing_files_ignored(self):
        # Tool dir with NO test_status.json should be ignored
        d = os.path.join(self.tools_dir, "tool_no_tests")
        os.makedirs(d)
        
        status, msg = get_devops_aggregated_test_status(self.tools_dir)
        self.assertEqual(status, "UNKNOWN")

    @patch('serve.run_command')
    def test_feature_status_complete_capping(self, mock_run):
        # Mock git log to return timestamps for 15 "complete" features
        features_abs = os.path.join(self.test_dir, "features")
        os.makedirs(features_abs)
        for i in range(15):
            fname = f"feat_{i:02d}.md"
            with open(os.path.join(features_abs, fname), "w") as f:
                f.write("# Test")
        
        # Mock run_command: return high timestamp for Complete, empty for Ready
        # (complete_ts > test_ts and file_mod_ts <= complete_ts)
        def mock_git(cmd):
            if "Complete" in cmd:
                return "2000000000"
            return ""
        mock_run.side_effect = mock_git
        
        complete, testing, todo = get_feature_status("features", features_abs)
        self.assertEqual(len(complete), 15)
        self.assertEqual(len(testing), 0)
        self.assertEqual(len(todo), 0)

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

    @patch('serve.IS_META', False)
    @patch('serve.DOMAINS', [
        {"label": "Application", "features_rel": "features",
         "features_abs": "/tmp/test_features", "test_mode": "auto"},
        {"label": "Agentic Core", "features_rel": "core/features",
         "features_abs": "/tmp/test_features", "test_mode": "devops_aggregate",
         "tools_dir": "/tmp/test_tools"},
    ])
    @patch('serve.get_feature_status')
    @patch('serve.get_domain_test_status')
    @patch('serve.extract_label')
    def test_json_structure_both_domains(self, mock_label, mock_test, mock_features):
        mock_features.return_value = ([("feat_a.md", 100)], ["feat_b.md"], ["feat_c.md"])
        mock_test.return_value = ("PASS", "All good")
        mock_label.return_value = "Test Label"

        data = generate_feature_status_json()

        self.assertIn("generated_at", data)
        self.assertIn("domains", data)
        self.assertIn("application", data["domains"])
        self.assertIn("agentic", data["domains"])

        for domain_key in ["application", "agentic"]:
            domain = data["domains"][domain_key]
            self.assertEqual(domain["test_status"], "PASS")
            self.assertIn("features", domain)
            self.assertEqual(len(domain["features"]["complete"]), 1)
            self.assertEqual(len(domain["features"]["testing"]), 1)
            self.assertEqual(len(domain["features"]["todo"]), 1)
            # Each entry must have file and label keys
            for entry in domain["features"]["todo"]:
                self.assertIn("file", entry)
                self.assertIn("label", entry)

    @patch('serve.IS_META', True)
    @patch('serve.DOMAINS', [
        {"label": "Agentic Core", "features_rel": "./features",
         "features_abs": "/tmp/test_features", "test_mode": "devops_aggregate",
         "tools_dir": "/tmp/test_tools"},
    ])
    @patch('serve.get_feature_status')
    @patch('serve.get_domain_test_status')
    @patch('serve.extract_label')
    def test_meta_mode_mirrors_domains(self, mock_label, mock_test, mock_features):
        mock_features.return_value = ([], [], ["feat.md"])
        mock_test.return_value = ("UNKNOWN", "No tests")
        mock_label.return_value = "Label"

        data = generate_feature_status_json()

        self.assertIn("application", data["domains"])
        self.assertIn("agentic", data["domains"])
        self.assertEqual(data["domains"]["application"], data["domains"]["agentic"])

    @patch('serve.IS_META', False)
    @patch('serve.DOMAINS', [
        {"label": "Application", "features_rel": "features",
         "features_abs": "/tmp/test_features", "test_mode": "auto"},
    ])
    @patch('serve.get_feature_status')
    @patch('serve.get_domain_test_status')
    @patch('serve.extract_label')
    def test_arrays_sorted_by_file(self, mock_label, mock_test, mock_features):
        # Return features in non-alphabetical order
        mock_features.return_value = (
            [("z_feat.md", 300), ("a_feat.md", 100), ("m_feat.md", 200)],
            ["z_test.md", "a_test.md"],
            ["z_todo.md", "a_todo.md"],
        )
        mock_test.return_value = ("PASS", "OK")
        mock_label.return_value = "Label"

        data = generate_feature_status_json()
        domain = data["domains"]["application"]

        for status_key in ["complete", "testing", "todo"]:
            items = domain["features"][status_key]
            files = [item["file"] for item in items]
            self.assertEqual(files, sorted(files),
                             f"{status_key} array not sorted by file path")

    @patch('serve.IS_META', False)
    @patch('serve.DOMAINS', [
        {"label": "Application", "features_rel": "features",
         "features_abs": "/tmp/test_features", "test_mode": "auto"},
    ])
    @patch('serve.get_feature_status')
    @patch('serve.get_domain_test_status')
    @patch('serve.extract_label')
    def test_json_keys_sorted(self, mock_label, mock_test, mock_features):
        mock_features.return_value = ([], [], ["feat.md"])
        mock_test.return_value = ("PASS", "OK")
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
        mock_gen.return_value = {"domains": {}, "generated_at": "2026-01-01T00:00:00Z"}
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
        self.assertIn("domains", data)

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
    unittest.main()
