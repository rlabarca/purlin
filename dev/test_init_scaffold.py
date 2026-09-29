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

The last section walks a real python, typescript and C# project from init to
the signed tag with the commands a person runs, one case per step.
"""

import contextlib
import io
import json
import os
import pathlib
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


def _minimum(made, gate, *flags):
    """`min_strength` after a set-up at `gate`, the seven keys checked too."""
    made.run('--gate', gate, *flags)
    config = made.config()
    assert config['gate'] == gate
    assert sorted(config) == CONFIG_KEYS
    return config['min_strength']


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

    # purlin: scaffold PROOF-2
    def test_with_mutation_on_passed_has_no_minimum(self, project):
        assert _minimum(project, 'passed', '--mutation') is None

    # purlin: scaffold PROOF-99
    def test_with_mutation_on_strong_asks_70(self, project):
        assert _minimum(project, 'strong', '--mutation') == 70

    # purlin: scaffold PROOF-100
    def test_with_mutation_on_signed_asks_80(self, project):
        assert _minimum(project, 'signed', '--mutation') == 80

    # purlin: scaffold PROOF-103
    def test_with_mutation_off_passed_has_no_minimum(self, project):
        assert _minimum(project, 'passed') is None

    # purlin: scaffold PROOF-101
    def test_with_mutation_off_strong_has_no_minimum(self, project):
        assert _minimum(project, 'strong') is None

    # purlin: scaffold PROOF-102
    def test_with_mutation_off_signed_has_no_minimum(self, project):
        assert _minimum(project, 'signed') is None

    # purlin: scaffold PROOF-3
    def test_the_gate_flag_answers_the_question_without_asking(self, project):
        output = project.run('--gate', 'passed')
        assert scaffold_module.GATE_QUESTION not in output
        assert project.config()['gate'] == 'passed'

    # purlin: scaffold PROOF-104
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
        assert asked(output) == [scaffold_module.MUTATION_QUESTION % 'mutmut'
                                 ], output
        assert 'audit_parallel' not in output

    # purlin: scaffold PROOF-54
    def test_the_template_carries_six_keys_in_order(self):
        template = json.loads(read(TEMPLATE_CONFIG))
        assert list(template) == ['gate', 'mutation_engine', 'min_strength',
                                  'audit_parallel', 'tests', 'ci']
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

    def test_a_child_run_and_an_in_process_run_agree(self):
        """The command line and `main()` write the same config and output.

        No proof: this holds the in-process runs the other cases make to the
        command a person runs, so what they show is what init does.
        """
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
            assert ('Mutation testing is off: no engine breaks shell code, so '
                    'the AI audit alone judges test strength.'
                    in re.sub(r'\[[^\]\n]*\]: ', '', out).splitlines()), out
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
    def test_the_first_run_writes_the_readme(self, project):
        output = project.run('--gate', 'passed')
        readme = project.path('.purlin/evidence/README.md')
        with open(readme, 'rb') as got, open(os.path.join(
                ROOT, 'templates', 'evidence-readme.md'), 'rb') as want:
            assert got.read() == want.read()
        text = read(readme)
        assert 'local/' in text and 'ci/' in text
        assert summary_paths(output)[README] == 'wrote', output

    # purlin: scaffold PROOF-124
    def test_a_second_run_keeps_the_readme(self, project):
        project.run('--gate', 'passed')
        again = project.run('--gate', 'passed')
        assert summary_paths(again)[README] == 'kept', again

    # purlin: scaffold PROOF-125
    def test_a_readme_the_project_edited_stays_edited(self, project):
        project.run('--gate', 'passed')
        text = read(project.path(README))
        with open(project.path(README), 'wb') as handle:
            handle.write((text + 'Our own note.\n').encode('utf-8'))
        edited = tree(project.root)[README]
        third = project.run('--gate', 'passed')
        assert summary_paths(third)[README] == 'kept', third
        assert tree(project.root)[README] == edited


README = '.purlin/evidence/README.md'


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

    # purlin: scaffold PROOF-59
    def test_nothing_is_written_into_a_vitest_suite(self):
        _nothing_in_the_node_suite('vitest', 'vitest.config.ts')

    # purlin: scaffold PROOF-60
    def test_nothing_is_written_into_a_jest_suite(self):
        _nothing_in_the_node_suite('jest', 'jest.config.js')

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
    def test_a_vitest_project_is_told_about_stryker(self):
        _told_about_stryker('vitest', 'passed')

    # purlin: scaffold PROOF-105
    def test_a_jest_project_is_told_about_stryker(self):
        _told_about_stryker('jest', 'strong')

    # purlin: scaffold PROOF-106
    def test_a_csharp_project_is_told_about_stryker(self):
        _told_about_stryker('dotnet', 'strong')


def _nothing_in_the_node_suite(language, wiring):
    """A Node project set up at `passed` holds no runner file of Purlin's."""
    made = Project(language)
    try:
        output = made.run('--gate', 'passed')
        assert not made.has(wiring), output
        assert wiring not in summary_paths(output)
    finally:
        made.close()


def _told_about_stryker(language, gate):
    """The one line a project whose engine is Stryker is told."""
    made = Project(language)
    try:
        output = made.run('--gate', gate, '--mutation')
        assert ('%s: Stryker measures the breaks. Without it test strength '
                'is not measured.' % language in output.splitlines()), output
    finally:
        made.close()


# ---------------------------------------------------------------------------
# The gate moves
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
            assert summary_paths(output)[
                '.github/workflows/purlin.yml'] == 'wrote', output
        finally:
            shutil.rmtree(bare, ignore_errors=True)
            made.close()

    # purlin: scaffold PROOF-78
    def test_gh_installed_is_named_and_the_workflow_written(self):
        _host_tool_line('github', 'gh', installed=True)

    # purlin: scaffold PROOF-79
    def test_gh_missing_is_named_and_the_workflow_still_written(self):
        _host_tool_line('github', 'gh', installed=False)

    # purlin: scaffold PROOF-113
    def test_az_installed_is_named_and_the_pipeline_written(self):
        _host_tool_line('azure', 'az', installed=True)

    # purlin: scaffold PROOF-114
    def test_az_missing_is_named_and_the_pipeline_still_written(self):
        _host_tool_line('azure', 'az', installed=False)

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


def _host_tool_line(host, tool, installed):
    """Init on a `host` remote with `tool` on the search path or not.

    The search path holds a link to git and, where `installed`, an empty
    `tool`, so which of the two lines prints is decided by that alone.
    """
    if os.name == 'nt':
        pytest.skip('a PATH of one linked git is built on POSIX only')
    if host == 'azure':
        made = Project('pytest',
                       remote='https://dev.azure.com/acme/demo/_git/demo')
        runner = 'purlin.azure-pipelines.yml'
    else:
        made = Project('pytest')
        runner = '.github/workflows/purlin.yml'
    bin_dir = os.path.realpath(tempfile.mkdtemp(prefix='purlin-bin-'))
    try:
        tag_foreign(made)
        os.symlink(shutil.which('git'), os.path.join(bin_dir, 'git'))
        if installed:
            write(os.path.join(bin_dir, tool), '#!/bin/sh\n')
        output = made.run('--gate', 'strong', env={'PATH': bin_dir})
        lines = output.splitlines()
        present = '%s is installed, so a remote run can be watched from here.'
        absent = ('%s is not installed, so purlin:test --remote cannot watch '
                  'a run. Install it, or open the run on the git host '
                  'instead.')
        assert ((present % tool) in lines) is installed, output
        assert ((absent % tool) in lines) is not installed, output
        assert made.has(runner), output
    finally:
        shutil.rmtree(bin_dir, ignore_errors=True)
        made.close()


# The line for a remote that names a git host Purlin cannot use, word for word.
UNKNOWN_HOST = ('This git host cannot run tests remotely. Everything on this '
                'machine works.')


def _host_read(url, host):
    """Init on a project whose remote is `url` prints and writes `host`."""
    made = Project('pytest', remote=url)
    try:
        output = made.run('--gate', 'strong')
        assert ('Gate strong. Suites none. Git host %s.' % host
                in output.splitlines()), output
        assert made.config()['ci'] == host
    finally:
        made.close()


class TestTheHost:

    # purlin: scaffold PROOF-14
    def test_a_github_ssh_remote_reads_github(self):
        _host_read('git@github.com:acme/demo.git', 'github')

    # purlin: scaffold PROOF-67
    def test_a_github_https_remote_reads_github(self):
        _host_read('https://github.com/acme/demo.git', 'github')

    # purlin: scaffold PROOF-68
    def test_a_dev_azure_com_remote_reads_azure(self):
        _host_read('https://dev.azure.com/acme/demo/_git/demo', 'azure')

    # purlin: scaffold PROOF-107
    def test_a_visualstudio_com_remote_reads_azure(self):
        _host_read('https://acme.visualstudio.com/demo/_git/demo', 'azure')

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
            assert git(made.root, 'remote').stdout == ''
            output = made.run('--gate', 'strong')
            assert ('Gate strong. Suites none. Git host not read from a '
                    'remote.' in output.splitlines()), output
            assert 'cannot run tests remotely' not in output, output
            assert made.config()['ci'] == 'none'
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Everything else init writes
# ---------------------------------------------------------------------------

class TestWhatInitWrites:

    # purlin: scaffold PROOF-18
    def test_the_summary_names_the_four_files_it_writes(self, project):
        output = project.run('--gate', 'strong')
        named = summary_paths(output)
        for rel in ('.purlin/config.json', '.gitignore',
                    '.purlin/evidence/README.md', 'purlin-report.html'):
            assert named.get(rel) in ('wrote', 'copied'), output
            assert project.has(rel), rel

    # purlin: scaffold PROOF-108
    def test_what_appears_is_exactly_what_the_summary_wrote(self, project):
        before = tree(project.root)
        output = project.run('--gate', 'strong')
        written = sorted(rel for rel, word in summary_paths(output).items()
                         if word in ('wrote', 'copied'))
        assert [rel for rel in written if not project.has(rel)] == [], output
        assert sorted(set(tree(project.root)) - set(before)) == written

    # purlin: scaffold PROOF-109
    def test_the_dashboard_is_copied(self, project):
        output = project.run('--gate', 'passed')
        source = os.path.join(ROOT, 'scripts', 'report', 'purlin-report.html')
        assert read(project.path('purlin-report.html')) == read(source)
        assert summary_paths(output)['purlin-report.html'] == 'copied', output

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

    # purlin: scaffold PROOF-110
    def test_the_engine_block_joins_a_pyproject_once(self, project):
        write(project.path('pyproject.toml'), '[project]\nname = "demo"\n')
        os.makedirs(project.path('src'), exist_ok=True)
        write(project.path('src/app.py'), 'def go():\n    return 1\n')
        project.run('--gate', 'passed', '--mutation')
        project.run('--gate', 'passed')
        text = read(project.path('pyproject.toml'))
        assert text.startswith('[project]\nname = "demo"\n'), text
        assert text.count('[tool.mutmut]') == 1, text
        assert 'source_paths = ["src"]' in text
        assert 'pytest_add_cli_args_test_selection = ["tests"]' in text

    # purlin: scaffold PROOF-111
    def test_without_a_pyproject_setup_cfg_gets_the_block_once(self, project):
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
        """Plain ASCII and the four glyphs the design allows, and nothing
        else, so no emoji in any block of the character set."""
        tag_foreign(project)
        output = project.run('--gate', 'signed')
        assert project.has('.github/workflows/purlin.yml'), output
        assert sorted({ch for ch in output if ord(ch) > 0x7F}
                      - set('→▶▼▲')) == [], output


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

    # purlin: scaffold PROOF-112
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

    # purlin: scaffold PROOF-115
    def test_a_root_that_does_not_exist_exits_2(self):
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', '/no/such/dir',
             '--gate', 'passed', '--yes'], capture_output=True, encoding='utf-8',
            timeout=300, stdin=subprocess.DEVNULL)
        assert done.returncode == 2, done.stdout + done.stderr

    # purlin: scaffold PROOF-116
    def test_a_missing_root_is_named_and_nothing_is_made(self):
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

    # purlin: scaffold PROOF-97
    def test_a_fresh_project_set_up_from_the_copy_does_not_name_it(self):
        """Every file, binary ones too, is read for the install's path."""
        cache, installed = self.copy_plugin()
        made = Project(None, host=None)
        try:
            write(made.path('pyproject.toml'), '[tool.pytest.ini_options]\n')
            write(made.path('greeting.py'),
                  'def greet(name):\n    return "Hello, %s!" % name\n')
            made.run('--gate', 'passed',
                     script=os.path.join(installed, 'scripts', 'init',
                                         'scaffold.py'),
                     env={'CLAUDE_PLUGIN_ROOT': installed})
            assert made.has('.purlin/config.json')
            files = tree(made.root)
            assert [rel for rel, body in files.items() if body is not None
                    and installed.encode('utf-8') in body] == [], installed
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
# The engine's block, which names the source and the tests
# ---------------------------------------------------------------------------

def _mutmut_block(project):
    """The `setup.cfg` init writes for the project with mutation testing on."""
    output = project.run('--gate', 'passed', '--mutation')
    assert summary_paths(output)['setup.cfg'] == 'wrote', output
    return read(project.path('setup.cfg'))


def _block_naming(source, selection):
    """The `setup.cfg` that names one source and one test selection."""
    return ('[mutmut]\nsource_paths =\n    %s\n'
            'pytest_add_cli_args_test_selection =\n    %s\n'
            % (source, selection))


class TestTheEngineBlock:

    # purlin: scaffold PROOF-39
    def test_nested_code_is_source_and_a_test_directory_is_the_selection(
            self, project):
        shutil.rmtree(project.path('tests'), ignore_errors=True)
        write(project.path('scripts/run/job.py'), 'def go():\n    return 1\n')
        write(project.path('dev/test_job.py'), 'def test_go():\n    pass\n')
        write(project.path('dev/build.py'), '')
        write(project.path('docs/guide.md'), '# Guide\n')
        assert _mutmut_block(project) == _block_naming('scripts', 'dev')

    # purlin: scaffold PROOF-120
    def test_src_and_tests_still_win_over_other_directories(self, project):
        write(project.path('src/app.py'), '')
        write(project.path('tools/helper.py'), '')
        write(project.path('tests/test_app.py'), '')
        write(project.path('dev/test_extra.py'), '')
        assert _mutmut_block(project) == _block_naming('src', 'tests')

    # purlin: scaffold PROOF-121
    def test_modules_at_the_root_are_named_one_by_one(self, project):
        write(project.path('greeting.py'), 'def greet(name):\n    return name\n')
        write(project.path('conftest.py'), '')
        write(project.path('test_greeting.py'), 'def test_greet():\n    pass\n')
        assert _mutmut_block(project) == _block_naming('greeting.py', 'tests')

    # purlin: scaffold PROOF-122
    def test_no_python_anywhere_falls_back_to_the_root(self, project):
        write(project.path('docs/guide.md'), '# Guide\n')
        assert _mutmut_block(project) == _block_naming('.', 'tests')

    # purlin: scaffold PROOF-123
    def test_a_package_folder_is_the_source_where_there_is_no_src(
            self, project):
        write(project.path('demo/__init__.py'), '')
        assert _mutmut_block(project) == _block_naming('demo', 'tests')


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


# ---------------------------------------------------------------------------
# A real project of each language, walked from init to the signed tag
# ---------------------------------------------------------------------------
#
# Each project is built once for this file and walked step by step with the
# commands a person runs: init, the first test run and the entry it
# suggests, `purlin:test --commit`, init again at `strong`, the audit, a
# runner's two kinds of run, init at `signed`, `purlin:sign` and the tag.
# Every step's output is kept, and each case below reads the one step it is
# about. Nothing here reaches a git host: the remote is a bare repository on
# disk, and no token is set.

RUN_SCRIPT = os.path.join(ROOT, 'scripts', 'run', 'purlin_run.py')
SIGN_SCRIPT = os.path.join(ROOT, 'scripts', 'review', 'sign.py')

GREETING_SPEC = """# Feature: greeting

> Scope: %s
> Description: One rule, walked from its first test run to the signed tag.

## Rules

- RULE-1: `greet(name)` returns `Hello, <name>!`

## Proof

- PROOF-1 (RULE-1): `greet("Ada")` returns exactly `Hello, Ada!`
"""

# What each language's project holds before init runs, the file its rule
# covers, and its one marked test, written after init.
WALKED = {
    'python': {
        'before': {'pyproject.toml': '[tool.pytest.ini_options]\n',
                   'greeting.py': 'def greet(name):\n'
                                  '    return "Hello, %s!" % name\n',
                   '.gitignore': '__pycache__/\n'},
        'scope': 'greeting.py',
        'test': ('tests/test_greeting.py',
                 'from greeting import greet\n\n\n'
                 '# purlin: greeting PROOF-1\n'
                 'def test_greet():\n'
                 '    assert greet("Ada") == "Hello, Ada!"\n'),
    },
    'typescript': {
        'before': {'package.json': '{"name": "demo", "private": true, '
                                   '"devDependencies": {"vitest": "^3.2.0"}}\n',
                   'greeting.ts': 'export function greet(name: string) {\n'
                                  '  return `Hello, ${name}!`;\n}\n',
                   '.gitignore': 'node_modules/\n'},
        'scope': 'greeting.ts',
        'test': ('tests/greeting.test.ts',
                 "import { expect, test } from 'vitest';\n\n"
                 "import { greet } from '../greeting';\n\n"
                 '// purlin: greeting PROOF-1\n'
                 "test('greets by name', () => {\n"
                 "  expect(greet('Ada')).toBe('Hello, Ada!');\n});\n"),
    },
    'csharp': {
        'before': {
            'App/Greeting.cs': 'namespace App {\n'
                               '  public static class Greeting {\n'
                               '    public static string Greet(string name) '
                               '{ return "Hello, " + name + "!"; }\n'
                               '  }\n}\n',
            'App.Tests/App.Tests.csproj':
                '<Project Sdk="Microsoft.NET.Sdk">\n'
                '  <PropertyGroup>\n'
                '    <TargetFramework>net8.0</TargetFramework>\n'
                '    <IsPackable>false</IsPackable>\n'
                '  </PropertyGroup>\n'
                '  <ItemGroup>\n'
                '    <Compile Include="../App/Greeting.cs" />\n'
                '  </ItemGroup>\n'
                '  <ItemGroup>\n'
                '    <PackageReference Include="Microsoft.NET.Test.Sdk" '
                'Version="17.11.1" />\n'
                '    <PackageReference Include="xunit" Version="2.9.2" />\n'
                '    <PackageReference Include="xunit.runner.visualstudio" '
                'Version="2.8.2" />\n'
                '  </ItemGroup>\n'
                '</Project>\n',
            '.gitignore': 'bin/\nobj/\n'},
        'scope': 'App/Greeting.cs',
        'test': ('App.Tests/GreetingTests.cs',
                 'using Xunit;\n\nnamespace App.Tests {\n'
                 '  public class GreetingTests {\n'
                 '    // purlin: greeting PROOF-1\n'
                 '    [Fact]\n'
                 '    public void GreetsByName() {\n'
                 '      Assert.Equal("Hello, Ada!", '
                 'App.Greeting.Greet("Ada"));\n'
                 '    }\n  }\n}\n'),
    },
}


def walk_env(**extra):
    """The environment every step runs in.

    No variable of a git host's runner is passed on, so a run is a run on a
    person's machine unless a step names the ones it wants, and no token
    means no request is made of any host. This interpreter's folder goes
    first on the search path, so the suggested `python3 -m pytest` finds
    pytest. The `claude` found is the fake the session put on the path.
    """
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('GITHUB_', 'SYSTEM_', 'BUILD_', 'RUNNER_'))
           and key not in ('TF_BUILD', 'CLAUDE_PLUGIN_ROOT',
                           'PURLIN_PROJECT_ROOT')}
    env['PATH'] = os.path.dirname(sys.executable) + os.pathsep + env['PATH']
    found = shutil.which('claude', path=env['PATH'])
    assert found and os.path.isfile(os.path.join(
        os.path.dirname(found), 'fake_claude.json')), found
    env.update(extra)
    return env


class Walk(object):
    """One project of one language, and what each step of its walk printed."""

    def __init__(self, base, language):
        self.language = language
        self.root = os.path.join(base, language)
        self.base = base
        self.out = {}
        self.code = {}
        self.facts = {}

    def path(self, rel):
        return os.path.join(self.root, rel)

    def git(self, *args):
        return git(self.root, *args).stdout.strip()

    def step(self, name, argv, **extra):
        done = subprocess.run(argv, cwd=self.root, capture_output=True,
                              encoding='utf-8', env=walk_env(**extra),
                              stdin=subprocess.DEVNULL, timeout=900)
        self.code[name] = done.returncode
        self.out[name] = done.stdout + done.stderr
        return done

    def init(self, name, gate):
        return self.step(name, [sys.executable, SCAFFOLD, '--project-root',
                                self.root, '--gate', gate, '--yes'])

    def purlin(self, name, *args, **extra):
        return self.step(name, [sys.executable, RUN_SCRIPT, '--project-root',
                                self.root] + list(args), **extra)

    def sign(self, name, *args):
        return self.step(name, [sys.executable, SIGN_SCRIPT] + list(args)
                         + ['--project-root', self.root])

    def lines(self, name):
        return self.out[name].splitlines()

    def last_lines(self, name, count):
        return [line for line in self.lines(name) if line.strip()][-count:]

    def config(self):
        return json.loads(read(self.path('.purlin/config.json')))

    def commit_all(self, message):
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-q', '-m', message)


def set_up(base, language, prepare=None):
    """A project of `language` set up at `passed`, its first spec and marked
    test committed, the entry its first test run suggested written, and the
    test run again with it."""
    walk = Walk(base, language)
    shape = WALKED[language]
    os.makedirs(walk.root)
    git(walk.root, 'init', '-q', '.')
    git(walk.root, 'symbolic-ref', 'HEAD', 'refs/heads/main')
    git(walk.root, 'config', 'user.email', 'dev@example.com')
    git(walk.root, 'config', 'user.name', 'Dev')
    git(walk.root, 'config', 'commit.gpgsign', 'false')
    for rel, body in shape['before'].items():
        write(walk.path(rel), body)
    if prepare:
        prepare(walk)
    bare = os.path.join(base, '%s.github-origin.git' % language)
    git(base, 'init', '--bare', '-q', '-b', 'main', bare)
    git(walk.root, 'remote', 'add', 'origin', bare)
    walk.commit_all('the project')
    git(walk.root, 'push', '-q', '-u', 'origin', 'main')

    walk.init('init at passed', 'passed')
    walk.facts['tests after init'] = walk.config()['tests']
    walk.facts['files after init'] = sorted(tree(walk.root))
    if language == 'csharp':
        # A solution at the root lets the suggested `dotnet test` reach the
        # test project.
        walk.step('solution', ['dotnet', 'new', 'sln', '-n', 'App'])
        walk.step('solution add', ['dotnet', 'sln', 'App.sln', 'add',
                                   'App.Tests/App.Tests.csproj'])
    write(walk.path('specs/core/greeting.md'), GREETING_SPEC % shape['scope'])
    write(walk.path(shape['test'][0]), shape['test'][1])
    write(walk.path('VERSION'), '0.1.0\n')
    walk.commit_all('the first spec and its test')

    walk.purlin('first test run', '--feature', 'greeting', '--test')
    take_the_suggestion(pathlib.Path(walk.root), walk.out['first test run'])
    walk.purlin('test run', '--feature', 'greeting', '--test')
    return walk


def walk_the_gates(walk):
    """From `passed` to the signed tag, one step at a time."""
    walk.purlin('commit', '--all', '--test', '--commit')
    walk.facts['work subject'] = walk.git('log', '-1', '--format=%s', 'HEAD~1')
    walk.facts['work sha7'] = walk.git('rev-parse', 'HEAD~1')[:7]
    walk.facts['evidence subject'] = walk.git('log', '-1', '--format=%s')
    walk.facts['evidence paths'] = walk.git(
        'show', '--name-only', '--format=', 'HEAD').splitlines()

    walk.init('init at strong', 'strong')
    walk.purlin('audit', '--all', '--audit', '--commit')
    # The evidence as the audit's commit holds it.
    evidence = json.loads(walk.git(
        'show', 'HEAD:.purlin/evidence/local/greeting.json') or '{}')
    walk.facts['audited'] = sorted((evidence.get('audit') or {}).get(
        'rules', {}))

    # A runner's two kinds of run, told apart by the variables its host sets.
    ci = walk.path('.purlin/evidence/ci/greeting.json')
    walk.purlin('tag run', '--all', '--ci', GITHUB_REPOSITORY='acme/demo',
                GITHUB_REF='refs/tags/signed/0.1.0',
                GITHUB_REF_NAME='signed/0.1.0')
    walk.facts['ci after the tag run'] = os.path.exists(ci)
    walk.purlin('run branch run', '--all', '--ci',
                GITHUB_REPOSITORY='acme/demo',
                GITHUB_REF_NAME='run/main-0000000')
    walk.facts['ci after the run branch run'] = os.path.exists(ci)
    # A runner commits what it wrote on its own branch, never on this one.
    git(walk.root, 'checkout', '-q', '--', '.purlin/evidence',
        '.purlin/tests.md')
    git(walk.root, 'clean', '-q', '-f', '-d', '--', '.purlin/evidence')

    walk.init('init at signed', 'signed')
    walk.commit_all('raise the gate to signed')
    key = walk.path('.git/signing-key')
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                    '-C', 'jane@acme.com', '-f', key], check=True,
                   capture_output=True)
    for setting, value in (('user.email', 'jane@acme.com'),
                           ('user.name', 'Signer'), ('gpg.format', 'ssh'),
                           ('user.signingkey', key + '.pub')):
        git(walk.root, 'config', setting, value)
    fingerprint = subprocess.run(['ssh-keygen', '-lf', key + '.pub'],
                                 capture_output=True, encoding='utf-8',
                                 check=True).stdout.split()[1]
    walk.facts['key ending'] = fingerprint[-4:]
    walk.sign('sign the rule', 'greeting', 'RULE-1')
    walk.facts['signed commit'] = git(walk.root, 'cat-file', 'commit',
                                      'HEAD').stdout
    walk.sign('sign all', '--all')
    walk.facts['tags'] = walk.git('tag', '-l').splitlines()
    return walk


@pytest.fixture(scope='module')
def python_walk(tmp_path_factory):
    base = os.path.realpath(str(tmp_path_factory.mktemp('walk-python')))
    return walk_the_gates(set_up(base, 'python'))


@pytest.fixture(scope='module')
def typescript_project(tmp_path_factory):
    if not shutil.which('npm'):
        pytest.skip('npm is not on this machine')

    def install(walk):
        done = subprocess.run(
            ['npm', 'install', '--prefer-offline', '--no-fund',
             '--loglevel=error'], cwd=walk.root, capture_output=True,
            encoding='utf-8', timeout=900, env=walk_env())
        if done.returncode != 0:
            pytest.skip('npm could not install Vitest here: %s'
                        % done.stderr.strip()[-200:])
    base = os.path.realpath(str(tmp_path_factory.mktemp('walk-typescript')))
    return set_up(base, 'typescript', install)


@pytest.fixture(scope='module')
def csharp_project(tmp_path_factory):
    if not shutil.which('dotnet'):
        pytest.skip('dotnet is not on this machine')
    base = os.path.realpath(str(tmp_path_factory.mktemp('walk-csharp')))
    return set_up(base, 'csharp')


def suggested_name(walk):
    (line,) = [line for line in walk.lines('first test run')
               if line.startswith(SUGGESTED)]
    return json.loads(line[len(SUGGESTED):])['name']


class TestEachLanguageIsSetUp:

    # purlin: scaffold PROOF-37
    def test_a_python_project_runs_its_marked_test(self, python_walk):
        walk = python_walk
        assert walk.facts['tests after init'] == []
        assert 'conftest.py' not in walk.facts['files after init']
        assert suggested_name(walk) == 'pytest', walk.out['first test run']
        assert walk.last_lines('test run', 2) == [
            '1 rule. 1 passes its tests.', 'Nothing left to do.'], (
            walk.out['test run'])
        assert ('Markers: 1 tied to a test, 0 not tied.'
                in walk.lines('test run')), walk.out['test run']

    # purlin: scaffold PROOF-94
    def test_a_typescript_project_runs_its_marked_test(self,
                                                       typescript_project):
        walk = typescript_project
        assert walk.facts['tests after init'] == []
        assert 'vitest.config.ts' not in walk.facts['files after init']
        assert suggested_name(walk) == 'vitest', walk.out['first test run']
        assert walk.last_lines('test run', 2) == [
            '1 rule. 1 passes its tests.', 'Nothing left to do.'], (
            walk.out['test run'])

    # purlin: scaffold PROOF-95
    def test_a_csharp_project_runs_its_marked_test(self, csharp_project):
        walk = csharp_project
        assert walk.facts['tests after init'] == []
        assert suggested_name(walk) == 'dotnet', walk.out['first test run']
        assert walk.last_lines('test run', 2) == [
            '1 rule. 1 passes its tests.', 'Nothing left to do.'], (
            walk.out['test run'])


class TestTheThreeGates:

    # purlin: scaffold PROOF-36
    def test_at_passed_the_test_run_commits_the_work_then_its_evidence(
            self, python_walk):
        walk = python_walk
        assert walk.code['commit'] == 0, walk.out['commit']
        assert (walk.facts['work subject']
                == 'purlin: specs, tests and settings for greeting')
        assert (walk.facts['evidence subject']
                == 'purlin: evidence at %s' % walk.facts['work sha7'])
        for rel in ('.purlin/evidence/local/greeting.json',
                    '.purlin/tests.md'):
            assert rel in walk.facts['evidence paths'], walk.facts
        assert walk.last_lines('commit', 1) == ['Nothing left to do.'], (
            walk.out['commit'])

    # purlin: scaffold PROOF-90
    def test_raised_to_strong_one_rule_is_left_to_audit(self, python_walk):
        assert python_walk.last_lines('init at strong', 1) == [
            '  1 rule to audit: purlin:audit'], python_walk.out['init at strong']

    # purlin: scaffold PROOF-117
    def test_the_audit_writes_into_the_evidence_and_commits_it(
            self, python_walk):
        walk = python_walk
        assert walk.facts['audited'] == ['RULE-1'], walk.out['audit']
        assert 'Evidence committed.' in walk.lines('audit'), walk.out['audit']
        assert walk.last_lines('audit', 2) == [
            '1 rule. 1 passes its tests. 1 is strong.',
            'Nothing left to do.'], walk.out['audit']

    # purlin: scaffold PROOF-91
    def test_a_runner_s_run_on_the_signed_tag_writes_nothing(
            self, python_walk):
        walk = python_walk
        assert ('Tag run: nothing is written. This run reruns the tests on '
                'signed/0.1.0.' in walk.lines('tag run')), walk.out['tag run']
        assert walk.facts['ci after the tag run'] is False

    # purlin: scaffold PROOF-118
    def test_a_runner_s_run_on_a_run_branch_writes_its_evidence(
            self, python_walk):
        walk = python_walk
        out = walk.out['run branch run']
        assert ('Evidence written to .purlin/evidence/ci/greeting.json.'
                in walk.lines('run branch run')), out
        assert walk.facts['ci after the run branch run'] is True
        assert 'Tag run:' not in out, out

    # purlin: scaffold PROOF-92
    def test_raised_to_signed_one_rule_is_left_to_sign(self, python_walk):
        assert python_walk.last_lines('init at signed', 1) == [
            '  1 rule to sign: purlin:sign'], python_walk.out['init at signed']

    # purlin: scaffold PROOF-119
    def test_signing_the_rule_makes_a_signed_commit_naming_the_signer(
            self, python_walk):
        walk = python_walk
        assert walk.code['sign the rule'] == 0, walk.out['sign the rule']
        assert ('\ngpgsig ' in walk.facts['signed commit']), (
            walk.facts['signed commit'])
        assert ('Signed 1 rule as jane@acme.com with the key ending ...%s.'
                % walk.facts['key ending'] in walk.lines('sign the rule')), (
            walk.out['sign the rule'])

    # purlin: scaffold PROOF-93
    def test_with_the_rule_signed_the_signed_tag_is_written(
            self, python_walk):
        walk = python_walk
        assert 'signed/0.1.0' in walk.facts['tags'], walk.out['sign all']
        assert ('Nothing left to do. Push the tag to release it: git push '
                'origin signed/0.1.0' in walk.lines('sign all')), (
            walk.out['sign all'])
