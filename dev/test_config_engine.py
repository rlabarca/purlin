"""Tests for the Purlin config engine.

Tests the two-file config resolution strategy: config.local.json (per-user)
takes precedence over config.json (team defaults), with copy-on-first-access.
"""

import json
import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
from config_engine import find_project_root, resolve_config, update_config


class TestConfigEngine:

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.project_root, '.purlin')
        os.makedirs(self.purlin_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    @pytest.mark.proof("config-engine", "PROOF-1", "RULE-1")
    def test_find_project_root_env_var(self):
        """PURLIN_PROJECT_ROOT env var takes precedence."""
        old = os.environ.get('PURLIN_PROJECT_ROOT')
        try:
            os.environ['PURLIN_PROJECT_ROOT'] = self.project_root
            result = find_project_root()
            assert result == self.project_root
        finally:
            if old is None:
                os.environ.pop('PURLIN_PROJECT_ROOT', None)
            else:
                os.environ['PURLIN_PROJECT_ROOT'] = old

    @pytest.mark.proof("config-engine", "PROOF-2", "RULE-2")
    def test_resolve_local_config(self):
        """config.local.json is returned when it exists and is valid."""
        local_path = os.path.join(self.purlin_dir, 'config.local.json')
        with open(local_path, 'w') as f:
            json.dump({"framework": "pytest", "local": True}, f)
        result = resolve_config(self.project_root)
        assert result == {"framework": "pytest", "local": True}

    @pytest.mark.proof("config-engine", "PROOF-3", "RULE-3")
    def test_copy_on_first_access(self):
        """When only config.json exists, it's copied to config.local.json."""
        shared_path = os.path.join(self.purlin_dir, 'config.json')
        with open(shared_path, 'w') as f:
            json.dump({"version": "0.9.0", "test_framework": "auto"}, f)

        result = resolve_config(self.project_root)
        assert result["version"] == "0.9.0"

        local_path = os.path.join(self.purlin_dir, 'config.local.json')
        assert os.path.exists(local_path)
        with open(local_path) as f:
            local_data = json.load(f)
        assert local_data == result

    @pytest.mark.proof("config-engine", "PROOF-4", "RULE-4")
    def test_malformed_local_falls_back(self, capsys):
        """Malformed config.local.json falls back to config.json with warning."""
        local_path = os.path.join(self.purlin_dir, 'config.local.json')
        with open(local_path, 'w') as f:
            f.write('{not valid json}}}')

        shared_path = os.path.join(self.purlin_dir, 'config.json')
        with open(shared_path, 'w') as f:
            json.dump({"fallback": True}, f)

        result = resolve_config(self.project_root)
        assert result == {"fallback": True}

        captured = capsys.readouterr()
        assert "Warning" in captured.err

    @pytest.mark.proof("config-engine", "PROOF-5", "RULE-5")
    def test_no_config_files_returns_empty(self):
        """When neither config file exists, return empty dict."""
        result = resolve_config(self.project_root)
        assert result == {}

    @pytest.mark.proof("config-engine", "PROOF-6", "RULE-6")
    def test_update_writes_to_local(self):
        """update_config writes to config.local.json, not config.json."""
        shared_path = os.path.join(self.purlin_dir, 'config.json')
        with open(shared_path, 'w') as f:
            json.dump({"original": True}, f)

        update_config(self.project_root, "test_framework", "jest")

        local_path = os.path.join(self.purlin_dir, 'config.local.json')
        assert os.path.exists(local_path)
        with open(local_path) as f:
            local_data = json.load(f)
        assert local_data["test_framework"] == "jest"

        # config.json must be untouched
        with open(shared_path) as f:
            shared_data = json.load(f)
        assert shared_data == {"original": True}
