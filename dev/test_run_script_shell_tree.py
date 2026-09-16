"""Tests for where the run script's shell arm finds `*.test.sh`.

A consumer keeps shell tests under `tests/` as often as at the root, so the arm
walks the project. The project builders are `dev/test_run_script.py`'s.
"""

import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(REPO, 'scripts', 'run'))
sys.path.insert(0, os.path.join(REPO, 'scripts', 'mcp'))

import purlin_run  # noqa: E402
from test_run_script import (SHELL_HARNESS, _project, _proofs,  # noqa: E402
                             _run, _spec)


def _script(root, rel, proof_id):
    path = root.joinpath(*rel.split('/'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        'source %s\n'
        'purlin_proof "feat" "%s" "RULE-1" pass "shell case"\n'
        'purlin_proof_finish\n' % (SHELL_HARNESS, proof_id), encoding='utf-8')


@pytest.mark.proof("run_script", "PROOF-63", "RULE-44")
def test_a_shell_test_in_a_subdirectory_proves_what_it_records(tmp_path):
    root = _project(tmp_path, frameworks='shell')
    _spec(root, 'feat')
    _script(root, 'tests/shell/feat.test.sh', 'PROOF-1')
    _script(root, 'mutants/tests/shell/feat.test.sh', 'PROOF-2')
    _script(root, '.hidden/feat.test.sh', 'PROOF-2')
    code, output = _run(root, '--all', '--quick')
    data = _proofs(root, 'feat')
    assert data is not None, output
    entries = data['proofs']
    ours = [entry for entry in entries if entry['id'] == 'PROOF-1']
    assert ours and ours[0]['test_file'] == 'tests/shell/feat.test.sh', entries
    assert ours[0]['status'] == 'pass', entries
    assert not [entry for entry in entries if entry['id'] == 'PROOF-2'], entries


@pytest.mark.proof("run_script", "PROOF-64", "RULE-44")
def test_the_shell_tests_are_found_in_sorted_order(tmp_path):
    for rel in ('b/z.test.sh', 'a.test.sh', 'a/y.test.sh',
                'node_modules/x/n.test.sh', 'a/helper.sh'):
        path = tmp_path.joinpath(*rel.split('/'))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('true\n', encoding='utf-8')
    assert purlin_run.shell_tests(str(tmp_path)) == [
        'a.test.sh', 'a/y.test.sh', 'b/z.test.sh']
