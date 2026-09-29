"""Tests for config_engine: the project root and the one settings file.

`.purlin/config.json` is committed; the resolver reads it whole and a write
sets one top-level key in it.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
import config_engine
from config_engine import (PROJECT_ROOT_SOURCES, find_project_root,
                           resolve_config, resolve_project_root,
                           update_config)


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

    # purlin: config_engine PROOF-1
    def test_env_var_takes_precedence_only_when_the_directory_exists(self):
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        os.environ['PURLIN_PROJECT_ROOT'] = self.tmpdir
        assert find_project_root() == self.tmpdir

        # The 'and the directory exists' half of the rule: a stale root that
        # was deleted (a worktree removed, a container rebuilt) is not handed
        # back. The climb runs instead and finds the real marker.
        gone = os.path.join(self.tmpdir, 'deleted_root')
        assert not os.path.isdir(gone)
        os.environ['PURLIN_PROJECT_ROOT'] = gone
        marker_root = os.path.join(self.tmpdir, 'real_project')
        os.makedirs(os.path.join(marker_root, '.purlin'))
        deep = os.path.join(marker_root, 'src')
        os.makedirs(deep)
        assert find_project_root(start_dir=deep) == marker_root, (
            "PURLIN_PROJECT_ROOT names a directory that does not exist; "
            "find_project_root must fall through to the .purlin climb")

    # purlin: config_engine PROOF-2
    def test_climbs_to_purlin_marker(self):
        root = os.path.join(self.tmpdir, 'a')
        os.makedirs(os.path.join(root, '.purlin'))
        deep = os.path.join(root, 'b', 'c')
        os.makedirs(deep)
        result = find_project_root(start_dir=deep)
        assert result == root

    # purlin: config_engine PROOF-3
    def test_falls_back_to_cwd(self):
        bare = os.path.join(self.tmpdir, 'no_marker')
        os.makedirs(bare)
        result = find_project_root(start_dir=bare)
        assert result == os.path.abspath(os.getcwd())

    # purlin: config_engine PROOF-15
    def test_resolve_project_root_names_how_it_resolved(self):
        project = os.path.join(self.tmpdir, 'project')
        deep = os.path.join(project, 'src')
        os.makedirs(os.path.join(project, '.purlin'))
        os.makedirs(deep)

        # 1. The climb, with nothing in the environment to beat it.
        assert resolve_project_root(start_dir=deep) == (project, 'climb')

        # 2. The environment wins over the marker the climb would have found.
        elsewhere = os.path.join(self.tmpdir, 'elsewhere')
        os.makedirs(elsewhere)
        os.environ['PURLIN_PROJECT_ROOT'] = elsewhere
        assert resolve_project_root(start_dir=deep) == (elsewhere, 'env')

        # 3. A root that does not exist does not win; the climb answers again.
        gone = os.path.join(self.tmpdir, 'gone')
        assert not os.path.isdir(gone)
        os.environ['PURLIN_PROJECT_ROOT'] = gone
        assert resolve_project_root(start_dir=deep) == (project, 'climb')

        # 4. No marker anywhere above: cwd, and said to be cwd.
        os.environ.pop('PURLIN_PROJECT_ROOT', None)
        bare = os.path.join(self.tmpdir, 'bare')
        os.makedirs(bare)
        root, source = resolve_project_root(start_dir=bare)
        assert source == 'cwd', source
        assert root == os.path.abspath(os.getcwd())

        # The fallback is named, not silent, and so is every other case.
        assert sorted(PROJECT_ROOT_SOURCES) == ['climb', 'cwd', 'env']
        assert all(isinstance(v, str) and v.strip()
                   for v in PROJECT_ROOT_SOURCES.values()), PROJECT_ROOT_SOURCES
        cwd_text = PROJECT_ROOT_SOURCES['cwd']
        assert 'working directory' in cwd_text and 'marker' in cwd_text, cwd_text

        # The two entry points cannot answer differently.
        for start, env in ((deep, None), (deep, elsewhere), (deep, gone),
                           (bare, None)):
            if env is None:
                os.environ.pop('PURLIN_PROJECT_ROOT', None)
            else:
                os.environ['PURLIN_PROJECT_ROOT'] = env
            assert (find_project_root(start_dir=start)
                    == resolve_project_root(start_dir=start)[0])


class TestResolveConfig:

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.project_root, '.purlin')
        os.makedirs(self.purlin_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _write_shared(self, data):
        with open(os.path.join(self.purlin_dir, 'config.json'), 'w',
                  encoding='utf-8') as f:
            json.dump(data, f)

    # purlin: config_engine PROOF-4
    def test_the_config_is_config_json_whole(self):
        self._write_shared({"team": "default", "shared": "base"})
        assert resolve_config(self.project_root) == {
            "team": "default", "shared": "base"}

    # purlin: config_engine PROOF-7
    def test_no_config_returns_empty(self):
        result = resolve_config(self.project_root)
        assert result == {}


class TestUpdateConfig:

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.project_root, '.purlin')
        self.path = os.path.join(self.purlin_dir, 'config.json')
        os.makedirs(self.purlin_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _write(self, data):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    def _read(self):
        with open(self.path, encoding='utf-8') as f:
            return json.load(f)

    # purlin: config_engine PROOF-8
    def test_a_write_reaches_config_json(self):
        self._write({"team": "v1"})
        update_config(self.project_root, "user_pref", "dark")
        assert self._read() == {"team": "v1", "user_pref": "dark"}
        assert os.listdir(self.purlin_dir) == ['config.json']

    # purlin: config_engine PROOF-8
    def test_a_write_creates_config_json_when_absent(self):
        assert not os.path.exists(self.path)
        update_config(self.project_root, "new", True)
        assert self._read() == {"new": True}

    # purlin: config_engine PROOF-12
    def test_the_written_value_is_what_the_resolver_reads(self):
        self._write({"gate": "passed", "version": "0.9.0"})
        update_config(self.project_root, "gate", "strong")
        assert resolve_config(self.project_root) == {
            "gate": "strong", "version": "0.9.0"}

    # purlin: config_engine PROOF-9
    def test_a_write_preserves_every_other_key(self):
        self._write({"existing": "keep", "shade": "old"})
        update_config(self.project_root, "added", "new")
        update_config(self.project_root, "shade", "new")
        assert self._read() == {"existing": "keep", "shade": "new",
                                "added": "new"}

    # purlin: config_engine PROOF-10
    def test_atomic_replacement(self):
        # Behavioral proof of the atomic mechanism: the durable file is produced
        # by renaming a .tmp via os.replace, never by an in-place write.
        real_replace = os.replace
        replace_calls = []

        def spy_replace(src, dst):
            replace_calls.append((src, dst))
            return real_replace(src, dst)

        with mock.patch.object(config_engine.os, 'replace', side_effect=spy_replace):
            update_config(self.project_root, "key", "val")

        assert replace_calls, "update_config is not atomic: os.replace was never called"
        src, dst = replace_calls[-1]
        assert src.endswith('.tmp'), f"expected rename from a .tmp file, got {src!r}"
        assert os.path.abspath(dst) == os.path.abspath(self.path), \
            f"os.replace target {dst!r} is not config.json"

        # No partial write: file exists, is valid JSON with the new key, no .tmp left.
        assert not os.path.exists(self.path + '.tmp')
        assert self._read()["key"] == "val"

        # An interrupted rename must leave the original file untouched (no partial write).
        self._write({"key": "val"})
        with mock.patch.object(config_engine.os, 'replace',
                               side_effect=OSError("simulated crash mid-rename")):
            try:
                update_config(self.project_root, "key", "other")
            except OSError:
                pass
        assert self._read() == {"key": "val"}, "interrupted write corrupted the config"
        assert not os.path.exists(self.path + '.tmp')


class TestCLI:

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.project_root, '.purlin')
        os.makedirs(self.purlin_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _write(self, data):
        with open(os.path.join(self.purlin_dir, 'config.json'), 'w',
                  encoding='utf-8') as f:
            json.dump(data, f)

    # purlin: config_engine PROOF-5
    def test_cli_key(self):
        self._write({"version": "0.9.0"})
        script = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp', 'config_engine.py')
        env = {**os.environ, 'PURLIN_PROJECT_ROOT': self.project_root}

        r = subprocess.run(
            [sys.executable, script, '--key', 'version'],
            capture_output=True, text=True, cwd=self.project_root, env=env,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == "0.9.0"

    def _main(self, *args):
        """The command line's `main()` in this process: (exit code, stdout).

        In-process is what lets a mutation run see which case caught a break;
        the case above still starts the script as a child.
        """
        out = io.StringIO()
        code = 0
        env = {'PURLIN_PROJECT_ROOT': self.project_root}
        with mock.patch.object(sys, 'argv', ['config_engine.py'] + list(args)), \
                mock.patch.dict(os.environ, env), \
                contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()):
            try:
                config_engine.main()
            except SystemExit as stop:
                code = stop.code if isinstance(stop.code, int) else 1
        return code, out.getvalue()

    # purlin: config_engine PROOF-4
    def test_dump_in_process_prints_the_config(self):
        self._write({"team": "default", "shared": "base"})
        code, out = self._main('--dump')
        assert code == 0
        assert json.loads(out) == {"team": "default", "shared": "base"}

    # purlin: config_engine PROOF-5
    def test_key_in_process_prints_the_value(self):
        self._write({"version": "0.9.0"})
        code, out = self._main('--key', 'version')
        assert code == 0
        assert out == "0.9.0\n"
