"""Read the test results `purlin:test` writes and commits.

A run of the tagged tests writes one file per feature it covered:

    .purlin/tests/<feature>.json        a person's own run
    .purlin/tests/ci/<feature>.json     a remote run's, on a run branch

and one table for the whole project at `.purlin/tests.md`. All of them are
tracked, because a teammate reads them on the git host without running
anything and without a runner. `references/formats/tests_format.md` is the
contract.

The file:

    {
      "schema": "purlin-tests/2",
      "source": "local",
      "commit": "<full sha>",
      "at": "2026-09-26T12:00:00Z",
      "os": "macos",
      "scope_tree": "<sha256 from specs.scope_tree>",
      "rules": {"RULE-1": "passed"},
      "proofs": [
        {"id": "PROOF-1", "rule": "RULE-1", "result": "pass", "env": null,
         "test": "tests/test_feat.py::test_ok"}
      ]
    }

`rules` carries the passed cell's own word for each of the feature's rules:
`passed`, `failed`, `no test` or `not run`. `proofs` carries one entry per
proof the run observed, with `result` `pass`, `fail` or `missing`.

**The folder is the source, as it is for a record.** A file in
`.purlin/tests/` is a person's own run; one under `.purlin/tests/ci/` is a
run branch's, written by the runner through the git host's API and pulled
home by `purlin:test --remote`. That is how a proof tagged `@env` for an
operating system nobody here has reaches the tree at the gate `passed`, where
no record is written at all.

A person's own results and an uncommitted run in this checkout are the same
kind of evidence, and the newer of the two answers: a run in this checkout
that has not been committed yet is newer than the file it will replace, and a
file somebody else committed is newer than a run this checkout made before
pulling it.
"""

import json
import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import proofs as proofs_module

SCHEMA = 'purlin-tests/2'

# The three operating systems `@env` names, and how `sys.platform` spells them.
_OS_NAMES = (('win', 'windows'), ('darwin', 'macos'), ('linux', 'linux'))
TESTS_DIR = os.path.join('.purlin', 'tests')
# Where a remote run's results land. A person's own sit beside it, in the
# directory itself, so nothing a person wrote ever moved.
CI_DIR = os.path.join(TESTS_DIR, 'ci')
TABLE_PATH = os.path.join('.purlin', 'tests.md')

# The words a rule reads in a result file, which are the passed cell's own.
WORDS = ('passed', 'failed', 'no test', 'not run')


def host_os():
    """`windows`, `macos` or `linux` for the machine this checkout is on.

    The one answer, so a run that writes a platform into its results and a
    cell that reads one out of them never spell a system two ways.
    """
    import sys as _sys
    for prefix, name in _OS_NAMES:
        if _sys.platform.startswith(prefix):
            return name
    return _sys.platform


def tests_dir(project_root, source='local'):
    """Where one source's results sit: the directory, or `ci/` inside it."""
    if source == 'ci':
        return os.path.join(project_root, CI_DIR)
    return os.path.join(project_root, TESTS_DIR)


def table_path(project_root):
    return os.path.join(project_root, TABLE_PATH)


def load_results(project_root, source='local'):
    """`{feature: data}` for one source, each dict carrying `feature` and `source`.

    A missing directory is an empty result rather than an error: a project
    whose tests have never run is an ordinary state. Only the `.json` names
    directly in the directory are read, so the `ci/` folder inside it is not
    mistaken for a person's own run.
    """
    directory = tests_dir(project_root, source)
    prefix = (CI_DIR if source == 'ci' else TESTS_DIR).replace(os.sep, '/')
    found = {}
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return found
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
        feature = data.get('feature') or name[:-len('.json')]
        data = dict(data)
        data['feature'] = feature
        data['source'] = source
        data['path'] = '%s/%s' % (prefix, name)
        found[feature] = data
    return found


def all_results(project_root):
    """`{feature: data}`, the newest run of each feature whichever source.

    The table is one row per feature, so where a person's own run and a run
    branch's both cover a feature the newer one is the row. Each dict carries
    the source it came from, which the row names.
    """
    found = dict(load_results(project_root, 'local'))
    for feature, data in load_results(project_root, 'ci').items():
        held = found.get(feature)
        if held is None or str(data.get('at') or '') >= str(held.get('at') or ''):
            found[feature] = data
    return found


def ci_runs(project_root):
    """`{feature: {os: record_like}}` for the results a remote run committed.

    The passed cell reads a record per platform, and a run branch's results
    are the same news in a different file, so they are handed over in the
    shape the cell already reads: the proofs it observed, the operating
    system it ran on, the commit and the scope tree that say whether it still
    describes this checkout.
    """
    out = {}
    for feature, data in load_results(project_root, 'ci').items():
        os_name = data.get('os')
        proofs = [{'id': entry.get('id'), 'rule': entry.get('rule'),
                   'status': entry.get('result')}
                  for entry in data.get('proofs') or ()
                  if isinstance(entry, dict)]
        out.setdefault(feature, {})[os_name] = {
            'feature': feature, 'source': 'ci', 'label': 'ci',
            'os': os_name, 'environment': {'os': os_name},
            'commit': data.get('commit'), 'timestamp': data.get('at'),
            'scope_tree': data.get('scope_tree'),
            'path': data.get('path'), 'proofs': proofs,
        }
    return out


def status_by_proof(data):
    """`{proof_id: 'pass' | 'fail'}` for one feature's committed results.

    `fail` wins over `pass`, as it does in a runtime proof file: a proof that
    failed in any test claiming it is not proved. `missing` is left out, so a
    proof nothing observed reads as nothing observed.
    """
    statuses = {}
    for entry in (data or {}).get('proofs') or ():
        if not isinstance(entry, dict):
            continue
        proof_id = entry.get('id')
        result = entry.get('result')
        if not proof_id or result not in ('pass', 'fail'):
            continue
        if statuses.get(proof_id) == 'fail':
            continue
        statuses[proof_id] = result
    return statuses


def runtime_times(project_root):
    """`{feature_stem: seconds}` for the runtime proof files on disk.

    The runtime files carry no timestamp of their own, so the file's own
    modification time is what says when this checkout last ran that feature.
    """
    directory = proofs_module.proof_dir(project_root)
    times = {}
    try:
        names = os.listdir(directory)
    except OSError:
        return times
    for name in names:
        if not name.endswith('.json'):
            continue
        try:
            when = os.path.getmtime(os.path.join(directory, name))
        except OSError:
            continue
        stem = name[:-len('.json')]
        if when > times.get(stem, 0):
            times[stem] = when
    return times


def local_run_map(project_root):
    """`{feature: {'os': <os>, 'at': <stamp>}}` for the local source.

    The passed cell lists one platform per operating system a counting run
    covered, and the test results are one of them, so it needs to know which
    system they came from. A run this checkout made and has not committed yet
    is this machine's, so a feature with no committed results still answers
    with the operating system it is being read on.
    """
    committed = load_results(project_root)
    times = runtime_times(project_root)
    here = host_os()
    out = {}
    for feature, data in committed.items():
        out[feature] = {'os': data.get('os') or here, 'at': data.get('at')}
    for feature in times:
        written = _epoch((committed.get(feature) or {}).get('at'))
        ran = times.get(feature)
        if feature not in out or written is None or ran >= written:
            out[feature] = {'os': here, 'at': _iso_from_epoch(ran)}
    return out


def _iso_from_epoch(seconds):
    """Seconds as an ISO 8601 UTC stamp, or None."""
    import time

    if seconds is None:
        return None
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(seconds))


def _epoch(stamp):
    """An ISO 8601 UTC stamp as seconds, or None when it cannot be read."""
    import calendar
    import time

    try:
        return calendar.timegm(time.strptime(str(stamp), '%Y-%m-%dT%H:%M:%SZ'))
    except (TypeError, ValueError):
        return None


def local_status_map(project_root, runtime_proofs):
    """`{feature: {proof_id: status}}` for the `local` source of every feature.

    The committed results and this checkout's own run are the same kind of
    evidence, so the newer of the two answers for a feature. A feature only
    one of them knows about is read from that one.
    """
    committed = load_results(project_root)
    times = runtime_times(project_root)
    runtime = {}
    for feature, entries in (runtime_proofs or {}).items():
        runtime[feature] = {key[1]: status for key, status
                            in proofs_module.status_by_proof(entries).items()}

    out = {}
    for feature in set(committed) | set(runtime):
        from_file = status_by_proof(committed.get(feature))
        from_run = runtime.get(feature) or {}
        if not from_file:
            out[feature] = from_run
            continue
        if not from_run:
            out[feature] = from_file
            continue
        written = _epoch((committed.get(feature) or {}).get('at'))
        ran = times.get(feature)
        # An unreadable stamp on either side leaves this checkout's own run
        # to answer: it is the one thing a reader can re-run.
        if written is None or ran is None or ran >= written:
            out[feature] = from_run
        else:
            out[feature] = from_file
    return out
