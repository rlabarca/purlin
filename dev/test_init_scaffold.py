"""Behavioural proofs for `scripts/init/scaffold.py`, the whole of init.

Every case drives the real script against a temp git project. Most call its
`main()` in this process, so a mutation run can see which case caught a
break; the copied-plugin cases and one comparison case run it as a subprocess,
so the command line and these proofs cannot drift apart. Nothing here
re-implements what the script does: the fixture builds a repository, the
script writes, and the assertions read what is on disk and what the summary
said it wrote.

The two ways Purlin is loaded are both exercised. `claude --plugin-dir <this
checkout>` is the default every case runs under, and `TestTheMarketplacePath`
copies the plugin into a temp directory, points `CLAUDE_PLUGIN_ROOT` at the
copy and runs that copy's script, which is what an install from the
marketplace is.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
SCAFFOLD = os.path.join(ROOT, 'scripts', 'init', 'scaffold.py')
TEMPLATE_CONFIG = os.path.join(ROOT, 'templates', 'config.json')
PROOF_DIR = os.path.join(ROOT, 'scripts', 'proof')

sys.path.insert(0, os.path.join(ROOT, 'scripts', 'init'))
import scaffold as scaffold_module  # noqa: E402

# What every framework this release ships a plugin for looks like on disk, and
# the file a project gets when it is detected. The table is the one place a
# case says "a project of this kind", so adding a framework adds a case.
LANGUAGES = {
    'pytest': ({'conftest.py': '', 'tests/test_x.py': 'def test_x(): pass\n'},
               '.purlin/plugins/pytest_purlin.py'),
    'vitest': ({'package.json': '{"devDependencies": {"vitest": "^1.0.0"}}'},
               '.purlin/plugins/vitest_purlin.ts'),
    'jest': ({'package.json': '{"devDependencies": {"jest": "^29.0.0"}}'},
             '.purlin/plugins/jest_purlin.js'),
    'xunit': ({'App.Tests/App.Tests.csproj':
               '<Project><ItemGroup><PackageReference Include="xunit" '
               'Version="2.6.0" /></ItemGroup></Project>'},
              '.purlin/plugins/xunit_purlin.cs'),
    'sql': ({'tests/test_login.sql': '-- @purlin login PROOF-1 RULE-1\n'},
            '.purlin/plugins/sql_purlin.sh'),
    'shell': ({'run.sh': 'echo hello\n'},
              '.purlin/plugins/purlin-proof.sh'),
}

SPEC = """# Feature: login

> Scope: login.py
> Description: One rule, so a project has something for status to report on.

## Rules

- RULE-1: A person signs in with an email address and a password

## Proof

- PROOF-1 (RULE-1): Call `sign_in` with a known pair and verify it returns a session
"""


# ---------------------------------------------------------------------------
# The fixture
# ---------------------------------------------------------------------------

def write(path, text):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def git(root, *args):
    return subprocess.run(['git'] + list(args), cwd=root, capture_output=True,
                          encoding='utf-8', timeout=120)


class Project(object):
    """A temp git project of one language, and the runs made against it."""

    def __init__(self, language='pytest', remote=None, host='github',
                 branch='main'):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix='purlin-init-'))
        self.remote_root = None
        git(self.root, 'init', '-q', '.')
        git(self.root, 'symbolic-ref', 'HEAD', 'refs/heads/%s' % branch)
        git(self.root, 'config', 'user.email', 'dev@example.com')
        git(self.root, 'config', 'user.name', 'Dev')
        git(self.root, 'config', 'commit.gpgsign', 'false')
        if language is not None:
            for rel, body in LANGUAGES[language][0].items():
                write(os.path.join(self.root, rel), body)
        if remote:
            git(self.root, 'remote', 'add', 'origin', remote)
        elif host:
            self._bare(host, branch)

    def _bare(self, host, branch='main'):
        """A local bare repository standing in for the git host.

        Init reads the host off the remote URL. A bare repository on disk
        answers that with no network: the directory name carries the host,
        and one push puts `main` on it.
        """
        self.remote_root = os.path.realpath(
            tempfile.mkdtemp(prefix='purlin-remote-'))
        url = os.path.join(self.remote_root, '%s-origin.git' % host)
        git(self.remote_root, 'init', '--bare', '-q', '-b', branch, url)
        git(self.root, 'remote', 'add', 'origin', url)
        write(os.path.join(self.root, '.keep'), '')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-q', '-m', 'the project')
        git(self.root, 'push', '-q', '-u', 'origin', branch)

    def run(self, *args, **kwargs):
        """Init against this project, and what its summary printed.

        A case runs `main()` in this process, which is what lets a mutation
        run see which break it caught: a break reached only through a child
        process counts as untested. `script=` (a copied plugin) and
        `subprocess=True` run the script as a child instead, the way init
        actually reaches it, and `test_a_child_run_and_an_in_process_run_agree`
        holds the two paths to the same answer.
        """
        env = kwargs.get('env') or {}
        if kwargs.get('script') or kwargs.get('subprocess'):
            return self._run_child(args, env, kwargs.get('script', SCAFFOLD),
                                   kwargs.get('code', 0))
        argv = ['--project-root', self.root, '--yes'] + list(args)
        saved = dict(os.environ)
        os.environ.pop('CLAUDE_PLUGIN_ROOT', None)
        os.environ.update(env)
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), \
                    contextlib.redirect_stderr(err):
                try:
                    code = scaffold_module.main(argv)
                except SystemExit as stop:
                    code = stop.code if isinstance(stop.code, int) else 1
        finally:
            os.environ.clear()
            os.environ.update(saved)
        assert (code or 0) == kwargs.get('code', 0), (
            out.getvalue() + err.getvalue())
        return out.getvalue()

    def _run_child(self, args, env, script, code):
        """The script as a subprocess, which is how init actually reaches it."""
        child = dict(os.environ)
        child.pop('CLAUDE_PLUGIN_ROOT', None)
        child.update(env)
        done = subprocess.run(
            [sys.executable, script, '--project-root', self.root, '--yes']
            + list(args), capture_output=True, encoding='utf-8', timeout=300,
            env=child, stdin=subprocess.DEVNULL)
        assert done.returncode == code, done.stdout + done.stderr
        return done.stdout

    def path(self, rel):
        return os.path.join(self.root, rel)

    def has(self, rel):
        return os.path.exists(self.path(rel))

    def config(self):
        return json.loads(read(self.path('.purlin/config.json')))

    def spec(self, name='login'):
        write(self.path('specs/core/%s.md' % name), SPEC)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)
        if self.remote_root:
            shutil.rmtree(self.remote_root, ignore_errors=True)


@pytest.fixture
def project():
    made = Project()
    yield made
    made.close()


def summary_paths(output):
    """Every path the summary says it wrote, kept, copied or skipped."""
    paths = {}
    for line in output.splitlines():
        parts = line.split(' ', 1)
        if len(parts) == 2 and parts[0] in ('wrote', 'kept', 'copied',
                                            'skipped'):
            rest = parts[1]
            if parts[0] == 'copied' and ' -> ' in rest:
                rest = rest.split(' -> ', 1)[1]
            paths[rest.split(' (')[0].rstrip('/')] = parts[0]
    return paths


# ---------------------------------------------------------------------------
# The one question
# ---------------------------------------------------------------------------

class TestTheOneQuestion:

    @pytest.mark.proof("scaffold", "PROOF-1", "RULE-1")
    def test_a_project_with_code_is_asked_two_questions_and_no_others(self):
        """The gate and trust are the only prompts a detectable project sees."""
        made = Project('pytest')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root],
                input='strong\n', capture_output=True, encoding='utf-8',
                timeout=300)
            assert done.returncode == 0, done.stdout + done.stderr
            assert scaffold_module.GATE_QUESTION in done.stdout
            assert scaffold_module.TRUST_QUESTION in done.stdout
            assert scaffold_module.LANGUAGE_QUESTION not in done.stdout
            assert 'email' not in done.stdout.lower(), done.stdout
            assert made.config()['gate'] == 'strong'
            assert made.config()['trust'] == 'local'
        finally:
            made.close()

    @pytest.mark.parametrize('gate,strength',
                             [('passed', None),
                              ('strong', 70),
                              ('signed', 80)])
    @pytest.mark.proof("scaffold", "PROOF-2", "RULE-2")
    def test_each_answer_derives_its_own_settings(self, project, gate,
                                                  strength):
        project.run('--gate', gate)
        config = project.config()
        assert config['gate'] == gate
        assert config['min_strength'] == strength
        assert sorted(config) == ['ci', 'gate', 'min_strength',
                                  'mutation_engine', 'sql_engine',
                                  'test_framework', 'trust', 'version']
        for key in scaffold_module.gate_module.RETIRED_KEYS:
            assert key not in config, key

    @pytest.mark.proof("scaffold", "PROOF-3", "RULE-3")
    def test_the_gate_flag_answers_the_question_without_asking(self, project):
        output = project.run('--gate', 'passed')
        assert scaffold_module.GATE_QUESTION not in output

    @pytest.mark.proof("scaffold", "PROOF-4", "RULE-4")
    def test_an_unreadable_answer_falls_back_to_passed(self):
        made = Project('pytest')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root],
                input='whenever\n', capture_output=True, encoding='utf-8',
                timeout=300)
            assert made.config()['gate'] == 'passed'
            assert 'is not a gate' in done.stdout
        finally:
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-5", "RULE-5")
    def test_the_config_holds_the_shape_and_no_retired_key(self, project):
        project.run('--gate', 'strong')
        config = project.config()
        assert sorted(config) == ['ci', 'gate', 'min_strength',
                                  'mutation_engine', 'sql_engine',
                                  'test_framework', 'trust', 'version']
        assert config['version'] == read(os.path.join(ROOT, 'VERSION')).strip()

    @pytest.mark.proof("scaffold", "PROOF-5", "RULE-5")
    def test_a_child_run_and_an_in_process_run_agree(self):
        """The command line and `main()` write the same config and summary."""
        child, inline = Project(), Project()
        try:
            child_out = child.run('--gate', 'strong', subprocess=True)
            inline_out = inline.run('--gate', 'strong')
            assert sorted(child.config()) == ['ci', 'gate', 'min_strength',
                                              'mutation_engine', 'sql_engine',
                                              'test_framework', 'trust',
                                              'version']
            assert child.config() == inline.config()
            assert summary_paths(child_out) == summary_paths(inline_out)
            assert (child_out.replace(child.root, '<root>')
                    == inline_out.replace(inline.root, '<root>'))
        finally:
            child.close()
            inline.close()

    @pytest.mark.proof("scaffold", "PROOF-5", "RULE-5")
    def test_the_template_carries_the_same_shape(self):
        template = json.loads(read(TEMPLATE_CONFIG))
        assert sorted(template) == ['ci', 'gate', 'min_strength',
                                    'mutation_engine', 'sql_engine',
                                    'test_framework', 'trust', 'version']
        assert template['version'] == read(
            os.path.join(ROOT, 'VERSION')).strip()


# ---------------------------------------------------------------------------
# Languages
# ---------------------------------------------------------------------------

class TestEachLanguage:

    @pytest.mark.parametrize('language', sorted(LANGUAGES))
    @pytest.mark.proof("scaffold", "PROOF-7", "RULE-7")
    def test_detection_installs_that_language_s_plugin(self, language):
        made = Project(language)
        try:
            output = made.run('--gate', 'passed')
            plugin = LANGUAGES[language][1]
            assert made.has(plugin), output
            # Shell has no detector, so it is the one answer a person gives.
            assert made.config()['test_framework'] == (
                'shell' if language == 'shell' else 'auto')
        finally:
            made.close()

    @pytest.mark.parametrize('language', sorted(LANGUAGES))
    @pytest.mark.proof("scaffold", "PROOF-7", "RULE-7")
    def test_the_copy_is_byte_equal_to_the_plugin_it_came_from(self, language):
        made = Project(language)
        try:
            made.run('--gate', 'passed')
            installed = made.path(LANGUAGES[language][1])
            source = os.path.join(
                PROOF_DIR,
                scaffold_module.plugin_files(ROOT)[language][0])
            with open(installed, 'rb') as copy, open(source, 'rb') as origin:
                assert copy.read() == origin.read()
        finally:
            made.close()

    @pytest.mark.parametrize('language,wiring',
                             [('pytest', 'conftest.py'),
                              ('vitest', 'vitest.config.ts'),
                              ('jest', 'jest.config.js')])
    @pytest.mark.proof("scaffold", "PROOF-8", "RULE-8")
    def test_the_runner_wiring_is_written(self, language, wiring):
        made = Project(language)
        try:
            if language == 'pytest':
                os.remove(made.path('conftest.py'))
                write(made.path('pyproject.toml'), '[tool.pytest]\n')
            made.run('--gate', 'passed')
            assert '%s_purlin' % language in read(made.path(wiring))
        finally:
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-8", "RULE-8")
    def test_a_runner_config_the_project_wrote_is_never_replaced(self):
        made = Project('jest')
        try:
            write(made.path('jest.config.js'), '// ours\n')
            output = made.run('--gate', 'passed')
            assert read(made.path('jest.config.js')) == '// ours\n'
            assert summary_paths(output)['jest.config.js'] == 'kept'
        finally:
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-9", "RULE-9")
    def test_xunit_is_told_how_to_wire_its_logger(self):
        made = Project('xunit')
        try:
            output = made.run('--gate', 'passed')
            assert 'TestLogger.dll' in output
            assert 'dotnet test --logger purlin' in output
        finally:
            made.close()


class TestTheLanguageQuestion:

    @pytest.mark.proof("scaffold", "PROOF-6", "RULE-6")
    def test_an_empty_tree_is_asked_and_shell_is_the_default(self):
        made = Project(None)
        try:
            output = made.run('--gate', 'passed')
            assert scaffold_module.LANGUAGE_QUESTION in output
            assert '[shell]: shell' in output
            assert made.config()['test_framework'] == 'shell'
        finally:
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-6", "RULE-6")
    def test_the_named_framework_is_the_one_installed(self):
        made = Project(None)
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root,
                 '--gate', 'passed'], input='pytest\n', capture_output=True,
                encoding='utf-8', timeout=300)
            assert done.returncode == 0, done.stdout + done.stderr
            assert made.has('.purlin/plugins/pytest_purlin.py')
            assert made.config()['test_framework'] == 'pytest'
        finally:
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-6", "RULE-6")
    def test_a_framework_with_no_plugin_is_read_as_shell(self):
        made = Project(None)
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root,
                 '--gate', 'passed'], input='rspec\n', capture_output=True,
                encoding='utf-8', timeout=300)
            assert 'reading it as shell' in done.stdout
            assert made.config()['test_framework'] == 'shell'
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Nobody is named
# ---------------------------------------------------------------------------

class TestNobodyIsNamed:

    @pytest.mark.proof("scaffold", "PROOF-10", "RULE-10")
    def test_no_gate_asks_who_may_sign(self):
        for gate in ('strong', 'signed'):
            made = Project('pytest')
            try:
                done = subprocess.run(
                    [sys.executable, SCAFFOLD, '--project-root', made.root,
                     '--gate', gate],
                    input='\n', capture_output=True, encoding='utf-8',
                    timeout=300)
                assert done.returncode == 0, done.stdout + done.stderr
                assert 'email' not in done.stdout.lower(), done.stdout
                assert not [key for key in made.config() if 'signer' in key], (
                    made.config())
                if gate == 'signed':
                    assert 'git config gpg.format ssh' in done.stdout
                    assert 'git config commit.gpgsign true' in done.stdout
            finally:
                made.close()

    @pytest.mark.proof("scaffold", "PROOF-12", "RULE-12")
    def test_raising_the_gate_writes_the_setting_and_no_workflow(self,
                                                                 project):
        """The gate no longer decides whether a project has a runner."""
        project.run('--gate', 'passed')
        assert not project.has('.github/workflows/purlin.yml')
        project.run('--gate', 'strong')
        assert not project.has('.github/workflows/purlin.yml')
        assert project.config()['gate'] == 'strong'

    @pytest.mark.proof("scaffold", "PROOF-12", "RULE-12")
    def test_raising_to_signed_keeps_the_workflow_trust_asked_for(self,
                                                                  project):
        write(project.path('.purlin/config.json'),
              json.dumps({'trust': 'remote'}) + '\n')
        project.run('--gate', 'strong')
        before = read(project.path('.github/workflows/purlin.yml'))
        output = project.run('--gate', 'signed')
        assert read(project.path('.github/workflows/purlin.yml')) == before
        assert summary_paths(output)['.github/workflows/purlin.yml'] == 'kept'

    @pytest.mark.proof("scaffold", "PROOF-12", "RULE-12")
    def test_lowering_writes_the_setting_and_deletes_nothing(self, project):
        write(project.path('.purlin/config.json'),
              json.dumps({'trust': 'remote'}) + '\n')
        project.run('--gate', 'signed')
        project.run('--gate', 'passed')
        assert project.config()['gate'] == 'passed'
        assert project.config()['min_strength'] is None
        assert project.has('.github/workflows/purlin.yml')

    @pytest.mark.proof("scaffold", "PROOF-20", "RULE-20")
    def test_a_second_run_at_the_same_gate_changes_nothing(self, project):
        project.run('--gate', 'strong')
        output = project.run('--gate', 'strong')
        assert 'wrote' not in summary_paths(output).values()

    @pytest.mark.proof("scaffold", "PROOF-3", "RULE-3")
    def test_the_gate_is_remembered_when_no_flag_names_one(self, project):
        project.run('--gate', 'strong')
        output = project.run()
        assert scaffold_module.GATE_QUESTION not in output
        assert project.config()['gate'] == 'strong'


# ---------------------------------------------------------------------------
# CI
# ---------------------------------------------------------------------------

class TestTheWorkflow:
    """A workflow is written for two reasons and no others."""

    @staticmethod
    def _trust_remote(made):
        """Answer the trust question `no` before the run, through the config."""
        write(made.path('.purlin/config.json'),
              json.dumps({'trust': 'remote'}) + '\n')

    @staticmethod
    def _foreign_env(made):
        """A spec naming the two operating systems this machine is not."""
        host = scaffold_module.evidence_module.host_os()
        other = [name for name in ('linux', 'macos', 'windows')
                 if name != host]
        write(made.path('specs/core/login.md'),
              SPEC.replace('returns a session\n',
                           'returns a session @env(%s)\n' % other[0]))
        return other[0]

    @pytest.mark.proof("scaffold", "PROOF-13", "RULE-13")
    def test_a_trusted_project_with_no_foreign_proof_gets_no_workflow(
            self, project):
        output = project.run('--gate', 'strong')
        assert not project.has('.github/workflows/purlin.yml')
        assert scaffold_module.workflow_module.NO_REASON in output, output

    @pytest.mark.proof("scaffold", "PROOF-13", "RULE-13")
    def test_a_proof_this_machine_cannot_prove_writes_one(self, project):
        named = self._foreign_env(project)
        output = project.run('--gate', 'passed')
        assert project.has('.github/workflows/purlin.yml'), output
        assert scaffold_module.REMOTE_INTRO in output
        assert named in output, output

    @pytest.mark.proof("scaffold", "PROOF-13", "RULE-13")
    def test_answering_no_to_trust_writes_one(self, project):
        self._trust_remote(project)
        output = project.run('--gate', 'passed')
        assert project.has('.github/workflows/purlin.yml'), output
        assert project.config()['trust'] == 'remote'
        assert 'signing' in output, output

    @pytest.mark.proof("scaffold", "PROOF-13", "RULE-13")
    def test_with_no_remote_nothing_is_written(self):
        made = Project('pytest', host=None)
        try:
            self._trust_remote(made)
            output = made.run('--gate', 'strong')
            assert not made.has('.github/workflows/purlin.yml')
            assert 'there is no git remote' in output
        finally:
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-44", "RULE-44")
    def test_a_missing_prerequisite_is_named_and_nothing_is_written(self):
        made = Project('pytest', remote='https://example.invalid/x.git')
        try:
            self._trust_remote(made)
            output = made.run('--gate', 'strong')
            assert 'neither GitHub nor Azure DevOps' in output, output
            assert not made.has('.github/workflows/purlin.yml')
        finally:
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-44", "RULE-44")
    def test_a_remote_with_no_branch_yet_still_gets_the_workflow(self):
        made = Project('pytest', host=None)
        bare = os.path.realpath(tempfile.mkdtemp(prefix='purlin-empty-remote-'))
        try:
            self._trust_remote(made)
            url = os.path.join(bare, 'github-origin.git')
            git(bare, 'init', '--bare', '-q', '-b', 'main', url)
            git(made.root, 'remote', 'add', 'origin', url)
            output = made.run('--gate', 'strong')
            assert made.has('.github/workflows/purlin.yml'), output
            assert 'is not on origin' not in output, output
            assert 'git push -u' not in output, output
        finally:
            shutil.rmtree(bare, ignore_errors=True)
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-44", "RULE-44")
    def test_the_host_cli_is_reported_either_way(self, project):
        self._trust_remote(project)
        output = project.run('--gate', 'strong')
        assert ('gh is installed' in output
                or 'gh is not installed' in output), output

    @pytest.mark.proof("scaffold", "PROOF-14", "RULE-14")
    def test_the_host_is_read_from_the_remote(self):
        made = Project('pytest', remote='https://github.com/acme/demo.git')
        try:
            self._trust_remote(made)
            made.run('--gate', 'strong')
            assert made.config()['ci'] == 'github'
            assert made.has('.github/workflows/purlin.yml')
        finally:
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-14", "RULE-14")
    def test_an_azure_remote_gets_the_pipeline(self):
        made = Project('pytest',
                       remote='https://dev.azure.com/acme/demo/_git/demo')
        try:
            self._trust_remote(made)
            output = made.run('--gate', 'strong')
            assert made.config()['ci'] == 'azure'
            assert made.has('purlin.azure-pipelines.yml'), output
        finally:
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-15", "RULE-15")
    def test_the_matrix_is_rendered_from_the_env_tags(self, project):
        named = self._foreign_env(project)
        output = project.run('--gate', 'strong')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert '%s-latest' % ('ubuntu' if named == 'linux' else named) \
            in workflow
        assert 'ubuntu-latest' in workflow
        assert 'ubuntu-latest' in output

    @pytest.mark.proof("scaffold", "PROOF-15", "RULE-15")
    def test_no_env_tag_means_one_linux_job(self, project):
        self._trust_remote(project)
        project.spec()
        project.run('--gate', 'strong')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert 'ubuntu-latest' in workflow
        assert 'windows-latest' not in workflow

    @pytest.mark.proof("scaffold", "PROOF-15", "RULE-15")
    def test_the_purlin_release_is_pinned(self, project):
        self._trust_remote(project)
        project.run('--gate', 'strong')
        version = read(os.path.join(ROOT, 'VERSION')).strip()
        assert 'v%s' % version in read(
            project.path('.github/workflows/purlin.yml'))

    @pytest.mark.proof("scaffold", "PROOF-17", "RULE-17")
    def test_no_branch_rule_is_printed(self, project):
        """The gate is the tag now, so there is no rule to apply."""
        for gate in ('passed', 'strong', 'signed'):
            output = project.run('--gate', gate)
            assert 'Branch rule' not in output, output
            assert 'force push' not in output.lower(), output

    @pytest.mark.proof("scaffold", "PROOF-42", "RULE-42")
    def test_the_triggers_are_a_run_branch_and_the_signing_tag(self, project):
        self._trust_remote(project)
        project.run('--gate', 'strong')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        block = workflow.split('\non:\n', 1)[1].split('\npermissions:', 1)[0]
        assert block == ("  push:\n    branches: ['run/**']\n"
                         "    tags: ['signed/**']\n")

    @pytest.mark.proof("scaffold", "PROOF-42", "RULE-42")
    def test_the_last_step_checks_the_gate_and_verifies(self, project):
        self._trust_remote(project)
        project.run('--gate', 'strong')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert 'name: Check the gate' in workflow
        assert 'scripts/ci/gate_check.py" --check --verify' in workflow
        assert 'actions/upload-artifact@v4' not in workflow
        assert workflow.rstrip().endswith('--check --verify')

    @pytest.mark.proof("scaffold", "PROOF-42", "RULE-42")
    def test_the_azure_pipeline_carries_the_same_two(self):
        made = Project('pytest',
                       remote='https://dev.azure.com/acme/demo/_git/demo')
        try:
            TestTheWorkflow._trust_remote(made)
            made.run('--gate', 'strong')
            pipeline = read(made.path('purlin.azure-pipelines.yml'))
            assert '      - run/*\n' in pipeline
            assert '      - signed/*\n' in pipeline
            assert 'pr: none\n' in pipeline
            assert 'displayName: Check the gate' in pipeline
            assert 'scripts/ci/gate_check.py" --check --verify' in pipeline
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Everything else init writes
# ---------------------------------------------------------------------------

class TestWhatInitWrites:

    @pytest.mark.proof("scaffold", "PROOF-18", "RULE-18")
    def test_the_summary_names_every_write(self, project):
        output = project.run('--gate', 'strong')
        named = summary_paths(output)
        for rel in ('.purlin/config.json',
                    '.purlin/plugins/pytest_purlin.py', 'conftest.py',
                    '.gitignore', 'purlin-report.html'):
            assert rel in named, output
            assert project.has(rel), rel
        assert not project.has('designs'), 'init writes no designs folder'

    @pytest.mark.proof("scaffold", "PROOF-19", "RULE-19")
    def test_the_gitignore_block_is_added_once(self, project):
        write(project.path('.gitignore'), 'node_modules/\n')
        project.run('--gate', 'passed')
        first = read(project.path('.gitignore'))
        project.run('--gate', 'passed')
        assert read(project.path('.gitignore')) == first
        assert first.startswith('node_modules/\n')
        assert '.purlin/runtime/' in first
        assert first.count('.purlin/report-data.js') == 1

    @pytest.mark.proof("scaffold", "PROOF-19", "RULE-19")
    def test_the_engine_block_names_the_source_and_the_tests(self, project):
        write(project.path('pyproject.toml'), '[project]\nname = "demo"\n')
        os.makedirs(project.path('src'), exist_ok=True)
        write(project.path('src/app.py'), 'def go():\n    return 1\n')
        project.run('--gate', 'passed')
        text = read(project.path('pyproject.toml'))
        assert '[tool.mutmut]' in text
        assert 'source_paths = ["src"]' in text
        assert 'pytest_add_cli_args_test_selection = ["tests"]' in text
        assert text.startswith('[project]\nname = "demo"\n')

    @pytest.mark.proof("scaffold", "PROOF-19", "RULE-19")
    def test_without_a_pyproject_the_block_lands_in_setup_cfg(self, project):
        project.run('--gate', 'passed')
        assert '[mutmut]' in read(project.path('setup.cfg'))

    @pytest.mark.proof("scaffold", "PROOF-40", "RULE-40")
    def test_the_mutmut_copy_is_ignored_once(self, project):
        write(project.path('greeting.py'), 'def greet(name):\n    return name\n')
        write(project.path('tests/test_greeting.py'), 'def test_greet():\n    pass\n')
        project.run('--gate', 'passed')
        project.run('--gate', 'passed')
        lines = read(project.path('.gitignore')).splitlines()
        assert lines.count('mutants/') == 1

    @pytest.mark.proof("scaffold", "PROOF-19", "RULE-19")
    def test_the_engine_block_is_added_once(self, project):
        project.run('--gate', 'passed')
        project.run('--gate', 'passed')
        assert read(project.path('setup.cfg')).count('[mutmut]') == 1

    @pytest.mark.proof("scaffold", "PROOF-9", "RULE-9")
    def test_a_node_project_is_told_about_stryker(self):
        made = Project('vitest')
        try:
            assert 'Stryker' in made.run('--gate', 'passed')
        finally:
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-18", "RULE-18")
    def test_the_dashboard_is_copied(self, project):
        project.run('--gate', 'passed')
        source = os.path.join(ROOT, 'scripts', 'report', 'purlin-report.html')
        assert read(project.path('purlin-report.html')) == read(source)

    @pytest.mark.proof("scaffold", "PROOF-34", "RULE-34")
    def test_the_next_step_is_the_last_line(self, project):
        lines = project.run('--gate', 'passed').strip().splitlines()
        assert lines[-1].startswith('→')
        assert 'purlin:spec' in lines[-1]

    @pytest.mark.proof("scaffold", "PROOF-34", "RULE-34")
    def test_the_next_step_reads_the_state_once_specs_exist(self, project):
        project.spec()
        lines = project.run('--gate', 'passed').strip().splitlines()
        assert lines[-1].startswith('→')

    @pytest.mark.proof("scaffold", "PROOF-35", "RULE-35")
    def test_no_emoji_and_no_retired_word_in_the_output(self, project):
        output = project.run('--gate', 'signed')
        # Spelled in halves so this file does not carry the words either.
        for word in ('rece' + 'ipt', 'CODE' + 'OWNERS', 'fo' + 'rge',
                     'plat' + 'form', 'tes' + 'ted', 'reco' + 'rded',
                     'appro' + 'ved', 'appro' + 'ver', 'ver' + 'dict',
                     'verify' + '_gate'):
            assert word not in output.lower(), word
        assert all(ord(ch) < 0x1F000 for ch in output)


class TestNoHookIsInstalled:
    """Nothing runs at commit time and nothing runs at push time."""

    @pytest.mark.proof("scaffold", "PROOF-24", "RULE-24")
    def test_no_git_hook_is_written_at_all(self, project):
        project.run('--gate', 'passed')
        for rel in ('.purlin/hooks/pre-push', '.git/hooks/pre-push',
                    '.purlin/hooks/pre-commit', '.git/hooks/pre-commit'):
            assert not project.has(rel), rel

    @pytest.mark.proof("scaffold", "PROOF-24", "RULE-24")
    def test_a_hook_someone_else_wrote_is_left_alone(self, project):
        write(project.path('.git/hooks/pre-push'), '#!/bin/sh\necho mine\n')
        project.run('--gate', 'passed')
        assert read(project.path('.git/hooks/pre-push')) == \
            '#!/bin/sh\necho mine\n'

    @pytest.mark.proof("scaffold", "PROOF-24", "RULE-24")
    def test_the_plugin_ships_no_hook_script(self):
        assert not os.path.exists(
            os.path.join(ROOT, 'scripts', 'hooks', 'pre-push.sh'))


# ---------------------------------------------------------------------------
# The flags
# ---------------------------------------------------------------------------

class TestTheFlags:

    @pytest.mark.proof("scaffold", "PROOF-32", "RULE-32")
    def test_add_keeps_what_was_detected(self, project):
        project.run('--gate', 'passed')
        project.run('--add', 'vitest')
        assert project.config()['test_framework'] == 'pytest,vitest'
        assert project.has('.purlin/plugins/pytest_purlin.py')
        assert project.has('.purlin/plugins/vitest_purlin.ts')

    @pytest.mark.proof("scaffold", "PROOF-32", "RULE-32")
    def test_add_twice_names_the_framework_once(self, project):
        project.run('--gate', 'passed')
        project.run('--add', 'vitest')
        project.run('--add', 'vitest')
        assert project.config()['test_framework'] == 'pytest,vitest'

    @pytest.mark.proof("scaffold", "PROOF-38", "RULE-38")
    def test_a_gate_change_drops_a_framework_the_tree_cannot_run(self, project):
        """An older release wrote down every plugin it shipped, runnable or not."""
        project.run('--gate', 'passed')
        written = project.config()
        written['test_framework'] = 'pytest,jest,shell,vitest'
        write(project.path('.purlin/config.json'),
              json.dumps(written, indent=2))
        output = project.run('--gate', 'strong')
        assert project.config()['test_framework'] == 'pytest,shell'
        for name in ('jest', 'vitest'):
            assert ('dropped %s from test_framework: nothing in the tree '
                    'runs it' % name) in output
        assert not project.has('jest.config.js')
        assert not project.has('vitest.config.ts')

    @pytest.mark.proof("scaffold", "PROOF-38", "RULE-38")
    def test_a_framework_the_tree_carries_survives_a_gate_change(self, project):
        """Wiring the tree carries outranks detection, the stricter test."""
        write(project.path('package.json'), '{"name": "app"}\n')
        project.run('--gate', 'passed')
        written = project.config()
        written['test_framework'] = 'pytest,jest,shell'
        write(project.path('.purlin/config.json'),
              json.dumps(written, indent=2))
        output = project.run('--gate', 'strong')
        assert project.config()['test_framework'] == 'pytest,jest,shell'
        assert 'dropped' not in output

    @pytest.mark.proof("scaffold", "PROOF-30", "RULE-30")
    def test_dry_run_writes_nothing_and_prints_the_plan(self):
        made = Project('pytest')
        try:
            output = made.run('--gate', 'strong', '--dry-run')
            assert '.purlin/config.json' in summary_paths(output)
            assert not made.has('.purlin')
            assert not made.has('conftest.py') or read(
                made.path('conftest.py')) == ''
            assert not made.has('.github/workflows/purlin.yml')
        finally:
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-30", "RULE-30")
    def test_dry_run_outside_a_repository_still_prints_the_plan(self):
        directory = tempfile.mkdtemp(prefix='purlin-nogit-')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', directory,
                 '--gate', 'strong', '--yes', '--dry-run'],
                capture_output=True, encoding='utf-8', timeout=300,
                stdin=subprocess.DEVNULL)
            assert done.returncode == 0, done.stdout + done.stderr
            assert scaffold_module.LANGUAGE_QUESTION in done.stdout
            assert '[shell]: shell' in done.stdout
            assert '.purlin/config.json' in summary_paths(done.stdout)
            assert done.stdout.strip().splitlines()[-1].startswith('→')
            assert os.listdir(directory) == []
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    @pytest.mark.proof("scaffold", "PROOF-31", "RULE-31")
    def test_outside_a_repository_a_real_run_refuses(self):
        directory = tempfile.mkdtemp(prefix='purlin-nogit-')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', directory,
                 '--gate', 'passed', '--yes'], capture_output=True, encoding='utf-8',
                timeout=300, stdin=subprocess.DEVNULL)
            assert done.returncode == 2
            assert 'git init' in done.stderr
            assert os.listdir(directory) == []
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    @pytest.mark.proof("scaffold", "PROOF-31", "RULE-31")
    def test_a_missing_project_root_is_a_bad_invocation(self):
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', '/no/such/dir',
             '--gate', 'passed', '--yes'], capture_output=True, encoding='utf-8',
            timeout=300)
        assert done.returncode == 2

    @pytest.mark.proof("scaffold", "PROOF-33", "RULE-33")
    def test_update_hands_the_project_to_the_upgrade(self, project):
        """`--update` reaches update.py, which is what owns the upgrade."""
        project.run('--gate', 'passed')
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', project.root,
             '--update', '--yes'], capture_output=True, encoding='utf-8', timeout=300,
            stdin=subprocess.DEVNULL)
        if os.path.isfile(os.path.join(ROOT, 'scripts', 'init', 'update.py')):
            assert done.returncode == 0, done.stdout + done.stderr
            assert 'does not carry' not in done.stdout
        else:
            assert done.returncode == 1
            assert 'scripts/init/update.py' in done.stdout

    @pytest.mark.proof("scaffold", "PROOF-33", "RULE-33")
    def test_update_with_dry_run_asks_the_upgrade_what_is_pending(self,
                                                                  project):
        project.run('--gate', 'passed')
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', project.root,
             '--update', '--dry-run'], capture_output=True, encoding='utf-8',
            timeout=300, stdin=subprocess.DEVNULL)
        assert done.returncode in (0, 1, 3), done.stdout + done.stderr
        assert 'does not carry' not in done.stdout


# ---------------------------------------------------------------------------
# Both ways Purlin is loaded
# ---------------------------------------------------------------------------

class TestTheMarketplacePath:
    """An install is a copy under ~/.claude/plugins/cache/purlin/purlin/<v>/."""

    @staticmethod
    def copy_plugin():
        cache = os.path.realpath(tempfile.mkdtemp(prefix='purlin-cache-'))
        installed = os.path.join(cache, 'purlin', 'purlin', '0.10.0')
        os.makedirs(installed)
        for name in ('VERSION', 'templates', 'references', 'scripts'):
            source = os.path.join(ROOT, name)
            target = os.path.join(installed, name)
            if os.path.isdir(source):
                shutil.copytree(source, target,
                                ignore=shutil.ignore_patterns('__pycache__'))
            else:
                shutil.copyfile(source, target)
        return cache, installed

    @pytest.mark.proof("scaffold", "PROOF-22", "RULE-22")
    def test_the_copy_sets_a_project_up_the_same_way(self):
        cache, installed = self.copy_plugin()
        made = Project('pytest')
        try:
            write(made.path('.purlin/config.json'),
                  json.dumps({'trust': 'remote'}) + '\n')
            output = made.run('--gate', 'strong',
                              script=os.path.join(installed, 'scripts', 'init',
                                                  'scaffold.py'),
                              env={'CLAUDE_PLUGIN_ROOT': installed})
            assert made.has('.purlin/plugins/pytest_purlin.py')
            assert made.has('.github/workflows/purlin.yml'), output
            assert '.purlin/config.json' in summary_paths(output)
        finally:
            made.close()
            shutil.rmtree(cache, ignore_errors=True)

    @pytest.mark.proof("scaffold", "PROOF-21", "RULE-21")
    def test_nothing_a_project_holds_names_the_plugin(self):
        cache, installed = self.copy_plugin()
        made = Project('pytest')
        try:
            made.run('--gate', 'strong',
                     script=os.path.join(installed, 'scripts', 'init',
                                         'scaffold.py'),
                     env={'CLAUDE_PLUGIN_ROOT': installed})
            for base, _dirs, names in os.walk(made.root):
                if '.git' in base.split(os.sep):
                    continue
                for name in names:
                    path = os.path.join(base, name)
                    try:
                        text = read(path)
                    except (UnicodeDecodeError, OSError):
                        continue
                    assert installed not in text, path
        finally:
            made.close()
            shutil.rmtree(cache, ignore_errors=True)

    @pytest.mark.proof("scaffold", "PROOF-23", "RULE-23")
    def test_no_project_file_points_at_the_repository_s_own_dev_folder(self):
        made = Project('pytest')
        try:
            made.run('--gate', 'strong')
            for base, _dirs, names in os.walk(made.root):
                if '.git' in base.split(os.sep):
                    continue
                for name in names:
                    path = os.path.join(base, name)
                    try:
                        text = read(path)
                    except (UnicodeDecodeError, OSError):
                        continue
                    assert '/dev/' not in text.replace('/dev/null', ''), path
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The pieces, read directly
# ---------------------------------------------------------------------------

class TestThePieces:

    @pytest.mark.proof("scaffold", "PROOF-7", "RULE-7")
    def test_the_registry_answers_every_framework(self):
        rows = scaffold_module.plugin_files(ROOT)
        assert sorted(rows) == ['jest', 'pytest', 'shell', 'sql', 'vitest',
                                'xunit']
        assert rows['shell'] == ('shell_purlin.sh', 'purlin-proof.sh')
        for source, _installed in rows.values():
            assert os.path.isfile(os.path.join(PROOF_DIR, source))

    @pytest.mark.parametrize('url,host', [
        ('https://github.com/acme/demo.git', 'github'),
        ('git@github.com:acme/demo.git', 'github'),
        ('https://dev.azure.com/acme/demo/_git/demo', 'azure'),
        ('https://acme.visualstudio.com/demo/_git/demo', 'azure'),
        ('https://git.example.com/acme/demo.git', None),
    ])
    @pytest.mark.proof("scaffold", "PROOF-14", "RULE-14")
    def test_the_host_is_read_from_the_url(self, url, host):
        made = Project('pytest', remote=url)
        try:
            assert scaffold_module.git_host(made.root) == host
        finally:
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-14", "RULE-14")
    def test_no_remote_reads_no_host(self):
        made = Project('pytest', host=None)
        try:
            assert scaffold_module.git_host(made.root) is None
            assert scaffold_module.git_remote(made.root) is False
        finally:
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-19", "RULE-19")
    def test_the_source_paths_prefer_src(self, project):
        os.makedirs(project.path('src'), exist_ok=True)
        os.makedirs(project.path('tests'), exist_ok=True)
        assert scaffold_module.mutmut_paths(project.root) == (['src'],
                                                              ['tests'])

    @pytest.mark.proof("scaffold", "PROOF-19", "RULE-19")
    def test_a_package_directory_is_found_when_there_is_no_src(self, project):
        os.makedirs(project.path('demo'), exist_ok=True)
        write(project.path('demo/__init__.py'), '')
        sources, tests = scaffold_module.mutmut_paths(project.root)
        assert sources == ['demo']
        assert tests == ['tests']

    @pytest.mark.proof("scaffold", "PROOF-39", "RULE-39")
    def test_nested_code_is_source_and_a_test_directory_is_the_selection(
            self, project):
        shutil.rmtree(project.path('tests'), ignore_errors=True)
        write(project.path('scripts/run/job.py'), 'def go():\n    return 1\n')
        write(project.path('dev/test_job.py'), 'def test_go():\n    pass\n')
        write(project.path('dev/build.py'), '')
        write(project.path('docs/guide.md'), '# Guide\n')
        assert scaffold_module.mutmut_paths(project.root) == (['scripts'],
                                                              ['dev'])

    @pytest.mark.proof("scaffold", "PROOF-39", "RULE-39")
    def test_src_and_tests_still_win_over_other_directories(self, project):
        write(project.path('src/app.py'), '')
        write(project.path('tools/helper.py'), '')
        write(project.path('tests/test_app.py'), '')
        write(project.path('dev/test_extra.py'), '')
        assert scaffold_module.mutmut_paths(project.root) == (['src'],
                                                              ['tests'])

    @pytest.mark.proof("scaffold", "PROOF-39", "RULE-39")
    def test_modules_at_the_root_are_named_one_by_one(self, project):
        write(project.path('greeting.py'), 'def greet(name):\n    return name\n')
        write(project.path('conftest.py'), '')
        write(project.path('test_greeting.py'), 'def test_greet():\n    pass\n')
        sources, _tests = scaffold_module.mutmut_paths(project.root)
        assert sources == ['greeting.py']

    @pytest.mark.proof("scaffold", "PROOF-39", "RULE-39")
    def test_no_python_anywhere_falls_back_to_the_root(self, project):
        write(project.path('docs/guide.md'), '# Guide\n')
        sources, _tests = scaffold_module.mutmut_paths(project.root)
        assert sources == ['.']
