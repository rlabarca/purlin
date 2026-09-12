"""Behavioural proofs for `purlin:init --update` and its migration script.

Every case here drives the real `scripts/update/migrate.py` against a temp git
project rather than asserting on a hand-built expectation of what it would do,
so the script and the proofs cannot drift apart.

One convention runs through this file: the legacy tier name is built as
`WIN = 'win' + 'dows'` and interpolated, never written as a literal. The
detector this file exercises scans the repository for exactly those literals,
so a fixture spelled out in full would make Purlin's own `--check` report a
pending migration forever, and the CI preflight would fail on this test file.

Covers `skill_init` PROOF-52 through PROOF-57 and PROOF-60 (behavioural halves)
and `skill_verify` PROOF-13 (the issuer half).
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
MIGRATE = os.path.join(ROOT, 'scripts', 'update', 'migrate.py')
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, DEV)

import purlin_server as ps  # noqa: E402
import issue_receipts  # noqa: E402

# The legacy tier name, never spelled out. See the module docstring.
WIN = 'win' + 'dows'
PID = 'windows-2022'

SPEC = f'''# Feature: demo

> Scope: src/demo.py
> Description: A feature with one platform proof.

## Rules

- RULE-1: does the thing on the platform

## Proof

- PROOF-1 (RULE-1): Call it and assert the thing @{WIN}
'''

# One legacy marker per plugin syntax: seven files, seven rewrites.
MARKER_FILES = {
    'tests/test_demo.py': (
        'import pytest\n\n\n'
        f'@pytest.mark.proof("demo", "PROOF-1", "RULE-1", tier="{WIN}")\n'
        'def test_thing():\n    assert 1\n'),
    'tests/demo.test.js': (
        f'it("[proof:demo:PROOF-1:RULE-1:{WIN}] thing", () => {{}});\n'),
    'tests/demo.sh': (
        f'PURLIN_PROOF_TIER="{WIN}" purlin_proof "demo" "PROOF-1" "RULE-1" '
        'pass "thing"\n'),
    'tests/demo.c': (
        '  purlin_proof("demo", "PROOF-1", "RULE-1", ok, "thing", __FILE__, '
        f'"{WIN}");\n'),
    'tests/DemoTest.php': f'/** @purlin demo PROOF-1 RULE-1 {WIN} */\n',
    'tests/demo.sql': f'-- @purlin demo PROOF-1 RULE-1 {WIN}\n',
    'tests/DemoTests.cs': (
        f'    [Trait("PurlinProof", "demo:PROOF-1:RULE-1:{WIN}")]\n'),
}

# What each file must read after `--apply legacy-marker --platform-id <PID>`.
MARKER_EXPECTED = {
    'tests/test_demo.py': f'tier="unit", platforms=("{PID}",)',
    'tests/demo.test.js': f'[proof:demo:PROOF-1:RULE-1:unit:on({PID})]',
    'tests/demo.sh': f'PURLIN_PROOF_TIER="unit" PURLIN_PROOF_PLATFORMS="{PID}"',
    'tests/demo.c': f'purlin_proof_on("demo", "PROOF-1", "RULE-1", ok, '
                    f'"thing", __FILE__, "unit", "{PID}")',
    'tests/DemoTest.php': f'@purlin demo PROOF-1 RULE-1 unit on({PID})',
    'tests/demo.sql': f'@purlin demo PROOF-1 RULE-1 unit on({PID})',
    'tests/DemoTests.cs': f'"demo:PROOF-1:RULE-1:unit:on({PID})"',
}

ALL_IDS = ['legacy-tier-windows', 'legacy-proof-file', 'legacy-marker',
           'plugin-copies-stale', 'config-fields-missing', 'receipt-v1',
           'legacy-mcp']
SCRIPTED_IDS = ALL_IDS[:5]


def _git(root, *args):
    return subprocess.run(['git'] + list(args), cwd=root,
                          capture_output=True, text=True)


def _read(root, rel):
    with open(os.path.join(root, rel), encoding='utf-8') as f:
        return f.read()


def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def _tree_hashes(root):
    """(relpath -> sha256) for every file under `root`, skipping `.git`."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != '.git']
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            with open(path, 'rb') as f:
                out[rel] = hashlib.sha256(f.read()).hexdigest()
    return out


def _make_legacy_project(with_mcp=True, with_mutation_field=False,
                         version='0.9.0'):
    """A temp project carrying every migration `purlin:init --update` owns."""
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, '.purlin', 'plugins'))
    spec_dir = os.path.join(root, 'specs', 'demo')
    os.makedirs(spec_dir)

    config = {'version': version, 'test_framework': 'pytest',
              'spec_dir': 'specs', 'pre_push': 'warn', 'report': False,
              'digest': 'auto'}
    if with_mutation_field:
        config['mutation_checks'] = False
    _write(root, '.purlin/config.json', json.dumps(config, indent=2) + '\n')

    _write(root, 'specs/demo/demo.md', SPEC)
    _write(root, f'specs/demo/demo.proofs-{WIN}.json', json.dumps({
        'tier': WIN,
        'proofs': [{'feature': 'demo', 'id': 'PROOF-1', 'rule': 'RULE-1',
                    'test_file': 'tests/test_demo.py',
                    'test_name': 'test_thing', 'status': 'pass',
                    'tier': WIN}],
    }, indent=2) + '\n')

    for rel, body in MARKER_FILES.items():
        _write(root, rel, body)

    shutil.copyfile(os.path.join(ROOT, 'scripts', 'proof', 'pytest_purlin.py'),
                    os.path.join(root, '.purlin', 'plugins',
                                 'pytest_purlin.py'))
    with open(os.path.join(root, '.purlin', 'plugins', 'pytest_purlin.py'),
              'a') as f:
        f.write('\n# one byte of drift\n')

    # A version 1 receipt: no `vhash_version`, no `evidence` block.
    _write(root, 'specs/demo/demo.receipt.json', json.dumps({
        'feature': 'demo', 'vhash': 'deadbeef', 'commit': 'x',
        'timestamp': '2025-01-01T00:00:00+00:00',
        'rules': ['RULE-1'], 'proofs': [],
    }, indent=2) + '\n')

    if with_mcp:
        _write(root, '.mcp.json', json.dumps({'mcpServers': {'purlin': {
            'command': 'python3',
            'args': ['/home/u/.claude/plugins/cache/purlin/scripts/mcp/'
                     'purlin_server.py'],
        }}}, indent=2) + '\n')

    _git(root, 'init', '-q')
    for key, value in (('user.email', 't@e'), ('user.name', 't')):
        _git(root, 'config', key, value)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'legacy project')
    return root


def _run(root, *args):
    """Run the real migrate.py; returns (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, MIGRATE, '--project-root', root] + list(args),
        capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def _pending(stdout):
    return {entry['id']: entry for entry in json.loads(stdout)['pending']}


# ---------------------------------------------------------------------------
# skill_init RULE-49: content-based detection, every check names its files
# ---------------------------------------------------------------------------

class TestUpdateDetection:

    @pytest.mark.proof("skill_init", "PROOF-52", "RULE-49", tier="integration")
    def test_check_lists_every_migration_with_its_files_and_ignores_version(self):
        """RULE-49: what is on disk decides, and every entry names its files.

        A version stamp that already reads current must change nothing about
        the list, or a half-migrated project would report itself finished.
        """
        root = _make_legacy_project()
        try:
            code, out, err = _run(root, '--check')
            assert code == 1, f'pending migrations must exit 1: {out} {err}'
            pending = _pending(out)
            assert sorted(pending) == sorted(ALL_IDS), sorted(pending)

            expected_files = {
                'legacy-tier-windows': 'specs/demo/demo.md',
                'legacy-proof-file': f'specs/demo/demo.proofs-{WIN}.json',
                'plugin-copies-stale': '.purlin/plugins/pytest_purlin.py',
                'config-fields-missing': '.purlin/config.json',
                'receipt-v1': 'specs/demo/demo.receipt.json',
                'legacy-mcp': '.mcp.json',
            }
            for mid, rel in expected_files.items():
                assert pending[mid]['files'] == [rel], (mid, pending[mid])
                assert pending[mid]['count'] >= 1, pending[mid]
            assert sorted(pending['legacy-marker']['files']) == \
                sorted(MARKER_FILES), pending['legacy-marker']
            assert pending['legacy-marker']['count'] == 7, \
                pending['legacy-marker']

            # The version stamp is not consulted: current version, same list.
            config = json.loads(_read(root, '.purlin/config.json'))
            config['version'] = ps._read_version()
            _write(root, '.purlin/config.json',
                   json.dumps(config, indent=2) + '\n')
            code, out, _ = _run(root, '--check')
            assert code == 1
            assert sorted(_pending(out)) == sorted(ALL_IDS), out
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill_init RULE-50: every plugin's marker syntax
# ---------------------------------------------------------------------------

class TestMarkerRewrite:

    @pytest.mark.proof("skill_init", "PROOF-53", "RULE-50", tier="integration")
    def test_every_plugin_marker_syntax_is_rewritten(self):
        """RULE-50: seven syntaxes, seven rewrites, each in its own grammar."""
        root = _make_legacy_project()
        try:
            code, out, err = _run(root, '--apply', 'legacy-marker',
                                  '--platform-id', PID)
            assert code == 0, err
            for rel, expected in MARKER_EXPECTED.items():
                text = _read(root, rel)
                assert expected in text, f'{rel}: expected {expected!r}, got {text!r}'
                assert WIN not in text.replace(PID, ''), \
                    f'{rel} still declares the legacy tier: {text!r}'
            code, out, _ = _run(root, '--check')
            assert 'legacy-marker' not in _pending(out), out
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill_init RULE-51: the check writes nothing
# ---------------------------------------------------------------------------

class TestCheckWritesNothing:

    @pytest.mark.proof("skill_init", "PROOF-54", "RULE-51", tier="integration")
    def test_check_leaves_the_tree_byte_identical(self):
        """RULE-51: the preflight a runner executes cannot edit the tree."""
        root = _make_legacy_project()
        try:
            before = _tree_hashes(root)
            before_status = _git(root, 'status', '--porcelain').stdout
            code, _out, _err = _run(root, '--check')
            assert code == 1
            assert _tree_hashes(root) == before, 'check modified the tree'
            assert _git(root, 'status', '--porcelain').stdout == before_status
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill_init RULE-52: no proof entry, no receipt, a rename that keeps history
# ---------------------------------------------------------------------------

class TestApplyNeverClaims:

    @pytest.mark.proof("skill_init", "PROOF-55", "RULE-52", tier="integration")
    def test_apply_renames_without_writing_a_claim(self):
        """RULE-52: a rename moves a record; it does not make a new claim."""
        root = _make_legacy_project()
        try:
            receipt_before = _read(root, 'specs/demo/demo.receipt.json')
            with open(os.path.join(root, f'specs/demo/demo.proofs-{WIN}.json')) as f:
                entries_before = json.load(f)['proofs']

            code, out, err = _run(root, '--apply', *ALL_IDS,
                                  '--platform-id', PID,
                                  '--mutation-checks', 'on')
            assert code == 0, err

            assert _read(root, 'specs/demo/demo.receipt.json') == receipt_before, \
                'the receipt must be untouched'

            new_rel = f'specs/demo/demo.proofs-unit@{PID}.json'
            with open(os.path.join(root, new_rel)) as f:
                payload = json.load(f)
            assert payload['tier'] == 'unit' and payload['platform'] == PID
            assert len(payload['proofs']) == len(entries_before)
            for was, now in zip(entries_before, payload['proofs']):
                assert now['id'] == was['id'] and now['status'] == was['status']
                assert now['test_name'] == was['test_name']
                assert now['tier'] == 'unit' and now['platform'] == PID
            assert not os.path.exists(
                os.path.join(root, f'specs/demo/demo.proofs-{WIN}.json'))

            status = _git(root, 'status', '--porcelain').stdout
            assert any(line.startswith('R') and new_rel in line
                       for line in status.splitlines()), status

            assert 'purlin:verify' in out, out
            assert 'purlin:init --mcp' in out, out
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill_init RULE-53: plugin copies end byte-identical
# ---------------------------------------------------------------------------

class TestPluginCopies:

    @pytest.mark.proof("skill_init", "PROOF-56", "RULE-53", tier="integration")
    def test_stale_copy_is_replaced_and_a_custom_plugin_is_left_alone(self):
        """RULE-53: a copy with a counterpart is refreshed; one without is not."""
        root = _make_legacy_project()
        try:
            _write(root, '.purlin/plugins/custom_purlin.py',
                   '# a plugin this project installed itself\n')
            custom_before = _read(root, '.purlin/plugins/custom_purlin.py')

            code, out, _ = _run(root, '--check')
            entry = _pending(out)['plugin-copies-stale']
            assert entry['files'] == ['.purlin/plugins/pytest_purlin.py'], entry

            code, _out, err = _run(root, '--apply', 'plugin-copies-stale')
            assert code == 0, err
            with open(os.path.join(ROOT, 'scripts', 'proof',
                                   'pytest_purlin.py'), 'rb') as f:
                source = f.read()
            with open(os.path.join(root, '.purlin', 'plugins',
                                   'pytest_purlin.py'), 'rb') as f:
                assert f.read() == source, 'copy must be byte-identical'
            assert _read(root, '.purlin/plugins/custom_purlin.py') == \
                custom_before
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill_init RULE-54: idempotent
# ---------------------------------------------------------------------------

class TestIdempotence:

    @pytest.mark.proof("skill_init", "PROOF-57", "RULE-54", tier="integration")
    def test_second_apply_changes_nothing(self):
        """RULE-54: a migration that cannot be re-run cannot recover."""
        # No `.mcp.json`: `legacy-mcp` is a directive the script never applies,
        # so leaving it pending would keep the check at exit 1 forever and say
        # nothing about whether the five scripted ones are idempotent.
        root = _make_legacy_project(with_mcp=False)
        try:
            code, _out, err = _run(root, '--apply', *SCRIPTED_IDS,
                                   '--platform-id', PID,
                                   '--mutation-checks', 'off')
            assert code == 0, err
            _git(root, 'add', '-A')
            _git(root, 'commit', '-q', '-m', 'migrated')
            after_first = _tree_hashes(root)

            code, out, _ = _run(root, '--check')
            pending = _pending(out)
            assert code == 0, out
            assert 'legacy-tier-windows' not in pending
            assert 'legacy-marker' not in pending
            assert 'plugin-copies-stale' not in pending
            assert 'legacy-proof-file' not in pending
            assert 'config-fields-missing' not in pending
            # Reported, and not a reason to fail the preflight.
            assert 'receipt-v1' in pending, pending

            code, _out, err = _run(root, '--apply', *SCRIPTED_IDS,
                                   '--platform-id', PID,
                                   '--mutation-checks', 'off')
            assert code == 0, err
            assert _tree_hashes(root) == after_first, 'second apply changed files'
            assert _git(root, 'status', '--porcelain').stdout.strip() == ''
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill_init RULE-57: mutation_checks is asked, never backfilled
# ---------------------------------------------------------------------------

class TestMutationChecksIsAsked:

    @pytest.mark.proof("skill_init", "PROOF-60", "RULE-57", tier="integration")
    def test_mutation_checks_is_a_question_not_a_backfill(self):
        """RULE-57: every other field is filled from the template; not this one."""
        root = _make_legacy_project()
        try:
            code, out, _ = _run(root, '--check')
            entry = _pending(out)['config-fields-missing']
            summary = entry['summary']
            assert 'ask about, not backfill' in summary, summary
            assert 'mutation_checks' in summary.split(
                'ask about, not backfill')[1], summary
            before_ask = summary.split('ask about, not backfill')[0]
            assert 'mutation_checks' not in before_ask, summary

            code, out, err = _run(root, '--apply', 'config-fields-missing')
            assert code == 0, err
            config = json.loads(_read(root, '.purlin/config.json'))
            assert 'mutation_checks' not in config, config
            assert '--mutation-checks' in out, out

            code, _out, err = _run(root, '--apply', 'config-fields-missing',
                                   '--mutation-checks', 'on')
            assert code == 0, err
            config = json.loads(_read(root, '.purlin/config.json'))
            assert config['mutation_checks'] is True, config
            assert config['remote_verification'] == 'off', config
            assert config['version'] == ps._read_version(), config
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill_verify RULE-13: no receipt while a legacy migration is pending
# ---------------------------------------------------------------------------

class TestIssuerRefusesWhileLegacyPending:

    @pytest.mark.proof("skill_verify", "PROOF-13", "RULE-13", tier="integration")
    def test_issuer_refuses_until_the_project_is_migrated(self, capsys):
        """RULE-13: the legacy alias makes coverage a guess, so no claim."""
        root = _make_legacy_project(with_mcp=False)
        try:
            issue_receipts.write_run_marker(root)
            issued, skipped = issue_receipts.main(root)
            out = capsys.readouterr().out
            assert issued == [], f'issued while legacy pending: {issued}'
            assert 'REFUSED' in out and 'legacy-tier-windows' in out, out
            assert 'purlin:init --update' in out, out
            assert not os.path.exists(
                os.path.join(root, 'specs', 'demo', 'demo.receipt.json.new'))

            code, _out, err = _run(root, '--apply', *SCRIPTED_IDS,
                                   '--platform-id', PID,
                                   '--mutation-checks', 'off')
            assert code == 0, err
            # The marker must name the file the migrated proofs point at.
            _git(root, 'add', '-A')
            _git(root, 'commit', '-q', '-m', 'migrated')
            issue_receipts.write_run_marker(root)
            issued, skipped = issue_receipts.main(root)
            out = capsys.readouterr().out
            assert 'REFUSED' not in out, out
            assert [name for name, _v, _a in issued] == ['demo'], (issued, skipped)
        finally:
            shutil.rmtree(root, ignore_errors=True)
