"""The dashboard's data file: which commands write it, and that nothing else does.

`.purlin/report-data.js` is what the page reads. `purlin:status`,
`purlin:test`, `purlin:audit` and `purlin:sign` each write it as they finish,
and nothing runs in the background, so an edit made with no Purlin command
leaves it as it was. Each test drives the real command against a throwaway
project and reads the file back.

    python3 -m pytest dev/test_report_refresh.py -q
"""

import json
import os
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))

import sign as sign_module  # noqa: E402
from purlin import payload as purlin_payload  # noqa: E402
from purlin import report_data  # noqa: E402
from purlin import status as purlin_status  # noqa: E402
from mcp_project import SPEC, Project  # noqa: E402
from test_run_script import (_pytest_project, _run, _spec,  # noqa: E402
                             claude)  # noqa: F401
from test_signatures import signing_project  # noqa: E402

DATA = os.path.join('.purlin', 'report-data.js')


def _data(root):
    """The payload the data file holds, or None where there is no file."""
    path = os.path.join(str(root), DATA)
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as handle:
        text = handle.read()
    prefix = 'const PURLIN_DATA = '
    assert text.startswith(prefix) and text.endswith(';\n'), text[:80]
    return json.loads(text[len(prefix):-len(';\n')])


def _rule(data, feature, rule_id):
    entry = next(f for f in data['features'] if f['name'] == feature)
    return next(r for r in entry['rules'] if r['id'] == rule_id)


def _stamp(root):
    """The data file's bytes and its modification time, to the nanosecond."""
    path = os.path.join(str(root), DATA)
    with open(path, 'rb') as handle:
        return handle.read(), os.stat(path).st_mtime_ns


# purlin: purlin_report PROOF-56
def test_status_writes_the_data_file():
    made = Project(gate='passed')
    try:
        assert _data(made.root) is None
        purlin_status.sync_status(made.root)
        data = _data(made.root)
        assert data is not None, 'purlin:status wrote no data file'
        assert [f['name'] for f in data['features']] == ['login']
        assert data['schema_version'] == purlin_payload.SCHEMA_VERSION
    finally:
        made.close()


# purlin: purlin_report PROOF-57
def test_a_test_run_writes_the_data_file(tmp_path):
    root = _pytest_project(tmp_path)
    _spec(root, 'feat')
    assert _data(root) is None
    code, output = _run(root, '--all', '--test')
    assert code == 0, output
    data = _data(root)
    assert data is not None, 'purlin:test wrote no data file'
    assert _rule(data, 'feat', 'RULE-1')['cells']['passed']['word'] == 'passed'


# purlin: purlin_report PROOF-58
def test_an_audit_writes_the_data_file(tmp_path, claude):  # noqa: F811
    root = _pytest_project(tmp_path)
    _spec(root, 'feat')
    code, output = _run(root, '--all', '--test')
    assert code == 0, output
    os.remove(os.path.join(str(root), DATA))
    code, output = _run(root, '--audit')
    assert code == 0, output
    data = _data(root)
    assert data is not None, 'purlin:audit wrote no data file'
    audit = _rule(data, 'feat', 'RULE-1')['audit']
    assert audit and audit['verdict'] == 'strong', audit


# purlin: purlin_report PROOF-59
def test_a_signature_writes_the_data_file(capsys):
    made = signing_project(every_rule=False)
    try:
        path = os.path.join(made.root, DATA)
        if os.path.exists(path):
            os.remove(path)
        code = sign_module.main(['--batch', '--project-root', made.root])
        assert code == 0, capsys.readouterr().out
        data = _data(made.root)
        assert data is not None, 'purlin:sign wrote no data file'
        assert _rule(data, 'login', 'RULE-2')['cells']['signed']['word'] == (
            'signed')
    finally:
        made.close()


EXTRA_RULE = ('- RULE-3: A locked account reads 423 until fifteen minutes '
              'pass\n')


# purlin: purlin_report PROOF-60
def test_an_edit_with_no_command_leaves_the_data_file_alone():
    made = Project(gate='passed')
    try:
        purlin_status.sync_status(made.root)
        before = _stamp(made.root)
        spec = os.path.join(made.root, 'specs', 'auth', 'login.md')
        with open(spec, encoding='utf-8') as handle:
            text = handle.read()
        with open(spec, 'w', encoding='utf-8') as handle:
            handle.write(text.replace('\n\n## Proof', '\n' + EXTRA_RULE
                                      + '\n## Proof'))
        with open(os.path.join(made.root, 'src', 'login.py'), 'a',
                  encoding='utf-8') as handle:
            handle.write('# edited\n')
        subprocess.run(['git', 'add', '-A'], cwd=made.root, check=True)
        subprocess.run(['git', 'commit', '-q', '-m', 'an edit by hand'],
                       cwd=made.root, check=True)
        assert _stamp(made.root) == before
        assert len(_rule_ids(_data(made.root))) == 2

        purlin_status.sync_status(made.root)
        assert len(_rule_ids(_data(made.root))) == 3
    finally:
        made.close()


def _rule_ids(data):
    return [rule['id'] for feature in data['features']
            for rule in feature['rules']]


# purlin: purlin_report PROOF-61
def test_a_directory_with_no_settings_file_gets_no_data_file(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), 'specs', 'auth'))
    with open(os.path.join(str(tmp_path), 'specs', 'auth', 'login.md'), 'w',
              encoding='utf-8') as handle:
        handle.write(SPEC)
    assert report_data.refresh(str(tmp_path)) is None
    purlin_status.sync_status(str(tmp_path))
    assert not os.path.exists(os.path.join(str(tmp_path), DATA))
