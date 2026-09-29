"""Tests for config_engine: the project root and the one settings file.

`.purlin/config.json` is committed; the resolver reads it whole and a write
sets one top-level key in it. One test per proof: each shows one case.
"""

import contextlib
import errno
import io
import json
import os
import subprocess
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
import config_engine
from config_engine import (PROJECT_ROOT_SOURCES, find_project_root,
                           resolve_config, resolve_project_root,
                           update_config)

SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp',
                      'config_engine.py')


@pytest.fixture
def tmp(tmp_path, monkeypatch):
    """A real temporary folder, with `PURLIN_PROJECT_ROOT` unset."""
    monkeypatch.delenv('PURLIN_PROJECT_ROOT', raising=False)
    return os.path.realpath(str(tmp_path))


def _folder(*parts):
    path = os.path.join(*parts)
    os.makedirs(path, exist_ok=True)
    return path


def _marked(*parts):
    """A folder holding a `.purlin/` marker."""
    path = os.path.join(*parts)
    os.makedirs(os.path.join(path, '.purlin'), exist_ok=True)
    return path


# -- The project root --------------------------------------------------------

class TestProjectRoot:

    # purlin: config_engine PROOF-1
    def test_the_variable_naming_an_existing_folder_wins_over_a_marker(
            self, tmp, monkeypatch):
        chosen = _folder(tmp, 'chosen')
        start = _folder(_marked(tmp, 'other'), 'src')
        monkeypatch.setenv('PURLIN_PROJECT_ROOT', chosen)
        assert find_project_root(start_dir=start) == chosen

    # purlin: config_engine PROOF-16
    def test_the_variable_naming_a_missing_path_gives_way_to_the_climb(
            self, tmp, monkeypatch):
        gone = os.path.join(tmp, 'gone')
        project = _marked(tmp, 'real_project')
        start = _folder(project, 'src')
        monkeypatch.setenv('PURLIN_PROJECT_ROOT', gone)
        assert not os.path.exists(gone)
        assert find_project_root(start_dir=start) == project

    # purlin: config_engine PROOF-17
    def test_the_variable_naming_a_file_gives_way_to_the_climb(
            self, tmp, monkeypatch):
        a_file = os.path.join(tmp, 'settings.txt')
        with open(a_file, 'w', encoding='utf-8') as f:
            f.write('not a folder\n')
        project = _marked(tmp, 'real_project')
        start = _folder(project, 'src')
        monkeypatch.setenv('PURLIN_PROJECT_ROOT', a_file)
        assert find_project_root(start_dir=start) == project

    # purlin: config_engine PROOF-2
    def test_the_climb_reaches_the_marker_above_the_start(self, tmp):
        root = _marked(tmp, 'a')
        start = _folder(root, 'b', 'c')
        assert find_project_root(start_dir=start) == root

    # purlin: config_engine PROOF-18
    def test_the_climb_stops_at_the_nearest_marker(self, tmp):
        outer = _marked(tmp, 'outer')
        inner = _marked(outer, 'inner')
        start = _folder(inner, 'src')
        assert find_project_root(start_dir=start) == inner

    # purlin: config_engine PROOF-3
    def test_with_no_marker_the_root_is_the_working_directory(
            self, tmp, monkeypatch):
        work = _folder(tmp, 'work')
        start = _folder(tmp, 'bare')
        monkeypatch.chdir(work)
        assert find_project_root(start_dir=start) == work


class TestHowTheRootWasFound:
    """Each case: the root with the way it was found, and the root alone."""

    @staticmethod
    def _both(start):
        return resolve_project_root(start_dir=start), find_project_root(
            start_dir=start)

    # purlin: config_engine PROOF-15
    def test_a_marker_above_the_start_is_found_by_climb(self, tmp):
        project = _marked(tmp, 'project')
        start = _folder(project, 'src')
        found, alone = self._both(start)
        assert found == (project, 'climb')
        assert alone == project

    # purlin: config_engine PROOF-28
    def test_the_variable_is_found_by_env(self, tmp, monkeypatch):
        project = _marked(tmp, 'project')
        start = _folder(project, 'src')
        elsewhere = _folder(tmp, 'elsewhere')
        monkeypatch.setenv('PURLIN_PROJECT_ROOT', elsewhere)
        found, alone = self._both(start)
        assert found == (elsewhere, 'env')
        assert alone == elsewhere

    # purlin: config_engine PROOF-29
    def test_a_missing_variable_path_is_passed_over_for_climb(
            self, tmp, monkeypatch):
        project = _marked(tmp, 'project')
        start = _folder(project, 'src')
        monkeypatch.setenv('PURLIN_PROJECT_ROOT', os.path.join(tmp, 'gone'))
        found, alone = self._both(start)
        assert found == (project, 'climb')
        assert alone == project

    # purlin: config_engine PROOF-30
    def test_no_marker_anywhere_is_named_cwd(self, tmp, monkeypatch):
        work = _folder(tmp, 'work')
        start = _folder(tmp, 'bare')
        monkeypatch.chdir(work)
        found, alone = self._both(start)
        assert found == (work, 'cwd')
        assert alone == work

    # purlin: config_engine PROOF-31
    def test_each_way_has_its_own_sentence(self):
        assert PROJECT_ROOT_SOURCES == {
            'env': 'the PURLIN_PROJECT_ROOT environment variable',
            'climb': 'climbing from the working directory to a .purlin/ marker',
            'cwd': ('the working directory, with no .purlin/ marker in it '
                    'or above it'),
        }


# -- Reading the settings file -----------------------------------------------

@pytest.fixture
def project(tmp):
    """A project folder holding `.purlin/` and no settings file yet."""
    return _marked(tmp, 'project')


def _settings(project):
    return os.path.join(project, '.purlin', 'config.json')


def _write(project, data):
    with open(_settings(project), 'w', encoding='utf-8') as f:
        json.dump(data, f)


def _read(project):
    with open(_settings(project), encoding='utf-8') as f:
        return json.load(f)


def _purlin_files(project):
    return sorted(os.listdir(os.path.join(project, '.purlin')))


class TestReading:

    # purlin: config_engine PROOF-4
    def test_the_settings_file_is_read_whole(self, project):
        held = {"team": "default", "shared": {"paths": ["a", "b"]}}
        _write(project, held)
        assert resolve_config(project) == held

    # purlin: config_engine PROOF-7
    def test_no_settings_file_reads_as_empty(self, project):
        assert _purlin_files(project) == []
        assert resolve_config(project) == {}


# -- Writing one key ---------------------------------------------------------

class TestWriting:

    # purlin: config_engine PROOF-8
    def test_a_write_adds_its_key_to_the_settings_file(self, project):
        _write(project, {"team": "v1"})
        update_config(project, "user_pref", "dark")
        assert _read(project) == {"team": "v1", "user_pref": "dark"}
        assert _purlin_files(project) == ['config.json']

    # purlin: config_engine PROOF-24
    def test_a_write_creates_the_settings_file_when_absent(self, project):
        assert _purlin_files(project) == []
        update_config(project, "new", True)
        assert _read(project) == {"new": True}

    # purlin: config_engine PROOF-12
    def test_the_written_value_is_what_the_settings_read(self, project):
        _write(project, {"gate": "passed", "version": "0.9.0"})
        update_config(project, "gate", "strong")
        assert resolve_config(project) == {
            "gate": "strong", "version": "0.9.0"}

    # purlin: config_engine PROOF-9
    def test_adding_a_key_keeps_every_other_key_as_it_was(self, project):
        _write(project, {"existing": "keep", "nested": {"list": [1, 2]}})
        update_config(project, "added", "new")
        assert _read(project) == {"existing": "keep",
                                  "nested": {"list": [1, 2]},
                                  "added": "new"}

    # purlin: config_engine PROOF-25
    def test_changing_a_key_keeps_every_other_key_as_it_was(self, project):
        _write(project, {"existing": "keep", "shade": "old"})
        update_config(project, "shade", "new")
        assert _read(project) == {"existing": "keep", "shade": "new"}


class TestAtomicWrite:

    # purlin: config_engine PROOF-10
    def test_the_whole_file_is_written_beside_and_moved_onto_it(self, project):
        _write(project, {"key": "old"})
        target = _settings(project)
        real_replace = os.replace
        moves = []

        def watch_the_move(src, dst):
            with open(src, encoding='utf-8') as f:
                moves.append((src, dst, json.load(f)))
            return real_replace(src, dst)

        with mock.patch.object(config_engine.os, 'replace',
                               side_effect=watch_the_move):
            update_config(project, "key", "val")

        assert [(os.path.abspath(s), os.path.abspath(d), held)
                for s, d, held in moves] == [
            (os.path.abspath(target + '.tmp'), os.path.abspath(target),
             {"key": "val"})]
        assert _purlin_files(project) == ['config.json']
        assert _read(project) == {"key": "val"}

    # purlin: config_engine PROOF-26
    def test_a_failed_move_leaves_the_previous_file_and_no_temporary(
            self, project):
        _write(project, {"key": "val"})
        with mock.patch.object(config_engine.os, 'replace',
                               side_effect=OSError("the move failed")):
            with contextlib.suppress(OSError):
                update_config(project, "key", "other")
        assert _read(project) == {"key": "val"}
        assert _purlin_files(project) == ['config.json']

    # purlin: config_engine PROOF-27
    def test_a_disk_full_partway_leaves_the_previous_file_and_no_temporary(
            self, project):
        _write(project, {"key": "val"})

        def fill_the_disk(obj, f, **_):
            f.write('{"key": ')
            raise OSError(errno.ENOSPC, 'No space left on device')

        with mock.patch.object(config_engine.json, 'dump',
                               side_effect=fill_the_disk):
            with contextlib.suppress(OSError):
                update_config(project, "key", "other")
        assert _read(project) == {"key": "val"}
        assert _purlin_files(project) == ['config.json']


# -- The command line --------------------------------------------------------

def _main(project, *args):
    """The command line's `main()` in this process: (exit code, out, err).

    In-process is what lets a mutation run see which case caught a break; the
    first case below also starts the script as a child.
    """
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with mock.patch.object(sys, 'argv', ['config_engine.py'] + list(args)), \
            mock.patch.dict(os.environ, {'PURLIN_PROJECT_ROOT': project}), \
            contextlib.redirect_stdout(out), \
            contextlib.redirect_stderr(err):
        try:
            config_engine.main()
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
    return code, out.getvalue(), err.getvalue()


class TestCommandLine:

    # purlin: config_engine PROOF-5
    def test_key_prints_the_value_as_its_own_process(self, project):
        _write(project, {"version": "0.9.0"})
        r = subprocess.run(
            [sys.executable, SCRIPT, '--key', 'version'],
            capture_output=True, text=True, cwd=project,
            env={**os.environ, 'PURLIN_PROJECT_ROOT': project},
        )
        assert r.returncode == 0
        assert r.stdout == "0.9.0\n"

    # purlin: config_engine PROOF-5
    def test_key_prints_the_value(self, project):
        _write(project, {"version": "0.9.0"})
        assert _main(project, '--key', 'version')[:2] == (0, "0.9.0\n")

    # purlin: config_engine PROOF-19
    def test_dump_prints_the_whole_settings_as_json(self, project):
        _write(project, {"team": "default", "shared": "base"})
        code, out, _ = _main(project, '--dump')
        assert code == 0
        assert json.loads(out) == {"team": "default", "shared": "base"}

    # purlin: config_engine PROOF-20
    def test_key_the_settings_do_not_hold_prints_an_empty_line(self, project):
        _write(project, {"version": "0.9.0"})
        assert _main(project, '--key', 'missing')[:2] == (0, "\n")

    # purlin: config_engine PROOF-21
    def test_no_argument_is_refused_with_the_usage(self, project):
        _write(project, {"version": "0.9.0"})
        assert _main(project) == (
            1, "", "Usage: config_engine.py [--dump | --key <name>]\n")

    # purlin: config_engine PROOF-22
    def test_key_with_no_name_is_refused_with_its_usage(self, project):
        _write(project, {"version": "0.9.0"})
        assert _main(project, '--key') == (
            1, "", "Usage: config_engine.py --key <name>\n")

    # purlin: config_engine PROOF-23
    def test_an_unknown_argument_is_refused_and_named(self, project):
        _write(project, {"version": "0.9.0"})
        assert _main(project, '--show') == (
            1, "", "Unknown argument: --show\n")
