"""Tests for the MCP transport of `scripts/mcp/purlin/`.

What the server answers on stdin, and the package hygiene it keeps. The
throwaway project and its helpers are in `dev/mcp_project.py`.
"""

import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from mcp_project import PROJECT_ROOT, SERVER_PY, Project, _rpc, project
# `mcp_project` puts `scripts/mcp` on the path.
from purlin import server as purlin_srv


# ---------------------------------------------------------------------------
# What a client sends, and what it reads back
# ---------------------------------------------------------------------------

def _call(tool, arguments=None, req_id=1):
    """A `tools/call` request for one tool."""
    return {'jsonrpc': '2.0', 'id': req_id, 'method': 'tools/call',
            'params': {'name': tool, 'arguments': arguments or {}}}


def _initialize(req_id=1):
    return {'jsonrpc': '2.0', 'id': req_id, 'method': 'initialize',
            'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                       'clientInfo': {'name': 't', 'version': '0'}}}


def _text(response):
    """The text a tool answered, read as the client reads it."""
    return response['result']['content'][0]['text']


def _config_file(root):
    return os.path.join(root, '.purlin', 'config.json')


def _read_bytes(path):
    with open(path, 'rb') as handle:
        return handle.read()


def _version():
    with open(os.path.join(PROJECT_ROOT, 'VERSION'), encoding='utf-8') as handle:
        return handle.read().strip()


def _child(root, lines, command=None, env=None):
    """Start the server as its own process, as a client does; raw stdout and stderr."""
    result = subprocess.run(command or [sys.executable, SERVER_PY],
                            input=lines, capture_output=True, text=True,
                            encoding='utf-8', cwd=root, env=env, timeout=180)
    return result.stdout, result.stderr


def _child_bytes(root, lines):
    """The server started as its own process; its stdout and stderr as bytes."""
    result = subprocess.run([sys.executable, SERVER_PY],
                            input=lines.encode('utf-8'), capture_output=True,
                            cwd=root, timeout=180)
    return result.stdout, result.stderr


# ---------------------------------------------------------------------------
# The MCP transport
# ---------------------------------------------------------------------------

class TestTransport:

    # purlin: server PROOF-1
    def test_initialize_names_the_protocol_the_server_and_the_version(
            self, project):
        responses, _stderr = _rpc(project.root, _initialize(), child=True)
        result = responses[0]['result']
        assert result['protocolVersion'] == '2024-11-05'
        assert result['serverInfo']['name'] == 'purlin'
        assert result['serverInfo']['version'] == _version()
        # A client discovers the tools through this capability.
        assert 'tools' in result['capabilities'], result['capabilities']

    # purlin: server PROOF-159
    def test_on_windows_the_answer_is_one_line_and_the_startup_line_is_on_stderr(
            self, project):
        raw_out, raw_err = _child_bytes(project.root,
                                        json.dumps(_initialize()) + '\n')
        # The bytes, so a carriage return Windows adds to a line is seen.
        assert raw_out.count(b'\n') == 1 and raw_out.endswith(b'\n'), raw_out
        assert b'\r' not in raw_out, raw_out
        answer = json.loads(raw_out.decode('utf-8'))
        assert answer['jsonrpc'] == '2.0' and answer['id'] == 1, answer
        assert ('Purlin MCP server v%s started' % _version()) in \
            raw_err.decode('utf-8'), raw_err

    # purlin: server PROOF-138
    def test_stdout_holds_one_answer_per_tool_call_and_nothing_else(
            self, project):
        root = {'project_root': project.root}
        requests = [_call('sync_status', root, req_id=1),
                    _call('drift', dict(root, since='1'), req_id=2),
                    _call('purlin_config', dict(root, action='read'), req_id=3)]
        stdout, _stderr = _child(
            project.root, ''.join(json.dumps(r) + '\n' for r in requests))
        lines = stdout.splitlines()
        assert len(lines) == 3, stdout
        answers = [json.loads(line) for line in lines]
        assert [(a['jsonrpc'], a['id']) for a in answers] == [
            ('2.0', 1), ('2.0', 2), ('2.0', 3)], stdout

    # purlin: server PROOF-2
    def test_tools_list_names_the_three_tools_each_taking_an_optional_root(
            self, project):
        responses, _stderr = _rpc(project.root, {
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})
        tools = responses[0]['result']['tools']
        assert sorted(t['name'] for t in tools) == [
            'drift', 'purlin_config', 'sync_status']
        for tool in tools:
            schema = tool['inputSchema']
            assert 'project_root' in schema['properties'], tool['name']
            assert 'project_root' not in schema.get('required', []), \
                tool['name']

    # purlin: server PROOF-3
    def test_the_initialized_notification_gets_no_response(self, project):
        responses, _stderr = _rpc(
            project.root,
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 9, 'method': 'tools/list'})
        assert [r['id'] for r in responses] == [9], responses

    # purlin: server PROOF-125
    def test_a_line_that_is_not_json_gets_a_parse_error(self, project):
        stdout, _stderr = _child(project.root, 'not json\n')
        lines = stdout.splitlines()
        assert len(lines) == 1, stdout
        assert json.loads(lines[0])['error']['code'] == -32700, stdout

    # purlin: server PROOF-127
    def test_an_unknown_method_is_an_error(self, project):
        responses, _stderr = _rpc(project.root, {
            'jsonrpc': '2.0', 'id': 2, 'method': 'nope/at/all'})
        assert responses[0]['error'] == {
            'code': -32601, 'message': 'Unknown method: nope/at/all'}


# ---------------------------------------------------------------------------
# Which project root a call answers for
# ---------------------------------------------------------------------------

def _status_from_the_home_folder(project, tmp_path, monkeypatch):
    """Start the server in an empty folder and ask for the status of `~/ws`,
    a copy of the project in the home folder; the answer's text."""
    monkeypatch.delenv('PURLIN_PROJECT_ROOT', raising=False)
    home, empty = tmp_path / 'home', tmp_path / 'empty'
    empty.mkdir()
    shutil.copytree(project.root, str(home / 'ws'), symlinks=True)
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('USERPROFILE', str(home))
    responses, _stderr = _rpc(str(empty), _call(
        'sync_status', {'project_root': '~/ws'}))
    return _text(responses[0])


class TestWhichProjectRoot:

    # purlin: server PROOF-129
    def test_a_workspace_named_from_the_home_folder_is_found(self, project,
                                                             tmp_path,
                                                             monkeypatch):
        text = _status_from_the_home_folder(project, tmp_path, monkeypatch)
        assert text.startswith('Purlin status: ws,'), text
        assert 'login' in text, text

    # purlin: server PROOF-160
    def test_on_windows_a_workspace_named_from_the_home_folder_is_found(
            self, project, tmp_path, monkeypatch):
        text = _status_from_the_home_folder(project, tmp_path, monkeypatch)
        assert text.startswith('Purlin status: ws,'), text
        assert 'login' in text, text

    # purlin: server PROOF-168
    def test_a_status_naming_an_empty_folder_says_no_project_is_there(
            self, project, tmp_path):
        empty = tmp_path / 'empty'
        empty.mkdir()
        responses, _stderr = _rpc(project.root, _call(
            'sync_status', {'project_root': str(empty)}))
        first = _text(responses[0]).split('\n')[0]
        assert first.startswith(
            'No Purlin project root at %s: .purlin/config.json is not there.'
            % empty), first

    # purlin: server PROOF-169
    def test_a_config_write_naming_an_empty_folder_writes_nothing(
            self, project, tmp_path):
        empty = tmp_path / 'empty'
        empty.mkdir()
        responses, _stderr = _rpc(project.root, _call(
            'purlin_config', {'action': 'write', 'key': 'tests', 'value': [],
                              'project_root': str(empty)}))
        text = _text(responses[0])
        assert text.startswith('No Purlin project root at'), text
        assert not os.path.exists(_config_file(str(empty))), text

    # purlin: server PROOF-166
    def test_a_call_naming_no_root_is_refused_in_one_line(self, project):
        responses, _stderr = _rpc(project.root, _call('sync_status'))
        text = _text(responses[0])
        assert text == ('sync_status needs project_root: pass the top folder '
                        'of the git checkout you are working in.'), text
        assert 'login' not in text, text

    # purlin: server PROOF-167
    def test_a_root_named_by_an_earlier_call_is_not_used_by_the_next(
            self, project, tmp_path):
        other = Project()
        try:
            before = _read_bytes(_config_file(project.root))
            responses, _stderr = _rpc(
                project.root,
                _call('sync_status', {'project_root': other.root}, req_id=1),
                _call('purlin_config', {'action': 'write', 'key': 'tests',
                                        'value': []}, req_id=2))
            assert _text(responses[0]).startswith('Purlin status:'), responses
            assert _text(responses[1]).startswith(
                'purlin_config needs project_root:'), responses
            assert _read_bytes(_config_file(project.root)) == before
        finally:
            other.close()


# ---------------------------------------------------------------------------
# A settings file that cannot be read
# ---------------------------------------------------------------------------

TRAILING_COMMA = '{\n  "tests": [],}\n'


def _unreadable(root):
    """Give the project a settings file with a trailing comma; its bytes and sentence."""
    with open(_config_file(root), 'wb') as handle:
        handle.write(TRAILING_COMMA.encode('utf-8'))
    with pytest.raises(json.JSONDecodeError) as refused:
        json.loads(TRAILING_COMMA)
    assert refused.value.lineno == 2
    return _read_bytes(_config_file(root)), (
        '.purlin/config.json cannot be read: %s at line 2. Fix the file by '
        'hand; nothing ran and nothing was saved.' % refused.value.msg)


class TestAnUnreadableSettingsFile:

    # purlin: server PROOF-141
    def test_the_configuration_tool_answers_the_sentence_and_writes_nothing(
            self, project):
        before, sentence = _unreadable(project.root)
        responses, _stderr = _rpc(project.root, _call(
            'purlin_config', {'action': 'write', 'key': 'tests', 'value': [],
                              'project_root': project.root}))
        assert _text(responses[0]) == sentence
        assert _read_bytes(_config_file(project.root)) == before


# ---------------------------------------------------------------------------
# A tool that fails
# ---------------------------------------------------------------------------

class TestAToolThatFails:

    # purlin: server PROOF-133
    def test_the_session_answers_the_call_after_a_failure(self, project,
                                                          monkeypatch):
        real, calls = purlin_srv.status_module.sync_status, []

        def fails_once(root):
            calls.append(root)
            if len(calls) == 1:
                raise RuntimeError('boom')
            return real(root)

        monkeypatch.setattr(purlin_srv.status_module, 'sync_status',
                            fails_once)
        root = {'project_root': project.root}
        responses, _stderr = _rpc(project.root,
                                  _call('sync_status', root, req_id=1),
                                  _call('sync_status', root, req_id=2))
        assert [r['id'] for r in responses] == [1, 2], responses
        texts = [_text(r) for r in responses]
        assert texts[0] == 'Error running sync_status: boom', texts
        assert texts[1].startswith('Purlin status: '), texts
        assert 'login' in texts[1], texts


# ---------------------------------------------------------------------------
# The configuration tool
# ---------------------------------------------------------------------------

def _settings(root, data):
    """Write `data` as the project's whole settings file."""
    with open(_config_file(root), 'w', encoding='utf-8') as handle:
        json.dump(data, handle)


def _configure(project, arguments, req_id=1):
    """The configuration tool's answer to one call naming the project."""
    responses, _stderr = _rpc(project.root, _call(
        'purlin_config', dict(arguments, project_root=project.root),
        req_id=req_id))
    return _text(responses[0])


class TestTheConfigurationTool:

    # purlin: server PROOF-9
    def test_a_read_of_tests_answers_that_key(self, project):
        _settings(project.root, {'version': _version(), 'tests': []})
        text = _configure(project, {'action': 'read', 'key': 'tests'})
        assert text == json.dumps({'tests': []}, indent=2), text
        assert json.loads(text) == {'tests': []}, text

    # purlin: server PROOF-134
    def test_a_write_of_tests_sets_it_and_keeps_the_version(self, project):
        _settings(project.root, {'version': _version(), 'tests': []})
        text = _configure(project, {'action': 'write', 'key': 'tests',
                                    'value': [{'name': 'pytest'}]})
        assert text == ('tests is now [{"name": "pytest"}]; saved to '
                        '.purlin/config.json.'), text
        with open(_config_file(project.root), encoding='utf-8') as handle:
            on_disk = json.load(handle)
        assert on_disk == {'version': _version(),
                           'tests': [{'name': 'pytest'}]}, on_disk

    # purlin: server PROOF-142
    def test_a_read_of_an_absent_tests_answers_it_as_null(self, project):
        _settings(project.root, {'version': _version()})
        text = _configure(project, {'action': 'read', 'key': 'tests'})
        assert text == '{\n  "tests": null\n}', text


def _refused(project, arguments):
    """The configuration tool's answer to a write, asserting the file is unchanged."""
    before = _read_bytes(_config_file(project.root))
    text = _configure(project, dict(arguments, action='write'))
    assert _read_bytes(_config_file(project.root)) == before
    return text


class TestAWriteTheToolRefuses:

    # purlin: server PROOF-151
    def test_tests_given_as_text_is_refused(self, project):
        assert _refused(project, {'key': 'tests', 'value': 'pytest'}) == (
            '"pytest" is not accepted for tests; it takes a list. Nothing was '
            'saved.')

    # purlin: server PROOF-155
    def test_a_write_of_the_version_is_refused(self, project):
        assert _refused(project, {'key': 'version', 'value': '9.9.9'}) == (
            "version is written by purlin:init from Purlin's own version; "
            "nothing was saved.")

    # purlin: server PROOF-164
    def test_a_write_of_gate_is_refused(self, project):
        assert _refused(project, {'key': 'gate', 'value': 'signed'}) == (
            'gate is not a setting; .purlin/config.json holds version and '
            'tests. Nothing was saved.')


# ---------------------------------------------------------------------------
# How Claude Code starts the server
# ---------------------------------------------------------------------------

def _manifest_entry():
    with open(os.path.join(PROJECT_ROOT, '.claude-plugin', 'plugin.json'),
              encoding='utf-8') as handle:
        return json.load(handle)['mcpServers']['purlin']


class TestThePluginManifest:

    # purlin: server PROOF-137
    def test_the_manifest_command_starts_a_server_that_answers(self, project):
        entry = _manifest_entry()
        # On Windows `sh` is the one Git for Windows puts on the search path.
        assert shutil.which(entry['command']), (
            '%s is not on the search path' % entry['command'])
        command = [entry['command']] + [
            arg.replace('${CLAUDE_PLUGIN_ROOT}', PROJECT_ROOT)
            for arg in entry['args']]
        env = dict(os.environ, PURLIN_PYTHON=sys.executable)
        stdout, stderr = _child(project.root, json.dumps(_initialize()) + '\n',
                                command=command, env=env)
        lines = stdout.splitlines()
        assert len(lines) == 1, (stdout, stderr)
        assert json.loads(lines[0])['result']['serverInfo']['name'] == \
            'purlin', stdout

    # purlin: server PROOF-158
    def test_the_plugin_entry_asks_the_resolver_for_a_soft_exit(self):
        entry = _manifest_entry()
        assert entry['env'] == {'PURLIN_PYTHON_SOFT': '1'}, entry
        assert entry['command'] == 'sh' and entry['args'], entry


LOOKUP = os.path.join(PROJECT_ROOT, 'scripts', 'purlin_python.sh')
NO_PYTHON = ('purlin: no Python 3 interpreter found; tried $PURLIN_PYTHON, '
             'python3, python and py -3. Set PURLIN_PYTHON to the one to use.\n')


def _lookup_with_no_python(tmp_path, soft=None):
    """Start the resolver on the server with a search path holding nothing."""
    empty = tmp_path / 'no-python'
    empty.mkdir()
    env = {'PATH': str(empty)}
    if soft is not None:
        env['PURLIN_PYTHON_SOFT'] = soft
    return subprocess.run(['/bin/sh', LOOKUP, SERVER_PY], capture_output=True,
                          text=True, env=env, cwd=str(tmp_path), timeout=60)


class TestTheInterpreterResolver:

    # purlin: server PROOF-156
    def test_no_python_fails_loudly(self, tmp_path):
        result = _lookup_with_no_python(tmp_path)
        assert (result.returncode, result.stdout, result.stderr) == (
            1, '', NO_PYTHON)

    # purlin: server PROOF-157
    def test_no_python_with_the_soft_variable_exits_0(self, tmp_path):
        result = _lookup_with_no_python(tmp_path, soft='1')
        assert (result.returncode, result.stdout, result.stderr) == (
            0, '', NO_PYTHON)


class TestPackageHygiene:
    """What the package may not do, whatever else it does."""

    def test_every_open_passes_an_encoding(self):
        package = os.path.join(PROJECT_ROOT, 'scripts', 'mcp', 'purlin')
        offenders = []
        for name in sorted(os.listdir(package)):
            if not name.endswith('.py'):
                continue
            with open(os.path.join(package, name), encoding='utf-8') as handle:
                for number, line in enumerate(handle, 1):
                    if re.search(r'(?<!\w)open\(', line) and 'encoding=' not in line:
                        offenders.append('%s:%d %s' % (name, number, line.strip()))
        assert offenders == [], offenders

    def test_the_package_imports_nothing_outside_the_standard_library(self):
        package = os.path.join(PROJECT_ROOT, 'scripts', 'mcp', 'purlin')
        allowed = set(sys.stdlib_module_names) if hasattr(
            sys, 'stdlib_module_names') else set()
        local = {'purlin', 'config_engine', 'package'}
        offenders = []
        for name in sorted(os.listdir(package)):
            if not name.endswith('.py'):
                continue
            with open(os.path.join(package, name), encoding='utf-8') as handle:
                for line in handle:
                    m = re.match(r'\s*(?:import|from)\s+([A-Za-z_][\w.]*)', line)
                    if not m:
                        continue
                    top = m.group(1).split('.')[0]
                    if top in local or not allowed or top in allowed:
                        continue
                    offenders.append('%s: %s' % (name, line.strip()))
        assert offenders == [], offenders
