"""proof_common RULE-14: the sweep runs every test file the committed proofs name.

A proof entry whose `test_file` nothing executes is evidence that never
regenerates: it stays green in the committed proof files no matter what the
code does. This test reads three things and compares them:

  1. every `$SCRIPT_DIR/test_*` path `dev/run_tests.sh` invokes,
  2. every `test_file` named by an entry in a tracked `*.proofs-*.json`,
  3. the exception list written into RULE-14 itself (the backticked
     `dev/test_*` paths in that rule's text).

The proof-named files the sweep does not invoke must equal the exception list
exactly. A file in neither set fails (a proof nothing regenerates); a listed
exception the sweep now runs also fails (a stale exception). The list lives in
the spec so the rule and the test cannot disagree about it.
"""

import json
import os
import re
import subprocess

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SWEEP = os.path.join(PROJECT_ROOT, 'dev', 'run_tests.sh')
ANCHOR = os.path.join(PROJECT_ROOT, 'specs', '_anchors', 'proof_common.md')

_SWEEP_REF = re.compile(r'\$SCRIPT_DIR/(test_[A-Za-z0-9_]+\.(?:py|sh))\b')
_EXCEPTION_REF = re.compile(r'`(dev/test_[A-Za-z0-9_]+\.(?:py|sh))`')


def sweep_test_files(sweep_path=SWEEP):
    """Every dev/test_* path the sweep script invokes, project-relative."""
    with open(sweep_path) as f:
        text = f.read()
    return {'dev/' + name for name in _SWEEP_REF.findall(text)}


def tracked_proof_test_files(root=PROJECT_ROOT):
    """Every `test_file` named by an entry in a git-tracked proof file."""
    listed = subprocess.run(
        ['git', 'ls-files', '--', 'specs'],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout.split()
    files = set()
    for rel in listed:
        if not re.search(r'\.proofs-[^/]+\.json$', rel):
            continue
        with open(os.path.join(root, rel)) as f:
            for entry in json.load(f).get('proofs', []):
                files.add(entry['test_file'])
    return files


def rule_14_exceptions(anchor_path=ANCHOR):
    """The exception list as written in RULE-14's own text."""
    with open(anchor_path) as f:
        for line in f:
            if line.startswith('- RULE-14:'):
                return set(_EXCEPTION_REF.findall(line))
    raise AssertionError('proof_common.md has no RULE-14 line to read the exception list from')


@pytest.mark.proof("proof_common", "PROOF-18", "RULE-14")
def test_every_proof_named_test_file_is_swept_or_excepted():
    swept = sweep_test_files()
    named = tracked_proof_test_files()
    exceptions = rule_14_exceptions()

    # Sanity on the three inputs, so a broken parser cannot pass vacuously.
    assert len(swept) >= 20, f'sweep parser found only {sorted(swept)}'
    assert len(named) >= 20, f'proof reader found only {sorted(named)}'
    for path in swept | exceptions:
        assert os.path.exists(os.path.join(PROJECT_ROOT, path)), \
            f'{path} is named by the sweep or the exception list but does not exist'

    unswept = named - swept
    missing = unswept - exceptions
    stale = exceptions - unswept
    assert not missing, (
        'proof entries name test files dev/run_tests.sh never runs and RULE-14 '
        f'does not except: {sorted(missing)}. Add each to the sweep, or to the '
        'exception list with its runner.'
    )
    assert not stale, (
        'RULE-14 excepts test files that are no longer needed as exceptions '
        f'(the sweep runs them, or no proof names them): {sorted(stale)}'
    )
    assert unswept == exceptions
