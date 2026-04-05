"""Tests for config_engine — merge-based two-file config resolution.

config.json = team defaults (committed).
config.local.json = per-user overrides (gitignored, sparse).
Resolution = merge config.json base + config.local.json overlay.
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

    def _write_shared(self, data):
        with open(os.path.join(self.purlin_dir, 'config.json'), 'w') as f:
            json.dump(data, f)

    def _write_local(self, data):
        with open(os.path.join(self.purlin_dir, 'config.local.json'), 'w') as f:
            if isinstance(data, str):
                f.write(data)  # raw string for malformed tests
            else:
                json.dump(data, f)

    def _local_exists(self):
        return os.path.isfile(os.path.join(self.purlin_dir, 'config.local.json'))

    @pytest.mark.proof("config_engine", "PROOF-4", "RULE-4")
    def test_merge_base_with_overrides(self):
        """Local keys win, base keys preserved, local-only keys included."""
        self._write_shared({"team": "default", "shared": "base"})
        self._write_local({"shared": "override", "local_only": True})
        result = resolve_config(self.project_root)
        assert result == {"team": "default", "shared": "override", "local_only": True}

    @pytest.mark.proof("config_engine", "PROOF-5", "RULE-5")
    def test_shared_only_no_copy(self):
        """config.json returned when no local exists. Local file NOT created."""
        self._write_shared({"key": "val"})
        result = resolve_config(self.project_root)
        assert result == {"key": "val"}
        assert not self._local_exists(), "config.local.json should NOT be created"

    @pytest.mark.proof("config_engine", "PROOF-6", "RULE-6")
    def test_malformed_local_falls_back(self, capsys):
        """Malformed local is ignored with warning. Returns shared only."""
        self._write_local("{bad json}}}")
        self._write_shared({"key": "fallback"})
        result = resolve_config(self.project_root)
        assert result == {"key": "fallback"}
        assert "Warning" in capsys.readouterr().err

    @pytest.mark.proof("config_engine", "PROOF-7", "RULE-7")
    def test_no_configs_returns_empty(self):
        result = resolve_config(self.project_root)
        assert result == {}

    @pytest.mark.proof("config_engine", "PROOF-11", "RULE-4")
    def test_framework_new_key_visible_through_existing_local(self):
        """When framework adds a new key to config.json, it's visible even
        when config.local.json already exists with unrelated overrides.
        This is the scenario that broke with copy-on-first-access."""
        self._write_shared({"report": True, "version": "0.9.0"})
        self._write_local({"pre_push": "strict"})
        result = resolve_config(self.project_root)
        assert result["report"] is True, "new framework key must be visible"
        assert result["version"] == "0.9.0", "shared key preserved"
        assert result["pre_push"] == "strict", "local override preserved"

    @pytest.mark.proof("config_engine", "PROOF-12", "RULE-8")
    def test_local_override_wins_in_merge(self):
        """User overrides a framework default. config.json untouched."""
        self._write_shared({"report": True, "version": "0.9.0"})
        shared_before = json.loads(open(os.path.join(self.purlin_dir, 'config.json')).read())

        update_config(self.project_root, "report", False)

        # config.json must not change
        shared_after = json.loads(open(os.path.join(self.purlin_dir, 'config.json')).read())
        assert shared_after == shared_before, "config.json must be untouched"

        # local should have the override
        with open(os.path.join(self.purlin_dir, 'config.local.json')) as f:
            local = json.load(f)
        assert local["report"] is False

        # Merged result should have local's value
        result = resolve_config(self.project_root)
        assert result["report"] is False, "local override must win"
        assert result["version"] == "0.9.0", "unrelated shared key preserved"

    @pytest.mark.proof("config_engine", "PROOF-4", "RULE-4")
    def test_local_only_keys_included(self):
        """Keys in local that aren't in shared are still in the merge."""
        self._write_shared({"version": "0.9.0"})
        self._write_local({"custom_setting": 42})
        result = resolve_config(self.project_root)
        assert result == {"version": "0.9.0", "custom_setting": 42}

    @pytest.mark.proof("config_engine", "PROOF-4", "RULE-4")
    def test_empty_local_returns_shared(self):
        """Empty local override file means all shared keys visible."""
        self._write_shared({"version": "0.9.0", "report": True})
        self._write_local({})
        result = resolve_config(self.project_root)
        assert result == {"version": "0.9.0", "report": True}

    @pytest.mark.proof("config_engine", "PROOF-5", "RULE-5")
    def test_local_without_shared(self):
        """local exists but shared doesn't — local is the full config."""
        self._write_local({"standalone": True})
        result = resolve_config(self.project_root)
        assert result == {"standalone": True}


class TestUpdateConfig:

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.project_root, '.purlin')
        os.makedirs(self.purlin_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    @pytest.mark.proof("config_engine", "PROOF-8", "RULE-8")
    def test_writes_only_to_local(self):
        """update_config writes to config.local.json, not config.json."""
        shared_path = os.path.join(self.purlin_dir, 'config.json')
        with open(shared_path, 'w') as f:
            json.dump({"team": "v1"}, f)
        shared_mtime = os.path.getmtime(shared_path)

        update_config(self.project_root, "user_pref", "dark")

        # config.json unchanged
        assert os.path.getmtime(shared_path) == shared_mtime
        with open(shared_path) as f:
            assert json.load(f) == {"team": "v1"}

        # config.local.json has the new key
        with open(os.path.join(self.purlin_dir, 'config.local.json')) as f:
            local = json.load(f)
        assert local == {"user_pref": "dark"}

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
    def test_atomic_replacement(self):
        update_config(self.project_root, "key", "val")
        local_path = os.path.join(self.purlin_dir, 'config.local.json')
        assert os.path.exists(local_path)
        assert not os.path.exists(local_path + '.tmp')
        import inspect
        source = inspect.getsource(update_config)
        assert 'os.replace' in source

    @pytest.mark.proof("config_engine", "PROOF-8", "RULE-8")
    def test_update_creates_local_if_missing(self):
        """update_config creates config.local.json if it doesn't exist."""
        local_path = os.path.join(self.purlin_dir, 'config.local.json')
        assert not os.path.exists(local_path)
        update_config(self.project_root, "new", True)
        assert os.path.exists(local_path)
        with open(local_path) as f:
            assert json.load(f) == {"new": True}

    @pytest.mark.proof("config_engine", "PROOF-9", "RULE-9")
    def test_update_overwrites_existing_key(self):
        """update_config replaces an existing key's value."""
        local_path = os.path.join(self.purlin_dir, 'config.local.json')
        with open(local_path, 'w') as f:
            json.dump({"mode": "old"}, f)
        update_config(self.project_root, "mode", "new")
        with open(local_path) as f:
            assert json.load(f)["mode"] == "new"


class TestCLI:

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.project_root, '.purlin')
        os.makedirs(self.purlin_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    @pytest.mark.proof("config_engine", "PROOF-4", "RULE-4")
    def test_cli_dump(self):
        with open(os.path.join(self.purlin_dir, 'config.json'), 'w') as f:
            json.dump({"team": "default"}, f)
        with open(os.path.join(self.purlin_dir, 'config.local.json'), 'w') as f:
            json.dump({"local": True}, f)

        script = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp', 'config_engine.py')
        env = {**os.environ, 'PURLIN_PROJECT_ROOT': self.project_root}

        r = subprocess.run(
            [sys.executable, script, '--dump'],
            capture_output=True, text=True, cwd=self.project_root, env=env,
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        # Must show merged result
        assert data["team"] == "default"
        assert data["local"] is True

    @pytest.mark.proof("config_engine", "PROOF-5", "RULE-5")
    def test_cli_key(self):
        with open(os.path.join(self.purlin_dir, 'config.json'), 'w') as f:
            json.dump({"version": "0.9.0"}, f)

        script = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp', 'config_engine.py')
        env = {**os.environ, 'PURLIN_PROJECT_ROOT': self.project_root}

        r = subprocess.run(
            [sys.executable, script, '--key', 'version'],
            capture_output=True, text=True, cwd=self.project_root, env=env,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == "0.9.0"
