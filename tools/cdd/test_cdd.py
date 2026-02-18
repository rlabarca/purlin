import unittest
from unittest.mock import patch, MagicMock
import os
import json
import tempfile
import shutil
from serve import get_devops_aggregated_test_status, get_feature_status, COMPLETE_CAP

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
        
        # Mock run_command to return a timestamp that makes it COMPLETE
        # (complete_ts > test_ts and file_mod_ts <= complete_ts)
        mock_run.side_effect = lambda cmd: "2000000000" if "git log" in cmd else ""
        
        complete, testing, todo = get_feature_status("features", features_abs)
        self.assertEqual(len(complete), 15)
        self.assertEqual(len(testing), 0)
        self.assertEqual(len(todo), 0)

if __name__ == '__main__':
    unittest.main()
