"""Tests for the committed consumer-CI fixture.

`dev/fixtures/consumer-ci/` is a complete minimal consumer project: what
`purlin:init` writes for a `strong` gate, plus one spec, one module and one
test file. It carries no Purlin `scripts/` and no `dev/`, exactly as a project
that installed Purlin from the marketplace does, so its workflow has to clone
the tooling on the runner.

The fixture's value is that it is the documentation, executed. The workflow is
rendered from `templates/purlin.yml` and compared with the committed file, so
the fixture cannot drift from the template without a red test; the rest asserts
the project is complete, that its structure is what a runner will read, and
that Purlin reads it as one feature with one Linux-scoped proof.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'run'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

import workflow as workflow_module  # noqa: E402
from purlin import payload as payload_module  # noqa: E402

FIXTURE = os.path.join(ROOT, 'dev', 'fixtures', 'consumer-ci')
FIXTURE_REL = 'dev/fixtures/consumer-ci'
WORKFLOW_REL = '.github/workflows/purlin.yml'

# Every file the fixture is made of. `.purlin/runtime/` and the dashboard page
# are deliberately absent: they are generated state that the fixture's own
# `.gitignore` excludes, and a fixture that shipped them would
# ship a claim about a run that did not happen here.
FIXTURE_FILES = (
    '.github/workflows/purlin.yml',
    '.gitignore',
    '.purlin/config.json',
    'greeting.py',
    'specs/core/greeting.md',
    'tests/test_greeting.py',
)

# The Purlin release a consumer's runner clones. The fixture is rendered at the
# version this repository is on, so a release bump and the fixture move
# together.
with open(os.path.join(ROOT, 'VERSION'), encoding='utf-8') as _handle:
    PURLIN_REF = 'v' + _handle.read().strip()


def read(rel, root=FIXTURE):
    with open(os.path.join(root, rel), encoding='utf-8') as handle:
        return handle.read()


def tracked(rel):
    """True when `rel` is tracked by git, not merely present on disk."""
    listed = subprocess.run(['git', 'ls-files', '--error-unmatch', '--', rel],
                            cwd=ROOT, capture_output=True, text=True)
    return listed.returncode == 0


# ---------------------------------------------------------------------------
# A structural read of the workflow, with the standard library alone
# ---------------------------------------------------------------------------

def parse_blocks(text):
    """`{top-level key: [line, ...]}` for a YAML document of plain mappings.

    This is not a YAML parser and does not pretend to be one. It checks the
    shape a workflow file has to have: comments and blank lines between
    blocks, every other line indented under a key at column zero, no tabs, and
    every indent a multiple of two. Anything else raises, which is the point:
    a rendered file that is not shaped like a workflow must fail here rather
    than on a runner.
    """
    blocks = {}
    current = None
    for number, line in enumerate(text.splitlines(), 1):
        if '\t' in line:
            raise ValueError('line %d has a tab' % number)
        if line.rstrip() != line:
            raise ValueError('line %d has trailing whitespace' % number)
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip(' '))
        if indent % 2:
            raise ValueError('line %d is indented by %d' % (number, indent))
        if indent == 0:
            if ':' not in line:
                raise ValueError('line %d is not a key: %r' % (number, line))
            current = line.split(':', 1)[0]
            blocks[current] = []
        elif current is None:
            raise ValueError('line %d is indented under nothing' % number)
        else:
            blocks[current].append(line)
    return blocks


def step_names(lines):
    """Every `- name:` and `- uses:` in a job's lines, in order."""
    found = []
    for line in lines:
        stripped = line.strip()
        for prefix in ('- name: ', '- uses: '):
            if stripped.startswith(prefix):
                found.append(stripped[len(prefix):])
    return found


# ---------------------------------------------------------------------------
# The workflow
# ---------------------------------------------------------------------------

# purlin: host PROOF-17
def test_the_fixture_workflow_is_what_the_template_renders():
    rendered = workflow_module.render_workflow('github', ['linux'], PURLIN_REF)
    committed = read(WORKFLOW_REL)
    if rendered != committed:
        expected = rendered.splitlines()
        actual = committed.splitlines()
        for index in range(max(len(expected), len(actual))):
            left = expected[index] if index < len(expected) else '<end of file>'
            right = actual[index] if index < len(actual) else '<end of file>'
            if left != right:
                raise AssertionError(
                    '%s/%s differs from the rendered template at line %d:\n'
                    '  template renders: %r\n'
                    '  fixture carries:  %r'
                    % (FIXTURE_REL, WORKFLOW_REL, index + 1, left, right))
        raise AssertionError('the two texts differ only in trailing bytes')


# purlin: host PROOF-40
def test_the_template_still_carries_the_placeholders():
    """A substitution that has become a no-op proves nothing."""
    template = read(os.path.join('templates', 'purlin.yml'), root=ROOT)
    assert '<<MATRIX>>' in template
    assert '<<PURLIN_REF>>' in template


# purlin: host PROOF-41
def test_a_project_with_no_env_tag_gets_no_workflow():
    wanted, reasons = workflow_module.wanted([], 'macos')
    assert wanted is False and reasons == []


# purlin: host PROOF-42
def test_a_proof_tagged_for_another_system_gets_a_workflow_for_that_reason():
    wanted, reasons = workflow_module.wanted(['windows'], 'macos')
    assert wanted is True
    assert reasons == [
        'A proof in specs/ is tagged @env for Windows, which this machine is '
        'not, so only a runner can prove it.'], reasons


# purlin: host PROOF-128
def test_proofs_tagged_for_two_other_systems_are_named_together():
    wanted, reasons = workflow_module.wanted(['windows', 'linux'], 'macos',
                                             'strong')
    assert wanted is True
    assert reasons == [
        'Proofs in specs/ are tagged @env for Linux/Unix and Windows, which '
        'this machine is not, so only a runner can prove them.'], reasons


# purlin: host PROOF-129
def test_tests_tagged_for_two_other_systems_are_named_together_at_passed():
    wanted, reasons = workflow_module.wanted(['windows', 'linux'], 'macos',
                                             'passed')
    assert wanted is True
    assert reasons == [
        'Tests are tagged @env for Linux/Unix and Windows, which this machine '
        'is not, so only a runner can run them.'], reasons


# purlin: host PROOF-43
def test_a_tag_naming_this_machines_own_system_gets_no_workflow():
    wanted, reasons = workflow_module.wanted(['macos'], 'macos')
    assert wanted is False, reasons


# purlin: host PROOF-18
def test_the_workflow_is_shaped_like_a_workflow():
    blocks = parse_blocks(read(WORKFLOW_REL))
    assert sorted(blocks) == ['jobs', 'name', 'on', 'permissions']
    assert 'contents: write' in read(WORKFLOW_REL)
    assert 'pull-requests' not in read(WORKFLOW_REL)
    assert '\n'.join(blocks['on']) == (
        "  push:\n    branches: ['run/**']\n    tags: ['signed/**']")
    for placeholder in ('<<MATRIX>>', '<<PURLIN_REF>>'):
        assert placeholder not in read(WORKFLOW_REL), (
            '%s was left unfilled' % placeholder)


# purlin: host PROOF-45
def test_the_workflow_ends_on_the_test_step_and_uploads_nothing():
    jobs = '\n'.join(parse_blocks(read(WORKFLOW_REL))['jobs'])
    names = step_names(jobs.splitlines())
    assert 'actions/checkout@v4' in names
    assert 'Locate Purlin' in names
    assert 'actions/upload-artifact@v4' not in names, (
        'a run uploads nothing: the two runs are a remote run and a tag run')
    assert names[-1] == 'Run the tests', (
        "the test step is the last word of every run: %s" % names)
    last = jobs.split('- name: Run the tests', 1)[1]
    assert 'scripts/run/purlin_run.py" --all --ci' in last
    assert '- name:' not in last and '- uses:' not in last


# purlin: host PROOF-44
def test_the_job_is_named_purlin():
    jobs = parse_blocks(read(WORKFLOW_REL))['jobs']
    assert jobs[0].strip() == 'purlin:', jobs[0]
    job_keys = [line.strip() for line in jobs
                if len(line) - len(line.lstrip(' ')) == 2]
    assert job_keys == ['purlin:'], 'the workflow has one job: %s' % job_keys
    for word in ('pull_request', 'fork'):
        assert word not in read(WORKFLOW_REL), (
            '%r appears in the workflow; it runs on a push alone' % word)


# purlin: host PROOF-47
def test_the_azure_pipeline_has_the_same_triggers_and_ends_on_the_test_step():
    pipeline = workflow_module.render_workflow('azure', ['windows'],
                                               PURLIN_REF)
    blocks = parse_blocks(pipeline)
    assert '\n'.join(blocks['trigger']) == (
        '  branches:\n    include:\n      - run/*\n'
        '  tags:\n    include:\n      - signed/*')
    assert 'pr: none' in pipeline.splitlines()
    steps = [line.strip() for line in blocks['jobs']
             if line.strip().startswith('- ')]
    assert steps[-1] == ('- bash: python3 "$PURLIN_ROOT/scripts/run/'
                         'purlin_run.py" --all --ci'), steps
    tail = pipeline.split('purlin_run.py" --all --ci', 1)[1]
    assert 'displayName: Run the tests' in tail
    assert '- bash:' not in tail and '- task:' not in tail


# purlin: host PROOF-51
def test_the_matrix_is_the_one_operating_system_the_spec_names():
    jobs = '\n'.join(parse_blocks(read(WORKFLOW_REL))['jobs'])
    assert 'os: [ubuntu-latest]' in jobs
    assert 'windows-latest' not in jobs
    assert workflow_module.env_tags_in_specs(FIXTURE) == ['linux']


# purlin: host PROOF-19
def test_the_matrix_follows_a_fixed_order():
    assert workflow_module.runners_for(['windows', 'linux']) == [
        'ubuntu-latest', 'windows-latest']


# purlin: host PROOF-48
def test_a_project_that_names_windows_alone_gets_one_windows_job():
    assert workflow_module.runners_for(['windows']) == ['windows-latest']
    rendered = workflow_module.render_workflow('github', ['windows'],
                                               PURLIN_REF)
    assert 'os: [windows-latest]' in rendered
    assert 'ubuntu-latest' not in rendered


# purlin: host PROOF-49
def test_two_named_systems_get_two_jobs_and_no_linux_one():
    assert workflow_module.runners_for(['windows', 'macos']) == [
        'macos-latest', 'windows-latest']


# purlin: host PROOF-50
def test_a_name_that_is_no_operating_system_adds_no_job():
    assert workflow_module.runners_for(['plan9']) == []


# purlin: host PROOF-46
def test_the_workflow_clones_the_release_the_project_pins():
    jobs = '\n'.join(parse_blocks(read(WORKFLOW_REL))['jobs'])
    assert 'ref="%s"' % PURLIN_REF in jobs, (
        'a consumer runner has no plugin, so the ref it clones must be pinned')
    assert 'https://github.com/rlabarca/purlin' in jobs
    assert 'vars.PURLIN_REF' in jobs, 'the pin must be movable without an edit'


# ---------------------------------------------------------------------------
# The project
# ---------------------------------------------------------------------------

# purlin: host PROOF-20
def test_the_fixture_is_complete_and_every_file_is_tracked():
    on_disk = set()
    for folder, dirnames, filenames in os.walk(FIXTURE):
        dirnames[:] = [d for d in dirnames if d != '__pycache__']
        for name in filenames:
            rel = os.path.relpath(os.path.join(folder, name), FIXTURE)
            on_disk.add(rel.replace(os.sep, '/'))

    assert on_disk == set(FIXTURE_FILES), (
        'the fixture holds %s and is missing %s'
        % (sorted(on_disk - set(FIXTURE_FILES)),
           sorted(set(FIXTURE_FILES) - on_disk)))
    for rel in FIXTURE_FILES:
        assert tracked(FIXTURE_REL + '/' + rel), (
            '%s/%s is on disk but not tracked, so a clone of this repository '
            'would not carry it' % (FIXTURE_REL, rel))


# purlin: host PROOF-84
def test_the_config_is_the_shape_this_release_reads():
    config = json.loads(read('.purlin/config.json'))
    assert config['gate'] == 'strong'
    assert [suite['name'] for suite in config['tests']] == ['pytest']
    assert config['version'] == PURLIN_REF[1:]
    template = json.loads(read(os.path.join('templates', 'config.json'),
                               root=ROOT))
    assert list(config) == ['version'] + list(template), (
        'the fixture config carries %s where init writes %s'
        % (list(config), ['version'] + list(template)))


# purlin: host PROOF-87
def test_purlin_reads_the_fixture_as_one_feature_with_a_linux_proof():
    data = payload_module.build_payload(FIXTURE, generated_by='test')
    assert data['warnings'] == []
    assert [f['name'] for f in data['features']] == ['greeting']
    greeting = data['features'][0]
    assert [r['id'] for r in greeting['rules']] == ['RULE-1', 'RULE-2']

    envs = {proof['id']: proof['env']
            for rule in greeting['rules'] for proof in rule['proofs']}
    assert envs == {'PROOF-1': None, 'PROOF-2': 'linux'}
    assert data['gate']['gate'] == 'strong'
    assert data['gate']['min_strength'] == 70
    assert data['evidence'] == {}, 'no run has happened in the fixture'


# purlin: host PROOF-85
def test_the_fixtures_own_test_file_names_nothing_of_purlin():
    test_file = 'tests/test_greeting.py'
    imported = set()
    for line in read(test_file).splitlines():
        words = line.split()
        if words[:1] in (['import'], ['from']):
            imported.add(words[1].split('.')[0])
    assert imported == {'os', 'sys', 'greeting'}, imported
    assert 'scripts' not in read(test_file) and 'dev/' not in read(test_file)


# purlin: host PROOF-86
def test_the_fixtures_own_test_file_runs_by_itself(tmp_path):
    """The fixture's tests, run by themselves; the Linux one passes on Linux alone."""
    test_file = 'tests/test_greeting.py'
    ini = tmp_path / 'pytest.ini'
    ini.write_text('[pytest]\n', encoding='utf-8')
    report = tmp_path / 'report.xml'
    ran = subprocess.run(
        [sys.executable, '-m', 'pytest', test_file, '-q', '-p', 'no:cacheprovider',
         '-c', str(ini), '--rootdir', FIXTURE, '--junitxml', str(report)],
        cwd=FIXTURE, capture_output=True, text=True,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    xml = report.read_text(encoding='utf-8')
    outcomes = {}
    for case in xml.split('<testcase ')[1:]:
        name = case.split(' name="', 1)[1].split('"', 1)[0]
        body = case.split('</testcase>')[0]
        outcomes[name] = ('failed' if '<failure' in body or '<error' in body
                          else 'skipped' if '<skipped' in body else 'passed')
    on_linux = sys.platform.startswith('linux')
    assert outcomes == {
        'test_greet_names_and_empty': 'passed',
        'test_os_tag_is_linux': 'passed' if on_linux else 'failed',
    }, ran.stdout + ran.stderr
    assert ran.returncode == (0 if on_linux else 1), ran.stdout + ran.stderr


# ---------------------------------------------------------------------------
# sqlite3 on a Windows runner
# ---------------------------------------------------------------------------

SQLITE_STEP = 'Install sqlite3 on Windows'
CHOCO_ARGS = 'install sqlite -y --no-progress'
# A test command that runs SQL scripts, as a project's settings name it.
SQL_SETTINGS = ('{"tests": [{"name": "sql", '
                '"run": "sqlite3 -bail :memory: < {files}"}]}\n')
# The step runs under bash with a search path of stand-ins, so it is run
# where a POSIX shell and symbolic links are at hand.
posix_only = pytest.mark.skipif(
    os.name == 'nt', reason='the step is run under bash with stand-in tools')


def _github_step(text, name):
    """The script of one GitHub step's `run: |` block, dedented."""
    lines = text.splitlines()
    start = lines.index('      - name: %s' % name)
    run = next(index for index in range(start, len(lines))
               if lines[index].strip() == 'run: |')
    body = []
    for line in lines[run + 1:]:
        if line.strip() and len(line) - len(line.lstrip(' ')) < 10:
            break
        body.append(line[10:])
    return '\n'.join(body).strip() + '\n'


def _azure_step(text, name):
    """The script of the Azure DevOps `- bash: |` step named `name`."""
    lines = text.splitlines()
    end = lines.index('        displayName: %s' % name)
    start = max(index for index in range(end)
                if lines[index] == '      - bash: |')
    return '\n'.join(line[10:] for line in lines[start + 1:end]).strip() + '\n'


def _standin(path, body):
    path.write_text('#!/bin/sh\nPATH=/bin:/usr/bin\n' + body, encoding='utf-8')
    path.chmod(0o755)


def _run_sqlite_step(tmp_path, host, os_value, settings=SQL_SETTINGS,
                     sqlite_found=False):
    """Run the rendered step on this machine as a Windows runner would.

    The project is a git repository holding the runner file and a settings
    file. The search path holds git, find and dirname, a stand-in `choco`
    that logs its arguments and leaves a `sqlite3.exe` under the chocolatey
    folder, a stand-in `cygpath` that answers the path it is given, and a
    `sqlite3` only when `sqlite_found`. `(exit code, stdout, choco's calls,
    the text written to GITHUB_PATH, the folder holding sqlite3.exe)`.
    """
    text = workflow_module.render_workflow(host, ['windows'], PURLIN_REF)
    rel = workflow_module.workflow_path(host)
    script = (_github_step if host == 'github' else _azure_step)(
        text, SQLITE_STEP)
    project = tmp_path / 'project'
    (project / os.path.dirname(rel) if os.path.dirname(rel)
     else project).mkdir(parents=True, exist_ok=True)
    (project / rel).write_text(text, encoding='utf-8')
    (project / '.purlin').mkdir()
    (project / '.purlin' / 'config.json').write_text(settings, encoding='utf-8')
    for args in (['init', '-q'], ['add', '-A'],
                 ['-c', 'user.name=T', '-c', 'user.email=t@example.com',
                  '-c', 'commit.gpgsign=false', 'commit', '-qm', 'init']):
        subprocess.run(['git'] + args, cwd=str(project), check=True,
                       capture_output=True)
    tools = tmp_path / 'bin'
    tools.mkdir()
    for name in ('git', 'find', 'dirname'):
        os.symlink(shutil.which(name), str(tools / name))
    choco_log = tmp_path / 'choco.log'
    _standin(tools / 'choco',
             'echo "$*" >> "$CHOCO_LOG"\n'
             'mkdir -p "$ChocolateyInstall/lib/SQLite/tools"\n'
             'printf "#!/bin/sh\\necho 3.46.1\\n" '
             '> "$ChocolateyInstall/lib/SQLite/tools/sqlite3.exe"\n'
             'chmod +x "$ChocolateyInstall/lib/SQLite/tools/sqlite3.exe"\n')
    _standin(tools / 'cygpath', 'for last; do :; done\necho "$last"\n')
    if sqlite_found:
        _standin(tools / 'sqlite3', 'echo 3.46.1\n')
    github_path = tmp_path / 'github_path'
    github_path.write_text('', encoding='utf-8')
    choco = tmp_path / 'choco'
    variable = 'RUNNER_OS' if host == 'github' else 'AGENT_OS'
    env = {'PATH': str(tools), 'HOME': str(tmp_path),
           'ChocolateyInstall': str(choco), 'GITHUB_PATH': str(github_path),
           'CHOCO_LOG': str(choco_log), variable: os_value}
    # GitHub starts a bash step with -e and pipefail; Azure DevOps does not.
    flags = ['-eo', 'pipefail'] if host == 'github' else []
    done = subprocess.run([shutil.which('bash')] + flags + ['-c', script],
                          cwd=str(project), env=env, capture_output=True,
                          text=True)
    calls = (choco_log.read_text(encoding='utf-8').splitlines()
             if choco_log.exists() else [])
    return (done.returncode, done.stdout + done.stderr, calls,
            github_path.read_text(encoding='utf-8'),
            str(choco / 'lib' / 'SQLite' / 'tools'))


# purlin: host PROOF-121
def test_the_sqlite_step_comes_just_before_the_test_step():
    text = workflow_module.render_workflow('github', ['windows'], PURLIN_REF)
    jobs = '\n'.join(parse_blocks(text)['jobs'])
    names = step_names(jobs.splitlines())
    assert names.index(SQLITE_STEP) == names.index('Run the tests') - 1, names
    block = jobs.split('- name: %s' % SQLITE_STEP, 1)[1].split('- name:', 1)[0]
    assert '        shell: bash' in block.splitlines(), block


@posix_only
# purlin: host PROOF-122
def test_a_windows_runner_gets_sqlite3_when_a_tracked_file_names_it(tmp_path):
    code, output, calls, path, folder = _run_sqlite_step(
        tmp_path, 'github', 'Windows')
    assert code == 0, output
    assert calls == [CHOCO_ARGS], calls
    assert path == folder + '\n', path


@posix_only
# purlin: host PROOF-123
def test_a_macos_runner_installs_nothing(tmp_path):
    code, output, calls, path, _folder = _run_sqlite_step(
        tmp_path, 'github', 'macOS')
    assert code == 0, output
    assert calls == [] and path == '', (calls, path)


@posix_only
# purlin: host PROOF-124
def test_a_project_where_only_the_runner_file_names_sqlite3_installs_nothing(
        tmp_path):
    code, output, calls, path, _folder = _run_sqlite_step(
        tmp_path, 'github', 'Windows', settings='{"tests": []}\n')
    assert code == 0, output
    assert calls == [] and path == '', (calls, path)


@posix_only
# purlin: host PROOF-125
def test_a_windows_runner_that_has_sqlite3_installs_nothing(tmp_path):
    code, output, calls, path, _folder = _run_sqlite_step(
        tmp_path, 'github', 'Windows', sqlite_found=True)
    assert code == 0, output
    assert calls == [] and path == '', (calls, path)


@posix_only
# purlin: host PROOF-126
def test_an_azure_windows_agent_gets_sqlite3_on_its_search_path(tmp_path):
    code, output, calls, path, folder = _run_sqlite_step(
        tmp_path, 'azure', 'Windows_NT')
    assert code == 0, output
    assert calls == [CHOCO_ARGS], calls
    assert '##vso[task.prependpath]%s' % folder in output.splitlines(), output


# ---------------------------------------------------------------------------
# What the runner file's comments say
# ---------------------------------------------------------------------------

def _rendered_for_windows():
    """`{host: the runner file}` for a proof tagged `@env(windows)`."""
    return {host: workflow_module.render_workflow(host, ['windows'],
                                                  PURLIN_REF)
            for host in ('github', 'azure')}


def _comment_text(text):
    """Every comment line of `text`, its `#` taken off, joined into one line."""
    words = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            words.extend(stripped.lstrip('#').split())
    return ' '.join(words)


# purlin: host PROOF-133
def test_the_runner_file_opens_on_why_it_exists():
    for host, text in _rendered_for_windows().items():
        first = []
        for line in text.splitlines():
            if line.strip() in ('', '#'):
                break
            first.append(line.lstrip('#').strip())
        assert ' '.join(first) == (
            'Purlin runs here, on a clean machine, for one reason: a rule '
            'that must hold on an operating system your machine is not.'), host


# purlin: host PROOF-134
def test_the_runner_file_says_whom_the_matrix_holds():
    for host, text in _rendered_for_windows().items():
        assert ('The matrix holds one job for each operating system a proof '
                'in specs/ is tagged @env for that the machine running setup '
                'is not, and no other.') in _comment_text(text), host


# purlin: host PROOF-135
def test_the_runner_file_says_what_starts_a_run():
    for host, text in _rendered_for_windows().items():
        said = _comment_text(text)
        start = said.index('Two things start a run and nothing else does:')
        sentence = said[start:said.index('.', start)]
        assert 'a push to a `run/*` branch' in sentence, (host, sentence)
        assert 'a push of a `signed/*` tag' in sentence, (host, sentence)


# purlin: host PROOF-136
def test_the_runner_file_says_the_job_is_capped_at_ninety_minutes():
    limits = {'github': 'timeout-minutes: 90', 'azure': 'timeoutInMinutes: 90'}
    for host, text in _rendered_for_windows().items():
        assert 'The job is capped at 90 minutes' in _comment_text(text), host
        settings = [line.strip() for line in text.splitlines()
                    if not line.strip().startswith('#')
                    and 'imeout' in line]
        assert settings == [limits[host]], (host, settings)


# purlin: host PROOF-137
def test_the_runner_file_says_no_breaks_and_no_audit_run_there():
    for host, text in _rendered_for_windows().items():
        assert 'No breaks and no AI audit run here.' in _comment_text(text), \
            host
        named = [line for line in text.splitlines()
                 if '--audit' in line or 'mutation' in line]
        assert named == [], (host, named)


# purlin: host PROOF-138
def test_the_runner_file_says_each_test_command_has_an_hour():
    for host, text in _rendered_for_windows().items():
        assert ('The run caps each test command at an hour of its own.'
                in _comment_text(text)), host
