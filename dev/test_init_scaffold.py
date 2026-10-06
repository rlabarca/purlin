"""Behavioural proofs for `scripts/init/scaffold.py`, the whole of init.

Every case drives the real script against a temp git project. Most call its
`main()` in this process; the cases that read what a person sees with nothing
to answer from, and the marketplace-copy cases, run it as a subprocess, the
way `purlin:init` reaches it. Nothing here re-implements what the script
does: the fixture builds a repository, the script writes, and the assertions
read what is on disk and what the summary said it wrote.

The two ways Purlin is loaded are both exercised. `claude --plugin-dir <this
checkout>` is the default every case runs under, and `TestTheMarketplacePath`
copies the plugin into a temp directory, points `CLAUDE_PLUGIN_ROOT` at the
copy and runs that copy's script, which is what an install from the
marketplace is.

The last section sets up a real python, typescript and C# project and runs
each one's marked test, and walks the python project from setup to the signed
tag with the commands a person runs, one case per step.
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
VERSION = open(os.path.join(ROOT, 'VERSION'), encoding='utf-8').read().strip()

sys.path.insert(0, os.path.join(ROOT, 'scripts', 'init'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
import scaffold as scaffold_module  # noqa: E402
from purlin import evidence as evidence_module  # noqa: E402

# What a project of each framework looks like on disk.
LANGUAGES = {
    'pytest': {'conftest.py': '', 'tests/test_x.py': 'def test_x(): pass\n'},
    'jest': {'package.json': '{"devDependencies": {"jest": "^29.0.0"}}'},
}

SPEC = """# Feature: login

> Scope: login.py
> Description: One rule, so a project has something for status to report on.

## Rules

- RULE-1: A person signs in with an email address and a password

## Proof

- PROOF-1 (RULE-1): Call `sign_in` with a known pair and verify it returns a session
"""

COMMIT = 'Commit the files setup wrote? [y/N] '
README = '.purlin/evidence/README.md'
# The dashboard's data file, which the status the run ends on refreshes
# wherever a spec exists.
REPORT_DATA = '.purlin/report-data.js'


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
        """A local bare repository standing in for the git host, holding the
        project's first commit."""
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
        """Init with `--yes` against this project, and what it printed."""
        argv = ['--project-root', self.root, '--yes'] + list(args)
        saved = dict(os.environ)
        os.environ.pop('CLAUDE_PLUGIN_ROOT', None)
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), \
                    contextlib.redirect_stderr(err):
                code = scaffold_module.main(argv)
        finally:
            os.environ.clear()
            os.environ.update(saved)
        assert (code or 0) == kwargs.get('code', 0), (
            out.getvalue() + err.getvalue())
        return out.getvalue()

    def child(self, *args, **kwargs):
        """The script as a subprocess with nothing on stdin: `(code, stdout,
        stderr)`. `script` runs a copied plugin's, `env` adds variables."""
        env = dict(os.environ)
        env.pop('CLAUDE_PLUGIN_ROOT', None)
        env.update(kwargs.get('env') or {})
        done = subprocess.run(
            [sys.executable, kwargs.get('script', SCAFFOLD), '--project-root',
             self.root] + list(args), capture_output=True, encoding='utf-8',
            timeout=300, env=env, stdin=subprocess.DEVNULL)
        return done.returncode, done.stdout, done.stderr

    def path(self, rel):
        return os.path.join(self.root, rel)

    def has(self, rel):
        return os.path.exists(self.path(rel))

    def config(self):
        return json.loads(read(self.path('.purlin/config.json')))

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


def readable(root):
    """`{path: text}` for every file outside `.git/` that reads as UTF-8."""
    found = {}
    for rel, body in tree(root).items():
        if body is None:
            continue
        try:
            found[rel] = body.decode('utf-8')
        except UnicodeDecodeError:
            continue
    return found


def masked(output, root):
    """The output with the project's path and the commit's sha set aside."""
    return re.sub(r'^Committed [0-9a-f]{7},', 'Committed <sha7>,',
                  output.replace(root, '<root>'), flags=re.M)


def tag_foreign(made):
    """A spec whose one proof is tagged `@env` for a system this machine is
    not: Windows, or macOS on a Windows machine."""
    here = evidence_module.host_os()
    system = 'windows' if here != 'windows' else 'macos'
    write(made.path('specs/core/login.md'), SPEC.replace(
        'verify it returns a session',
        'verify it returns a session @env(%s)' % system))
    return system


def head(root):
    return git(root, 'rev-parse', 'HEAD').stdout.strip()


ON_WINDOWS = pytest.mark.skipif(
    os.name != 'nt', reason='only a Windows machine can show it')


# ---------------------------------------------------------------------------
# The one question, and the settings file
# ---------------------------------------------------------------------------

class TestTheQuestion:

    # purlin: scaffold PROOF-171
    def test_a_foreign_proof_adds_no_question_to_the_commit(self):
        made = Project('pytest')
        try:
            tag_foreign(made)
            code, out, err = made.child()
            assert code == 0, out + err
            # Its output is both streams: a second question on standard
            # error is a second question.
            assert (out + err).count('[y/N]') == 1, out + err
            assert '[y/N]' not in err, err
            (asked,) = [line for line in out.splitlines() if '[y/N]' in line]
            assert asked == 'Commit the files setup wrote? [y/N] ', out
        finally:
            made.close()

    # purlin: scaffold PROOF-88
    def test_an_empty_project_is_asked_only_whether_to_commit(self):
        made = Project(None, host=None)
        try:
            code, out, err = made.child()
            assert code == 0, out + err
            assert [line[:-len(' [y/N] ')] for line in out.splitlines()
                    if line.endswith(' [y/N] ')] == [
                        'Commit the files setup wrote?'], out
            assert out.count('?') == 1, out
            # The one question is the one question on either stream: setup
            # writes nothing at all to standard error here.
            assert (out + err).count('?') == 1, out + err
            assert err == '', err
            assert made.config()['tests'] == []
        finally:
            made.close()


class TestTheSettings:

    # purlin: scaffold PROOF-172
    def test_the_settings_hold_version_and_an_empty_tests(self):
        made = Project('pytest')
        try:
            code, out, err = made.child()
            assert code == 0, out + err
            config = made.config()
            assert sorted(config) == ['tests', 'version'], config
            assert config['tests'] == []
            assert config['version'] == VERSION
        finally:
            made.close()

    # purlin: scaffold PROOF-48
    def test_a_tests_setting_the_project_carries_is_kept(self, project):
        project.run()
        written = project.config()
        ours = [{'name': 'unit', 'run': 'make test REPORT={report}',
                 'report': 'out/unit.xml', 'format': 'junit',
                 'files': ['spec/**/*_spec.py']}]
        written['tests'] = ours
        write(project.path('.purlin/config.json'),
              json.dumps(written, indent=2))
        project.run()
        assert project.config()['tests'] == ours
        assert [suite['name'] for suite in project.config()['tests']] == [
            'unit']


# ---------------------------------------------------------------------------
# The evidence folder and the ignore file
# ---------------------------------------------------------------------------

class TestTheEvidenceFolder:

    # purlin: scaffold PROOF-47
    def test_the_first_run_writes_the_readme(self, project):
        output = project.run()
        with open(project.path(README), 'rb') as got, open(os.path.join(
                ROOT, 'templates', 'evidence-readme.md'), 'rb') as want:
            assert got.read() == want.read()
        text = read(project.path(README))
        assert 'local/' in text and 'ci/' in text
        assert summary_paths(output)[README] == 'wrote', output

    # purlin: scaffold PROOF-136
    @ON_WINDOWS
    def test_on_windows_the_readme_is_the_bytes_purlin_ships(self, project):
        output = project.run()
        with open(project.path(README), 'rb') as got, open(os.path.join(
                ROOT, 'templates', 'evidence-readme.md'), 'rb') as want:
            assert got.read() == want.read()
        text = read(project.path(README))
        assert 'local/' in text and 'ci/' in text
        assert summary_paths(output)[README] == 'wrote', output


class TestTheIgnoreFile:

    # purlin: scaffold PROOF-153
    def test_the_gitignore_names_the_dashboard_page(self, project):
        project.run()
        assert '/purlin-report.html' in read(
            project.path('.gitignore')).splitlines()

    # purlin: scaffold PROOF-154
    def test_the_gitignore_names_the_runtime_folder(self, project):
        project.run()
        assert '.purlin/runtime/' in read(
            project.path('.gitignore')).splitlines()

    # purlin: scaffold PROOF-176
    def test_the_gitignore_names_the_bytecode_cache(self, project):
        project.run()
        assert '__pycache__/' in read(
            project.path('.gitignore')).splitlines()

    # purlin: scaffold PROOF-130
    @ON_WINDOWS
    def test_on_windows_a_crlf_gitignore_is_the_same_after_a_second_run(
            self, project):
        with open(project.path('.gitignore'), 'wb') as handle:
            handle.write(b'node_modules/\r\n')
        project.run()
        first = tree(project.root)['.gitignore']
        project.run()
        assert tree(project.root)['.gitignore'] == first
        assert first.decode('utf-8').count('.purlin/report-data.js') == 1


# ---------------------------------------------------------------------------
# Nothing in the tests, and nothing more than the summary says
# ---------------------------------------------------------------------------

class TestNothingInTheTests:

    # purlin: scaffold PROOF-8
    def test_nothing_is_written_into_a_pytest_suite(self):
        made = Project('pytest')
        try:
            os.remove(made.path('conftest.py'))
            write(made.path('pyproject.toml'), '[tool.pytest]\n')
            before = tree(made.root)
            output = made.run()
            assert not made.has('conftest.py'), output
            assert 'conftest.py' not in output, output
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

    # purlin: scaffold PROOF-61
    def test_a_runner_config_the_project_wrote_is_left_alone(self):
        made = Project('jest')
        try:
            write(made.path('jest.config.js'), '// ours\n')
            output = made.run()
            assert read(made.path('jest.config.js')) == '// ours\n'
            assert 'jest.config.js' not in output, output
        finally:
            made.close()


class TestWhatInitWrites:

    # purlin: scaffold PROOF-108
    def test_what_appears_is_exactly_what_the_summary_wrote(self, project):
        before = tree(project.root)
        output = project.run()
        written = sorted(rel for rel, word in summary_paths(output).items()
                         if word in ('wrote', 'copied'))
        assert written, output
        assert [rel for rel in written if not project.has(rel)] == [], output
        assert sorted(set(tree(project.root)) - set(before)) == written

    # purlin: scaffold PROOF-20
    def test_a_second_run_writes_nothing(self, project):
        project.run()
        before = tree(project.root)
        again = project.run()
        assert [line for line in again.splitlines()
                if line.startswith('wrote')] == [], again
        assert tree(project.root) == before


class TestNoHookIsInstalled:
    """Nothing runs at commit time and nothing runs at push time."""

    # purlin: scaffold PROOF-24
    def test_no_git_hook_is_written_at_all(self, project):
        hooks = project.path('.git/hooks')
        before = sorted(os.listdir(hooks)) if os.path.isdir(hooks) else []
        project.run()
        after = sorted(os.listdir(hooks)) if os.path.isdir(hooks) else []
        assert after == before
        assert 'pre-push' not in after and 'pre-commit' not in after

    # purlin: scaffold PROOF-112
    def test_a_hook_someone_else_wrote_is_left_alone(self, project):
        write(project.path('.git/hooks/pre-push'), 'echo mine\n')
        project.run()
        assert read(project.path('.git/hooks/pre-push')) == 'echo mine\n'


# ---------------------------------------------------------------------------
# The commit setup asks for
# ---------------------------------------------------------------------------

class TestTheCommit:

    # purlin: scaffold PROOF-157
    def test_with_no_answer_nothing_is_committed(self, project):
        before = head(project.root)
        code, out, err = project.child()
        assert code == 0, out + err
        lines = out.splitlines()
        at = lines.index(COMMIT)
        named = [index for index, line in enumerate(lines)
                 if line.split(' ', 1)[0] in ('wrote', 'kept', 'copied')]
        assert named[-1] == at - 1, lines
        assert lines[at - 1] == ('copied scripts/report/purlin-report.html to '
                                 'purlin-report.html'), lines
        assert not [line for line in lines if line.startswith('Committed')]
        assert head(project.root) == before

    # purlin: scaffold PROOF-158
    def test_yes_commits_the_files_and_names_them(self, project):
        code, output, err = project.child('--yes')
        assert code == 0, output + err
        # No commit question on either stream: not its words, not its
        # `[y/N]`, and no question mark before the commit is named.
        shown = output + err
        assert 'Commit the files setup wrote' not in shown, shown
        assert '[y/N]' not in shown, shown
        assert '?' not in output.split('Committed ', 1)[0], output
        assert err == '', err
        assert git(project.root, 'log', '-1', '--format=%s').stdout.strip() \
            == 'chore(init): set up Purlin'
        lines = output.splitlines()
        at = lines.index('Committed %s, the files setup wrote:'
                         % head(project.root)[:7])
        assert lines[at + 1:at + 4] == [
            '  .purlin/config.json', '  .gitignore',
            '  .purlin/evidence/README.md'], lines

    # purlin: scaffold PROOF-160
    def test_a_project_with_no_commit_gets_setup_s_as_its_first(self):
        made = Project('pytest', host=None)
        try:
            assert git(made.root, 'rev-parse', 'HEAD').returncode != 0
            made.run()
            assert git(made.root, 'log', '--format=%s').stdout.splitlines() \
                == ['chore(init): set up Purlin']
        finally:
            made.close()

    # purlin: scaffold PROOF-159
    def test_a_file_already_staged_stays_out_of_the_commit(self, project):
        write(project.path('notes.txt'), 'ours\n')
        git(project.root, 'add', 'notes.txt')
        project.run()
        committed = git(project.root, 'show', '--name-only', '--format=',
                        'HEAD').stdout.split()
        assert sorted(committed) == ['.gitignore', '.purlin/config.json',
                                     '.purlin/evidence/README.md'], committed
        assert git(project.root, 'diff', '--cached',
                   '--name-only').stdout.split() == ['notes.txt']

    # purlin: scaffold PROOF-174
    def test_a_second_run_with_yes_commits_what_the_first_wrote(self):
        made = Project('pytest', host=None)
        try:
            code, out, err = made.child()
            assert code == 0, out + err
            assert git(made.root, 'rev-parse', 'HEAD').returncode != 0
            code, out, err = made.child('--yes')
            assert code == 0, out + err
            lines = masked(out, made.root).splitlines()
            at = lines.index('Committed <sha7>, the files setup wrote:')
            assert lines[at + 1:at + 4] == [
                '  .purlin/config.json', '  .gitignore',
                '  .purlin/evidence/README.md'], lines
            assert git(made.root, 'log', '--format=%s').stdout.splitlines() \
                == ['chore(init): set up Purlin']
        finally:
            made.close()

    # purlin: scaffold PROOF-175
    def test_a_tracked_gitignore_is_committed_by_the_second_run(self):
        made = Project(None, host=None)
        try:
            write(made.path('README.md'), '# The project\n')
            write(made.path('.gitignore'), 'node_modules/\n')
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'the project')
            first = head(made.root)
            code, out, err = made.child()
            assert code == 0, out + err
            assert head(made.root) == first
            code, out, err = made.child('--yes')
            assert code == 0, out + err
            assert git(made.root, 'rev-parse', 'HEAD~1').stdout.strip() \
                == first, out
            committed = git(made.root, 'show', '--name-only', '--format=',
                            'HEAD').stdout.split()
            assert sorted(committed) == [
                '.gitignore', '.purlin/config.json',
                '.purlin/evidence/README.md'], committed
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The flags
# ---------------------------------------------------------------------------

class TestTheFlags:

    # purlin: scaffold PROOF-178
    def test_the_usage_lists_setup_s_flags_and_no_other(self, project):
        code, out, err = project.child('--help')
        assert code == 0
        # Every word of the usage that opens with two dashes, in any case
        # and with any character a flag can hold, on either stream.
        assert sorted(set(re.findall(r'(?<![\w-])--[^\s,\[\]()=|]+',
                                     out + err))) == [
            '--apply', '--help', '--project-root', '--test-command',
            '--update', '--yes'], out + err
        before = tree(project.root)
        code, _out, err = project.child('--colour')
        assert code == 2
        assert 'unrecognized arguments: --colour' in err, err
        assert tree(project.root) == before


# ---------------------------------------------------------------------------
# The refusals, and the hand-off to the upgrade
# ---------------------------------------------------------------------------

class TestTheRefusals:

    # purlin: scaffold PROOF-31
    def test_outside_a_repository_setup_refuses(self):
        directory = tempfile.mkdtemp(prefix='purlin-nogit-')
        try:
            done = subprocess.run(
                [sys.executable, SCAFFOLD, '--project-root', directory,
                 '--yes'], capture_output=True, encoding='utf-8',
                timeout=300, stdin=subprocess.DEVNULL)
            assert done.returncode == 2
            assert done.stderr == ('This is not a git repository. Run git '
                                   'init, then purlin:init.\n'), done.stderr
            assert os.listdir(directory) == []
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    # purlin: scaffold PROOF-128
    def test_a_settings_file_that_cannot_be_read_stops_setup(self, project):
        broken = '{\n  "version": "0.1.0",\n  "tests": [],\n}\n'
        write(project.path('.purlin/config.json'), broken)
        # The cause is the JSON reader's own words and line, which differ
        # between Python releases.
        with pytest.raises(ValueError) as reader:
            json.loads(broken)
        cause = '%s at line %d' % (reader.value.msg, reader.value.lineno)
        before = tree(project.root)
        code, out, err = project.child()
        assert code == 1, out + err
        assert ('.purlin/config.json cannot be read: %s. Fix the file by '
                'hand; nothing ran and nothing was saved.' % cause
                in (out + err).splitlines()), out + err
        assert tree(project.root) == before

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
                 '--yes'], capture_output=True, encoding='utf-8', timeout=300,
                env=env, stdin=subprocess.DEVNULL)
            assert done.returncode == 0, done.stdout + done.stderr
            assert ('The files setup wrote are staged and not committed: no '
                    'email was given and auto-detection is disabled.'
                    in done.stdout.splitlines()), done.stdout
            assert '.purlin/config.json' in git(
                made.root, 'diff', '--cached', '--name-only').stdout.split()
        finally:
            shutil.rmtree(empty, ignore_errors=True)
            made.close()

    # purlin: scaffold PROOF-33
    def test_update_hands_the_project_to_the_upgrade(self, project):
        project.run()
        code, out, err = project.child('--update', '--yes')
        assert code == 0, out + err
        assert ('Nothing is pending: this project is at %s.' % VERSION
                in out.splitlines()), out

    # purlin: scaffold PROOF-177
    def test_update_hands_over_the_migrations_named_and_a_test_command(
            self, project):
        project.run()
        write(project.path('.purlin/config.json'), json.dumps(
            {'version': '0.9.5', 'test_framework': 'pytest'}) + '\n')
        git(project.root, 'add', '-A')
        git(project.root, 'commit', '-q', '-m', 'the settings 0.9.5 wrote')
        code, out, err = project.child(
            '--update', '--apply', 'config', '--test-command',
            'pytest=make test REPORT={report}')
        assert code == 0, out + err
        assert '[y/N]' not in out, out
        assert [(entry['name'], entry['run'])
                for entry in project.config()['tests']] == [
                    ('pytest', 'make test REPORT={report}')]
        assert project.config()['version'] == VERSION


# ---------------------------------------------------------------------------
# Both ways Purlin is loaded
# ---------------------------------------------------------------------------

def copy_plugin():
    """A marketplace-style install: a copy under
    `<cache>/purlin/purlin/<version>/`."""
    cache = os.path.realpath(tempfile.mkdtemp(prefix='purlin-cache-'))
    installed = os.path.join(cache, 'purlin', 'purlin', VERSION)
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


def from_the_copy(made, installed):
    """Set `made` up with the copy's own script, `CLAUDE_PLUGIN_ROOT` naming
    it, as a marketplace install runs it."""
    code, out, err = made.child(
        '--yes', script=os.path.join(installed, 'scripts', 'init',
                                     'scaffold.py'),
        env={'CLAUDE_PLUGIN_ROOT': installed})
    assert code == 0, out + err
    return out


class TestTheMarketplacePath:

    # purlin: scaffold PROOF-22
    def test_the_copy_sets_a_project_up_the_same_way(self):
        cache, installed = copy_plugin()
        made, here = Project('pytest'), Project('pytest')
        try:
            theirs_out = from_the_copy(made, installed)
            code, ours_out, err = here.child('--yes')
            assert code == 0, ours_out + err
            theirs, ours = tree(made.root), tree(here.root)
            for files in (theirs, ours):
                files.pop(REPORT_DATA, None)
            assert theirs == ours
            assert (masked(theirs_out, made.root)
                    == masked(ours_out, here.root))
        finally:
            made.close()
            here.close()
            shutil.rmtree(cache, ignore_errors=True)

    # purlin: scaffold PROOF-23
    def test_no_project_file_names_a_development_folder(self):
        made = Project('pytest')
        try:
            made.run()
            files = readable(made.root)
            assert files
            for rel, text in files.items():
                kept = text.replace('/dev/null', '')
                assert '/dev/' not in kept, rel
                # Nor a relative path into it, such as `dev/test_x.py`,
                # whatever it is attached to: `-cdev/pytest.ini` holds one.
                # So no `dev/` or `dev\` is left anywhere in the file.
                assert re.findall(r'\S*dev[/\\]\S*', kept) == [], rel
        finally:
            made.close()

    # purlin: scaffold PROOF-132
    @ON_WINDOWS
    def test_on_windows_no_file_names_the_copy(self):
        cache, installed = copy_plugin()
        made = Project('pytest')
        try:
            from_the_copy(made, installed)
            spellings = {installed, installed.replace('\\', '/')}
            for rel, text in readable(made.root).items():
                for spelled in spellings:
                    assert spelled not in text, (rel, spelled)
        finally:
            made.close()
            shutil.rmtree(cache, ignore_errors=True)


# ---------------------------------------------------------------------------
# A real project of each language, walked from setup to the signed tag
# ---------------------------------------------------------------------------
#
# Each project is built once for this file and walked step by step with the
# commands a person runs: setup with nothing to answer from, the first test
# run and the entry it suggests, `purlin:test --all --commit`, the audit, and
# `purlin:sign`, which writes the signed tag. Every step's output is kept,
# and each case below reads the step it is about. Nothing here reaches a git
# host: the remote is a bare repository on disk, and no token is set.

RUN_SCRIPT = os.path.join(ROOT, 'scripts', 'run', 'purlin_run.py')
SIGN_SCRIPT = os.path.join(ROOT, 'scripts', 'review', 'sign.py')
SUGGESTED = 'Suggested tests setting: '
SIGN_OPTIONAL = ('Every rule passes its tests on the committed evidence. Optional: '
             'sign this version with purlin:sign')

GREETING_SPEC = """# Feature: greeting

> Scope: %s
> Description: One rule, walked from its first test run to the signed tag.

## Rules

- RULE-1: `greet(name)` returns `Hello, <name>!`

## Proof

- PROOF-1 (RULE-1): `greet("Ada")` returns exactly `Hello, Ada!` @env(%s)
"""

# The greeting proof is tagged for the system this machine is, so a person's
# run here proves it and nothing is left to run on another system.
HERE_OS = evidence_module.host_os()

# What each language's project holds before setup runs, the file its rule
# covers, and its one marked test, written after setup.
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
    person's machine, and no token means no request is made of any host.
    This interpreter's folder goes first on the search path, so the
    suggested `python3 -m pytest` finds pytest. The `claude` found is the
    fake the session put on the path.
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

    def purlin(self, name, *args):
        return self.step(name, [sys.executable, RUN_SCRIPT, '--project-root',
                                self.root] + list(args))

    def sign(self, name, *args):
        return self.step(name, [sys.executable, SIGN_SCRIPT] + list(args)
                         + ['--project-root', self.root])

    def lines(self, name):
        return self.out[name].splitlines()

    def last_lines(self, name, count):
        return [line for line in self.lines(name) if line.strip()][-count:]

    def commit_all(self, message):
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-q', '-m', message)


def take_the_suggestion(root, output):
    """Write the setting a first test run suggested, as `purlin:test` does."""
    (line,) = [line for line in output.splitlines()
               if line.startswith(SUGGESTED)]
    path = root / '.purlin' / 'config.json'
    config = json.loads(path.read_text(encoding='utf-8'))
    config['tests'] = json.loads(line[len(SUGGESTED):])
    path.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')


def set_up(base, language, prepare=None):
    """A project of `language` set up with nothing to answer from, its first
    spec and marked test committed, the entry its first test run suggested
    written, and the test run again with it."""
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

    walk.step('init', [sys.executable, SCAFFOLD, '--project-root', walk.root])
    walk.facts['tests after init'] = json.loads(read(walk.path(
        '.purlin/config.json')))['tests']
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


def run_and_commit(walk):
    """`purlin:test --all --commit`, then the audit, committed the same way."""
    walk.purlin('commit', '--all', '--test', '--commit')
    walk.facts['work subject'] = walk.git('log', '-1', '--format=%s', 'HEAD~1')
    walk.facts['work sha7'] = walk.git('rev-parse', 'HEAD~1')[:7]
    walk.facts['evidence subject'] = walk.git('log', '-1', '--format=%s')
    walk.facts['evidence paths'] = walk.git(
        'show', '--name-only', '--format=', 'HEAD').splitlines()
    walk.purlin('audit', '--all', '--audit', '--commit')
    return walk


def sign_off(walk):
    """An SSH signing key for jane@acme.com, and `purlin:sign --answers` with
    the signature answered yes."""
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
    walk.facts['branch'] = walk.git('rev-parse', '--abbrev-ref', 'HEAD')
    answers = os.path.join(os.path.dirname(walk.root), 'answers.json')
    write(answers, json.dumps({'audit': 'go on', 'stops': {},
                               'sign': 'jane@acme.com'}))
    walk.sign('sign', '--answers', answers)
    walk.facts['signed commit'] = git(walk.root, 'cat-file', 'commit',
                                      'HEAD').stdout
    walk.facts['tags'] = walk.git('tag', '-l').splitlines()
    walk.facts['tagged'] = walk.git('rev-list', '-n', '1', 'signed/0.1.0')
    walk.facts['head'] = walk.git('rev-parse', 'HEAD')
    return walk


@pytest.fixture(scope='module')
def python_walk(tmp_path_factory):
    base = os.path.realpath(str(tmp_path_factory.mktemp('walk-python')))
    return run_and_commit(set_up(base, 'python'))


@pytest.fixture(scope='module')
def signed_walk(python_walk):
    if not shutil.which('ssh-keygen'):
        pytest.skip('ssh-keygen is not on this machine')
    return sign_off(python_walk)


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
        pytest.skip('dotnet is not installed here')
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
        assert walk.code['init'] == 0, walk.out['init']
        assert walk.facts['tests after init'] == []
        # No `conftest.py` in any folder of the project, `tests/` included.
        assert [path for path in walk.facts['files after init']
                if path.rsplit('/', 1)[-1].lower() == 'conftest.py'] == []
        assert suggested_name(walk) == 'pytest', walk.out['first test run']
        lines = walk.lines('test run')
        assert 'Markers: 1 tied to a test, 0 not tied.' in lines, (
            walk.out['test run'])
        assert '1 rule. 1 passes its tests.' in lines, walk.out['test run']

    # purlin: scaffold PROOF-94
    def test_a_typescript_project_runs_its_marked_test(self,
                                                       typescript_project):
        walk = typescript_project
        assert walk.code['init'] == 0, walk.out['init']
        assert walk.facts['tests after init'] == []
        # No `vitest.config.ts` in any folder of the project outside the
        # packages npm installed.
        assert [path for path in walk.facts['files after init']
                if path.rsplit('/', 1)[-1].lower() == 'vitest.config.ts'
                and not path.startswith('node_modules/')] == []
        assert suggested_name(walk) == 'vitest', walk.out['first test run']
        assert '1 rule. 1 passes its tests.' in walk.lines('test run'), (
            walk.out['test run'])

    # purlin: scaffold PROOF-95
    def test_a_csharp_project_runs_its_marked_test(self, csharp_project):
        walk = csharp_project
        assert walk.code['init'] == 0, walk.out['init']
        assert walk.facts['tests after init'] == []
        assert suggested_name(walk) == 'dotnet', walk.out['first test run']
        assert '1 rule. 1 passes its tests.' in walk.lines('test run'), (
            walk.out['test run'])


class TestRunCommitAndSignOff:

    # purlin: scaffold PROOF-36
    def test_the_test_run_commits_the_work_then_its_evidence(
            self, python_walk):
        walk = python_walk
        assert walk.code['commit'] == 0, walk.out['commit']
        assert (walk.facts['work subject']
                == 'purlin: specs, tests and settings for greeting')
        assert (walk.facts['evidence subject']
                == 'purlin: evidence at %s' % walk.facts['work sha7'])
        assert '.purlin/evidence/local/greeting.json' in walk.facts[
            'evidence paths'], walk.facts
        assert walk.last_lines('commit', 1) == [SIGN_OPTIONAL], walk.out['commit']

    # purlin: scaffold PROOF-119
    def test_the_sign_off_makes_a_signed_commit_naming_the_signer(
            self, signed_walk):
        walk = signed_walk
        assert walk.code['sign'] == 0, walk.out['sign']
        assert '\ngpgsig ' in walk.facts['signed commit'], (
            walk.facts['signed commit'])
        assert ('Signed 0.1.0 as jane@acme.com with the key ending ...%s.'
                % walk.facts['key ending'] in walk.lines('sign')), (
            walk.out['sign'])

    # purlin: scaffold PROOF-93
    def test_the_first_sign_off_writes_the_signed_tag(self, signed_walk):
        walk = signed_walk
        assert 'signed/0.1.0' in walk.facts['tags'], walk.out['sign']
        assert walk.facts['tagged'] == walk.facts['head'], walk.facts
        assert walk.facts['branch'] == 'main'
        assert ('Push the branch and the tag: git push origin main '
                'signed/0.1.0' in walk.lines('sign')), walk.out['sign']
