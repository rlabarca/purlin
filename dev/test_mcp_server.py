"""Tests for the MCP transport of `scripts/mcp/purlin/`.

What the server answers on stdin, and the package hygiene it keeps. The
throwaway project and its helpers are in `dev/mcp_project.py`.
"""

import json
import os
import re
import subprocess
import sys

from mcp_project import PROJECT_ROOT, SERVER_PY, _rpc, project
# `mcp_project` puts `scripts/mcp` on the path.
from purlin import server as purlin_srv


# ---------------------------------------------------------------------------
# The MCP transport
# ---------------------------------------------------------------------------

class TestTransport:

    # purlin: server PROOF-1
    # purlin: server PROOF-5
    def test_initialize_names_the_protocol_and_the_version(self, project):
        responses, stderr = _rpc(project.root, {
            'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
            'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                       'clientInfo': {'name': 't', 'version': '0'}}},
            child=True)
        result = responses[0]['result']
        assert result['protocolVersion'] == '2024-11-05'
        assert result['serverInfo']['name'] == 'purlin'
        with open(os.path.join(PROJECT_ROOT, 'VERSION'),
                  encoding='utf-8') as handle:
            version = handle.read().strip()
        assert result['serverInfo']['version'] == version
        # A client discovers the tools through this capability.
        assert 'tools' in result['capabilities'], result['capabilities']
        assert 'Purlin MCP server' in stderr
        # The startup line names the version and the root it resolved.
        started = re.search(r'Purlin MCP server v(\S+) started \(root: (.+?), ',
                            stderr)
        assert started and started.group(1) == version, stderr
        assert os.path.realpath(started.group(2)) == os.path.realpath(
            project.root), stderr

    # purlin: server PROOF-2
    def test_tools_list_names_the_three_tools(self, project):
        responses, _stderr = _rpc(project.root, {
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})
        names = [t['name'] for t in responses[0]['result']['tools']]
        assert sorted(names) == ['drift', 'purlin_config', 'sync_status']
        for tool in responses[0]['result']['tools']:
            assert 'project_root' in tool['inputSchema']['properties']

    def test_sync_status_answers_the_table(self, project):
        responses, _stderr = _rpc(project.root, {
            'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
            'params': {'name': 'sync_status', 'arguments': {}}})
        text = responses[0]['result']['content'][0]['text']
        assert 'Spec' in text and 'Tests' in text and 'login' in text

    # purlin: server PROOF-9
    def test_purlin_config_reads_and_writes(self, project):
        responses, _stderr = _rpc(
            project.root,
            {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
             'params': {'name': 'purlin_config',
                        'arguments': {'action': 'read', 'key': 'gate'}}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
             'params': {'name': 'purlin_config',
                        'arguments': {'action': 'write', 'key': 'gate',
                                      'value': 'strong'}}},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
             'params': {'name': 'purlin_config',
                        'arguments': {'action': 'read', 'key': 'gate'}}},
            {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call',
             'params': {'name': 'purlin_config',
                        'arguments': {'action': 'read'}}})
        assert json.loads(responses[0]['result']['content'][0]['text']) == {
            'gate': 'passed'}
        assert json.loads(responses[2]['result']['content'][0]['text']) == {
            'gate': 'strong'}
        # The write lands in the one settings file.
        with open(os.path.join(project.root, '.purlin', 'config.json'),
                  encoding='utf-8') as handle:
            on_disk = json.load(handle)
        assert on_disk['gate'] == 'strong'
        # A read naming no key answers the whole file, every key it holds.
        whole = json.loads(responses[3]['result']['content'][0]['text'])
        assert whole == on_disk, whole
        assert sorted(whole) == ['gate', 'project_name', 'tests'], whole

    def test_drift_answers_json(self, project):
        responses, _stderr = _rpc(project.root, {
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': 'drift', 'arguments': {'since': '1'}}})
        report = json.loads(responses[0]['result']['content'][0]['text'])
        assert sorted(report) == ['roles', 'since'], sorted(report)
        assert sorted(report['roles']) == ['eng', 'pm', 'qa']

    # purlin: server PROOF-7
    def test_a_root_with_no_workspace_says_so_rather_than_reporting_nothing(
            self, tmp_path, monkeypatch):
        monkeypatch.delenv('PURLIN_PROJECT_ROOT', raising=False)
        responses, _stderr = _rpc(str(tmp_path), {
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': 'sync_status', 'arguments': {}}})
        text = responses[0]['result']['content'][0]['text']
        assert 'No Purlin workspace' in text and 'purlin:init' in text
        # It names the root, and that the root is the working directory
        # because no .purlin/ marker was found; it carries no status table and
        # no report of an empty project.
        assert 'No Purlin workspace at %s:' % os.path.realpath(
            str(tmp_path)) in text, text
        assert 'That root came from the working directory, with no .purlin/ ' \
            'marker in it or above it.' in text, text
        assert 'Tests' not in text and 'Rules' not in text, text
        assert 'No specs found' not in text, text

    # purlin: server PROOF-3
    def test_a_notification_gets_no_response_and_bad_json_gets_a_parse_error(
            self, project):
        responses, _stderr = _rpc(
            project.root,
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 9, 'method': 'tools/list'})
        assert [r['id'] for r in responses] == [9]

        result = subprocess.run([sys.executable, SERVER_PY],
                                input='not json\n', capture_output=True,
                                text=True, cwd=project.root, timeout=60)
        parsed = json.loads(result.stdout.strip())
        assert parsed['error']['code'] == -32700

    # purlin: server PROOF-4
    def test_an_unknown_tool_and_an_unknown_method_are_errors(self, project):
        responses, _stderr = _rpc(
            project.root,
            {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
             'params': {'name': 'nope', 'arguments': {}}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'nope/at/all'})
        assert responses[0]['error']['code'] == -32601
        assert responses[1]['error']['code'] == -32601

    # purlin: server PROOF-6
    def test_project_root_can_be_named_per_call(self, project, tmp_path):
        responses, _stderr = _rpc(str(tmp_path), {
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': 'sync_status',
                       'arguments': {'project_root': project.root}}}, {
            'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
            'params': {'name': 'sync_status', 'arguments': {}}})
        assert 'login' in responses[0]['result']['content'][0]['text']
        # The named root was for that call alone: the next call in the same
        # session, naming none, answers for the empty startup folder.
        again = responses[1]['result']['content'][0]['text']
        assert again.startswith('No Purlin workspace'), again

    # purlin: server PROOF-8
    def test_a_tool_that_raises_answers_rather_than_crashing(self, project,
                                                             monkeypatch):
        def boom(_root):
            raise RuntimeError('boom')

        request = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                   'params': {'name': 'sync_status', 'arguments': {}}}
        monkeypatch.setattr(purlin_srv.status_module, 'sync_status', boom)
        text = purlin_srv.handle_request(
            request, project.root)['result']['content'][0]['text']
        assert text.startswith('Error running sync_status'), text
        assert 'boom' in text, text
        monkeypatch.undo()
        # The session is still usable: the next call answers normally.
        again = purlin_srv.handle_request(
            request, project.root)['result']['content'][0]['text']
        assert 'Tests' in again, again
        # Through one running session: the call that fails and the call
        # after it each get an answer, so the session stayed open.
        real, calls = purlin_srv.status_module.sync_status, []

        def fails_once(root):
            calls.append(root)
            if len(calls) == 1:
                raise RuntimeError('boom')
            return real(root)

        monkeypatch.setattr(purlin_srv.status_module, 'sync_status',
                            fails_once)
        responses, _stderr = _rpc(project.root, request,
                                  dict(request, id=2))
        texts = [r['result']['content'][0]['text'] for r in responses]
        assert [r['id'] for r in responses] == [1, 2], responses
        assert texts[0].startswith('Error running sync_status'), texts
        assert 'boom' in texts[0] and 'Tests' in texts[1], texts

    # purlin: server PROOF-10
    def test_a_write_with_no_key_and_an_unknown_action_are_refused(self,
                                                                   project):
        before = purlin_srv.resolve_config(project.root)
        no_key = purlin_srv.handle_purlin_config(
            project.root, {'action': 'write', 'value': 'x'})
        assert "'key' is required" in no_key, no_key
        unknown = purlin_srv.handle_purlin_config(
            project.root, {'action': 'delete', 'key': 'gate'})
        assert unknown.startswith('Unknown action'), unknown
        assert purlin_srv.resolve_config(project.root) == before


class TestPackageHygiene:
    """What the package may not do, whatever else it does."""

    def test_every_open_passes_an_encoding(self):
        import re
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
        import re
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

    # purlin: server PROOF-22
    def test_the_plugin_entry_point_names_the_package(self):
        with open(os.path.join(PROJECT_ROOT, '.claude-plugin', 'plugin.json'),
                  encoding='utf-8') as handle:
            manifest = json.load(handle)
        entry = manifest['mcpServers']['purlin']
        assert entry['command'] == 'sh', entry
        args = entry['args']
        assert args[0].endswith('scripts/purlin_python.sh'), args
        assert args[-1].endswith('scripts/mcp/purlin/server.py'), args
