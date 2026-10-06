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

from mcp_project import (NO_PROOF_SPEC, PROJECT_ROOT, SERVER_PY, SPEC, Project,
                         _commit_tests, _entry, _git, _report_held, _rpc,
                         _write, project)
# `mcp_project` puts `scripts/mcp` on the path.
from purlin import evidence as purlin_evidence
from purlin import server as purlin_srv
from purlin import status as purlin_status


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
        # A JSON-RPC answer holds `jsonrpc`, `id` and its `result`, and no
        # other member: each of the three tools answers one text.
        assert [sorted(a) for a in answers] == [
            ['id', 'jsonrpc', 'result']] * 3, stdout
        for answer in answers:
            content = answer['result']['content']
            assert [sorted(part) for part in content] == [
                ['text', 'type']], answer
            assert content[0]['type'] == 'text', answer
            assert type(content[0]['text']) is str and content[0]['text'], \
                answer

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
        assert _text(responses[0]) == (
            'No Purlin project root at %s: .purlin/config.json is not there. '
            'Run purlin:init.' % empty), responses

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
# Purlin's own folder
# ---------------------------------------------------------------------------

def _plugin_copy(tmp_path):
    """A copy of the plugin that is also a project: `scripts/` and `VERSION`,
    `.purlin/config.json` and the spec `login`, committed. Its real path."""
    copy = os.path.join(os.path.realpath(str(tmp_path)), 'plugin')
    shutil.copytree(os.path.join(PROJECT_ROOT, 'scripts'),
                    os.path.join(copy, 'scripts'),
                    ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy(os.path.join(PROJECT_ROOT, 'VERSION'), copy)
    _write(os.path.join(copy, '.purlin', 'config.json'),
           json.dumps({'version': _version(), 'tests': []}))
    _write(os.path.join(copy, '.gitignore'), '.purlin/runtime/\n')
    _write(os.path.join(copy, 'specs', 'auth', 'login.md'), SPEC)
    _git(copy, 'init', '-q')
    _git(copy, 'config', 'user.email', 'dev@example.com')
    _git(copy, 'config', 'user.name', 'Dev')
    _git(copy, 'config', 'commit.gpgsign', 'false')
    _git(copy, 'add', '-A')
    _git(copy, 'commit', '-q', '-m', 'chore: a copy of the plugin')
    return copy


def _status_of_the_copy(copy, started_in, monkeypatch):
    """What the copy's own server, started in `started_in`, answers a
    `sync_status` naming the copy."""
    monkeypatch.delenv('PURLIN_PROJECT_ROOT', raising=False)
    stdout, stderr = _child(
        started_in,
        json.dumps(_call('sync_status', {'project_root': copy})) + '\n',
        command=[sys.executable, os.path.join(
            copy, 'scripts', 'mcp', 'purlin', 'server.py')])
    lines = stdout.splitlines()
    assert len(lines) == 1, (stdout, stderr)
    return _text(json.loads(lines[0]))


class TestPurlinsOwnFolder:

    # purlin: server PROOF-170
    def test_the_copy_named_from_another_workspace_is_refused(
            self, project, tmp_path, monkeypatch):
        copy = _plugin_copy(tmp_path)
        text = _status_of_the_copy(copy, project.root, monkeypatch)
        assert text == (
            "%s is Purlin's own folder, not your project. Pass the top folder "
            "of the git checkout you are working in." % copy), text

    # purlin: server PROOF-171
    def test_a_server_started_in_the_copy_answers_for_it(
            self, tmp_path, monkeypatch):
        copy = _plugin_copy(tmp_path)
        text = _status_of_the_copy(copy, copy, monkeypatch)
        assert text.startswith('Purlin status:'), text
        assert 'login' in text, text

    # purlin: server PROOF-172
    def test_a_server_started_in_a_second_checkout_answers_for_the_copy(
            self, tmp_path, monkeypatch):
        copy = _plugin_copy(tmp_path)
        second = os.path.join(os.path.dirname(copy), 'second')
        added = _git(copy, 'worktree', 'add', '-q', second)
        assert added.returncode == 0, added.stderr
        text = _status_of_the_copy(copy, second, monkeypatch)
        assert text.startswith('Purlin status:'), text
        assert 'login' in text, text


# ---------------------------------------------------------------------------
# The status and drift scripts
# ---------------------------------------------------------------------------

STATUS_PY = os.path.join(PROJECT_ROOT, 'scripts', 'run', 'purlin_status.py')
DRIFT_PY = os.path.join(PROJECT_ROOT, 'scripts', 'run', 'purlin_drift.py')


def _script(script, root, *args):
    """A script started in `root` on `--project-root <root>`: `(exit code, stdout)`."""
    result = subprocess.run(
        [sys.executable, script, '--project-root', root] + list(args),
        capture_output=True, text=True, encoding='utf-8', cwd=root,
        stdin=subprocess.DEVNULL, timeout=180)
    return result.returncode, result.stdout


class TestTheStatusScript:

    # purlin: server PROOF-173
    def test_it_prints_what_the_tool_answers(self, project):
        code, printed = _script(STATUS_PY, project.root)
        assert printed == purlin_status.sync_status(project.root) + '\n'
        assert printed.startswith('Purlin status:') and 'login' in printed
        assert code == 0, printed
        # The text the tool answers, asked of the server as a client asks it.
        responses, _stderr = _rpc(project.root, _call(
            'sync_status', {'project_root': project.root}))
        assert len(responses) == 1, responses
        assert printed == _text(responses[0]) + '\n', (printed, responses)
        assert printed.splitlines()[0] == 'Purlin status: %s, plugin %s' % (
            os.path.basename(project.root), _version()), printed

    # purlin: server PROOF-174
    def test_an_empty_folder_is_refused_in_one_line(self, tmp_path):
        empty = str(tmp_path / 'empty')
        os.mkdir(empty)
        code, printed = _script(STATUS_PY, empty)
        assert printed == (
            'No Purlin project root at %s: .purlin/config.json is not there. '
            'Run purlin:init.\n' % empty), printed
        assert code == 1, printed

    # purlin: server PROOF-175
    def test_a_spec_with_a_mistake_prints_its_warning_first(self, project):
        project.spec(SPEC.replace('> Scope:', '> Requires: api\n> Scope:'))
        code, printed = _script(STATUS_PY, project.root, '--spec', 'login')
        assert printed.splitlines()[:3] == [
            'login: > Requires: is not read, because every anchor covers the '
            'whole project. Run purlin:spec login.',
            '',
            'specs/auth/login.md: 2 rules'], printed
        assert code == 1, printed

    # purlin: server PROOF-176
    def test_a_spec_with_no_mistake_opens_on_its_view(self, project):
        project.spec(SPEC + '- PROOF-3 (RULE-2): POST /login with no '
                     'password; verify 401\n')
        code, printed = _script(STATUS_PY, project.root, '--spec', 'login')
        assert printed.splitlines()[0] == 'specs/auth/login.md: 2 rules', printed
        assert 'mistake' not in printed, printed
        assert code == 0, printed
        # The view of 2 rules and 3 proofs is all it prints: no line before
        # it, and none after its last proof.
        assert printed == (
            'specs/auth/login.md: 2 rules\n'
            '  RULE-1  no test  waiting\n'
            '    no test: no test for PROOF-1\n'
            '    PROOF-1  no test\n'
            '  RULE-2  no test  waiting\n'
            '    no test: no test for PROOF-2, PROOF-3\n'
            '    PROOF-2  no test\n'
            '    PROOF-3  no test\n'), printed

    # purlin: server PROOF-178
    def test_a_name_no_spec_has_is_said_so(self, project):
        code, printed = _script(STATUS_PY, project.root, '--spec', 'signup')
        assert printed == ('signup: no spec of this checkout has that name. '
                           'Run purlin:status to see its specs.\n'), printed
        assert code == 1, printed


def _one_of_two_tested(project):
    """`login`: `RULE-1`'s test passed in a current section, `RULE-2` with
    no test."""
    _commit_tests(project, 'PROOF-1')
    project.evidence([_entry('PROOF-1', 'RULE-1')])


def _view(project, name='login'):
    code, printed = _script(STATUS_PY, project.root, '--spec', name)
    assert code == 0, printed
    return printed.splitlines()


def _under(lines, line):
    """The lines after `line`, up to the next rule's line."""
    out = []
    for text in lines[lines.index(line) + 1:]:
        if text.startswith('  RULE-'):
            break
        out.append(text)
    return out


class TestOneSpecsView:

    # purlin: server PROOF-179
    def test_it_opens_on_the_path_then_one_line_per_rule(self, project):
        _one_of_two_tested(project)
        lines = _view(project)
        assert lines[0] == 'specs/auth/login.md: 2 rules', lines
        assert [line for line in lines if line.startswith('  RULE-')] == [
            '  RULE-1  passed  not audited', '  RULE-2  no test  waiting'], lines

    # purlin: server PROOF-180
    def test_an_anchor_is_shown_as_a_feature_is(self, project):
        project.spec('# Anchor: security\n\n## Rules\n\n- RULE-1: No eval '
                     'anywhere\n\n## Proof\n\n- PROOF-1 (RULE-1): Grep for '
                     'eval(; verify 0 matches\n', name='security',
                     category='_anchors')
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'anchor(security): create')
        lines = _view(project, 'security')
        assert lines[:2] == ['specs/_anchors/security.md: 1 rule',
                             '  RULE-1  no test  waiting'], lines

    # purlin: server PROOF-181
    def test_a_cell_that_needs_work_gives_its_reasons_and_no_other_does(
            self, project):
        _one_of_two_tested(project)
        lines = _view(project)
        # Exactly the two lines under `RULE-2`, and exactly the one under
        # `RULE-1`: no reason for a cell that needs no work, no line twice.
        assert _under(lines, '  RULE-2  no test  waiting') == [
            '    no test: no test for PROOF-2',
            '    PROOF-2  no test'], lines
        assert _under(lines, '  RULE-1  passed  not audited') == [
            '    PROOF-1  passed  tests/test_login.py::test_proof_1'], lines
        assert lines == [
            'specs/auth/login.md: 2 rules',
            '  RULE-1  passed  not audited',
            '    PROOF-1  passed  tests/test_login.py::test_proof_1',
            '  RULE-2  no test  waiting',
            '    no test: no test for PROOF-2',
            '    PROOF-2  no test'], lines

    # purlin: server PROOF-182
    def test_a_strong_rule_shows_no_reason(self, project):
        _one_of_two_tested(project)
        project.audit('RULE-1')
        lines = _view(project)
        # The one line under it: no reason, and the test named once.
        assert _under(lines, '  RULE-1  passed  strong') == [
            '    PROOF-1  passed  tests/test_login.py::test_proof_1'], lines
        assert lines[1:4] == [
            '  RULE-1  passed  strong',
            '    PROOF-1  passed  tests/test_login.py::test_proof_1',
            '  RULE-2  no test  waiting'], lines

    # purlin: server PROOF-183
    def test_each_rule_ends_on_its_proof_lines(self, project):
        _one_of_two_tested(project)
        lines = _view(project)
        assert _under(lines, '  RULE-1  passed  not audited')[-1] == (
            '    PROOF-1  passed  tests/test_login.py::test_proof_1'), lines
        assert lines[-1] == '    PROOF-2  no test', lines

    # purlin: server PROOF-184
    def test_a_proof_of_two_tests_sets_the_second_under_the_first(
            self, project):
        _write(os.path.join(project.root, 'tests', 'test_login.py'),
               '# purlin: login PROOF-1\ndef test_proof_1():\n    pass\n\n'
               '# purlin: login PROOF-1\ndef test_proof_1_again():\n'
               '    pass\n')
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'test(login): two tests')
        again = dict(_entry('PROOF-1', 'RULE-1'),
                     test_name='test_proof_1_again')
        project.evidence([_entry('PROOF-1', 'RULE-1'), again])
        lines = _view(project)
        assert _under(lines, '  RULE-1  passed  not audited') == [
            '    PROOF-1  passed  tests/test_login.py::test_proof_1',
            '                     tests/test_login.py::test_proof_1_again'], \
            lines

    # purlin: server PROOF-185
    def test_a_rule_with_no_proof_lists_the_tests_marked_with_its_id(self):
        made = Project(spec=NO_PROOF_SPEC)
        try:
            _write(os.path.join(made.root, 'tests', 'test_login.py'),
                   '# purlin: login RULE-1\ndef test_rule_1():\n    pass\n')
            _git(made.root, 'add', '-A')
            _git(made.root, 'commit', '-q', '-m', 'test(login): RULE-1')
            made.evidence([_entry('RULE-1', 'RULE-1')])
            lines = _view(made)
        finally:
            made.close()
        assert lines[-1] == '    RULE-1  tests/test_login.py::test_rule_1', lines


def _carry(project, taken_at, ids=None, feature='login'):
    """Mark the results of `feature`'s local section as carried forward
    from the commit `taken_at`, those of `ids` or all, and commit it."""
    rel = os.path.join('.purlin', 'evidence', 'local', '%s.json' % feature)
    path = os.path.join(project.root, rel)
    with open(path, encoding='utf-8') as handle:
        data = json.load(handle)
    for section in data['platforms'].values():
        for entry in section['proofs']:
            if ids is None or entry['id'] in ids:
                entry['carried'] = {
                    'commit': taken_at, 'at': '2026-09-12T08:00:00Z',
                    'machine': 'dana-laptop', 'email': 'dana@example.com'}
    _write(path, json.dumps(data, indent=2, sort_keys=True) + '\n')
    _git(project.root, 'add', '-A')
    _git(project.root, 'commit', '-q', '-m', 'purlin: evidence carried')


class TestACarriedResultInTheView:

    # purlin: server PROOF-186
    def test_a_carried_proof_names_the_commit_and_the_system(self, project):
        _one_of_two_tested(project)
        _carry(project, 'a1b2c3d4' * 5)
        lines = _view(project)
        assert _under(lines, '  RULE-1  passed  not audited') == [
            '    PROOF-1  passed  tests/test_login.py::test_proof_1',
            '      carried forward from a1b2c3d on %s'
            % purlin_evidence.os_word(purlin_evidence.host_os())], lines

    # purlin: server PROOF-187
    def test_a_result_the_run_took_has_no_such_line(self, project):
        _one_of_two_tested(project)
        assert not any('carried forward' in line for line in _view(project))

    # purlin: server PROOF-188
    def test_a_carried_test_of_a_rule_with_no_proof_is_named_too(self):
        made = Project(spec=NO_PROOF_SPEC)
        try:
            _write(os.path.join(made.root, 'tests', 'test_login.py'),
                   '# purlin: login RULE-1\ndef test_rule_1():\n    pass\n')
            _git(made.root, 'add', '-A')
            _git(made.root, 'commit', '-q', '-m', 'test(login): RULE-1')
            made.evidence([_entry('RULE-1', 'RULE-1')])
            _carry(made, 'a1b2c3d4' * 5)
            lines = _view(made)
        finally:
            made.close()
        assert lines[-2:] == [
            '    RULE-1  tests/test_login.py::test_rule_1',
            '      carried forward from a1b2c3d on %s'
            % purlin_evidence.os_word(purlin_evidence.host_os())], lines


class TestAFailingTestsTextInTheView:

    @staticmethod
    def _failing(project):
        _commit_tests(project, 'PROOF-1')
        project.evidence([_entry('PROOF-1', 'RULE-1', status='fail')])

    # purlin: server PROOF-189
    def test_a_failing_test_gives_the_first_line_its_tool_reported(
            self, project):
        self._failing(project)
        _report_held(project, "AssertionError: expected 'Account locked'\n\n"
                              'def test_proof_1():\n>       assert shown == '
                              "'Account locked'")
        lines = _view(project)
        rule = next(line for line in lines if line.startswith('  RULE-1'))
        under = _under(lines, rule)
        at = under.index('    PROOF-1  failed  tests/test_login.py::'
                         'test_proof_1')
        assert under[at + 1:] == [
            "      failed with: AssertionError: expected 'Account locked'"], \
            lines

    # purlin: server PROOF-190
    def test_a_long_first_line_is_cut_at_200_characters(self, project):
        self._failing(project)
        _report_held(project, 'x' * 250 + '\nsecond line')
        lines = _view(project)
        assert ('      failed with: ' + 'x' * 200 + '...') in lines, lines
        assert not any('second line' in line for line in lines), lines

    # purlin: server PROOF-191
    def test_a_failing_test_with_no_text_kept_has_no_such_line(self, project):
        self._failing(project)
        lines = _view(project)
        assert ('    PROOF-1  failed  tests/test_login.py::test_proof_1'
                in lines), lines
        assert not any('failed with' in line for line in lines), lines


class TestTheDriftScript:

    # purlin: server PROOF-177
    def test_it_prints_the_view_one_line_per_line(self, project, tmp_path):
        checkout = str(tmp_path / 'checkout')
        cloned = subprocess.run(['git', 'clone', '-q', project.root, checkout],
                                capture_output=True, text=True)
        assert cloned.returncode == 0, cloned.stderr
        project.spec(SPEC.replace(
            '\n\n## Proof', '\n- RULE-3: Five wrong passwords lock the '
            'account\n\n## Proof'))
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'spec(login): RULE-3')
        pulled = _git(checkout, 'pull', '-q', '--no-rebase')
        assert pulled.returncode == 0, pulled.stderr
        code, printed = _script(DRIFT_PY, checkout)
        lines = printed.splitlines()
        assert lines[0].startswith('Since your last pull, '), printed
        assert lines[1:] == ['1 rule added: login RULE-3.'], printed
        assert code == 0, printed
        # The whole line naming the range: how long ago, the commit the
        # checkout was at, the one it is at now, and the 1 commit between.
        before, after = _git(project.root, 'rev-parse', 'HEAD~1',
                             'HEAD').stdout.split()
        assert re.fullmatch(
            r'Since your last pull, \d+ seconds? ago \(%s\.\.%s, 1 commit\)\.'
            % (before[:7], after[:7]), lines[0]), printed
        assert printed.endswith('.\n1 rule added: login RULE-3.\n'), printed


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
        # The status table once over: its opening lines, its one row naming
        # `login`, and the one line it ends on.
        table = texts[1].splitlines()
        assert table[:8] == [
            'Purlin status: %s, plugin %s' % (
                os.path.basename(project.root), _version()),
            'Tests: not met',
            'Sign-off: not signed',
            '',
            'Spec   Rules  Proofs         Tests',
            '\u2500' * 35,
            'login  2      2 \u00b7 2 no test  0 of 2',
            '\u2500' * 35], texts
        assert [line for line in table if line.startswith('login')] == [
            'login  2      2 \u00b7 2 no test  0 of 2'], texts
        assert [line for line in table
                if line.startswith('Purlin status: ')] == table[:1], texts
        assert texts[1].count('Purlin status: ') == 1, texts
        assert table[-1] == ('  2 rules to write a test for: purlin:build'), \
            texts
        assert len(calls) == 2, calls


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
        # As Claude Code starts it: the manifest's own environment and no
        # `PURLIN_PYTHON`, so the resolver finds the interpreter by name.
        as_started = dict(os.environ, **entry['env'])
        as_started.pop('PURLIN_PYTHON', None)
        stdout, stderr = _child(project.root, json.dumps(_initialize()) + '\n',
                                command=command, env=as_started)
        lines = stdout.splitlines()
        assert len(lines) == 1, (stdout, stderr)
        answer = json.loads(lines[0])
        assert (answer['jsonrpc'], answer['id']) == ('2.0', 1), stdout
        assert answer['result']['serverInfo']['name'] == 'purlin', stdout

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


# ---------------------------------------------------------------------------
# A project Purlin 0.9.5 set up
# ---------------------------------------------------------------------------

@pytest.fixture
def set_up_by_095(project):
    """A project holding one spec and the settings file 0.9.5 wrote. The
    three lines its status is."""
    with open(_config_file(project.root), 'w', encoding='utf-8') as handle:
        json.dump({'version': '0.9.5', 'test_framework': 'pytest'}, handle)
    return project, [
        'Purlin status: %s, plugin %s' % (
            os.path.basename(project.root), _version()),
        'This project was set up by Purlin 0.9.5. Nothing here counts until '
        'it is brought to %s.' % _version(),
        '→ Run: purlin:init --update']


class TestAProjectSetUpBy095:

    # purlin: states PROOF-304
    def test_the_status_command_prints_three_lines(self, set_up_by_095):
        project, three = set_up_by_095
        _code, printed = _script(STATUS_PY, project.root)
        assert printed.splitlines() == three, printed

    # purlin: states PROOF-305
    def test_the_tool_answers_the_same_three_lines(self, set_up_by_095):
        project, three = set_up_by_095
        responses, _stderr = _rpc(project.root, _call(
            'sync_status', {'project_root': project.root}))
        assert _text(responses[0]).splitlines() == three


# ---------------------------------------------------------------------------
# The markers Purlin 0.9.5 wrote that are still in a test
# ---------------------------------------------------------------------------

OLD_OPENS = ' a marker from Purlin 0.9.5, which is not read:'
OLD_DO = ('For each, write the proof with purlin:spec, put the comment above '
          'the test, and take the old tag out.')
OLD_DATA = (' a marker from Purlin 0.9.5, which is not read. Run '
            'purlin:status to see each.')
OLD_TS = ("import { it } from 'vitest';\n"
          "it('signs in ' + '[proof:login:PROOF-1b:RULE-1:unit]', () => {});\n")
OLD_MARK = ('@pytest.mark.proof("login", "%s", "RULE-2")\n'
            'def test_%s():\n'
            '    assert True\n')
OLD_PY = ('import pytest\n\n\n' + OLD_MARK % ('PROOF-2b', 'denied')
          + '\n\n' + OLD_MARK % ('PROOF-2c', 'denied_twice'))


def _tracked(project, files):
    """Write `files` into the project and commit them."""
    for rel, text in files.items():
        _write(os.path.join(project.root, rel), text)
    _git(project.root, 'add', '-A')
    _git(project.root, 'commit', '-q', '-m', 'test: the tests')


def _old_block(opening, places):
    """The warning as the terminal prints it: its opening line, one line per
    test, and what to do."""
    return [opening + OLD_OPENS] + ['  ' + place for place in places] + [OLD_DO]


def _holds(lines, block):
    """How many times `lines` holds `block`, its lines one after another."""
    return sum(1 for at in range(len(lines))
               if lines[at:at + len(block)] == block)


@pytest.fixture
def three_old_markers(project):
    _tracked(project, {'tests/login.test.ts': OLD_TS,
                       'tests/test_login.py': OLD_PY})
    return project, _old_block('3 tests still carry', [
        'tests/login.test.ts:2  login RULE-1',
        'tests/test_login.py:4  login RULE-2',
        'tests/test_login.py:9  login RULE-2'])


def _report_data(root):
    with open(os.path.join(root, '.purlin', 'report-data.js'),
              encoding='utf-8') as handle:
        text = handle.read()
    return json.loads(text[text.index('{'):text.rindex('}') + 1])


def _tree(root):
    """`{path: bytes}` for every file under `root` outside `.git`."""
    held = {}
    for folder, names, files in os.walk(root):
        names[:] = [name for name in names if name != '.git']
        for name in files:
            full = os.path.join(folder, name)
            held[os.path.relpath(full, root)] = _read_bytes(full)
    return held


class TestMarkersFrom095StillInATest:

    # purlin: states PROOF-308
    def test_the_status_command_names_each_test_with_its_rule(
            self, three_old_markers):
        project, block = three_old_markers
        _code, printed = _script(STATUS_PY, project.root)
        assert _holds(printed.splitlines(), block) == 1, printed
        assert printed.count('a marker from Purlin 0.9.5') == 1, printed

    # purlin: states PROOF-309
    def test_the_tool_answers_what_the_command_prints(self, three_old_markers):
        project, block = three_old_markers
        _code, printed = _script(STATUS_PY, project.root)
        responses, _stderr = _rpc(project.root, _call(
            'sync_status', {'project_root': project.root}))
        assert _text(responses[0]).splitlines() == printed.splitlines()
        assert _holds(_text(responses[0]).splitlines(), block) == 1

    # purlin: states PROOF-310
    def test_two_are_both_named(self, project):
        _tracked(project, {
            'tests/login.test.ts': OLD_TS,
            'tests/test_login.py': OLD_PY.split('\n\n\n')[0] + '\n\n\n'
            + OLD_MARK % ('PROOF-2b', 'denied')})
        lines = purlin_status.sync_status(project.root).splitlines()
        assert _holds(lines, _old_block('2 tests still carry', [
            'tests/login.test.ts:2  login RULE-1',
            'tests/test_login.py:4  login RULE-2'])) == 1, lines

    # purlin: states PROOF-311
    def test_one_reads_still_carries(self, project):
        _tracked(project, {
            'tests/test_login.py': 'import pytest\n\n\n'
            + OLD_MARK % ('PROOF-2b', 'denied')})
        lines = purlin_status.sync_status(project.root).splitlines()
        assert _holds(lines, _old_block('1 test still carries', [
            'tests/test_login.py:4  login RULE-2'])) == 1, lines

    # purlin: states PROOF-312
    def test_it_is_the_last_of_the_warnings(self, three_old_markers):
        project, block = three_old_markers
        project.spec(SPEC.replace('\n## Proof', '- A line with no number\n\n'
                                  '## Proof'))
        lines = purlin_status.sync_status(project.root).splitlines()
        at = lines.index(block[0])
        assert 'not numbered' in lines[at - 1], lines
        assert lines[at:at + 5] == block, lines
        assert lines[at + 5] == '', lines
        assert all(later.strip() for later in lines[at + 6:]), lines
        assert '2 rules. 0 pass their tests.' in lines[at + 6:], lines

    # purlin: states PROOF-313
    def test_the_dashboard_data_carries_one_line_last(self, three_old_markers):
        project, _block = three_old_markers
        purlin_status.sync_status(project.root)
        warnings = _report_data(project.root)['warnings']
        assert warnings[-1] == '3 tests still carry' + OLD_DATA, warnings
        assert sum('a marker from Purlin 0.9.5' in line
                   for line in warnings) == 1, warnings

    # purlin: states PROOF-316
    def test_the_line_named_is_the_tags_own_as_the_file_stands(self, project):
        _tracked(project, {
            'tests/login.test.ts':
                "import { test } from 'vitest';\n"
                "// purlin: login PROOF-1\n"
                "test(\n"
                "  'signs in',\n"
                "  () => {});\n"
                "test(\n"
                "  'signs in again '\n"
                "  + '[proof:login:PROOF-1b:RULE-1:unit]',\n"
                "  () => {});\n"})
        lines = purlin_status.sync_status(project.root).splitlines()
        assert '  tests/login.test.ts:8  login RULE-1' in lines, lines

    # purlin: states PROOF-317
    def test_a_marker_that_names_no_rule_shows_its_feature_alone(
            self, project):
        _tracked(project, {
            'tests/test_login.py':
                'import pytest\n\n\n'
                '@pytest.mark.proof("login", "PROOF-2b")\n'
                'def test_denied():\n'
                '    assert True\n',
            'tests/login.test.ts':
                "import { it } from 'vitest';\n"
                "it('signs in [proof:login:PROOF-1b:unit]', () => {});\n"})
        lines = purlin_status.sync_status(project.root).splitlines()
        assert _holds(lines, _old_block('2 tests still carry', [
            'tests/login.test.ts:2  login',
            'tests/test_login.py:4  login'])) == 1, lines

    # purlin: states PROOF-318
    def test_over_twenty_the_first_twenty_and_a_count(self, project):
        _tracked(project, {
            'tests/test_login.py': 'import pytest\n' + ''.join(
                '\n\n' + OLD_MARK % ('PROOF-2b', 'denied_%02d' % number)
                for number in range(1, 23))})
        lines = purlin_status.sync_status(project.root).splitlines()
        at = lines.index('22 tests still carry' + OLD_OPENS)
        assert lines[at + 1:at + 23] == [
            '  tests/test_login.py:%d  login RULE-2' % (4 + 5 * number)
            for number in range(20)] + ['  and 2 more', OLD_DO], lines

    # purlin: states PROOF-319
    def test_one_in_the_dashboard_data_reads_still_carries(self, project):
        _tracked(project, {
            'tests/test_login.py': 'import pytest\n\n\n'
            + OLD_MARK % ('PROOF-2b', 'denied')})
        purlin_status.sync_status(project.root)
        assert _report_data(project.root)['warnings'][-1] == (
            '1 test still carries' + OLD_DATA)

    # purlin: states PROOF-314
    def test_a_comment_a_docstring_and_an_untracked_file_are_not_one(
            self, project):
        _tracked(project, {
            'tests/test_login.py':
                'def test_denied():\n'
                '    """Was marked:\n'
                '@pytest.mark.proof("login", "PROOF-2b", "RULE-2")\n'
                '    [proof:login:PROOF-1b:RULE-1:unit]\n'
                '    """\n'
                '    # pytestmark = pytest.mark.proof("login", "PROOF-2b")\n'
                '    assert True\n',
            'tests/login.test.ts':
                "import { expect, it } from 'vitest';\n"
                "// it('x [proof:login:PROOF-1b:RULE-1:unit]')\n"
                "it('reads a tag', () => {\n"
                "  expect(tag()).toBe('[proof:login:PROOF-1b:RULE-1:unit]');\n"
                "});\n"})
        _write(os.path.join(project.root, 'tests', 'test_new.py'),
               'import pytest\n\n\n' + OLD_MARK % ('PROOF-2b', 'denied'))
        printed = purlin_status.sync_status(project.root)
        assert 'a marker from Purlin 0.9.5' not in printed, printed
        assert '2 rules. 0 pass their tests.' in printed.splitlines()

    # purlin: states PROOF-315
    def test_a_pending_095_project_prints_its_three_lines_and_writes_nothing(
            self, set_up_by_095):
        project, three = set_up_by_095
        _tracked(project, {
            'tests/test_login.py': 'import pytest\n\n\n'
            + OLD_MARK % ('PROOF-2b', 'denied')})
        _code, printed = _script(STATUS_PY, project.root)
        assert printed.splitlines() == three, printed


class TestThePending095ProjectIsLeftAsItWas:

    PAGE = '<html>the page Purlin 0.9.5 wrote</html>\n'
    DATA = 'window.PURLIN_DATA = {"written": "by 0.9.5"};\n'

    @pytest.fixture
    def with_its_page(self, set_up_by_095):
        project, three = set_up_by_095
        _write(os.path.join(project.root, '.gitignore'),
               '.purlin/runtime/\npurlin-report.html\n.purlin/report-data.js\n')
        _write(os.path.join(project.root, 'purlin-report.html'), self.PAGE)
        _write(os.path.join(project.root, '.purlin', 'report-data.js'),
               self.DATA)
        return project, three

    # purlin: states PROOF-320
    def test_the_status_command_changes_no_file(self, with_its_page):
        project, three = with_its_page
        before = _tree(project.root)
        _code, printed = _script(STATUS_PY, project.root)
        assert printed.splitlines() == three, printed
        assert _tree(project.root) == before

    # purlin: states PROOF-321
    def test_the_tool_changes_no_file(self, with_its_page):
        project, three = with_its_page
        before = _tree(project.root)
        responses, _stderr = _rpc(project.root, _call(
            'sync_status', {'project_root': project.root}))
        assert _text(responses[0]).splitlines() == three
        assert _tree(project.root) == before

    # purlin: states PROOF-322
    def test_with_no_page_and_no_data_file_it_writes_neither(
            self, set_up_by_095):
        project, three = set_up_by_095
        _write(os.path.join(project.root, '.gitignore'),
               '.purlin/runtime/\npurlin-report.html\n.purlin/report-data.js\n')
        _code, printed = _script(STATUS_PY, project.root)
        assert printed.splitlines() == three, printed
        assert not os.path.exists(os.path.join(project.root,
                                               'purlin-report.html'))
        assert not os.path.exists(os.path.join(project.root, '.purlin',
                                               'report-data.js'))
