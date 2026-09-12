"""proof_common RULE-14: the sweep runs every test file the committed proofs name.

A proof entry whose `test_file` nothing executes is evidence that never
regenerates: it stays green in the committed proof files no matter what the
code does. This test reads three things and compares them:

  1. every `$SCRIPT_DIR/test_*` path `dev/run_tests.sh` invokes,
  2. every `test_file` named by an entry in a tracked `*.proofs-*.json`,
     together with the platform scope of the file that names it,
  3. the platform registry resolved from `.purlin/config.json`.

A proof-named test file the sweep does not invoke is allowed only when every
entry naming it lives in a platform-scoped file (`<feature>.proofs-<tier>@<id>.json`)
whose id the registry declares: the evidence then says which platform
regenerates it. There is no hand-maintained exception list to go stale. The
check runs in both directions, so an unswept file with an agnostic entry fails,
and so does a scoped file whose id the registry dropped.
"""

import json
import os
import re
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SWEEP = os.path.join(PROJECT_ROOT, 'dev', 'run_tests.sh')

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
import purlin_server  # noqa: E402

_SWEEP_REF = re.compile(r'\$SCRIPT_DIR/(test_[A-Za-z0-9_]+\.(?:py|sh))\b')
_PROOF_FILE_RE = re.compile(r'\.proofs-[^/@]+(?:@([^/]+))?\.json$')


def sweep_test_files(sweep_path=SWEEP):
    """Every dev/test_* path the sweep script invokes, project-relative."""
    with open(sweep_path) as f:
        text = f.read()
    return {'dev/' + name for name in _SWEEP_REF.findall(text)}


def tracked_proof_files(root=PROJECT_ROOT):
    """[(proof file, platform id or None, {test_file, ...})] for tracked proofs."""
    listed = subprocess.run(
        ['git', 'ls-files', '--', 'specs'],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout.split()
    out = []
    for rel in listed:
        m = _PROOF_FILE_RE.search(rel)
        if not m:
            continue
        with open(os.path.join(root, rel)) as f:
            named = {entry['test_file'] for entry in json.load(f).get('proofs', [])}
        out.append((rel, m.group(1), named))
    return out


def registered_platform_ids(root=PROJECT_ROOT):
    """Every id the project's `platforms` registry declares, families included."""
    sys.path.insert(0, os.path.join(root, 'scripts', 'mcp'))
    from config_engine import resolve_config
    registry, _errors = purlin_server._platform_registry(resolve_config(root))
    return set(registry)


@pytest.mark.proof("proof_common", "PROOF-18", "RULE-14")
def test_every_proof_named_test_file_is_swept_or_platform_scoped():
    swept = sweep_test_files()
    proof_files = tracked_proof_files()
    registered = registered_platform_ids()

    named = {path for _rel, _pid, paths in proof_files for path in paths}
    # Sanity on the three inputs, so a broken parser cannot pass vacuously.
    assert len(swept) >= 20, f'sweep parser found only {sorted(swept)}'
    assert len(named) >= 20, f'proof reader found only {sorted(named)}'
    assert {'windows', 'macos', 'linux'} <= registered, sorted(registered)
    for path in swept:
        assert os.path.exists(os.path.join(PROJECT_ROOT, path)), \
            f'{path} is named by the sweep but does not exist'

    # A scope is a claim about a platform the project defined.
    unregistered = sorted(
        (rel, pid) for rel, pid, _paths in proof_files
        if pid is not None and pid not in registered
    )
    assert not unregistered, (
        'platform-scoped proof files name ids that .purlin/config.json does '
        f'not declare: {unregistered}. Register each under "platforms", or '
        'rename the file to an id that is registered.'
    )

    # An unswept test file is exempt only while a scoped file carries it.
    agnostic_unswept = sorted(
        (path, rel) for rel, pid, paths in proof_files if pid is None
        for path in paths if path not in swept
    )
    assert not agnostic_unswept, (
        'proof entries in unscoped files name test files dev/run_tests.sh '
        f'never runs: {agnostic_unswept}. Add each file to the sweep, or '
        'scope its proofs with @on(<platform-id>) so the evidence names the '
        'platform that regenerates them.'
    )
