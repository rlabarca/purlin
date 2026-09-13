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
              'pre_push': 'warn', 'report': False, 'digest': 'auto'}
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


# ---------------------------------------------------------------------------
# skill_init RULE-72: an up-to-date project is told so and left alone
# ---------------------------------------------------------------------------

# A spec with nothing legacy about it: the proof line carries `@unit`, which is
# a tier, so the detector has no `@windows` tag to report.
CURRENT_SPEC = '''# Feature: demo

> Scope: src/demo.py
> Description: A feature with one already migrated proof.

## Rules

- RULE-1: does the thing on the platform

## Proof

- PROOF-1 (RULE-1): Call it and assert the thing @unit
'''


def _make_current_project():
    """A temp project that was never migrated and has nothing pending.

    Built field by field rather than by running `--apply` over a legacy
    project, because "already migrated once" is RULE-54's case (PROOF-57) and
    this one is the project that never needed a migration at all.
    """
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, '.purlin', 'plugins'))

    # The template verbatim, with only `version` stamped, so no field is
    # missing and no version gap exists.
    config = dict(ps._template_config())
    config['version'] = ps._read_version()
    _write(root, '.purlin/config.json', json.dumps(config, indent=2) + '\n')

    _write(root, 'specs/demo/demo.md', CURRENT_SPEC)
    # Tier in the filename, not a platform: not a legacy proof file.
    _write(root, 'specs/demo/demo.proofs-unit.json', json.dumps({
        'tier': 'unit',
        'proofs': [{'feature': 'demo', 'id': 'PROOF-1', 'rule': 'RULE-1',
                    'test_file': 'tests/test_demo.py',
                    'test_name': 'test_thing', 'status': 'pass',
                    'tier': 'unit'}],
    }, indent=2) + '\n')

    # A modern marker, and a plugin copy with no drift.
    _write(root, 'tests/test_demo.py',
           'import pytest\n\n\n'
           '@pytest.mark.proof("demo", "PROOF-1", "RULE-1")\n'
           'def test_thing():\n    assert 1\n')
    shutil.copyfile(os.path.join(ROOT, 'scripts', 'proof', 'pytest_purlin.py'),
                    os.path.join(root, '.purlin', 'plugins',
                                 'pytest_purlin.py'))

    # No receipt at all and no `.mcp.json`: the two directive migrations have
    # nothing to report either, so `pending` must come back completely empty.
    _git(root, 'init', '-q')
    for key, value in (('user.email', 't@e'), ('user.name', 't')):
        _git(root, 'config', key, value)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'current project')
    return root


class TestUpToDateProject:

    @pytest.mark.proof("skill_init", "PROOF-75", "RULE-72", tier="integration")
    def test_nothing_pending_means_nothing_written(self):
        """RULE-72: an update that rewrites a clean project cannot be trusted."""
        root = _make_current_project()
        try:
            code, out, err = _run(root, '--check')
            assert code == 0, f'a current project must exit 0: {out} {err}'
            assert json.loads(out)['pending'] == [], out

            before = _tree_hashes(root)
            code, out, err = _run(root, '--apply', *SCRIPTED_IDS)
            assert code == 0, err
            assert out.strip() == 'nothing to do', out

            after = _tree_hashes(root)
            assert set(after) == set(before), (
                'apply added or removed a path on a clean project: '
                f'{sorted(set(after) ^ set(before))}')
            changed = [rel for rel in before if after[rel] != before[rel]]
            assert changed == [], f'apply rewrote {changed} on a clean project'
            assert _git(root, 'status', '--porcelain').stdout.strip() == ''

            # The skill's own stopping point for the same state.
            with open(os.path.join(ROOT, 'skills', 'init', 'SKILL.md'),
                      encoding='utf-8') as f:
                skill = f.read()
            assert ('If `pending` is empty, print\n'
                    '`Project is up to date with Purlin <VERSION>.` and stop.'
                    ) in skill, 'SKILL.md no longer stops on an empty pending list'
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill_init RULE-73: --platform-id defaults to the OS family id
# ---------------------------------------------------------------------------

class TestPlatformIdDefault:

    @pytest.mark.proof("skill_init", "PROOF-76", "RULE-73", tier="integration")
    def test_absent_platform_id_flag_stamps_the_os_family(self):
        """RULE-73: no flag means the OS family id, never a runner label."""
        root = _make_legacy_project(with_mcp=False)
        try:
            # No --platform-id anywhere on the command line.
            code, _out, err = _run(root, '--apply', 'legacy-tier-windows',
                                   'legacy-proof-file', 'legacy-marker')
            assert code == 0, err

            spec = _read(root, 'specs/demo/demo.md')
            assert f'@unit @on({WIN})' in spec, spec
            assert not spec.rstrip().endswith(f'@{WIN}'), spec

            new_rel = f'specs/demo/demo.proofs-unit@{WIN}.json'
            assert os.path.exists(os.path.join(root, new_rel)), new_rel
            assert not os.path.exists(
                os.path.join(root, f'specs/demo/demo.proofs-{WIN}.json'))
            with open(os.path.join(root, new_rel)) as f:
                payload = json.load(f)
            assert payload['tier'] == 'unit', payload
            assert payload['platform'] == WIN, payload
            for entry in payload['proofs']:
                assert entry['platform'] == WIN, entry
                assert entry['tier'] == 'unit', entry

            marker = _read(root, 'tests/test_demo.py')
            assert f'tier="unit", platforms=("{WIN}",)' in marker, marker

            # The documented default, read off the parser itself.
            help_out = subprocess.run([sys.executable, MIGRATE, '--help'],
                                      capture_output=True, text=True).stdout
            assert f'default: {WIN}' in help_out, help_out
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill_init RULE-76: a retired template key is removed by config-fields-missing
# ---------------------------------------------------------------------------

class TestRetiredConfigFields:

    @pytest.mark.proof("skill_init", "PROOF-81", "RULE-76", tier="integration")
    def test_a_retired_key_is_removed_and_named_and_nothing_else_moves(self):
        """RULE-76: `spec_dir` leaves the template and leaves every config the
        update touches, and the delta line names it so the user reads what
        went before consenting."""
        with open(os.path.join(ROOT, 'templates', 'config.json')) as f:
            template = json.load(f)
        assert 'spec_dir' not in template, (
            "spec_dir is still a template key; new projects would be stamped "
            "with a field nothing reads")

        root = tempfile.mkdtemp()
        try:
            with open(os.path.join(ROOT, 'VERSION')) as f:
                version = f.read().strip()
            config = dict(template)
            config['version'] = version
            config['spec_dir'] = 'specs'
            config['platforms'] = {'windows-2022': {'os': 'windows'}}
            os.makedirs(os.path.join(root, '.purlin'))
            _write(root, '.purlin/config.json',
                   json.dumps(config, indent=2) + '\n')
            _write(root, 'README.md', 'untouched\n')
            _git(root, 'init', '-q')

            code, out, err = _run(root, '--check')
            assert code == 0, (code, err)
            entry = _pending(out).get('config-fields-missing')
            assert entry, out
            assert '1 retired field to remove: spec_dir' in entry['summary'], \
                entry['summary']

            before = _tree_hashes(root)
            code, out, err = _run(root, '--apply', 'config-fields-missing')
            assert code == 0, (code, err)
            assert 'spec_dir removed (retired)' in out, out

            written = json.loads(_read(root, '.purlin/config.json'))
            assert 'spec_dir' not in written, written
            expected = dict(config)
            del expected['spec_dir']
            assert written == expected, written

            after = _tree_hashes(root)
            moved = sorted(rel for rel in set(before) | set(after)
                           if before.get(rel) != after.get(rel))
            assert moved == ['.purlin/config.json'], moved

            # The migration is done: nothing pending, and a second apply is
            # a no-op rather than a second rewrite.
            code, out, err = _run(root, '--check')
            assert code == 0, (code, err)
            assert 'config-fields-missing' not in _pending(out), out

            frozen = _read(root, '.purlin/config.json')
            code, out, err = _run(root, '--apply', 'config-fields-missing')
            assert code == 0, (code, err)
            assert out.strip() == 'nothing to do', out
            assert _read(root, '.purlin/config.json') == frozen, \
                "a second apply rewrote the config"
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill_init RULE-53: a copy is resolved through the registry, under either name
# ---------------------------------------------------------------------------

SHELL_SOURCE = os.path.join(ROOT, 'scripts', 'proof', 'shell_purlin.sh')


def _make_shell_project(copy_name):
    """A temp project whose shell harness sits under `copy_name`, drifted."""
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, '.purlin', 'plugins'))
    config = dict(ps._template_config())
    config['version'] = ps._read_version()
    config['test_framework'] = 'shell'
    _write(root, '.purlin/config.json', json.dumps(config, indent=2) + '\n')
    dest = os.path.join(root, '.purlin', 'plugins', copy_name)
    shutil.copyfile(SHELL_SOURCE, dest)
    with open(dest, 'a') as f:
        f.write('\n# one byte of drift\n')
    _write(root, 'tests/demo.sh',
           f'. "$(git rev-parse --show-toplevel)/.purlin/plugins/{copy_name}"\n')
    _git(root, 'init', '-q')
    for key, value in (('user.email', 't@e'), ('user.name', 't')):
        _git(root, 'config', key, value)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'shell project')
    return root


class TestShellCopyUnderEitherName:

    @pytest.mark.proof("skill_init", "PROOF-86", "RULE-53", tier="integration")
    @pytest.mark.parametrize('copy_name',
                             ['purlin-proof.sh', 'shell_purlin.sh'])
    def test_the_shell_harness_is_seen_under_both_names(self, copy_name):
        """RULE-53: the registry resolves the copy, so neither name is invisible.

        Keying by basename against `scripts/proof/` saw neither: the installed
        name has no file of that name in the plugin, and the legacy name is the
        one the plugin stopped installing under.
        """
        root = _make_shell_project(copy_name)
        rel = f'.purlin/plugins/{copy_name}'
        try:
            code, out, err = _run(root, '--check')
            assert code == 1, (out, err)   # a stale copy blocks the preflight
            entry = _pending(out).get('plugin-copies-stale')
            assert entry, f'{copy_name} was not seen as stale: {out}'
            assert entry['files'] == [rel], entry

            code, _out, err = _run(root, '--apply', 'plugin-copies-stale')
            assert code == 0, err
            with open(SHELL_SOURCE, 'rb') as f:
                source = f.read()
            with open(os.path.join(root, rel), 'rb') as f:
                assert f.read() == source, 'the copy is not the plugin''s file'

            # Refreshed in place: the path the project's own test sources is
            # still the path that exists.
            sourced = _read(root, 'tests/demo.sh').strip().split('/')[-1]
            assert sourced.rstrip('"') == copy_name, sourced
            assert os.path.isfile(os.path.join(root, rel)), rel

            code, out, _ = _run(root, '--check')
            assert 'plugin-copies-stale' not in _pending(out), out
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill_init RULE-80 and RULE-81: the hook install and the dashboard copy
# ---------------------------------------------------------------------------

sys.path.insert(0, os.path.join(ROOT, 'scripts', 'init'))
import scaffold  # noqa: E402

HOOK_BODY = os.path.join(ROOT, 'scripts', 'hooks', 'pre-commit.sh')
DASHBOARD = os.path.join(ROOT, 'scripts', 'report', 'purlin-report.html')


def _make_plain_project(with_shims=True):
    """A temp git project with nothing pending: template config, no specs."""
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, '.purlin', 'plugins'))
    config = dict(ps._template_config())
    config['version'] = ps._read_version()
    _write(root, '.purlin/config.json', json.dumps(config, indent=2) + '\n')
    if with_shims:
        for name in ('pre-commit', 'pre-push'):
            rel = f'.purlin/hooks/{name}'
            _write(root, rel, scaffold._shim(name, f'scripts/hooks/{name}.sh'))
            os.chmod(os.path.join(root, rel), 0o755)
    _write(root, 'README.md', 'a project\n')
    _git(root, 'init', '-q')
    for key, value in (('user.email', 't@e'), ('user.name', 't')):
        _git(root, 'config', key, value)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'plain project')
    return root


def _install_defect(root, defect):
    """Put one shape of broken Purlin pre-commit hook in the hooks directory."""
    slot = os.path.join(root, '.git', 'hooks', 'pre-commit')
    if defect == 'dangling':
        missing = os.path.join(root, 'gone', 'pre-commit.sh')
        os.symlink(missing, slot)
    elif defect == 'plugin-symlink':
        target = os.path.join(root, 'fake-plugin', 'pre-commit.sh')
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'w') as f:
            f.write('#!/bin/sh\nexit 0\n')
        os.symlink(target, slot)
    elif defect == 'body-copy':
        shutil.copyfile(HOOK_BODY, slot)
        os.chmod(slot, 0o755)
    elif defect == 'guardless-delegator':
        text = scaffold._DELEGATOR.replace('@NAME@', 'pre-commit')
        start = text.index('PURLIN_SHIM=')
        with open(slot, 'w') as f:
            f.write(text[:start] + 'exec "$(git rev-parse --show-toplevel)'
                                   '/.purlin/hooks/pre-commit" "$@"\n')
        os.chmod(slot, 0o755)
    else:
        raise KeyError(defect)
    return slot


class TestHooksStale:

    @pytest.mark.proof("skill_init", "PROOF-87", "RULE-80", tier="integration")
    @pytest.mark.parametrize('defect', ['dangling', 'plugin-symlink',
                                        'body-copy', 'guardless-delegator'])
    def test_a_broken_purlin_hook_is_pending_and_repaired(self, defect):
        """RULE-80: every shape the plugin stopped writing is seen and rewritten."""
        root = _make_plain_project()
        try:
            slot = _install_defect(root, defect)
            code, out, err = _run(root, '--check')
            assert code == 0, (out, err)   # not blocking
            entry = _pending(out).get('hooks-stale')
            assert entry, f'{defect} was not seen: {out}'
            assert '.git/hooks/pre-commit' in entry['files'], entry
            assert entry['summary'].strip(), entry

            code, out, err = _run(root, '--apply', 'hooks-stale')
            assert code == 0, err
            want = scaffold._shim('pre-commit', 'scripts/hooks/pre-commit.sh')
            assert _read(root, '.purlin/hooks/pre-commit') == want
            assert _read(root, '.git/hooks/pre-commit') == \
                scaffold._DELEGATOR.replace('@NAME@', 'pre-commit'), slot
            assert os.stat(slot).st_mode & 0o111, slot

            code, out, _ = _run(root, '--check')
            assert 'hooks-stale' not in _pending(out), out
            before = _tree_hashes(root)
            code, _out, err = _run(root, '--apply', 'hooks-stale')
            assert code == 0, err
            assert _tree_hashes(root) == before, 'a second apply rewrote files'
        finally:
            shutil.rmtree(root, ignore_errors=True)

    @pytest.mark.proof("skill_init", "PROOF-87", "RULE-80", tier="integration")
    def test_a_free_slot_and_a_foreign_hook_are_not_stale(self):
        """RULE-80: RULE-78 owns both, so an update never touches either."""
        free = _make_plain_project()
        foreign = _make_plain_project()
        try:
            code, out, err = _run(free, '--check')
            assert code == 0, (out, err)
            assert 'hooks-stale' not in _pending(out), out

            body = '#!/bin/sh\necho custom\n'
            _write(foreign, '.git/hooks/pre-commit', body)
            os.chmod(os.path.join(foreign, '.git', 'hooks', 'pre-commit'), 0o755)
            code, out, err = _run(foreign, '--check')
            assert code == 0, (out, err)
            assert 'hooks-stale' not in _pending(out), out
            code, _out, err = _run(foreign, '--apply', *SCRIPTED_IDS,
                                   'hooks-stale', 'dashboard-stale')
            assert code == 0, err
            assert _read(foreign, '.git/hooks/pre-commit') == body, \
                "a foreign hook was rewritten"

            # A shim that drifted by one byte is the other half of the rule.
            with open(os.path.join(free, '.purlin', 'hooks', 'pre-push'),
                      'a') as f:
                f.write('# drift\n')
            code, out, _ = _run(free, '--check')
            entry = _pending(out).get('hooks-stale')
            assert entry and '.purlin/hooks/pre-push' in entry['files'], out
            code, _out, err = _run(free, '--apply', 'hooks-stale')
            assert code == 0, err
            assert _read(free, '.purlin/hooks/pre-push') == \
                scaffold._shim('pre-push', 'scripts/hooks/pre-push.sh')
        finally:
            shutil.rmtree(free, ignore_errors=True)
            shutil.rmtree(foreign, ignore_errors=True)


class TestDashboardStale:

    @pytest.mark.proof("skill_init", "PROOF-88", "RULE-81", tier="integration")
    @pytest.mark.parametrize('shape', ['dangling-symlink', 'old-copy'])
    def test_the_root_dashboard_becomes_the_installed_one(self, shape):
        """RULE-81: a link into a version-pinned cache and an old copy both go."""
        root = _make_plain_project()
        dest = os.path.join(root, 'purlin-report.html')
        try:
            if shape == 'dangling-symlink':
                cache = os.path.join(root, 'cache', '0.9.5',
                                     'purlin-report.html')
                os.makedirs(os.path.dirname(cache))
                with open(cache, 'w') as f:
                    f.write('<html>cached</html>\n')
                os.symlink(cache, dest)
                shutil.rmtree(os.path.join(root, 'cache'))
                expected_cue = 'does not resolve'
            else:
                with open(dest, 'w') as f:
                    f.write('<html>old</html>\n')
                expected_cue = 'differ'

            code, out, err = _run(root, '--check')
            assert code == 0, (out, err)
            entry = _pending(out).get('dashboard-stale')
            assert entry, out
            assert entry['files'] == ['purlin-report.html'], entry
            assert expected_cue in entry['summary'], entry['summary']

            code, _out, err = _run(root, '--apply', 'dashboard-stale')
            assert code == 0, err
            assert not os.path.islink(dest), 'the dashboard is still a link'
            with open(dest, 'rb') as f:
                have = f.read()
            with open(DASHBOARD, 'rb') as f:
                assert have == f.read(), 'the copy is not the installed one'

            code, out, _ = _run(root, '--check')
            assert 'dashboard-stale' not in _pending(out), out
            before = _tree_hashes(root)
            code, _out, err = _run(root, '--apply', 'dashboard-stale')
            assert code == 0, err
            assert _tree_hashes(root) == before
        finally:
            shutil.rmtree(root, ignore_errors=True)

    @pytest.mark.proof("skill_init", "PROOF-88", "RULE-81", tier="integration")
    def test_a_project_without_a_dashboard_is_not_given_one(self):
        """RULE-81: the dashboard is an answer init asks for, not a backfill."""
        root = _make_plain_project()
        try:
            code, out, err = _run(root, '--check')
            assert code == 0, (out, err)
            assert 'dashboard-stale' not in _pending(out), out
            code, _out, err = _run(root, '--apply', *SCRIPTED_IDS,
                                   'hooks-stale', 'dashboard-stale')
            assert code == 0, err
            assert not os.path.lexists(
                os.path.join(root, 'purlin-report.html')), \
                'the update handed a dashboard to a project that has none'
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill_init RULE-82: a digest written at an older schema is rebuilt
# ---------------------------------------------------------------------------

def _make_digest_project():
    """A plain project with one feature and a real digest on disk."""
    root = _make_plain_project()
    _write(root, 'specs/demo/demo.md', CURRENT_SPEC)
    _write(root, 'tests/test_demo.py',
           'import pytest\n\n\n'
           '@pytest.mark.proof("demo", "PROOF-1", "RULE-1")\n'
           'def test_thing():\n    assert 1\n')
    config = json.loads(_read(root, '.purlin/config.json'))
    config['report'] = True
    _write(root, '.purlin/config.json', json.dumps(config, indent=2) + '\n')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'a feature')
    assert ps.generate_digest(root, generated_by='pre-commit',
                              network=False) is not None
    return root


def _rewrite_schema(root, value):
    """Put `value` in the digest's `schema_version`, or remove it when None."""
    path = os.path.join(root, '.purlin', 'report-data.js')
    payload = ps._read_report_data_file(path)
    assert payload is not None
    if value is None:
        payload.pop('schema_version', None)
    else:
        payload['schema_version'] = value
    with open(path, 'w', encoding='utf-8') as f:
        f.write('const PURLIN_DATA = ' + json.dumps(payload) + ';\n')


class TestDigestSchemaOld:

    @pytest.mark.proof("skill_init", "PROOF-90", "RULE-82", tier="integration")
    @pytest.mark.parametrize('stamp', [None, 'one-less'])
    def test_an_older_digest_is_rebuilt_at_the_current_schema(self, stamp):
        """RULE-82: an absent field is schema 1, and both cases are rebuilt."""
        root = _make_digest_project()
        current = ps._REPORT_SCHEMA_VERSION
        try:
            _rewrite_schema(root, None if stamp is None else current - 1)
            expected_found = 1 if stamp is None else current - 1

            code, out, err = _run(root, '--check')
            assert code == 0, (out, err)
            entry = _pending(out).get('digest-schema-old')
            assert entry, out
            assert entry['files'] == ['.purlin/report-data.js'], entry
            assert str(expected_found) in entry['summary'], entry['summary']
            assert str(current) in entry['summary'], entry['summary']

            code, out, err = _run(root, '--apply', 'digest-schema-old')
            assert code == 0, err
            payload = ps._read_report_data_file(
                os.path.join(root, '.purlin', 'report-data.js'))
            assert payload['schema_version'] == current, payload[
                'schema_version']
            assert payload['generated_by'] == 'update', payload['generated_by']

            code, out, _ = _run(root, '--check')
            assert 'digest-schema-old' not in _pending(out), out
            before = _tree_hashes(root)
            code, _out, err = _run(root, '--apply', 'digest-schema-old')
            assert code == 0, err
            assert _tree_hashes(root) == before, 'a second apply rebuilt it'
        finally:
            shutil.rmtree(root, ignore_errors=True)

    @pytest.mark.proof("skill_init", "PROOF-90", "RULE-82", tier="integration")
    def test_a_newer_digest_and_no_digest_are_both_left_alone(self):
        """RULE-82: the update never throws away a payload it cannot rebuild."""
        root = _make_digest_project()
        try:
            _rewrite_schema(root, ps._REPORT_SCHEMA_VERSION + 1)
            frozen = _read(root, '.purlin/report-data.js')
            code, out, err = _run(root, '--check')
            assert code == 0, (out, err)
            assert 'digest-schema-old' not in _pending(out), out
            code, _out, err = _run(root, '--apply', 'digest-schema-old')
            assert code == 0, err
            assert _read(root, '.purlin/report-data.js') == frozen, \
                'a newer digest was rewritten'
        finally:
            shutil.rmtree(root, ignore_errors=True)

        bare = _make_plain_project()
        try:
            code, out, err = _run(bare, '--check')
            assert code == 0, (out, err)
            assert 'digest-schema-old' not in _pending(out), out
            code, _out, err = _run(bare, '--apply', *SCRIPTED_IDS,
                                   'digest-schema-old')
            assert code == 0, err
            assert not os.path.exists(
                os.path.join(bare, '.purlin', 'report-data.js')), \
                'the update handed a digest to a project that has none'
        finally:
            shutil.rmtree(bare, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill_init RULE-83: a locally modified copy is kept before it is overwritten
# ---------------------------------------------------------------------------

PYTEST_SOURCE = os.path.join(ROOT, 'scripts', 'proof', 'pytest_purlin.py')


def _drift_pytest_copy(root, line):
    """Put the plugin's file plus one line of the project's own in the copy."""
    dest = os.path.join(root, '.purlin', 'plugins', 'pytest_purlin.py')
    shutil.copyfile(PYTEST_SOURCE, dest)
    with open(dest, 'a') as f:
        f.write(line)
    with open(dest, 'rb') as f:
        previous = f.read()
    return previous, hashlib.sha256(previous).hexdigest()[:8]


class TestLocalCopyIsBackedUp:

    @pytest.mark.proof("skill_init", "PROOF-91", "RULE-83", tier="integration")
    def test_the_previous_bytes_survive_at_a_named_path(self):
        """RULE-83: a local change and an old plugin look alike, so both are kept."""
        root = _make_plain_project()
        try:
            local = '\n# this project measures something of its own\n'
            previous, digest = _drift_pytest_copy(root, local)
            backup_rel = f'.purlin/plugins/pytest_purlin.py.local-{digest}.bak'

            code, out, err = _run(root, '--apply', 'plugin-copies-stale')
            assert code == 0, err
            with open(PYTEST_SOURCE, 'rb') as f:
                source = f.read()
            with open(os.path.join(root, '.purlin', 'plugins',
                                   'pytest_purlin.py'), 'rb') as f:
                assert f.read() == source, 'the copy is not the plugin file'
            with open(os.path.join(root, backup_rel), 'rb') as f:
                assert f.read() == previous, 'the previous bytes are gone'
            assert backup_rel in out, out

            # The backup is not itself a plugin copy, and nothing is pending.
            code, out, _ = _run(root, '--check')
            assert 'plugin-copies-stale' not in _pending(out), out
            assert backup_rel not in out, out

            before = _tree_hashes(root)
            code, _out, err = _run(root, '--apply', 'plugin-copies-stale')
            assert code == 0, err
            assert _tree_hashes(root) == before, 'a second apply wrote again'

            # The same drift again writes the same path, not a second file.
            _drift_pytest_copy(root, local)
            code, _out, err = _run(root, '--apply', 'plugin-copies-stale')
            assert code == 0, err
            backups = sorted(n for n in os.listdir(
                os.path.join(root, '.purlin', 'plugins'))
                if n.endswith('.bak'))
            assert backups == [os.path.basename(backup_rel)], backups

            ignore = _read(ROOT, 'templates/gitignore.purlin')
            assert '.purlin/plugins/*.local-*.bak' in ignore, ignore
            _write(root, '.gitignore', ignore)
            done = _git(root, 'check-ignore', backup_rel)
            assert done.returncode == 0, (done.stdout, done.stderr)
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# sync_status RULE-55: the version gap runs one way
# ---------------------------------------------------------------------------

def _bump(version, delta):
    """`version` with its minor release moved by `delta`."""
    major, minor, patch = (int(p) for p in version.split('.')[:3])
    return f'{major}.{minor + delta}.{patch}'


def _with_version(root, version):
    config = json.loads(_read(root, '.purlin/config.json'))
    config['version'] = version
    _write(root, '.purlin/config.json', json.dumps(config, indent=2) + '\n')
    return config


class TestVersionGapIsOneDirectional:

    @pytest.mark.proof("sync_status", "PROOF-124", "RULE-55", tier="integration")
    def test_a_newer_stamp_is_a_line_and_not_a_migration(self):
        """RULE-55: the work is on the plugin's side, so there is no id."""
        installed = ps._read_version()
        root = _make_plain_project()
        try:
            newer = _bump(installed, 1)
            config = _with_version(root, newer)
            gaps = ps._config_field_gaps(config)
            assert gaps[3] is None, gaps
            assert gaps[4] == (newer, installed), gaps
            assert ps._pending_migrations(root) == [], \
                ps._pending_migrations(root)

            code, out, err = _run(root, '--check')
            assert code == 0, (out, err)
            assert json.loads(out)['pending'] == [], out
            assert newer in err and installed in err, err
            assert 'Update the plugin, not the project' in err, err
            for migration_id in ps._MIGRATION_ORDER:
                assert migration_id not in err, (migration_id, err)

            # Older, which is the direction the update repairs.
            older = _bump(installed, -1) if not installed.startswith('0.0') \
                else '0.0.1'
            config = _with_version(root, older)
            code, out, err = _run(root, '--check')
            entry = _pending(out).get('config-fields-missing')
            assert entry, out
            assert f'version is {older}, VERSION is {installed}' in \
                entry['summary'], entry['summary']
            assert 'Update the plugin, not the project' not in err, err

            # A stamp that is not a semver is still a gap a reader should see.
            _with_version(root, 'not-a-version')
            code, out, _err = _run(root, '--check')
            entry = _pending(out).get('config-fields-missing')
            assert entry and 'version is not-a-version' in entry['summary'], out

            # Only the numeric release is compared.
            config = _with_version(root, installed + '-rc1')
            gaps = ps._config_field_gaps(config)
            assert gaps[3] is None and gaps[4] is None, gaps
        finally:
            shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill_init RULE-49: the guide carries one row per id
# ---------------------------------------------------------------------------

class TestTheGuideNamesEveryMigration:

    @pytest.mark.proof("skill_init", "PROOF-93", "RULE-49", tier="integration")
    def test_the_installation_guide_table_equals_the_id_list(self):
        """RULE-49: an id a user consents to is one they can look up."""
        guide = _read(ROOT, 'docs/installation-guide.md')
        rows = []
        for line in guide.splitlines():
            if not line.startswith('| `legacy-') and not rows:
                continue
            if not line.startswith('|'):
                break
            cells = [c.strip() for c in line.strip('|').split('|')]
            rows.append((cells[0].strip('`'), cells[1] if len(cells) > 1
                         else ''))
        assert [name for name, _ in rows] == list(ps._MIGRATION_ORDER), \
            [name for name, _ in rows]
        for name, description in rows:
            assert description, f'{name} has an empty description cell'

        flat = ' '.join(guide.split())
        assert 'was initialized by Purlin' in flat, \
            'the guide never names the newer-plugin case'
        assert 'Update the plugin, not the project' in flat, flat[:0]
        assert 'purlin:init --update` is not the fix' in flat, \
            'the guide does not say the update is not the fix for it'
