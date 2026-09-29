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

# The seven settings a new project gets, and the only ones.
CONFIG_KEYS = sorted(['version', 'gate', 'mutation_engine', 'min_strength',
                      'audit_parallel', 'tests', 'ci'])

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


def foreign_system():
    """Windows, or macOS on a Windows machine: a system this machine is not."""
    here = scaffold_module.evidence_module.host_os()
    return 'windows' if here != 'windows' else 'macos'


def tag_foreign(made, *systems):
    """A spec whose proofs are tagged `@env` for `systems`, one proof each."""
    systems = systems or (foreign_system(),)
    lines = ['- PROOF-%d (RULE-1): Sign in on this system @env(%s)'
             % (index, name) for index, name in enumerate(systems, 1)]
    write(made.path('specs/core/login.md'),
          SPEC.split('## Proof\n')[0] + '## Proof\n\n' + '\n'.join(lines)
          + '\n')
    return systems[0]


def reasons_under_heading(output):
    """The indented lines under `A remote runner is written because:`."""
    lines = output.splitlines()
    start = lines.index(scaffold_module.REMOTE_INTRO)
    reasons = []
    for line in lines[start + 1:]:
        if not line.startswith('  '):
            break
        reasons.append(line)
    return reasons


def changed_since(before, after):
    """The paths of `before` that `after` lacks or holds other bytes for."""
    return sorted(rel for rel in before
                  if rel not in after or after[rel] != before[rel])


# The dashboard's data file, which the status the run ends on refreshes
# wherever a spec exists.
REPORT_DATA = '.purlin/report-data.js'


# ---------------------------------------------------------------------------
# The questions
# ---------------------------------------------------------------------------

class TestTheQuestions:

    # purlin: scaffold PROOF-1
    def test_at_strong_a_project_with_code_is_asked_two_questions(self):
        made = Project('pytest')
        try:
            out = _answering(made, 'strong\n')
            mutation = scaffold_module.MUTATION_QUESTION % 'mutmut'
            assert asked(out) == [scaffold_module.GATE_QUESTION, mutation], out
            assert made.config()['gate'] == 'strong'
            assert made.config()['mutation_engine'] == 'none'
        finally:
            made.close()

    # purlin: scaffold PROOF-53
    def test_at_passed_a_project_with_code_is_asked_the_gate_alone(self):
        made = Project('pytest')
        try:
            out = _answering(made, 'passed\n')
            assert asked(out) == [scaffold_module.GATE_QUESTION], out
            assert made.config()['gate'] == 'passed'
            assert made.config()['mutation_engine'] == 'none'
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

    # purlin: scaffold PROOF-3
    def test_the_gate_is_remembered_when_no_flag_names_one(self, project):
        project.run('--gate', 'strong')
        output = project.run()
        assert scaffold_module.GATE_QUESTION not in output
        assert project.config()['gate'] == 'strong'

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


# ---------------------------------------------------------------------------
# The settings file
# ---------------------------------------------------------------------------

class TestTheSettings:

    # purlin: scaffold PROOF-5
    def test_the_config_holds_the_seven_keys(self, project):
        output = project.run('--gate', 'strong')
        config = project.config()
        assert sorted(config) == CONFIG_KEYS
        assert config['version'] == read(os.path.join(ROOT, 'VERSION')).strip()
        assert config['audit_parallel'] == 4
        assert 'audit_parallel' not in output
        assert 'at a time' not in output

    # purlin: scaffold PROOF-54
    def test_the_template_carries_the_same_seven_keys(self):
        template = json.loads(read(TEMPLATE_CONFIG))
        assert sorted(template) == CONFIG_KEYS
        assert template['version'] == read(
            os.path.join(ROOT, 'VERSION')).strip()
        assert template['tests'] == []
        assert template['ci'] == 'none'

    # purlin: scaffold PROOF-55
    def test_audit_parallel_keeps_a_value_in_range(self, project):
        project.run('--gate', 'passed')
        config = project.config()
        config['audit_parallel'] = 9
        write(project.path('.purlin/config.json'), json.dumps(config))
        project.run()
        assert project.config()['audit_parallel'] == 9

    # purlin: scaffold PROOF-56
    def test_audit_parallel_out_of_range_is_put_back_to_4(self, project):
        project.run('--gate', 'passed')
        config = project.config()
        config['audit_parallel'] = 40
        write(project.path('.purlin/config.json'), json.dumps(config))
        project.run()
        assert project.config()['audit_parallel'] == 4

    # purlin: scaffold PROOF-57
    def test_a_child_run_and_an_in_process_run_agree(self):
        """The command line and `main()` write the same config and output."""
        child, inline = Project(), Project()
        try:
            child_out = child.run('--gate', 'strong', subprocess=True)
            inline_out = inline.run('--gate', 'strong')
            assert sorted(child.config()) == CONFIG_KEYS
            assert child.config() == inline.config()
            assert (child_out.replace(child.root, '<root>')
                    == inline_out.replace(inline.root, '<root>'))
        finally:
            child.close()
            inline.close()

    # purlin: scaffold PROOF-58
    def test_a_key_outside_the_seven_is_not_written_back(self, project):
        project.run('--gate', 'passed')
        config = project.config()
        config['colour'] = 'blue'
        write(project.path('.purlin/config.json'), json.dumps(config))
        project.run('--gate', 'passed')
        assert sorted(project.config()) == CONFIG_KEYS

    # purlin: scaffold PROOF-87
    def test_a_project_with_tests_is_asked_nothing_about_them(self, project):
        output = project.run('--gate', 'strong')
        assert asked(output) == [scaffold_module.MUTATION_QUESTION % 'mutmut'
                                 ], output
        assert project.config()['tests'] == []

    # purlin: scaffold PROOF-88
    def test_an_empty_project_is_asked_nothing(self):
        made = Project(None)
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root,
                 '--gate', 'passed'], capture_output=True, encoding='utf-8',
                timeout=300, stdin=subprocess.DEVNULL)
            assert done.returncode == 0, done.stdout + done.stderr
            assert asked(done.stdout) == [], done.stdout
            assert made.config()['tests'] == []
        finally:
            made.close()

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
            out = _answering(made, 'y\n', '--gate', 'strong')
            assert scaffold_module.MUTATION_QUESTION % 'mutmut' in out, out
            assert made.config()['mutation_engine'] == 'auto'
            assert made.config()['min_strength'] == 70
            assert '[mutmut]' in read(made.path('setup.cfg'))
        finally:
            made.close()

    # purlin: scaffold PROOF-81
    def test_no_turns_it_off_and_wires_nothing(self):
        made = Project('pytest')
        try:
            _answering(made, 'n\n', '--gate', 'strong')
            assert made.config()['mutation_engine'] == 'none'
            assert made.config()['min_strength'] is None
            assert not made.has('setup.cfg')
            assert 'mutants/' not in read(made.path('.gitignore'))
        finally:
            made.close()

    # purlin: scaffold PROOF-82
    def test_at_strong_a_framework_with_no_engine_is_told_why(self):
        made = Project('shell')
        try:
            out = _answering(made, '\n', '--gate', 'strong')
            assert 'Measure test strength' not in out, out
            assert made.config()['mutation_engine'] == 'none'
            assert 'no engine breaks shell code' in out, out
        finally:
            made.close()

    # purlin: scaffold PROOF-83
    def test_at_passed_a_framework_with_no_engine_is_told_nothing(self):
        made = Project('shell')
        try:
            out = _answering(made, '\n', '--gate', 'passed')
            assert 'Measure test strength' not in out, out
            assert made.config()['mutation_engine'] == 'none'
            assert 'no engine breaks' not in out, out
        finally:
            made.close()

    # purlin: scaffold PROOF-84
    def test_a_value_the_config_carries_is_kept_without_asking(self, project):
        write(project.path('.purlin/config.json'),
              json.dumps({'mutation_engine': 'auto'}) + '\n')
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', project.root,
             '--gate', 'strong'], capture_output=True, encoding='utf-8',
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

    # purlin: scaffold PROOF-85
    def test_yes_with_no_gate_takes_passed(self, project):
        output = project.run()
        assert '[passed]: passed' in output.splitlines(), output
        assert project.config()['gate'] == 'passed'

    # purlin: scaffold PROOF-86
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


class TestTheAnchorsFolder:

    # purlin: scaffold PROOF-89
    def test_no_folder_for_anchors_is_made(self, project):
        output = project.run('--gate', 'strong')
        assert os.path.isdir(project.path('specs'))
        assert not os.path.exists(project.path('specs/_anchors'))
        assert 'specs/_anchors' not in output, output


# ---------------------------------------------------------------------------
# Nothing in the tests
# ---------------------------------------------------------------------------

class TestNothingInTheTests:

    # purlin: scaffold PROOF-8
    def test_nothing_is_written_into_a_pytest_suite(self):
        made = Project('pytest')
        try:
            os.remove(made.path('conftest.py'))
            write(made.path('pyproject.toml'), '[tool.pytest]\n')
            before = tree(made.root)
            output = made.run('--gate', 'passed')
            assert not made.has('conftest.py'), output
            assert 'conftest.py' not in summary_paths(output)
            # Every file the project held reads the same, and the only paths
            # added are Purlin's own: nothing lands among the tests.
            after = tree(made.root)
            assert {rel: after.get(rel) for rel in before} == before
            assert sorted(set(after) - set(before)) == [
                '.gitignore', '.purlin', '.purlin/config.json',
                '.purlin/evidence', '.purlin/evidence/README.md',
                'purlin-report.html', 'specs'], output
        finally:
            made.close()

    @pytest.mark.parametrize('language,wiring',
                             [('vitest', 'vitest.config.ts'),
                              ('jest', 'jest.config.js')])
    # purlin: scaffold PROOF-59
    # purlin: scaffold PROOF-60
    def test_nothing_is_written_into_a_node_suite(self, language, wiring):
        made = Project(language)
        try:
            output = made.run('--gate', 'passed')
            assert not made.has(wiring), output
            assert wiring not in summary_paths(output)
        finally:
            made.close()

    # purlin: scaffold PROOF-61
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
    def test_a_node_project_is_told_about_stryker(self):
        made = Project('vitest')
        try:
            output = made.run('--gate', 'passed', '--mutation')
            assert ('vitest: Stryker measures the breaks. Without it the test '
                    'strength reads n/a.' in output.splitlines()), output
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Nobody is named, and the gate moves
# ---------------------------------------------------------------------------

class TestTheGateMoves:

    # purlin: scaffold PROOF-12
    def test_raising_the_gate_writes_the_setting_and_no_workflow(self,
                                                                 project):
        """A runner is decided by the `@env` tags, not the gate."""
        project.run('--gate', 'passed')
        assert not project.has('.github/workflows/purlin.yml')
        project.run('--gate', 'strong')
        assert not project.has('.github/workflows/purlin.yml')
        assert project.config()['gate'] == 'strong'

    # purlin: scaffold PROOF-62
    def test_raising_to_signed_keeps_the_workflow(self, project):
        tag_foreign(project)
        project.run('--gate', 'strong')
        before = tree(project.root)
        output = project.run('--gate', 'signed')
        assert summary_paths(output)['.github/workflows/purlin.yml'] == 'kept'
        # Every file the earlier run wrote is there, and only the settings
        # file and the dashboard's data differ.
        assert changed_since(before, tree(project.root)) == [
            '.purlin/config.json', REPORT_DATA]
        assert project.config()['gate'] == 'signed'

    # purlin: scaffold PROOF-63
    def test_lowering_writes_the_setting_and_deletes_nothing(self, project):
        tag_foreign(project)
        project.run('--gate', 'signed')
        before = tree(project.root)
        project.run('--gate', 'passed')
        assert project.config()['gate'] == 'passed'
        assert project.config()['min_strength'] is None
        assert project.has('.github/workflows/purlin.yml')
        assert changed_since(before, tree(project.root)) == [
            '.purlin/config.json', REPORT_DATA]

    # purlin: scaffold PROOF-20
    def test_a_second_run_at_the_same_gate_changes_nothing(self, project):
        project.run('--gate', 'strong')
        files = tree(project.root)
        output = project.run('--gate', 'strong')
        assert 'wrote' not in summary_paths(output).values()
        # Not a byte of the project changed, whatever the summary says.
        assert tree(project.root) == files


# ---------------------------------------------------------------------------
# The remote runner
# ---------------------------------------------------------------------------

class TestTheWorkflow:
    """A workflow is written for one reason and no other."""

    # purlin: scaffold PROOF-13
    def test_a_project_with_no_foreign_proof_gets_no_workflow(self, project):
        output = project.run('--gate', 'strong')
        assert not project.has('.github/workflows/purlin.yml')
        assert ('No remote runner: every proof runs on this operating system, '
                'so nothing has to run remotely.') in output.splitlines(), output

    # purlin: scaffold PROOF-64
    def test_at_passed_the_reason_names_the_test(self, project):
        named = tag_foreign(project)
        output = project.run('--gate', 'passed')
        assert project.has('.github/workflows/purlin.yml'), output
        assert reasons_under_heading(output) == [
            '  A test is tagged @env for %s, which this machine is not, so '
            'only a runner can run it.' % named], output

    # purlin: scaffold PROOF-65
    def test_at_strong_the_reason_names_the_proof(self, project):
        named = tag_foreign(project)
        output = project.run('--gate', 'strong')
        assert project.has('.github/workflows/purlin.yml'), output
        assert reasons_under_heading(output) == [
            '  A proof in specs/ is tagged @env for %s, which this machine '
            'is not, so only a runner can prove it.' % named], output

    # purlin: scaffold PROOF-51
    def test_two_foreign_systems_are_one_reason(self, project):
        here = scaffold_module.evidence_module.host_os()
        others = [name for name in ('linux', 'macos', 'windows')
                  if name != here]
        tag_foreign(project, *others)
        output = project.run('--gate', 'strong')
        (reason,) = reasons_under_heading(output)
        assert all(name in reason for name in others), reason

    # purlin: scaffold PROOF-66
    def test_with_no_remote_nothing_is_written(self):
        made = Project('pytest', host=None)
        try:
            tag_foreign(made)
            output = made.run('--gate', 'strong')
            assert not made.has('.github/workflows/purlin.yml')
            assert 'there is no git remote' in output
        finally:
            made.close()

    # purlin: scaffold PROOF-44
    def test_a_missing_prerequisite_is_named_and_nothing_is_written(self):
        made = Project('pytest', remote='https://example.invalid/x.git')
        try:
            tag_foreign(made)
            output = made.run('--gate', 'strong')
            assert not made.has('.github/workflows/purlin.yml')
            assert output.splitlines().count(UNKNOWN_HOST) == 1, output
            assert ('skipped the CI workflow (a prerequisite is missing)'
                    in output.splitlines()), output
        finally:
            made.close()

    # purlin: scaffold PROOF-77
    def test_a_remote_with_no_branch_yet_still_gets_the_workflow(self):
        made = Project('pytest', host=None)
        bare = os.path.realpath(tempfile.mkdtemp(prefix='purlin-empty-remote-'))
        try:
            tag_foreign(made)
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

    @pytest.mark.parametrize('gh', (True, False))
    # purlin: scaffold PROOF-78
    # purlin: scaffold PROOF-79
    def test_gh_present_or_absent_is_named_and_the_workflow_written(
            self, project, gh):
        """A PATH holding git, and `gh` or not, decides which line prints."""
        if os.name == 'nt':
            pytest.skip('a PATH of one linked git is built on POSIX only')
        tag_foreign(project)
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

    # purlin: scaffold PROOF-71
    def test_an_azure_remote_gets_the_pipeline(self):
        made = Project('pytest',
                       remote='https://dev.azure.com/acme/demo/_git/demo')
        try:
            tag_foreign(made)
            output = made.run('--gate', 'strong')
            assert made.has('purlin.azure-pipelines.yml'), output
            assert 'wrote purlin.azure-pipelines.yml' in output.splitlines()
            assert not made.has('.github/workflows/purlin.yml'), output
        finally:
            made.close()

    # purlin: scaffold PROOF-15
    def test_windows_and_macos_tags_are_the_matrix(self, project):
        tag_foreign(project, 'windows', 'macos')
        project.run('--gate', 'strong')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert '        os: [macos-latest, windows-latest]\n' in workflow, (
            workflow)

    # purlin: scaffold PROOF-72
    def test_one_foreign_system_is_the_whole_matrix(self, project):
        named = tag_foreign(project)
        project.run('--gate', 'strong')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert '        os: [%s-latest]\n' % named in workflow, workflow
        assert 'ubuntu-latest' not in workflow, workflow

    # purlin: scaffold PROOF-73
    def test_the_purlin_release_is_pinned(self, project):
        tag_foreign(project)
        project.run('--gate', 'strong')
        version = read(os.path.join(ROOT, 'VERSION')).strip()
        assert 'v%s' % version in read(
            project.path('.github/workflows/purlin.yml'))

    # purlin: scaffold PROOF-42
    def test_the_triggers_are_a_run_branch_and_the_signing_tag(self, project):
        tag_foreign(project)
        project.run('--gate', 'strong')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        block = workflow.split('\non:\n', 1)[1].split('\npermissions:', 1)[0]
        assert block == ("  push:\n    branches: ['run/**']\n"
                         "    tags: ['signed/**']\n")

    # purlin: scaffold PROOF-74
    def test_the_last_step_is_the_test_run(self, project):
        tag_foreign(project)
        project.run('--gate', 'strong')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert workflow.rstrip().endswith(
            'scripts/run/purlin_run.py" --all --ci'), workflow

    # purlin: scaffold PROOF-75
    def test_the_azure_pipeline_has_the_same_triggers(self):
        made = Project('pytest',
                       remote='https://dev.azure.com/acme/demo/_git/demo')
        try:
            tag_foreign(made)
            made.run('--gate', 'strong')
            pipeline = read(made.path('purlin.azure-pipelines.yml'))
            assert '      - run/*\n' in pipeline
            assert '      - signed/*\n' in pipeline
            assert 'pr: none\n' in pipeline
        finally:
            made.close()

    # purlin: scaffold PROOF-76
    def test_the_azure_pipeline_ends_on_the_test_run(self):
        made = Project('pytest',
                       remote='https://dev.azure.com/acme/demo/_git/demo')
        try:
            tag_foreign(made)
            made.run('--gate', 'strong')
            pipeline = read(made.path('purlin.azure-pipelines.yml'))
            # The test run is the last step: no step follows it.
            tail = pipeline.split('scripts/run/purlin_run.py" --all --ci',
                                  1)[1]
            assert not [line for line in tail.splitlines()
                        if line.lstrip().startswith('- ')], tail
        finally:
            made.close()


# The line for a remote that names neither host, word for word.
UNKNOWN_HOST = ('The origin remote is neither GitHub nor Azure DevOps. '
                'Everything on this machine works with any host; only '
                'purlin:test --remote needs one of those two.')


class TestTheHost:

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
        finally:
            made.close()

    @pytest.mark.parametrize('url,host', [
        ('https://github.com/acme/demo.git', 'github'),
        ('https://dev.azure.com/acme/demo/_git/demo', 'azure')])
    # purlin: scaffold PROOF-67
    # purlin: scaffold PROOF-68
    def test_a_known_host_is_printed_and_written(self, url, host):
        made = Project('pytest', remote=url)
        try:
            output = made.run('--gate', 'strong')
            assert ('Gate strong. Suites none. Git host %s.' % host
                    in output.splitlines()), output
            assert made.config()['ci'] == host
        finally:
            made.close()

    # purlin: scaffold PROOF-69
    def test_a_host_that_is_neither_says_what_still_works(self):
        made = Project('pytest', remote='https://git.example.com/acme/demo.git')
        try:
            lines = made.run('--gate', 'strong').splitlines()
            at = lines.index('Gate strong. Suites none. Git host not read '
                             'from a remote.')
            assert lines[at + 1] == UNKNOWN_HOST, lines
            assert made.config()['ci'] == 'none'
        finally:
            made.close()

    # purlin: scaffold PROOF-70
    def test_no_remote_reads_no_host(self):
        made = Project('pytest', host=None)
        try:
            assert scaffold_module.git_remote(made.root) is False
            output = made.run('--gate', 'strong')
            assert ('Gate strong. Suites none. Git host not read from a '
                    'remote.' in output.splitlines()), output
            assert 'neither GitHub nor Azure DevOps' not in output, output
            assert made.config()['ci'] == 'none'
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

    # purlin: scaffold PROOF-18
    def test_the_dashboard_is_copied(self, project):
        project.run('--gate', 'passed')
        source = os.path.join(ROOT, 'scripts', 'report', 'purlin-report.html')
        assert read(project.path('purlin-report.html')) == read(source)

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

    # purlin: scaffold PROOF-19
    def test_the_engine_block_is_added_once(self, project):
        project.run('--gate', 'passed', '--mutation')
        project.run('--gate', 'passed')
        assert read(project.path('setup.cfg')).count('[mutmut]') == 1

    # purlin: scaffold PROOF-40
    def test_the_mutmut_copy_is_ignored_once(self, project):
        write(project.path('greeting.py'), 'def greet(name):\n    return name\n')
        write(project.path('tests/test_greeting.py'), 'def test_greet():\n    pass\n')
        project.run('--gate', 'passed', '--mutation')
        project.run('--gate', 'passed')
        lines = read(project.path('.gitignore')).splitlines()
        assert lines.count('mutants/') == 1

    # purlin: scaffold PROOF-34
    def test_with_no_spec_the_last_line_sends_you_to_write_one(self, project):
        lines = project.run('--gate', 'passed').strip().splitlines()
        assert lines[-1] == '→ Run: purlin:spec to write the first spec.'

    # purlin: scaffold PROOF-80
    def test_with_a_spec_it_ends_on_what_is_left_to_do(self, project):
        project.spec()
        lines = project.run('--gate', 'passed').strip().splitlines()
        assert lines[-3:] == ['1 rule. 0 pass their tests.', 'Left to do:',
                              '  1 rule to write a test for: purlin:build'], (
            lines)

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
    def test_add_appends_to_the_suites_already_there(self, project):
        project.run('--gate', 'passed')
        project.run('--add', 'pytest')
        project.run('--add', 'vitest')
        assert [suite['name'] for suite in project.config()['tests']] == [
            'pytest', 'vitest']

    # purlin: scaffold PROOF-98
    def test_add_twice_names_the_framework_once(self, project):
        project.run('--gate', 'passed')
        project.run('--add', 'pytest')
        project.run('--add', 'vitest')
        project.run('--add', 'vitest')
        assert [suite['name'] for suite in project.config()['tests']] == [
            'pytest', 'vitest']

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
             '--update', '--yes'], capture_output=True, encoding='utf-8',
            timeout=300, stdin=subprocess.DEVNULL)
        assert done.returncode == 0, done.stdout + done.stderr
        assert ('Nothing is pending: this project is at %s.'
                % read(os.path.join(ROOT, 'VERSION')).strip()
                in done.stdout.splitlines()), done.stdout


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
            tag_foreign(made)
            output = made.run('--gate', 'strong',
                              script=os.path.join(installed, 'scripts', 'init',
                                                  'scaffold.py'),
                              env={'CLAUDE_PLUGIN_ROOT': installed})
            assert made.has('.github/workflows/purlin.yml'), output
            # The same project set up from this checkout ends the same, file
            # for file and line for line.
            here = Project('pytest')
            try:
                tag_foreign(here)
                ours = here.run('--gate', 'strong', subprocess=True)
                theirs, mine = tree(made.root), tree(here.root)
                for files in (theirs, mine):
                    files.pop(REPORT_DATA, None)
                assert theirs == mine
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
# A Go module through the command its first test run suggests
# ---------------------------------------------------------------------------

SUGGESTED = 'Suggested entry: '


def take_the_suggestion(root, output):
    """Write the entry a first test run suggested, as `purlin:test` does."""
    (line,) = [line for line in output.splitlines()
               if line.startswith(SUGGESTED)]
    path = root / '.purlin' / 'config.json'
    config = json.loads(path.read_text(encoding='utf-8'))
    config['tests'] = [json.loads(line[len(SUGGESTED):])]
    path.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')


# purlin: scaffold PROOF-52
def test_a_go_module_runs_through_the_command_its_first_run_suggests(tmp_path):
    """Go itself, not a sample of what it prints: init sets the module up,
    the first run suggests the module's own command, and each marker reads
    what Go said."""
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
    for name, text in GO_SPECS.items():
        _write(root, 'specs/shop/%s.md' % name, text)
    subprocess.run(['git', 'add', '-A'], cwd=str(root), check=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'the module'], cwd=str(root),
                   check=True)

    _code, first = _run(root, '--all', '--test')
    take_the_suggestion(root, first)
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
