"""Read the proof files a test run leaves behind.

A test run writes one file per feature under `.purlin/runtime/proofs/`, which
is gitignored: proof files are runtime, so two runs on two branches never
conflict and nothing about a run is committed.

    .purlin/runtime/proofs/<feature>.json

Each file is:

    {
      "proofs": [
        {
          "feature": "login",
          "id": "PROOF-1",
          "rule": "RULE-1",
          "test_file": "tests/test_login.py",
          "test_name": "test_rejects_expired_token",
          "status": "pass"
        }
      ]
    }

`status` is `pass` or `fail`; anything else is read as neither and the entry
does not prove its rule. `test_file` is relative to the project root with `/`
separators on every operating system. No entry carries a runner, an operating
system or a run marker: the record (`records.py`) is what says where a run
happened, and it says it once per run rather than once per proof.

The proof plugins write exactly what this reads.
"""

import json
import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

PROOF_DIR = os.path.join('.purlin', 'runtime', 'proofs')


def proof_dir(project_root):
    return os.path.join(project_root, PROOF_DIR)


def load_proofs(project_root):
    """`{feature: [entry, ...]}` from `.purlin/runtime/proofs/`.

    A missing directory is an empty result, not an error: a project that has
    never run its tests is a normal state, and every reader here treats "no
    proof" and "no directory" the same way.
    """
    directory = proof_dir(project_root)
    results = {}
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return results
    for name in names:
        if not name.endswith('.json'):
            continue
        path = os.path.join(directory, name)
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, IOError, OSError, UnicodeDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        for entry in data.get('proofs', []):
            if not isinstance(entry, dict):
                continue
            feature = entry.get('feature', '')
            results.setdefault(feature, []).append(entry)
    return results


def status_by_proof(entries):
    """`{(feature, proof_id): status}` for one feature's entries.

    A feature's proof has one status per run: `fail` wins over `pass`, because
    a proof that failed in any test that claims it is not proved.
    """
    statuses = {}
    for entry in entries or ():
        key = (entry.get('feature', ''), entry.get('id', ''))
        status = entry.get('status')
        if statuses.get(key) == 'fail':
            continue
        statuses[key] = status
    return statuses


def tests_for(entries, proof_id):
    """`[(test_file, test_name), ...]` naming the tests tagged with a proof."""
    found = []
    for entry in entries or ():
        if entry.get('id') != proof_id:
            continue
        pair = (entry.get('test_file', ''), entry.get('test_name', ''))
        if pair not in found:
            found.append(pair)
    return found
