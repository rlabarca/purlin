"""Behavioural proofs for `scripts/init/scaffold.py`, the whole of init.

Every case drives the real script against a temp git project, most of them as
a subprocess, so the script and these proofs cannot drift apart. Nothing here
re-implements what the script does: the fixture builds a repository, the
script writes, and the assertions read what is on disk and what the summary
said it wrote.

The two ways Purlin is loaded are both exercised. `claude --plugin-dir <this
checkout>` is the default every case runs under, and `TestTheMarketplacePath`
copies the plugin into a temp directory, points `CLAUDE_PLUGIN_ROOT` at the
copy and runs that copy's script, which is what an install from the
marketplace is.
"""

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
    'sql': ({'tests/test_login.sql': '-- @purlin login PROOF-1 RULE-1 unit\n'},
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

- PROOF-1 (RULE-1): Call `sign_in` with a known pair and verify it returns a session @unit
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
                          text=True, timeout=120)


class Project(object):
    """A temp git project of one language, and the runs made against it."""

    def __init__(self, language='pytest', remote=None):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix='purlin-init-'))
        git(self.root, 'init', '-q', '.')
        git(self.root, 'config', 'user.email', 'dev@example.com')
        git(self.root, 'config', 'user.name', 'Dev')
        if language is not None:
            for rel, body in LANGUAGES[language][0].items():
                write(os.path.join(self.root, rel), body)
        if remote:
            git(self.root, 'remote', 'add', 'origin', remote)

    def run(self, *args, **kwargs):
        """The script as a subprocess, which is how init actually reaches it."""
        env = dict(os.environ)
        env.pop('CLAUDE_PLUGIN_ROOT', None)
        env.update(kwargs.get('env') or {})
        script = kwargs.get('script', SCAFFOLD)
        done = subprocess.run(
            [sys.executable, script, '--project-root', self.root, '--yes']
            + list(args), capture_output=True, text=True, timeout=300,
            env=env, stdin=subprocess.DEVNULL)
        assert done.returncode == kwargs.get('code', 0), (
            done.stdout + done.stderr)
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

    def test_a_project_with_code_is_asked_the_gate_and_nothing_else(self):
        """The gate question is the only prompt a detectable project sees."""
        made = Project('pytest')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root],
                input='recorded\n', capture_output=True, text=True,
                timeout=300)
            assert done.returncode == 0, done.stdout + done.stderr
            assert scaffold_module.GATE_QUESTION in done.stdout
            assert scaffold_module.LANGUAGE_QUESTION not in done.stdout
            assert scaffold_module.APPROVER_QUESTION not in done.stdout
            assert made.config()['gate'] == 'recorded'
        finally:
            made.close()

    @pytest.mark.parametrize('gate,strength,review',
                             [('tested', 50, 'never'),
                              ('recorded', 70, 'high'),
                              ('approved', 80, 'medium')])
    def test_each_answer_derives_its_own_settings(self, project, gate,
                                                  strength, review):
        project.run('--gate', gate)
        config = project.config()
        assert config['gate'] == gate
        assert config['min_strength'] == strength
        assert config['ai_review_at'] == review

    def test_the_gate_flag_answers_the_question_without_asking(self, project):
        output = project.run('--gate', 'tested')
        assert scaffold_module.GATE_QUESTION not in output

    def test_an_unreadable_answer_falls_back_to_tested(self):
        made = Project('pytest')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root],
                input='whenever\n', capture_output=True, text=True,
                timeout=300)
            assert made.config()['gate'] == 'tested'
            assert 'is not a gate' in done.stdout
        finally:
            made.close()

    def test_the_config_holds_the_shape_and_no_retired_key(self, project):
        project.run('--gate', 'recorded')
        config = project.config()
        assert sorted(config) == ['ai_review_at', 'ci', 'gate',
                                  'min_strength', 'mutation_engine',
                                  'sql_engine', 'test_framework', 'version']
        assert config['version'] == read(os.path.join(ROOT, 'VERSION')).strip()

    def test_the_template_carries_the_same_shape(self):
        template = json.loads(read(TEMPLATE_CONFIG))
        assert sorted(template) == ['ai_review_at', 'ci', 'gate',
                                    'min_strength', 'mutation_engine',
                                    'sql_engine', 'test_framework', 'version']
        assert template['version'] == read(
            os.path.join(ROOT, 'VERSION')).strip()


# ---------------------------------------------------------------------------
# Languages
# ---------------------------------------------------------------------------

class TestEachLanguage:

    @pytest.mark.parametrize('language', sorted(LANGUAGES))
    def test_detection_installs_that_language_s_plugin(self, language):
        made = Project(language)
        try:
            output = made.run('--gate', 'tested')
            plugin = LANGUAGES[language][1]
            assert made.has(plugin), output
            # Shell has no detector, so it is the one answer a person gives.
            assert made.config()['test_framework'] == (
                'shell' if language == 'shell' else 'auto')
        finally:
            made.close()

    @pytest.mark.parametrize('language', sorted(LANGUAGES))
    def test_the_copy_is_byte_equal_to_the_plugin_it_came_from(self, language):
        made = Project(language)
        try:
            made.run('--gate', 'tested')
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
    def test_the_runner_wiring_is_written(self, language, wiring):
        made = Project(language)
        try:
            if language == 'pytest':
                os.remove(made.path('conftest.py'))
                write(made.path('pyproject.toml'), '[tool.pytest]\n')
            made.run('--gate', 'tested')
            assert '%s_purlin' % language in read(made.path(wiring))
        finally:
            made.close()

    def test_a_runner_config_the_project_wrote_is_never_replaced(self):
        made = Project('jest')
        try:
            write(made.path('jest.config.js'), '// ours\n')
            output = made.run('--gate', 'tested')
            assert read(made.path('jest.config.js')) == '// ours\n'
            assert summary_paths(output)['jest.config.js'] == 'kept'
        finally:
            made.close()

    def test_xunit_is_told_how_to_wire_its_logger(self):
        made = Project('xunit')
        try:
            output = made.run('--gate', 'tested')
            assert 'TestLogger.dll' in output
            assert 'dotnet test --logger purlin' in output
        finally:
            made.close()


class TestTheLanguageQuestion:

    def test_an_empty_tree_is_asked_and_shell_is_the_default(self):
        made = Project(None)
        try:
            output = made.run('--gate', 'tested')
            assert scaffold_module.LANGUAGE_QUESTION in output
            assert '[shell]: shell' in output
            assert made.config()['test_framework'] == 'shell'
        finally:
            made.close()

    def test_the_named_framework_is_the_one_installed(self):
        made = Project(None)
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root,
                 '--gate', 'tested'], input='pytest\n', capture_output=True,
                text=True, timeout=300)
            assert done.returncode == 0, done.stdout + done.stderr
            assert made.has('.purlin/plugins/pytest_purlin.py')
            assert made.config()['test_framework'] == 'pytest'
        finally:
            made.close()

    def test_a_framework_with_no_plugin_is_read_as_shell(self):
        made = Project(None)
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root,
                 '--gate', 'tested'], input='rspec\n', capture_output=True,
                text=True, timeout=300)
            assert 'reading it as shell' in done.stdout
            assert made.config()['test_framework'] == 'shell'
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The approver question
# ---------------------------------------------------------------------------

class TestTheApproverQuestion:

    def test_only_approved_is_asked(self, project):
        assert scaffold_module.APPROVER_QUESTION not in project.run(
            '--gate', 'recorded')

    def test_the_emails_are_written_and_the_signing_setup_printed(self):
        made = Project('pytest')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root,
                 '--gate', 'approved'],
                input='Jane@Acme.com, sam@acme.com\n', capture_output=True,
                text=True, timeout=300)
            assert done.returncode == 0, done.stdout + done.stderr
            assert made.config()['approvers'] == ['jane@acme.com',
                                                  'sam@acme.com']
            assert 'git config gpg.format ssh' in done.stdout
            assert 'git config commit.gpgsign true' in done.stdout
        finally:
            made.close()

    def test_no_list_prints_the_directive_the_gate_will_fail_on(self, project):
        output = project.run('--gate', 'approved')
        assert 'approver list' in output
        assert project.config()['approvers'] == []

    def test_rules_without_a_risk_tag_are_listed(self, project):
        project.spec()
        output = project.run('--gate', 'approved')
        assert 'login RULE-1' in output
        assert 'no risk tag' in output

    def test_a_tagged_rule_is_not_listed(self, project):
        write(project.path('specs/core/login.md'),
              SPEC.replace('and a password',
                           'and a password [risk: high] [origin: pm]'))
        output = project.run('--gate', 'approved')
        assert 'login RULE-1' not in output


# ---------------------------------------------------------------------------
# The gate transitions
# ---------------------------------------------------------------------------

class TestTheGateTransitions:

    def test_raising_to_recorded_adds_the_workflow(self, project):
        project.run('--gate', 'tested')
        assert not project.has('.github/workflows/purlin.yml')
        project.run('--gate', 'recorded')
        assert project.has('.github/workflows/purlin.yml')
        assert project.config()['gate'] == 'recorded'

    def test_raising_to_approved_keeps_what_recorded_wrote(self, project):
        project.run('--gate', 'recorded')
        before = read(project.path('.github/workflows/purlin.yml'))
        output = project.run('--gate', 'approved')
        assert read(project.path('.github/workflows/purlin.yml')) == before
        assert summary_paths(output)['.github/workflows/purlin.yml'] == 'kept'

    def test_lowering_writes_the_setting_and_deletes_nothing(self, project):
        project.run('--gate', 'approved')
        project.run('--gate', 'tested')
        assert project.config()['gate'] == 'tested'
        assert project.config()['min_strength'] == 50
        assert project.has('.github/workflows/purlin.yml')

    def test_lowering_from_approved_keeps_the_approver_list(self, project):
        project.run('--gate', 'approved')
        config = project.config()
        config['approvers'] = ['jane@acme.com']
        write(project.path('.purlin/config.json'),
              json.dumps(config, indent=2) + '\n')
        project.run('--gate', 'recorded')
        assert project.config()['approvers'] == ['jane@acme.com']

    def test_a_second_run_at_the_same_gate_changes_nothing(self, project):
        project.run('--gate', 'recorded')
        output = project.run('--gate', 'recorded')
        assert 'wrote' not in summary_paths(output).values()

    def test_the_gate_is_remembered_when_no_flag_names_one(self, project):
        project.run('--gate', 'recorded')
        output = project.run()
        assert scaffold_module.GATE_QUESTION not in output
        assert project.config()['gate'] == 'recorded'


# ---------------------------------------------------------------------------
# CI
# ---------------------------------------------------------------------------

class TestTheWorkflow:

    def test_tested_writes_no_workflow(self, project):
        output = project.run('--gate', 'tested')
        assert not project.has('.github/workflows/purlin.yml')
        assert 'pass --ci to write it anyway' in output

    def test_ci_under_tested_writes_it_anyway(self, project):
        project.run('--gate', 'tested', '--ci', 'github')
        assert project.has('.github/workflows/purlin.yml')

    def test_the_host_is_read_from_the_remote(self):
        made = Project('pytest', remote='https://github.com/acme/demo.git')
        try:
            made.run('--gate', 'recorded')
            assert made.config()['ci'] == 'github'
            assert made.has('.github/workflows/purlin.yml')
        finally:
            made.close()

    def test_an_azure_remote_gets_the_pipeline(self):
        made = Project('pytest',
                       remote='https://dev.azure.com/acme/demo/_git/demo')
        try:
            output = made.run('--gate', 'recorded')
            assert made.config()['ci'] == 'azure'
            assert made.has('purlin.azure-pipelines.yml')
            assert 'Azure DevOps' in output
        finally:
            made.close()

    def test_ci_ado_overrides_the_remote(self):
        made = Project('pytest', remote='https://github.com/acme/demo.git')
        try:
            made.run('--gate', 'recorded', '--ci', 'ado')
            assert made.has('purlin.azure-pipelines.yml')
            assert made.config()['ci'] == 'azure'
        finally:
            made.close()

    def test_the_matrix_is_rendered_from_the_env_tags(self, project):
        write(project.path('specs/core/login.md'),
              SPEC.replace('@unit', '@unit @env(windows)'))
        output = project.run('--gate', 'recorded')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert 'windows-latest' in workflow
        assert 'windows-latest' in output

    def test_no_env_tag_means_one_linux_job(self, project):
        project.spec()
        project.run('--gate', 'recorded')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert 'ubuntu-latest' in workflow
        assert 'windows-latest' not in workflow

    def test_the_purlin_release_is_pinned(self, project):
        project.run('--gate', 'recorded')
        version = read(os.path.join(ROOT, 'VERSION')).strip()
        assert 'v%s' % version in read(
            project.path('.github/workflows/purlin.yml'))

    def test_upstream_check_adds_the_scheduled_job(self, project):
        project.run('--gate', 'recorded', '--ci', 'github',
                    '--upstream-check')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert 'upstream-check:' in workflow
        assert 'schedule:' in workflow

    def test_without_it_the_scheduled_job_is_absent(self, project):
        project.run('--gate', 'recorded')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert 'upstream-check:' not in workflow

    def test_the_branch_rules_are_printed(self, project):
        output = project.run('--gate', 'recorded')
        assert '.purlin/records/**' in output
        assert 'specs/**/*.approvals/*.ci.json' in output
        assert 'force push' in output.lower()

    def test_tested_prints_only_the_force_push_rule(self, project):
        output = project.run('--gate', 'tested')
        assert 'force push' in output.lower()
        assert '.purlin/records/**' not in output


# ---------------------------------------------------------------------------
# Everything else init writes
# ---------------------------------------------------------------------------

class TestWhatInitWrites:

    def test_the_summary_names_every_write(self, project):
        output = project.run('--gate', 'recorded')
        named = summary_paths(output)
        for rel in ('.purlin/config.json', '.purlin/plugin-root',
                    '.purlin/plugins/pytest_purlin.py', 'conftest.py',
                    '.gitignore', 'designs', 'designs/README.md',
                    '.purlin/records', '.purlin/records/README.md',
                    'purlin-report.html', '.purlin/hooks/pre-push',
                    '.github/workflows/purlin.yml'):
            assert rel in named, output
            assert project.has(rel), rel

    def test_the_two_readmes_are_three_lines_each(self, project):
        project.run('--gate', 'recorded')
        for rel in ('designs/README.md', '.purlin/records/README.md'):
            assert len(read(project.path(rel)).strip().splitlines()) == 3

    def test_the_gitignore_block_is_added_once(self, project):
        write(project.path('.gitignore'), 'node_modules/\n')
        project.run('--gate', 'tested')
        first = read(project.path('.gitignore'))
        project.run('--gate', 'tested')
        assert read(project.path('.gitignore')) == first
        assert first.startswith('node_modules/\n')
        assert '.purlin/runtime/' in first
        assert first.count('.purlin/plugin-root') == 1

    def test_the_engine_block_names_the_source_and_the_tests(self, project):
        write(project.path('pyproject.toml'), '[project]\nname = "demo"\n')
        os.makedirs(project.path('src'), exist_ok=True)
        write(project.path('src/app.py'), 'def go():\n    return 1\n')
        project.run('--gate', 'tested')
        text = read(project.path('pyproject.toml'))
        assert '[tool.mutmut]' in text
        assert 'source_paths = ["src"]' in text
        assert 'pytest_add_cli_args_test_selection = ["tests"]' in text
        assert text.startswith('[project]\nname = "demo"\n')

    def test_without_a_pyproject_the_block_lands_in_setup_cfg(self, project):
        project.run('--gate', 'tested')
        assert '[mutmut]' in read(project.path('setup.cfg'))

    def test_the_engine_block_is_added_once(self, project):
        project.run('--gate', 'tested')
        project.run('--gate', 'tested')
        assert read(project.path('setup.cfg')).count('[mutmut]') == 1

    def test_a_node_project_is_told_about_stryker(self):
        made = Project('vitest')
        try:
            assert 'Stryker' in made.run('--gate', 'tested')
        finally:
            made.close()

    def test_the_dashboard_is_copied(self, project):
        project.run('--gate', 'tested')
        source = os.path.join(ROOT, 'scripts', 'report', 'purlin-report.html')
        assert read(project.path('purlin-report.html')) == read(source)

    def test_the_next_step_is_the_last_line(self, project):
        lines = project.run('--gate', 'tested').strip().splitlines()
        assert lines[-1].startswith('→')
        assert 'purlin:spec' in lines[-1]

    def test_the_next_step_reads_the_state_once_specs_exist(self, project):
        project.spec()
        lines = project.run('--gate', 'tested').strip().splitlines()
        assert lines[-1].startswith('→')

    def test_no_emoji_and_no_retired_word_in_the_output(self, project):
        output = project.run('--gate', 'approved')
        # Spelled in halves so this file does not carry the words either.
        for word in ('rece' + 'ipt', 'au' + 'dit', 'CODE' + 'OWNERS',
                     'fo' + 'rge', 'plat' + 'form'):
            assert word not in output.lower()
        assert all(ord(ch) < 0x1F000 for ch in output)


class TestTheHook:

    def test_the_shim_and_the_delegator_are_written(self, project):
        project.run('--gate', 'tested')
        shim = read(project.path('.purlin/hooks/pre-push'))
        assert 'scripts/hooks/pre-push.sh' in shim
        assert os.access(project.path('.purlin/hooks/pre-push'), os.X_OK)
        delegator = read(project.path('.git/hooks/pre-push'))
        assert '.purlin/hooks/pre-push' in delegator

    def test_no_pre_commit_hook_is_installed(self, project):
        project.run('--gate', 'tested')
        assert not project.has('.purlin/hooks/pre-commit')
        assert not project.has('.git/hooks/pre-commit')

    def test_the_shim_names_no_machine(self, project):
        project.run('--gate', 'tested')
        shim = read(project.path('.purlin/hooks/pre-push'))
        assert ROOT not in shim
        assert project.root not in shim

    def test_a_hook_someone_else_wrote_is_kept(self, project):
        write(project.path('.git/hooks/pre-push'), '#!/bin/sh\necho mine\n')
        output = project.run('--gate', 'tested')
        assert read(project.path('.git/hooks/pre-push')) == \
            '#!/bin/sh\necho mine\n'
        assert 'add this line to it' in output

    def test_a_hook_manager_is_named_rather_than_written_over(self, project):
        write(project.path('.pre-commit-config.yaml'), 'repos: []\n')
        output = project.run('--gate', 'tested')
        assert 'pre-commit framework' in output
        assert not project.has('.git/hooks/pre-push')

    def test_the_plugin_root_file_points_at_this_checkout(self, project):
        project.run('--gate', 'tested')
        assert read(project.path('.purlin/plugin-root')).strip() == ROOT


# ---------------------------------------------------------------------------
# The flags
# ---------------------------------------------------------------------------

class TestTheFlags:

    def test_add_keeps_what_was_detected(self, project):
        project.run('--gate', 'tested')
        project.run('--add', 'vitest')
        assert project.config()['test_framework'] == 'pytest,vitest'
        assert project.has('.purlin/plugins/pytest_purlin.py')
        assert project.has('.purlin/plugins/vitest_purlin.ts')

    def test_add_twice_names_the_framework_once(self, project):
        project.run('--gate', 'tested')
        project.run('--add', 'vitest')
        project.run('--add', 'vitest')
        assert project.config()['test_framework'] == 'pytest,vitest'

    def test_dry_run_writes_nothing_and_prints_the_plan(self):
        made = Project('pytest')
        try:
            output = made.run('--gate', 'recorded', '--dry-run')
            assert '.purlin/config.json' in summary_paths(output)
            assert not made.has('.purlin')
            assert not made.has('conftest.py') or read(
                made.path('conftest.py')) == ''
            assert not made.has('.github/workflows/purlin.yml')
        finally:
            made.close()

    def test_dry_run_outside_a_repository_still_prints_the_plan(self):
        directory = tempfile.mkdtemp(prefix='purlin-nogit-')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', directory,
                 '--gate', 'recorded', '--yes', '--dry-run'],
                capture_output=True, text=True, timeout=300,
                stdin=subprocess.DEVNULL)
            assert done.returncode == 0, done.stdout + done.stderr
            assert scaffold_module.LANGUAGE_QUESTION in done.stdout
            assert '[shell]: shell' in done.stdout
            assert '.purlin/config.json' in summary_paths(done.stdout)
            assert done.stdout.strip().splitlines()[-1].startswith('→')
            assert os.listdir(directory) == []
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def test_outside_a_repository_a_real_run_refuses(self):
        directory = tempfile.mkdtemp(prefix='purlin-nogit-')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', directory,
                 '--gate', 'tested', '--yes'], capture_output=True, text=True,
                timeout=300, stdin=subprocess.DEVNULL)
            assert done.returncode == 2
            assert 'git init' in done.stderr
            assert os.listdir(directory) == []
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def test_a_missing_project_root_is_a_bad_invocation(self):
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', '/no/such/dir',
             '--gate', 'tested', '--yes'], capture_output=True, text=True,
            timeout=300)
        assert done.returncode == 2

    def test_update_hands_the_project_to_the_upgrade(self, project):
        """`--update` reaches update.py, which is what owns the upgrade."""
        project.run('--gate', 'tested')
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', project.root,
             '--update', '--yes'], capture_output=True, text=True, timeout=300,
            stdin=subprocess.DEVNULL)
        if os.path.isfile(os.path.join(ROOT, 'scripts', 'init', 'update.py')):
            assert done.returncode == 0, done.stdout + done.stderr
            assert 'does not carry' not in done.stdout
        else:
            assert done.returncode == 1
            assert 'scripts/init/update.py' in done.stdout

    def test_update_with_dry_run_asks_the_upgrade_what_is_pending(self,
                                                                  project):
        project.run('--gate', 'tested')
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', project.root,
             '--update', '--dry-run'], capture_output=True, text=True,
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

    def test_the_copy_sets_a_project_up_the_same_way(self):
        cache, installed = self.copy_plugin()
        made = Project('pytest')
        try:
            output = made.run('--gate', 'recorded',
                              script=os.path.join(installed, 'scripts', 'init',
                                                  'scaffold.py'),
                              env={'CLAUDE_PLUGIN_ROOT': installed})
            assert made.has('.purlin/plugins/pytest_purlin.py')
            assert made.has('.github/workflows/purlin.yml')
            assert '.purlin/config.json' in summary_paths(output)
        finally:
            made.close()
            shutil.rmtree(cache, ignore_errors=True)

    def test_the_plugin_root_file_names_the_install(self):
        cache, installed = self.copy_plugin()
        made = Project('pytest')
        try:
            made.run('--gate', 'tested',
                     script=os.path.join(installed, 'scripts', 'init',
                                         'scaffold.py'),
                     env={'CLAUDE_PLUGIN_ROOT': installed})
            assert read(made.path('.purlin/plugin-root')).strip() == installed
        finally:
            made.close()
            shutil.rmtree(cache, ignore_errors=True)

    def test_nothing_a_project_holds_names_the_plugin_but_that_one_file(self):
        cache, installed = self.copy_plugin()
        made = Project('pytest')
        try:
            made.run('--gate', 'recorded',
                     script=os.path.join(installed, 'scripts', 'init',
                                         'scaffold.py'),
                     env={'CLAUDE_PLUGIN_ROOT': installed})
            for base, _dirs, names in os.walk(made.root):
                if '.git' in base.split(os.sep):
                    continue
                for name in names:
                    path = os.path.join(base, name)
                    if os.path.relpath(path, made.root) == '.purlin/plugin-root':
                        continue
                    try:
                        text = read(path)
                    except (UnicodeDecodeError, OSError):
                        continue
                    assert installed not in text, path
        finally:
            made.close()
            shutil.rmtree(cache, ignore_errors=True)

    def test_no_project_file_points_at_the_repository_s_own_dev_folder(self):
        made = Project('pytest')
        try:
            made.run('--gate', 'recorded')
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
    def test_the_host_is_read_from_the_url(self, url, host):
        made = Project('pytest', remote=url)
        try:
            assert scaffold_module.git_host(made.root) == host
        finally:
            made.close()

    def test_no_remote_reads_no_host(self, project):
        assert scaffold_module.git_host(project.root) is None

    def test_untagged_rules_names_the_feature_and_the_rule(self, project):
        project.spec()
        assert scaffold_module.untagged_rules(project.root) == [
            ('login', 'RULE-1')]

    def test_the_source_paths_prefer_src(self, project):
        os.makedirs(project.path('src'), exist_ok=True)
        os.makedirs(project.path('tests'), exist_ok=True)
        assert scaffold_module.mutmut_paths(project.root) == (['src'],
                                                              ['tests'])

    def test_a_package_directory_is_found_when_there_is_no_src(self, project):
        os.makedirs(project.path('demo'), exist_ok=True)
        write(project.path('demo/__init__.py'), '')
        sources, tests = scaffold_module.mutmut_paths(project.root)
        assert sources == ['demo']
        assert tests == ['tests']
