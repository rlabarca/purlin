"""Tests for purlin_version: 9 rules.

Ensures the Purlin version string is defined in exactly one place (the VERSION
file) and all references to it read from that file or match its value.
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
VERSION_FILE = os.path.join(PROJECT_ROOT, 'VERSION')
CONFIG_TEMPLATE = os.path.join(PROJECT_ROOT, 'templates', 'config.json')
PLUGIN_MANIFEST = os.path.join(PROJECT_ROOT, '.claude-plugin', 'plugin.json')
PACKAGE_INIT = os.path.join(PROJECT_ROOT, 'scripts', 'mcp', 'purlin',
                            '__init__.py')
SERVER_PY = os.path.join(PROJECT_ROOT, 'scripts', 'mcp', 'purlin',
                         'server.py')
PROJECT_CONFIG = os.path.join(PROJECT_ROOT, '.purlin', 'config.json')
BUMP_SCRIPT = os.path.join(PROJECT_ROOT, 'dev', 'bump_version.sh')

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'run'))
import purlin as purlin_package
from purlin import server as purlin_srv
from purlin_run import bash_command, bash_path

# The bash a shell test runs under. `bash` on PATH is the Windows
# Subsystem for Linux launcher on a Windows runner, which never reads the
# script, so the run script finds Git Bash and this asks it the same
# question rather than asking it again.
BASH = bash_command()


class TestVersionFileSemver:

    @pytest.mark.proof("purlin_version", "PROOF-1", "RULE-1")
    def test_version_file_exists_and_is_valid_semver(self):
        """VERSION file must exist and contain a valid semver string (X.Y.Z)."""
        assert os.path.isfile(VERSION_FILE), \
            f"VERSION file not found at {VERSION_FILE}"
        with open(VERSION_FILE) as f:
            content = f.read().strip()
        assert content, "VERSION file is empty"
        semver_pattern = re.compile(r'^\d+\.\d+\.\d+$')
        assert semver_pattern.match(content), \
            f"VERSION file contains '{content}', expected a semver string like '1.2.3'"


class TestServerReadsVersionFromFile:

    @pytest.mark.proof("purlin_version", "PROOF-2", "RULE-2")
    def test_the_package_reads_the_version_from_the_file(self):
        """The package must define _read_version() and assign its result to
        PURLIN_VERSION; SERVER_INFO must use PURLIN_VERSION."""
        # Verify _read_version is defined and callable
        assert hasattr(purlin_package, '_read_version'), \
            "_read_version() not found in the purlin package"
        assert callable(purlin_package._read_version), \
            "_read_version is not callable"

        # Verify PURLIN_VERSION is set from the function
        with open(PACKAGE_INIT, encoding='utf-8') as f:
            init_source = f.read()
        assert 'PURLIN_VERSION = _read_version()' in init_source, \
            "PURLIN_VERSION must be assigned via _read_version(), not a literal"

        # Verify SERVER_INFO uses PURLIN_VERSION
        with open(SERVER_PY, encoding='utf-8') as f:
            source = f.read()
        assert 'SERVER_INFO' in source, "SERVER_INFO not found in server.py"
        server_info_match = re.search(
            r'SERVER_INFO\s*=\s*\{[^}]*"version"\s*:\s*PURLIN_VERSION',
            source,
            re.DOTALL,
        )
        assert server_info_match, \
            'SERVER_INFO must use PURLIN_VERSION for the "version" field, not a literal'

        # Verify the runtime value matches the VERSION file
        with open(VERSION_FILE) as f:
            expected = f.read().strip()
        assert purlin_package.PURLIN_VERSION == expected, \
            (f"PURLIN_VERSION is '{purlin_package.PURLIN_VERSION}' at runtime "
             f"but VERSION file contains '{expected}'")


class TestTemplateVersionMatchesVersionFile:

    @pytest.mark.proof("purlin_version", "PROOF-3", "RULE-3")
    def test_template_config_version_matches_version_file(self):
        """templates/config.json version field must match VERSION file content."""
        with open(VERSION_FILE) as f:
            file_version = f.read().strip()

        assert os.path.isfile(CONFIG_TEMPLATE), \
            f"templates/config.json not found at {CONFIG_TEMPLATE}"
        with open(CONFIG_TEMPLATE) as f:
            config = json.load(f)

        assert 'version' in config, \
            "templates/config.json has no 'version' field"
        assert config['version'] == file_version, \
            (f"templates/config.json version is '{config['version']}' "
             f"but VERSION file contains '{file_version}'")


class TestPluginManifestVersionMatchesVersionFile:

    @pytest.mark.proof("purlin_version", "PROOF-5", "RULE-5")
    def test_plugin_manifest_version_matches_version_file(self):
        """.claude-plugin/plugin.json version field must match VERSION file content.

        The plugin manifest is the version consumers install against via the Claude
        plugin marketplace. It is a separate version source from VERSION and
        templates/config.json, so it must be kept in lockstep with the release.
        """
        with open(VERSION_FILE) as f:
            file_version = f.read().strip()

        assert os.path.isfile(PLUGIN_MANIFEST), \
            f".claude-plugin/plugin.json not found at {PLUGIN_MANIFEST}"
        with open(PLUGIN_MANIFEST) as f:
            manifest = json.load(f)

        assert 'version' in manifest, \
            ".claude-plugin/plugin.json has no 'version' field"
        assert manifest['version'] == file_version, \
            (f".claude-plugin/plugin.json version is '{manifest['version']}' "
             f"but VERSION file contains '{file_version}'")


class TestNoHardcodedVersionInServer:

    @pytest.mark.proof("purlin_version", "PROOF-4", "RULE-4")
    def test_no_hardcoded_version_strings_in_the_package(self):
        """No module of the package may carry a version literal like
        '0.9.0' or any X.Y.Z pattern outside its comments."""
        import glob as _glob
        package_dir = os.path.dirname(PACKAGE_INIT)
        raw = ''
        for path in sorted(_glob.glob(os.path.join(package_dir, '*.py'))):
            with open(path, encoding='utf-8') as f:
                raw += f.read() + '\n'

        # Strip full-line comments before searching
        non_comment_lines = [
            line for line in raw.splitlines()
            if not line.lstrip().startswith('#')
        ]
        non_comment_source = '\n'.join(non_comment_lines)

        # Match quoted semver literals. Exclude '0.0.0': that is the documented
        # sentinel returned by _read_version() when the VERSION file cannot be read,
        # not a hardcoded release version. The spec targets patterns like '0.9.0'
        # or '0.10.0' (real release versions that should live only in VERSION file).
        semver_pattern = re.compile(r'["\'](\d+\.\d+\.\d+)["\']')
        all_matches = semver_pattern.findall(non_comment_source)
        release_matches = [v for v in all_matches if v != '0.0.0']

        assert release_matches == [], (
            f"Found hardcoded release version string(s) in scripts/mcp/purlin/ "
            f"(outside comments): {release_matches}. "
            f"Version must be read from the VERSION file via _read_version()."
        )


class TestProjectConfigVersionMatchesVersionFile:

    @pytest.mark.proof("purlin_version", "PROOF-6", "RULE-6")
    def test_project_config_version_matches_version_file(self):
        """This repo's own .purlin/config.json version must match VERSION.

        Purlin develops itself, so the repo is also a Purlin project. Its
        config.json carries the framework version that initialized it, and the
        dashboard reports that field. It drifted to 0.9.2 while VERSION,
        templates/config.json and plugin.json all read 0.10.0, and the three
        existing rules could not see it.
        """
        with open(VERSION_FILE, encoding='utf-8') as f:
            file_version = f.read().strip()

        assert os.path.isfile(PROJECT_CONFIG), \
            f".purlin/config.json not found at {PROJECT_CONFIG}"
        with open(PROJECT_CONFIG, encoding='utf-8') as f:
            config = json.load(f)

        assert 'version' in config, \
            ".purlin/config.json has no 'version' field"
        assert config['version'] == file_version, \
            (f".purlin/config.json version is '{config['version']}' "
             f"but VERSION file contains '{file_version}'. "
             f"Fix with: bash dev/bump_version.sh {file_version}")


class TestBumpVersionScriptPropagatesAndDetectsDrift:

    DERIVED = [
        os.path.join('templates', 'config.json'),
        os.path.join('.claude-plugin', 'plugin.json'),
        os.path.join('.purlin', 'config.json'),
    ]

    def _fake_project(self, root, version):
        """Build a minimal tree with VERSION and all three derived files."""
        with open(os.path.join(root, 'VERSION'), 'w', encoding='utf-8') as f:
            f.write(version + '\n')
        for rel in self.DERIVED:
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({'version': version}, f, indent=2)
                f.write('\n')
        # The script resolves the root as its own parent, so it must be invoked
        # from a dev/ directory inside the tree under test.
        dev_dir = os.path.join(root, 'dev')
        os.makedirs(dev_dir, exist_ok=True)
        shutil.copy2(BUMP_SCRIPT, os.path.join(dev_dir, 'bump_version.sh'))
        return os.path.join(dev_dir, 'bump_version.sh')

    def _read(self, root, rel):
        with open(os.path.join(root, rel), encoding='utf-8') as f:
            return json.load(f)['version']

    @pytest.mark.proof("purlin_version", "PROOF-7", "RULE-7", tier="integration")
    def test_bump_propagates_everywhere_and_check_reports_drift(self, tmp_path):
        """bump_version.sh <semver> writes VERSION and every derived location;
        --check exits 1 naming the drifted file, and 0 on a matching tree."""
        root = str(tmp_path / 'proj')
        os.makedirs(root)
        script = self._fake_project(root, '1.2.3')

        # ── Propagation ────────────────────────────────────────────────
        bump = subprocess.run(
            [BASH, bash_path(script), '9.8.7'],
            capture_output=True, text=True,
        )
        assert bump.returncode == 0, \
            f"bump exited {bump.returncode}\nstdout:{bump.stdout}\nstderr:{bump.stderr}"

        with open(os.path.join(root, 'VERSION'), encoding='utf-8') as f:
            assert f.read().strip() == '9.8.7', "VERSION file was not rewritten"
        for rel in self.DERIVED:
            assert self._read(root, rel) == '9.8.7', \
                f"{rel} still reports {self._read(root, rel)}, expected 9.8.7"

        # ── --check passes on the propagated tree ─────────────────────
        ok = subprocess.run(
            [BASH, bash_path(script), '--check'], capture_output=True, text=True,
        )
        assert ok.returncode == 0, \
            f"--check failed on a matching tree:\n{ok.stdout}\n{ok.stderr}"

        # ── --check fails, naming the drifted file ────────────────────
        drifted = os.path.join(root, '.purlin', 'config.json')
        with open(drifted, encoding='utf-8') as f:
            data = json.load(f)
        data['version'] = '1.2.3'
        with open(drifted, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            f.write('\n')

        bad = subprocess.run(
            [BASH, bash_path(script), '--check'], capture_output=True, text=True,
        )
        assert bad.returncode == 1, \
            f"--check exited {bad.returncode} on a drifted tree, expected 1"
        assert '.purlin/config.json' in bad.stdout, \
            f"--check did not name the drifted file:\n{bad.stdout}"
        assert 'DRIFT' in bad.stdout, \
            f"--check did not mark the drift:\n{bad.stdout}"
        # The other two must still be reported as matching, so the operator can
        # see the check is scoped rather than blanket-failing.
        assert 'templates/config.json' in bad.stdout
        assert '.claude-plugin/plugin.json' in bad.stdout

    @pytest.mark.proof("purlin_version", "PROOF-7", "RULE-7", tier="integration")
    def test_bump_rejects_non_semver_and_tolerates_absent_optional_file(self, tmp_path):
        """A non-semver argument is refused before anything is written, and an
        absent .purlin/config.json is skipped rather than failing the run."""
        root = str(tmp_path / 'proj')
        os.makedirs(root)
        script = self._fake_project(root, '1.2.3')

        bad = subprocess.run(
            [BASH, bash_path(script), 'not-a-version'], capture_output=True, text=True,
        )
        assert bad.returncode == 2, f"expected exit 2, got {bad.returncode}"
        with open(os.path.join(root, 'VERSION'), encoding='utf-8') as f:
            assert f.read().strip() == '1.2.3', \
                "VERSION was modified despite an invalid argument"

        # A consumer checkout of the framework has no .purlin/config.json.
        os.remove(os.path.join(root, '.purlin', 'config.json'))
        run = subprocess.run(
            [BASH, bash_path(script), '2.0.0'], capture_output=True, text=True,
        )
        assert run.returncode == 0, \
            f"bump failed with the optional file absent:\n{run.stdout}\n{run.stderr}"
        assert self._read(root, os.path.join('templates', 'config.json')) == '2.0.0'

        check = subprocess.run(
            [BASH, bash_path(script), '--check'], capture_output=True, text=True,
        )
        assert check.returncode == 0, \
            f"--check failed with the optional file absent:\n{check.stdout}"
        assert 'absent' in check.stdout, \
            f"--check did not report the absent optional file:\n{check.stdout}"


class TestDocsCiteVersionFileInsteadOfALiteral:

    OWNER = os.path.join('references', 'drift_criteria.md')
    MARKER = '| `version` |'

    @pytest.mark.proof("purlin_version", "PROOF-8", "RULE-8")
    def test_config_version_field_docs_carry_no_semver_literal(self):
        """The one config-field table must name the VERSION file, not a
        number, and no second copy of the row may exist.

        The table sat in two files at `"0.9.0"`, two releases stale, because a
        literal in prose has nothing keeping it honest.
        """
        semver_literal = re.compile(r'`?"?\d+\.\d+\.\d+"?`?')
        path = os.path.join(PROJECT_ROOT, self.OWNER)
        assert os.path.isfile(path), f"{self.OWNER} not found"
        with open(path, encoding='utf-8') as f:
            lines = [ln for ln in f.read().splitlines()
                     if ln.strip().startswith(self.MARKER)]
        assert lines, f"no `version` field row found in {self.OWNER}"
        for ln in lines:
            assert not semver_literal.search(ln), \
                (f"{self.OWNER} restates a version literal in its `version` "
                 f"row: {ln.strip()!r}: cite the VERSION file instead")
            assert 'VERSION' in ln, \
                (f"{self.OWNER} `version` row does not reference the VERSION "
                 f"file: {ln.strip()!r}")

        copies = []
        for base in ('skills', 'references'):
            for dirpath, _dirs, files in os.walk(
                    os.path.join(PROJECT_ROOT, base)):
                for name in files:
                    if not name.endswith('.md'):
                        continue
                    rel = os.path.relpath(
                        os.path.join(dirpath, name), PROJECT_ROOT)
                    if rel == self.OWNER:
                        continue
                    with open(os.path.join(dirpath, name),
                              encoding='utf-8') as f:
                        if any(ln.strip().startswith(self.MARKER)
                               for ln in f.read().splitlines()):
                            copies.append(rel)
        assert not copies, (
            f"a second `version` field row lives in {sorted(copies)}; "
            f"{self.OWNER} is the field's one documented home")


DEV_SWEEP = 'dev/run_tests.sh'
RUN_TESTS_SH = os.path.join(PROJECT_ROOT, 'dev', 'run_tests.sh')
RELEASE_NOTES = os.path.join(PROJECT_ROOT, 'RELEASE_NOTES.md')
SWEEP_RECORD = os.path.join(PROJECT_ROOT, '.purlin', 'runtime', 'last_sweep.json')


def _parse_unreleased_counts():
    """Return (passed, skipped) from the one counts line in the Unreleased
    section of RELEASE_NOTES.md, asserting that there is exactly one."""
    with open(RELEASE_NOTES, encoding='utf-8') as f:
        notes = f.read()
    assert '## Unreleased' in notes, "RELEASE_NOTES.md has no Unreleased section"
    section = notes.split('## Unreleased', 1)[1]
    section = re.split(r'^## ', section, maxsplit=1, flags=re.MULTILINE)[0]
    hits = re.findall(r'(\d+) passed, (\d+) skipped', section)
    assert len(hits) == 1, (
        f"the Unreleased section must state the sweep counts exactly once "
        f"as 'N passed, M skipped'; found {len(hits)}: {hits}")
    return int(hits[0][0]), int(hits[0][1])


def _compare_notes_to_sweep(notes_passed, notes_skipped, record_path):
    """Compare the notes counts to the dev sweep's own record, or say why
    there is nothing to compare against (RULE-9).

    Returns None once the comparison has been made and both counts agree, and
    a skip reason when no record exists at `record_path`: it is gitignored
    runtime state, so a checkout that has never run the sweep has nothing to
    compare. Asserts, so a disagreement fails the caller naming both numbers.
    """
    if not os.path.isfile(record_path):
        return (f"no sweep record at {record_path}; run `bash dev/run_tests.sh` "
                f"to write one, then the notes can be checked against it")
    with open(record_path, encoding='utf-8') as f:
        record = json.load(f)
    assert notes_passed == record.get('passed'), (
        f"RELEASE_NOTES.md Unreleased says {notes_passed} passed; the "
        f"{DEV_SWEEP} record in {record_path} says {record.get('passed')}")
    assert notes_skipped == record.get('skipped'), (
        f"RELEASE_NOTES.md Unreleased says {notes_skipped} skipped; the "
        f"{DEV_SWEEP} record in {record_path} says {record.get('skipped')}")
    return None


def _write_marker_function_text():
    """The `write_marker` function as dev/run_tests.sh defines it, cut out
    between its opening line and the closing brace on a line of its own."""
    cut = subprocess.run(
        ['sed', '-n', '/^write_marker()/,/^}$/p', RUN_TESTS_SH],
        capture_output=True, text=True, check=True,
    ).stdout
    assert cut.startswith('write_marker()'), \
        f"could not cut write_marker out of {RUN_TESTS_SH}"
    assert cut.rstrip().endswith('}'), \
        f"the write_marker cut from {RUN_TESTS_SH} is not closed: {cut[-200:]!r}"
    return cut


class TestReleaseNotesCounts:
    """RULE-9 - the Unreleased counts are checked against .purlin/runtime/
    last_sweep.json, the dev sweep's own record of itself, not against the
    shared marker a proof plugin rewrites mid-sweep and not against the memory
    of whoever wrote the notes."""

    @pytest.mark.proof("purlin_version", "PROOF-9", "RULE-9", tier="integration")
    def test_sweep_exit_trap_writes_its_own_sweep_record(self, tmp_path):
        """Leg (a): drive the sweep's real writer and verify it writes
        last_sweep.json, unmerged, beside the shared test_run.json."""
        root = tmp_path / 'proj'
        (root / '.purlin' / 'runtime').mkdir(parents=True)
        git = ['git', '-c', 'user.email=t@example.com', '-c', 'user.name=t']
        subprocess.run(['git', '-c', 'init.defaultBranch=main', 'init', '-q'], cwd=str(root), check=True)
        subprocess.run(git + ['commit', '-q', '--allow-empty', '-m', 'seed'],
                       cwd=str(root), check=True, capture_output=True)
        head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(root),
                              capture_output=True, text=True,
                              check=True).stdout.strip()

        marker = root / '.purlin' / 'runtime' / 'test_run.json'
        record = root / '.purlin' / 'runtime' / 'last_sweep.json'
        preamble = '\n'.join([
            'ROOT=' + shlex.quote(str(root)),
            'MARKER=' + shlex.quote(str(marker)),
            'LAST_SWEEP=' + shlex.quote(str(record)),
            'PYTEST_LOG=' + shlex.quote(str(tmp_path / 'pytest.log')),
            # The pytest pool counts as one suite in PASS; its 11 tests are
            # counted individually, so the record must report 11 + 1 = 12.
            "SUITES=$'Proof Plugins (Shell)\\nAll Pytest Tests\\n'",
            "TEST_FILES=$'dev/test_purlin_version.py\\n'",
            'PASS=2',
            'FAIL=0',
            'PYTEST_PASSED=11',
            'PYTEST_FAILED=0',
            'PYTEST_SKIPPED=3',
            'SWEEP_COMPLETE=1',
        ])
        run = subprocess.run(
            [BASH, '-c', preamble + '\n' + _write_marker_function_text()
             + '\nwrite_marker\n'],
            cwd=str(root), capture_output=True, text=True,
        )
        assert run.returncode == 0, (
            f"write_marker exited {run.returncode}\n"
            f"stdout:{run.stdout}\nstderr:{run.stderr}")

        assert marker.is_file(), (
            f"the sweep's exit trap wrote no test_run.json at {marker}\n"
            f"stdout:{run.stdout}\nstderr:{run.stderr}")
        assert record.is_file(), (
            f"the sweep's exit trap wrote no last_sweep.json at {record}: the "
            f"dev sweep must record its own counts in last_sweep.json beside "
            f"test_run.json, because the shared marker is rewritten by every "
            f"proof plugin as it finishes\n"
            f"stdout:{run.stdout}\nstderr:{run.stderr}")

        sweep = json.loads(record.read_text(encoding='utf-8'))
        assert sweep.get('passed') == 12, \
            f"last_sweep.json passed is {sweep.get('passed')!r}, expected 12"
        assert sweep.get('failed') == 0, \
            f"last_sweep.json failed is {sweep.get('failed')!r}, expected 0"
        assert sweep.get('skipped') == 3, \
            f"last_sweep.json skipped is {sweep.get('skipped')!r}, expected 3"
        assert sweep.get('ok') is True, \
            f"last_sweep.json ok is {sweep.get('ok')!r}, expected True"
        assert sweep.get('suites') == ['Proof Plugins (Shell)',
                                       'All Pytest Tests'], \
            f"last_sweep.json suites is {sweep.get('suites')!r}"
        assert sweep.get('commit') == head, \
            f"last_sweep.json commit is {sweep.get('commit')!r}, expected {head!r}"
        assert sweep.get('at'), "last_sweep.json carries no `at` timestamp"
        assert 'runs' not in sweep, (
            f"last_sweep.json is the sweep's own record and is never merged "
            f"with the plugin runs, so it must carry no `runs` key; it has "
            f"{sweep.get('runs')!r}")

        shared = json.loads(marker.read_text(encoding='utf-8'))
        assert shared.get('sweep') == DEV_SWEEP, (
            f"test_run.json sweep is {shared.get('sweep')!r}, expected "
            f"{DEV_SWEEP!r}")
        assert 'runs' in shared, \
            "test_run.json is the merged marker and must carry a `runs` list"

    @pytest.mark.proof("purlin_version", "PROOF-9", "RULE-9", tier="integration")
    def test_unreleased_counts_match_the_sweep_record(self, tmp_path):
        """Legs (b), (c) and (d): the notes parse, the comparison helper, and
        the real record."""
        # ── (b) exactly one counts line in the Unreleased section ──────
        passed, skipped = _parse_unreleased_counts()

        # ── (c) the helper fails loudly on a disagreement ──────────────
        disagreeing = tmp_path / 'last_sweep.json'
        disagreeing.write_text(json.dumps({
            'at': '2026-01-01T00:00:00+00:00',
            'commit': 'deadbeef',
            'passed': passed + 1,
            'failed': 0,
            'skipped': skipped,
            'ok': True,
            'suites': ['All Pytest Tests'],
        }), encoding='utf-8')
        with pytest.raises(AssertionError) as raised:
            _compare_notes_to_sweep(passed, skipped, str(disagreeing))
        message = str(raised.value)
        assert str(passed) in message and str(passed + 1) in message, (
            f"the failure must name the notes count and the sweep's count "
            f"side by side; got: {message}")

        # ── (c) an absent record is an absent observation, not a failure ─
        absent = tmp_path / 'never-swept' / 'last_sweep.json'
        reason = _compare_notes_to_sweep(passed, skipped, str(absent))
        assert reason is not None, \
            "an absent sweep record must yield a skip reason, not a comparison"
        assert str(absent) in reason and 'bash dev/run_tests.sh' in reason, (
            f"the skip reason must name the missing path and how to write it; "
            f"got: {reason}")

        # ── (d) the real record ────────────────────────────────────────
        reason = _compare_notes_to_sweep(passed, skipped, SWEEP_RECORD)
        if reason is not None:
            pytest.skip(reason)
