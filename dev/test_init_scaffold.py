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

The last section sets up a real python, typescript and C# project and runs
each one's marked test, and walks the python project from init to the signed
tag with the commands a person runs, one case per step.
"""

import contextlib
import functools
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
CONFIG_KEYS = sorted(['version', 'gate', 'mutation_engine',
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
            if parts[0] == 'copied' and ' to ' in rest:
                rest = rest.split(' to ', 1)[1]
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


# Where setup waits for an answer: `[<default>]: ` under the gate question,
# and ` [y/N] ` at the end of a yes-or-no question's own line.
PROMPT = r'\[[^\]\n]*\]: | \[y/N\] '


def asked(output):
    """Each question a run with answers on stdin asked: the first line of
    the question above a `[<default>]: ` prompt, and the words before
    `[y/N]` on a yes-or-no question's own line."""
    questions, start = [], 0
    for prompt in re.finditer(PROMPT, output):
        before = output[start:prompt.start()]
        if prompt.group(0).endswith(': '):
            questions.append(before.split('\n', 1)[0])
        else:
            questions.append(before.rsplit('\n', 1)[-1])
        start = prompt.end()
    return questions


def unprompted(output):
    """The output's lines, each prompt a piped answer left unended set aside."""
    return re.sub(PROMPT, '\n', output).splitlines()


COMMIT = scaffold_module.COMMIT_QUESTION


def masked(output, root):
    """The output with the project's path and the commit's sha set aside."""
    return re.sub(r'^Committed [0-9a-f]{7},', 'Committed <sha7>,',
                  output.replace(root, '<root>'), flags=re.M)


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


def system_word(name):
    """How a person reads a stored system word: `Windows`, `macOS`,
    `Linux/Unix`."""
    return {'windows': 'Windows', 'macos': 'macOS', 'linux': 'Linux/Unix'}[name]


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
    def test_at_signed_a_project_with_code_is_asked_three_questions(self):
        made = Project('pytest')
        try:
            out = _answering(made, 'signed\n')
            mutation = scaffold_module.MUTATION_QUESTION % 'mutmut'
            assert asked(out) == [
                'What must be true of every rule before a version is '
                'finished?', mutation, 'Commit the files setup wrote?'], out
            assert made.config()['gate'] == 'signed'
            assert made.config()['mutation_engine'] == 'none'
        finally:
            made.close()

    # purlin: scaffold PROOF-53
    def test_at_passed_a_project_with_code_is_asked_the_gate_alone(self):
        made = Project('pytest')
        try:
            out = _answering(made, 'passed\n')
            assert asked(out) == [
                'What must be true of every rule before a version is '
                'finished?', COMMIT], out
            assert made.config()['gate'] == 'passed'
            assert made.config()['mutation_engine'] == 'none'
        finally:
            made.close()

    # purlin: scaffold PROOF-126
    def test_a_later_run_asks_nothing_before_it_writes(self):
        made = Project('pytest')
        try:
            made.run('--gate', 'passed')
            # Answers wait on stdin, so any question would be seen asked.
            out = _answering(made, 'n\n' * 20, '--gate', 'signed')
            assert asked(out) == [COMMIT], out
            # It is asked once the lines naming each file are printed.
            lines = unprompted(out)
            assert lines.index(COMMIT) > lines.index(
                'wrote .purlin/config.json'), out
            assert made.config()['gate'] == 'signed'
        finally:
            made.close()

    # purlin: scaffold PROOF-3
    def test_the_gate_flag_answers_the_question_without_asking(self, project):
        output = project.run('--gate', 'passed')
        assert ('What must be true of every rule before a version is '
                'finished?') not in output
        assert project.config()['gate'] == 'passed'

    # purlin: scaffold PROOF-104
    def test_the_gate_is_remembered_when_no_flag_names_one(self, project):
        project.run('--gate', 'signed')
        output = project.run()
        assert scaffold_module.GATE_QUESTION not in output
        assert project.config()['gate'] == 'signed'

    # purlin: scaffold PROOF-4
    def test_an_unreadable_answer_falls_back_to_passed(self):
        made = Project('pytest')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root],
                input='whenever\n', capture_output=True, encoding='utf-8',
                timeout=300)
            assert made.config()['gate'] == 'passed'
            assert done.returncode == 0, done.stdout + done.stderr
            # A piped answer ends no line, so the prompt is set aside first.
            assert ('"whenever" is not accepted for gate; it takes passed '
                    'or signed. Reading it as passed.'
                    in unprompted(done.stdout)), done.stdout
        finally:
            made.close()

    # purlin: scaffold PROOF-138
    def test_a_gate_flag_that_is_no_gate_is_refused(self):
        made = Project('pytest')
        try:
            before = tree(made.root)
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root,
                 '--gate', 'gold'], capture_output=True, encoding='utf-8',
                timeout=300, stdin=subprocess.DEVNULL)
            assert done.returncode == 2, done.stdout + done.stderr
            assert done.stderr == (
                '"gold" is not accepted for gate; it takes passed or signed. '
                'Nothing was written.\n'), done.stderr
            assert tree(made.root) == before
        finally:
            made.close()

    # purlin: scaffold PROOF-167
    def test_the_gate_question_offers_two_choices(self, project):
        lines = project.run().splitlines()
        at = lines.index('What must be true of every rule before a version '
                         'is finished?')
        assert lines[at + 1:at + 3] == [
            "  passed  every rule's tests pass",
            "  signed  every rule's tests pass, and a person signs each "
            'release'], lines
        assert not lines[at + 3].startswith('  '), lines

    # purlin: scaffold PROOF-168
    def test_at_passed_the_mutation_question_is_not_asked(self):
        made = Project('pytest')
        try:
            out = _answering(made, 'y\n' * 5, '--gate', 'passed')
            assert not [question for question in asked(out)
                        if question.startswith('Measure test strength')], out
            assert made.config()['mutation_engine'] == 'none'
        finally:
            made.close()

    # purlin: scaffold PROOF-169
    def test_at_signed_the_mutation_question_is_asked(self):
        made = Project('pytest')
        try:
            out = _answering(made, 'n\n' * 5, '--gate', 'signed')
            assert scaffold_module.MUTATION_QUESTION % 'mutmut' in asked(
                out), out
            assert scaffold_module.MUTATION_QUESTION % 'mutmut' == (
                'Measure test strength by breaking the code on purpose? It '
                'needs mutmut and takes minutes to hours per run.')
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The settings file
# ---------------------------------------------------------------------------

class TestTheSettings:

    # purlin: scaffold PROOF-5
    def test_the_config_holds_the_six_keys(self, project):
        output = project.run('--gate', 'signed')
        config = project.config()
        assert sorted(config) == CONFIG_KEYS
        assert config['version'] == read(os.path.join(ROOT, 'VERSION')).strip()
        assert config['audit_parallel'] == 4
        assert asked(output) == [scaffold_module.MUTATION_QUESTION % 'mutmut'
                                 ], output
        assert 'audit_parallel' not in output

    # purlin: scaffold PROOF-54
    def test_the_template_carries_five_keys_in_order(self):
        template = json.loads(read(TEMPLATE_CONFIG))
        assert list(template) == ['gate', 'mutation_engine',
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
            child_out = child.run('--gate', 'signed', subprocess=True)
            inline_out = inline.run('--gate', 'signed')
            assert sorted(child.config()) == CONFIG_KEYS
            assert child.config() == inline.config()
            assert (masked(child_out, child.root)
                    == masked(inline_out, inline.root))
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
        output = project.run('--gate', 'signed')
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
            assert asked(done.stdout) == [COMMIT], done.stdout
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
        project.run('--gate', 'signed')
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
            out = _answering(made, 'y\n', '--gate', 'signed')
            assert (scaffold_module.MUTATION_QUESTION % 'mutmut' + ' [y/N] '
                    in out), out
            assert made.config()['mutation_engine'] == 'auto'
            assert '[mutmut]' in read(made.path('setup.cfg'))
        finally:
            made.close()

    # purlin: scaffold PROOF-81
    def test_no_turns_it_off_and_wires_nothing(self):
        made = Project('pytest')
        try:
            _answering(made, 'n\n', '--gate', 'signed')
            assert made.config()['mutation_engine'] == 'none'
            assert not made.has('setup.cfg')
            assert 'mutants/' not in read(made.path('.gitignore'))
        finally:
            made.close()

    # purlin: scaffold PROOF-82
    def test_at_signed_a_framework_with_no_engine_is_told_why(self):
        made = Project('shell')
        try:
            out = _answering(made, '\n', '--gate', 'signed')
            assert 'Measure test strength' not in out, out
            assert made.config()['mutation_engine'] == 'none'
            assert ('Mutation testing is off: no engine breaks shell code, so '
                    'the AI audit alone judges test strength.'
                    in unprompted(out)), out
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

    # purlin: scaffold PROOF-127
    def test_on_windows_a_pytest_project_is_told_mutmut_does_not_run(
            self, project, monkeypatch):
        mutation = scaffold_module.mutation_module
        monkeypatch.setattr(mutation, 'runs_here', functools.partial(
            mutation.runs_here, os_name='windows'))
        output = project.run('--gate', 'signed')
        assert 'Measure test strength' not in output, output
        assert project.config()['mutation_engine'] == 'none'
        assert ('Mutation testing is off: mutmut does not run on Windows, so '
                'the AI audit alone judges test strength.'
                in output.splitlines()), output

    # purlin: scaffold PROOF-84
    def test_a_value_the_config_carries_is_kept_without_asking(self, project):
        write(project.path('.purlin/config.json'),
              json.dumps({'mutation_engine': 'auto'}) + '\n')
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', project.root,
             '--gate', 'signed'], capture_output=True, encoding='utf-8',
            timeout=300, stdin=subprocess.DEVNULL)
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'Measure test strength' not in done.stdout, done.stdout
        assert project.config()['mutation_engine'] == 'auto'

    # purlin: scaffold PROOF-46
    def test_yes_leaves_it_off(self, project):
        output = project.run('--gate', 'signed')
        assert ('Measure test strength by breaking the code on purpose? It '
                'needs mutmut and takes minutes to hours per run. [y/N] n'
                in output.splitlines()), output
        assert project.config()['mutation_engine'] == 'none'
        assert not project.has('setup.cfg')

    # purlin: scaffold PROOF-85
    def test_yes_with_no_gate_takes_passed(self, project):
        output = project.run()
        assert '[passed]: passed' in output.splitlines(), output
        assert project.config()['gate'] == 'passed'

    # purlin: scaffold PROOF-86
    def test_the_flag_turns_it_on_without_asking(self, project):
        output = project.run('--gate', 'passed', '--mutation')
        assert 'Measure test strength' not in output
        assert project.config()['mutation_engine'] == 'auto'
        assert '[mutmut]' in read(project.path('setup.cfg'))

    # purlin: scaffold PROOF-170
    def test_no_minimum_is_written_with_mutation_on(self, project):
        project.run('--gate', 'signed', '--mutation')
        config = project.config()
        assert config['mutation_engine'] == 'auto'
        assert 'min_strength' not in config, config


class TestTheEvidenceFolder:

    # purlin: scaffold PROOF-47
    # purlin: scaffold PROOF-136
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

    # purlin: scaffold PROOF-162
    def test_a_second_setup_keeps_the_dashboard_page_as_it_is(self, project):
        project.run('--gate', 'passed')
        page = project.path('purlin-report.html')
        with open(page, 'ab') as handle:
            handle.write(b'<!-- changed by hand -->\n')
        with open(page, 'rb') as handle:
            changed = handle.read()
        again = project.run('--gate', 'passed')
        with open(page, 'rb') as handle:
            assert handle.read() == changed
        assert 'kept purlin-report.html' in again.splitlines(), again

    # purlin: scaffold PROOF-150
    def test_at_passed_the_readme_names_no_audit(self, project):
        project.run('--gate', 'passed')
        text = read(project.path(README))
        assert not re.search(r'\baudit', text, re.I), text

    # purlin: scaffold PROOF-151
    def test_the_readme_opens_on_what_a_run_leaves(self, project):
        project.run('--gate', 'passed')
        heading, body = read(project.path(README)).split('\n\n', 2)[:2]
        assert heading == '# Evidence'
        assert ' '.join(body.split()).startswith(
            "What a run leaves behind for each feature: each proof's result "
            'on each operating system, the commit and the time.'), body


README = '.purlin/evidence/README.md'


class TestTheAnchorsFolder:

    # purlin: scaffold PROOF-89
    def test_no_folder_for_anchors_is_made(self, project):
        output = project.run('--gate', 'signed')
        assert os.path.isdir(project.path('specs'))
        assert not os.path.exists(project.path('specs/_anchors'))
        assert 'specs/_anchors' not in output, output


class TestASettingsFileThatCannotBeRead:

    # purlin: scaffold PROOF-128
    def test_it_stops_setup_and_nothing_is_written(self, project):
        broken = '{\n  "gate": "passed",\n  "tests": [],\n}\n'
        write(project.path('.purlin/config.json'), broken)
        # The cause is the JSON reader's own words and line, which differ
        # between Python releases.
        try:
            json.loads(broken)
        except ValueError as error:
            cause = '%s at line %d' % (error.msg, error.lineno)
        before = tree(project.root)
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', project.root,
             '--gate', 'signed'], capture_output=True, encoding='utf-8',
            timeout=300, stdin=subprocess.DEVNULL)
        assert done.returncode == 1, done.stdout + done.stderr
        assert ('.purlin/config.json cannot be read: %s. Fix the file by '
                'hand; nothing ran and nothing was saved.' % cause
                in (done.stdout + done.stderr).splitlines()), (
            done.stdout + done.stderr)
        assert tree(project.root) == before


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
    def test_a_vitest_project_is_told_how_to_install_stryker(self):
        assert _stryker_lines('vitest', 'passed') == [
            'vitest: stryker is not installed: run "npm install --save-dev '
            '@stryker-mutator/core"']

    # purlin: scaffold PROOF-105
    def test_a_jest_project_is_told_how_to_install_stryker(self):
        assert _stryker_lines('jest', 'signed') == [
            'jest: stryker is not installed: run "npm install --save-dev '
            '@stryker-mutator/core"']

    # purlin: scaffold PROOF-106
    def test_a_csharp_project_with_no_dotnet_is_told_to_install_it(self):
        assert _stryker_lines('dotnet', 'signed') == [
            'dotnet: dotnet is not installed: install the .NET SDK, then run '
            '"dotnet tool install -g dotnet-stryker"']

    # purlin: scaffold PROOF-139
    def test_a_csharp_project_with_no_stryker_tool_is_told_to_add_it(self):
        # A `dotnet` that answers `dotnet stryker --version` with a failure,
        # as one with no Stryker tool installed does.
        assert _stryker_lines('dotnet', 'signed', stand_in='dotnet') == [
            'dotnet: dotnet stryker is not installed: run "dotnet tool install '
            '-g dotnet-stryker"']

    # purlin: scaffold PROOF-140
    def test_an_installed_stryker_prints_no_line(self):
        name = 'stryker.cmd' if os.name == 'nt' else 'stryker'
        assert _stryker_lines('jest', 'signed', local=name) == []


def _nothing_in_the_node_suite(language, wiring):
    """A Node project set up at `passed` holds no runner file of Purlin's."""
    made = Project(language)
    try:
        output = made.run('--gate', 'passed')
        assert not made.has(wiring), output
        assert wiring not in summary_paths(output)
    finally:
        made.close()


def _stand_in(folder, name, body_posix, body_windows):
    """A program on the search path that does what `body` says: on POSIX a
    file with the exec bit, on Windows `<name>.cmd`."""
    if os.name == 'nt':
        with open(os.path.join(folder, name + '.cmd'), 'wb') as handle:
            handle.write(body_windows)
    else:
        path = os.path.join(folder, name)
        write(path, body_posix)
        os.chmod(path, 0o755)


def _stryker_lines(language, gate, stand_in=None, local=None):
    """The lines naming `language` that a set-up with the breaks on prints.

    The search path holds git's own folder and nothing else of Stryker's,
    plus a `stand_in` program that fails whatever it is asked; `local` puts
    a Stryker into the project's own `node_modules/.bin/`.
    """
    git_dir = os.path.dirname(shutil.which('git'))
    for program in ('stryker', 'dotnet'):
        assert shutil.which(program, path=git_dir) is None, (git_dir, program)
    made = Project(language)
    bin_dir = os.path.realpath(tempfile.mkdtemp(prefix='purlin-bin-'))
    try:
        if stand_in:
            _stand_in(bin_dir, stand_in, '#!/bin/sh\nexit 1\n',
                      b'@exit /b 1\r\n')
        if local:
            write(made.path('node_modules/.bin/' + local), '')
            os.chmod(made.path('node_modules/.bin/' + local), 0o755)
        output = made.run('--gate', gate, '--mutation',
                          env={'PATH': bin_dir + os.pathsep + git_dir})
        return [line for line in output.splitlines()
                if line.startswith(language + ':')]
    finally:
        shutil.rmtree(bin_dir, ignore_errors=True)
        made.close()


# ---------------------------------------------------------------------------
# Test fixtures are not the project's tools
# ---------------------------------------------------------------------------

CSHARP_TESTS = ('<Project><ItemGroup><PackageReference Include="xunit" '
                'Version="2.6.0" /></ItemGroup></Project>')


def _python_setup_with(files):
    """A pytest project that also holds `files`, set up at `signed` with the
    breaks on and nothing but git's own folder on the search path: `(the
    output, setup.cfg as written or '')`."""
    git_dir = os.path.dirname(shutil.which('git'))
    made = Project('pytest')
    try:
        for rel, body in files.items():
            write(made.path(rel), body)
        output = made.run('--gate', 'signed', '--mutation',
                          env={'PATH': git_dir})
        cfg = read(made.path('setup.cfg')) if made.has('setup.cfg') else ''
        return output, cfg
    finally:
        made.close()


def _naming(output, *words):
    """The lines of `output` that hold any of `words`, in any case."""
    return [line for line in output.splitlines()
            if any(word in line.lower() for word in words)]


class TestFixturesAreNotTheProjectsTools:

    # purlin: scaffold PROOF-163
    def test_a_csharp_project_under_dev_fixtures_is_left_out(self):
        output, cfg = _python_setup_with(
            {'dev/fixtures/app/App.Tests.csproj': CSHARP_TESTS})
        assert _naming(output, 'dotnet', 'stryker') == [], output
        if scaffold_module.mutation_module.runs_here('mutmut'):
            assert '[mutmut]' in cfg, output
        else:
            assert scaffold_module.NO_ENGINE_HERE in output.splitlines()

    # purlin: scaffold PROOF-164
    def test_a_csharp_project_at_the_root_keeps_its_dotnet_line(self):
        output, _cfg = _python_setup_with({'App.Tests.csproj': CSHARP_TESTS})
        assert ('dotnet: dotnet is not installed: install the .NET SDK, then '
                'run "dotnet tool install -g dotnet-stryker"'
                in output.splitlines()), output

    # purlin: scaffold PROOF-165
    def test_a_javascript_sample_is_left_out(self):
        output, _cfg = _python_setup_with({
            'samples/web/package.json':
                '{"devDependencies": {"jest": "^29.0.0"}}',
            'samples/web/jest.config.js': 'module.exports = {};\n',
            'samples/web/sum.test.js': 'test("sum", () => {});\n'})
        assert _naming(output, 'jest', 'vitest', 'stryker') == [], output

    # purlin: scaffold PROOF-166
    @pytest.mark.parametrize('folder', ['fixtures', 'fixture', 'samples',
                                        'sample', 'testdata', 'test_data',
                                        'test-data'])
    def test_each_fixture_folder_name_is_left_out_at_any_depth(self, folder):
        output, _cfg = _python_setup_with(
            {'src/%s/app/App.Tests.csproj' % folder: CSHARP_TESTS})
        assert _naming(output, 'dotnet', 'stryker') == [], output


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
        project.run('--gate', 'signed')
        assert not project.has('.github/workflows/purlin.yml')
        assert project.config()['gate'] == 'signed'

    # purlin: scaffold PROOF-62
    def test_raising_to_signed_keeps_the_workflow(self, project):
        tag_foreign(project)
        project.run('--gate', 'passed')
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
        assert project.has('.github/workflows/purlin.yml')
        assert changed_since(before, tree(project.root)) == [
            '.purlin/config.json', REPORT_DATA]

    # purlin: scaffold PROOF-20
    # purlin: scaffold PROOF-131
    def test_a_second_run_at_the_same_gate_changes_nothing(self, project):
        project.run('--gate', 'signed')
        files = tree(project.root)
        output = project.run('--gate', 'signed')
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
        output = project.run('--gate', 'signed')
        assert not project.has('.github/workflows/purlin.yml')
        assert ('skipped the runner file (every proof runs on this operating '
                'system, so nothing has to run remotely)'
                in output.splitlines()), output

    # purlin: scaffold PROOF-141
    def test_at_passed_the_skip_line_says_every_test(self, project):
        output = project.run('--gate', 'passed')
        assert not project.has('.github/workflows/purlin.yml')
        assert ('skipped the runner file (every test runs on this operating '
                'system, so nothing has to run remotely)'
                in output.splitlines()), output

    # purlin: scaffold PROOF-64
    # purlin: scaffold PROOF-129
    def test_at_passed_the_reason_names_the_test(self, project):
        named = system_word(tag_foreign(project))
        output = project.run('--gate', 'passed')
        assert project.has('.github/workflows/purlin.yml'), output
        assert reasons_under_heading(output) == [
            '  A test is tagged @env for %s, which this machine is not, so '
            'only a runner can run it.' % named], output

    # purlin: scaffold PROOF-65
    def test_at_signed_the_reason_names_the_proof(self, project):
        named = system_word(tag_foreign(project))
        output = project.run('--gate', 'signed')
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
        output = project.run('--gate', 'signed')
        assert reasons_under_heading(output) == [
            '  Proofs in specs/ are tagged @env for %s and %s, which this '
            'machine is not, so only a runner can prove them.'
            % tuple(system_word(name) for name in others)], output

    # purlin: scaffold PROOF-66
    def test_with_no_remote_nothing_is_written(self):
        made = Project('pytest', host=None)
        try:
            tag_foreign(made)
            output = made.run('--gate', 'signed')
            assert not made.has('.github/workflows/purlin.yml')
            assert ('skipped the runner file (there is no git remote, so '
                    'there is no runner to read it)'
                    in output.splitlines()), output
        finally:
            made.close()

    # purlin: scaffold PROOF-142
    def test_with_no_remote_no_heading_is_printed(self):
        made = Project('pytest', host=None)
        try:
            tag_foreign(made)
            output = made.run('--gate', 'signed')
            assert ('A remote runner is written because:'
                    not in output.splitlines()), output
        finally:
            made.close()

    # purlin: scaffold PROOF-143
    def test_with_a_prerequisite_missing_no_heading_is_printed(self):
        made = Project('pytest', remote='https://git.example.com/acme/x.git')
        try:
            tag_foreign(made)
            output = made.run('--gate', 'signed')
            assert not made.has('.github/workflows/purlin.yml'), output
            assert ('A remote runner is written because:'
                    not in output.splitlines()), output
        finally:
            made.close()

    # purlin: scaffold PROOF-44
    def test_a_missing_prerequisite_is_named_and_nothing_is_written(self):
        made = Project('pytest', remote='https://example.invalid/x.git')
        try:
            tag_foreign(made)
            output = made.run('--gate', 'signed')
            assert not made.has('.github/workflows/purlin.yml')
            lines = output.splitlines()
            assert lines.count(UNKNOWN_HOST) == 1, output
            assert lines.index(
                'skipped the runner file (a prerequisite is missing)') > (
                lines.index(UNKNOWN_HOST)), output
        finally:
            made.close()

    # purlin: scaffold PROOF-144
    def test_under_the_runner_file_it_names_where_it_runs(self, project):
        named = tag_foreign(project)
        lines = project.run('--gate', 'signed').splitlines()
        at = lines.index('wrote .github/workflows/purlin.yml')
        assert lines[at + 1] == (
            '  it runs on %s-latest, the systems a proof in specs/ is tagged '
            '@env for that this machine is not.' % named), lines

    # purlin: scaffold PROOF-145
    def test_under_the_runner_file_it_names_its_triggers(self, project):
        tag_foreign(project)
        lines = project.run('--gate', 'signed').splitlines()
        assert ('  it runs on a push to a run/* branch and on a push of a '
                'signed/* tag.' in lines), lines

    # purlin: scaffold PROOF-77
    def test_a_remote_with_no_branch_yet_still_gets_the_workflow(self):
        made = Project('pytest', host=None)
        bare = os.path.realpath(tempfile.mkdtemp(prefix='purlin-empty-remote-'))
        try:
            tag_foreign(made)
            url = os.path.join(bare, 'github-origin.git')
            git(bare, 'init', '--bare', '-q', '-b', 'main', url)
            git(made.root, 'remote', 'add', 'origin', url)
            output = made.run('--gate', 'signed')
            assert made.has('.github/workflows/purlin.yml'), output
            assert summary_paths(output)[
                '.github/workflows/purlin.yml'] == 'wrote', output
        finally:
            shutil.rmtree(bare, ignore_errors=True)
            made.close()

    # purlin: scaffold PROOF-78
    # purlin: scaffold PROOF-135
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
            output = made.run('--gate', 'signed')
            assert made.has('purlin.azure-pipelines.yml'), output
            assert 'wrote purlin.azure-pipelines.yml' in output.splitlines()
            assert not made.has('.github/workflows/purlin.yml'), output
        finally:
            made.close()

    # purlin: scaffold PROOF-15
    def test_the_matrix_names_only_the_systems_this_machine_is_not(
            self, project):
        tag_foreign(project, 'windows', 'macos')
        project.run('--gate', 'signed')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        # On a Mac the one foreign system is Windows; on Windows, macOS.
        matrix = {'macos': 'windows-latest', 'windows': 'macos-latest'}.get(
            scaffold_module.evidence_module.host_os(),
            'macos-latest, windows-latest')
        assert '        os: [%s]\n' % matrix in workflow, workflow

    # purlin: scaffold PROOF-72
    def test_one_foreign_system_is_the_whole_matrix(self, project):
        named = tag_foreign(project)
        project.run('--gate', 'signed')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert '        os: [%s-latest]\n' % named in workflow, workflow
        assert 'ubuntu-latest' not in workflow, workflow

    # purlin: scaffold PROOF-73
    def test_the_purlin_release_is_pinned(self, project):
        tag_foreign(project)
        project.run('--gate', 'signed')
        version = read(os.path.join(ROOT, 'VERSION')).strip()
        assert 'v%s' % version in read(
            project.path('.github/workflows/purlin.yml'))

    # purlin: scaffold PROOF-42
    def test_the_triggers_are_a_run_branch_and_the_signing_tag(self, project):
        tag_foreign(project)
        project.run('--gate', 'signed')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        block = workflow.split('\non:\n', 1)[1].split('\npermissions:', 1)[0]
        assert block == ("  push:\n    branches: ['run/**']\n"
                         "    tags: ['signed/**']\n")

    # purlin: scaffold PROOF-74
    def test_the_last_step_is_the_test_run(self, project):
        tag_foreign(project)
        project.run('--gate', 'signed')
        workflow = read(project.path('.github/workflows/purlin.yml'))
        assert workflow.rstrip().endswith(
            'scripts/run/purlin_run.py" --all --ci'), workflow

    # purlin: scaffold PROOF-75
    def test_the_azure_pipeline_has_the_same_triggers(self):
        made = Project('pytest',
                       remote='https://dev.azure.com/acme/demo/_git/demo')
        try:
            tag_foreign(made)
            made.run('--gate', 'signed')
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
            made.run('--gate', 'signed')
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

    The search path holds git's own folder and, where `installed`, a
    stand-in `tool`, so which of the two lines prints is decided by that
    alone. The stand-in is found the way the real program is: on POSIX a
    file with the exec bit, on Windows `<tool>.cmd`.
    """
    git_dir = os.path.dirname(shutil.which('git'))
    assert shutil.which(tool, path=git_dir) is None, (
        'git\'s own folder %s holds %s' % (git_dir, tool))
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
        if installed:
            if os.name == 'nt':
                # Bytes, so text mode adds no second carriage return.
                with open(os.path.join(bin_dir, tool + '.cmd'), 'wb') as handle:
                    handle.write(b'@echo off\r\n')
            else:
                stand_in = os.path.join(bin_dir, tool)
                write(stand_in, '#!/bin/sh\n')
                os.chmod(stand_in, 0o755)
        output = made.run('--gate', 'signed',
                          env={'PATH': bin_dir + os.pathsep + git_dir})
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
        output = made.run('--gate', 'signed')
        assert ('Gate signed. Suites none. Git host %s.' % host
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
            lines = made.run('--gate', 'signed').splitlines()
            at = lines.index('Gate signed. Suites none.')
            assert lines[at + 1] == UNKNOWN_HOST, lines
            assert made.config()['ci'] == 'none'
        finally:
            made.close()

    # purlin: scaffold PROOF-70
    def test_no_remote_reads_no_host(self):
        made = Project('pytest', host=None)
        try:
            assert git(made.root, 'remote').stdout == ''
            lines = made.run('--gate', 'signed').splitlines()
            at = lines.index('Gate signed. Suites none.')
            assert lines[at + 1] == 'No git host found.', lines
            assert made.config()['ci'] == 'none'
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Everything else init writes
# ---------------------------------------------------------------------------

class TestWhatInitWrites:

    # purlin: scaffold PROOF-18
    def test_the_summary_names_the_four_files_it_writes(self, project):
        output = project.run('--gate', 'signed')
        named = summary_paths(output)
        for rel in ('.purlin/config.json', '.gitignore',
                    '.purlin/evidence/README.md', 'purlin-report.html'):
            assert named.get(rel) in ('wrote', 'copied'), output
            assert project.has(rel), rel

    # purlin: scaffold PROOF-108
    def test_what_appears_is_exactly_what_the_summary_wrote(self, project):
        before = tree(project.root)
        output = project.run('--gate', 'signed')
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

    # purlin: scaffold PROOF-146
    def test_the_gitignore_is_named_once(self, project):
        output = project.run('--gate', 'signed', '--mutation')
        assert 'mutants/' in read(project.path('.gitignore'))
        # The lines naming each file end where the commit's list begins.
        summary = output.split('\nCommitted ', 1)[0].splitlines()
        named = [line for line in summary
                 if re.search(r'(^|\s)\.gitignore\b', line)]
        assert named == ['wrote .gitignore'], output

    # purlin: scaffold PROOF-153
    def test_the_gitignore_names_the_dashboard_page(self, project):
        project.run('--gate', 'passed')
        assert '/purlin-report.html' in read(
            project.path('.gitignore')).splitlines()

    # purlin: scaffold PROOF-154
    def test_the_gitignore_names_the_runtime_folder(self, project):
        project.run('--gate', 'passed')
        assert '.purlin/runtime/' in read(
            project.path('.gitignore')).splitlines()

    # purlin: scaffold PROOF-155
    def test_each_ignored_entry_has_its_comment_above_it(self, project):
        project.run('--gate', 'passed')
        lines = read(project.path('.gitignore')).splitlines()
        for comment, entry in (
                ('# Purlin runtime: the test reports and the run log, never '
                 'committed', '.purlin/runtime/'),
                ('# Dashboard HTML (copied by purlin:init and refreshed by '
                 'purlin:init --update)', '/purlin-report.html'),
                ('# Dashboard data, regenerated locally, never committed',
                 '.purlin/report-data.js')):
            assert lines[lines.index(entry) - 1] == comment, lines

    # purlin: scaffold PROOF-156
    def test_the_gitignore_says_the_evidence_is_tracked(self, project):
        project.run('--gate', 'passed')
        text = read(project.path('.gitignore'))
        assert ('# .purlin/evidence/ and .purlin/tests.md are tracked on '
                'purpose: they are\n# the evidence of each run, for somebody '
                'who did not make it to read.\n' in text), text

    # purlin: scaffold PROOF-19
    # purlin: scaffold PROOF-130
    def test_the_gitignore_block_is_added_once(self, project):
        # The project's own file ends its line the way this system's editors
        # do: a carriage return and a line feed on Windows.
        ending = b'\r\n' if os.name == 'nt' else b'\n'
        with open(project.path('.gitignore'), 'wb') as handle:
            handle.write(b'node_modules/' + ending)
        project.run('--gate', 'passed')
        first = tree(project.root)['.gitignore']
        project.run('--gate', 'passed')
        # Byte for byte, so a line ending the second run rewrote is seen.
        assert tree(project.root)['.gitignore'] == first
        text = first.decode('utf-8')
        assert text.splitlines()[0] == 'node_modules/', text
        assert '.purlin/runtime/' in text
        assert text.count('.purlin/report-data.js') == 1, text

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
    def test_with_no_spec_over_code_it_ends_on_spec_from_code(self, project):
        lines = project.run('--gate', 'passed').strip().splitlines()
        assert lines[-2:] == [
            'No specs found under specs/.',
            '→ Run: purlin:spec-from-code to write the specs this code '
            'already implies.'], lines

    # purlin: scaffold PROOF-137
    def test_with_no_spec_and_no_code_it_sends_you_to_write_one(self):
        made = Project(language=None)
        try:
            lines = made.run('--gate', 'passed').strip().splitlines()
        finally:
            made.close()
        assert lines[-2:] == [
            'No specs found under specs/.',
            '→ Run: purlin:spec <name> to write the first spec.'], lines

    # purlin: scaffold PROOF-80
    def test_with_a_spec_it_ends_on_what_is_left_to_do(self, project):
        project.spec()
        lines = project.run('--gate', 'passed').strip().splitlines()
        assert lines[-3:] == ['1 rule. 0 pass their tests.', 'Left to do:',
                              '  1 rule to write a test for: purlin:build'], (
            lines)


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
# The commit setup asks for
# ---------------------------------------------------------------------------

def head(root):
    return git(root, 'rev-parse', 'HEAD').stdout.strip()


class TestTheCommit:

    # purlin: scaffold PROOF-157
    def test_with_no_answer_nothing_is_committed(self, project):
        before = head(project.root)
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', project.root,
             '--gate', 'passed'], capture_output=True, encoding='utf-8',
            timeout=300, stdin=subprocess.DEVNULL)
        assert done.returncode == 0, done.stdout + done.stderr
        lines = done.stdout.splitlines()
        at = lines.index('Commit the files setup wrote? [y/N] ')
        assert lines[at - 1].startswith('skipped the runner file ('), lines
        assert not [line for line in lines if line.startswith('Committed')]
        assert head(project.root) == before

    # purlin: scaffold PROOF-158
    def test_yes_commits_the_files_and_names_them(self, project):
        output = project.run('--gate', 'passed')
        assert COMMIT not in output, output
        assert git(project.root, 'log', '-1', '--format=%s').stdout.strip() \
            == 'chore(init): set up Purlin at the gate passed'
        lines = output.splitlines()
        at = lines.index('Committed %s, the files setup wrote:'
                         % head(project.root)[:7])
        assert lines[at + 1:at + 4] == [
            '  .purlin/config.json', '  .gitignore',
            '  .purlin/evidence/README.md'], lines

    # purlin: scaffold PROOF-159
    def test_a_file_already_staged_stays_out_of_the_commit(self, project):
        write(project.path('notes.txt'), 'ours\n')
        git(project.root, 'add', 'notes.txt')
        project.run('--gate', 'passed')
        committed = git(project.root, 'show', '--name-only', '--format=',
                        'HEAD').stdout.split()
        assert sorted(committed) == ['.gitignore', '.purlin/config.json',
                                     '.purlin/evidence/README.md'], committed
        assert git(project.root, 'diff', '--cached',
                   '--name-only').stdout.split() == ['notes.txt']

    # purlin: scaffold PROOF-160
    def test_a_project_with_no_commit_gets_setup_s_as_its_first(self):
        made = Project('pytest', host=None)
        try:
            assert git(made.root, 'rev-parse', 'HEAD').returncode != 0
            made.run('--gate', 'passed')
            assert git(made.root, 'log', '--format=%s').stdout.splitlines() \
                == ['chore(init): set up Purlin at the gate passed']
        finally:
            made.close()

    # purlin: scaffold PROOF-161
    def test_git_refusing_leaves_the_files_staged_and_says_so(self):
        made = Project('pytest', host=None)
        empty = os.path.realpath(tempfile.mkdtemp(prefix='purlin-gitcfg-'))
        try:
            # No author git can find: none in the project, none in a global
            # or system file, none in the environment, and no guessing.
            git(made.root, 'config', '--unset', 'user.email')
            git(made.root, 'config', '--unset', 'user.name')
            git(made.root, 'config', 'user.useConfigOnly', 'true')
            global_config = os.path.join(empty, 'gitconfig')
            write(global_config, '')
            env = {key: value for key, value in os.environ.items()
                   if key not in ('CLAUDE_PLUGIN_ROOT', 'EMAIL')
                   and not key.startswith(('GIT_AUTHOR_', 'GIT_COMMITTER_'))}
            env.update(GIT_CONFIG_GLOBAL=global_config, GIT_CONFIG_NOSYSTEM='1')
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', made.root,
                 '--gate', 'passed', '--yes'], capture_output=True,
                encoding='utf-8', timeout=300, env=env,
                stdin=subprocess.DEVNULL)
            assert done.returncode == 0, done.stdout + done.stderr
            assert ('The files setup wrote are staged and not committed: no '
                    'email was given and auto-detection is disabled.'
                    in done.stdout.splitlines()), done.stdout
            assert '.purlin/config.json' in git(
                made.root, 'diff', '--cached', '--name-only').stdout.split()
        finally:
            shutil.rmtree(empty, ignore_errors=True)
            made.close()


# ---------------------------------------------------------------------------
# The flags
# ---------------------------------------------------------------------------

class TestTheFlags:

    # purlin: scaffold PROOF-31
    def test_outside_a_repository_a_real_run_refuses(self):
        directory = tempfile.mkdtemp(prefix='purlin-nogit-')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', directory,
                 '--gate', 'passed', '--yes'], capture_output=True, encoding='utf-8',
                timeout=300, stdin=subprocess.DEVNULL)
            assert done.returncode == 2
            assert done.stderr == ('This is not a git repository. Run git '
                                   'init, then purlin:init.\n'), done.stderr
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
    # purlin: scaffold PROOF-133
    def test_the_copy_sets_a_project_up_the_same_way(self):
        cache, installed = self.copy_plugin()
        made = Project('pytest')
        try:
            tag_foreign(made)
            output = made.run('--gate', 'signed',
                              script=os.path.join(installed, 'scripts', 'init',
                                                  'scaffold.py'),
                              env={'CLAUDE_PLUGIN_ROOT': installed})
            assert made.has('.github/workflows/purlin.yml'), output
            # The same project set up from this checkout ends the same, file
            # for file and line for line.
            here = Project('pytest')
            try:
                tag_foreign(here)
                ours = here.run('--gate', 'signed', subprocess=True)
                theirs, mine = tree(made.root), tree(here.root)
                for files in (theirs, mine):
                    files.pop(REPORT_DATA, None)
                assert theirs == mine
                assert masked(output, made.root) == masked(ours, here.root)
            finally:
                here.close()
        finally:
            made.close()
            shutil.rmtree(cache, ignore_errors=True)

    # purlin: scaffold PROOF-21
    # purlin: scaffold PROOF-132
    def test_nothing_a_project_holds_names_the_plugin(self):
        cache, installed = self.copy_plugin()
        made = Project('pytest')
        try:
            made.run('--gate', 'signed',
                     script=os.path.join(installed, 'scripts', 'init',
                                         'scaffold.py'),
                     env={'CLAUDE_PLUGIN_ROOT': installed})
            # The copy's path as a file could hold it: with `\`, with `/`,
            # and with each `\` doubled as JSON writes it. On a Mac the three
            # are one path.
            spellings = {installed, installed.replace('\\', '/'),
                         installed.replace('\\', '\\\\')}
            for base, _dirs, names in os.walk(made.root):
                if '.git' in base.split(os.sep):
                    continue
                for name in names:
                    path = os.path.join(base, name)
                    try:
                        text = read(path)
                    except (UnicodeDecodeError, OSError):
                        continue
                    for spelled in spellings:
                        assert spelled not in text, (path, spelled)
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

    # purlin: scaffold PROOF-147
    def test_a_project_set_up_from_this_checkout_does_not_name_it(self):
        """This checkout is what `claude --plugin-dir` loads."""
        made = Project('pytest')
        try:
            made.run('--gate', 'signed', subprocess=True)
            spellings = {ROOT, ROOT.replace('\\', '/'),
                         ROOT.replace('\\', '\\\\')}
            files = tree(made.root)
            assert [rel for rel, body in files.items() if body is not None
                    and any(spelled.encode('utf-8') in body
                            for spelled in spellings)] == [], ROOT
        finally:
            made.close()

    # purlin: scaffold PROOF-23
    # purlin: scaffold PROOF-134
    def test_no_project_file_points_at_the_repository_s_own_dev_folder(self):
        made = Project('pytest')
        try:
            made.run('--gate', 'signed')
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
                    # Windows spells the folder with `\`.
                    assert '\\dev\\' not in text, path
                    # Nor a relative path into it, such as `dev/test_x.py` or
                    # `dev\test_x.py`.
                    assert not re.search(r'(?<![\w./\\-])dev[/\\]', text), path
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

    # purlin: scaffold PROOF-148
    def test_a_nested_tests_folder_is_the_selection_and_bench_is_not(
            self, project):
        shutil.rmtree(project.path('tests'), ignore_errors=True)
        write(project.path('pkg/core.py'), 'def go():\n    return 1\n')
        write(project.path('pkg/tests/test_a.py'), 'def test_a():\n    pass\n')
        write(project.path('bench/test_b.py'), 'def test_b():\n    pass\n')
        assert _mutmut_block(project) == _block_naming('pkg', 'pkg/tests')

    # purlin: scaffold PROOF-149
    def test_docs_and_examples_are_not_source(self, project):
        write(project.path('demo/__init__.py'), '')
        write(project.path('doc/conf.py'), 'project = "demo"\n')
        write(project.path('examples/x.py'), 'print(1)\n')
        assert _mutmut_block(project) == _block_naming('demo', 'tests')

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

SUGGESTED = 'Suggested tests setting: '


def take_the_suggestion(root, output):
    """Write the setting a first test run suggested, as `purlin:test` does."""
    (line,) = [line for line in output.splitlines()
               if line.startswith(SUGGESTED)]
    path = root / '.purlin' / 'config.json'
    config = json.loads(path.read_text(encoding='utf-8'))
    config['tests'] = json.loads(line[len(SUGGESTED):])
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
# suggests, `purlin:test --commit`, the audit, a runner's two kinds of run,
# the release at `passed`, init at `signed`, the release there, and
# `purlin:sign`, which writes the signed tag.
# Every step's output is kept, and each case below reads the one step it is
# about. Nothing here reaches a git host: the remote is a bare repository on
# disk, and no token is set.

RUN_SCRIPT = os.path.join(ROOT, 'scripts', 'run', 'purlin_run.py')
# The last line a finished project prints at `passed` before its release.
TO_RELEASE = 'Nothing left to do. To release a version: purlin:test --release'
SIGN_SCRIPT = os.path.join(ROOT, 'scripts', 'review', 'sign.py')

GREETING_SPEC = """# Feature: greeting

> Scope: %s
> Description: One rule, walked from its first test run to the signed tag.

## Rules

- RULE-1: `greet(name)` returns `Hello, <name>!`

## Proof

- PROOF-1 (RULE-1): `greet("Ada")` returns exactly `Hello, Ada!` @env(%s)
"""

# The greeting proof is tagged for the system this machine is, so a person's
# run here proves it and a runner's `--ci` run on this system writes a
# section for it; no workflow is written for this machine's own system.
HERE_OS = scaffold_module.evidence_module.host_os()

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
    write(walk.path('specs/core/greeting.md'),
          GREETING_SPEC % (shape['scope'], HERE_OS))
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

    walk.purlin('release at passed', '--release')
    walk.facts['tags at passed'] = walk.git('tag', '-l').splitlines()

    walk.init('init at signed', 'signed')
    walk.commit_all('raise the gate to signed')
    walk.purlin('release at signed', '--release')
    walk.facts['tags at signed'] = walk.git('tag', '-l').splitlines()
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
    # The agent's second step: every stop answered, the strong list passed.
    answers = walk.path('.purlin/runtime/signoff-answers.json')
    write(answers, json.dumps({'strong': 'go on', 'stops': {},
                               'sign': True}))
    walk.sign('sign the release', '--answers', answers)
    walk.facts['signed commit'] = git(walk.root, 'cat-file', 'commit',
                                      'HEAD').stdout
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
    (entry,) = json.loads(line[len(SUGGESTED):])
    return entry['name']


class TestEachLanguageIsSetUp:

    # purlin: scaffold PROOF-37
    def test_a_python_project_runs_its_marked_test(self, python_walk):
        walk = python_walk
        assert walk.facts['tests after init'] == []
        assert 'conftest.py' not in walk.facts['files after init']
        assert suggested_name(walk) == 'pytest', walk.out['first test run']
        assert walk.last_lines('test run', 2) == [
            '1 rule. 1 passes its tests.', TO_RELEASE], (
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
            '1 rule. 1 passes its tests.', TO_RELEASE], (
            walk.out['test run'])

    # purlin: scaffold PROOF-95
    def test_a_csharp_project_runs_its_marked_test(self, csharp_project):
        walk = csharp_project
        assert walk.facts['tests after init'] == []
        assert suggested_name(walk) == 'dotnet', walk.out['first test run']
        assert walk.last_lines('test run', 2) == [
            '1 rule. 1 passes its tests.', TO_RELEASE], (
            walk.out['test run'])


class TestTheTwoGates:

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
        assert walk.last_lines('commit', 1) == [TO_RELEASE], (
            walk.out['commit'])

    # purlin: scaffold PROOF-117
    def test_the_audit_writes_into_the_evidence_and_commits_it(
            self, python_walk):
        walk = python_walk
        assert walk.facts['audited'] == ['RULE-1'], walk.out['audit']
        assert 'Evidence committed.' in walk.lines('audit'), walk.out['audit']
        assert walk.last_lines('audit', 2) == [
            '1 rule. 1 passes its tests. The audit found 1 strong and 0 weak.',
            TO_RELEASE], walk.out['audit']

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

    # purlin: scaffold PROOF-90
    def test_the_release_at_passed_writes_the_passed_tag(self, python_walk):
        walk = python_walk
        assert walk.code['release at passed'] == 0, (
            walk.out['release at passed'])
        assert 'passed/0.1.0' in walk.facts['tags at passed'], walk.facts
        assert walk.last_lines('release at passed', 1) == [
            'Nothing left to do. Push the tag to release it: git push origin '
            'passed/0.1.0'], walk.out['release at passed']

    # purlin: scaffold PROOF-92
    def test_the_release_at_signed_writes_no_tag(self, python_walk):
        walk = python_walk
        assert ('Run purlin:sign to sign it; the first signature writes '
                'signed/0.1.0.' in walk.lines('release at signed')), (
            walk.out['release at signed'])
        assert 'signed/0.1.0' not in walk.facts['tags at signed'], walk.facts

    # purlin: scaffold PROOF-119
    def test_the_sign_off_makes_a_signed_commit_naming_the_signer(
            self, python_walk):
        walk = python_walk
        assert walk.code['sign the release'] == 0, (
            walk.out['sign the release'])
        assert ('\ngpgsig ' in walk.facts['signed commit']), (
            walk.facts['signed commit'])
        assert ('Signed 0.1.0 as jane@acme.com with the key ending ...%s.'
                % walk.facts['key ending']
                in walk.lines('sign the release')), (
            walk.out['sign the release'])

    # purlin: scaffold PROOF-93
    def test_the_first_sign_off_writes_the_signed_tag(self, python_walk):
        walk = python_walk
        assert 'signed/0.1.0' in walk.facts['tags'], (
            walk.out['sign the release'])
        assert ('Nothing left to do. Push the tag to release it: git push '
                'origin signed/0.1.0' in walk.lines('sign the release')), (
            walk.out['sign the release'])
