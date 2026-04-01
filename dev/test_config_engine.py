"""Tests for config_engine — 10 rules.

Covers find_project_root (env var, climbing, cwd fallback),
resolve_config (local, copy-on-first-access, malformed fallback, empty),
update_config (atomic write, key preservation), and CLI mode.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
from config_engine import find_project_root, resolve_config, update_config


class TestFindProjectRoot:

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self._old_env = os.environ.get('PURLIN_PROJECT_ROOT')
        os.environ.pop('PURLIN_PROJECT_ROOT', None)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)
        if self._old_env is None:
            os.environ.pop('PURLIN_PROJECT_ROOT', None)
        else:
            os.environ['PURLIN_PROJECT_ROOT'] = self._old_env

    @pytest.mark.proof("config_engine", "PROOF-1", "RULE-1")
    def test_env_var_takes_precedence(self):
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        os.environ['PURLIN_PROJECT_ROOT'] = self.tmpdir
        result = find_project_root()
        assert result == self.tmpdir

    @pytest.mark.proof("config_engine", "PROOF-2", "RULE-2")
    def test_climbs_to_purlin_marker(self):
        root = os.path.join(self.tmpdir, 'a')
        os.makedirs(os.path.join(root, '.purlin'))
        deep = os.path.join(root, 'b', 'c')
        os.makedirs(deep)
        result = find_project_root(start_dir=deep)
        assert result == root

    @pytest.mark.proof("config_engine", "PROOF-3", "RULE-3")
    def test_falls_back_to_cwd(self):
        bare = os.path.join(self.tmpdir, 'no_marker')
        os.makedirs(bare)
        result = find_project_root(start_dir=bare)
        assert result == os.path.abspath(os.getcwd())


class TestResolveConfig:

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.project_root, '.purlin')
        os.makedirs(self.purlin_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    @pytest.mark.proof("config_engine", "PROOF-4", "RULE-4")
    def test_local_config_returned(self):
        local_path = os.path.join(self.purlin_dir, 'config.local.json')
        with open(local_path, 'w') as f:
            json.dump({"key": "local_val"}, f)
        result = resolve_config(self.project_root)
        assert result == {"key": "local_val"}

    @pytest.mark.proof("config_engine", "PROOF-5", "RULE-5")
    def test_copy_on_first_access(self):
        shared_path = os.path.join(self.purlin_dir, 'config.json')
        with open(shared_path, 'w') as f:
            json.dump({"key": "shared_val"}, f)
        result = resolve_config(self.project_root)
        assert result == {"key": "shared_val"}
        local_path = os.path.join(self.purlin_dir, 'config.local.json')
        assert os.path.exists(local_path)
        with open(local_path) as f:
            assert json.load(f) == {"key": "shared_val"}

    @pytest.mark.proof("config_engine", "PROOF-6", "RULE-6")
    def test_malformed_local_falls_back(self, capsys):
        local_path = os.path.join(self.purlin_dir, 'config.local.json')
        with open(local_path, 'w') as f:
            f.write('{bad json}}}')
        shared_path = os.path.join(self.purlin_dir, 'config.json')
        with open(shared_path, 'w') as f:
            json.dump({"key": "fallback"}, f)
        result = resolve_config(self.project_root)
        assert result == {"key": "fallback"}
        assert "Warning" in capsys.readouterr().err

    @pytest.mark.proof("config_engine", "PROOF-7", "RULE-7")
    def test_no_configs_returns_empty(self):
        result = resolve_config(self.project_root)
        assert result == {}


class TestUpdateConfig:

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.project_root, '.purlin')
        os.makedirs(self.purlin_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    @pytest.mark.proof("config_engine", "PROOF-8", "RULE-8")
    def test_atomic_replacement(self):
        update_config(self.project_root, "newkey", "newval")
        local_path = os.path.join(self.purlin_dir, 'config.local.json')
        assert os.path.exists(local_path)
        with open(local_path) as f:
            assert json.load(f)["newkey"] == "newval"
        assert not os.path.exists(local_path + '.tmp')

    @pytest.mark.proof("config_engine", "PROOF-9", "RULE-9")
    def test_preserves_existing_keys(self):
        local_path = os.path.join(self.purlin_dir, 'config.local.json')
        with open(local_path, 'w') as f:
            json.dump({"existing": "keep"}, f)
        update_config(self.project_root, "added", "new")
        with open(local_path) as f:
            data = json.load(f)
        assert data == {"existing": "keep", "added": "new"}

    @pytest.mark.proof("config_engine", "PROOF-10", "RULE-10")
    def test_cli_dump_and_key(self):
        config_path = os.path.join(self.purlin_dir, 'config.json')
        with open(config_path, 'w') as f:
            json.dump({"test_key": "val", "number": 42}, f)

        script = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp', 'config_engine.py')
        env = {**os.environ, 'PURLIN_PROJECT_ROOT': self.project_root}

        r = subprocess.run(
            [sys.executable, script, '--dump'],
            capture_output=True, text=True, cwd=self.project_root, env=env,
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["test_key"] == "val"

        r = subprocess.run(
            [sys.executable, script, '--key', 'test_key'],
            capture_output=True, text=True, cwd=self.project_root, env=env,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == "val"
