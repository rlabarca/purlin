"""Behavioural tests for the six proof plugins, one arm per plugin.

Each arm drives the real plugin, through its framework where the framework can
be driven, and reads the runtime proof file it left behind. An arm is skipped
only for its own missing toolchain, so a host without `dotnet` still proves the
other five.

The behaviour under test is section A of `references/proof_plugin_contract.md`:
the proof file's location and its seven fields, the write-scoped merge and
orphan reaping, ordinal ordering after the merge, the project root found by
walking up, `test_file` written relative to it, a skipped test keeping its
entry, a plugin that saw markers and wrote nothing failing loudly, a retired
marker keyword refused by name, atomic writes, and no third-party import.

Frameworks: pytest, jest, vitest, xunit, shell, sql. C and PHP were dropped in
0.10.0 and have no arm here.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

PROOF_SCRIPTS = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'scripts', 'proof'))
PROOF_REL = os.path.join('.purlin', 'runtime', 'proofs')
# A path a test writes into a shell script is spelled with forward slashes:
# bash reads a backslash as an escape, so a Windows path sourced as it comes
# off os.path.join loses every separator. Git bash reads C:/... unchanged.
SHELL_HARNESS = os.path.join(PROOF_SCRIPTS, 'shell_purlin.sh').replace(
    os.sep, '/')
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'scripts', 'run'))
from purlin_run import bash_command, bash_path  # noqa: E402

# The bash a shell test runs under. `bash` on PATH is the Windows
# Subsystem for Linux launcher on a Windows runner, which never reads the
# script, so the run script finds Git Bash and this asks it the same
# question rather than asking it again.
BASH = bash_command()

PLUGINS = {
    'pytest': 'pytest_purlin.py',
    'jest': 'jest_purlin.js',
    'vitest': 'vitest_purlin.ts',
    'xunit': 'xunit_purlin.cs',
    'shell': 'shell_purlin.sh',
    'sql': 'sql_purlin.sh',
}

SKIP_CAPABLE = ('pytest', 'jest', 'vitest', 'xunit')
SKIP_EXEMPT = ('shell', 'sql')

REQUIRED_FIELDS = ('feature', 'id', 'rule', 'test_file', 'test_name', 'status',
                   'tier')


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _purlin_project(tmp_path, feature='feat', sub='a'):
    """A project root with `specs/` and `.purlin/`, which is what the plugins
    walk up to find."""
    root = tmp_path / 'project'
    (root / 'specs' / sub).mkdir(parents=True)
    (root / '.purlin').mkdir(parents=True)
    (root / 'specs' / sub / ('%s.md' % feature)).write_text(
        '# %s\n\n## Rules\n- RULE-1: a\n- RULE-2: b\n\n'
        '## Proof\n- PROOF-1 (RULE-1): t\n- PROOF-2 (RULE-2): t\n' % feature,
        encoding='utf-8')
    return root


def _read_proofs(root, feature, tier='unit'):
    path = os.path.join(str(root), PROOF_REL, '%s.%s.json' % (feature, tier))
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def _write_proofs(root, feature, tier, entries):
    directory = os.path.join(str(root), PROOF_REL)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, '%s.%s.json' % (feature, tier))
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump({'tier': tier, 'proofs': entries}, handle, indent=2)
    return path


def _entry(feature='feat', proof_id='PROOF-1', rule='RULE-1',
           test_file='tests/test_feat.py', test_name='test_ok', status='pass',
           tier='unit'):
    return {'feature': feature, 'id': proof_id, 'rule': rule,
            'test_file': test_file, 'test_name': test_name, 'status': status,
            'tier': tier}


# ---------------------------------------------------------------------------
# Drivers, one per framework
# ---------------------------------------------------------------------------

def _run_pytest(root, extra=()):
    (root / 'conftest.py').write_text(
        'import sys\n'
        'sys.path.insert(0, %r)\n'
        'from pytest_purlin import pytest_configure  # noqa: F401\n'
        % PROOF_SCRIPTS, encoding='utf-8')
    return subprocess.run(
        [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider']
        + list(extra),
        cwd=str(root), capture_output=True, text=True)


def _run_jest_reporter(root, test_file_rel, results, rootdir=None):
    """Drive the real jest reporter class with one synthetic test result set.

    Jest is not installed here, and the reporter's contract is the two hooks it
    exposes, so the harness calls them the way jest does.
    """
    harness = root / 'harness.cjs'
    harness.write_text(
        'const Reporter = require(%s);\n'
        'const r = new Reporter({rootDir: %s});\n'
        'r.onTestResult({}, {testFilePath: %s, testResults: %s});\n'
        'r.onRunComplete();\n'
        % (json.dumps(os.path.join(PROOF_SCRIPTS, 'jest_purlin.js')),
           json.dumps(str(rootdir or root)),
           json.dumps(os.path.join(str(root), test_file_rel)),
           json.dumps(results)), encoding='utf-8')
    return subprocess.run(['node', str(harness)], cwd=str(root),
                          capture_output=True, text=True)


def _node_can_run_ts():
    """True when node is present and can load a `.ts` file."""
    if not shutil.which('node'):
        return False
    if shutil.which('tsc'):
        return True
    try:
        out = subprocess.run(['node', '--version'], capture_output=True,
                             text=True)
        major, minor = (int(x) for x in
                        out.stdout.strip().lstrip('v').split('.')[:2])
        return major > 22 or (major == 22 and minor >= 6)
    except Exception:
        return False


def _run_vitest_reporter(root, body):
    """Compile or type-strip the real vitest reporter and run `body` against it.

    `body` is JavaScript that receives `Reporter` in scope.
    """
    shutil.copy(os.path.join(PROOF_SCRIPTS, 'vitest_purlin.ts'),
                str(root / 'vitest_purlin.ts'))
    if shutil.which('tsc'):
        (root / 'tsconfig.json').write_text(json.dumps({
            'compilerOptions': {
                'target': 'ES2020', 'module': 'commonjs',
                'esModuleInterop': True, 'skipLibCheck': True,
                'noEmitOnError': False, 'types': [],
                'outDir': str(root / 'dist')},
            'include': ['vitest_purlin.ts']}), encoding='utf-8')
        subprocess.run(['tsc', '--project', str(root / 'tsconfig.json')],
                       capture_output=True, text=True, cwd=str(root))
        compiled = root / 'dist' / 'vitest_purlin.js'
        assert compiled.exists(), 'tsc did not emit dist/vitest_purlin.js'
        harness = root / 'harness.cjs'
        harness.write_text(
            'const Reporter = require("./dist/vitest_purlin.js").default;\n'
            + body, encoding='utf-8')
        command = ['node', str(harness)]
    else:
        harness = root / 'harness.mjs'
        harness.write_text(
            'import Reporter from "./vitest_purlin.ts";\n' + body,
            encoding='utf-8')
        command = ['node', '--experimental-strip-types', str(harness)]
    return subprocess.run(command, cwd=str(root), capture_output=True,
                          text=True)


def _run_shell(root, script_rel, calls, tier=None):
    """Source the real shell harness from a script and call it."""
    lines = ['source %s' % SHELL_HARNESS]
    if tier:
        lines.append('export PURLIN_PROOF_TIER=%s' % tier)
    for feature, proof_id, rule, status, name in calls:
        lines.append('purlin_proof "%s" "%s" "%s" %s "%s"'
                     % (feature, proof_id, rule, status, name))
    lines.append('purlin_proof_finish')
    path = root / script_rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return subprocess.run([BASH, script_rel], cwd=str(root),
                          capture_output=True, text=True)


def _run_sql(root, sql_rel, body):
    path = root / sql_rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    return subprocess.run(
        [BASH, bash_path(os.path.join(PROOF_SCRIPTS, 'sql_purlin.sh')),
         sql_rel],
        cwd=str(root), capture_output=True, text=True)


# ---------------------------------------------------------------------------
# The location and the seven fields
# ---------------------------------------------------------------------------

class TestTheRuntimeProofFile:
    """Every plugin writes `.purlin/runtime/proofs/<feature>.<tier>.json`."""

    def test_pytest(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_feat.py').write_text(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            'def test_ok():\n    assert True\n', encoding='utf-8')
        _run_pytest(root)
        data = _read_proofs(root, 'feat')
        assert data is not None
        assert data['tier'] == 'unit'
        entry = data['proofs'][0]
        assert set(entry) == set(REQUIRED_FIELDS)
        assert entry['test_file'] == 'tests/test_feat.py'
        assert entry['status'] == 'pass'

    @pytest.mark.skipif(not shutil.which('node'), reason='node not available')
    def test_jest(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'feat.test.js').write_text('// marked\n',
                                                     encoding='utf-8')
        result = _run_jest_reporter(root, 'tests/feat.test.js', [
            {'title': 'works [proof:feat:PROOF-1:RULE-1:unit]',
             'status': 'passed'}])
        assert result.returncode == 0, result.stderr
        entry = _read_proofs(root, 'feat')['proofs'][0]
        assert set(entry) == set(REQUIRED_FIELDS)
        assert entry['test_file'] == 'tests/feat.test.js'

    @pytest.mark.skipif(not _node_can_run_ts(),
                        reason='node with a TypeScript loader not available')
    @pytest.mark.proof("proof_common", "PROOF-5", "RULE-5")
    def test_vitest(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'feat.test.ts').write_text('// marked\n', encoding='utf-8')
        result = _run_vitest_reporter(root, '''
const files = [{
  type: "suite",
  filepath: process.cwd() + "/feat.test.ts",
  tasks: [
    { type: "test", name: "works [proof:feat:PROOF-1:RULE-1:unit]",
      result: { state: "pass" } },
    { type: "test", name: "breaks [proof:feat:PROOF-2:RULE-2:unit]",
      result: { state: "fail" } },
  ],
}];
new Reporter().onFinished(files);
''')
        assert result.returncode == 0, result.stderr
        data = _read_proofs(root, 'feat')
        by_id = {e['id']: e for e in data['proofs']}
        assert set(by_id['PROOF-1']) == set(REQUIRED_FIELDS)
        assert by_id['PROOF-1']['status'] == 'pass'
        assert by_id['PROOF-2']['status'] == 'fail'
        assert by_id['PROOF-1']['test_file'] == 'feat.test.ts'

    def test_shell(self, tmp_path):
        root = _purlin_project(tmp_path)
        _run_shell(root, 'tests/feat.test.sh',
                   [('feat', 'PROOF-1', 'RULE-1', 'pass', 'the case')])
        entry = _read_proofs(root, 'feat')['proofs'][0]
        assert set(entry) == set(REQUIRED_FIELDS)
        assert entry['test_file'] == 'tests/feat.test.sh'
        assert entry['test_name'] == 'the case'

    @pytest.mark.skipif(shutil.which('sqlite3') is None,
                        reason='sqlite3 not available')
    def test_sql(self, tmp_path):
        root = _purlin_project(tmp_path)
        _run_sql(root, 'tests/test_feat.sql',
                 "-- @purlin feat PROOF-1 RULE-1 unit\n"
                 "-- Test: it passes\n"
                 "SELECT 'PASS';\n")
        entry = _read_proofs(root, 'feat')['proofs'][0]
        assert set(entry) == set(REQUIRED_FIELDS)
        assert entry['test_file'] == 'tests/test_feat.sql'
        assert entry['test_name'] == 'it passes'


class TestTheTierNamesTheFile:

    def test_pytest_tier_kwarg(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_feat.py').write_text(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1", '
            'tier="integration")\n'
            'def test_ok():\n    assert True\n', encoding='utf-8')
        _run_pytest(root)
        assert _read_proofs(root, 'feat', 'unit') is None
        assert _read_proofs(root, 'feat', 'integration')['tier'] == 'integration'

    def test_shell_tier_env(self, tmp_path):
        root = _purlin_project(tmp_path)
        _run_shell(root, 'tests/feat.test.sh',
                   [('feat', 'PROOF-1', 'RULE-1', 'pass', 'e2e case')],
                   tier='e2e')
        assert _read_proofs(root, 'feat', 'e2e')['tier'] == 'e2e'
        assert _read_proofs(root, 'feat', 'unit') is None

    @pytest.mark.skipif(shutil.which('sqlite3') is None,
                        reason='sqlite3 not available')
    def test_sql_tier_defaults_to_unit(self, tmp_path):
        root = _purlin_project(tmp_path)
        _run_sql(root, 'tests/test_feat.sql',
                 "-- @purlin feat PROOF-1 RULE-1\nSELECT 'PASS';\n")
        assert _read_proofs(root, 'feat', 'unit') is not None


# ---------------------------------------------------------------------------
# The merge
# ---------------------------------------------------------------------------

class TestWriteScopedMergeKey:
    """Another feature survives; another test file survives; a gone file is
    reaped; the same file is replaced."""

    def _seed(self, root):
        return _write_proofs(root, 'feat', 'unit', [
            _entry(feature='other', proof_id='PROOF-1',
                   test_file='tests/test_other.py', test_name='other'),
            _entry(proof_id='PROOF-2', test_file='tests/test_second.py',
                   test_name='second'),
            _entry(proof_id='PROOF-3', test_file='tests/test_gone.py',
                   test_name='gone'),
            _entry(proof_id='PROOF-1', test_file='tests/test_feat.py',
                   test_name='stale', status='fail'),
        ])

    def test_pytest(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_other.py').write_text('# kept\n',
                                                      encoding='utf-8')
        (root / 'tests' / 'test_second.py').write_text('# kept\n',
                                                       encoding='utf-8')
        (root / 'tests' / 'test_feat.py').write_text(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            'def test_ok():\n    assert True\n', encoding='utf-8')
        self._seed(root)
        _run_pytest(root, ['tests/test_feat.py'])
        entries = _read_proofs(root, 'feat')['proofs']
        by = {(e['feature'], e['id'], e['test_file']): e for e in entries}
        assert ('other', 'PROOF-1', 'tests/test_other.py') in by
        assert ('feat', 'PROOF-2', 'tests/test_second.py') in by
        assert ('feat', 'PROOF-3', 'tests/test_gone.py') not in by
        assert by[('feat', 'PROOF-1', 'tests/test_feat.py')]['status'] == 'pass'
        assert by[('feat', 'PROOF-1', 'tests/test_feat.py')]['test_name'] \
            == 'test_ok'

    def test_shell(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_other.py').write_text('# kept\n',
                                                      encoding='utf-8')
        (root / 'tests' / 'test_second.py').write_text('# kept\n',
                                                       encoding='utf-8')
        self._seed(root)
        _run_shell(root, 'tests/test_feat.py.sh', [])
        _run_shell(root, 'tests/feat.test.sh',
                   [('feat', 'PROOF-1', 'RULE-1', 'pass', 'fresh')])
        entries = _read_proofs(root, 'feat')['proofs']
        files = {(e['feature'], e['test_file']) for e in entries}
        assert ('other', 'tests/test_other.py') in files
        assert ('feat', 'tests/test_second.py') in files
        assert ('feat', 'tests/test_gone.py') not in files
        assert ('feat', 'tests/feat.test.sh') in files


class TestOrdinalOrderAfterTheMerge:
    """`PROOF-1` < `PROOF-10` < `PROOF-2`, and the sort runs after the merge."""

    @pytest.mark.proof("proof_common", "PROOF-7", "RULE-7")
    def test_pytest(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_kept.py').write_text('# kept\n',
                                                     encoding='utf-8')
        _write_proofs(root, 'feat', 'unit', [
            _entry(proof_id='PROOF-2', test_file='tests/test_kept.py',
                   test_name='kept')])
        (root / 'tests' / 'test_feat.py').write_text(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-10", "RULE-1")\n'
            'def test_ten():\n    assert True\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            'def test_one():\n    assert True\n', encoding='utf-8')
        _run_pytest(root)
        ids = [e['id'] for e in _read_proofs(root, 'feat')['proofs']]
        assert ids == ['PROOF-1', 'PROOF-10', 'PROOF-2']

    def test_a_second_run_writes_the_same_bytes(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_feat.py').write_text(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-2", "RULE-1")\n'
            'def test_b():\n    assert True\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            'def test_a():\n    assert True\n', encoding='utf-8')
        path = os.path.join(str(root), PROOF_REL, 'feat.unit.json')
        _run_pytest(root)
        first = open(path, encoding='utf-8').read()
        _run_pytest(root)
        assert open(path, encoding='utf-8').read() == first


# ---------------------------------------------------------------------------
# The project root and the relative test file
# ---------------------------------------------------------------------------

class TestProjectRootFoundByWalking:
    """A run started below the root writes into the project's own tree."""

    @pytest.mark.proof("proof_common", "PROOF-2", "RULE-2")
    def test_pytest_from_a_subdirectory(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'service' / 'tests').mkdir(parents=True)
        (root / 'service' / 'tests' / 'test_feat.py').write_text(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            'def test_ok():\n    assert True\n', encoding='utf-8')
        (root / 'service' / 'conftest.py').write_text(
            'import sys\n'
            'sys.path.insert(0, %r)\n'
            'from pytest_purlin import pytest_configure  # noqa: F401\n'
            % PROOF_SCRIPTS, encoding='utf-8')
        subprocess.run([sys.executable, '-m', 'pytest', '-q',
                        '-p', 'no:cacheprovider'],
                       cwd=str(root / 'service'), capture_output=True,
                       text=True)
        assert not (root / 'service' / '.purlin').exists()
        data = _read_proofs(root, 'feat')
        assert data is not None
        assert data['proofs'][0]['test_file'] == 'service/tests/test_feat.py'

    @pytest.mark.proof("proof_common", "PROOF-2", "RULE-2")
    def test_shell_from_a_subdirectory(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'service').mkdir()
        script = root / 'service' / 'feat.test.sh'
        script.write_text(
            'source %s\n'
            'purlin_proof "feat" "PROOF-1" "RULE-1" pass "sub case"\n'
            'purlin_proof_finish\n'
            % SHELL_HARNESS,
            encoding='utf-8')
        subprocess.run([BASH, 'feat.test.sh'], cwd=str(root / 'service'),
                       capture_output=True, text=True)
        data = _read_proofs(root, 'feat')
        assert data is not None
        assert data['proofs'][0]['test_file'] == 'service/feat.test.sh'


class TestTestFileIsProjectRelative:
    """Whatever shape the framework handed over, one value is written."""

    @pytest.mark.proof("proof_common", "PROOF-3", "RULE-3")
    def test_shell_records_the_same_path_either_way(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        script = root / 'tests' / 'feat.test.sh'
        script.write_text(
            'source %s\n'
            'purlin_proof "feat" "PROOF-1" "RULE-1" pass "case"\n'
            'purlin_proof_finish\n'
            % SHELL_HARNESS,
            encoding='utf-8')
        subprocess.run([BASH, 'tests/feat.test.sh'], cwd=str(root),
                       capture_output=True, text=True)
        relative = _read_proofs(root, 'feat')['proofs'][0]['test_file']
        subprocess.run([BASH, bash_path(script)], cwd=str(root),
                       capture_output=True, text=True)
        entries = _read_proofs(root, 'feat')['proofs']
        assert len(entries) == 1, entries
        assert entries[0]['test_file'] == relative == 'tests/feat.test.sh'

    def test_no_backslash_reaches_a_recorded_path(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        _run_shell(root, 'tests/feat.test.sh',
                   [('feat', 'PROOF-1', 'RULE-1', 'pass', 'case')])
        assert '\\' not in _read_proofs(root, 'feat')['proofs'][0]['test_file']


# ---------------------------------------------------------------------------
# Skips
# ---------------------------------------------------------------------------

class TestSkippedTestKeepsItsEntry:
    """A skipped test writes nothing and the entry it had survives the run."""

    @pytest.mark.proof("proof_common", "PROOF-6", "RULE-6")
    def test_pytest(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_feat.py').write_text(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            'def test_ok():\n    assert True\n\n'
            '@pytest.mark.proof("feat", "PROOF-2", "RULE-2")\n'
            '@pytest.mark.skip(reason="no tool")\n'
            'def test_skipped():\n    assert True\n', encoding='utf-8')
        _write_proofs(root, 'feat', 'unit', [
            _entry(proof_id='PROOF-2', rule='RULE-2',
                   test_file='tests/test_feat.py', test_name='test_skipped')])
        _run_pytest(root)
        by_id = {e['id']: e for e in _read_proofs(root, 'feat')['proofs']}
        assert by_id['PROOF-2']['status'] == 'pass'
        assert by_id['PROOF-2']['test_name'] == 'test_skipped'
        assert by_id['PROOF-1']['test_name'] == 'test_ok'

    @pytest.mark.skipif(not shutil.which('node'), reason='node not available')
    @pytest.mark.proof("proof_common", "PROOF-5", "RULE-5")
    def test_jest(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'feat.test.js').write_text('// marked\n',
                                                     encoding='utf-8')
        _write_proofs(root, 'feat', 'unit', [
            _entry(proof_id='PROOF-2', rule='RULE-2',
                   test_file='tests/feat.test.js', test_name='skipped one')])
        _run_jest_reporter(root, 'tests/feat.test.js', [
            {'title': 'works [proof:feat:PROOF-1:RULE-1:unit]',
             'status': 'passed'},
            {'title': 'skipped one', 'status': 'pending'},
            {'title': 'later [proof:feat:PROOF-2:RULE-2:unit]',
             'status': 'skipped'}])
        by_id = {e['id']: e for e in _read_proofs(root, 'feat')['proofs']}
        assert by_id['PROOF-2']['test_name'] == 'skipped one'
        assert by_id['PROOF-1']['status'] == 'pass'

    def test_an_executed_test_replaces_its_own_entry(self, tmp_path):
        """A skipped sibling carrying the same proof id never protects it."""
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_feat.py').write_text(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            'def test_ok():\n    assert True\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            '@pytest.mark.skip(reason="no tool")\n'
            'def test_other():\n    assert True\n', encoding='utf-8')
        _write_proofs(root, 'feat', 'unit', [
            _entry(proof_id='PROOF-1', test_file='tests/test_feat.py',
                   test_name='test_ok', status='fail')])
        _run_pytest(root)
        entries = [e for e in _read_proofs(root, 'feat')['proofs']
                   if e['test_name'] == 'test_ok']
        assert len(entries) == 1
        assert entries[0]['status'] == 'pass'


class TestSkipExemptionListMatchesTheSources:
    """The two shapes of the merge filter, and which plugin has which."""

    @pytest.mark.parametrize('framework', SKIP_CAPABLE)
    @pytest.mark.proof("proof_common", "PROOF-12", "RULE-12")
    def test_a_skip_capable_plugin_tracks_skipped_tests(self, framework):
        source = open(os.path.join(PROOF_SCRIPTS, PLUGINS[framework]),
                      encoding='utf-8').read()
        assert 'skip' in source.lower()
        for token in ('run_wrote', 'runWrote', 'runWrote'):
            if token in source:
                break
        else:
            pytest.fail('%s has no this-run-wrote set' % framework)

    @pytest.mark.parametrize('framework', SKIP_EXEMPT)
    @pytest.mark.proof("proof_common", "PROOF-12", "RULE-12")
    def test_a_skip_exempt_plugin_says_it_has_no_skip_signal(self, framework):
        source = open(os.path.join(PROOF_SCRIPTS, PLUGINS[framework]),
                      encoding='utf-8').read()
        assert 'no skip signal' in source


# ---------------------------------------------------------------------------
# Markers seen and nothing written
# ---------------------------------------------------------------------------

class TestSeenMarkersAndNoEntryFails:

    @pytest.mark.proof("proof_common", "PROOF-10", "RULE-10")
    def test_pytest_exits_non_zero_and_names_the_feature(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_feat.py').write_text(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1")\n'
            '@pytest.mark.skip(reason="no tool")\n'
            'def test_skipped():\n    assert True\n', encoding='utf-8')
        result = _run_pytest(root)
        assert result.returncode != 0
        assert 'markers were seen and no proof entry was written for feat' \
            in result.stderr
        assert _read_proofs(root, 'feat') is None

    @pytest.mark.skipif(not shutil.which('node'), reason='node not available')
    def test_jest_exits_non_zero(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'feat.test.js').write_text('// marked\n',
                                                     encoding='utf-8')
        result = _run_jest_reporter(root, 'tests/feat.test.js', [
            {'title': 'later [proof:feat:PROOF-1:RULE-1:unit]',
             'status': 'skipped'}])
        assert result.returncode != 0
        assert 'markers were seen and no proof entry was written' \
            in result.stderr

    def test_an_unmarked_run_writes_nothing_and_passes(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_feat.py').write_text(
            'def test_ok():\n    assert True\n', encoding='utf-8')
        result = _run_pytest(root)
        assert result.returncode == 0, result.stdout
        assert _read_proofs(root, 'feat') is None


# ---------------------------------------------------------------------------
# The retired operating-system keyword
# ---------------------------------------------------------------------------

class TestRetiredKeywordRefused:
    """Every plugin refuses the keyword it used to read, and names `@env`."""

    @pytest.mark.proof("proof_common", "PROOF-11", "RULE-11")
    def test_pytest_platforms_kwarg(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'test_feat.py').write_text(
            'import pytest\n\n'
            '@pytest.mark.proof("feat", "PROOF-1", "RULE-1", '
            'platforms=("windows-2022",))\n'
            'def test_ok():\n    assert True\n', encoding='utf-8')
        result = _run_pytest(root)
        assert result.returncode != 0
        assert '@env(windows)' in result.stderr
        assert _read_proofs(root, 'feat') is None

    @pytest.mark.skipif(not shutil.which('node'), reason='node not available')
    def test_jest_on_segment(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'feat.test.js').write_text('// marked\n',
                                                     encoding='utf-8')
        result = _run_jest_reporter(root, 'tests/feat.test.js', [
            {'title': 'locks [proof:feat:PROOF-1:RULE-1:unit:on(windows)]',
             'status': 'passed'}])
        assert result.returncode != 0
        assert '@env(windows)' in result.stderr
        assert _read_proofs(root, 'feat') is None

    def test_shell_platforms_variable(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        (root / 'tests' / 'feat.test.sh').write_text(
            'source %s\n'
            'export PURLIN_PROOF_PLATFORMS=windows-2022\n'
            'purlin_proof "feat" "PROOF-1" "RULE-1" pass "case"\n'
            'purlin_proof_finish\n'
            % SHELL_HARNESS,
            encoding='utf-8')
        result = subprocess.run([BASH, 'tests/feat.test.sh'], cwd=str(root),
                                capture_output=True, text=True)
        assert result.returncode != 0
        assert '@env(windows)' in result.stderr
        assert _read_proofs(root, 'feat') is None

    @pytest.mark.skipif(shutil.which('sqlite3') is None,
                        reason='sqlite3 not available')
    def test_sql_on_marker(self, tmp_path):
        root = _purlin_project(tmp_path)
        result = _run_sql(root, 'tests/test_feat.sql',
                          "-- @purlin feat PROOF-1 RULE-1 unit on(windows)\n"
                          "SELECT 'PASS';\n")
        assert result.returncode != 0
        assert '@env(windows)' in result.stderr
        assert _read_proofs(root, 'feat') is None


# ---------------------------------------------------------------------------
# Atomic writes, and what a plugin imports
# ---------------------------------------------------------------------------

class TestAtomicWrites:

    @pytest.mark.parametrize('framework', sorted(PLUGINS))
    @pytest.mark.proof("proof_common", "PROOF-8", "RULE-8")
    def test_the_temp_name_carries_the_process_id(self, framework):
        source = open(os.path.join(PROOF_SCRIPTS, PLUGINS[framework]),
                      encoding='utf-8').read()
        assert '.tmp' in source
        assert any(token in source for token in
                   ('os.getpid()', 'process.pid', 'Environment.ProcessId'))

    def test_a_run_leaves_no_temp_file_behind(self, tmp_path):
        root = _purlin_project(tmp_path)
        (root / 'tests').mkdir()
        _run_shell(root, 'tests/feat.test.sh',
                   [('feat', 'PROOF-1', 'RULE-1', 'pass', 'case')])
        leftovers = [name for name in
                     os.listdir(os.path.join(str(root), PROOF_REL))
                     if name.endswith('.tmp')]
        assert leftovers == []


class TestNoThirdPartyImport:
    """A plugin that needs a package installed does not run where it is copied."""

    @pytest.mark.proof("proof_common", "PROOF-13", "RULE-13")
    def test_the_node_plugins_require_only_builtins(self):
        for framework in ('jest', 'vitest'):
            source = open(os.path.join(PROOF_SCRIPTS, PLUGINS[framework]),
                          encoding='utf-8').read()
            for line in source.splitlines():
                stripped = line.strip()
                if stripped.startswith('import ') or 'require(' in stripped:
                    for module in ('"fs"', '"path"', "'fs'", "'path'"):
                        if module in stripped:
                            break
                    else:
                        assert stripped.startswith('//'), stripped

    def test_the_python_plugin_imports_only_the_standard_library(self):
        source = open(os.path.join(PROOF_SCRIPTS, PLUGINS['pytest']),
                      encoding='utf-8').read()
        imported = [line.split()[1] for line in source.splitlines()
                    if line.startswith('import ')]
        assert set(imported) <= {'json', 'os', 'pytest', 'sys'}


# ---------------------------------------------------------------------------
# xUnit, driven end to end
# ---------------------------------------------------------------------------

_LOGGER_CSPROJ = (
    '<Project Sdk="Microsoft.NET.Sdk">\n'
    '  <PropertyGroup><TargetFramework>net8.0</TargetFramework>'
    '<AssemblyName>Purlin.TestLogger</AssemblyName><Nullable>enable</Nullable>'
    '<ImplicitUsings>disable</ImplicitUsings></PropertyGroup>\n'
    '  <ItemGroup><PackageReference '
    'Include="Microsoft.TestPlatform.ObjectModel" Version="17.11.1" />'
    '</ItemGroup>\n'
    '</Project>\n'
)

_TEST_CSPROJ = (
    '<Project Sdk="Microsoft.NET.Sdk">\n'
    '  <PropertyGroup><TargetFramework>net8.0</TargetFramework>'
    '<Nullable>enable</Nullable><IsPackable>false</IsPackable></PropertyGroup>\n'
    '  <ItemGroup>\n'
    '    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.11.1" />\n'
    '    <PackageReference Include="xunit" Version="2.9.2" />\n'
    '    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2" />\n'
    '  </ItemGroup>\n'
    '  <ItemGroup><ProjectReference Include="../logger/logger.csproj" />'
    '</ItemGroup>\n'
    '</Project>\n'
)

_TEST_CS = (
    'using Xunit;\n'
    'namespace Svc.Tests {\n'
    '  public class FeatTests {\n'
    '    [Fact][Trait("PurlinProof","feat:PROOF-1:RULE-1:unit")]\n'
    '    public void Passes() { Assert.Equal(4, 2+2); }\n'
    '    [Fact][Trait("PurlinProof","feat:PROOF-2:RULE-2:unit")]\n'
    '    public void Fails() { Assert.True(false); }\n'
    '    [Fact(Skip="nyi")][Trait("PurlinProof","feat:PROOF-9:RULE-9:unit")]\n'
    '    public void SkippedTagged() { Assert.True(false); }\n'
    '    [Fact][Trait("PurlinProof","feat:PROOF-7:RULE-7")]\n'
    '    public void TierOmitted() { Assert.True(true); }\n'
    '    [Fact][Trait("Category","feat:PROOF-8:RULE-8:unit")]\n'
    '    public void CategoryTraitIgnored() { Assert.True(true); }\n'
    '    [Fact][Trait("purlinproof","feat:PROOF-8:RULE-8:unit")]\n'
    '    public void LowerCaseTraitNameIgnored() { Assert.True(true); }\n'
    '    [Fact]\n'
    '    public void Untagged() { Assert.True(true); }\n'
    '  }\n'
    '}\n'
)


# What `dotnet test` prints when the host, not the logger, is the reason the
# fixture's project did not run: the runtime the project targets is absent, the
# SDK cannot target it, or nothing on this host could fetch the packages.
_DOTNET_HOST_PROBLEMS = (
    'app-launch-failed',
    'You must install or update .NET',
    'NETSDK1045',
    'NU1101',
    'NU1301',
    'Unable to load the service index',
)


def _dotnet_host_reason(output):
    """Why this host could not run the xunit fixture's project, or None.

    `dotnet` resolving is not the same as `dotnet` being able to build and run
    a project targeting the framework the fixture names: a machine carrying
    only a newer runtime, or with no way to reach a package source, fails for a
    reason that is about the host. That is a skip, not a failure. Reported as a
    failure it ends the whole pytest arm 1 while every marked test passed,
    which is a run that says evidence is missing and never says why.
    """
    for marker in _DOTNET_HOST_PROBLEMS:
        if marker in output:
            return marker
    return None


@pytest.mark.skipif(not shutil.which('dotnet'), reason='dotnet SDK not available')
class TestXUnitProofPlugin:

    @pytest.fixture(scope='class')
    def run(self, tmp_path_factory):
        root = tmp_path_factory.mktemp('xunit_proj')
        specs = root / 'specs' / 'svc'
        specs.mkdir(parents=True)
        (specs / 'feat.md').write_text(
            '# feat\n\n## Rules\n- RULE-1: a\n- RULE-2: b\n- RULE-7: g\n\n'
            '## Proof\n- PROOF-1 (RULE-1): t\n- PROOF-2 (RULE-2): t\n'
            '- PROOF-7 (RULE-7): t\n', encoding='utf-8')
        (root / '.purlin').mkdir()
        # Another feature's entry, which the write-scoped merge must keep, and
        # a pre-existing entry for the skipped test, which must survive.
        proofs = root / '.purlin' / 'runtime' / 'proofs'
        proofs.mkdir(parents=True)
        (proofs / 'feat.unit.json').write_text(json.dumps({
            'tier': 'unit',
            'proofs': [{'feature': 'otherfeat', 'id': 'PROOF-1',
                        'rule': 'RULE-1', 'test_file': 'tests/Tests.cs',
                        'test_name': 'Other.Keep', 'status': 'pass',
                        'tier': 'unit'}]}), encoding='utf-8')

        logger = root / 'logger'
        logger.mkdir()
        shutil.copy(os.path.join(PROOF_SCRIPTS, 'xunit_purlin.cs'),
                    str(logger / 'PurlinProofLogger.cs'))
        (logger / 'logger.csproj').write_text(_LOGGER_CSPROJ, encoding='utf-8')

        tests = root / 'tests'
        tests.mkdir()
        (tests / 'tests.csproj').write_text(_TEST_CSPROJ, encoding='utf-8')
        (tests / 'Tests.cs').write_text(_TEST_CS, encoding='utf-8')

        env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT='1',
                   DOTNET_NOLOGO='1')
        command = ['dotnet', 'test', 'tests/tests.csproj', '--logger', 'purlin',
                   '--', 'RunConfiguration.CollectSourceInformation=true']
        proc = subprocess.run(command, cwd=str(root), capture_output=True,
                              text=True, env=env)
        data = json.loads((proofs / 'feat.unit.json').read_text(
            encoding='utf-8'))
        if not any(p['feature'] == 'feat' for p in data['proofs']):
            reason = _dotnet_host_reason(proc.stdout + proc.stderr)
            if reason:
                pytest.skip('dotnet cannot build and run a net8.0 project on '
                            'this host: %s' % reason)
            raise AssertionError(
                'logger did not record proofs:\nSTDOUT:%s\nSTDERR:%s'
                % (proc.stdout, proc.stderr))
        return {'root': root, 'proc': proc, 'cmd': command, 'data': data,
                'by_id': {p['id']: p for p in data['proofs']
                          if p['feature'] == 'feat'}}

    def test_the_trait_parses_and_the_tier_defaults(self, run):
        entry = run['by_id']['PROOF-1']
        assert (entry['feature'], entry['id'], entry['rule'], entry['tier']) \
            == ('feat', 'PROOF-1', 'RULE-1', 'unit')
        omitted = run['by_id']['PROOF-7']
        assert omitted['tier'] == 'unit'

    def test_the_logger_collects_in_process(self, run):
        output = run['proc'].stderr + run['proc'].stdout
        assert '[PurlinProofLogger] collected' in output, output
        assert 'trx' not in run['cmd']
        assert not list(run['root'].rglob('*.trx'))

    def test_only_the_purlinproof_trait_is_a_marker(self, run):
        names = [p['test_name'] for p in run['data']['proofs']]
        assert not any('Untagged' in name for name in names), names
        assert 'PROOF-8' not in run['by_id'], run['data']['proofs']

    @pytest.mark.proof("proof_common", "PROOF-5", "RULE-5")
    def test_status_mapping_and_the_skipped_test(self, run):
        assert run['by_id']['PROOF-1']['status'] == 'pass'
        assert run['by_id']['PROOF-2']['status'] == 'fail'
        assert 'PROOF-9' not in run['by_id'], run['data']['proofs']

    def test_the_file_is_relative_and_the_name_fully_qualified(self, run):
        entry = run['by_id']['PROOF-1']
        assert entry['test_file'] and not entry['test_file'].startswith('/')
        assert entry['test_file'].endswith('.cs')
        assert entry['test_name'] == 'Svc.Tests.FeatTests.Passes'
        assert set(entry) == set(REQUIRED_FIELDS)

    def test_the_merge_keeps_the_other_feature(self, run):
        features = {p['feature'] for p in run['data']['proofs']}
        assert 'otherfeat' in features
        assert 'feat' in features


# ---------------------------------------------------------------------------
# What the six plugins no longer carry
# ---------------------------------------------------------------------------

class TestTheRetiredFieldsAreGone:

    @pytest.mark.parametrize('framework', sorted(PLUGINS))
    def test_no_run_marker_and_no_os_field(self, framework):
        source = open(os.path.join(PROOF_SCRIPTS, PLUGINS[framework]),
                      encoding='utf-8').read()
        assert 'test_run.json' not in source
        assert 'PURLIN_PLATFORM' not in source
        assert 'proofs-' not in source

    @pytest.mark.parametrize('framework', sorted(PLUGINS))
    def test_the_runtime_location_is_the_one_written(self, framework):
        source = open(os.path.join(PROOF_SCRIPTS, PLUGINS[framework]),
                      encoding='utf-8').read()
        assert 'runtime' in source and 'proofs' in source

    @pytest.mark.proof("run_script", "PROOF-46", "RULE-37")
    def test_the_dropped_languages_have_no_plugin(self):
        names = {name for name in os.listdir(PROOF_SCRIPTS)
                 if not name.startswith('__')}
        for gone in ('c_purlin.h', 'c_purlin_emit.py', 'phpunit_purlin.php'):
            assert gone not in names, gone
        assert names == set(PLUGINS.values())
