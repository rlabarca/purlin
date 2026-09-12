"""Behavioural proofs for `scripts/init/scaffold.py`, the mechanical half of init.

Every case here drives the real script as a subprocess against a temp git
project, the way `dev/test_init_update.py` drives `scripts/update/migrate.py`,
so the script and the proofs cannot drift apart. Nothing in this file
re-implements what the script does: the fixtures build a repository, the script
writes, and the assertions read what is on disk and what the plan said.

Covers `skill_init` PROOF-61 through PROOF-74 (RULE-58 through RULE-71).
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
SCAFFOLD = os.path.join(ROOT, 'scripts', 'init', 'scaffold.py')
SKILL = os.path.join(ROOT, 'skills', 'init', 'SKILL.md')
TEMPLATE_CONFIG = os.path.join(ROOT, 'templates', 'config.json')
TEMPLATE_GITIGNORE = os.path.join(ROOT, 'templates', 'gitignore.purlin')

GIT_REQUIRED = "Purlin requires git. Run 'git init' first."


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def _tmp_repo():
    """A temp directory that is a git repository and nothing else."""
    root = tempfile.mkdtemp()
    subprocess.run(['git', 'init', '-q'], cwd=root, capture_output=True)
    for key, value in (('user.email', 't@e'), ('user.name', 't')):
        subprocess.run(['git', 'config', key, value], cwd=root,
                       capture_output=True)
    return root


def _run(root, *args):
    """Run the real scaffolder; returns (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, SCAFFOLD, '--project-root', root,
         '--plugin-root', ROOT] + list(args),
        capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def _config(root):
    return json.loads(_read(os.path.join(root, '.purlin', 'config.json')))


def _plugins(root):
    directory = os.path.join(root, '.purlin', 'plugins')
    return sorted(os.listdir(directory)) if os.path.isdir(directory) else []


def _tree(root):
    """relpath -> sha256 of the bytes, or `link:<target>` for a symlink.

    `.git` is skipped: its index and logs move on their own, and every file
    this script writes lives outside it apart from the two hooks, which are
    checked by name where they matter.
    """
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != '.git']
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            if os.path.islink(path):
                out[rel] = 'link:' + os.readlink(path)
                continue
            with open(path, 'rb') as f:
                out[rel] = hashlib.sha256(f.read()).hexdigest()
    return out


@pytest.fixture
def repo():
    root = _tmp_repo()
    yield root
    shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# RULE-58: the skill asks, the script writes
# ---------------------------------------------------------------------------

class TestDelegation:

    @pytest.mark.proof("skill_init", "PROOF-61", "RULE-58", tier="integration")
    def test_skill_delegates_the_mechanics_to_the_real_script(self, repo):
        """RULE-58: every flag the skill names is one the script accepts, and
        no step of the skill still writes a file by hand."""
        skill = _read(SKILL)
        assert 'scripts/init/scaffold.py' in skill, \
            "the skill never runs the scaffolder"

        help_text = subprocess.run([sys.executable, SCAFFOLD, '--help'],
                                   capture_output=True, text=True).stdout
        named = set()
        for block in re.findall(r'scaffold\.py"?((?:[^\n`]|\n\s{2,})*)', skill):
            named.update(re.findall(r'--[a-z][a-z-]+', block))
        assert named, "the skill names no flags on its scaffolder invocation"
        # Whole flags, not substrings: `--digest` is a prefix of a renamed
        # `--digest-mode`, and a substring check would call that accepted.
        accepted = set(re.findall(r'--[a-z][a-z-]+', help_text))
        unknown = sorted(f for f in named if f not in accepted)
        assert not unknown, \
            f"the skill passes flags the script does not accept: {unknown}"

        # Every flag the skill names really works, together, on a real repo.
        code, out, err = _run(
            repo, '--test-framework', 'shell', '--pre-push', 'warn',
            '--mutation-checks', 'off', '--remote-verification', 'off',
            '--report', 'on', '--digest', 'auto', '--force')
        assert code == 0, (code, out, err)

        # The two halves the skill keeps: --update is migrate.py, --mcp is 5c.
        assert 'scripts/update/migrate.py' in skill, \
            "the skill must keep --update pointing at migrate.py"
        assert '--mcp' in skill

        steps = skill[skill.index('## Step 1'):skill.index('## Step 8')]
        for by_hand in ('ln -s ', 'chmod +x', 'Copy ALL selected proof plugins'):
            assert by_hand not in steps, (
                f"the init steps still instruct {by_hand!r} by hand; the "
                f"scaffolder owns that")


# ---------------------------------------------------------------------------
# RULE-59, RULE-60, RULE-61: pre-flight, refusal and --force
# ---------------------------------------------------------------------------

class TestPreflight:

    @pytest.mark.proof("skill_init", "PROOF-62", "RULE-59", tier="integration")
    def test_refuses_a_directory_that_is_not_a_git_repository(self):
        """RULE-59: no git, no init, and nothing written on the way out."""
        root = tempfile.mkdtemp()
        try:
            code, out, err = _run(root, '--test-framework', 'shell')
            assert code == 2, (code, out, err)
            assert err.strip() == GIT_REQUIRED, err
            assert os.listdir(root) == [], os.listdir(root)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    @pytest.mark.proof("skill_init", "PROOF-63", "RULE-60", tier="integration")
    def test_refuses_an_initialized_project_without_force(self, repo):
        """RULE-60: exit 1, `--force` named, and not one byte moved."""
        assert _run(repo, '--test-framework', 'shell')[0] == 0
        before = _tree(repo)

        code, out, err = _run(repo, '--test-framework', 'pytest')
        assert code == 1, (code, out, err)
        assert '--force' in err, err
        assert _tree(repo) == before, "a refused run edited the project"

    @pytest.mark.proof("skill_init", "PROOF-64", "RULE-61", tier="integration")
    def test_force_keeps_unanswered_keys_and_existing_artifacts(self, repo):
        """RULE-61: `--force` changes what was re-answered and nothing else."""
        assert _run(repo, '--test-framework', 'shell',
                    '--pre-push', 'strict')[0] == 0
        config = _config(repo)
        config['platforms'] = {'windows-2022': {'os': 'windows'}}
        config['audit_llm'] = 'gemini -m pro -p "{prompt}"'
        _write(repo, '.purlin/config.json', json.dumps(config, indent=2) + '\n')

        code, out, err = _run(repo, '--test-framework', 'shell',
                              '--report', 'off', '--force')
        assert code == 0, (code, out, err)

        after = _config(repo)
        assert after['pre_push'] == 'strict', after
        assert after['platforms'] == {'windows-2022': {'os': 'windows'}}, after
        assert after['audit_llm'] == 'gemini -m pro -p "{prompt}"', after
        assert after['report'] is False, after
        assert after['version'] == _read(os.path.join(ROOT, 'VERSION')).strip()
        assert 'kept .purlin/plugins/purlin-proof.sh' in out, out


# ---------------------------------------------------------------------------
# RULE-62, RULE-63, RULE-64: config, plugin copies, runner wiring
# ---------------------------------------------------------------------------

class TestArtifacts:

    @pytest.mark.proof("skill_init", "PROOF-65", "RULE-62", tier="integration")
    def test_config_is_the_template_with_the_answers_and_the_version(self, repo):
        """RULE-62: the template decides the fields, VERSION the stamp."""
        code, out, err = _run(repo, '--test-framework', 'pytest',
                              '--pre-push', 'warn', '--digest', 'auto',
                              '--report', 'on')
        assert code == 0, (code, out, err)

        template = json.loads(_read(TEMPLATE_CONFIG))
        written = _config(repo)
        assert set(written) == set(template), (sorted(written), sorted(template))

        answered = {'version', 'test_framework', 'pre_push', 'digest', 'report'}
        for key in set(template) - answered:
            assert written[key] == template[key], (
                f"{key} was not taken from templates/config.json: "
                f"{written[key]!r} != {template[key]!r}")
        assert written['test_framework'] == 'pytest'
        assert written['version'] == _read(os.path.join(ROOT, 'VERSION')).strip()

    @pytest.mark.proof("skill_init", "PROOF-66", "RULE-63", tier="integration")
    def test_plugin_copies_are_byte_identical_per_framework(self):
        """RULE-63: the registry names the file, the copy matches it exactly."""
        expected = {
            'pytest': ('pytest_purlin.py', 'pytest_purlin.py'),
            'jest': ('jest_purlin.js', 'jest_purlin.js'),
            'vitest': ('vitest_purlin.ts', 'vitest_purlin.ts'),
            'shell': ('shell_purlin.sh', 'purlin-proof.sh'),
        }
        for framework, (source, dest) in expected.items():
            root = _tmp_repo()
            try:
                code, out, err = _run(root, '--test-framework', framework)
                assert code == 0, (framework, code, err)
                assert _plugins(root) == [dest], (framework, _plugins(root))
                with open(os.path.join(ROOT, 'scripts', 'proof', source),
                          'rb') as f:
                    want = f.read()
                with open(os.path.join(root, '.purlin', 'plugins', dest),
                          'rb') as f:
                    got = f.read()
                assert got == want, f"{dest} is not byte-identical to {source}"
            finally:
                shutil.rmtree(root, ignore_errors=True)

        root = _tmp_repo()
        try:
            assert _run(root, '--test-framework', 'pytest,jest')[0] == 0
            assert _plugins(root) == ['jest_purlin.js', 'pytest_purlin.py'], \
                _plugins(root)
        finally:
            shutil.rmtree(root, ignore_errors=True)

        root = _tmp_repo()
        try:
            code, out, err = _run(root, '--test-framework', 'other')
            assert code == 0, (code, err)
            assert _plugins(root) == [], _plugins(root)
            assert 'purlin:init --add-plugin' in out, out
        finally:
            shutil.rmtree(root, ignore_errors=True)

        root = _tmp_repo()
        try:
            code, out, err = _run(root, '--test-framework', 'gtest')
            assert code == 2, (code, out, err)
            assert 'unknown test framework: gtest' in err, err
            assert not os.path.exists(os.path.join(root, '.purlin')), \
                "an unknown framework still scaffolded the project"
        finally:
            shutil.rmtree(root, ignore_errors=True)

    @pytest.mark.proof("skill_init", "PROOF-67", "RULE-64", tier="integration")
    def test_runner_wiring_is_written_when_absent_and_kept_when_present(self):
        """RULE-64: the written conftest.py is the one a bare pytest run uses."""
        root = _tmp_repo()
        try:
            code, out, err = _run(root, '--test-framework', 'pytest')
            assert code == 0, (code, err)
            assert 'wrote conftest.py' in out, out

            _write(root, 'specs/auth/login.md',
                   '# Feature: login\n\n## Rules\n\n- RULE-1: it logs in\n\n'
                   '## Proof\n\n- PROOF-1 (RULE-1): call it @unit\n')
            _write(root, 'test_login.py',
                   'import pytest\n\n\n'
                   '@pytest.mark.proof("login", "PROOF-1", "RULE-1")\n'
                   'def test_login():\n    assert True\n')

            # No -p, no --override-ini: the conftest.py init wrote is the only
            # thing that can put the plugin in front of this run.
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', 'test_login.py', '-q',
                 '-p', 'no:cacheprovider'],
                cwd=root, capture_output=True, text=True)
            assert result.returncode == 0, result.stdout + result.stderr
            emitted = os.path.join(root, 'specs', 'auth',
                                   'login.proofs-unit.json')
            assert os.path.isfile(emitted), result.stdout + result.stderr
            payload = json.loads(_read(emitted))
            assert payload['proofs'][0]['id'] == 'PROOF-1', payload
        finally:
            shutil.rmtree(root, ignore_errors=True)

        root = _tmp_repo()
        try:
            _write(root, 'conftest.py', '# the project had its own\n')
            code, out, err = _run(root, '--test-framework', 'pytest')
            assert code == 0, (code, err)
            assert 'kept conftest.py' in out, out
            assert _read(os.path.join(root, 'conftest.py')) == \
                '# the project had its own\n'
        finally:
            shutil.rmtree(root, ignore_errors=True)

        for framework, name, plugin in (
                ('jest', 'jest.config.js', '.purlin/plugins/jest_purlin.js'),
                ('vitest', 'vitest.config.ts',
                 '.purlin/plugins/vitest_purlin.ts')):
            root = _tmp_repo()
            try:
                code, out, err = _run(root, '--test-framework', framework)
                assert code == 0, (framework, code, err)
                assert f'wrote {name}' in out, out
                assert plugin in _read(os.path.join(root, name)), \
                    f"{name} does not name {plugin}"
            finally:
                shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# RULE-65, RULE-66, RULE-67: gitignore, dashboard, hooks
# ---------------------------------------------------------------------------

class TestGitArtifacts:

    @pytest.mark.proof("skill_init", "PROOF-68", "RULE-65", tier="integration")
    def test_gitignore_block_is_the_template_and_is_written_once(self, repo):
        """RULE-65: one source for the block, and config.local.json in it."""
        assert _run(repo, '--test-framework', 'shell')[0] == 0
        written = _read(os.path.join(repo, '.gitignore'))
        assert written == _read(TEMPLATE_GITIGNORE), (
            "the gitignore block is not templates/gitignore.purlin verbatim")
        assert '.purlin/config.local.json' in written, written
        assert '.purlin/report-data.js' not in written, written

        def check_ignore(rel):
            return subprocess.run(['git', 'check-ignore', rel], cwd=repo,
                                  capture_output=True, text=True).returncode

        assert check_ignore('.purlin/config.local.json') == 0, \
            "the per-user overlay is not ignored, so it would be committed"
        assert check_ignore('.purlin/report-data.js') == 1, \
            "the committed digest is being ignored"

        assert _run(repo, '--test-framework', 'shell', '--force')[0] == 0
        again = _read(os.path.join(repo, '.gitignore'))
        assert again == written, "a second run rewrote .gitignore"
        assert again.count('.purlin/cache/') == 1, again

        other = _tmp_repo()
        try:
            _write(other, '.gitignore', 'node_modules/\n.purlin/cache/\n')
            assert _run(other, '--test-framework', 'shell')[0] == 0
            seeded = _read(os.path.join(other, '.gitignore'))
            assert seeded.count('.purlin/cache/') == 1, seeded
            assert seeded.startswith('node_modules/\n.purlin/cache/\n'), seeded
            assert '/purlin-report.html' in seeded, seeded
        finally:
            shutil.rmtree(other, ignore_errors=True)

    @pytest.mark.proof("skill_init", "PROOF-69", "RULE-66", tier="integration")
    def test_dashboard_is_a_symlink_and_report_off_deletes_nothing(self, repo):
        """RULE-66: a copy goes stale on the next plugin update; a link does not."""
        code, out, err = _run(repo, '--test-framework', 'shell', '--report', 'on')
        assert code == 0, (code, err)
        link = os.path.join(repo, 'purlin-report.html')
        assert os.path.islink(link), "the dashboard is not a symlink"
        assert os.path.realpath(link) == os.path.realpath(
            os.path.join(ROOT, 'scripts', 'report', 'purlin-report.html'))
        assert any(l.startswith('linked purlin-report.html') for l in
                   out.splitlines()), out

        off = _tmp_repo()
        try:
            assert _run(off, '--test-framework', 'shell', '--report', 'off')[0] == 0
            assert not os.path.lexists(os.path.join(off, 'purlin-report.html'))
            _write(off, 'purlin-report.html', '<!-- the user kept this -->\n')
            code, out, err = _run(off, '--test-framework', 'shell',
                                  '--report', 'off', '--force')
            assert code == 0, (code, err)
            assert _read(os.path.join(off, 'purlin-report.html')) == \
                '<!-- the user kept this -->\n', "report off deleted a dashboard"
        finally:
            shutil.rmtree(off, ignore_errors=True)

    @pytest.mark.proof("skill_init", "PROOF-70", "RULE-67", tier="integration")
    def test_hooks_are_linked_kept_and_skipped_at_digest_off(self, repo):
        """RULE-67: linked to the plugin, never over an existing hook, and
        no pre-commit hook at all when the digest is off."""
        assert _run(repo, '--test-framework', 'shell', '--digest', 'auto')[0] == 0
        for name, script in (('pre-push', 'pre-push.sh'),
                             ('pre-commit', 'pre-commit.sh')):
            hook = os.path.join(repo, '.git', 'hooks', name)
            assert os.path.islink(hook), f"{name} is not a symlink"
            assert os.path.realpath(hook) == os.path.realpath(
                os.path.join(ROOT, 'scripts', 'hooks', script)), name

        existing = _tmp_repo()
        try:
            body = '#!/bin/sh\necho custom\n'
            _write(existing, '.git/hooks/pre-push', body)
            code, out, err = _run(existing, '--test-framework', 'shell')
            assert code == 0, (code, err)
            assert _read(os.path.join(existing, '.git/hooks/pre-push')) == body
            assert ('kept .git/hooks/pre-push (existing non-purlin hook '
                    'preserved)') in out, out
        finally:
            shutil.rmtree(existing, ignore_errors=True)

        quiet = _tmp_repo()
        try:
            code, out, err = _run(quiet, '--test-framework', 'shell',
                                  '--digest', 'off')
            assert code == 0, (code, err)
            assert not os.path.lexists(
                os.path.join(quiet, '.git', 'hooks', 'pre-commit')), \
                "digest off still installed the pre-commit hook"
            assert 'skipped .git/hooks/pre-commit (digest mode "off")' in out, out
        finally:
            shutil.rmtree(quiet, ignore_errors=True)


# ---------------------------------------------------------------------------
# RULE-68, RULE-69, RULE-70, RULE-71: the plan, determinism, answers, auto
# ---------------------------------------------------------------------------

class TestPlanAndAnswers:

    @pytest.mark.proof("skill_init", "PROOF-71", "RULE-68", tier="integration")
    def test_the_plan_names_every_path_and_dry_run_writes_nothing(self, repo):
        """RULE-68: the skill prints this instead of inspecting the tree."""
        args = ('--test-framework', 'pytest', '--pre-push', 'warn',
                '--report', 'on', '--digest', 'auto')
        code, out, err = _run(repo, *args)
        assert code == 0, (code, err)

        verbs = ('wrote ', 'kept ', 'copied ', 'linked ', 'skipped ')
        for line in out.splitlines():
            assert line.startswith(verbs), f"plan line has no verb: {line!r}"
        for path in ('.purlin/config.json', '.gitignore', 'purlin-report.html',
                     '.git/hooks/pre-push', '.git/hooks/pre-commit'):
            assert any(path in line for line in out.splitlines()), \
                f"the plan never names {path}: {out}"

        dry = _tmp_repo()
        try:
            code, dry_out, err = _run(dry, *args + ('--dry-run',))
            assert code == 0, (code, err)
            assert dry_out == out, "the dry run planned something else"
            assert not os.path.exists(os.path.join(dry, '.purlin')), \
                "--dry-run created .purlin/"
            assert not os.path.exists(os.path.join(dry, '.gitignore')), \
                "--dry-run wrote .gitignore"
        finally:
            shutil.rmtree(dry, ignore_errors=True)

    @pytest.mark.proof("skill_init", "PROOF-72", "RULE-69", tier="integration")
    def test_two_runs_with_the_same_answers_leave_the_same_bytes(self, repo):
        """RULE-69: a scaffolder that is not idempotent cannot be re-run."""
        args = ('--test-framework', 'pytest,jest', '--pre-push', 'strict',
                '--report', 'on', '--digest', 'warn')
        assert _run(repo, *args)[0] == 0
        first = _tree(repo)
        assert _run(repo, *args + ('--force',))[0] == 0
        second = _tree(repo)
        assert sorted(second) == sorted(first), (
            f"added: {sorted(set(second) - set(first))}, "
            f"removed: {sorted(set(first) - set(second))}")
        differing = [p for p in first if first[p] != second[p]]
        assert not differing, f"a second run changed: {differing}"

    @pytest.mark.proof("skill_init", "PROOF-73", "RULE-70", tier="integration")
    def test_every_answered_mode_is_written_verbatim(self):
        """RULE-70: not only the defaults reach the config."""
        cases = (
            (('--pre-push', 'strict'), {'pre_push': 'strict'}),
            (('--pre-push', 'off'), {'pre_push': 'off'}),
            (('--digest', 'warn'), {'digest': 'warn'}),
            (('--digest', 'off'), {'digest': 'off'}),
            (('--mutation-checks', 'on', '--report', 'off'),
             {'mutation_checks': True, 'report': False}),
            (('--remote-verification', 'required'),
             {'remote_verification': 'required'}),
        )
        for flags, expected in cases:
            root = _tmp_repo()
            try:
                code, out, err = _run(root, '--test-framework', 'shell', *flags)
                assert code == 0, (flags, code, err)
                written = _config(root)
                for key, value in expected.items():
                    assert written[key] == value, (flags, key, written[key])
            finally:
                shutil.rmtree(root, ignore_errors=True)

    @pytest.mark.proof("skill_init", "PROOF-74", "RULE-71", tier="integration")
    def test_auto_scaffolds_what_it_detects_and_never_defaults_to_shell(self):
        """RULE-71: two indicators, two plugins; no indicator, no plugin."""
        both = _tmp_repo()
        try:
            _write(both, 'conftest.py', '')
            _write(both, 'package.json',
                   '{"devDependencies": {"jest": "^29.0.0"}}\n')
            code, out, err = _run(both, '--test-framework', 'auto')
            assert code == 0, (code, err)
            assert _config(both)['test_framework'] == 'auto', _config(both)
            assert _plugins(both) == ['jest_purlin.js', 'pytest_purlin.py'], \
                _plugins(both)
        finally:
            shutil.rmtree(both, ignore_errors=True)

        bare = _tmp_repo()
        try:
            code, out, err = _run(bare, '--test-framework', 'auto')
            assert code == 0, (code, err)
            assert _plugins(bare) == [], _plugins(bare)
            assert _config(bare)['test_framework'] == 'auto', _config(bare)
            assert 'shell' not in json.dumps(_config(bare)), \
                "detection wrote a silent shell fallback"
            assert ('skipped .purlin/plugins/ (no framework selected; run '
                    'purlin:init --add-plugin or re-run with '
                    '--test-framework)') in out, out
        finally:
            shutil.rmtree(bare, ignore_errors=True)
