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
MIGRATE = os.path.join(ROOT, 'scripts', 'update', 'migrate.py')

GIT_REQUIRED = "Purlin requires git. Run 'git init' first."

# An instruction to the agent to write the config file: an imperative write verb
# opening a sentence, a list item or a bolded lead-in, with
# `.purlin/config.json` as what it writes within the same sentence. Prose that
# only mentions the file ("the run rewrites that key of ...", "three modes, set
# in ...", "Do NOT hand-edit ...") is not an instruction and does not match.
CONFIG_WRITE = re.compile(
    r'(?:^|[.:)]\s|\*\*\s)(?:write|set|save|add|edit|put)\b'
    r'[^\n]{0,90}`\.purlin/config\.json`',
    re.I | re.M)

# The four fields Steps 7b and 7c write: the scaffolder has no flag for any of
# them, so these two steps are the only exemption RULE-58 grants.
AUDIT_FIELDS = ('audit_criteria', 'audit_criteria_pinned',
                'audit_llm', 'audit_llm_name')
CONFIG_WRITE_STEPS = ('Step 7b', 'Step 7c')


def _unwrap(text):
    """Join hard-wrapped prose so one sentence is one line.

    A line is folded onto the one before it only when it continues a prose
    paragraph: not blank, not indented, and not opening a list item, heading,
    quote, table row or code fence. Without this a sentence that happens to
    wrap between its verb and the config path would read as two lines and slip
    past the scan.
    """
    lines = []
    for line in text.split('\n'):
        if (lines and lines[-1].strip() and line.strip()
                and not re.match(r'[\s\-*#>|`]|\d+[.)]', line)):
            lines[-1] = lines[-1].rstrip() + ' ' + line
        else:
            lines.append(line)
    return '\n'.join(lines)


def _skill_steps(skill):
    """`(heading, body)` for every `## Step ...` section of the skill."""
    parts = re.split(r'^## ([^\n]+)$', skill, flags=re.M)
    return [(head, body) for head, body in zip(parts[1::2], parts[2::2])
            if head.startswith('Step ')]


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


def _run_without_symlink(root, *args):
    """Run the real scaffolder in an interpreter where `os.symlink` raises.

    The copy fallback in `_link_or_copy` is reached only when `os.symlink`
    fails, which it never does on a developer machine. A `sitecustomize.py`
    on PYTHONPATH replaces `os.symlink` with one that raises OSError before
    the script is imported, which is the non-symlink host the rule names.
    """
    shim = tempfile.mkdtemp()
    try:
        with open(os.path.join(shim, 'sitecustomize.py'), 'w',
                  encoding='utf-8') as f:
            f.write('import os\n'
                    'def _no_symlink(*a, **k):\n'
                    "    raise OSError(1, 'symlinks are not available here')\n"
                    'os.symlink = _no_symlink\n')
        env = dict(os.environ)
        env['PYTHONPATH'] = shim + os.pathsep + env.get('PYTHONPATH', '')
        result = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', root,
             '--plugin-root', ROOT] + list(args),
            capture_output=True, text=True, env=env)
        return result.returncode, result.stdout, result.stderr
    finally:
        shutil.rmtree(shim, ignore_errors=True)


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
            '--report', 'on', '--digest', 'auto', '--quality-gate', 'off',
            '--force')
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

        # No step writes `.purlin/config.json` by hand except Steps 7b and 7c,
        # and those two only for the four audit fields the scaffolder has no
        # flag for. Every step is scanned, not one slice of the file.
        found = {}
        for head, body in _skill_steps(skill):
            for line in _unwrap(body).split('\n'):
                if CONFIG_WRITE.search(line):
                    found.setdefault(head, []).append(line.strip())
        assert found, "the scan found no config-write instruction at all"

        offenders = sorted(
            (head, line) for head, lines in found.items() for line in lines
            if not head.startswith(CONFIG_WRITE_STEPS))
        assert not offenders, (
            "these steps instruct writing `.purlin/config.json` by hand; the "
            "scaffolder takes the answer as a flag instead: "
            + '; '.join(f'{head}: {line}' for head, line in offenders))

        # The exemption has to be real on both sides: each exempt step still
        # writes the fields it is exempt for, or the clause is dead prose.
        for step in CONFIG_WRITE_STEPS:
            matched = [h for h in found if h.startswith(step)]
            assert matched, (
                f"{step} no longer writes `.purlin/config.json`, so RULE-58's "
                f"exemption for it is stale")
        exempt = '\n'.join(body for head, body in _skill_steps(skill)
                           if head.startswith(CONFIG_WRITE_STEPS))
        missing = [f for f in AUDIT_FIELDS if f not in exempt]
        assert not missing, \
            f"the exempt steps no longer name the audit fields: {missing}"


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
        # A key the template carries but this older config does not: the
        # re-init has to fill it from the template, not leave it out.
        template = json.loads(_read(TEMPLATE_CONFIG))
        assert 'remote_verification' in template, sorted(template)
        del config['remote_verification']
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
        assert 'remote_verification' in after, (
            "--force dropped a template key the old config was missing: "
            f"{sorted(after)}")
        assert after['remote_verification'] == template['remote_verification'], (
            "the missing template key was not filled with the template's own "
            f"value {template['remote_verification']!r}, got "
            f"{after['remote_verification']!r}")
        assert set(template) - set(after) == set(), (
            f"--force left template keys out: {sorted(set(template) - set(after))}")


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

        # RULE-9: seven required fields, `spec_dir` retired (RULE-76). The
        # count is asserted as well as the names so a key added to the
        # template without a row in RULE-9's list cannot slip through.
        assert sorted(template) == ['digest', 'mutation_checks', 'pre_push',
                                    'remote_verification', 'report',
                                    'test_framework', 'version'], \
            sorted(template)
        assert len(template) == 7, sorted(template)

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

        # RULE-66's fallback: a host where os.symlink raises copies instead.
        nolink = _tmp_repo()
        try:
            code, out, err = _run_without_symlink(
                nolink, '--test-framework', 'shell', '--report', 'on')
            assert code == 0, (code, out, err)
            copy = os.path.join(nolink, 'purlin-report.html')
            assert os.path.isfile(copy) and not os.path.islink(copy), \
                "the fallback did not leave a real file"
            source = os.path.join(ROOT, 'scripts', 'report',
                                  'purlin-report.html')
            with open(copy, 'rb') as f:
                copied_bytes = f.read()
            with open(source, 'rb') as f:
                assert copied_bytes == f.read(), \
                    "the copied dashboard is not byte-identical to the plugin's"
            assert any(l.startswith('copied ') and
                       l.endswith('-> purlin-report.html')
                       for l in out.splitlines()), \
                f"the plan never said `copied` for the dashboard: {out!r}"
        finally:
            shutil.rmtree(nolink, ignore_errors=True)

    @pytest.mark.proof("skill_init", "PROOF-70", "RULE-67", tier="integration")
    def test_the_delegator_lands_in_the_hooks_directory_git_actually_reads(
            self, repo):
        """RULE-67: `core.hooksPath` when it is set, the common directory
        otherwise, a delegator only into a free slot, and no pre-commit hook
        at all when the digest is off."""
        code, out, err = _run(repo, '--test-framework', 'shell',
                              '--digest', 'auto')
        assert code == 0, (code, err)
        for name in ('pre-push', 'pre-commit'):
            hook = os.path.join(repo, '.git', 'hooks', name)
            assert os.path.isfile(hook) and not os.path.islink(hook), \
                f"{name} is not a regular file"
            assert os.stat(hook).st_mode & 0o111, f"{name} is not executable"
            body = _read(hook)
            assert body.splitlines() == [
                '#!/bin/sh',
                f'# purlin-delegator (purlin:init): the hook body is '
                f'.purlin/hooks/{name}, tracked in git.',
                f'exec "$(git rev-parse --show-toplevel)/.purlin/hooks/{name}"'
                f' "$@"'], body
            assert f'wrote .git/hooks/{name} (delegates to ' \
                   f'.purlin/hooks/{name})' in out, out
        # A second run keeps what it recognizes as its own.
        code, out, err = _run(repo, '--test-framework', 'shell', '--force')
        assert code == 0, (code, err)
        for name in ('pre-push', 'pre-commit'):
            assert f'kept .git/hooks/{name} (purlin delegator already ' \
                   f'installed)' in out, out

        # core.hooksPath set: git reads nothing in .git/hooks, so nothing of
        # Purlin's may be written there.
        hooked = _tmp_repo()
        try:
            subprocess.run(['git', 'config', 'core.hooksPath', '.githooks'],
                           cwd=hooked, capture_output=True)
            code, out, err = _run(hooked, '--test-framework', 'shell')
            assert code == 0, (code, err)
            for name in ('pre-push', 'pre-commit'):
                assert os.path.isfile(
                    os.path.join(hooked, '.githooks', name)), \
                    f"{name} did not land in core.hooksPath"
                assert not os.path.lexists(
                    os.path.join(hooked, '.git', 'hooks', name)), \
                    f"{name} was written where git would never read it"
                assert f'wrote .githooks/{name} (delegates to ' \
                       f'.purlin/hooks/{name})' in out, out
        finally:
            shutil.rmtree(hooked, ignore_errors=True)

        # A linked worktree: the hooks git runs are the common directory's,
        # never `.git/worktrees/<name>/hooks`, which git never reads.
        base = tempfile.mkdtemp()
        try:
            main = os.path.join(base, 'main')
            os.makedirs(main)
            for args in (['init', '-q'], ['config', 'user.email', 't@e'],
                         ['config', 'user.name', 't'],
                         ['commit', '-q', '--allow-empty', '-m', 'seed']):
                subprocess.run(['git'] + args, cwd=main, capture_output=True)
            tree = os.path.join(base, 'wt')
            subprocess.run(['git', 'worktree', 'add', '-q', tree, '-b', 'lane'],
                           cwd=main, capture_output=True)
            code, out, err = _run(tree, '--test-framework', 'shell')
            assert code == 0, (code, err)
            for name in ('pre-push', 'pre-commit'):
                assert os.path.isfile(
                    os.path.join(main, '.git', 'hooks', name)), \
                    f"{name} did not land in the common directory"
                assert not os.path.exists(os.path.join(
                    main, '.git', 'worktrees', 'wt', 'hooks', name)), \
                    f"{name} landed where a worktree's git never reads hooks"
        finally:
            shutil.rmtree(base, ignore_errors=True)

        quiet = _tmp_repo()
        try:
            code, out, err = _run(quiet, '--test-framework', 'shell',
                                  '--digest', 'off')
            assert code == 0, (code, err)
            assert not os.path.lexists(
                os.path.join(quiet, '.git', 'hooks', 'pre-commit')), \
                "digest off still installed the pre-commit hook"
            assert not os.path.lexists(
                os.path.join(quiet, '.purlin', 'hooks', 'pre-commit')), \
                "digest off still wrote the pre-commit shim"
            assert 'skipped .git/hooks/pre-commit (digest mode "off")' in out, out
            assert 'skipped .purlin/hooks/pre-commit (digest mode "off")' in out, \
                out
        finally:
            shutil.rmtree(quiet, ignore_errors=True)

        # No symlink is made anywhere, so a host where os.symlink raises gets
        # the same working hooks as every other host.
        nolink = _tmp_repo()
        try:
            code, out, err = _run_without_symlink(
                nolink, '--test-framework', 'shell', '--digest', 'auto')
            assert code == 0, (code, out, err)
            assert 'linked ' not in out, \
                f"the hook install still tries to link: {out!r}"
            for name in ('pre-push', 'pre-commit'):
                for path in (os.path.join(nolink, '.git', 'hooks', name),
                             os.path.join(nolink, '.purlin', 'hooks', name)):
                    assert os.path.isfile(path) and not os.path.islink(path), \
                        f"{path} is not a regular file"
                    assert os.stat(path).st_mode & 0o111, \
                        f"{path} is not executable"
        finally:
            shutil.rmtree(nolink, ignore_errors=True)

    @pytest.mark.proof("skill_init", "PROOF-83", "RULE-78", tier="integration")
    def test_a_slot_purlin_does_not_own_is_never_written(self, repo):
        """RULE-78: an existing hook and a hook manager each get the line to
        add, named, and neither has a byte written over it."""
        body = '#!/bin/sh\necho custom\n'
        _write(repo, '.git/hooks/pre-push', body)
        code, out, err = _run(repo, '--test-framework', 'shell')
        assert code == 0, (code, err)
        assert _read(os.path.join(repo, '.git', 'hooks', 'pre-push')) == body, \
            "an existing hook was overwritten"
        line = ('exec "$(git rev-parse --show-toplevel)/.purlin/hooks/pre-push"'
                ' "$@"')
        assert ('skipped .git/hooks/pre-push (a hook is already installed '
                f'there and is kept; add this line to it: {line})') in out, out

        # husky: core.hooksPath names its directory, so its files are the only
        # hooks git runs and Purlin writes into none of them.
        husky = _tmp_repo()
        try:
            _write(husky, '.husky/pre-commit', '#!/bin/sh\necho husky\n')
            subprocess.run(['git', 'config', 'core.hooksPath', '.husky'],
                           cwd=husky, capture_output=True)
            code, out, err = _run(husky, '--test-framework', 'shell')
            assert code == 0, (code, err)
            assert _read(os.path.join(husky, '.husky', 'pre-commit')) == \
                '#!/bin/sh\necho husky\n', "husky's own hook was rewritten"
            assert not os.path.lexists(
                os.path.join(husky, '.husky', 'pre-push')), \
                "a hook was written into the manager's directory"
            for name in ('pre-push', 'pre-commit'):
                assert os.path.isfile(
                    os.path.join(husky, '.purlin', 'hooks', name)), \
                    f"the {name} shim was not written for a husky project"
                assert (f"skipped .husky/{name} (husky manages this "
                        f"repository's hooks; add this line to .husky/{name}: "
                        f'exec "$(git rev-parse --show-toplevel)/.purlin/'
                        f'hooks/{name}" "$@")') in out, out
        finally:
            shutil.rmtree(husky, ignore_errors=True)

        # lefthook and the pre-commit framework are named the same way.
        left = _tmp_repo()
        try:
            subprocess.run(['git', 'config', 'core.hooksPath',
                            '.git/hooks/lefthook'], cwd=left,
                           capture_output=True)
            code, out, err = _run(left, '--test-framework', 'shell')
            assert code == 0, (code, err)
            assert 'lefthook manages' in out and 'lefthook.yml' in out, out
        finally:
            shutil.rmtree(left, ignore_errors=True)

        framework = _tmp_repo()
        try:
            _write(framework, '.pre-commit-config.yaml', 'repos: []\n')
            code, out, err = _run(framework, '--test-framework', 'shell')
            assert code == 0, (code, err)
            assert 'the pre-commit framework manages' in out, out
            assert '.pre-commit-config.yaml:' in out, out
            for name in ('pre-push', 'pre-commit'):
                assert not os.path.lexists(
                    os.path.join(framework, '.git', 'hooks', name)), \
                    f"{name} was written under a hook framework"
        finally:
            shutil.rmtree(framework, ignore_errors=True)


# ---------------------------------------------------------------------------
# RULE-77: the generated shim, .purlin/plugin-root and the install registry
# ---------------------------------------------------------------------------

def _fake_plugin(base, marker):
    """A plugin root whose pre-push script records where it ran from.

    The shim execs `<root>/scripts/hooks/pre-push.sh`, so a directory holding
    that one file is everything a plugin has to be for a resolution test, and
    the line it appends names the root the shim chose.
    """
    hooks = os.path.join(base, 'scripts', 'hooks')
    os.makedirs(hooks, exist_ok=True)
    script = os.path.join(hooks, 'pre-push.sh')
    with open(script, 'w', encoding='utf-8') as f:
        f.write('#!/bin/sh\n'
                'printf "%s\\n" "$(cd "$(dirname "$0")/../.." && pwd)" >> '
                f'"{marker}"\n'
                'exit 0\n')
    os.chmod(script, 0o755)
    return base


def _registry(home, project, install_path, version, last_updated):
    """Write Claude Code's install registry with one entry for this project."""
    directory = os.path.join(home, '.claude', 'plugins')
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, 'installed_plugins.json'), 'w',
              encoding='utf-8') as f:
        json.dump({'version': 1, 'plugins': {'purlin@purlin': [{
            'installPath': install_path,
            'version': version,
            'lastUpdated': last_updated,
            'projectPath': project,
            'scope': 'local',
        }]}}, f)


def _run_shim(repo, name, env):
    """Run a generated shim in `repo` with `env`; returns (rc, out+err)."""
    result = subprocess.run(['sh', os.path.join(repo, '.purlin', 'hooks', name)],
                            cwd=repo, capture_output=True, text=True, env=env)
    return result.returncode, result.stdout + result.stderr


class TestShimResolution:

    @pytest.mark.proof("skill_init", "PROOF-82", "RULE-77", tier="integration")
    def test_the_shim_survives_the_plugin_moving_to_a_new_version(self, repo):
        """RULE-77: the shim is tracked and machine independent, and it finds
        the plugin through Claude Code's install registry, which is what moves
        when the plugin updates and a version-pinned path does not."""
        code, out, err = _run(repo, '--test-framework', 'shell',
                              '--digest', 'auto')
        assert code == 0, (code, err)

        for name in ('pre-push', 'pre-commit'):
            shim = os.path.join(repo, '.purlin', 'hooks', name)
            assert os.path.isfile(shim) and not os.path.islink(shim), name
            assert os.stat(shim).st_mode & 0o111, f"{name} is not executable"
            body = _read(shim)
            assert ROOT not in body, (
                f"the {name} shim names this checkout, so the copy in the "
                f"repository is wrong for every other clone of it")
            assert f'PURLIN_SCRIPT="scripts/hooks/{name}.sh"' in body, \
                f"the {name} shim does not name the plugin's hook script"
            assert 'exec "$PURLIN_ROOT/$PURLIN_SCRIPT" "$@"' in body, \
                f"the {name} shim does not exec that script with its arguments"
        assert 'wrote .purlin/hooks/pre-push' in out, out
        assert _read(os.path.join(repo, '.purlin', 'plugin-root')) == \
            ROOT + '\n', "the plugin root was not recorded for this machine"

        # git tracks the shims and ignores the machine-specific path.
        subprocess.run(['git', 'add', '-A'], cwd=repo, capture_output=True)
        tracked = subprocess.run(['git', 'ls-files'], cwd=repo,
                                 capture_output=True, text=True).stdout.split()
        assert '.purlin/hooks/pre-push' in tracked, tracked
        assert '.purlin/hooks/pre-commit' in tracked, tracked
        assert '.purlin/plugin-root' not in tracked, \
            "the machine-specific plugin path was committed"

        # Candidate 1 set to a directory with no hook script, and candidate 2
        # likewise: both have to be stepped over for the registry to be
        # reached at all.
        home = os.path.join(repo, 'home')
        marker = os.path.join(repo, 'marker.txt')
        for name in ('empty_env', 'empty_pin'):
            os.makedirs(os.path.join(repo, name), exist_ok=True)
        _write(repo, '.purlin/plugin-root',
               os.path.join(repo, 'empty_pin') + '\n')
        env = dict(os.environ)
        env.pop('CLAUDE_PLUGIN_ROOT', None)
        env['PURLIN_PLUGIN_ROOT'] = os.path.join(repo, 'empty_env')
        env['HOME'] = home

        old = _fake_plugin(os.path.join(repo, 'cache', 'purlin', 'purlin',
                                        '0.9.5'), marker)
        _registry(home, repo, old, '0.9.5', '2026-08-20T13:05:56.278Z')
        code, output = _run_shim(repo, 'pre-push', env)
        assert code == 0, output
        assert _read(marker).split() == [old], (
            f"the registry entry's installPath did not run: {output}")

        # The plugin updates: the directory moves to a new version and the
        # registry entry moves with it. A symlink or a recorded path into the
        # old directory dangles here; the shim must not.
        os.remove(marker)
        new = os.path.join(repo, 'cache', 'purlin', 'purlin', '0.11.0')
        shutil.move(old, new)
        _registry(home, repo, new, '0.11.0', '2026-09-01T09:00:00.000Z')
        assert not os.path.exists(old), "the old version path still exists"
        code, output = _run_shim(repo, 'pre-push', env)
        assert code == 0, output
        assert _read(marker).split() == [new], (
            f"the shim did not follow the plugin to its new version path, so "
            f"a plugin update leaves the hook pointing at nothing: {output}")

        # Nothing resolves: the shim says so, names every path it searched,
        # and honours pre-push's own contract per mode.
        os.remove(os.path.join(home, '.claude', 'plugins',
                               'installed_plugins.json'))
        code, output = _run_shim(repo, 'pre-push', env)
        assert code == 0, output
        assert 'WARNING' in output and 'scripts/hooks/pre-push.sh' in output, \
            output
        for path in (os.path.join(repo, 'empty_env'),
                     os.path.join(repo, 'empty_pin')):
            assert path in output, f"the search never named {path}: {output}"
        config = _config(repo)
        config['pre_push'] = 'strict'
        _write(repo, '.purlin/config.json', json.dumps(config, indent=2))
        code, output = _run_shim(repo, 'pre-push', env)
        assert code == 1, (
            f"strict passed a push the plugin was not there to check: {output}")


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
            (('--quality-gate', 'deterministic'),
             {'quality_gate': 'deterministic'}),
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


# ---------------------------------------------------------------------------
# RULE-74: a single-step re-answer is a single config write
# ---------------------------------------------------------------------------

class TestSingleStepReanswer:

    @pytest.mark.proof("skill_init", "PROOF-77", "RULE-74", tier="integration")
    def test_one_flag_rewrites_one_field_and_nothing_else(self, repo):
        """RULE-74: `purlin:init --pre-push` changes the pre-push mode. If the
        script it runs also re-detects the frameworks or re-copies a plugin,
        the step that changed one setting cannot be told from one that changed
        two."""
        code, out, err = _run(
            repo, '--test-framework', 'pytest', '--pre-push', 'warn',
            '--digest', 'auto', '--report', 'on', '--mutation-checks', 'off',
            '--remote-verification', 'off')
        assert code == 0, (code, out, err)

        before_config = _config(repo)
        before_tree = _tree(repo)
        assert before_config['test_framework'] == 'pytest'
        assert 'pytest_purlin.py' in _plugins(repo)

        cases = (
            (('--pre-push', 'strict'), 'pre_push', 'strict'),
            (('--report', 'off'), 'report', False),
            (('--digest', 'warn'), 'digest', 'warn'),
            (('--mutation-checks', 'on'), 'mutation_checks', True),
            (('--quality-gate', 'deterministic'), 'quality_gate',
             'deterministic'),
        )
        for flags, key, value in cases:
            named = ' '.join(flags)
            code, out, err = _run(repo, '--force', *flags)
            assert code == 0, (named, code, out, err)

            after_config = _config(repo)
            assert after_config[key] == value, (
                f"{named} must write {key}={value!r}, got "
                f"{after_config.get(key)!r}")
            changed = {k for k in set(before_config) | set(after_config)
                       if before_config.get(k, '\0') != after_config.get(k, '\0')}
            assert changed == {key}, (
                f"{named} alone must rewrite exactly {key!r}; it changed "
                f"{sorted(changed)}")
            # Named outright, because these two are the ways a lone re-answer
            # stops being one: a re-detected framework and a restamped version.
            assert after_config['test_framework'] == 'pytest', (
                f"{named} rewrote test_framework to "
                f"{after_config['test_framework']!r}; the project's own answer "
                f"must be kept when the flag is absent")
            assert after_config['version'] == before_config['version'], named

            after_tree = _tree(repo)
            assert set(after_tree) == set(before_tree), (
                f"{named} changed the set of files: added "
                f"{sorted(set(after_tree) - set(before_tree))}, removed "
                f"{sorted(set(before_tree) - set(after_tree))}")
            differing = sorted(rel for rel in before_tree
                               if rel != os.path.join('.purlin', 'config.json')
                               and after_tree[rel] != before_tree[rel])
            assert not differing, (
                f"{named} rewrote {differing[0]}; a single-step re-answer "
                f"writes the config and nothing else")

            # The plan says the same thing the tree does: one write, the rest
            # kept or skipped. A re-copied plugin would read `copied ...`.
            stray = [line for line in out.splitlines()
                     if line and not line.startswith(('kept ', 'skipped '))
                     and line != 'wrote .purlin/config.json']
            assert not stray, (
                f"{named} planned more than the config write: {stray}")

            before_config, before_tree = after_config, after_tree


# ---------------------------------------------------------------------------
# RULE-75: `quality_gate` is written only when it is answered
# ---------------------------------------------------------------------------

class TestQualityGate:

    @pytest.mark.proof("skill_init", "PROOF-78", "RULE-75", tier="integration")
    def test_quality_gate_is_written_only_when_answered(self, repo):
        """RULE-75: the quality gate is project policy a project opts into.
        A field written as null, or backfilled as `off`, would read as a
        declaration nobody made."""
        code, out, err = _run(repo, '--test-framework', 'shell')
        assert code == 0, (code, out, err)

        template_keys = set(json.loads(_read(TEMPLATE_CONFIG)))
        written = _config(repo)
        assert set(written) == template_keys, (
            f"an unanswered run must write exactly the template's keys; "
            f"added {sorted(set(written) - template_keys)}, missing "
            f"{sorted(template_keys - set(written))}")
        assert 'quality_gate' not in written, (
            "an unanswered --quality-gate must write no key at all, not "
            f"null: {written.get('quality_gate')!r}")

        # Not a template key, so the update has nothing to backfill and
        # nothing to ask: `--check` must not name it at all.
        check = subprocess.run(
            [sys.executable, MIGRATE, '--check', '--project-root', repo],
            capture_output=True, text=True)
        assert check.returncode == 0, (check.returncode, check.stderr)
        pending = json.loads(check.stdout)['pending']
        gaps = [entry for entry in pending
                if entry['id'] == 'config-fields-missing']
        assert not gaps, (
            f"migrate.py --check reports a config gap on a project with no "
            f"quality_gate: {gaps}")
        assert 'quality_gate' not in check.stdout, (
            f"migrate.py --check names quality_gate: {check.stdout}")

        # Answered, it is written, and it is the only thing that moves.
        before_config, before_tree = written, _tree(repo)
        code, out, err = _run(repo, '--force', '--quality-gate',
                              'deterministic')
        assert code == 0, (code, out, err)
        after_config = _config(repo)
        assert after_config.get('quality_gate') == 'deterministic', \
            after_config
        changed = {k for k in set(before_config) | set(after_config)
                   if before_config.get(k, '\0') != after_config.get(k, '\0')}
        assert changed == {'quality_gate'}, (
            f"--quality-gate deterministic alone must rewrite exactly "
            f"'quality_gate'; it changed {sorted(changed)}")
        after_tree = _tree(repo)
        assert set(after_tree) == set(before_tree), (
            f"added {sorted(set(after_tree) - set(before_tree))}, removed "
            f"{sorted(set(before_tree) - set(after_tree))}")
        differing = sorted(rel for rel in before_tree
                           if rel != os.path.join('.purlin', 'config.json')
                           and after_tree[rel] != before_tree[rel])
        assert not differing, (
            f"--quality-gate rewrote {differing[0] if differing else None}")

        # A re-init that does not name the flag keeps the recorded mode.
        assert _run(repo, '--force', '--pre-push', 'strict')[0] == 0
        kept = _config(repo)
        assert kept.get('quality_gate') == 'deterministic', (
            f"--force without --quality-gate dropped the recorded mode: "
            f"{kept.get('quality_gate')!r}")
        assert set(kept) == template_keys | {'quality_gate'}, sorted(kept)

        # A value outside the closed set is refused, and refused before any
        # write: argparse rejects the choice and the config does not move.
        frozen = _read(os.path.join(repo, '.purlin', 'config.json'))
        code, out, err = _run(repo, '--force', '--quality-gate', 'always')
        assert code == 2, (code, out, err)
        assert 'invalid choice' in err, err
        assert _read(os.path.join(repo, '.purlin', 'config.json')) == frozen, \
            "a refused --quality-gate value still rewrote the config"


# ---------------------------------------------------------------------------
# RULE-71 (precision): each heuristic names a fact only that framework has
# ---------------------------------------------------------------------------

def _detected(files):
    """Scaffold a temp repo holding `files` and return the detected ids.

    `files` is a {relative path: text} map. `--test-framework auto` is the
    only flag, so what lands in `.purlin/plugins/` is exactly what detection
    chose.
    """
    root = _tmp_repo()
    try:
        for rel, text in sorted(files.items()):
            _write(root, rel, text)
        code, out, err = _run(root, '--test-framework', 'auto')
        assert code == 0, (code, err)
        assert _config(root)['test_framework'] == 'auto', _config(root)
        return _plugins(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _detection_table_ids():
    """The framework column of the Detection table, lowercased, in order."""
    content = _read(os.path.join(ROOT, 'references',
                                 'supported_frameworks.md'))
    section = re.search(r'^## Detection$(.*?)(?=^## )', content,
                        re.MULTILINE | re.DOTALL)
    assert section, "supported_frameworks.md has no ## Detection section"
    ids = []
    for line in section.group(1).splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) != 2 or cells[0].startswith('-') or cells[0] == 'Check':
            continue
        name = re.sub(r'\(.*?\)', '', cells[1]).strip().strip('`*').lower()
        ids.append(name)
    return ids


class TestDetectionPrecision:

    @pytest.mark.proof("skill_init", "PROOF-79", "RULE-71", tier="integration")
    def test_each_heuristic_names_a_fact_only_that_framework_has(self):
        """RULE-71: a build file is not a language and a .sql file is not a
        test. Every case below is a project the old substring and
        bare-build-file heuristics called a framework project wrongly."""
        # C: a Makefile alone is a task runner, not a C project.
        assert _detected({'Makefile': 'all:\n\t@echo hi\n',
                          'README.md': 'a python project\n'}) == [], \
            "a Makefile with no *.c file still selected the C plugin"
        assert _detected({'Makefile': 'all:\n\t@echo hi\n',
                          'src/main.c': 'int main(void){return 0;}\n'}) == \
            ['c_purlin.h', 'c_purlin_emit.py'], \
            "a Makefile beside a *.c file did not select C"

        # jest/vitest: the dependency maps are parsed, not the file's text.
        vitest_only = _detected({'package.json': json.dumps({
            'description': 'migrated off jest last year',
            'devDependencies': {'vitest': '^2.0.0'},
        })})
        assert vitest_only == ['vitest_purlin.ts'], (
            f"the word jest in a package.json string selected jest: "
            f"{vitest_only}")
        assert _detected({'package.json': json.dumps({
            'devDependencies': {'jest': '^29.0.0'}})}) == \
            ['jest_purlin.js'], "a declared jest dependency was not detected"

        # SQL: the file name has to say test.
        assert _detected({'tests/fixtures.sql': 'INSERT INTO t VALUES (1);\n'}) \
            == [], "tests/fixtures.sql, which is seed data, selected the SQL plugin"
        assert _detected({'tests/test_schema.sql': 'SELECT 1;\n'}) == \
            ['sql_purlin.sh'], "tests/test_schema.sql did not select SQL"

        # The reference's Detection table and the code's table are one list.
        sys.path.insert(0, os.path.join(ROOT, 'scripts', 'init'))
        try:
            import scaffold
        finally:
            sys.path.pop(0)
        code_ids = [framework_id for framework_id, _ in scaffold._DETECTORS]
        assert _detection_table_ids() == code_ids, (
            f"the Detection table of supported_frameworks.md says "
            f"{_detection_table_ids()} while _DETECTORS says {code_ids}")

    @pytest.mark.proof("skill_init", "PROOF-80", "RULE-71", tier="integration")
    def test_detection_reads_the_package_directories_not_only_the_root(self):
        """RULE-71: a monorepo keeps its indicators one or two levels down,
        and a root-only search told every one of them it had no framework."""
        assert _detected({'packages/api/conftest.py': ''}) == \
            ['pytest_purlin.py'], \
            "packages/api/conftest.py was not seen: detection is root-only"

        # The skip list is not decoration: a vendored package's conftest.py
        # and a tool's cache are not this project's frameworks.
        assert _detected({'node_modules/left-pad/conftest.py': ''}) == [], \
            "a conftest.py inside node_modules selected pytest"
        assert _detected({'.cache/conftest.py': ''}) == [], \
            "a conftest.py inside a dot directory selected pytest"

        mono = {
            'packages/api/package.json': json.dumps(
                {'devDependencies': {'vitest': '^2.0.0'}}),
            'services/db/tests/test_schema.sql': 'SELECT 1;\n',
        }
        assert _detected(mono) == ['sql_purlin.sh', 'vitest_purlin.ts'], \
            _detected(mono)
        assert _detected(mono) == _detected(mono), \
            "the same tree detected two different framework sets"
