"""Behavioural proofs for `scripts/init/scaffold.py`, the whole of init.

Every case drives the real script against a temp git project. Most call its
`main()` in this process, so a mutation run can see which case caught a
break; the marketplace-copy cases and one comparison case run it as a subprocess,
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
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
SCAFFOLD = os.path.join(ROOT, 'scripts', 'init', 'scaffold.py')
TEMPLATE_CONFIG = os.path.join(ROOT, 'templates', 'config.json')

sys.path.insert(0, os.path.join(ROOT, 'scripts', 'init'))
import scaffold as scaffold_module  # noqa: E402
from purlin import frameworks as frameworks_module  # noqa: E402
from reports_project import (GO_SPECS, REPO, _evidence,  # noqa: E402
                             _fixture, _run, _write)

# What a project of each framework init writes a command for looks like on
# disk. The table is the one place a case says "a project of this kind", so
# adding a framework adds a case.
LANGUAGES = {
    'pytest': {'conftest.py': '', 'tests/test_x.py': 'def test_x(): pass\n'},
    'vitest': {'package.json': '{"devDependencies": {"vitest": "^1.0.0"}}'},
    'jest': {'package.json': '{"devDependencies": {"jest": "^29.0.0"}}'},
    'dotnet': {'App.Tests/App.Tests.csproj':
               '<Project><ItemGroup><PackageReference Include="xunit" '
               'Version="2.6.0" /></ItemGroup></Project>'},
    'go': {'go.mod': 'module example.com/shop\n',
           'cart/cart_test.go': 'package cart\n'},
    'sql': {'tests/test_login.sql': 'SELECT 1;\n'},
    'shell': {'tests/login.test.sh': 'exit 0\n'},
}

# The eight settings a new project gets, and the only ones.
CONFIG_KEYS = sorted(['version', 'gate', 'mutation_engine', 'min_strength',
                      'audit_parallel', 'tests', 'ci', 'trust'])

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
            for rel, body in LANGUAGES[language].items():
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


def tree(root):
    """Every path under `root` outside `.git/`: a file's bytes, a folder None."""
    found = {}
    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != '.git')
        here = os.path.relpath(base, root).replace(os.sep, '/')
        prefix = '' if here == '.' else here + '/'
        for name in dirs:
            found[prefix + name] = None
        for name in names:
            with open(os.path.join(base, name), 'rb') as handle:
                found[prefix + name] = handle.read()
    return found


def asked(output):
    """The first line of each question a run with answers on stdin asked."""
    return [part.split('\n', 1)[0]
            for part in re.split(r'\[[^\]\n]*\]: ', output)[:-1]]


# ---------------------------------------------------------------------------
# The one question
# ---------------------------------------------------------------------------

class TestTheOneQuestion:

    # purlin: scaffold PROOF-1
    def test_a_project_with_code_is_asked_three_questions_and_no_others(self):
        """Gate, mutation and trust, in that order, for a detectable project."""
        made = Project('pytest')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root],
                input='strong\n', capture_output=True, encoding='utf-8',
                timeout=300)
            assert done.returncode == 0, done.stdout + done.stderr
            out = done.stdout
            mutation = scaffold_module.MUTATION_QUESTION % 'mutmut'
            for question in (scaffold_module.GATE_QUESTION, mutation,
                             scaffold_module.TRUST_QUESTION):
                assert question in out, (question, out)
            assert (out.index(scaffold_module.GATE_QUESTION)
                    < out.index(mutation)
                    < out.index(scaffold_module.TRUST_QUESTION)), out
            # The three are the only questions: one answer prompt each.
            assert asked(out) == [scaffold_module.GATE_QUESTION, mutation,
                                  scaffold_module.TRUST_QUESTION], out
            assert scaffold_module.COMMAND_QUESTION not in out
            assert 'email' not in out.lower(), out
            assert made.config()['gate'] == 'strong'
            assert made.config()['mutation_engine'] == 'none'
            assert made.config()['trust'] == 'local'
        finally:
            made.close()

    @pytest.mark.parametrize('gate,strength',
                             [('passed', None),
                              ('strong', 70),
                              ('signed', 80)])
    # purlin: scaffold PROOF-2
    def test_each_answer_derives_its_own_settings(self, project, gate,
                                                  strength):
        project.run('--gate', gate, '--mutation')
        config = project.config()
        assert config['gate'] == gate
        assert config['min_strength'] == strength
        assert sorted(config) == CONFIG_KEYS

    @pytest.mark.parametrize('gate', ['passed', 'strong', 'signed'])
    # purlin: scaffold PROOF-2
    def test_with_mutation_off_there_is_no_minimum(self, project, gate):
        project.run('--gate', gate)
        assert project.config()['min_strength'] is None

    # purlin: scaffold PROOF-3
    def test_the_gate_flag_answers_the_question_without_asking(self, project):
        output = project.run('--gate', 'passed')
        assert scaffold_module.GATE_QUESTION not in output

    # purlin: scaffold PROOF-4
    def test_an_unreadable_answer_falls_back_to_passed(self):
        made = Project('pytest')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root],
                input='whenever\n', capture_output=True, encoding='utf-8',
                timeout=300)
            assert made.config()['gate'] == 'passed'
            assert 'is not a gate' in done.stdout
            assert done.returncode == 0, done.stdout + done.stderr
            # A piped answer ends no line, so the prompt is set aside first.
            lines = re.sub(r'\[[^\]\n]*\]: ', '', done.stdout).splitlines()
            assert ('purlin: "whenever" is not a gate; reading it as passed.'
                    in lines), done.stdout
        finally:
            made.close()

    # purlin: scaffold PROOF-5
    def test_the_config_holds_the_shape(self, project):
        output = project.run('--gate', 'strong')
        config = project.config()
        assert sorted(config) == CONFIG_KEYS
        assert config['version'] == read(os.path.join(ROOT, 'VERSION')).strip()
        assert config['audit_parallel'] == 4
        assert 'audit_parallel' not in output
        assert 'at a time' not in output

    # purlin: scaffold PROOF-5
    def test_audit_parallel_keeps_a_value_in_range_only(self, project):
        project.run('--gate', 'passed')
        for written, kept in ((9, 9), (40, 4)):
            config = project.config()
            config['audit_parallel'] = written
            write(project.path('.purlin/config.json'), json.dumps(config))
            project.run()
            assert project.config()['audit_parallel'] == kept, written

    # purlin: scaffold PROOF-5
    def test_a_child_run_and_an_in_process_run_agree(self):
        """The command line and `main()` write the same config and summary."""
        child, inline = Project(), Project()
        try:
            child_out = child.run('--gate', 'strong', subprocess=True)
            inline_out = inline.run('--gate', 'strong')
            assert sorted(child.config()) == CONFIG_KEYS
            assert child.config() == inline.config()
            assert summary_paths(child_out) == summary_paths(inline_out)
            assert (child_out.replace(child.root, '<root>')
                    == inline_out.replace(inline.root, '<root>'))
        finally:
            child.close()
            inline.close()

    # purlin: scaffold PROOF-5
    def test_the_template_carries_the_same_shape(self):
        template = json.loads(read(TEMPLATE_CONFIG))
        assert sorted(template) == CONFIG_KEYS
        assert template['version'] == read(
            os.path.join(ROOT, 'VERSION')).strip()


# ---------------------------------------------------------------------------
# Mutation testing, and the evidence folder
# ---------------------------------------------------------------------------

def _answering(made, answers, *args):
    """The script as a child reading `answers` on stdin, with no `--yes`."""
    done = subprocess.run(
        [sys.executable, SCAFFOLD, '--project-root', made.root] + list(args),
        input=answers, capture_output=True, encoding='utf-8', timeout=300)
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


class TestMutationTesting:

    # purlin: scaffold PROOF-45
    def test_yes_turns_it_on_and_wires_the_engine(self):
        made = Project('pytest')
        try:
            out = _answering(made, 'y\n\n', '--gate', 'strong')
            assert scaffold_module.MUTATION_QUESTION % 'mutmut' in out, out
            assert made.config()['mutation_engine'] == 'auto'
            assert made.config()['min_strength'] == 70
            assert '[mutmut]' in read(made.path('setup.cfg'))
        finally:
            made.close()

    # purlin: scaffold PROOF-45
    def test_no_turns_it_off_and_wires_nothing(self):
        made = Project('pytest')
        try:
            _answering(made, 'n\n\n', '--gate', 'strong')
            assert made.config()['mutation_engine'] == 'none'
            assert made.config()['min_strength'] is None
            assert not made.has('setup.cfg')
            assert 'mutants/' not in read(made.path('.gitignore'))
        finally:
            made.close()

    # purlin: scaffold PROOF-45
    def test_a_framework_with_no_engine_is_asked_nothing(self):
        made = Project('shell')
        try:
            out = _answering(made, '\n\n', '--gate', 'strong')
            assert 'Measure test strength' not in out, out
            assert made.config()['mutation_engine'] == 'none'
            assert made.config()['min_strength'] is None
            assert 'no engine breaks shell code' in out, out
        finally:
            made.close()

    # purlin: scaffold PROOF-45
    def test_a_value_the_config_carries_is_kept_without_asking(self, project):
        write(project.path('.purlin/config.json'),
              json.dumps({'mutation_engine': 'auto'}) + '\n')
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', project.root,
             '--gate', 'passed'], capture_output=True, encoding='utf-8',
            timeout=300, stdin=subprocess.DEVNULL)
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'Measure test strength' not in done.stdout, done.stdout
        assert project.config()['mutation_engine'] == 'auto'

    # purlin: scaffold PROOF-46
    def test_yes_leaves_it_off(self, project):
        output = project.run('--gate', 'strong')
        question = scaffold_module.MUTATION_QUESTION % 'mutmut'
        assert '%s\n[n]: n' % question in output, output
        assert project.config()['mutation_engine'] == 'none'
        assert project.config()['min_strength'] is None
        assert not project.has('setup.cfg')
        # Every other question takes its default too.
        assert '%s\n[y]: y' % scaffold_module.TRUST_QUESTION in output, output
        assert project.config()['trust'] == 'local'
        fresh = Project('pytest')
        try:
            output = fresh.run()
            assert '[passed]: passed' in output.splitlines(), output
            assert fresh.config()['gate'] == 'passed'
        finally:
            fresh.close()

    # purlin: scaffold PROOF-46
    def test_the_flag_turns_it_on_without_asking(self, project):
        output = project.run('--gate', 'strong', '--mutation')
        assert 'Measure test strength' not in output
        assert project.config()['mutation_engine'] == 'auto'
        assert project.config()['min_strength'] == 70
        assert '[mutmut]' in read(project.path('setup.cfg'))


class TestTheEvidenceFolder:

    # purlin: scaffold PROOF-47
    def test_the_folder_and_its_readme_are_written_once(self, project):
        output = project.run('--gate', 'passed')
        readme = project.path('.purlin/evidence/README.md')
        with open(readme, 'rb') as got, open(os.path.join(
                ROOT, 'templates', 'evidence-readme.md'), 'rb') as want:
            assert got.read() == want.read()
        text = read(readme)
        assert 'local/' in text and 'ci/' in text
        assert summary_paths(output)['.purlin/evidence/README.md'] == 'wrote'
        again = project.run('--gate', 'passed')
        assert summary_paths(again)['.purlin/evidence/README.md'] == 'kept'
        # Kept means the bytes: a README the project edited stays edited.
        write(readme, text + 'Our own note.\n')
        third = project.run('--gate', 'passed')
        assert read(readme) == text + 'Our own note.\n'
        assert summary_paths(third)['.purlin/evidence/README.md'] == 'kept'


# ---------------------------------------------------------------------------
# Languages
# ---------------------------------------------------------------------------

_JS_GLOBS = ['**/*.%s.%s' % (kind, ext) for kind in ('test', 'spec')
             for ext in ('js', 'jsx', 'mjs', 'cjs', 'ts', 'tsx')]

# Where each framework's report lands and the globs its tests live under,
# written out here so a wrong value in the framework table is seen.
REPORTS_AND_GLOBS = {
    'pytest': ('.purlin/runtime/reports/pytest.xml',
               ['**/test_*.py', '**/*_test.py']),
    'vitest': ('.purlin/runtime/reports/vitest.xml', _JS_GLOBS),
    'jest': ('.purlin/runtime/reports/jest.xml', _JS_GLOBS),
    'dotnet': ('.purlin/runtime/reports/dotnet', ['**/*.cs']),
    'go': ('-', ['**/*_test.go']),
    'sql': (None, ['**/test_*.sql', '**/*_test.sql', '**/*.test.sql']),
    'shell': (None, ['**/*.test.sh']),
}


class TestEachLanguage:

    @pytest.mark.parametrize('language', sorted(LANGUAGES))
    # purlin: scaffold PROOF-7
    def test_detection_writes_that_framework_s_suite(self, language):
        made = Project(language)
        try:
            made.run('--gate', 'passed')
            (suite,) = made.config()['tests']
            assert suite == frameworks_module.entry_for(language)
            assert suite['name'] == language
            if suite['format'] in ('junit', 'trx'):
                assert '{report}' in suite['run'], suite
            assert (suite['report'], suite['files']) == \
                REPORTS_AND_GLOBS[language], suite
        finally:
            made.close()

    # purlin: scaffold PROOF-7
    def test_each_command_carries_the_flag_that_writes_its_report(self):
        expected = {
            'pytest': ('--junitxml={report}', 'junit'),
            'vitest': ('--outputFile.junit={report}', 'junit'),
            'jest': ('--reporters=jest-junit', 'junit'),
            'dotnet': ('--logger trx --results-directory {report}', 'trx'),
            'go': ('go test -json', 'gotest'),
            'sql': ('sqlite3 -bail', 'exit'),
            'shell': ('bash {files}', 'exit'),
        }
        assert sorted(frameworks_module.ENTRIES) == sorted(expected)
        for name, (flag, fmt) in expected.items():
            entry = frameworks_module.entry_for(name)
            assert flag in entry['run'], name
            assert entry['format'] == fmt, name
            assert entry['files'], name
        # The page a reader meets shows the same entries, word for word.
        page = read(os.path.join(ROOT, 'references', 'supported_frameworks.md'))
        shown = [json.loads(block.split('```', 1)[0])
                 for block in page.split('```json\n')[1:]]
        assert shown == [frameworks_module.entry_for(name) for name in
                         ('pytest', 'vitest', 'jest', 'dotnet', 'go', 'sql',
                          'shell')]

    @pytest.mark.parametrize('language,wiring',
                             [('pytest', 'conftest.py'),
                              ('vitest', 'vitest.config.ts'),
                              ('jest', 'jest.config.js')])
    # purlin: scaffold PROOF-8
    def test_nothing_is_written_into_the_test_suite(self, language, wiring):
        made = Project(language)
        try:
            if language == 'pytest':
                os.remove(made.path('conftest.py'))
                write(made.path('pyproject.toml'), '[tool.pytest]\n')
            before = tree(made.root)
            output = made.run('--gate', 'passed')
            assert not made.has(wiring), output
            assert wiring not in summary_paths(output)
            # Every file the project held reads the same, and the only paths
            # added are Purlin's own: nothing lands among the tests.
            after = tree(made.root)
            assert {rel: after.get(rel) for rel in before} == before
            assert sorted(set(after) - set(before)) == [
                '.gitignore', '.purlin', '.purlin/config.json',
                '.purlin/evidence', '.purlin/evidence/README.md',
                'purlin-report.html', 'specs', 'specs/_anchors'], output
        finally:
            made.close()

    # purlin: scaffold PROOF-8
    def test_a_runner_config_the_project_wrote_is_left_alone(self):
        made = Project('jest')
        try:
            write(made.path('jest.config.js'), '// ours\n')
            output = made.run('--gate', 'passed')
            assert read(made.path('jest.config.js')) == '// ours\n'
            assert 'jest.config.js' not in summary_paths(output)
        finally:
            made.close()

    # purlin: scaffold PROOF-9
    def test_a_framework_that_needs_something_added_is_told_what(self):
        for language, line in (
                ('jest', 'jest needs the package jest-junit to write its '
                         'report: run npm install --save-dev jest-junit'),
                ('sql', 'sql runs each test file through the sqlite3 '
                        'command, and a test fails by raising an error')):
            made = Project(language)
            try:
                assert line in made.run('--gate', 'passed'), language
            finally:
                made.close()
        made = Project('pytest')
        try:
            assert 'to write its report' not in made.run('--gate', 'passed')
        finally:
            made.close()


class TestTheTwoQuestions:

    # purlin: scaffold PROOF-6
    def test_an_empty_tree_is_asked_for_its_command(self):
        made = Project(None)
        try:
            output = made.run('--gate', 'passed')
            assert scaffold_module.COMMAND_QUESTION in output
            assert scaffold_module.NO_COMMAND in output
            assert made.config()['tests'] == []
        finally:
            made.close()

    # purlin: scaffold PROOF-6
    def test_the_command_and_the_report_are_the_suite_written(self):
        made = Project(None)
        try:
            out = _answering(made, 'make test\nbuild/report.xml\n\n',
                             '--gate', 'passed')
            assert (out.index(scaffold_module.COMMAND_QUESTION)
                    < out.index(scaffold_module.REPORT_QUESTION)), out
            assert made.config()['tests'] == [{
                'name': 'tests', 'run': 'make test',
                'report': 'build/report.xml', 'format': 'junit',
                'files': scaffold_module.ASKED_FILES}]
        finally:
            made.close()

    @pytest.mark.parametrize('command,report,fmt', [
        ('dotnet test', 'out/results.trx', 'trx'),
        ('go test -json ./...', '-', 'gotest')])
    # purlin: scaffold PROOF-6
    def test_a_trx_report_and_a_dash_name_their_formats(self, command,
                                                        report, fmt):
        made = Project(None)
        try:
            _answering(made, '%s\n%s\n\n' % (command, report),
                       '--gate', 'passed')
            assert made.config()['tests'] == [{
                'name': 'tests', 'run': command, 'report': report,
                'format': fmt,
                'files': ['**/test_*', '**/*_test.*', '**/*.test.*',
                          '**/*.spec.*']}]
        finally:
            made.close()

    # purlin: scaffold PROOF-6
    def test_no_report_makes_each_test_file_pass_by_its_exit_code(self):
        made = Project(None)
        try:
            _answering(made, './run-one.sh\n\n\n', '--gate', 'passed')
            (suite,) = made.config()['tests']
            assert suite['format'] == 'exit'
            assert suite['run'] == './run-one.sh {files}'
            assert suite['report'] is None
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Nobody is named
# ---------------------------------------------------------------------------

class TestNobodyIsNamed:

    # purlin: scaffold PROOF-10
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
                else:
                    assert 'Each signer runs this once' not in done.stdout
                    assert 'git config gpg.format ssh' not in done.stdout
                    assert 'git config commit.gpgsign' not in done.stdout
            finally:
                made.close()

    # purlin: scaffold PROOF-12
    def test_raising_the_gate_writes_the_setting_and_no_workflow(self,
                                                                 project):
        """A runner is decided by trust and the `@env` tags, not the gate."""
        project.run('--gate', 'passed')
        assert not project.has('.github/workflows/purlin.yml')
        project.run('--gate', 'strong')
        assert not project.has('.github/workflows/purlin.yml')
        assert project.config()['gate'] == 'strong'

    # purlin: scaffold PROOF-12
    def test_raising_to_signed_keeps_the_workflow_trust_asked_for(self,
                                                                  project):
        write(project.path('.purlin/config.json'),
              json.dumps({'trust': 'remote'}) + '\n')
        project.run('--gate', 'strong')
        before = read(project.path('.github/workflows/purlin.yml'))
        files = tree(project.root)
        output = project.run('--gate', 'signed')
        assert read(project.path('.github/workflows/purlin.yml')) == before
        assert summary_paths(output)['.github/workflows/purlin.yml'] == 'kept'
        # Every file the earlier run wrote is there, and only the settings
        # file differs.
        after = tree(project.root)
        assert [rel for rel in files if rel not in after] == []
        assert [rel for rel in files if after[rel] != files[rel]] == [
            '.purlin/config.json']
        assert project.config()['gate'] == 'signed'

    # purlin: scaffold PROOF-12
    def test_lowering_writes_the_setting_and_deletes_nothing(self, project):
        write(project.path('.purlin/config.json'),
              json.dumps({'trust': 'remote'}) + '\n')
        project.run('--gate', 'signed')
        files = tree(project.root)
        project.run('--gate', 'passed')
        assert project.config()['gate'] == 'passed'
        assert project.config()['min_strength'] is None
        assert project.has('.github/workflows/purlin.yml')
        after = tree(project.root)
        assert [rel for rel in files if rel not in after] == []
        assert [rel for rel in files if after[rel] != files[rel]] == [
            '.purlin/config.json']

    # purlin: scaffold PROOF-20
    def test_a_second_run_at_the_same_gate_changes_nothing(self, project):
        project.run('--gate', 'strong')
        files = tree(project.root)
        output = project.run('--gate', 'strong')
        assert 'wrote' not in summary_paths(output).values()
        # Not a byte of the project changed, whatever the summary says.
        assert tree(project.root) == files

    # purlin: scaffold PROOF-3
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

    # purlin: scaffold PROOF-49
    def test_at_passed_the_trust_lines_name_tests_and_no_signing(self):
        made = Project('pytest')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root],
                input='passed\n\n\n', capture_output=True,
                encoding='utf-8', timeout=300)
            assert done.returncode == 0, done.stdout + done.stderr
            out = done.stdout
            assert scaffold_module.TRUST_QUESTION_AT_PASSED in out, out
            assert scaffold_module.TRUST_QUESTION not in out, out
            lines = out.splitlines()
            assert 'Trust local: your own runs count.' in lines, out
            reason = ('every test runs on this operating system and you '
                      'trust this machine, so nothing has to run remotely')
            assert 'No remote runner: %s.' % reason in lines, out
            assert 'skipped the runner file (%s)' % reason in lines, out
            after = out[out.index(scaffold_module.TRUST_QUESTION_AT_PASSED):]
            assert 'proof' not in after.lower(), after
            assert 'sign' not in after.lower(), after
        finally:
            made.close()

    # purlin: scaffold PROOF-13
    def test_a_trusted_project_with_no_foreign_proof_gets_no_workflow(
            self, project):
        output = project.run('--gate', 'strong')
        assert not project.has('.github/workflows/purlin.yml')
        assert scaffold_module.workflow_module.NO_REASON in output, output

    # purlin: scaffold PROOF-13
    def test_a_proof_this_machine_cannot_prove_writes_one(self, project):
        named = self._foreign_env(project)
        output = project.run('--gate', 'passed')
        assert project.has('.github/workflows/purlin.yml'), output
        assert scaffold_module.REMOTE_INTRO in output
        # At `passed` the reason names the test and no proof.
        assert ('  A test is tagged @env for %s, which this machine is not, '
                'so only a runner can run it.' % named
                in output.splitlines()), output
        output = project.run('--gate', 'strong')
        assert ('  A proof in specs/ is tagged @env for %s, which this '
                'machine is not, so only a runner can prove it.' % named
                in output.splitlines()), output

    # purlin: scaffold PROOF-13
    def test_answering_no_to_trust_writes_one(self, project):
        self._trust_remote(project)
        output = project.run('--gate', 'strong')
        assert project.has('.github/workflows/purlin.yml'), output
        assert project.config()['trust'] == 'remote'
        assert ('  You chose not to trust this machine for signing, so the '
                'tests a signature rests on run on a clean one.'
                in output.splitlines()), output

    # purlin: scaffold PROOF-51
    @pytest.mark.parametrize('foreign', (False, True))
    def test_the_heading_is_true_for_any_count_of_reasons(self, project,
                                                          foreign):
        self._trust_remote(project)
        named = self._foreign_env(project) if foreign else None
        output = project.run('--gate', 'strong')
        lines = output.splitlines()
        start = lines.index('A remote runner is written because:')
        reasons = []
        for line in lines[start + 1:]:
            if not line.startswith('  '):
                break
            reasons.append(line)
        signing = ('  You chose not to trust this machine for signing, so '
                   'the tests a signature rests on run on a clean one.')
        if foreign:
            assert len(reasons) == 2, reasons
            assert named in reasons[0], reasons
            assert reasons[1] == signing, reasons
        else:
            assert reasons == [signing], reasons
        assert 'two reasons' not in output, output

    # purlin: scaffold PROOF-50
    @pytest.mark.parametrize('gate', ('passed', 'strong'))
    def test_the_trust_reason_names_the_tests_at_passed(self, project, gate):
        self._trust_remote(project)
        output = project.run('--gate', gate)
        assert project.has('.github/workflows/purlin.yml'), output
        at_passed = ('  You chose not to trust this machine for the tests, '
                     'so they run on a clean one.')
        signing = ('  You chose not to trust this machine for signing, so '
                   'the tests a signature rests on run on a clean one.')
        lines = output.splitlines()
        answer_at_passed = ('Trust remote: purlin:test --remote runs your '
                            'tests on the remote runner, and your own runs '
                            'count too.')
        if gate == 'passed':
            assert at_passed in lines, output
            assert signing not in lines, output
            assert answer_at_passed in lines, output
            assert not any(line.startswith('Trust remote: purlin:sign')
                           for line in lines), output
            start = next(i for i, line in enumerate(lines)
                         if line.startswith('A remote runner is written'))
            reasons = []
            for line in lines[start + 1:]:
                if not line.startswith('  '):
                    break
                reasons.append(line)
            assert reasons == [at_passed], reasons
            assert not any('sign' in line for line in reasons), reasons
        else:
            assert signing in lines, output
            assert at_passed not in lines, output
            assert scaffold_module.TRUST_REMOTE in lines, output
            assert answer_at_passed not in lines, output

    # purlin: scaffold PROOF-13
    def test_with_no_remote_nothing_is_written(self):
        made = Project('pytest', host=None)
        try:
            self._trust_remote(made)
            output = made.run('--gate', 'strong')
            assert not made.has('.github/workflows/purlin.yml')
            assert 'there is no git remote' in output
        finally:
            made.close()

    # purlin: scaffold PROOF-44
    def test_a_missing_prerequisite_is_named_and_nothing_is_written(self):
        made = Project('pytest', remote='https://example.invalid/x.git')
        try:
            self._trust_remote(made)
            output = made.run('--gate', 'strong')
            assert 'neither GitHub nor Azure DevOps' in output, output
            assert not made.has('.github/workflows/purlin.yml')
            assert ('The origin remote is neither GitHub nor Azure DevOps, '
                    'and those are the two hosts this release writes a '
                    'workflow for.' in output.splitlines()), output
            assert ('skipped the CI workflow (a prerequisite is missing)'
                    in output.splitlines()), output
        finally:
            made.close()

    # purlin: scaffold PROOF-44
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

    # purlin: scaffold PROOF-44
    def test_the_host_cli_is_reported_either_way(self, project):
        self._trust_remote(project)
        output = project.run('--gate', 'strong')
        assert ('gh is installed' in output
                or 'gh is not installed' in output), output
        assert project.has('.github/workflows/purlin.yml'), output

    @pytest.mark.parametrize('gh', (True, False))
    # purlin: scaffold PROOF-44
    def test_gh_present_or_absent_is_named_and_the_workflow_written(
            self, project, gh):
        """A PATH holding git, and `gh` or not, decides which line prints."""
        if os.name == 'nt':
            pytest.skip('a PATH of one linked git is built on POSIX only')
        self._trust_remote(project)
        bin_dir = os.path.realpath(tempfile.mkdtemp(prefix='purlin-bin-'))
        try:
            os.symlink(shutil.which('git'), os.path.join(bin_dir, 'git'))
            if gh:
                write(os.path.join(bin_dir, 'gh'), '#!/bin/sh\n')
            output = project.run('--gate', 'strong', env={'PATH': bin_dir})
            lines = output.splitlines()
            present = 'gh is installed, so a remote run can be watched from here.'
            absent = ('gh is not installed, so purlin:test --remote cannot '
                      'watch a run. Install it, or open the run on the git '
                      'host instead.')
            assert (present in lines) is gh, output
            assert (absent in lines) is not gh, output
            assert project.has('.github/workflows/purlin.yml'), output
        finally:
            shutil.rmtree(bin_dir, ignore_errors=True)

    # purlin: scaffold PROOF-14
    def test_the_host_is_read_from_the_remote(self):
        made = Project('pytest', remote='https://github.com/acme/demo.git')
        try:
            self._trust_remote(made)
            made.run('--gate', 'strong')
            assert made.config()['ci'] == 'github'
            assert made.has('.github/workflows/purlin.yml')
        finally:
            made.close()

    # purlin: scaffold PROOF-14
    def test_an_azure_remote_gets_the_pipeline(self):
        made = Project('pytest',
                       remote='https://dev.azure.com/acme/demo/_git/demo')
        try:
            self._trust_remote(made)
            output = made.run('--gate', 'strong')
            assert made.config()['ci'] == 'azure'
            assert made.has('purlin.azure-pipelines.yml'), output
            assert ('Gate strong. Suites pytest. Git host azure.'
                    in output.splitlines()), output
            assert 'wrote purlin.azure-pipelines.yml' in output.splitlines()
            assert not made.has('.github/workflows/purlin.yml'), output
        finally:
            made.close()

    # purlin: scaffold PROOF-15
    def test_the_matrix_is_rendered_from_the_env_tags(self, project):
        named = self._foreign_env(project)
        output = project.run('--gate', 'strong')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert '%s-latest' % ('ubuntu' if named == 'linux' else named) \
            in workflow
        assert 'ubuntu-latest' in workflow
        assert 'ubuntu-latest' in output

    # purlin: scaffold PROOF-15
    def test_windows_and_macos_tags_each_add_their_runner(self, project):
        """The same on every machine: trust `remote` writes the workflow."""
        self._trust_remote(project)
        write(project.path('specs/core/login.md'), SPEC.replace(
            'returns a session\n',
            'returns a session @env(windows)\n'
            '- PROOF-2 (RULE-1): Sign in on a Mac @env(macos)\n'))
        output = project.run('--gate', 'strong')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert ('        os: [ubuntu-latest, macos-latest, windows-latest]\n'
                in workflow), workflow
        assert ('  the matrix is ubuntu-latest, macos-latest, windows-latest: '
                'ubuntu-latest always, then the @env tags in specs/.'
                in output.splitlines()), output

    # purlin: scaffold PROOF-15
    def test_no_env_tag_means_one_linux_job(self, project):
        self._trust_remote(project)
        project.spec()
        project.run('--gate', 'strong')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert 'ubuntu-latest' in workflow
        assert 'windows-latest' not in workflow

    # purlin: scaffold PROOF-15
    def test_the_purlin_release_is_pinned(self, project):
        self._trust_remote(project)
        project.run('--gate', 'strong')
        version = read(os.path.join(ROOT, 'VERSION')).strip()
        assert 'v%s' % version in read(
            project.path('.github/workflows/purlin.yml'))

    # purlin: scaffold PROOF-42
    def test_the_triggers_are_a_run_branch_and_the_signing_tag(self, project):
        self._trust_remote(project)
        project.run('--gate', 'strong')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        block = workflow.split('\non:\n', 1)[1].split('\npermissions:', 1)[0]
        assert block == ("  push:\n    branches: ['run/**']\n"
                         "    tags: ['signed/**']\n")

    # purlin: scaffold PROOF-42
    def test_the_last_step_checks_the_gate_and_verifies(self, project):
        self._trust_remote(project)
        project.run('--gate', 'strong')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert 'name: Check the gate' in workflow
        assert 'scripts/ci/gate_check.py" --check --verify' in workflow
        assert 'actions/upload-artifact@v4' not in workflow
        assert workflow.rstrip().endswith('--check --verify')

    # purlin: scaffold PROOF-42
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
            # It is the last step: no step follows it.
            tail = pipeline.split('gate_check.py" --check --verify', 1)[1]
            assert not [line for line in tail.splitlines()
                        if line.lstrip().startswith('- ')], tail
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Everything else init writes
# ---------------------------------------------------------------------------

class TestWhatInitWrites:

    # purlin: scaffold PROOF-18
    def test_the_summary_names_every_write(self, project):
        before = tree(project.root)
        output = project.run('--gate', 'strong')
        named = summary_paths(output)
        for rel in ('.purlin/config.json', '.gitignore',
                    '.purlin/evidence/README.md', 'purlin-report.html'):
            assert rel in named, output
            assert project.has(rel), rel
        # Every path it says it wrote or copied is on disk, every path that
        # appeared is one it names, and none is a folder for design files.
        written = sorted(rel for rel, word in named.items()
                         if word in ('wrote', 'copied'))
        assert [rel for rel in written if not project.has(rel)] == [], output
        assert sorted(set(tree(project.root)) - set(before)) == written
        assert not [rel for rel in written
                    if 'design' in rel.lower().split('/')[-1]], written

    # purlin: scaffold PROOF-19
    def test_the_gitignore_block_is_added_once(self, project):
        write(project.path('.gitignore'), 'node_modules/\n')
        project.run('--gate', 'passed')
        first = read(project.path('.gitignore'))
        project.run('--gate', 'passed')
        assert read(project.path('.gitignore')) == first
        assert first.startswith('node_modules/\n')
        assert '.purlin/runtime/' in first
        assert first.count('.purlin/report-data.js') == 1

    # purlin: scaffold PROOF-19
    def test_the_engine_block_names_the_source_and_the_tests(self, project):
        write(project.path('pyproject.toml'), '[project]\nname = "demo"\n')
        os.makedirs(project.path('src'), exist_ok=True)
        write(project.path('src/app.py'), 'def go():\n    return 1\n')
        project.run('--gate', 'passed', '--mutation')
        text = read(project.path('pyproject.toml'))
        assert '[tool.mutmut]' in text
        assert 'source_paths = ["src"]' in text
        assert 'pytest_add_cli_args_test_selection = ["tests"]' in text
        assert text.startswith('[project]\nname = "demo"\n')

    # purlin: scaffold PROOF-19
    def test_without_a_pyproject_the_block_lands_in_setup_cfg(self, project):
        project.run('--gate', 'passed', '--mutation')
        assert '[mutmut]' in read(project.path('setup.cfg'))

    # purlin: scaffold PROOF-40
    def test_the_mutmut_copy_is_ignored_once(self, project):
        write(project.path('greeting.py'), 'def greet(name):\n    return name\n')
        write(project.path('tests/test_greeting.py'), 'def test_greet():\n    pass\n')
        project.run('--gate', 'passed', '--mutation')
        project.run('--gate', 'passed')
        lines = read(project.path('.gitignore')).splitlines()
        assert lines.count('mutants/') == 1

    # purlin: scaffold PROOF-19
    def test_the_engine_block_is_added_once(self, project):
        project.run('--gate', 'passed', '--mutation')
        project.run('--gate', 'passed')
        assert read(project.path('setup.cfg')).count('[mutmut]') == 1

    # purlin: scaffold PROOF-9
    def test_a_node_project_is_told_about_stryker(self):
        made = Project('vitest')
        try:
            assert 'Stryker' in made.run('--gate', 'passed', '--mutation')
        finally:
            made.close()

    # purlin: scaffold PROOF-18
    def test_the_dashboard_is_copied(self, project):
        project.run('--gate', 'passed')
        source = os.path.join(ROOT, 'scripts', 'report', 'purlin-report.html')
        assert read(project.path('purlin-report.html')) == read(source)

    # purlin: scaffold PROOF-34
    def test_the_next_step_is_the_last_line(self, project):
        lines = project.run('--gate', 'passed').strip().splitlines()
        assert lines[-1].startswith('→')
        assert 'purlin:spec' in lines[-1]

    # purlin: scaffold PROOF-34
    def test_the_next_step_reads_the_state_once_specs_exist(self, project):
        project.spec()
        lines = project.run('--gate', 'passed').strip().splitlines()
        assert lines[-1].startswith('→')

    # purlin: scaffold PROOF-35
    def test_no_emoji_in_the_output(self, project):
        output = project.run('--gate', 'signed')
        assert all(ord(ch) < 0x1F000 for ch in output)


class TestNoHookIsInstalled:
    """Nothing runs at commit time and nothing runs at push time."""

    # purlin: scaffold PROOF-24
    def test_no_git_hook_is_written_at_all(self, project):
        hooks = project.path('.git/hooks')
        before = sorted(os.listdir(hooks)) if os.path.isdir(hooks) else []
        project.run('--gate', 'passed')
        after = sorted(os.listdir(hooks)) if os.path.isdir(hooks) else []
        assert after == before
        assert 'pre-push' not in after and 'pre-commit' not in after

    # purlin: scaffold PROOF-24
    def test_a_hook_someone_else_wrote_is_left_alone(self, project):
        write(project.path('.git/hooks/pre-push'), '#!/bin/sh\necho mine\n')
        project.run('--gate', 'passed')
        assert read(project.path('.git/hooks/pre-push')) == \
            '#!/bin/sh\necho mine\n'


# ---------------------------------------------------------------------------
# The flags
# ---------------------------------------------------------------------------

class TestTheFlags:

    # purlin: scaffold PROOF-32
    def test_add_keeps_what_was_detected(self, project):
        project.run('--gate', 'passed')
        project.run('--add', 'vitest')
        assert [suite['name'] for suite in project.config()['tests']] == [
            'pytest', 'vitest']

    # purlin: scaffold PROOF-32
    def test_add_twice_names_the_framework_once(self, project):
        project.run('--gate', 'passed')
        project.run('--add', 'vitest')
        project.run('--add', 'vitest')
        assert [suite['name'] for suite in project.config()['tests']] == [
            'pytest', 'vitest']

    # purlin: scaffold PROOF-48
    def test_a_tests_setting_the_project_carries_is_kept(self, project):
        project.run('--gate', 'passed')
        written = project.config()
        ours = [{'name': 'unit', 'run': 'make test REPORT={report}',
                 'report': 'out/unit.xml', 'format': 'junit',
                 'files': ['spec/**/*_spec.py']}]
        written['tests'] = ours
        write(project.path('.purlin/config.json'),
              json.dumps(written, indent=2))
        project.run('--gate', 'strong')
        assert project.config()['tests'] == ours

    # purlin: scaffold PROOF-30
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

    # purlin: scaffold PROOF-30
    def test_dry_run_outside_a_repository_still_prints_the_plan(self):
        directory = tempfile.mkdtemp(prefix='purlin-nogit-')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', directory,
                 '--gate', 'strong', '--yes', '--dry-run'],
                capture_output=True, encoding='utf-8', timeout=300,
                stdin=subprocess.DEVNULL)
            assert done.returncode == 0, done.stdout + done.stderr
            assert scaffold_module.COMMAND_QUESTION in done.stdout
            assert '.purlin/config.json' in summary_paths(done.stdout)
            assert done.stdout.strip().splitlines()[-1].startswith('→')
            assert os.listdir(directory) == []
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    # purlin: scaffold PROOF-31
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

    # purlin: scaffold PROOF-31
    def test_a_missing_project_root_is_a_bad_invocation(self):
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', '/no/such/dir',
             '--gate', 'passed', '--yes'], capture_output=True, encoding='utf-8',
            timeout=300)
        assert done.returncode == 2
        # The error names the missing root, and nothing is made there.
        parent = os.path.realpath(tempfile.mkdtemp(prefix='purlin-noroot-'))
        missing = os.path.join(parent, 'no', 'such', 'dir')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', missing,
                 '--gate', 'passed', '--yes'], capture_output=True,
                encoding='utf-8', timeout=300, stdin=subprocess.DEVNULL)
            assert done.returncode == 2
            assert done.stderr == 'no such project root: %s\n' % missing
            assert done.stdout == ''
            assert os.listdir(parent) == []
        finally:
            shutil.rmtree(parent, ignore_errors=True)

    # purlin: scaffold PROOF-33
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
            assert ('Nothing is pending: this project is at %s.'
                    % read(os.path.join(ROOT, 'VERSION')).strip()
                    in done.stdout.splitlines()), done.stdout
        else:
            assert done.returncode == 1
            assert 'scripts/init/update.py' in done.stdout

    # purlin: scaffold PROOF-33
    def test_update_with_dry_run_asks_the_upgrade_what_is_pending(self,
                                                                  project):
        project.run('--gate', 'passed')
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', project.root,
             '--update', '--dry-run'], capture_output=True, encoding='utf-8',
            timeout=300, stdin=subprocess.DEVNULL)
        # A project this release just set up has nothing pending.
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'does not carry' not in done.stdout
        assert ('Nothing is pending: this project is at %s.'
                % read(os.path.join(ROOT, 'VERSION')).strip()
                in done.stdout.splitlines()), done.stdout

    # purlin: scaffold PROOF-33
    def test_update_with_dry_run_lists_what_an_older_project_needs(self):
        """A project 0.9.5 set up has migrations pending, and none is applied."""
        made = Project(None, host=None)
        try:
            fixture = os.path.join(DEV, 'fixtures', 'upgrade-0.9.5')
            shutil.copytree(fixture, made.root, dirs_exist_ok=True)
            os.rename(made.path('_gitignore'), made.path('.gitignore'))
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'as 0.9.5 left it')
            files = tree(made.root)
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root,
                 '--update', '--dry-run'], capture_output=True,
                encoding='utf-8', timeout=300, stdin=subprocess.DEVNULL)
            assert done.returncode == 1, done.stdout + done.stderr
            lines = done.stdout.splitlines()
            assert re.match(r'\d+ migrations pending in %s:$'
                            % re.escape(made.root), lines[0]), lines
            assert ('  config: write .purlin/config.json at this shape and '
                    'set the gate' in lines), lines
            assert lines[-1] == '→ Run: purlin:init --update', lines
            assert 'Nothing is pending' not in done.stdout
            assert tree(made.root) == files
            assert git(made.root, 'status', '--porcelain').stdout == ''
        finally:
            made.close()


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

    # purlin: scaffold PROOF-22
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
            assert [suite['name'] for suite in made.config()['tests']] == [
                'pytest']
            assert made.has('.github/workflows/purlin.yml'), output
            assert '.purlin/config.json' in summary_paths(output)
            # The same project set up from this checkout ends the same, file
            # for file and line for line.
            here = Project('pytest')
            try:
                write(here.path('.purlin/config.json'),
                      json.dumps({'trust': 'remote'}) + '\n')
                ours = here.run('--gate', 'strong', subprocess=True)
                assert tree(made.root) == tree(here.root)
                assert (output.replace(made.root, '<root>')
                        == ours.replace(here.root, '<root>'))
            finally:
                here.close()
        finally:
            made.close()
            shutil.rmtree(cache, ignore_errors=True)

    # purlin: scaffold PROOF-21
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

    # purlin: scaffold PROOF-23
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
                    # Nor a relative path into it, such as `dev/test_x.py`.
                    assert not re.search(r'(?<![\w./-])dev/', text), path
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The pieces, read directly
# ---------------------------------------------------------------------------

def _mutmut_block(project):
    """The `setup.cfg` init writes for the project with mutation testing on."""
    output = project.run('--gate', 'passed', '--mutation')
    assert summary_paths(output)['setup.cfg'] == 'wrote', output
    return read(project.path('setup.cfg'))


class TestThePieces:

    @pytest.mark.parametrize('url,host', [
        ('https://github.com/acme/demo.git', 'github'),
        ('git@github.com:acme/demo.git', 'github'),
        ('https://dev.azure.com/acme/demo/_git/demo', 'azure'),
        ('https://acme.visualstudio.com/demo/_git/demo', 'azure'),
        ('https://git.example.com/acme/demo.git', None),
    ])
    # purlin: scaffold PROOF-14
    def test_the_host_is_read_from_the_url(self, url, host):
        made = Project('pytest', remote=url)
        try:
            assert scaffold_module.git_host(made.root) == host
            # What init itself prints and writes for the same remote. With
            # no host read, `ci` keeps the template's `github`.
            output = made.run('--gate', 'strong')
            assert ('Gate strong. Suites pytest. Git host %s.'
                    % (host or 'not read from a remote')
                    in output.splitlines()), output
            assert made.config()['ci'] == (host or 'github')
        finally:
            made.close()

    # purlin: scaffold PROOF-14
    def test_no_remote_reads_no_host(self):
        made = Project('pytest', host=None)
        try:
            assert scaffold_module.git_host(made.root) is None
            assert scaffold_module.git_remote(made.root) is False
            output = made.run('--gate', 'strong')
            assert ('Gate strong. Suites pytest. Git host not read from a '
                    'remote.' in output.splitlines()), output
            assert made.config()['ci'] == 'github'
        finally:
            made.close()

    # purlin: scaffold PROOF-19
    def test_the_source_paths_prefer_src(self, project):
        os.makedirs(project.path('src'), exist_ok=True)
        os.makedirs(project.path('tests'), exist_ok=True)
        assert scaffold_module.mutmut_paths(project.root) == (['src'],
                                                              ['tests'])

    # purlin: scaffold PROOF-19
    def test_a_package_directory_is_found_when_there_is_no_src(self, project):
        os.makedirs(project.path('demo'), exist_ok=True)
        write(project.path('demo/__init__.py'), '')
        sources, tests = scaffold_module.mutmut_paths(project.root)
        assert sources == ['demo']
        assert tests == ['tests']

    # purlin: scaffold PROOF-39
    def test_nested_code_is_source_and_a_test_directory_is_the_selection(
            self, project):
        shutil.rmtree(project.path('tests'), ignore_errors=True)
        write(project.path('scripts/run/job.py'), 'def go():\n    return 1\n')
        write(project.path('dev/test_job.py'), 'def test_go():\n    pass\n')
        write(project.path('dev/build.py'), '')
        write(project.path('docs/guide.md'), '# Guide\n')
        assert scaffold_module.mutmut_paths(project.root) == (['scripts'],
                                                              ['dev'])
        assert _mutmut_block(project) == ('[mutmut]\nsource_paths =\n'
                                          '    scripts\n'
                                          'pytest_add_cli_args_test_selection'
                                          ' =\n    dev\n')

    # purlin: scaffold PROOF-39
    def test_src_and_tests_still_win_over_other_directories(self, project):
        write(project.path('src/app.py'), '')
        write(project.path('tools/helper.py'), '')
        write(project.path('tests/test_app.py'), '')
        write(project.path('dev/test_extra.py'), '')
        assert scaffold_module.mutmut_paths(project.root) == (['src'],
                                                              ['tests'])
        assert _mutmut_block(project) == ('[mutmut]\nsource_paths =\n'
                                          '    src\n'
                                          'pytest_add_cli_args_test_selection'
                                          ' =\n    tests\n')

    # purlin: scaffold PROOF-39
    def test_modules_at_the_root_are_named_one_by_one(self, project):
        write(project.path('greeting.py'), 'def greet(name):\n    return name\n')
        write(project.path('conftest.py'), '')
        write(project.path('test_greeting.py'), 'def test_greet():\n    pass\n')
        sources, _tests = scaffold_module.mutmut_paths(project.root)
        assert sources == ['greeting.py']
        assert _mutmut_block(project) == ('[mutmut]\nsource_paths =\n'
                                          '    greeting.py\n'
                                          'pytest_add_cli_args_test_selection'
                                          ' =\n    tests\n')

    # purlin: scaffold PROOF-39
    def test_no_python_anywhere_falls_back_to_the_root(self, project):
        write(project.path('docs/guide.md'), '# Guide\n')
        sources, _tests = scaffold_module.mutmut_paths(project.root)
        assert sources == ['.']
        assert _mutmut_block(project) == ('[mutmut]\nsource_paths =\n'
                                          '    .\n'
                                          'pytest_add_cli_args_test_selection'
                                          ' =\n    tests\n')


# ---------------------------------------------------------------------------
# A Go module through the command init writes
# ---------------------------------------------------------------------------

# purlin: scaffold PROOF-52
def test_a_go_module_runs_through_the_command_init_writes(tmp_path):
    """Go itself, not a sample of what it prints: init sets the module up,
    the module's own command runs, and each marker reads what Go said."""
    if not shutil.which('go'):
        pytest.skip('go is not on this machine')
    root = _fixture(tmp_path, 'go')
    (root / 'report.json').unlink()
    module = {str(p.relative_to(root)): p.read_bytes()
              for p in root.rglob('*') if p.is_file()}
    for command in (['init', '-q'], ['config', 'user.email', 'dev@example.com'],
                    ['config', 'user.name', 'Dev']):
        subprocess.run(['git'] + command, cwd=str(root), check=True)
    init = subprocess.run(
        [sys.executable, os.path.join(REPO, 'scripts', 'init', 'scaffold.py'),
         '--project-root', str(root), '--gate', 'passed', '--yes'],
        capture_output=True, encoding='utf-8', stdin=subprocess.DEVNULL)
    assert init.returncode == 0, init.stdout + init.stderr
    assert not [line for line in init.stdout.splitlines() if 'needs' in line], (
        init.stdout)
    config = json.loads((root / '.purlin' / 'config.json').read_text(
        encoding='utf-8'))
    assert config['tests'] == [{'name': 'go', 'run': 'go test -json ./...',
                                'report': '-', 'format': 'gotest',
                                'files': ['**/*_test.go']}], config
    for name, text in GO_SPECS.items():
        _write(root, 'specs/shop/%s.md' % name, text)
    subprocess.run(['git', 'add', '-A'], cwd=str(root), check=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'the module'], cwd=str(root),
                   check=True)

    code, out = _run(root, '--all', '--test')
    assert 'Markers: 7 tied to a test, 0 not tied.' in out, out
    seen = {}
    for feature in ('cart', 'tax'):
        for entry in _evidence(root, feature)['proofs']:
            seen[(feature, entry['id'])] = (entry['result'], entry['test'])
    assert seen == {
        ('cart', 'PROOF-1'): ('pass', 'cart/cart_test.go::TestTotal'),
        ('cart', 'PROOF-2'): ('fail', 'cart/cart_test.go::TestParse'),
        ('cart', 'PROOF-3'): ('missing', 'cart/cart_test.go::TestDiscount'),
        ('cart', 'PROOF-4'): ('fail', 'cart/cart_test.go::TestTotalIsWrong'),
        ('tax', 'PROOF-1'): ('pass', 'tax/tax_test.go::TestRate'),
        ('tax', 'PROOF-2'): ('fail', 'tax/tax_test.go::TestLookupPanics'),
        ('tax', 'PROOF-3'): ('missing', 'tax/tax_test.go::TestAfterThePanic'),
    }, seen
    assert code == 1, out
    # Nothing of Purlin was added to the module: every file it held reads as
    # it did, and every Go file there is one of them.
    assert {rel: (root / rel).read_bytes() for rel in module} == module
    assert sorted(str(p.relative_to(root)) for p in root.rglob('*.go')
                  ) == sorted(rel for rel in module if rel.endswith('.go'))
    assert not (root / 'go.sum').exists()
