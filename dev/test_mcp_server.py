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

from mcp_project import PROJECT_ROOT, SERVER_PY, _rpc, project
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
                            cwd=root, env=env, timeout=180)
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

    # purlin: server PROOF-5
    def test_stdout_holds_the_answer_alone_and_the_startup_line_is_on_stderr(
            self, project):
        stdout, stderr = _child(project.root, json.dumps(_initialize()) + '\n')
        lines = stdout.splitlines()
        assert len(lines) == 1, stdout
        answer = json.loads(lines[0])
        assert answer['jsonrpc'] == '2.0' and answer['id'] == 1, answer
        assert 'Purlin MCP server' not in stdout, stdout
        started = re.search(r'Purlin MCP server v(\S+) started \(root: (.+?), ',
                            stderr)
        assert started, stderr
        assert started.group(1) == _version(), stderr
        assert os.path.realpath(started.group(2)) == os.path.realpath(
            project.root), stderr

    # purlin: server PROOF-138
    def test_stdout_holds_one_answer_per_tool_call_and_nothing_else(
            self, project):
        requests = [_call('sync_status', req_id=1),
                    _call('drift', {'since': '1'}, req_id=2),
                    _call('purlin_config', {'action': 'read'}, req_id=3)]
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

    def test_sync_status_answers_the_table(self, project):
        responses, _stderr = _rpc(project.root, _call('sync_status', req_id=2))
        text = _text(responses[0])
        assert 'Spec' in text and 'Tests' in text and 'login' in text

    def test_drift_answers_json(self, project):
        responses, _stderr = _rpc(project.root,
                                  _call('drift', {'since': '1'}))
        report = json.loads(_text(responses[0]))
        assert sorted(report) == ['roles', 'since'], sorted(report)
        assert sorted(report['roles']) == ['eng', 'pm', 'qa']

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

    # purlin: server PROOF-126
    def test_a_notification_the_server_does_not_know_gets_no_response(
            self, project):
        responses, _stderr = _rpc(
            project.root,
            {'jsonrpc': '2.0', 'method': 'notifications/cancelled',
             'params': {'requestId': 3}},
            {'jsonrpc': '2.0', 'id': 9, 'method': 'tools/list'})
        assert [r['id'] for r in responses] == [9], responses

    # purlin: server PROOF-4
    def test_an_unknown_tool_is_an_error(self, project):
        responses, _stderr = _rpc(project.root, _call('nope'))
        assert responses[0]['error'] == {'code': -32601,
                                         'message': 'Unknown tool: nope'}

    # purlin: server PROOF-127
    def test_an_unknown_method_is_an_error(self, project):
        responses, _stderr = _rpc(project.root, {
            'jsonrpc': '2.0', 'id': 2, 'method': 'nope/at/all'})
        assert responses[0]['error'] == {
            'code': -32601, 'message': 'Unknown method: nope/at/all'}


# ---------------------------------------------------------------------------
# Which workspace a call answers for
# ---------------------------------------------------------------------------

def _named_then_unnamed(project, empty, monkeypatch):
    """Start the server in `empty`; call status naming the workspace, then naming none."""
    monkeypatch.delenv('PURLIN_PROJECT_ROOT', raising=False)
    responses, _stderr = _rpc(
        str(empty),
        _call('sync_status', {'project_root': project.root}, req_id=1),
        _call('sync_status', {}, req_id=2))
    return [_text(r) for r in responses]


class TestWhichWorkspace:

    # purlin: server PROOF-6
    def test_a_call_naming_a_workspace_answers_for_it(self, project, tmp_path,
                                                      monkeypatch):
        named, _unnamed = _named_then_unnamed(project, tmp_path, monkeypatch)
        assert named.startswith('Purlin status: proj'), named
        assert 'login' in named, named

    # purlin: server PROOF-128
    def test_the_named_workspace_is_for_that_call_alone(self, project,
                                                        tmp_path, monkeypatch):
        _named, unnamed = _named_then_unnamed(project, tmp_path, monkeypatch)
        assert unnamed.startswith('No Purlin workspace at %s:' % os.path.realpath(
            str(tmp_path))), unnamed

    # purlin: server PROOF-129
    def test_a_workspace_named_from_the_home_folder_is_found(self, project,
                                                             tmp_path,
                                                             monkeypatch):
        monkeypatch.delenv('PURLIN_PROJECT_ROOT', raising=False)
        home, empty = tmp_path / 'home', tmp_path / 'empty'
        empty.mkdir()
        shutil.copytree(project.root, str(home / 'ws'), symlinks=True)
        monkeypatch.setenv('HOME', str(home))
        monkeypatch.setenv('USERPROFILE', str(home))
        responses, _stderr = _rpc(str(empty), _call(
            'sync_status', {'project_root': '~/ws'}))
        text = _text(responses[0])
        assert text.startswith('Purlin status: proj'), text
        assert 'login' in text, text

    # purlin: server PROOF-7
    def test_a_root_with_no_workspace_says_so_rather_than_reporting_nothing(
            self, tmp_path, monkeypatch):
        monkeypatch.delenv('PURLIN_PROJECT_ROOT', raising=False)
        responses, _stderr = _rpc(str(tmp_path), _call('sync_status'))
        text = _text(responses[0])
        first, _newline, rest = text.partition('\n')
        assert first == (
            'No Purlin workspace at %s: .purlin/config.json is not there. '
            'That root came from the working directory, with no .purlin/ '
            'marker in it or above it.' % os.path.realpath(str(tmp_path))), text
        assert 'purlin:init' in rest, text
        assert 'Tests' not in text and 'Rules' not in text, text
        assert 'No specs found' not in text, text

    # purlin: server PROOF-130
    def test_a_named_root_with_no_workspace_says_it_came_from_the_argument(
            self, project, tmp_path):
        responses, _stderr = _rpc(project.root, _call(
            'sync_status', {'project_root': str(tmp_path)}))
        text = _text(responses[0])
        assert text.startswith('No Purlin workspace at %s:' % tmp_path), text
        assert 'That root came from the project_root argument.' in text, text

    # purlin: server PROOF-131
    def test_a_config_write_where_there_is_no_workspace_writes_nothing(
            self, tmp_path, monkeypatch):
        monkeypatch.delenv('PURLIN_PROJECT_ROOT', raising=False)
        responses, _stderr = _rpc(str(tmp_path), _call(
            'purlin_config', {'action': 'write', 'key': 'gate',
                              'value': 'strong'}))
        text = _text(responses[0])
        assert text.startswith('No Purlin workspace at'), text
        assert not os.path.exists(_config_file(str(tmp_path))), text

    # purlin: server PROOF-132
    def test_drift_where_there_is_no_workspace_says_so(self, tmp_path,
                                                       monkeypatch):
        monkeypatch.delenv('PURLIN_PROJECT_ROOT', raising=False)
        responses, _stderr = _rpc(str(tmp_path), _call('drift'))
        text = _text(responses[0])
        assert text.startswith('No Purlin workspace at %s:' % os.path.realpath(
            str(tmp_path))), text


# ---------------------------------------------------------------------------
# A tool that fails
# ---------------------------------------------------------------------------

class TestAToolThatFails:

    # purlin: server PROOF-8
    def test_a_tool_that_raises_answers_its_error_as_text(self, project,
                                                          monkeypatch):
        def boom(_root):
            raise RuntimeError('boom')

        monkeypatch.setattr(purlin_srv.status_module, 'sync_status', boom)
        responses, _stderr = _rpc(project.root, _call('sync_status'))
        assert 'error' not in responses[0], responses
        assert _text(responses[0]) == 'Error running sync_status: boom'

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
        responses, _stderr = _rpc(project.root,
                                  _call('sync_status', req_id=1),
                                  _call('sync_status', req_id=2))
        assert [r['id'] for r in responses] == [1, 2], responses
        texts = [_text(r) for r in responses]
        assert texts[0] == 'Error running sync_status: boom', texts
        assert texts[1].startswith('Purlin status: proj'), texts
        assert 'login' in texts[1], texts


# ---------------------------------------------------------------------------
# The configuration tool
# ---------------------------------------------------------------------------

class TestTheConfigurationTool:

    # purlin: server PROOF-9
    def test_a_read_of_one_key_answers_that_key(self, project):
        responses, _stderr = _rpc(project.root, _call(
            'purlin_config', {'action': 'read', 'key': 'gate'}))
        assert json.loads(_text(responses[0])) == {'gate': 'passed'}

    # purlin: server PROOF-134
    def test_a_write_sets_the_key_in_the_settings_file(self, project):
        with open(_config_file(project.root), encoding='utf-8') as handle:
            before = json.load(handle)
        responses, _stderr = _rpc(
            project.root,
            _call('purlin_config', {'action': 'write', 'key': 'gate',
                                    'value': 'strong'}, req_id=1),
            _call('purlin_config', {'action': 'read', 'key': 'gate'},
                  req_id=2))
        assert _text(responses[0]) == 'Set \'gate\' = "strong"', responses
        with open(_config_file(project.root), encoding='utf-8') as handle:
            on_disk = json.load(handle)
        assert on_disk == dict(before, gate='strong'), on_disk
        assert json.loads(_text(responses[1])) == {'gate': 'strong'}

    # purlin: server PROOF-135
    def test_a_read_naming_no_key_answers_the_whole_file(self, project):
        responses, _stderr = _rpc(project.root, _call(
            'purlin_config', {'action': 'read'}))
        whole = json.loads(_text(responses[0]))
        with open(_config_file(project.root), encoding='utf-8') as handle:
            on_disk = json.load(handle)
        assert whole == on_disk, whole
        assert sorted(whole) == ['gate', 'project_name', 'tests'], whole

    # purlin: server PROOF-10
    def test_a_write_naming_no_key_is_refused(self, project):
        before = _read_bytes(_config_file(project.root))
        responses, _stderr = _rpc(project.root, _call(
            'purlin_config', {'action': 'write', 'value': 'x'}))
        assert _text(responses[0]) == \
            "Error: 'key' is required for write action."
        assert _read_bytes(_config_file(project.root)) == before

    # purlin: server PROOF-136
    def test_an_unknown_action_is_refused(self, project):
        before = _read_bytes(_config_file(project.root))
        responses, _stderr = _rpc(project.root, _call(
            'purlin_config', {'action': 'delete', 'key': 'gate'}))
        assert _text(responses[0]) == \
            "Unknown action: delete. Use 'read' or 'write'."
        assert _read_bytes(_config_file(project.root)) == before


# ---------------------------------------------------------------------------
# How Claude Code starts the server
# ---------------------------------------------------------------------------

def _manifest_entry():
    with open(os.path.join(PROJECT_ROOT, '.claude-plugin', 'plugin.json'),
              encoding='utf-8') as handle:
        return json.load(handle)['mcpServers']['purlin']


class TestThePluginManifest:

    # purlin: server PROOF-22
    def test_the_plugin_entry_point_names_the_package(self):
        entry = _manifest_entry()
        assert entry['command'] == 'sh', entry
        args = entry['args']
        assert args[0].endswith('scripts/purlin_python.sh'), args
        assert args[-1].endswith('scripts/mcp/purlin/server.py'), args

    # purlin: server PROOF-137
    def test_the_manifest_command_starts_a_server_that_answers(self, project):
        entry = _manifest_entry()
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
        local = {'purlin', 'config_engine'}
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
