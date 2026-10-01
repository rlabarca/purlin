"""Tests for config_engine: the project root and the one settings file.

`.purlin/config.json` is committed; the resolver reads it whole and a write
sets one top-level key in it. One test per proof: each shows one case.
"""

import errno
import json
import os
import subprocess
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
import config_engine
from config_engine import (ConfigUnreadable, config_problem,
                           find_project_root, resolve_config,
                           resolve_project_root, settings_warnings,
                           update_config)
from purlin import PURLIN_VERSION
from purlin import status as purlin_status


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
    """Each case: the root with the way it was found, and the root alone."""

    @staticmethod
    def _both(start):
        return resolve_project_root(start_dir=start), find_project_root(
            start_dir=start)

    # purlin: config_engine PROOF-28
    def test_the_variable_is_found_by_env(self, tmp, monkeypatch):
        project = _marked(tmp, 'project')
        start = _folder(project, 'src')
        elsewhere = _folder(tmp, 'elsewhere')
        monkeypatch.setenv('PURLIN_PROJECT_ROOT', elsewhere)
        found, alone = self._both(start)
        assert found == (elsewhere, 'env')
        assert alone == elsewhere

    # purlin: config_engine PROOF-18
    def test_the_climb_stops_at_the_nearest_marker(self, tmp):
        outer = _marked(tmp, 'outer')
        inner = _marked(outer, 'inner')
        start = _folder(inner, 'src')
        assert find_project_root(start_dir=start) == inner
        assert find_project_root(start_dir=start) != outer

    # purlin: config_engine PROOF-30
    def test_no_marker_anywhere_is_named_cwd(self, tmp, monkeypatch):
        work = _folder(tmp, 'work')
        start = _folder(tmp, 'bare')
        monkeypatch.chdir(work)
        found, alone = self._both(start)
        assert found == (work, 'cwd')
        assert alone == work


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

    # purlin: config_engine PROOF-38
    def test_on_windows_a_write_ends_its_lines_with_no_carriage_return(
            self, project):
        _write(project, {"team": "v1"})
        update_config(project, "user_pref", "dark")
        assert _read(project) == {"team": "v1", "user_pref": "dark"}
        # The bytes, so a carriage return Windows adds to a line is seen.
        assert b'\r' not in _read_bytes(project)
        assert _read_bytes(project) == (
            b'{\n  "team": "v1",\n  "user_pref": "dark"\n}\n')
        assert _purlin_files(project) == ['config.json']

    # purlin: config_engine PROOF-24
    def test_a_write_creates_the_settings_file_when_absent(self, project):
        assert _purlin_files(project) == []
        update_config(project, "new", True)
        assert _read(project) == {"new": True}


def _hold_open(path):
    """Another program holding `path` open for reading until its input closes."""
    holder = subprocess.Popen(
        [sys.executable, '-c',
         'import sys\n'
         'f = open(sys.argv[1], "rb")\n'
         'sys.stdout.write("open\\n")\n'
         'sys.stdout.flush()\n'
         'sys.stdin.read()\n'
         'f.close()\n', path],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    assert holder.stdout.readline().strip() == b'open'
    return holder


class TestAtomicWrite:

    # purlin: config_engine PROOF-26
    def test_a_failed_move_leaves_the_previous_file_and_no_temporary(
            self, project):
        _write(project, {"key": "val"})
        with mock.patch.object(config_engine.os, 'replace',
                               side_effect=OSError("the move failed")):
            with pytest.raises(OSError, match='^the move failed$'):
                update_config(project, "key", "other")
        assert _read(project) == {"key": "val"}
        assert _purlin_files(project) == ['config.json']

    # purlin: config_engine PROOF-39
    @pytest.mark.skipif(os.name != 'nt', reason=(
        'only Windows refuses a move onto a file another program holds open'))
    def test_on_windows_a_move_onto_a_file_held_open_leaves_it_whole(
            self, project):
        _write(project, {"key": "val"})
        holder = _hold_open(_settings(project))
        try:
            with pytest.raises(OSError):
                update_config(project, "key", "other")
            assert _purlin_files(project) == ['config.json']
        finally:
            holder.stdin.close()
            holder.wait(timeout=60)
            holder.stdout.close()
        assert _read_bytes(project) == b'{"key": "val"}'

    # purlin: config_engine PROOF-27
    def test_a_disk_full_partway_leaves_the_previous_file_and_no_temporary(
            self, project):
        _write(project, {"key": "val"})

        def fill_the_disk(obj, f, **_):
            f.write('{"key": ')
            raise OSError(errno.ENOSPC, 'No space left on device')

        with mock.patch.object(config_engine.json, 'dump',
                               side_effect=fill_the_disk):
            with pytest.raises(OSError) as stopped:
                update_config(project, "key", "other")
        assert stopped.value.strerror == 'No space left on device'
        assert _read(project) == {"key": "val"}
        assert _purlin_files(project) == ['config.json']



# -- A settings file that cannot be read ------------------------------------

TRAILING_COMMA = '{\n  "tests": [],}\n'


def _write_bytes(project, raw):
    with open(_settings(project), 'wb') as f:
        f.write(raw)


def _read_bytes(project):
    with open(_settings(project), 'rb') as f:
        return f.read()


def _cannot_be_read(cause):
    return ('.purlin/config.json cannot be read: %s. Fix the file by hand; '
            'nothing ran and nothing was saved.' % cause)


def _readers_message(text):
    """The JSON reader's own message for `text`, and the line it names."""
    with pytest.raises(json.JSONDecodeError) as refused:
        json.loads(text)
    return refused.value.msg, refused.value.lineno


class TestASettingsFileThatCannotBeRead:

    # purlin: config_engine PROOF-32
    def test_a_trailing_comma_is_named_with_the_readers_message_and_line(
            self, project):
        _write_bytes(project, TRAILING_COMMA.encode('utf-8'))
        message, line = _readers_message(TRAILING_COMMA)
        assert line == 2
        assert message
        assert config_problem(project) == _cannot_be_read(
            '%s at line 2' % message)

    # purlin: config_engine PROOF-33
    def test_bytes_that_are_not_utf8_are_named(self, project):
        _write_bytes(project, b'{"version": "\xff"}')
        assert config_problem(project) == _cannot_be_read(
            'it is not UTF-8 text')

    # purlin: config_engine PROOF-35
    def test_a_write_is_refused_and_the_file_left_as_it_was(self, project):
        _write_bytes(project, TRAILING_COMMA.encode('utf-8'))
        before = _read_bytes(project)
        message, _line = _readers_message(TRAILING_COMMA)
        with pytest.raises(ConfigUnreadable) as refused:
            update_config(project, 'tests', [])
        assert str(refused.value) == _cannot_be_read(
            '%s at line 2' % message)
        assert _read_bytes(project) == before
        assert _purlin_files(project) == ['config.json']


# -- The project's name -----------------------------------------------------

def _git(root, *args):
    subprocess.run(['git'] + list(args), cwd=root, check=True,
                   capture_output=True, text=True)


def _set_up(root):
    """`root` made a git project holding `.purlin/config.json` with `version`
    and `tests` and the one spec `app`, every file committed."""
    os.makedirs(os.path.join(root, 'specs', 'app'), exist_ok=True)
    with open(os.path.join(root, 'specs', 'app', 'app.md'), 'w',
              encoding='utf-8') as f:
        f.write('# Feature: app\n\n## Rules\n\n- RULE-1: It starts\n\n'
                '## Proof\n\n- PROOF-1 (RULE-1): Start it; it exits 0\n')
    os.makedirs(os.path.join(root, '.purlin'), exist_ok=True)
    with open(os.path.join(root, '.purlin', 'config.json'), 'w',
              encoding='utf-8') as f:
        json.dump({'version': PURLIN_VERSION, 'tests': []}, f)
    _git(root, 'init', '-q')
    _git(root, 'add', '-A')
    _git(root, '-c', 'user.name=t', '-c', 'user.email=t@example.com',
         '-c', 'commit.gpgsign=false', 'commit', '-qm', 'start')


def _first_line(root):
    return purlin_status.sync_status(root).splitlines()[0]


class TestTheProjectsName:

    # purlin: config_engine PROOF-45
    def test_the_name_under_project_in_pyproject_wins(self, tmp):
        root = _folder(tmp, 'intake')
        with open(os.path.join(root, 'pyproject.toml'), 'w',
                  encoding='utf-8') as f:
            f.write('[project]\nname = "labconnect"\n')
        with open(os.path.join(root, 'package.json'), 'w',
                  encoding='utf-8') as f:
            json.dump({'name': 'intake-web'}, f)
        _set_up(root)
        assert _first_line(root).startswith('Purlin status: labconnect,'), \
            _first_line(root)
        with open(os.path.join(root, '.purlin', 'config.json'),
                  encoding='utf-8') as f:
            settings = f.read()
        assert sorted(json.loads(settings)) == ['tests', 'version'], settings
        assert 'labconnect' not in settings, settings

    # purlin: config_engine PROOF-48
    def test_with_no_project_file_the_origin_remote_names_it(self, tmp):
        root = _folder(tmp, 'work')
        _set_up(root)
        _git(root, 'remote', 'add', 'origin', '/srv/git/labconnect.git')
        assert _first_line(root).startswith('Purlin status: labconnect,'), \
            _first_line(root)

    # purlin: config_engine PROOF-49
    def test_with_no_project_file_and_no_remote_the_folder_names_it(self, tmp):
        root = _folder(tmp, 'labconnect')
        _set_up(root)
        assert _first_line(root).startswith('Purlin status: labconnect,'), \
            _first_line(root)


# -- Keys the file holds that this version does not read --------------------

class TestKeysThisVersionDoesNotRead:

    # purlin: config_engine PROOF-50
    def test_keys_the_upgrade_removes_name_the_upgrade(self, project):
        _write_bytes(project, b'{"version": "0.10.0", "tests": [], '
                              b'"gate": "passed", "mutation_engine": "none"}')
        assert settings_warnings(resolve_config(project)) == [
            '.purlin/config.json carries gate, mutation_engine, which this '
            'version does not read. Run purlin:init --update.']

    # purlin: config_engine PROOF-51
    def test_a_key_the_upgrade_has_no_step_for_is_to_be_removed(self, project):
        _write_bytes(project, b'{"version": "0.10.0", "tests": [], '
                              b'"colour": "blue"}')
        assert settings_warnings(resolve_config(project)) == [
            '.purlin/config.json carries colour, which this version does not '
            'read. Remove it from .purlin/config.json.']
